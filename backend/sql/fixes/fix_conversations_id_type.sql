-- ============================================================================
-- MIGRATION: Convertir conversations.id de TEXT vers UUID
-- ============================================================================
-- Date: 2025-10-11
-- Description: Corrige le type de la colonne id pour permettre la création
--              de la table messages avec foreign key
-- ============================================================================

-- ⚠️ ATTENTION: Ce script modifie la structure de la table conversations
-- ⚠️ Exécuter d'abord check_conversations_structure.sql pour voir l'état actuel

-- ============================================================================
-- ÉTAPE 1: BACKUP DES DONNÉES EXISTANTES
-- ============================================================================

-- Créer une table de backup (si elle n'existe pas)
CREATE TABLE IF NOT EXISTS conversations_backup_20251011 AS
SELECT * FROM conversations;

SELECT 'Backup créé:' as info, COUNT(*) as rows_backed_up
FROM conversations_backup_20251011;

-- ============================================================================
-- ÉTAPE 2: ANALYSER LES DONNÉES EXISTANTES
-- ============================================================================

-- Vérifier si les IDs actuels sont compatibles avec UUID
DO $$
DECLARE
    v_count_invalid INTEGER;
BEGIN
    -- Compter les IDs qui ne sont pas des UUIDs valides
    SELECT COUNT(*) INTO v_count_invalid
    FROM conversations
    WHERE id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

    IF v_count_invalid > 0 THEN
        RAISE NOTICE '⚠️  ATTENTION: % conversations ont des IDs qui ne sont pas des UUIDs valides', v_count_invalid;
        RAISE NOTICE '⚠️  Ces conversations devront être supprimées ou leurs IDs régénérés';
    ELSE
        RAISE NOTICE '✅ Tous les IDs sont des UUIDs valides - migration possible';
    END IF;
END $$;

-- ============================================================================
-- ÉTAPE 3: MIGRATION DE LA COLONNE ID
-- ============================================================================

DO $$
DECLARE
    v_total_rows INTEGER;
BEGIN
    -- Compter les lignes
    SELECT COUNT(*) INTO v_total_rows FROM conversations;

    IF v_total_rows = 0 THEN
        RAISE NOTICE '✅ Table conversations vide - migration simple';

        -- Si la table est vide, simplement changer le type
        ALTER TABLE conversations ALTER COLUMN id TYPE UUID USING id::UUID;
        ALTER TABLE conversations ALTER COLUMN id SET DEFAULT gen_random_uuid();

        RAISE NOTICE '✅ Colonne id convertie en UUID';
    ELSE
        RAISE NOTICE '⚠️  Table conversations contient % lignes', v_total_rows;
        RAISE NOTICE '⚠️  Migration nécessite conversion des données existantes';

        -- Vérifier que tous les IDs sont des UUIDs valides
        IF EXISTS (
            SELECT 1 FROM conversations
            WHERE id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        ) THEN
            RAISE EXCEPTION '❌ ERREUR: Des IDs ne sont pas des UUIDs valides. Migration impossible.';
        END IF;

        -- Convertir la colonne
        ALTER TABLE conversations ALTER COLUMN id TYPE UUID USING id::UUID;
        ALTER TABLE conversations ALTER COLUMN id SET DEFAULT gen_random_uuid();

        RAISE NOTICE '✅ Colonne id convertie en UUID avec préservation des données';
    END IF;

    -- Convertir session_id si nécessaire
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'conversations'
          AND column_name = 'session_id'
          AND data_type != 'uuid'
    ) THEN
        RAISE NOTICE 'ℹ️  Conversion de session_id en UUID...';
        ALTER TABLE conversations ALTER COLUMN session_id TYPE UUID USING session_id::UUID;
        RAISE NOTICE '✅ session_id converti en UUID';
    END IF;
END $$;

-- ============================================================================
-- ÉTAPE 4: VÉRIFICATION
-- ============================================================================

-- Vérifier que la conversion a réussi
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'conversations'
  AND column_name IN ('id', 'session_id')
ORDER BY column_name;

-- Vérifier que les données sont intactes
SELECT
    'Original:' as source,
    COUNT(*) as count
FROM conversations_backup_20251011
UNION ALL
SELECT
    'Après migration:' as source,
    COUNT(*) as count
FROM conversations;

-- ============================================================================
-- ÉTAPE 5: NETTOYAGE (optionnel)
-- ============================================================================

-- Décommenter cette ligne pour supprimer le backup après vérification
-- DROP TABLE IF EXISTS conversations_backup_20251011;

-- ============================================================================
-- FIN DE LA MIGRATION
-- ============================================================================

SELECT '✅ Migration terminée - Vous pouvez maintenant exécuter create_messages_table_only.sql' as status;
