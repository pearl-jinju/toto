SELECT 'export const fixtureContext = ' || content::text || ';' AS js
FROM fixture_context_snapshot
ORDER BY round_id DESC
LIMIT 1;
