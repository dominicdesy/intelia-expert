-- Table pour stocker les métadonnées des images médicales
-- Les images physiques sont dans S3, ici on stocke juste les métadonnées

CREATE TABLE IF NOT EXISTS medical_images (
    -- Identifiants
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,  -- ID utilisateur (pas de FK vers Supabase)

    -- Stockage
    s3_key TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    content_type VARCHAR(50) NOT NULL,

    -- Métadonnées
    description TEXT,
    upload_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Analyse (rempli après traitement par LLM)
    analyzed BOOLEAN DEFAULT FALSE,
    analysis_result JSONB,
    analysis_timestamp TIMESTAMP WITH TIME ZONE
);

-- Index pour recherche rapide par utilisateur
CREATE INDEX IF NOT EXISTS idx_medical_images_user_id
ON medical_images(user_id);

-- Index pour tri par date
CREATE INDEX IF NOT EXISTS idx_medical_images_upload_timestamp
ON medical_images(upload_timestamp DESC);

-- Index pour recherche par clé S3
CREATE INDEX IF NOT EXISTS idx_medical_images_s3_key
ON medical_images(s3_key);

-- Commentaires
COMMENT ON TABLE medical_images IS 'Métadonnées des images médicales uploadées (images physiques dans S3)';
COMMENT ON COLUMN medical_images.s3_key IS 'Clé unique de l''image dans le bucket S3';
COMMENT ON COLUMN medical_images.analysis_result IS 'Résultat de l''analyse IA (JSON): diagnostic, confiance, recommandations';
