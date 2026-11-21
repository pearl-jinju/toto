SELECT 'export const roundSnapshot = ' || content::text || ';' AS js
FROM proto_round_snapshot
ORDER BY game_year DESC, game_round DESC
LIMIT 1;
