-- ============================================================================
-- Migration: Add media_url field to messages table
-- ============================================================================
-- Description: Ajoute un champ pour stocker les URLs des médias (audio, images)
--              dans les messages WhatsApp
-- Date: 2025-10-24
-- ============================================================================

-- Ajouter le champ media_url à la table messages
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS media_url TEXT;

-- Ajouter un champ pour le type de média
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS media_type TEXT CHECK (media_type IN ('audio', 'image', 'video', 'document'));

-- Créer un index pour rechercher les messages avec médias
CREATE INDEX IF NOT EXISTS idx_messages_media_url ON messages(media_url) WHERE media_url IS NOT NULL;

-- Commentaires
COMMENT ON COLUMN messages.media_url IS 'URL du média attaché au message (audio, image, etc.). Pour WhatsApp, contient l''URL Twilio du média.';
COMMENT ON COLUMN messages.media_type IS 'Type de média: audio, image, video, document';
