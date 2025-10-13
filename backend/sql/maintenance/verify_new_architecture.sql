-- ============================================================================
-- VÉRIFICATION: État de la nouvelle architecture dans Supabase
-- ============================================================================
-- Date: 2025-10-11
-- Description: Vérifie que toutes les tables, fonctions et triggers sont en place
-- ============================================================================

-- ÉTAPE 1: Vérifier les tables
-- =============================
SELECT
    tablename as table_name,
    schemaname as schema
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Résultat attendu:
-- - conversations
-- - messages
-- - users
-- (+ éventuellement d'autres tables métier)

-- ÉTAPE 2: Vérifier les colonnes de la table conversations
-- ==========================================================
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'conversations'
ORDER BY ordinal_position;

-- Colonnes attendues:
-- - id (UUID, NOT NULL)
-- - session_id (UUID, NOT NULL)
-- - user_id (TEXT, NOT NULL)
-- - title (TEXT, NULL)
-- - language (TEXT, NULL)
-- - message_count (INTEGER, NULL)
-- - first_message_preview (TEXT, NULL)
-- - last_message_preview (TEXT, NULL)
-- - status (TEXT, NULL)
-- - created_at (TIMESTAMP WITH TIME ZONE, NULL)
-- - updated_at (TIMESTAMP WITH TIME ZONE, NULL)
-- - last_activity_at (TIMESTAMP WITH TIME ZONE, NULL)

-- ÉTAPE 3: Vérifier les colonnes de la table messages
-- ====================================================
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'messages'
ORDER BY ordinal_position;

-- Colonnes attendues:
-- - id (UUID, NOT NULL)
-- - conversation_id (UUID, NOT NULL)
-- - role (TEXT, NOT NULL)
-- - content (TEXT, NOT NULL)
-- - sequence_number (INTEGER, NOT NULL)
-- - response_source (TEXT, NULL)
-- - response_confidence (DOUBLE PRECISION, NULL)
-- - processing_time_ms (INTEGER, NULL)
-- - feedback (TEXT, NULL)
-- - feedback_comment (TEXT, NULL)
-- - created_at (TIMESTAMP WITH TIME ZONE, NULL)

-- ÉTAPE 4: Vérifier les index
-- ============================
SELECT
    indexname as index_name,
    tablename as table_name,
    indexdef as definition
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('conversations', 'messages')
ORDER BY tablename, indexname;

-- Index attendus:
-- Sur conversations:
-- - idx_conversations_user_id
-- - idx_conversations_session_id
-- - idx_conversations_status
-- - idx_conversations_last_activity
--
-- Sur messages:
-- - idx_messages_conversation_id
-- - idx_messages_sequence
-- - idx_messages_role

-- ÉTAPE 5: Vérifier les fonctions
-- ================================
SELECT
    routine_name,
    routine_type,
    data_type as return_type
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;

-- Fonctions attendues:
-- - create_conversation_with_messages (FUNCTION, UUID)
-- - add_message_to_conversation (FUNCTION, UUID)
-- - get_conversation_messages (FUNCTION, SETOF)
-- - update_conversation_metadata (FUNCTION, trigger)
-- + fonctions système Supabase

-- ÉTAPE 6: Vérifier les triggers
-- ===============================
SELECT
    trigger_name,
    event_manipulation as event,
    event_object_table as table_name,
    action_statement as action
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- Trigger attendu:
-- - update_conversation_on_message_insert ON messages

-- ÉTAPE 7: Vérifier les vues
-- ===========================
SELECT
    table_name as view_name,
    view_definition
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;

-- Vues attendues:
-- - conversation_stats
-- - conversation_details

-- ÉTAPE 8: Vérifier les contraintes
-- ==================================
SELECT
    tc.constraint_name,
    tc.table_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.table_name IN ('conversations', 'messages')
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

-- Contraintes attendues:
-- Sur conversations:
-- - PRIMARY KEY sur id
-- - UNIQUE sur session_id
-- - CHECK sur status IN ('active', 'archived', 'deleted')
--
-- Sur messages:
-- - PRIMARY KEY sur id
-- - FOREIGN KEY conversation_id -> conversations(id)
-- - UNIQUE sur (conversation_id, sequence_number)
-- - CHECK sur role IN ('user', 'assistant', 'system')
-- - CHECK sur feedback IN ('positive', 'negative', 'neutral')

-- ÉTAPE 9: Compter les données
-- =============================
SELECT 'conversations' as table_name, COUNT(*) as row_count FROM conversations
UNION ALL
SELECT 'messages', COUNT(*) FROM messages
ORDER BY table_name;

-- ÉTAPE 10: Tester les fonctions
-- ===============================

-- Test 1: Créer une conversation de test
DO $$
DECLARE
    test_conv_id UUID;
BEGIN
    -- Créer une conversation de test
    SELECT create_conversation_with_messages(
        gen_random_uuid()::uuid,  -- session_id
        'test_user_123',          -- user_id
        'Question de test',       -- question
        'Réponse de test',        -- réponse
        'fr',                     -- langue
        'rag',                    -- source
        0.95,                     -- confidence
        1500                      -- processing_time_ms
    ) INTO test_conv_id;

    RAISE NOTICE 'Conversation de test créée: %', test_conv_id;

    -- Vérifier la création
    IF test_conv_id IS NOT NULL THEN
        RAISE NOTICE '✅ Test réussi: create_conversation_with_messages fonctionne';

        -- Nettoyer la conversation de test
        DELETE FROM conversations WHERE id = test_conv_id;
        RAISE NOTICE '✅ Conversation de test nettoyée';
    ELSE
        RAISE EXCEPTION '❌ Test échoué: create_conversation_with_messages retourne NULL';
    END IF;
END $$;

-- ============================================================================
-- RÉSULTAT ATTENDU
-- ============================================================================

/*
Si tout fonctionne correctement, vous devriez voir:

ÉTAPE 1 (Tables):
- conversations
- messages
- users

ÉTAPE 2 (Colonnes conversations):
12 colonnes avec les bons types

ÉTAPE 3 (Colonnes messages):
11 colonnes avec les bons types

ÉTAPE 4 (Index):
7 index au total (4 sur conversations, 3 sur messages)

ÉTAPE 5 (Fonctions):
- create_conversation_with_messages
- add_message_to_conversation
- get_conversation_messages
- update_conversation_metadata
+ fonctions système

ÉTAPE 6 (Triggers):
- update_conversation_on_message_insert

ÉTAPE 7 (Vues):
- conversation_stats
- conversation_details

ÉTAPE 8 (Contraintes):
PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK

ÉTAPE 9 (Données):
Nombre de conversations et messages

ÉTAPE 10 (Test fonctions):
✅ Test réussi: create_conversation_with_messages fonctionne
✅ Conversation de test nettoyée

Si un élément manque, exécutez le fichier:
db_schema_conversations_messages.sql
*/
