-- ============================================================================
-- Vérifier les messages d'aujourd'hui (21 octobre)
-- ============================================================================

-- 1. Messages d'aujourd'hui avec leur contenu
SELECT
    '1. MESSAGES DU 21 OCTOBRE' as section,
    m.id,
    c.id as conversation_id,
    m.created_at,
    LEFT(m.content, 200) as content_preview,
    CASE WHEN m.content LIKE '%<thinking>%' THEN 'OUI' ELSE 'NON' END as a_balise_thinking_dans_content,
    CASE WHEN m.content LIKE '%<analysis>%' THEN 'OUI' ELSE 'NON' END as a_balise_analysis_dans_content,
    CASE WHEN m.content LIKE '%<answer>%' THEN 'OUI' ELSE 'NON' END as a_balise_answer_dans_content,
    CASE WHEN m.cot_thinking IS NOT NULL THEN 'OUI' ELSE 'NON' END as a_cot_thinking_colonne,
    CASE WHEN m.cot_analysis IS NOT NULL THEN 'OUI' ELSE 'NON' END as a_cot_analysis_colonne
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND DATE(m.created_at) = '2025-10-21'
ORDER BY m.created_at DESC;

-- 2. Voir le contenu COMPLET d'un message récent
SELECT
    '2. CONTENU COMPLET MESSAGE RECENT' as section,
    m.id,
    m.created_at,
    m.content as contenu_complet,
    m.cot_thinking,
    m.cot_analysis
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.role = 'assistant'
  AND c.status = 'active'
  AND DATE(m.created_at) = '2025-10-21'
ORDER BY m.created_at DESC
LIMIT 1;
