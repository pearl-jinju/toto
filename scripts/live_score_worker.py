import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Event, Lock, Thread
from time import monotonic

from scripts.live_match_context import round_number
from scripts.provider_live_scores import fetch_live_scores


CHECK_INTERVAL = 60
LIVE_GRACE = timedelta(seconds=145)
IDENTITY = ("home", "away", "startsAt")
log = logging.getLogger("live-scores")


def pending_fixtures(feed, checked_at):
    return {
        str(match["number"]): match
        for match in feed["matches"]
        if match.get("status") in {"scheduled", "pending"}
        and not match.get("result")
        and datetime.fromisoformat(match["startsAt"]) <= checked_at
    }


def same_fixture(row, fixture):
    return row is not None and all(row.get(field) == fixture[field] for field in IDENTITY)


def valid_live_row(row, fixture):
    if not isinstance(row, dict) or not same_fixture(row, fixture):
        return False
    state = row.get("state")
    if state not in {"live", "final", "delayed", "postponed", "scheduled"}:
        return False
    score = row.get("score")
    if state in {"live", "final"} and not (
        isinstance(score, (list, tuple)) and len(score) == 2 and
        all(type(value) is int and value >= 0 for value in score)
    ):
        return False
    source = row.get("source")
    return (
        isinstance(source, (list, tuple)) and len(source) == 2 and
        all(isinstance(value, str) and value for value in source) and source[1].startswith("https://")
    )


class LiveScoreWorker:
    def __init__(self, round_cache, provider=fetch_live_scores):
        self.round_cache = round_cache
        self.provider = provider
        self.wake = Event()
        self.lock = Lock()
        self.packet = None
        self.observed_round = None

    def start(self):
        Thread(target=self.run, name="live-scores", daemon=True).start()

    def notice_round(self, round_id):
        with self.lock:
            if self.observed_round is None or round_id > self.observed_round:
                self.wake.set()

    def cached(self, round_id):
        with self.lock:
            return self.packet if self.packet and self.packet["roundId"] == round_id else None

    def run(self):
        while True:
            self.wake.clear()
            started = monotonic()
            delay = CHECK_INTERVAL
            try:
                payload, _ = self.round_cache.get()
                if payload is None:
                    delay = 10
                else:
                    feed = json.loads(payload)
                    with self.lock:
                        self.observed_round = round_number(feed)
                    self.refresh(feed)
            except Exception as error:
                log.warning("진행 점수 갱신 실패 (%s)", type(error).__name__)
            self.wake.wait(max(1, delay - (monotonic() - started)))

    def refresh(self, feed):
        round_id = round_number(feed)
        pending = pending_fixtures(feed, datetime.now(timezone.utc))
        previous = (self.cached(round_id) or {}).get("fixtures", {})
        kept = {number: prior for number, fixture in pending.items()
                if (prior := previous.get(number)) and same_fixture(prior, fixture) and prior["state"] == "final"}
        targets = [fixture for number, fixture in pending.items() if number not in kept]
        try:
            reports = self.provider(targets) if targets else {}
            if not isinstance(reports, dict):
                reports = {}
        except Exception as error:
            log.warning("진행 점수 출처 조회 실패 (%s)", type(error).__name__)
            reports = {}
        checked_at = datetime.now(timezone.utc)
        stamp = checked_at.isoformat(timespec="seconds")
        for fixture in targets:
            number = str(fixture["number"])
            current = reports.get(fixture["number"], reports.get(number))
            if current and valid_live_row(current, fixture):
                kept[number] = {**current, "observedAt": stamp}
            elif (prior := previous.get(number)) and same_fixture(prior, fixture):
                if checked_at - datetime.fromisoformat(prior["observedAt"]) <= LIVE_GRACE:
                    kept[number] = prior
        packet = {"roundId": round_id, "updatedAt": stamp, "fixtures": kept}
        with self.lock:
            self.packet = packet
        return packet
