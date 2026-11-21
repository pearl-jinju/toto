CREATE TABLE IF NOT EXISTS fixture_context_snapshot (
    round_id integer PRIMARY KEY,
    content jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object')
);
