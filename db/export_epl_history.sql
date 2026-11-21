WITH teams AS (
    SELECT team, row_number() OVER (ORDER BY team) - 1 AS id
    FROM (
        SELECT home_team AS team FROM historical_football_match WHERE league_code = 'EPL'
        UNION
        SELECT away_team FROM historical_football_match WHERE league_code = 'EPL'
    ) names
), scores AS (
    SELECT m.match_date, m.season, h.id AS home_id, a.id AS away_id,
        concat_ws(',', m.match_date, h.id, a.id, coalesce(m.ht_home::text, ''),
            coalesce(m.ht_away::text, ''), m.ft_home, m.ft_away) AS fixture
    FROM historical_football_match m
    JOIN teams h ON h.team = m.home_team
    JOIN teams a ON a.team = m.away_team
    WHERE m.league_code = 'EPL'
)
SELECT 'export const eplHistory = ' || jsonb_build_object(
    'teams', (SELECT jsonb_agg(team ORDER BY id) FROM teams),
    'scores', string_agg(fixture, ';' ORDER BY match_date DESC, home_id, away_id),
    'first', min(match_date),
    'last', max(match_date),
    'count', count(*),
    'currentSeason', max(season),
    'sources', (SELECT jsonb_agg(source_url ORDER BY season DESC) FROM historical_football_season WHERE league_code = 'EPL')
)::text || ';' AS js
FROM scores;
