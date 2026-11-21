from datetime import timedelta
from math import exp, floor, sqrt
from statistics import mean, pstdev, NormalDist

from scripts.result_outlook import build_result_projection

from scripts.fixture_matching import (
    KST, completed_history, display_name, known_source, matchup_history, pair, score_of, team_matches, timestamp,
)


UNITS = {"축구": "골", "야구": "점", "농구": "점", "배구": "세트"}
PRIOR_GAMES = 4


def poisson_cdf(points, center):
    term = exp(-center)
    total = term
    for n in range(1, points + 1):
        term *= center / n
        total += term
    return total


def poisson_percentile(center, percentile):
    points = 0
    while points < 35 and poisson_cdf(points, center) < percentile:
        points += 1
    return points


def direction(probability, line, unit):
    if abs(probability - 0.5) < 0.025:
        return f"{line:g}{unit} 기준 언더·오버가 팽팽합니다"
    strength = "약간 " if abs(probability - 0.5) < .1 else ""
    side = "언더" if probability > .5 else "오버"
    return f"{line:g}{unit} {side} 쪽으로 {strength}기웁니다"


def outlook_evidence(fixture, team_keys, selected, h2h, league_count):
    names = dict(zip(team_keys, (fixture["home"], fixture["away"])))
    match_date = lambda day: day.astimezone(KST).date().isoformat()
    teams = [
        {
            "team": names[key],
            "games": [
                [match_date(day), opponent, venue, gf, ga]
                for day, opponent, venue, gf, ga, _ in team_matches(rows, key, names)
            ],
        }
        for key, rows in zip(team_keys, selected)
    ]
    head_to_head = [
        [match_date(day), display_name(home, row["home"], names), display_name(away, row["away"], names), *score]
        for day, home, away, score, row in h2h
    ]
    sources = {}
    for rows in (*selected, h2h):
        for *_, row in rows:
            source = known_source(row)
            if source:
                sources.setdefault(source[1], source)
    evidence = {"teams": teams, "headToHead": head_to_head, "sources": list(sources.values())}
    if league_count >= 12:
        evidence["leagueCount"] = league_count
    return evidence


def market_context(fixture, source, total, unit):
    line, under, over = market_parts(total)
    if line is None:
        return None
    probability = over / (under + over)
    # This is an implied market share, never a model probability.
    lead = "언더 쪽 배당이 낮습니다" if under < over else "오버 쪽 배당이 낮습니다" if over < under else "언더와 오버 배당이 같습니다"
    return {
        "kind": "market", "headline": f"베트맨 기준 {line:g}{unit} · {lead}",
        "basis": f"언더 {under:.2f} · 오버 {over:.2f}. 양쪽 배당을 같은 기준으로 환산하면 언더 몫은 약 {probability:.0%}입니다.",
        "source": source, "archived": fixture.get("status") == "finished",
    }


def market_parts(total):
    if isinstance(total, dict):
        fields = [total.get(key) for key in ("line", "under", "over")]
        if all(type(n) in (int, float) for n in fields) and 0 < fields[0] < 600 and min(fields[1:]) > 1:
            return fields
    return None, None, None


def venue_rate(rows, overall, home_site, prior):
    site = [row for row in rows if row[1 if home_site else 2] == overall]
    goals = lambda row: row[3] if row[1] == overall else row[3][::-1]
    if len(site) >= 3:
        return tuple(0.65 * mean(goals(row)[i] for row in rows) + 0.35 * mean(goals(row)[i] for row in site)
                     for i in range(2))
    return tuple((sum(goals(row)[i] for row in rows) + prior[i] * 2) / (len(rows) + 2) for i in range(2))


