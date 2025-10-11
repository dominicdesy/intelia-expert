-- ============================================================================
-- PRODUCTION DATABASE MIGRATION SCRIPT
-- ============================================================================
-- Ce script corrige les problèmes identifiés dans les logs de production
-- Date: 2025-10-10
--
-- PROBLÈMES RÉSOLUS:
-- 1. Colonnes manquantes dans la table conversations
-- 2. Vue user_questions_complete
--
-- EXÉCUTER DANS: PostgreSQL (DigitalOcean)
-- ============================================================================

-- ============================================================================
-- ÉTAPE 1: Ajouter les colonnes manquantes à conversations
-- ============================================================================

-- Ajouter response_source si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS response_source TEXT DEFAULT 'rag';

-- Ajouter processing_time_ms si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS processing_time_ms INTEGER;

-- Ajouter response_confidence si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS response_confidence FLOAT DEFAULT 0.85;

-- Ajouter title si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS title TEXT;

-- Ajouter preview si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS preview TEXT;

-- Ajouter last_message_preview si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS last_message_preview TEXT;

-- Ajouter message_count si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 1;

-- Ajouter language si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'fr';

-- Ajouter status si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

-- Ajouter feedback si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS feedback TEXT;

-- Ajouter feedback_comment si elle n'existe pas
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS feedback_comment TEXT;

-- ============================================================================
-- ÉTAPE 2: Créer ou recréer la vue user_questions_complete
-- ============================================================================

-- Supprimer la vue si elle existe
DROP VIEW IF EXISTS user_questions_complete;

-- Créer la vue avec la structure correcte
CREATE VIEW user_questions_complete AS
SELECT
    c.id::text as id,
    c.session_id,
    c.user_id::text as user_email,  -- Note: sera enrichi par Supabase
    c.question,
    c.response as response_text,
    c.response_source,
    c.response_confidence,
    COALESCE(c.processing_time_ms, 1000.0) as processing_time_ms,
    c.sources,
    c.mode,
    c.title,
    c.preview,
    c.last_message_preview,
    c.message_count,
    c.language,
    c.status,
    c.feedback,
    c.feedback_comment,
    c.created_at,
    c.updated_at
FROM conversations c
WHERE c.question IS NOT NULL
  AND c.response IS NOT NULL
  AND c.status = 'active'
ORDER BY c.created_at DESC;

-- ============================================================================
-- ÉTAPE 3: Créer des index pour optimiser les performances
-- ============================================================================

-- Index sur user_id pour les requêtes de top users
CREATE INDEX IF NOT EXISTS idx_conversations_user_id
ON conversations(user_id);

-- Index sur created_at pour les requêtes temporelles
CREATE INDEX IF NOT EXISTS idx_conversations_created_at
ON conversations(created_at);

-- Index sur status pour filtrer les conversations actives
CREATE INDEX IF NOT EXISTS idx_conversations_status
ON conversations(status);

-- Index composite pour les stats rapides
CREATE INDEX IF NOT EXISTS idx_conversations_stats
ON conversations(user_id, created_at, status);

-- ============================================================================
-- ÉTAPE 4: Vérification
-- ============================================================================

-- Compter les conversations
SELECT COUNT(*) as total_conversations FROM conversations;

-- Vérifier les colonnes de la table
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'conversations'
ORDER BY ordinal_position;

-- Tester la vue
SELECT COUNT(*) as total_in_view FROM user_questions_complete;

-- Afficher un échantillon
SELECT id, user_email, question, response_source, created_at
FROM user_questions_complete
LIMIT 5;

-- ============================================================================
-- FIN DU SCRIPT
-- ============================================================================
