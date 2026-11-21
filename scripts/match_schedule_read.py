"""Turn comparable pre-match schedule evidence into a concise observation."""

from datetime import datetime
from math import isfinite
from urllib.parse import urlsplit


SPORT_RULES = {
    "축구": (
        72, 24,
        "짧은 쪽은 후반까지 같은 강도로 압박하기 어려울 수 있습니다.",
        "후반 압박 강도와 첫 교체 시점",
    ),
    "농구": (
        30, 18,
        "짧은 쪽은 주전 출전 시간을 더 나눠 쓸 수 있습니다.",
        "경기 막판 주전 출전 시간과 속공 수비",
    ),
    "배구": (
        48, 24,
        "짧은 쪽은 세트가 길어질 때 공격수 체력 관리가 중요해질 수 있습니다.",
        "후반 세트 공격수 교체와 블로킹",
    ),
    "야구": (
        18, 18,
        "짧은 쪽은 전 경기에서 소모한 불펜에 따라 투수 교체 선택이 좁아질 수 있습니다.",
        "전 경기 불펜 투구 수와 첫 투수 교체",
    ),
}


def _source(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not all(isinstance(part, str) for part in value):
        return None
    try:
        url = urlsplit(value[1])
    except ValueError:
        return None
    return tuple(value) if value[0] and url.scheme == "https" and url.hostname else None


def _kickoff(value):
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return moment if moment.utcoffset() is not None else None


def _league_gaps(fixture, teams, analysis):
    latest = {}
    kickoff = _kickoff(fixture.get("startsAt"))
    if kickoff is None:
        return latest
    for row in (analysis or {}).get("teamStats", []):
        team = row.get("team")
        if team not in teams or row.get("lastPlayedDateOnly") is not False or not _source(row.get("source")):
            continue
        previous = _kickoff(row.get("lastPlayed"))
        if previous is not None:
            hours = (kickoff - previous).total_seconds() / 3600
            if 0 < hours <= 168:
                latest[team] = hours
    return latest


def _round_gaps(teams, factors):
    rows_by_source = {}
    for factor in factors or ():
        if factor.get("category") != "schedule":
            continue
        team = factor.get("team")
        hours = factor.get("gapHours")
        source = _source(factor.get("source"))
        if (team not in teams or not source or type(hours) not in (int, float)
                or not isfinite(hours) or not 0 < hours <= 120):
            continue
        domain = urlsplit(source[1]).hostname
        if domain != "betman.co.kr" and not domain.endswith(".betman.co.kr"):
            continue
        rows_by_source.setdefault(source, {})[team] = hours
    return next((rows for rows in rows_by_source.values() if all(team in rows for team in teams)), {})


def interpret_match_schedule(fixture, factors, analysis):
    """Compare both teams' known kickoff gaps, never assume actual recovery time."""
    rule = SPORT_RULES.get(fixture.get("sport"))
    if rule is None or fixture.get("status") == "cancelled":
        return None
    teams = (fixture.get("home"), fixture.get("away"))
    if not all(isinstance(team, str) and team for team in teams) or teams[0] == teams[1]:
        return None
    max_short, min_difference, effect, watch = rule
    candidates = (
        (_league_gaps(fixture, teams, analysis), "확인된 같은 리그 경기 시작 간격"),
        (_round_gaps(teams, factors), "베트맨 회차 안에 편성된 경기 시작 간격"),
    )
    for gaps, scope in candidates:
        if not all(team in gaps for team in teams):
            continue
        first, second = sorted(teams, key=gaps.__getitem__)
        if gaps[first] > max_short or gaps[second] - gaps[first] < min_difference:
            continue
        return {
            "headline": f"{first}의 경기 시작 간격이 더 짧습니다.",
            "explanation": (
                f"{scope}은 {first} 약 {gaps[first]:.0f}시간, {second} 약 {gaps[second]:.0f}시간입니다. "
                + effect
            ),
            "watch": watch,
        }
    return None
