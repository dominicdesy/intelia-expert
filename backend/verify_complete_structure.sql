-- ============================================================================
-- VÉRIFICATION COMPLÈTE: Structure DigitalOcean PostgreSQL
-- ============================================================================
-- Date: 2025-10-11
-- Description: Vérifie que toute l'architecture est correctement en place
-- ============================================================================

-- ============================================================================
-- PARTIE 1: TABLES
-- ============================================================================

SELECT '========== TABLES ==========' as section;

-- Lister toutes les tables
SELECT tablename as table_name
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- ============================================================================
-- PARTIE 2: STRUCTURE TABLE CONVERSATIONS
-- ============================================================================

SELECT '========== TABLE: conversations ==========' as section;

-- Vérifier que la table existe
SELECT
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'conversations')
         THEN '✅ conversations existe'
         ELSE '❌ conversations MANQUANTE'
    END as status;

-- Colonnes de conversations
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

-- Compter les conversations
SELECT 'Total conversations:' as info, COUNT(*) as count FROM conversations;

-- ============================================================================
-- PARTIE 3: STRUCTURE TABLE MESSAGES
-- ============================================================================

SELECT '========== TABLE: messages ==========' as section;

-- Vérifier que la table existe
SELECT
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'messages')
         THEN '✅ messages existe'
         ELSE '❌ messages MANQUANTE'
    END as status;

-- Colonnes de messages
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'messages'
ORDER BY ordinal_position;

-- Compter les messages
SELECT 'Total messages:' as info, COUNT(*) as count FROM messages;

-- ============================================================================
-- PARTIE 4: INDEX
-- ============================================================================

SELECT '========== INDEX ==========' as section;

-- Index sur conversations
SELECT
    indexname as index_name,
    indexdef as definition
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'conversations'
ORDER BY indexname;

-- Index sur messages
SELECT
    indexname as index_name,
    indexdef as definition
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'messages'
ORDER BY indexname;

-- ============================================================================
-- PARTIE 5: CONTRAINTES
-- ============================================================================

SELECT '========== CONTRAINTES ==========' as section;

-- Contraintes sur conversations
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    cc.check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
LEFT JOIN information_schema.check_constraints cc
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'conversations'
ORDER BY tc.constraint_type, tc.constraint_name;

-- Contraintes sur messages
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    cc.check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
LEFT JOIN information_schema.check_constraints cc
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'messages'
ORDER BY tc.constraint_type, tc.constraint_name;

-- ============================================================================
-- PARTIE 6: FONCTIONS
-- ============================================================================

SELECT '========== FONCTIONS ==========' as section;

-- Lister toutes les fonctions
SELECT
    routine_name,
    routine_type,
    data_type as return_type
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;

-- Vérifier les fonctions critiques
SELECT
    CASE WHEN EXISTS (SELECT FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'create_conversation_with_messages')
         THEN '✅ create_conversation_with_messages'
         ELSE '❌ create_conversation_with_messages MANQUANTE'
    END as function1,
    CASE WHEN EXISTS (SELECT FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'add_message_to_conversation')
         THEN '✅ add_message_to_conversation'
         ELSE '❌ add_message_to_conversation MANQUANTE'
    END as function2,
    CASE WHEN EXISTS (SELECT FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'get_conversation_messages')
         THEN '✅ get_conversation_messages'
         ELSE '❌ get_conversation_messages MANQUANTE'
    END as function3,
    CASE WHEN EXISTS (SELECT FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'update_conversation_metadata')
         THEN '✅ update_conversation_metadata'
         ELSE '❌ update_conversation_metadata MANQUANTE'
    END as function4;

-- ============================================================================
-- PARTIE 7: TRIGGERS
-- ============================================================================

SELECT '========== TRIGGERS ==========' as section;

-- Lister les triggers
SELECT
    trigger_name,
    event_manipulation as event,
    event_object_table as table_name,
    action_timing as timing,
    action_statement as action
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- Vérifier le trigger critique
SELECT
    CASE WHEN EXISTS (
        SELECT FROM information_schema.triggers
        WHERE trigger_schema = 'public'
          AND trigger_name = 'update_conversation_on_message_insert'
          AND event_object_table = 'messages'
    )
         THEN '✅ Trigger update_conversation_on_message_insert actif'
         ELSE '❌ Trigger update_conversation_on_message_insert MANQUANT'
    END as trigger_status;

