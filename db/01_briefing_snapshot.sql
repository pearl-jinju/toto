CREATE TABLE IF NOT EXISTS briefing_snapshot (
    effective_date date PRIMARY KEY,
    label text NOT NULL,
    sources jsonb NOT NULL CHECK (jsonb_typeof(sources) = 'object'),
    matches jsonb NOT NULL CHECK (jsonb_typeof(matches) = 'array'),
    updated_at timestamptz NOT NULL DEFAULT now()
);
