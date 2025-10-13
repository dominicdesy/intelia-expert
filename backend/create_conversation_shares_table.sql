-- ============================================================================
-- Table: conversation_shares
-- Pour gérer le partage de conversations via des liens
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversation_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    share_token TEXT UNIQUE NOT NULL,
    created_by TEXT NOT NULL,  -- user_id de celui qui crée le partage
    share_type TEXT DEFAULT 'public' CHECK (share_type IN ('public', 'private')),
    anonymize BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche rapide par conversation
CREATE INDEX IF NOT EXISTS idx_conversation_shares_conversation_id
ON conversation_shares(conversation_id);

-- Index pour recherche par token (utilisé pour accéder au partage)
CREATE INDEX IF NOT EXISTS idx_conversation_shares_token
ON conversation_shares(share_token);

-- Index pour recherche par créateur
CREATE INDEX IF NOT EXISTS idx_conversation_shares_created_by
ON conversation_shares(created_by);

-- Index pour nettoyer les partages expirés
CREATE INDEX IF NOT EXISTS idx_conversation_shares_expires_at
ON conversation_shares(expires_at)
WHERE expires_at IS NOT NULL;

-- Afficher le résultat
DO $$
BEGIN
    RAISE NOTICE '✅ Table conversation_shares créée avec succès!';
    RAISE NOTICE '   - Colonne id (UUID, primary key)';
    RAISE NOTICE '   - Colonne conversation_id (référence vers conversations)';
    RAISE NOTICE '   - Colonne share_token (token unique pour accès)';
    RAISE NOTICE '   - Colonne created_by (user_id du créateur)';
    RAISE NOTICE '   - Colonne share_type (public/private)';
    RAISE NOTICE '   - Colonne anonymize (masquer données personnelles)';
    RAISE NOTICE '   - Colonne expires_at (date expiration optionnelle)';
    RAISE NOTICE '   - Colonne view_count (nombre de consultations)';
    RAISE NOTICE '';
    RAISE NOTICE '📌 Vous pouvez maintenant partager des conversations!';
END $$;

-- Vérification
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename = 'conversation_shares';
