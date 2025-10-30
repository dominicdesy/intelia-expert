-- ============================================================================
-- Migration: Create user_compass_config table
-- Description: Store Compass integration configuration per user
-- Author: Claude Code
-- Date: 2025-10-30
-- ============================================================================

-- Create user_compass_config table
CREATE TABLE IF NOT EXISTS user_compass_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    compass_enabled BOOLEAN DEFAULT false,
    barns JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign key constraint to auth.users
    CONSTRAINT fk_user_compass_config_user_id
        FOREIGN KEY (user_id)
        REFERENCES auth.users(id)
        ON DELETE CASCADE,

    -- Ensure one config per user
    CONSTRAINT uq_user_compass_config_user_id UNIQUE (user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_compass_config_user_id
    ON user_compass_config(user_id);

CREATE INDEX IF NOT EXISTS idx_user_compass_config_enabled
    ON user_compass_config(compass_enabled)
    WHERE compass_enabled = true;

-- Enable Row Level Security
ALTER TABLE user_compass_config ENABLE ROW LEVEL SECURITY;

-- Policy: Admin full access
CREATE POLICY "admin_full_access_compass_config"
    ON user_compass_config
    FOR ALL
    USING (
        EXISTS (
            SELECT 1
            FROM auth.users
            WHERE auth.users.id = auth.uid()
            AND auth.users.role IN ('admin', 'superuser')
        )
    );

-- Policy: Users can view their own config (read-only)
CREATE POLICY "users_view_own_compass_config"
    ON user_compass_config
    FOR SELECT
    USING (auth.uid() = user_id);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_compass_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_compass_config_updated_at
    BEFORE UPDATE ON user_compass_config
    FOR EACH ROW
    EXECUTE FUNCTION update_user_compass_config_updated_at();

-- Add comments for documentation
COMMENT ON TABLE user_compass_config IS
    'Stores Compass integration configuration per user. Admins manage which barns users can access.';

COMMENT ON COLUMN user_compass_config.barns IS
    'JSONB array of barn configurations. Example: [{"compass_device_id": "849", "client_number": "2", "name": "Poulailler Est", "enabled": true}]';

COMMENT ON COLUMN user_compass_config.compass_enabled IS
    'Master switch to enable/disable Compass integration for this user';

-- Verification query
-- SELECT * FROM user_compass_config;
