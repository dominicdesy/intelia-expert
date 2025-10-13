-- ============================================================================
-- SCHEMA COMPLET: Conversations + Messages Architecture
-- ============================================================================
-- Description: Architecture complète pour gérer les conversations multi-tours
--              avec séparation conversations/messages
-- Version: 1.0
-- Date: 2025-10-11
-- ============================================================================

-- Table: conversations
-- Stocke les métadonnées de chaque conversation
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT,
    language TEXT DEFAULT 'fr',
    message_count INTEGER DEFAULT 0,
    first_message_preview TEXT,
    last_message_preview TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche par user_id
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity_at DESC);

-- Table: messages
-- Stocke tous les messages (user + assistant)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    response_source TEXT,
    response_confidence FLOAT,
    processing_time_ms INTEGER,
    feedback TEXT CHECK (feedback IN ('positive', 'negative', 'neutral')),
    feedback_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(conversation_id, sequence_number)
);

-- Index pour recherche par conversation
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_sequence ON messages(conversation_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Fonction: Mettre à jour les métadonnées de conversation après insertion de message
CREATE OR REPLACE FUNCTION update_conversation_metadata()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET
        message_count = (
            SELECT COUNT(*)
            FROM messages
            WHERE conversation_id = NEW.conversation_id
        ),
        last_message_preview = SUBSTRING(NEW.content, 1, 200),
        last_activity_at = NOW(),
        updated_at = NOW()
    WHERE id = NEW.conversation_id;

    -- Mettre à jour first_message_preview si c'est le premier message
    UPDATE conversations
    SET first_message_preview = SUBSTRING(NEW.content, 1, 200)
    WHERE id = NEW.conversation_id
      AND first_message_preview IS NULL;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Mise à jour automatique après insertion de message
DROP TRIGGER IF EXISTS update_conversation_on_message_insert ON messages;
CREATE TRIGGER update_conversation_on_message_insert
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_metadata();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Fonction: Créer une conversation avec les deux premiers messages (Q&R)
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

-- Fonction: Ajouter un message à une conversation existante
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

-- ============================================================================
-- VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW conversation_stats AS
SELECT
    user_id,
    COUNT(*) as total_conversations,
    SUM(message_count) as total_messages,
    MAX(last_activity_at) as last_activity
FROM conversations
WHERE status = 'active'
GROUP BY user_id;

-- Vue détaillée avec info du premier et dernier message
CREATE OR REPLACE VIEW conversation_details AS
SELECT
    c.id,
    c.session_id,
    c.user_id,
    c.title,
    c.language,
    c.message_count,
    c.first_message_preview,
    c.last_message_preview,
    c.status,
    c.created_at,
    c.updated_at,
    c.last_activity_at,
    -- Premier message complet
    (SELECT content FROM messages WHERE conversation_id = c.id AND sequence_number = 1) as first_user_message,
    -- Dernière réponse complète
    (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY sequence_number DESC LIMIT 1) as last_message
FROM conversations c;

-- ============================================================================
-- EXEMPLE D'UTILISATION
-- ============================================================================

/*
-- 1. Créer une conversation avec le premier échange
SELECT create_conversation_with_messages(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::uuid,  -- session_id
    'user_123',                                      -- user_id
    'Comment fonctionne le système RAG ?',          -- question
    'Le système RAG utilise...',                    -- réponse
    'fr',                                            -- langue
    'rag',                                           -- source
    0.92,                                            -- confiance
    1250                                             -- temps de traitement
);

-- 2. Ajouter un message à une conversation existante
SELECT add_message_to_conversation(
    'conversation_uuid',
    'user',
    'Merci, et pour l''optimisation ?'
);

-- 3. Récupérer tous les messages d'une conversation
SELECT * FROM get_conversation_messages('conversation_uuid');

-- 4. Récupérer toutes les conversations d'un utilisateur
SELECT * FROM conversations
WHERE user_id = 'user_123' AND status = 'active'
ORDER BY last_activity_at DESC
LIMIT 20;

-- 5. Statistiques par utilisateur
SELECT * FROM conversation_stats WHERE user_id = 'user_123';
*/