def combined_condition(history, tag, line, now):
    if not tag or line is None:
        return None
    cases = [row for row in history if row[-1].get("observedWeatherTag") and row[0] >= now - timedelta(days=730)]
    wet = [row for row in cases if row[-1]["observedWeatherTag"] == tag]
    other = [row for row in cases if row[-1]["observedWeatherTag"] != tag]
    if len(wet) < 18 or len(other) < 30:
        return None
    hits = lambda sample: sum(sum(row[3]) < line for row in sample)
    first, second = hits(wet), hits(other)
    change = first / len(wet) - second / len(other)
    sampling_error = sqrt(0.25 / len(wet) + 0.25 / len(other))
    if abs(change) < max(0.09, sampling_error * 1.6):
        return None
    return change * min(0.35, len(wet) / (len(wet) + 80)), len(wet), first, len(other), second


def match_flow(fixture, unit, midpoint, home_estimate=None, away_estimate=None):
    sport = fixture["sport"]
    if sport == "배구":
        sets = round(midpoint)
        return {
            "headline": {3: "3세트로 끝나는 흐름이 조금 더 유력합니다.",
                         4: "양 팀이 세트를 주고받아 4세트 안팎까지 갈 흐름입니다.",
                         5: "5세트까지 이어질 가능성이 있습니다."}[sets],
            "basis": f"양 팀 경기의 예상 합계는 {midpoint:.1f}세트입니다.",
        }
    if home_estimate is None:
        return {}
    margin = {"축구": 0.45, "야구": 0.65, "농구": 5}[sport]
    difference = home_estimate - away_estimate
    if abs(difference) >= margin:
        team = fixture["home"] if difference > 0 else fixture["away"]
        headline = f"{team} 쪽에 득점이 더 많이 날 흐름입니다."
    else:
        headline = "양 팀 예상 득점이 비슷합니다."
    precision = 0 if sport == "농구" else 1
    return {
        "headline": headline,
        "basis": f"홈·원정 기록을 반영한 예상 · {fixture['home']} {home_estimate:.{precision}f}{unit}"
                 f" · {fixture['away']} {away_estimate:.{precision}f}{unit}",
    }


