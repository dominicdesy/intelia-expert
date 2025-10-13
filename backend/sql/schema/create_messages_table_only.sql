-- ============================================================================
-- CRÉATION: Table messages uniquement (DigitalOcean PostgreSQL)
-- ============================================================================
-- Date: 2025-10-11
-- Description: Crée UNIQUEMENT la table messages et ses dépendances
--              Sans toucher à la table conversations existante
-- ============================================================================

-- ÉTAPE 1: Créer la table messages
-- ============================================================================

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

-- ÉTAPE 2: Créer les triggers
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

-- ÉTAPE 3: Créer les fonctions helpers
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

-- ÉTAPE 4: Créer la vue conversation_stats
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

-- ============================================================================
-- VÉRIFICATION
-- ============================================================================

-- Vérifier que tout a été créé
SELECT
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'messages')
         THEN '✅ Table messages créée'
         ELSE '❌ ERREUR: Table messages non créée'
    END as messages_status;

SELECT
    CASE WHEN EXISTS (SELECT FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'create_conversation_with_messages')
         THEN '✅ Fonction create_conversation_with_messages créée'
         ELSE '❌ ERREUR: Fonction non créée'
    END as function_status;

-- Afficher la structure de la table messages
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'messages'
ORDER BY ordinal_position;
