CREATE SCHEMA IF NOT EXISTS match_context;

CREATE TABLE IF NOT EXISTS match_context.live_match_context_round (
    round_id integer PRIMARY KEY,
    collected_at timestamptz NOT NULL,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object')
);

CREATE TABLE IF NOT EXISTS match_context.live_external_match (
    provider text NOT NULL,
    league text NOT NULL,
    provider_event_id text NOT NULL,
    kickoff timestamptz NOT NULL,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    PRIMARY KEY (provider, league, provider_event_id)
);

CREATE INDEX IF NOT EXISTS live_external_match_league_kickoff_idx
    ON match_context.live_external_match (league, kickoff DESC);
