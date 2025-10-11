-- ============================================================================
-- NETTOYAGE: Tables inutiles DigitalOcean PostgreSQL
-- ============================================================================
-- Date: 2025-10-11
-- Description: Supprime les tables qui ne sont plus utilisées
-- ============================================================================

-- ⚠️ ATTENTION: Exécuter APRÈS avoir créé la table messages!
-- Fichier: create_messages_table_only.sql

-- Tables à supprimer (confirmé non utilisées dans le code):
DROP TABLE IF EXISTS invitations CASCADE;
DROP TABLE IF EXISTS invitations_cache CASCADE;
DROP TABLE IF EXISTS questions_cache CASCADE;

-- Vérification après suppression
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- ============================================================================
-- Tables attendues après nettoyage:
-- ============================================================================
/*
✅ analytics_cache
✅ billing_plans
✅ conversations (NOUVELLE ARCHITECTURE)
✅ daily_openai_summary
✅ dashboard_stats_lite
✅ dashboard_stats_snapshot
✅ messages (NOUVELLE ARCHITECTURE - à créer d'abord!)
✅ monthly_invoices
✅ monthly_usage_tracking
✅ openai_api_calls
✅ openai_costs_cache
✅ openai_usage
✅ quota_audit_log
✅ server_performance_metrics
✅ statistics_cache
✅ system_errors
✅ user_billing_info
✅ user_sessions

❌ invitations (supprimée - maintenant dans Supabase)
❌ invitations_cache (supprimée)
❌ questions_cache (supprimée - non utilisée)
*/
