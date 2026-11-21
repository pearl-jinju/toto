from datetime import timedelta
from math import exp, floor, sqrt
from statistics import mean, pstdev, NormalDist

from scripts.fixture_matching import completed_history, known_source, pair, score_of, timestamp


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


def matchup_history(events, teams, before):
    rows = {}
    for event in events:
        when = timestamp(event.get("start"))
        score = score_of(event.get("score"))
        oriented = pair(event)
        if (not when or when >= before - timedelta(minutes=10) or when < before - timedelta(days=730)
                or not event["complete"] or not score or set(oriented) != teams or not known_source(event)):
            continue
        key = next((key for key in rows if key[1:] == oriented and abs(key[0] - when) < timedelta(days=1)), None)
        if key is not None and rows[key] != sum(score):
            rows[key] = None
        elif key is None:
            rows[(when, *oriented)] = sum(score)
    return [value for key,value in sorted(rows.items(), reverse=True) if value is not None][:5]


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


def build_outlook(fixture, matched_event, events, factors, source):
    sport = fixture["sport"]
    unit = UNITS.get(sport)
    if not unit or fixture.get("status") == "cancelled":
        return None
    total = fixture.get("total")
    line, market_under, _ = market_parts(total)
    sources = []
    history = completed_history(fixture, matched_event, events, sources)
    home, away = pair(fixture)
    now = timestamp(fixture.get("startsAt"))
    if not now:
        return None
    selected = [[row for row in history if team in row[1:3] and row[0] >= now - timedelta(days=160)][:10]
                for team in (home, away)]
    usable_market = total if sport != "배구" or (line is not None and line < 6) else None
    if min(map(len, selected)) < 3:
        return market_context(fixture, source, total, "점" if sport == "배구" else unit)
    league = [row for row in history if row[0] >= now - timedelta(days=180)]
    prior = tuple(mean(row[3][i] for row in league) for i in range(2)) if len(league) >= 12 else None
    if prior is None:
        prior = tuple(mean(row[3][i] for series in selected for row in series) for i in range(2))
    home_for, home_against = venue_rate(selected[0], home, True, prior)
    away_for, away_against = venue_rate(selected[1], away, False, prior[::-1])
    observed = (home_for + away_against + away_for + home_against) / 2
    effective_n = min(map(len, selected))
    midpoint = (observed * effective_n + sum(prior) * PRIOR_GAMES) / (effective_n + PRIOR_GAMES)
    h2h = matchup_history(events, {home, away}, now)
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
    elif weather.get("forecastTag") in {"wind", "rain", "fog", "frost", "heat"}:
        weather_note = weather["text"].split(". ")[0] + "."
        if sport == "축구" and criterion and probability >= 0.525 and weather["forecastTag"] == "wind":
            weather_note = "강풍이 실제 구장에서도 이어지면 높은 패스가 흔들려 저득점 전망에 힘을 보탤 수 있습니다."

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
        basis += f" {criterion:g}{unit} 기준 언더 추정 {probability:.0%}."
    if market_under:
        basis += f" 베트맨 기준점 {line:g}{'점' if sport == '배구' and line >= 6 else unit}."
    return {
        "kind": "model", "headline": headline, "basis": basis, "range": f"{low}–{high}{unit}",
        "weather": weather_note, "source": sources[0], "archived": fixture.get("status") == "finished",
    }
