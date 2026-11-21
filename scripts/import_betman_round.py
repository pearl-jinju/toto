"""Fetch the standard fixtures in a public Betman Proto round as compact JSON."""

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, Request, build_opener


ORIGIN = "https://www.betman.co.kr"
KST = timezone(timedelta(hours=9))
STANDARD_MARKET = {"SC": "1", "BS": "2", "BK": "3", "VL": "4"}
SALE_STATE = {"1": "before", "2": "open", "3": "closed", "4": "settled"}


def read_round(round_id):
    page = f"{ORIGIN}/main/mainPage/gamebuy/gameSlip.do?gmId=G101&gmTs={round_id}"
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    with opener.open(Request(page, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as response:
        response.read()

    request = Request(
        f"{ORIGIN}/buyPsblGame/gameInfoInq.do",
        data=json.dumps({
            "gmId": "G101",
            "gmTs": round_id,
            "gameYear": str(2000 + round_id // 10000),
            "_sbmInfo": {"_sbmInfo": {"debugMode": "false"}},
        }).encode(),
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": ORIGIN,
            "Referer": page,
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    with opener.open(request, timeout=20) as response:
        data = json.load(response)
    if data.get("gmTs") != round_id:
        raise ValueError(f"Betman did not return round {round_id}")
    return page, data


def kst_timestamp(value):
    return datetime.fromtimestamp(value / 1000, KST)


def extract_fixtures(round_id):
    source, data = read_round(round_id)
    as_of = datetime.now(KST)
    schedules = data["compSchedules"]
    fixtures = []
    for values in schedules["datas"]:
        row = dict(zip(schedules["keys"], values, strict=True))
        code = row["itemCode"]
        if code not in STANDARD_MARKET or row["betId"] != STANDARD_MARKET[code]:
            continue

        start = kst_timestamp(row["gameDate"])
        odds = [row["winAllot"], row["drawAllot"], row["loseAllot"]]
        sale_status = SALE_STATE.get(row["protoStatus"], "unknown")
        score = row["mchScore"]
        result = score if sale_status == "settled" and re.fullmatch(r"\d+:\d+", score or "") else None
        if row["gameReject"] not in (None, "0", 0):
            status = "cancelled"
        elif result:
            status = "finished"
        else:
            status = "scheduled" if start > as_of else "pending"

        fixture = {
            "number": row["matchSeq"],
            "sport": row["itemName"],
            "sportCode": code,
            "league": row["leagueName"],
            "startsAt": start.isoformat(timespec="seconds"),
            "closesAt": kst_timestamp(row["endDate"]).isoformat(timespec="seconds") if row["endDate"] else None,
            "home": row["homeName"],
            "away": row["awayName"],
            "venue": row["meetStadiumFullName"] or None,
            "status": status,
            "saleStatus": sale_status,
            "result": result,
            "odds": [odd if odd and odd > 0 else None for odd in odds] if any(odds) else None,
        }
        fixtures.append(fixture)

    if not fixtures or len({match["number"] for match in fixtures}) != len(fixtures):
        raise ValueError(f"Missing or duplicate standard fixtures for round {round_id}")

    return {
        "year": 2000 + round_id // 10000,
        "round": round_id % 10000,
        "source": source,
        "snapshotAt": as_of.isoformat(timespec="seconds"),
        "matchCount": len(fixtures),
        "countsBySport": dict(Counter(match["sport"] for match in fixtures)),
        "matches": sorted(fixtures, key=lambda match: (match["startsAt"], match["number"])),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round_id", nargs="?", type=int, default=260138, help="Betman round ID, e.g. 260138")
    parser.add_argument("-o", "--output", help="Write the result as UTF-8 JSON")
    args = parser.parse_args()
    value = json.dumps(extract_fixtures(args.round_id), ensure_ascii=False, separators=(",", ":"))
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as target:
            target.write(value + "\n")
    else:
        print(value)
