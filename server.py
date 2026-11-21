import json
import logging
import os
from functools import partial
from http.client import HTTPException
from http.cookiejar import CookieJar
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from scripts.import_betman_round import ORIGIN, extract_fixtures
from scripts.live_context_store import NeonStore
from scripts.live_match_context import ContextWorker, round_number
from scripts.live_score_worker import LiveScoreWorker


DEFAULT_ROUND_ID = 260138
CACHE_TTL_SECONDS = 60
RETRY_DELAY_SECONDS = 30
ALLOWED_ORIGIN = "https://matchindex-proto.onrender.com"
UPSTREAM_ERRORS = (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError)


def discover_round():
    page = f"{ORIGIN}/main/mainPage/gamebuy/buyableGameList.do"
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    agent = "Mozilla/5.0"
    with opener.open(Request(page, headers={"User-Agent": agent}), timeout=8) as response:
        response.read()

    request = Request(
        f"{ORIGIN}/buyPsblGame/inqCacheBuyAbleGameInfoList.do",
        data=b'{"_sbmInfo":{"_sbmInfo":{"debugMode":"false"}}}',
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": ORIGIN,
            "Referer": page,
            "User-Agent": agent,
        },
        method="POST",
    )
    with opener.open(request, timeout=8) as response:
        games = json.load(response)["protoGames"]
    return max(int(game["gmTs"]) for game in games if game["gmId"] == "G101")


class RoundCache:
    def __init__(self, pinned_round=None, fetch=extract_fixtures, discover=discover_round, timer=monotonic):
        self.pinned_round = pinned_round
        self.last_round = DEFAULT_ROUND_ID
        self.fetch = fetch
        self.discover = discover
        self.timer = timer
        self.lock = Lock()
        self.payload = None
        self.fresh_until = 0
        self.retry_after = 0
        self.refreshing = False

    def get(self):
        with self.lock:
            now = self.timer()
            if self.payload is not None and now < self.fresh_until:
                return self.payload, False
            if self.refreshing or now < self.retry_after:
                return self.payload, True
            self.refreshing = True

        try:
            round_id = self.pinned_round
            if round_id is None:
                try:
                    round_id = self.discover()
                except UPSTREAM_ERRORS:
                    round_id = self.last_round
            result = self.fetch(round_id)
            payload = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except UPSTREAM_ERRORS:
            with self.lock:
                self.retry_after = self.timer() + RETRY_DELAY_SECONDS
                return self.payload, True
        else:
            with self.lock:
                self.last_round = round_id
                self.payload = payload
                self.fresh_until = self.timer() + CACHE_TTL_SECONDS
                return self.payload, False
        finally:
            with self.lock:
                self.refreshing = False


class MatchIndexHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, round_cache, context_worker, live_worker, **kwargs):
        self.round_cache = round_cache
        self.context_worker = context_worker
        self.live_worker = live_worker
        super().__init__(*args, **kwargs)

    def do_GET(self):
        route = urlsplit(self.path)
        path = route.path
        if path == "/healthz":
            self.send_json(200, b'{"ok":true}')
        elif path == "/api/round":
            payload, stale = self.round_cache.get()
            if payload is None:
                self.send_json(503, b'{"error":"Round data temporarily unavailable"}', stale=True)
            else:
                round_id = round_number(json.loads(payload))
                self.context_worker.notice_round(round_id)
                self.live_worker.notice_round(round_id)
                self.send_json(200, payload, stale=stale)
        elif path in {"/api/context", "/api/live"}:
            requested = parse_qs(route.query).get("round", [""])[0]
            if len(requested) != 6 or not requested.isascii() or not requested.isdigit():
                self.send_json(400, b'{"error":"Use a six-digit round ID"}', stale=False)
                return
            worker = self.context_worker if path == "/api/context" else self.live_worker
            packet = worker.cached(int(requested))
            if packet is None:
                self.send_json(202, b'{"pending":true}', stale=True)
            else:
                payload = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.send_json(200, payload, stale=path == "/api/context" and packet["storage"] != "neon")
        else:
            super().do_GET()

    def send_json(self, status, body, *, stale=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if stale is not None:
            self.send_header("Vary", "Origin")
            if self.headers.get("Origin") == ALLOWED_ORIGIN:
                self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
                self.send_header("Access-Control-Expose-Headers", "X-Data-Stale")
            self.send_header("X-Data-Stale", str(stale).lower())
        if status == 503:
            self.send_header("Retry-After", str(RETRY_DELAY_SECONDS))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    directory = Path(__file__).resolve().parent / "public"
    pinned_round = os.environ.get("BETMAN_ROUND_ID")
    round_cache = RoundCache(int(pinned_round) if pinned_round else None)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    connection = os.environ.get("MATCHINDEX_DATABASE_URL")
    context_worker = ContextWorker(round_cache, NeonStore(connection) if connection else None)
    context_worker.start()
    live_worker = LiveScoreWorker(round_cache)
    live_worker.start()
    handler = partial(MatchIndexHandler, directory=str(directory), round_cache=round_cache,
                      context_worker=context_worker, live_worker=live_worker)
    with ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), handler) as server:
        server.serve_forever()
