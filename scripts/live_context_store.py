import json
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class NeonStore:
    def __init__(self, connection):
        settings = urlsplit(connection)
        if settings.scheme not in {"postgresql", "postgres"} or not (settings.hostname or "").endswith(".neon.tech"):
            raise ValueError("Expected a Neon Postgres connection")
        self.connection = connection
        self.endpoint = "https://" + settings.hostname + "/sql"

    def query(self, statement, params):
        request = Request(
            self.endpoint,
            data=json.dumps({"query": statement, "params": params}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Neon-Connection-String": self.connection,
                "Neon-Raw-Text-Output": "true",
                "Neon-Array-Mode": "true",
                "User-Agent": "MatchIndex/1.0",
            },
            method="POST",
        )
        with urlopen(request, timeout=14) as response:
            return json.load(response)["rows"]

    def get(self, round_id):
        rows = self.query(
            "SELECT payload::text FROM match_context.live_match_context_round WHERE round_id = $1::integer", [str(round_id)]
        )
        return json.loads(rows[0][0]) if rows else None

    def save(self, round_id, packet):
        self.query(
            """INSERT INTO match_context.live_match_context_round (round_id, collected_at, payload)
               VALUES ($1::integer, $2::timestamptz, $3::jsonb)
               ON CONFLICT (round_id) DO UPDATE SET collected_at = EXCLUDED.collected_at, payload = EXCLUDED.payload
               WHERE live_match_context_round.collected_at <= EXCLUDED.collected_at""",
            [str(round_id), packet["updatedAt"], json.dumps(packet, ensure_ascii=False, separators=(",", ":"))],
        )

    def archive(self, events):
        for offset in range(0, len(events), 350):
            batch = events[offset:offset + 350]
            self.query(
                """INSERT INTO match_context.live_external_match (provider, league, provider_event_id, kickoff, payload)
                   SELECT item->>'provider', item->>'league', item->>'id', (item->>'start')::timestamptz, item
                   FROM jsonb_array_elements($1::jsonb) AS item
                   ON CONFLICT (provider, league, provider_event_id) DO UPDATE
                   SET kickoff = EXCLUDED.kickoff, payload = EXCLUDED.payload
                   WHERE live_external_match.kickoff IS DISTINCT FROM EXCLUDED.kickoff
                      OR live_external_match.payload IS DISTINCT FROM EXCLUDED.payload""",
                [json.dumps(batch, ensure_ascii=False, separators=(",", ":"))],
            )

    def history(self, leagues, before):
        rows = self.query(
            """SELECT payload::text FROM match_context.live_external_match
               WHERE league IN (SELECT jsonb_array_elements_text($1::jsonb))
                 AND kickoff >= ($2::timestamptz - interval '760 days')
                 AND kickoff <= ($2::timestamptz + interval '30 days')
               ORDER BY kickoff DESC LIMIT 18000""",
            [json.dumps(sorted(leagues), ensure_ascii=False), before],
        )
        return [json.loads(row[0]) for row in rows]
