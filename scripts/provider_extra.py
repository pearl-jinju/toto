from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic

from scripts.provider_domestic import fetch_events as domestic
from scripts.provider_openliga import fetch_events as openliga
from scripts.provider_sportsdataverse import fetch_events as nba
from scripts.provider_wkbl import fetch_events as wkbl
from scripts.import_betman_round import extract_fixtures


_archive_lock = Lock()
_betman_cache = {}
ARCHIVE_ROUNDS = 12


def fetch_prior_round(round_id):
    with _archive_lock:
        cached = _betman_cache.get(round_id)
    if cached and monotonic() < cached[0]:
        return cached[1]
    try:
        feed = extract_fixtures(round_id)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []
    events = []
    expected = 0
    for fixture in feed["matches"]:
        if not fixture.get("result"):
            expected += fixture["status"] != "cancelled"
            continue
        events.append({
            "provider": "betman", "league": fixture["league"],
            "id": f"{round_id}:{fixture['number']}", "start": fixture["startsAt"],
            "home": fixture["home"], "away": fixture["away"], "complete": True,
            "score": [int(part) for part in fixture["result"].split(":")],
            "source": [f"베트맨 · {feed['round']}회차 공개 결과", feed["source"]],
        })
    lifetime = 24 * 3600 if not expected else 3 * 3600
    with _archive_lock:
        _betman_cache[round_id] = (monotonic() + lifetime, events)
        while len(_betman_cache) > 30:
            _betman_cache.pop(min(_betman_cache))
    return events


def historical_results(round_id):
    first = max(round_id - ARCHIVE_ROUNDS, (round_id // 10_000) * 10_000 + 1)
    with ThreadPoolExecutor(max_workers=3) as pool:
        return [event for events in pool.map(fetch_prior_round, range(round_id - 1, first - 1, -1)) for event in events]


def fetch_provider(provider, fixtures):
    try:
        result = provider(fixtures)
        if isinstance(result, list):
            result = {"events": result, "coverage": {event["league"]: "verified" for event in result}}
        provider_id = provider.__module__.rsplit(".", 1)[-1].removeprefix("provider_")
        for event in result.get("events", []):
            event.setdefault("provider", provider_id)
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
        return {}


def fetch_events(fixtures):
    providers = (domestic, openliga, nba, wkbl)
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        results = list(pool.map(lambda provider: fetch_provider(provider, fixtures), providers))
    return {
        "events": [event for result in results for event in result.get("events", [])],
        "coverage": {league: state for result in results for league, state in result.get("coverage", {}).items()},
    }
