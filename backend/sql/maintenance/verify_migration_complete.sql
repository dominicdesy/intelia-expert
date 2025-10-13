-- ============================================================================
-- VÉRIFICATION COMPLÈTE: Migration conversations + messages
-- ============================================================================
-- Date: 2025-10-11
-- Description: Vérifie que toute la migration a été effectuée correctement
-- ============================================================================

SELECT '========== ÉTAPE 1: TYPES DE DONNÉES ==========' as section;

-- Vérifier les types de colonnes conversations
SELECT
    'conversations.' || column_name as column_name,
    data_type,
    CASE
        WHEN column_name = 'id' AND data_type = 'uuid' THEN '✅'
        WHEN column_name = 'session_id' AND data_type = 'uuid' THEN '✅'
        WHEN column_name = 'id' AND data_type != 'uuid' THEN '❌ ERREUR: doit être uuid'
        WHEN column_name = 'session_id' AND data_type != 'uuid' THEN '❌ ERREUR: doit être uuid'
        ELSE '✅'
    END as status
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'conversations'
  AND column_name IN ('id', 'session_id', 'user_id')
ORDER BY column_name;

SELECT '========== ÉTAPE 2: TABLE MESSAGES ==========' as section;

-- Vérifier si la table messages existe
SELECT
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'messages')
         THEN '✅ Table messages existe'
         ELSE '❌ Table messages MANQUANTE - Exécuter create_messages_table_only.sql'
    END as messages_status;

-- Vérifier les types de colonnes messages (si la table existe)
SELECT
    'messages.' || column_name as column_name,
    data_type,
    CASE
        WHEN column_name = 'id' AND data_type = 'uuid' THEN '✅'
        WHEN column_name = 'conversation_id' AND data_type = 'uuid' THEN '✅'
        WHEN column_name IN ('id', 'conversation_id') AND data_type != 'uuid' THEN '❌ ERREUR'
        ELSE '✅'
    END as status
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'messages'
  AND column_name IN ('id', 'conversation_id', 'role', 'sequence_number')
ORDER BY column_name;

SELECT '========== ÉTAPE 3: FOREIGN KEY ==========' as section;

-- Vérifier la foreign key messages -> conversations
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    CASE
        WHEN tc.constraint_type = 'FOREIGN KEY' THEN '✅ Foreign key existe'
        ELSE '❌'
    END as status
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'messages'
  AND tc.constraint_type = 'FOREIGN KEY'
  AND kcu.column_name = 'conversation_id';

SELECT '========== ÉTAPE 4: INDEX ==========' as section;

-- Vérifier les index sur messages
SELECT
    indexname as index_name,
    CASE
        WHEN indexname LIKE 'idx_messages_%' THEN '✅'
        ELSE '❌'
    END as status
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'messages'
ORDER BY indexname;

SELECT '========== ÉTAPE 5: FONCTIONS ==========' as section;

-- Vérifier les fonctions critiques
SELECT
    routine_name,
    CASE
        WHEN routine_name = 'create_conversation_with_messages' THEN '✅ Fonction create_conversation_with_messages'
        WHEN routine_name = 'add_message_to_conversation' THEN '✅ Fonction add_message_to_conversation'
        WHEN routine_name = 'get_conversation_messages' THEN '✅ Fonction get_conversation_messages'
        WHEN routine_name = 'update_conversation_metadata' THEN '✅ Fonction update_conversation_metadata'
        ELSE routine_name
    END as status
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'create_conversation_with_messages',
    'add_message_to_conversation',
    'get_conversation_messages',
    'update_conversation_metadata'
  )
ORDER BY routine_name;

-- Vérifier les fonctions manquantes
SELECT
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'create_conversation_with_messages')
        THEN '❌ MANQUANT: create_conversation_with_messages'
        ELSE ''
    END as missing_function
UNION ALL
SELECT
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'add_message_to_conversation')
        THEN '❌ MANQUANT: add_message_to_conversation'
        ELSE ''
    END
UNION ALL
SELECT
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'get_conversation_messages')
        THEN '❌ MANQUANT: get_conversation_messages'
        ELSE ''
    END
UNION ALL
SELECT
    CASE
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'update_conversation_metadata')
        THEN '❌ MANQUANT: update_conversation_metadata'
        ELSE ''
    END;

