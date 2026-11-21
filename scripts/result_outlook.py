
"""Winner outlook for the same pre-match sample as the scoring projection."""

from itertools import zip_longest
from math import exp, floor, isfinite
from statistics import NormalDist, stdev

from scripts.fixture_matching import pair


SIDES = ("home", "draw", "away")


def usable_number(value):
    return type(value) in (int, float) and isfinite(value)


def display_outlook(fixture, weights, basis, market=False):
    total = sum(weights.values())
    if total <= 0 or len(weights) < 2:
        return None
    shares = {side: weights[side] / total for side in SIDES if side in weights}
    exact = {side: share * 100 for side, share in shares.items()}
    rounded = {side: floor(value) for side, value in exact.items()}
    order = sorted(exact, key=lambda side: exact[side] - rounded[side], reverse=True)
    for side in order[:100 - sum(rounded.values())]:
        rounded[side] += 1

    ranked = sorted(shares, key=shares.get, reverse=True)
    lead, next_best = ranked[:2]
    gap = shares[lead] - shares[next_best]
    favorite = "무승부" if lead == "draw" else fixture[lead]
    if market:
        label = "베트맨 배당 환산"
        headline = "베트맨 배당상 팽팽합니다." if gap < .04 else f"베트맨 배당은 {favorite} 쪽으로 기웁니다."
    else:
        label = "경기 결과 추정"
        if gap < .04:
            headline = "결과 전망이 팽팽합니다."
        elif lead == "draw":
            headline = "무승부가 가장 높은 비중입니다."
        else:
            strength = "근소하게 " if gap < .12 else ""
            headline = f"{favorite} 쪽이 {strength}앞섭니다."
    outcomes = [{"side": side, "percent": value} for side, value in rounded.items()]
    return {"label": label, "headline": headline, "basis": basis, "outcomes": outcomes}


def market_outlook(fixture, source):
    odds = fixture.get("odds")
    if not isinstance(odds, (list, tuple)) or len(odds) != 3:
        return None
    home, draw, away = odds
    if not all(usable_number(odd) and odd > 1 for odd in (home, away)):
        return None
    if draw is not None and (not usable_number(draw) or draw <= 1):
        return None
    if fixture.get("sport") == "축구" and draw is None:
        return None
    weights = {side: 1 / odd for side, odd in zip(SIDES, odds) if odd is not None}
    basis = "베트맨 일반 배당의 역수를 합계 100%로 환산한 배당상 비중입니다."
    result = display_outlook(fixture, weights, basis, market=True)
    if result and source:
        result["source"] = ["베트맨 · 일반 배당", source[1]]
    return result


def score_terms(rate):
    point, mass = exp(-rate), 0
    terms = []
    while mass < 1 - 1e-12:
        terms.append(point)
        mass += point
        point *= rate / len(terms)
    return terms


def point_outcomes(home, away):
    """Poisson score pairs and their win, draw and loss mass."""
    home_below = away_below = 0
    weights = dict.fromkeys(SIDES, 0.0)
    for home_at, away_at in zip_longest(score_terms(home), score_terms(away), fillvalue=0):
        weights["home"] += home_at * away_below
        weights["draw"] += home_at * away_at
        weights["away"] += away_at * home_below
        home_below += home_at
        away_below += away_at
    return weights


def margin_sample(selected, league):
    sources = (league, (row for games in selected for row in games))
    for matches, minimum in zip(sources, (12, 8)):
        unique = {tuple(row[:3]): row[3][0] - row[3][1] for row in matches}
        margins = list(unique.values())
        if len(margins) >= minimum:
            spread = stdev(margins)
            if spread > 0:
                return len(margins), spread
    return None


def volleyball_weights(fixture, selected):
    if len(selected) != 2:
        return None
    home, away = pair(fixture)
    if not home or not away or home == away:
        return None

    def team_results(rows, team):
        records = []
        for _, first, second, (first_sets, second_sets), _ in rows:
            if team in (first, second) and max(first_sets, second_sets) == 3 and min(first_sets, second_sets) in (0, 1, 2):
                in_home = team == first
                won = first_sets > second_sets if in_home else second_sets > first_sets
                records.append((in_home, won))
        return records

    recent_home = team_results(selected[0], home)
    recent_away = team_results(selected[1], away)
    local_home = [won for in_home, won in recent_home if in_home]
    local_away = [won for in_home, won in recent_away if not in_home]
    if min(len(local_home), len(local_away)) >= 4:
        scope, home_results, away_results = "홈팀의 홈·원정팀의 원정", local_home, local_away
    else:
        scope = "양 팀의 최근"
        home_results = [won for _, won in recent_home]
        away_results = [won for _, won in recent_away]
    if min(len(home_results), len(away_results)) < 4:
        return None

    # Give each sample a mild, even prior to keep short win streaks from dominating.
    home_rate = (sum(home_results) + 2) / (len(home_results) + 4)
    away_rate = (sum(away_results) + 2) / (len(away_results) + 4)
    home_chance = (home_rate + 1 - away_rate) / 2
    basis = (f"{scope} 완료 경기 {len(home_results)}·{len(away_results)}개 승패로 추정했습니다. "
             "표본이 짧아 승률을 50% 쪽으로 보정했습니다.")
    return {"home": home_chance, "away": 1 - home_chance}, basis


def build_result_projection(fixture, home_estimate=None, away_estimate=None, selected=(), league=(), market_source=None):
    sport = fixture.get("sport")
    if (sport not in {"축구", "농구", "야구", "배구"} or fixture.get("status") == "cancelled"
            or fixture.get("voided") or not fixture.get("home") or not fixture.get("away")):
        return None
    estimates = (home_estimate, away_estimate)
    if sport == "배구":
        result = volleyball_weights(fixture, selected)
        if result:
            weights, basis = result
            return display_outlook(fixture, weights, basis)
    elif all(usable_number(value) and 0 <= value <= 400 for value in estimates):
        home, away = estimates
        if sport == "농구":
            sample = margin_sample(selected, league)
            if sample:
                count, spread = sample
                win = NormalDist().cdf((home - away) / spread)
                basis = f"예상 점수 홈 {home:.0f}점·원정 {away:.0f}점과 실제 {count}경기의 점수 차 변동 폭을 반영했습니다."
                return display_outlook(fixture, {"home": win, "away": 1 - win}, basis)
        elif max(estimates) <= 200:
            weights = point_outcomes(home, away)
            if sport == "축구":
                basis = f"홈 {home:.1f}골·원정 {away:.1f}골 예상으로 90분 승·무·패를 추정했습니다."
                return display_outlook(fixture, weights, basis)
            if home + away > 0:
                weights.pop("draw")
                basis = f"홈 {home:.1f}점·원정 {away:.1f}점 예상으로 승패가 갈리는 경우를 추정했습니다."
                return display_outlook(fixture, weights, basis)
    return market_outlook(fixture, market_source)
