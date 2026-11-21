CREATE TABLE IF NOT EXISTS historical_football_season (
    league_code text NOT NULL,
    season text NOT NULL CHECK (season ~ '^[0-9]{4}-[0-9]{2}$'),
    source_url text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[a-f0-9]{64}$'),
    imported_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (league_code, season)
);

CREATE TABLE IF NOT EXISTS historical_football_match (
    league_code text NOT NULL,
    season text NOT NULL,
    match_date date NOT NULL,
    home_team text NOT NULL,
    away_team text NOT NULL,
    ht_home smallint,
    ht_away smallint,
    ft_home smallint NOT NULL CHECK (ft_home >= 0),
    ft_away smallint NOT NULL CHECK (ft_away >= 0),
    PRIMARY KEY (league_code, season, home_team, away_team),
    FOREIGN KEY (league_code, season) REFERENCES historical_football_season (league_code, season),
    CHECK (home_team <> away_team),
    CHECK ((ht_home IS NULL) = (ht_away IS NULL)),
    CHECK (ht_home BETWEEN 0 AND ft_home),
    CHECK (ht_away BETWEEN 0 AND ft_away)
);