SELECT '========== ÉTAPE 6: TRIGGERS ==========' as section;

-- Vérifier le trigger sur messages
SELECT
    trigger_name,
    event_manipulation,
    CASE
        WHEN trigger_name = 'update_conversation_on_message_insert' THEN '✅ Trigger actif'
        ELSE '❌'
    END as status
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND event_object_table = 'messages'
ORDER BY trigger_name;

-- Vérifier si le trigger manque
SELECT
    CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.triggers
            WHERE trigger_schema = 'public'
              AND trigger_name = 'update_conversation_on_message_insert'
              AND event_object_table = 'messages'
        )
        THEN '❌ MANQUANT: Trigger update_conversation_on_message_insert'
        ELSE ''
    END as missing_trigger;

SELECT '========== ÉTAPE 7: VUE CONVERSATION_STATS ==========' as section;

-- Vérifier la vue
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'conversation_stats')
        THEN '✅ Vue conversation_stats existe'
        ELSE '❌ Vue conversation_stats MANQUANTE'
    END as view_status;

SELECT '========== ÉTAPE 8: DONNÉES ==========' as section;

-- Compter les conversations
SELECT
    'Conversations totales:' as info,
    COUNT(*) as count,
    CASE
        WHEN COUNT(*) > 0 THEN '✅ Données présentes'
        ELSE 'ℹ️  Table vide'
    END as status
FROM conversations;

-- Compter les messages (si la table existe)
SELECT
    'Messages totaux:' as info,
    COALESCE(
        (SELECT COUNT(*) FROM messages),
        0
    ) as count,
    CASE
        WHEN COALESCE((SELECT COUNT(*) FROM messages), 0) > 0 THEN '✅ Données présentes'
        ELSE 'ℹ️  Table vide ou inexistante'
    END as status;

SELECT '========== ÉTAPE 9: TEST FONCTIONNEL ==========' as section;

-- Test rapide de création/suppression
DO $$
DECLARE
    test_conv_id UUID;
    test_session_id UUID := gen_random_uuid();
BEGIN
    -- Vérifier que la fonction existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'create_conversation_with_messages') THEN
        RAISE NOTICE '⚠️  SKIP: Fonction create_conversation_with_messages non disponible';
        RETURN;
    END IF;

    -- Test création
    BEGIN
        SELECT create_conversation_with_messages(
            test_session_id,
            'test_user',
            'Question test',
            'Réponse test',
            'fr',
            'rag',
            0.95,
            1000
        ) INTO test_conv_id;

        IF test_conv_id IS NOT NULL THEN
            RAISE NOTICE '✅ Test création: RÉUSSI (ID: %)', test_conv_id;

            -- Vérifier les messages
            IF (SELECT COUNT(*) FROM messages WHERE conversation_id = test_conv_id) = 2 THEN
                RAISE NOTICE '✅ Test messages: RÉUSSI (2 messages créés)';
            ELSE
                RAISE NOTICE '❌ Test messages: ÉCHOUÉ';
            END IF;

            -- Nettoyage
            DELETE FROM conversations WHERE id = test_conv_id;
            RAISE NOTICE '✅ Nettoyage: Conversation de test supprimée';
        ELSE
            RAISE NOTICE '❌ Test création: ÉCHOUÉ';
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE '❌ Test fonctionnel: ERREUR - %', SQLERRM;
            -- Nettoyage en cas d'erreur
            IF test_conv_id IS NOT NULL THEN
                DELETE FROM conversations WHERE id = test_conv_id;
            END IF;
    END;
END $$;

SELECT '========== RÉSUMÉ FINAL ==========' as section;

-- Résumé de l'état de la migration
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'id' AND data_type = 'uuid')
         AND EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'messages')
         AND EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'create_conversation_with_messages')
         AND EXISTS (SELECT 1 FROM information_schema.triggers WHERE trigger_schema = 'public' AND trigger_name = 'update_conversation_on_message_insert')
        THEN '✅ ✅ ✅ MIGRATION COMPLÈTE ET FONCTIONNELLE ✅ ✅ ✅'
        ELSE '❌ MIGRATION INCOMPLÈTE - Voir les sections ci-dessus'
    END as final_status;

SELECT '========== FIN VÉRIFICATION ==========' as section;
