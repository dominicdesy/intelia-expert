-- ============================================================================
-- Vérifier le contenu réel des champs CoT dans les messages
-- ============================================================================

-- 1. Voir les messages avec cot_thinking (contenu complet)
SELECT
    '1. MESSAGES AVEC COT_THINKING' as section,
    m.id,
    c.id as conversation_id,
    LEFT(m.content, 100) as content_preview,
    m.cot_thinking,
    LENGTH(m.cot_thinking) as thinking_length,
    m.created_at
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND m.cot_thinking IS NOT NULL
ORDER BY m.created_at DESC
LIMIT 3;

-- 2. Voir les messages avec cot_analysis (contenu complet)
SELECT
    '2. MESSAGES AVEC COT_ANALYSIS' as section,
    m.id,
    c.id as conversation_id,
    LEFT(m.content, 100) as content_preview,
    m.cot_analysis,
    LENGTH(m.cot_analysis) as analysis_length,
    m.created_at
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND m.cot_analysis IS NOT NULL
ORDER BY m.created_at DESC
LIMIT 3;

-- 3. Vérifier si le content contient encore les balises <thinking>
SELECT
    '3. CONTENT AVEC BALISES <thinking>' as section,
    m.id,
    c.id as conversation_id,
    m.content,
    m.cot_thinking,
    m.cot_analysis
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND m.content LIKE '%<thinking>%'
ORDER BY m.created_at DESC
LIMIT 2;

-- 4. Statistiques détaillées
SELECT
    '4. STATISTIQUES DÉTAILLÉES' as section,
    COUNT(*) as total_assistant_messages,
    SUM(CASE WHEN cot_thinking IS NOT NULL AND cot_thinking != '' THEN 1 ELSE 0 END) as avec_thinking_non_vide,
    SUM(CASE WHEN cot_analysis IS NOT NULL AND cot_analysis != '' THEN 1 ELSE 0 END) as avec_analysis_non_vide,
    SUM(CASE WHEN content LIKE '%<thinking>%' THEN 1 ELSE 0 END) as content_avec_balises_thinking,
    SUM(CASE WHEN content LIKE '%<analysis>%' THEN 1 ELSE 0 END) as content_avec_balises_analysis
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active';