-- ============================================================================
-- PARTIE 8: VUES
-- ============================================================================

SELECT '========== VUES ==========' as section;

-- Lister les vues
SELECT
    table_name as view_name
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;

-- Vérifier la vue critique
SELECT
    CASE WHEN EXISTS (SELECT FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'conversation_stats')
         THEN '✅ Vue conversation_stats existe'
         ELSE '❌ Vue conversation_stats MANQUANTE'
    END as view_status;

-- ============================================================================
-- PARTIE 9: TEST FONCTIONNEL
-- ============================================================================

SELECT '========== TEST FONCTIONNEL ==========' as section;

-- Test 1: Créer une conversation de test
DO $$
DECLARE
    test_session_id UUID := gen_random_uuid();
    test_conv_id UUID;
    test_message_id UUID;
    messages_count INTEGER;
BEGIN
    RAISE NOTICE '--- Début du test fonctionnel ---';

    -- Test création conversation
    BEGIN
        SELECT create_conversation_with_messages(
            test_session_id,
            'test_user_verification',
            'Question de test',
            'Réponse de test',
            'fr',
            'rag',
            0.95,
            1500
        ) INTO test_conv_id;

        IF test_conv_id IS NOT NULL THEN
            RAISE NOTICE '✅ Test 1 RÉUSSI: Conversation créée (ID: %)', test_conv_id;
        ELSE
            RAISE EXCEPTION '❌ Test 1 ÉCHOUÉ: create_conversation_with_messages retourne NULL';
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION '❌ Test 1 ÉCHOUÉ: Erreur lors de la création - %', SQLERRM;
    END;

    -- Test ajout message
    BEGIN
        SELECT add_message_to_conversation(
            test_conv_id,
            'user',
            'Question de suivi',
            'rag',
            0.90,
            800
        ) INTO test_message_id;

        IF test_message_id IS NOT NULL THEN
            RAISE NOTICE '✅ Test 2 RÉUSSI: Message ajouté (ID: %)', test_message_id;
        ELSE
            RAISE EXCEPTION '❌ Test 2 ÉCHOUÉ: add_message_to_conversation retourne NULL';
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION '❌ Test 2 ÉCHOUÉ: Erreur lors de l''ajout - %', SQLERRM;
    END;

    -- Test récupération messages
    BEGIN
        SELECT COUNT(*) INTO messages_count
        FROM get_conversation_messages(test_conv_id);

        IF messages_count = 3 THEN -- 2 initiaux + 1 ajouté
            RAISE NOTICE '✅ Test 3 RÉUSSI: get_conversation_messages retourne % messages', messages_count;
        ELSE
            RAISE EXCEPTION '❌ Test 3 ÉCHOUÉ: Attendu 3 messages, reçu %', messages_count;
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION '❌ Test 3 ÉCHOUÉ: Erreur lors de la récupération - %', SQLERRM;
    END;

    -- Nettoyage
    DELETE FROM conversations WHERE id = test_conv_id;
    RAISE NOTICE '✅ Nettoyage: Conversation de test supprimée';

    RAISE NOTICE '--- Fin du test fonctionnel - TOUS LES TESTS RÉUSSIS ---';

EXCEPTION
    WHEN OTHERS THEN
        -- Nettoyage en cas d'erreur
        IF test_conv_id IS NOT NULL THEN
            DELETE FROM conversations WHERE id = test_conv_id;
        END IF;
        RAISE EXCEPTION 'ÉCHEC DU TEST FONCTIONNEL: %', SQLERRM;
END $$;

-- ============================================================================
-- PARTIE 10: RÉSUMÉ FINAL
-- ============================================================================

SELECT '========== RÉSUMÉ FINAL ==========' as section;

SELECT
    'Tables' as element,
    (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public') as count;

SELECT
    'Fonctions' as element,
    (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public') as count;

SELECT
    'Triggers' as element,
    (SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = 'public') as count;

SELECT
    'Vues' as element,
    (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public') as count;

SELECT
    'Conversations' as element,
    COUNT(*) as count
FROM conversations;

SELECT
    'Messages' as element,
    COUNT(*) as count
FROM messages;

SELECT '========== FIN VÉRIFICATION ==========' as section;
