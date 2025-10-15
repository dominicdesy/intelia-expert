-- ============================================================================
-- FIX: Créer TOUTES les fonctions SQL manquantes pour conversations + messages
-- ============================================================================
-- Date: 2025-10-15
-- Problème: Plusieurs fonctions SQL manquantes dans PostgreSQL
-- Solution: Créer toutes les fonctions helper nécessaires
-- ============================================================================

-- Fonction 1: Créer une conversation avec les deux premiers messages (Q&R)
CREATE OR REPLACE FUNCTION create_conversation_with_messages(
    p_session_id UUID,
    p_user_id TEXT,
    p_user_message TEXT,
    p_assistant_response TEXT,
    p_language TEXT DEFAULT 'fr',
    p_response_source TEXT DEFAULT 'rag',
    p_response_confidence FLOAT DEFAULT 0.85,
    p_processing_time_ms INTEGER DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    -- Créer la conversation
    INSERT INTO conversations (session_id, user_id, language)
    VALUES (p_session_id, p_user_id, p_language)
    RETURNING id INTO v_conversation_id;

    -- Ajouter le message user (sequence 1)
    INSERT INTO messages (
        conversation_id,
        role,
        content,
        sequence_number
    ) VALUES (
        v_conversation_id,
        'user',
        p_user_message,
        1
    );

    -- Ajouter la réponse assistant (sequence 2)
    INSERT INTO messages (
        conversation_id,
        role,
        content,
        sequence_number,
        response_source,
        response_confidence,
        processing_time_ms
    ) VALUES (
        v_conversation_id,
        'assistant',
        p_assistant_response,
        2,
        p_response_source,
        p_response_confidence,
        p_processing_time_ms
    );

    RETURN v_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction 2: Ajouter un message à une conversation existante
CREATE OR REPLACE FUNCTION add_message_to_conversation(
    p_conversation_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_response_source TEXT DEFAULT NULL,
    p_response_confidence FLOAT DEFAULT NULL,
    p_processing_time_ms INTEGER DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_message_id UUID;
    v_next_sequence INTEGER;
BEGIN
    -- Calculer le prochain sequence_number
    SELECT COALESCE(MAX(sequence_number), 0) + 1
    INTO v_next_sequence
    FROM messages
    WHERE conversation_id = p_conversation_id;

    -- Insérer le message
    INSERT INTO messages (
        conversation_id,
        role,
        content,
        sequence_number,
        response_source,
        response_confidence,
        processing_time_ms
    ) VALUES (
        p_conversation_id,
        p_role,
        p_content,
        v_next_sequence,
        p_response_source,
        p_response_confidence,
        p_processing_time_ms
    )
    RETURNING id INTO v_message_id;

    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction 3: Récupérer tous les messages d'une conversation
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

-- Vérifier que toutes les fonctions ont bien été créées
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_name IN (
    'create_conversation_with_messages',
    'add_message_to_conversation',
    'get_conversation_messages'
)
ORDER BY routine_name;
