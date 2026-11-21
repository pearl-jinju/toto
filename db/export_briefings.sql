SELECT 'export const snapshot = ' || to_json(label)::text || ';' || chr(10)
    || 'export const sources = ' || jsonb_pretty(sources) || ';' || chr(10)
    || 'export const games = ' || jsonb_pretty(matches) || ';' AS js
FROM briefing_snapshot
ORDER BY effective_date DESC
LIMIT 1;
