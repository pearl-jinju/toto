import hashlib
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic

from scripts.fixture_matching import analyze_fixture, match_fixtures, score_of
from scripts.provider_openfootball import fetch_events as openfootball
from scripts.provider_extra import fetch_events as other_scores, historical_results
from scripts.provider_match_stats import get_match_stats
from scripts.provider_standings import get_standings
from scripts.score_outlook import build_outlook
from scripts.venue_weather import enrich_fixtures


logger = logging.getLogger("match-context")
POLL_SECONDS = 1800
RETRY_SECONDS = 240
PREVIEW_FILE = Path(__file__).resolve().parent.parent / "data" / "verified_fixture_previews.json"
VERIFIED_PREVIEWS = {
    (entry["round"], entry["number"], entry["home"], entry["away"]): entry
    for entry in json.loads(PREVIEW_FILE.read_text(encoding="utf-8"))
}


def club_results(preview, league):
    for club in preview.get("clubs", []):
        team = club["team"]
        for day, opponent, venue, gf, ga in club["results"]:
            home, away, score = (team, opponent, [gf, ga]) if venue == "홈" else (opponent, team, [ga, gf])
            yield {"provider": "club-results", "league": league, "id": f"{day}:{home}:{away}",
                   "home": home, "away": away, "start": day + "T12:00:00+09:00", "dateOnly": True,
                   "complete": True, "score": score, "source": club["source"]}


def round_number(feed):
    return (feed["year"] % 100) * 10_000 + feed["round"]


def meta(fixture):
    return {key: fixture.get(key) for key in ("number", "league", "home", "away", "startsAt", "venue", "result", "status", "odds")}


def official_results(feed):
    for fixture in feed["matches"]:
        if not fixture.get("result"):
            continue
        yield {
            "provider": "betman",
            "league": fixture["league"],
            "id": f"{round_number(feed)}:{fixture['number']}",
            "home": fixture["home"],
            "away": fixture["away"],
            "start": fixture["startsAt"],
            "complete": True,
            "score": [int(score) for score in fixture["result"].split(":")],
            "source": [f"베트맨 · 승부식 {feed['round']}회차", feed["source"]],
        }


def previous_round_fixtures(fixtures, current, source):
    """Use only the published schedule gap, without assuming it is the team's entire schedule."""
    start = datetime.fromisoformat(current["startsAt"])
    changes = []
    for team in (current["home"], current["away"]):
        candidates = [f for f in fixtures if f["league"] == current["league"]
                      and f.get("status") != "cancelled" and team in (f["home"], f["away"])]
        previous = max((f for f in candidates if f["startsAt"] < current["startsAt"]),
                       key=lambda f: f["startsAt"], default=None)
        if previous is None:
            continue
        hours = round((start - datetime.fromisoformat(previous["startsAt"])).total_seconds() / 3600)
        if not 0 < hours <= 120:
            continue
        other = previous["away"] if previous["home"] == team else previous["home"]
        away_then = previous["away"] == team
        away_now = current["away"] == team
        changes.append({
            "category": "schedule", "title": team + "의 회차 내 일정", "value": f"시작 간격 약 {hours}시간",
            "text": f"같은 프로토 회차의 {other}전에서 이번 경기까지의 시작 간격입니다. "
                    + ("원정 경기가 연달아 잡혀 있어 교체와 출전 시간 관리가 달라질 수 있습니다." if away_then and away_now
                       else "경기가 연달아 잡히면 교체 시점이나 출전 시간 관리가 달라질 수 있습니다."),
            "source": source,
        })
    return changes


def read_provider(provider, fixtures):
    try:
        return provider(fixtures)
    except Exception as error:
        logger.warning("%s 조회 실패 (%s)", provider.__module__, type(error).__name__)
        return {}


def valid_event(event):
    return isinstance(event, dict) and all(event.get(key) for key in ("provider", "league", "id", "start", "home", "away"))


def distinct(events):
    return list({(e["provider"], e["league"], e["id"]): e for e in events if valid_event(e)}.values())


def recorded_periods(fixture, event):
    if not event or not event.get("complete"):
        return {}
    official = score_of(fixture.get("result"))
    final = score_of(event.get("score"))
    if final is None or (official and final != official):
        return {}
    if event.get("matchStats"):
        return dict(event["matchStats"])
    half = score_of(event.get("half"))
    if fixture["sport"] == "축구" and half and all(h <= f for h, f in zip(half, final)):
        return {"state": "finished", "source": event["source"], "periods": [
            {"label": "전반", "home": half[0], "away": half[1]},
            {"label": "후반", "home": final[0] - half[0], "away": final[1] - half[1]},
        ]}
    return {}


def factor_key(factor):
    return factor.get("category"), factor.get("title")


