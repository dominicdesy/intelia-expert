-- Migration: Add user analytics capabilities to metrics
-- Date: 2025-10-26
-- Purpose: Enable cost per user analysis by linking metrics to messages

-- Add user_id column to llm_metrics_history (nullable for backwards compatibility)
ALTER TABLE llm_metrics_history
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add index for user-based queries
CREATE INDEX IF NOT EXISTS idx_llm_metrics_user_id
ON llm_metrics_history(user_id) WHERE user_id IS NOT NULL;

-- Add composite index for user + date range queries
CREATE INDEX IF NOT EXISTS idx_llm_metrics_user_date
ON llm_metrics_history(user_id, recorded_at DESC) WHERE user_id IS NOT NULL;

-- Add index for provider-based error analysis
CREATE INDEX IF NOT EXISTS idx_llm_metrics_provider_status
ON llm_metrics_history(provider, status);

COMMENT ON COLUMN llm_metrics_history.user_id IS 'User who triggered this LLM call (enriched post-sync from messages table)';
