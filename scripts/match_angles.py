
"""Concise fixture-specific observations from completed pre-match records."""

from math import isfinite


SCORE_UNITS = {"축구": "골", "농구": "점", "야구": "점", "배구": "세트"}


def observation(label, summary, basis, source=None):
    result = {"label": label, "summary": summary, "basis": basis}
    if (isinstance(source, (list, tuple)) and len(source) == 2
            and all(isinstance(value, str) and value for value in source)
            and source[1].startswith("https://")):
        result["source"] = list(source)
    return result


def h2h_rows(analysis, home, away):
    """Use the historically listed home side to orient both scores."""
    rows = []
    for game in analysis.get("headToHead") or []:
        first, second = game.get("home"), game.get("away")
        score = game.get("score")
        if ({first, second} != {home, away} or not isinstance(score, (list, tuple))
                or len(score) != 2 or any(type(n) is not int or n < 0 for n in score)):
            continue
        rows.append((first == home, score if first == home else score[::-1], game.get("source")))
    return rows


def h2h_angle(rows, fixture, at_home, totals_only=False):
    count = len(rows)
    if count < 3:
        return None
    home, away = fixture["home"], fixture["away"]
    label = "홈 맞대결" if at_home else "최근 맞대결"
    scope = f"{home} 홈 맞대결" if at_home else "홈·원정 합산 맞대결"
    wins = sum(first > second for _, (first, second), _ in rows)
    draws = sum(first == second for _, (first, second), _ in rows)
    losses = count - wins - draws
    source = rows[0][2] if all(row[2] == rows[0][2] for row in rows) else None
    if not totals_only and max(wins, losses) * 3 >= count * 2:
        favored, struggling = (home, away) if wins > losses else (away, home)
        return observation(label, f"{struggling}, {favored} 상대 {count}경기 중 {max(wins, losses)}패.",
                           f"{scope} {count}경기 · {home} 기준 {wins}승 {draws}무 {losses}패.", source)
    if not totals_only and draws * 3 >= count * 2:
        return observation(label, "두 팀은 맞대결에서 자주 비겼습니다.",
                           f"{scope} {count}경기 중 {draws}경기가 무승부였습니다.", source)

    if not totals_only:
        return None

    sport = fixture.get("sport")
    market = fixture.get("total") or {}
    line = market.get("line")
    unit = SCORE_UNITS.get(sport)
    market_line = type(line) in (int, float) and isfinite(line) and 0 < line < 600
    if sport == "배구":
        market_line = market_line and 2.5 <= line <= 5.5
    if not market_line and sport == "축구":
        line = 2.5
    elif unit is None or not market_line:
        return None
    totals = [sum(score) for _, score, _ in rows]
    under = sum(value < line for value in totals)
    over = sum(value > line for value in totals)
    if max(under, over) * 3 < count * 2:
        return None
    direction = "미만" if under > over else "초과"
    hits = max(under, over)
    if market_line:
        threshold = f"{line:g}{unit} {direction}"
        summary = f"과거 맞대결은 현재 기준 {threshold}인 경우가 많았습니다."
    else:
        threshold = "2골 이하" if under > over else "3골 이상"
        summary = f"맞대결에서 합계 {threshold}가 자주 나왔습니다."
    return observation(label, summary,
                       f"{scope} {count}경기 중 {hits}경기에서 합계 {threshold}를 기록했습니다.", source)


def record_angle(stats, name, scope, source):
    count, wins, draws, losses = (stats.get(key, 0) for key in ("played", "wins", "draws", "losses"))
    if (any(type(value) is not int or value < 0 for value in (count, wins, draws, losses))
            or count < 4 or wins + draws + losses != count or max(wins, losses) * 4 < count * 3):
        return None
    what = "승리가 많았습니다" if wins > losses else "패배가 많았습니다"
    return (max(wins, losses) / count, count, f"{name}, {scope}에서 {what}.",
            f"{name} {scope} {count}경기 · {wins}승 {draws}무 {losses}패.", source)


def team_form_angle(fixture, analysis):
    stats = {row.get("team"): row for row in analysis.get("teamStats") or []}
    venue, overall = [], []
    for key, scope in (("home", "최근 홈 경기"), ("away", "최근 원정 경기")):
        name = fixture[key]
        row = stats.get(name, {})
        venue_angle = record_angle(row.get(key) or {}, name, scope, row.get("source"))
        if venue_angle:
            venue.append(venue_angle)
        recent_angle = record_angle(row, name, "최근 경기", row.get("source"))
        if recent_angle:
            overall.append(recent_angle)
    samples = venue or overall
    if samples:
        _, _, summary, basis, source = max(samples, key=lambda item: item[:2])
        return observation("홈·원정 흐름" if venue else "최근 팀 흐름", summary, basis, source)

    if fixture.get("sport") != "축구":
        return None
    candidates = []
    for name, games, source in analysis.get("recent") or []:
        if name not in (fixture["home"], fixture["away"]):
            continue
        scores = [(gf, ga) for _, _, _, gf, ga in games
                  if type(gf) is int and type(ga) is int and gf >= 0 and ga >= 0]
        count = len(scores)
        if count < 4:
            continue
        for goal_count, phrase in (
            (sum(gf == 0 for gf, _ in scores), "득점 없이 끝난 경기가 많았습니다."),
            (sum(ga == 0 for _, ga in scores), "무실점으로 막은 경기가 많았습니다."),
            (sum(gf >= 2 for gf, _ in scores), "두 골 이상 넣은 경기가 많았습니다."),
        ):
            if goal_count * 4 >= count * 3:
                candidates.append((goal_count / count, count, name, phrase, goal_count, source))
    if candidates:
        _, count, name, phrase, hits, source = max(candidates, key=lambda item: item[:2])
        return observation("최근 득점·수비 흐름", f"{name}, {phrase}",
                           f"{name} 최근 리그 {count}경기 중 {hits}경기에서 확인됐습니다.", source)
    return None


def build_match_angle(fixture, analysis, preview=None):
    """Select one documented matchup observation without modifying model estimates."""
    home, away = fixture.get("home"), fixture.get("away")
    if not home or not away or home == away or fixture.get("status") == "cancelled":
        return None
    analysis = analysis or {}
    matchups = h2h_rows(analysis, home, away)
    home_matchups = [row for row in matchups if row[0]]
    for totals_only in (False, True):
        for at_home, rows in ((True, home_matchups), (False, matchups)):
            angle = h2h_angle(rows, fixture, at_home, totals_only)
            if angle:
                return angle

    flow = (preview or {}).get("flow") or {}
    if flow.get("headline") and flow.get("basis") and flow.get("source"):
        return observation("공식 경기 전 분석", flow["headline"], flow["basis"], flow["source"])
    return team_form_angle(fixture, analysis)
