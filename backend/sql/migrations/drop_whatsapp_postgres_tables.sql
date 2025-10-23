-- Drop WhatsApp tables from PostgreSQL backend
-- These tables are no longer needed because WhatsApp numbers are now
-- stored directly in the Supabase users table

-- Version: 1.0
-- Date: 2025-10-23
-- Reason: Consolidation - WhatsApp numbers moved to Supabase users table

-- Drop functions first (they depend on tables)
DROP FUNCTION IF EXISTS get_or_create_whatsapp_conversation(VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS add_message_to_whatsapp_conversation(VARCHAR, JSONB);

-- Drop views
DROP VIEW IF EXISTS whatsapp_user_stats;
DROP VIEW IF EXISTS recent_whatsapp_messages;

-- Drop tables
DROP TABLE IF EXISTS whatsapp_conversations CASCADE;
DROP TABLE IF EXISTS whatsapp_message_logs CASCADE;
DROP TABLE IF EXISTS user_whatsapp_info CASCADE;

-- Confirmation message
DO $$
BEGIN
    RAISE NOTICE 'WhatsApp PostgreSQL tables dropped successfully';
    RAISE NOTICE 'WhatsApp numbers are now managed in Supabase users table';
END $$;
