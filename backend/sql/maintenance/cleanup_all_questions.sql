-- ============================================================================
-- CLEANUP: Suppression de toutes les questions et conversations
-- ============================================================================
-- Date: 2025-10-19
-- Description: Repart à zéro avec une base de données propre
-- ============================================================================

-- ATTENTION: Cette opération est IRRÉVERSIBLE !
-- Toutes les conversations et messages seront supprimés définitivement.

BEGIN;

-- Afficher le nombre de lignes AVANT suppression
SELECT
    (SELECT COUNT(*) FROM conversations) as conversations_count,
    (SELECT COUNT(*) FROM messages) as messages_count;

-- Supprimer tous les messages et conversations
-- CASCADE supprimera automatiquement tous les messages grâce au ON DELETE CASCADE
TRUNCATE TABLE conversations CASCADE;

-- Vérifier que les tables sont vides
SELECT
    (SELECT COUNT(*) FROM conversations) as conversations_count_after,
    (SELECT COUNT(*) FROM messages) as messages_count_after;

COMMIT;

-- ============================================================================
-- FIN DU CLEANUP
-- ============================================================================
-- Pour exécuter ce script:
-- psql -h localhost -U intelia_user -d intelia_db -f cleanup_all_questions.sql
-- ============================================================================