def build_outlook(fixture, matched_event, events, factors, source, verified=()):
    sport = fixture["sport"]
    unit = UNITS.get(sport)
    if not unit or fixture.get("status") == "cancelled":
        return None
    total = fixture.get("total")
    line, market_under, _ = market_parts(total)
    sources = []
    history = completed_history(fixture, matched_event, events, sources, verified)
    home, away = pair(fixture)
    now = timestamp(fixture.get("startsAt"))
    if not now:
        return None
    selected = [[row for row in history if team in row[1:3] and row[0] >= now - timedelta(days=160)][:10]
                for team in (home, away)]
    usable_market = total if sport != "배구" or (line is not None and line < 6) else None
    if min(map(len, selected)) < 3:
        market = market_context(fixture, source, total, "점" if sport == "배구" else unit)
        result = build_result_projection(fixture, market_source=source)
        if not result:
            return market
        return {
            **(market or {"kind": "result", "archived": fixture.get("status") == "finished"}),
            "result": result,
        }
    league = [row for row in history if row[0] >= now - timedelta(days=180)]
    prior = tuple(mean(row[3][i] for row in league) for i in range(2)) if len(league) >= 12 else None
    if prior is None:
        prior = tuple(mean(row[3][i] for series in selected for row in series) for i in range(2))
    home_for, home_against = venue_rate(selected[0], home, True, prior)
    away_for, away_against = venue_rate(selected[1], away, False, prior[::-1])
    observed = (home_for + away_against + away_for + home_against) / 2
    effective_n = min(map(len, selected))
    midpoint = (observed * effective_n + sum(prior) * PRIOR_GAMES) / (effective_n + PRIOR_GAMES)
    matchup_rows = matchup_history(events, {home, away}, now)
    h2h = [sum(row[3]) for row in matchup_rows]
    if h2h:
        weight = min(len(h2h) / 20, 0.2)
        midpoint = midpoint * (1 - weight) + mean(h2h) * weight

    if sport == "배구":
        midpoint = min(5, max(3, midpoint))
    criterion = market_parts(usable_market)[0]
    if criterion is None and sport == "축구":
        criterion = 2.5
    if sport in {"축구", "야구"}:
        low, high = poisson_percentile(midpoint, .20), poisson_percentile(midpoint, .80)
        probability = poisson_cdf(floor(criterion - 1e-8), midpoint) if criterion else None
    elif sport == "농구":
        scores = [sum(row[3]) for row in league] or [sum(row[3]) for games in selected for row in games]
        spread = max(8, pstdev(scores))
        low, high = round(midpoint - .84 * spread), round(midpoint + .84 * spread)
        probability = NormalDist(midpoint, spread).cdf(criterion) if criterion else None
    else:
        low, high = max(3, floor(midpoint)), min(5, floor(midpoint) + 1)
        key = {(row[0], *row[1:3]): sum(row[3]) for series in selected for row in series}
        probability = sum(v < criterion for v in key.values()) / len(key) if criterion else None

    weather = next((f for f in factors if f.get("category") == "weather" and f.get("forecastTag")), {})
    adjustment = combined_condition(history, weather.get("forecastTag"), criterion, now) if probability is not None else None
    weather_note = ""
    if adjustment:
        effect, n, hits, base_n, base_hits = adjustment
        probability = min(0.97, max(0.03, probability + effect))
        weather_note = f"비슷한 날씨의 같은 리그 경기 {n}개 중 {hits}개가 기준점 미만, 다른 조건은 {base_n}개 중 {base_hits}개였습니다."

    expected = f"{round(midpoint)}" if sport == "농구" else f"{midpoint:.1f}"
    description = direction(probability, criterion, unit) if probability is not None else f"합계 {expected}{unit} 안팎 예상"
    if sport == "배구" and criterion is None:
        description = f"{round(midpoint)}세트 안팎 이어질 경기"
    headline = f"{description} · 예상 합계 {expected}{unit}" if probability is not None else description
    basis = f"양 팀 직전 {len(selected[0])}·{len(selected[1])}경기와 최근 리그 흐름을 반영했습니다."
    if h2h:
        under_h2h = sum(total < criterion for total in h2h) if criterion else None
        basis += f" 맞대결은 {len(h2h)}경기" + (f" 중 {under_h2h}경기가 기준점 미만이었습니다." if under_h2h is not None else "를 참고했습니다.")
    if probability is not None:
        favored = "언더" if probability >= .5 else "오버"
        estimate = max(probability,1 - probability)
        basis += f" {criterion:g}{unit} 기준 {favored} 추정 {estimate:.0%}."
    home_estimate = away_estimate = None
    if sport != "배구" and observed > 0:
        home_share = (home_for + away_against) / (2 * observed)
        home_estimate, away_estimate = midpoint * home_share, midpoint * (1 - home_share)
        precision = 0 if sport == "농구" else 1
        basis += f" 팀별 예상은 홈 {home_estimate:.{precision}f}{unit} · 원정 {away_estimate:.{precision}f}{unit}."
    if market_under:
        basis += f" 베트맨 기준점 {line:g}{'점' if sport == '배구' and line >= 6 else unit}."
    if probability is None or abs(probability - .5) < .025:
        scoring_pose = "standing"
    else:
        scoring_pose = "resting" if probability > .5 else "running"
    result = build_result_projection(fixture, home_estimate, away_estimate, selected, league, source)
    return {
        **({"result": result} if result else {}),
        "kind": "model", "pose": scoring_pose, "headline": headline, "basis": basis, "range": f"{low}–{high}{unit}",
        "flow": match_flow(fixture, unit, midpoint, home_estimate, away_estimate),
        "weather": weather_note, "source": sources[0], "archived": fixture.get("status") == "finished",
        "evidence": outlook_evidence(fixture, (home, away), selected, matchup_rows, len(league)),
    }
