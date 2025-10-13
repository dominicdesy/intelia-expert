-- Migration: Créer la table conversation_shares pour le partage de conversations
-- Date: 2025-10-12
-- Description: Permet aux utilisateurs de partager leurs conversations via un lien public

CREATE TABLE IF NOT EXISTS conversation_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    created_by UUID NOT NULL,
    share_type VARCHAR(20) NOT NULL DEFAULT 'public' CHECK (share_type IN ('public', 'private')),
    anonymize BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche rapide par token
CREATE INDEX idx_conversation_shares_token ON conversation_shares(share_token);

-- Index pour recherche par conversation_id
CREATE INDEX idx_conversation_shares_conversation ON conversation_shares(conversation_id);

-- Index pour recherche par créateur
CREATE INDEX idx_conversation_shares_creator ON conversation_shares(created_by);

-- Index pour recherche des partages actifs (non expirés)
CREATE INDEX idx_conversation_shares_active ON conversation_shares(expires_at)
WHERE expires_at IS NULL OR expires_at > NOW();

-- Trigger pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_conversation_shares_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_conversation_shares_updated_at
    BEFORE UPDATE ON conversation_shares
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_shares_updated_at();

-- Commentaires
COMMENT ON TABLE conversation_shares IS 'Stocke les informations de partage de conversations';
COMMENT ON COLUMN conversation_shares.share_token IS 'Token unique cryptographique pour accéder au partage';
COMMENT ON COLUMN conversation_shares.share_type IS 'Type de partage: public (accessible sans auth) ou private (auth requise)';
COMMENT ON COLUMN conversation_shares.anonymize IS 'Si true, anonymise les données personnelles de l''utilisateur';
COMMENT ON COLUMN conversation_shares.expires_at IS 'Date d''expiration du partage (NULL = permanent)';
COMMENT ON COLUMN conversation_shares.view_count IS 'Nombre de fois que le partage a été consulté';
