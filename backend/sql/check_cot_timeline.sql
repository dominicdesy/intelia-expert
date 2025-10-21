-- ============================================================================
-- Vérifier la timeline d'activation du CoT
-- ============================================================================

-- 1. Messages AVEC CoT par date
SELECT
    '1. MESSAGES AVEC COT PAR DATE' as section,
    DATE(m.created_at) as date_creation,
    COUNT(*) as nb_messages_avec_cot,
    MIN(m.created_at) as premier_message,
    MAX(m.created_at) as dernier_message
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND (m.cot_thinking IS NOT NULL OR m.cot_analysis IS NOT NULL)
GROUP BY DATE(m.created_at)
ORDER BY date_creation DESC;

-- 2. Messages SANS CoT par date
SELECT
    '2. MESSAGES SANS COT PAR DATE' as section,
    DATE(m.created_at) as date_creation,
    COUNT(*) as nb_messages_sans_cot,
    MIN(m.created_at) as premier_message,
    MAX(m.created_at) as dernier_message
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND m.cot_thinking IS NULL
  AND m.cot_analysis IS NULL
GROUP BY DATE(m.created_at)
ORDER BY date_creation DESC;

-- 3. Tous les messages par date avec ratio CoT
SELECT
    '3. RATIO COT PAR DATE' as section,
    DATE(m.created_at) as date_creation,
    COUNT(*) as total_messages,
    SUM(CASE WHEN m.cot_thinking IS NOT NULL OR m.cot_analysis IS NOT NULL THEN 1 ELSE 0 END) as avec_cot,
    SUM(CASE WHEN m.cot_thinking IS NULL AND m.cot_analysis IS NULL THEN 1 ELSE 0 END) as sans_cot,
    ROUND(100.0 * SUM(CASE WHEN m.cot_thinking IS NOT NULL OR m.cot_analysis IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as pourcentage_cot
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
GROUP BY DATE(m.created_at)
ORDER BY date_creation DESC;
