SELECT 'export const research = ' || jsonb_pretty(content) || ';' AS js
FROM research_snapshot
ORDER BY effective_date DESC
LIMIT 1;