def combine_context(existing, current):
    if existing.get("fixture", {}).get("home") != current["fixture"]["home"] or existing.get("fixture", {}).get("away") != current["fixture"]["away"]:
        return current
    if existing.get("fixture", {}).get("startsAt") != current["fixture"]["startsAt"]:
        return current
    result = {**existing, **current}
    if result.get("matchStats", {}).get("state") == "live" and "matchStats" not in current:
        result.pop("matchStats")
    if current["fixture"].get("status") == "cancelled":
        result.pop("outlook", None)
        result.pop("flowPreview", None)
        result.pop("matchStats", None)
    # Retain confirmed information across an upstream outage. The original fact timestamps stay attached.
    factors = {factor_key(f): f for f in existing.get("factors", [])}
    updated_categories = {f["category"] for f in current["factors"]}
    factors = {key: f for key, f in factors.items() if key[0] not in updated_categories}
    factors.update((factor_key(f), f) for f in current["factors"])
    result["factors"] = list(factors.values())
    if not current["coverage"].get("matched") and existing.get("coverage", {}).get("matched"):
        result["coverage"]["matchedPreviously"] = True
    return result


class ContextWorker:
    def __init__(self, round_cache, store=None, providers=(openfootball, other_scores), weather=enrich_fixtures):
        self.round_cache = round_cache
        self.store = store
        self.providers = providers
        self.weather = weather
        self.lock = Lock()
        self.wake = Event()
        self.packets = {}
        self.round_id = None
        self.last_events_digest = None
        self.next_run = 0

    def start(self):
        Thread(target=self.run, name="match-context", daemon=True).start()

    def notice_round(self, round_id):
        with self.lock:
            if self.round_id is None or round_id > self.round_id or monotonic() >= self.next_run:
                self.wake.set()

    def cached(self, round_id):
        with self.lock:
            return self.packets.get(round_id)

    def remember(self, round_id, packet):
        with self.lock:
            self.packets[round_id] = packet
            while len(self.packets) > 3:
                self.packets.pop(min(self.packets))

    def run(self):
        while True:
            self.wake.clear()
            try:
                payload, stale = self.round_cache.get()
                if not payload or stale:
                    delay = RETRY_SECONDS
                else:
                    feed = json.loads(payload)
                    round_id = round_number(feed)
                    with self.lock:
                        self.round_id = round_id
                        self.next_run = monotonic() + POLL_SECONDS
                    packet = self.refresh(feed, round_id)
                    self.remember(round_id, packet)
                    delay = POLL_SECONDS if packet["storage"] == "neon" or not self.store else RETRY_SECONDS
            except Exception as error:
                logger.warning("상세 수집 실패 (%s)", type(error).__name__)
                delay = RETRY_SECONDS
            with self.lock:
                self.next_run = monotonic() + delay
            self.wake.wait(delay)

    def refresh(self, feed, round_id):
        fixtures = feed["matches"]
        previews = {
            fixture["number"]: VERIFIED_PREVIEWS[(round_id, fixture["number"], fixture["home"], fixture["away"])]
            for fixture in fixtures
            if (round_id, fixture["number"], fixture["home"], fixture["away"]) in VERIFIED_PREVIEWS
        }
        verified_games = {
            fixture["number"]: list(club_results(previews[fixture["number"]], fixture["league"]))
            for fixture in fixtures if fixture["number"] in previews
        }
        previous = self.cached(round_id)
        if previous is None and self.store:
            try:
                previous = self.store.get(round_id)
                if previous:
                    self.remember(round_id, previous)
            except (OSError, ValueError, KeyError, TypeError) as error:
                logger.warning("Neon 이전 스냅샷 읽기 실패 (%s)", type(error).__name__)
        old_contexts = (previous or {}).get("contexts", {})
        with ThreadPoolExecutor(max_workers=len(self.providers) + 3) as executor:
            jobs = [executor.submit(read_provider, provider, fixtures) for provider in self.providers]
            venues = executor.submit(self.weather, fixtures, round_source=feed["source"])
            archive = executor.submit(historical_results, round_id)
            rankings = executor.submit(get_standings, fixtures)
            responses = [job.result() for job in jobs]
            try:
                venue_factors = venues.result()
            except (OSError, ValueError, KeyError, TypeError):
                venue_factors = {}
            past_proto = archive.result()
            try:
                standings = rankings.result()
            except (OSError, ValueError, KeyError, TypeError) as error:
                logger.warning("리그 순위 확인 실패 (%s)", type(error).__name__)
                standings = {}

        external = distinct(event for response in responses for event in response.get("events", []))
        leagues = {fixture["league"] for fixture in fixtures}
        verified_leagues = {event["league"] for event in external if event["complete"]}
        latest = {key: state for response in responses for key, state in response.get("coverage", {}).items()}
        selected_days = {fixture["league"] for fixture in fixtures}
        events = distinct([*external, *(event for event in past_proto if event["league"] in selected_days), *official_results(feed)])
        archive_events = distinct([*events, *(game for games in verified_games.values() for game in games)])
        digest = hashlib.sha256(json.dumps(archive_events, ensure_ascii=False, sort_keys=True).encode("utf-8")).digest()
        if self.store:
            try:
                if self.last_events_digest != digest:
                    self.store.archive(archive_events)
                    self.last_events_digest = digest
                missing_leagues = leagues - verified_leagues
                if missing_leagues:
                    external = distinct([*self.store.history(missing_leagues, fixtures[0]["startsAt"]),
                                         *external])
                    events = distinct([*external, *events])
            except (OSError, ValueError, KeyError, TypeError) as error:
                logger.warning("Neon 경기 이력 동기화 실패 (%s)", type(error).__name__)

        buckets = defaultdict(list)
        for event in events:
            buckets[event["league"]].append(event)
        matched = match_fixtures(fixtures, [event for event in external if event["provider"] != "betman" and not event.get("dateOnly")])
        try:
            recorded = get_match_stats(fixtures, matched)
        except (OSError, ValueError, KeyError, TypeError) as error:
            logger.warning("경기 통계 확인 실패 (%s)", type(error).__name__)
            recorded = {}
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        contexts = {}
        verified = 0
        analysis_count = 0
        for fixture in fixtures:
            number = fixture["number"]
            provider_event = matched.get(number)
            preview = previews.get(number)
            club_games = verified_games.get(number, ())
            analysis = analyze_fixture(fixture, provider_event, buckets[fixture["league"]], club_games) or {}
            scoring = analysis.pop("scoring", None)
            match_stats = recorded_periods(fixture, provider_event)
            match_stats.update(recorded.get(number) or {})
            if fixture.get("status") == "cancelled":
                match_stats = {}
            factors = list(venue_factors.get(number, venue_factors.get(str(number), [])))
            factors.extend(previous_round_fixtures(fixtures, fixture, [f"베트맨 · {feed['round']}회차 일정", feed["source"]]))
            if scoring:
                factors.append({**scoring, "category": "scoring"})
            if provider_event:
                factors.extend(provider_event.get("factors", []))
                crowd = provider_event.get("attendance")
                if fixture.get("status") == "finished" and isinstance(crowd, int) and crowd > 0:
                    factors.append({"category": "venue", "title": "공식 관중 수", "value": f"{crowd:,}명",
                                    "text": "리그가 이 경기의 공식 결과에 기록한 관중 수입니다.", "source": provider_event["source"]})
            outlook = build_outlook(fixture, provider_event, buckets[fixture["league"]], factors,
                                    ["베트맨 · 해당 회차 득점 기준점", feed["source"]], club_games)
            details = {
                **analysis,
                **({"outlook": outlook} if outlook else {}),
                **({"flowPreview": preview["flow"]} if preview and fixture.get("status") != "cancelled" else {}),
                **({"matchStats": match_stats} if match_stats else {}),
                "fixture": meta(fixture),
                "updatedAt": checked_at,
                "factors": factors,
                "coverage": {
                    "matched": bool(provider_event),
                    "source": provider_event["source"][0] if provider_event else None,
                    "leagueStatus": "verified" if fixture["league"] in verified_leagues else latest.get(fixture["league"], "unavailable"),
                    "checked": ["경기 이력", "경기장 환경", "공개 경기 자료"],
                },
            }
            merged = combine_context(old_contexts.get(str(number), {}), details)
            contexts[str(number)] = merged
            verified += bool(provider_event)
            analysis_count += bool(merged.get("recent") or merged.get("records") or
                                   any(f.get("category") in {"weather", "players", "news", "odds", "scoring"}
                                       for f in merged["factors"]))
        packet = {
            "roundId": round_id,
            "updatedAt": checked_at,
            "officialSnapshotAt": feed["snapshotAt"],
            "matchCount": len(fixtures),
            "verifiedMatches": verified,
            "enrichedMatches": analysis_count,
            "outlookCount": sum(bool(context.get("outlook")) for context in contexts.values()),
            "forecastCount": sum(any(f.get("forecastTag") or (f.get("category") == "weather" and f.get("date"))
                                     for f in context["factors"]) for context in contexts.values()),
            "externalEvents": len(external),
            "leagueCoverage": {league: sum(event["provider"] != "betman" for event in buckets[league]) for league in sorted(leagues)},
            "contexts": contexts,
            "standingsByLeague": {**(previous or {}).get("standingsByLeague", {}), **standings},
            "storage": "memory",
        }
        if self.store:
            try:
                packet["storage"] = "neon"
                self.store.save(round_id, packet)
            except (OSError, ValueError, KeyError, TypeError) as error:
                packet["storage"] = "memory"
                logger.warning("Neon 상세 스냅샷 저장 실패 (%s)", type(error).__name__)
        return packet
