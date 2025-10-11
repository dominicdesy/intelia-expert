-- ============================================================================
-- VÉRIFICATION: Structure de la table conversations
-- ============================================================================
-- Date: 2025-10-11
-- Description: Vérifie le type de données de la colonne id
-- ============================================================================

-- Vérifier le type de la colonne id
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'conversations'
ORDER BY ordinal_position;

-- Vérifier les contraintes
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'conversations'
ORDER BY tc.constraint_type, tc.constraint_name;

-- Compter les conversations existantes
SELECT COUNT(*) as total_conversations FROM conversations;

-- Vérifier les types de données des IDs existants
SELECT
    id,
    session_id,
    user_id,
    LENGTH(id) as id_length,
    LENGTH(session_id) as session_id_length
FROM conversations
LIMIT 5;
