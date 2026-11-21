CREATE TABLE IF NOT EXISTS proto_round_snapshot (
    game_year integer NOT NULL,
    game_round integer NOT NULL,
    captured_at timestamptz NOT NULL,
    content jsonb NOT NULL CHECK (jsonb_typeof(content->'matches') = 'array'),
    PRIMARY KEY (game_year, game_round)
);
