-- ============================================================================
-- SCHÉMA POSTGRESQL (DigitalOcean) - Données applicatives
-- ============================================================================
-- Base de données: PostgreSQL principale pour conversations, feedback, invitations
-- Date: 2025-10-11
-- ============================================================================

-- ============================================================================
-- TABLE: conversations
-- Stocke toutes les questions/réponses de tous les utilisateurs
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    -- Identifiants
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,  -- Référence à Supabase auth.users.id

    -- Contenu
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    mode TEXT DEFAULT 'broiler',  -- broiler, layer, general

    -- Métadonnées de la réponse
    sources JSONB DEFAULT '[]'::jsonb,
    response_source TEXT DEFAULT 'rag',  -- rag, openai_fallback, table_lookup
    response_confidence FLOAT DEFAULT 0.85,
    processing_time_ms INTEGER,

    -- Informations conversation
    title TEXT,
    preview TEXT,
    last_message_preview TEXT,
    message_count INTEGER DEFAULT 1,

    -- Localisation
    language TEXT DEFAULT 'fr',

    -- Statut et feedback
    status TEXT DEFAULT 'active',  -- active, deleted, archived
    feedback TEXT,  -- '1' (positif), '-1' (négatif), NULL
    feedback_comment TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations(user_id, status, created_at DESC);

-- ============================================================================
-- TABLE: feedback
-- Stocke le feedback utilisateur détaillé
-- ============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,

    -- Feedback
    rating INTEGER CHECK (rating IN (-1, 1)),  -- -1 = négatif, 1 = positif
    comment TEXT,
    feedback_type TEXT,  -- quality, accuracy, speed, relevance

    -- Métadonnées
    user_agent TEXT,
    ip_address INET,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_conversation_id ON feedback(conversation_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);

-- ============================================================================
-- TABLE: invitations
-- Système d'invitations utilisateur
-- ============================================================================
CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Inviteur
    inviter_email TEXT NOT NULL,
    inviter_name TEXT,
    inviter_user_id UUID,  -- NULL si pas encore inscrit

    -- Invité
    invited_email TEXT NOT NULL,
    invited_name TEXT,

    -- Statut
    status TEXT DEFAULT 'pending',  -- pending, accepted, expired, cancelled
    token TEXT UNIQUE,

    -- Métadonnées
    invitation_code TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    accepted_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_inviter_email ON invitations(inviter_email);
CREATE INDEX IF NOT EXISTS idx_invitations_invited_email ON invitations(invited_email);
CREATE INDEX IF NOT EXISTS idx_invitations_status ON invitations(status);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);

-- ============================================================================
-- VUE: user_questions_complete
-- Vue consolidée pour analytics et dashboard
-- ============================================================================
DROP VIEW IF EXISTS user_questions_complete;

CREATE VIEW user_questions_complete AS
SELECT
    -- IDs
    c.id::text as id,
    c.session_id,
    c.user_id::text as user_email,  -- Note: contient user_id, pas email
    c.id::text as question_id,

    -- Contenu
    c.question,
    c.response as response_text,

    -- Métadonnées réponse
    c.response_source,
    c.response_confidence,
    0.0 as completeness_score,
    COALESCE(c.processing_time_ms, 1000.0) as processing_time_ms,

    -- Localisation et intent
    COALESCE(c.language, 'fr') as language,
    'question_answer' as intent,

    -- Feedback
    c.feedback,
    c.feedback_comment,

    -- Métadonnées JSON
    '{}'::jsonb as entities,

    -- Erreurs
    NULL::text as error_type,
    NULL::text as error_message,
    NULL::text as error_traceback,

    -- Stats
    LENGTH(c.response) / 1024 as data_size_kb,
    COALESCE(c.status, 'success') as status,

    -- Timestamps
    c.created_at,
    c.updated_at

FROM conversations c
WHERE c.question IS NOT NULL
  AND c.response IS NOT NULL
  AND c.status = 'active';

-- Index sur la vue (via table sous-jacente déjà indexée)

-- ============================================================================
-- TRIGGER: update_updated_at
-- Met à jour automatiquement updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invitations_updated_at
    BEFORE UPDATE ON invitations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FONCTION: get_user_conversation_count
-- Compte les conversations d'un utilisateur
-- ============================================================================
CREATE OR REPLACE FUNCTION get_user_conversation_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM conversations
        WHERE user_id = p_user_id
        AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VÉRIFICATIONS
-- ============================================================================

-- Vérifier les tables créées
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('conversations', 'feedback', 'invitations')
ORDER BY table_name;

-- Vérifier les index
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('conversations', 'feedback', 'invitations')
ORDER BY tablename, indexname;

-- Vérifier la vue
SELECT COUNT(*) as total_in_view FROM user_questions_complete;

-- ============================================================================
-- NOTES D'UTILISATION
-- ============================================================================

/*
CONNEXION:
----------
Cette base de données PostgreSQL (DigitalOcean) est accessible via:
- Variable d'env: DATABASE_URL
- Format: postgresql://user:password@host:port/database

SÉPARATION DES RESPONSABILITÉS:
-------------------------------
PostgreSQL (ici):
  ✅ conversations - Historique complet Q&R
  ✅ feedback - Retours utilisateurs
  ✅ invitations - Système d'invitation
  ✅ user_questions_complete - Vue analytics

Supabase (autre DB):
  ✅ auth.users - Authentification
  ✅ public.users - Profils utilisateurs

ACCÈS UTILISATEUR:
-----------------
L'utilisateur peut accéder à ses conversations via:
  SELECT * FROM conversations WHERE user_id = '<user_uuid>' AND status = 'active';

ANALYTICS:
----------
Les statistiques utilisent la vue user_questions_complete:
  SELECT * FROM user_questions_complete WHERE created_at >= NOW() - INTERVAL '30 days';

BACKUP:
-------
Penser à configurer des backups automatiques sur DigitalOcean.
*/
