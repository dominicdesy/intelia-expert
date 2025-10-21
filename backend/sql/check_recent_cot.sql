-- Vérifier les messages récents avec CoT
SELECT
    m.id,
    m.role,
    m.has_cot_structure,
    LENGTH(m.cot_thinking) as thinking_length,
    LENGTH(m.cot_analysis) as analysis_length,
    LENGTH(m.content) as answer_length,
    LEFT(m.content, 200) as answer_preview,
    m.created_at
FROM messages m
WHERE m.role = 'assistant'
  AND m.created_at > NOW() - INTERVAL '1 day'
ORDER BY m.created_at DESC
LIMIT 10;

-- Compter les messages avec/sans CoT
SELECT
    has_cot_structure,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM messages
WHERE role = 'assistant'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY has_cot_structure;
