-- ============================================================================
-- NETTOYAGE FINAL: DigitalOcean PostgreSQL
-- ============================================================================
-- Date: 2025-10-11
-- Description: Supprime les tables qui appartiennent à Supabase
-- ============================================================================

-- Tables à supprimer (maintenant dans Supabase):
DROP TABLE IF EXISTS invitations CASCADE;
DROP TABLE IF EXISTS invitations_cache CASCADE;

-- Tables obsolètes (non utilisées):
DROP TABLE IF EXISTS questions_cache CASCADE;

-- Vérification après suppression
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- ============================================================================
-- Tables attendues dans DigitalOcean après nettoyage:
-- ============================================================================
/*
✅ analytics_cache
✅ billing_plans
✅ conversations (NOUVELLE ARCHITECTURE)
✅ daily_openai_summary
✅ dashboard_stats_lite
✅ dashboard_stats_snapshot
✅ messages (NOUVELLE ARCHITECTURE)
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

-- ============================================================================
-- Répartition finale des bases:
-- ============================================================================
/*
🟦 SUPABASE PostgreSQL:
  ✅ auth.users (authentification Supabase)
  ✅ public.users (profils utilisateurs)
  ✅ public.invitations (système d'invitation)

🟧 DIGITALOCEAN PostgreSQL:
  ✅ conversations (metadata des conversations)
  ✅ messages (messages individuels Q&R)
  ✅ analytics_cache, billing_plans, etc. (données métier)

📝 BACKEND (app/core/database.py):
  ✅ get_pg_connection() → DigitalOcean
  ✅ get_supabase_client() → Supabase
  ✅ get_user_from_supabase() → Supabase users

📂 SERVICES:
  ✅ conversation_service.py → DigitalOcean (conversations + messages)
  ✅ invitations.py → Supabase (invitations)
*/
