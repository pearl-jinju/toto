CREATE TABLE IF NOT EXISTS research_snapshot (
    effective_date date PRIMARY KEY,
    content jsonb NOT NULL CHECK (jsonb_typeof(content) = 'object'),
    updated_at timestamptz NOT NULL DEFAULT now()
);
