-- ============================================================================
-- FIX: Créer la fonction get_conversation_messages manquante
-- ============================================================================
-- Date: 2025-10-15
-- Problème: function get_conversation_messages(uuid) does not exist
-- Solution: Créer la fonction SQL pour récupérer les messages d'une conversation
-- ============================================================================

-- Fonction: Récupérer tous les messages d'une conversation
CREATE OR REPLACE FUNCTION get_conversation_messages(p_conversation_id UUID)
RETURNS TABLE (
    id UUID,
    role TEXT,
    content TEXT,
    sequence_number INTEGER,
    response_source TEXT,
    response_confidence FLOAT,
    processing_time_ms INTEGER,
    feedback TEXT,
    feedback_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.role,
        m.content,
        m.sequence_number,
        m.response_source,
        m.response_confidence,
        m.processing_time_ms,
        m.feedback,
        m.feedback_comment,
        m.created_at
    FROM messages m
    WHERE m.conversation_id = p_conversation_id
    ORDER BY m.sequence_number ASC;
END;
$$ LANGUAGE plpgsql;

-- Vérifier que la fonction a bien été créée
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_name = 'get_conversation_messages';

-- Test rapide (remplacer par un vrai conversation_id)
-- SELECT * FROM get_conversation_messages('90e16ae1-eb95-44cf-942d-1e993fcafafe'::uuid);
