-- ============================================================================
-- Migration: Create user_headway_tracking table
-- Description: Track Headway articles viewed by users (for navigation privée)
-- Author: Claude Code
-- Date: 2025-10-31
-- ============================================================================

-- Create user_headway_tracking table
CREATE TABLE IF NOT EXISTS user_headway_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    article_id TEXT NOT NULL,
    viewed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraint to auth.users
    CONSTRAINT fk_user_headway_tracking_user_id
        FOREIGN KEY (user_id)
        REFERENCES auth.users(id)
        ON DELETE CASCADE,

    -- Ensure one record per user/article
    CONSTRAINT uq_user_headway_tracking_user_article UNIQUE (user_id, article_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_headway_tracking_user_id
    ON user_headway_tracking(user_id);

CREATE INDEX IF NOT EXISTS idx_user_headway_tracking_viewed_at
    ON user_headway_tracking(viewed_at DESC);

-- Enable Row Level Security
ALTER TABLE user_headway_tracking ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own tracking
CREATE POLICY "users_view_own_headway_tracking"
    ON user_headway_tracking
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own tracking
CREATE POLICY "users_insert_own_headway_tracking"
    ON user_headway_tracking
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Add comments for documentation
COMMENT ON TABLE user_headway_tracking IS
    'Tracks Headway articles viewed by users. Persists across sessions and private browsing.';

COMMENT ON COLUMN user_headway_tracking.article_id IS
    'Headway article ID (from Headway widget)';

COMMENT ON COLUMN user_headway_tracking.viewed_at IS
    'Timestamp when user viewed the article';

-- Verification query
-- SELECT * FROM user_headway_tracking;
