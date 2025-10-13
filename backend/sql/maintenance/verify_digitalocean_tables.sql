-- ============================================================================
-- VÉRIFICATION: Tables dans DigitalOcean PostgreSQL
-- ============================================================================

-- Lister toutes les tables
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Vérifier que les tables de la nouvelle architecture existent
SELECT
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'conversations')
         THEN '✅ conversations existe'
         ELSE '❌ conversations MANQUANTE'
    END as conversations_status,
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'messages')
         THEN '✅ messages existe'
         ELSE '❌ messages MANQUANTE'
    END as messages_status;

-- Compter les données
SELECT 'conversations' as table_name, COUNT(*) as row_count FROM conversations
UNION ALL
SELECT 'messages', COUNT(*) FROM messages;

-- Vérifier les fonctions
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
