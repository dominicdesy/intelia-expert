-- ============================================================================
-- MIGRATION: Ajout des préférences vocales utilisateur
-- Date: 2025-01-24
-- Description: Ajoute voice_preference et voice_speed pour personnalisation
--              de l'assistant vocal (plans Elite et Intelia uniquement)
-- ============================================================================

-- Ajouter colonnes pour les préférences vocales
ALTER TABLE users
ADD COLUMN IF NOT EXISTS voice_preference VARCHAR(20) DEFAULT 'alloy',
ADD COLUMN IF NOT EXISTS voice_speed DECIMAL(3,2) DEFAULT 1.0;

-- Contraintes de validation
ALTER TABLE users
ADD CONSTRAINT check_voice_preference
    CHECK (voice_preference IN ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer')),
ADD CONSTRAINT check_voice_speed
    CHECK (voice_speed >= 0.25 AND voice_speed <= 4.0);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_users_voice_settings
    ON users(voice_preference, voice_speed)
    WHERE voice_preference IS NOT NULL;

-- Commentaires
COMMENT ON COLUMN users.voice_preference IS 'Voix préférée pour assistant vocal (OpenAI TTS: alloy, echo, fable, onyx, nova, shimmer)';
COMMENT ON COLUMN users.voice_speed IS 'Vitesse de parole (0.25-4.0, recommandé: 0.8-1.5, défaut: 1.0)';

-- Vérification
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
    AND column_name IN ('voice_preference', 'voice_speed')
ORDER BY column_name;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Voice settings columns added to users table';
    RAISE NOTICE '  - voice_preference: VARCHAR(20) DEFAULT ''alloy''';
    RAISE NOTICE '  - voice_speed: DECIMAL(3,2) DEFAULT 1.0';
END $$;
