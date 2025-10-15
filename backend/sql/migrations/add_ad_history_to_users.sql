-- Migration: Add ad_history column to users table for persistent ad rotation
-- Date: 2025-01-15
-- Description: Store the last 10 ads shown to each user to ensure rotation works
--              even in private browsing mode where all local storage is cleared

-- Add ad_history column as JSONB array
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS ad_history JSONB DEFAULT '[]'::jsonb;

-- Add comment to document the column
COMMENT ON COLUMN public.users.ad_history IS
'Array of the last 10 ad IDs shown to the user. Format: ["ad-01-poultry-ai", "ad-02-smart-sensors-mike-2024"]. Used for ad rotation to prevent showing the same ad twice in a row.';

-- Create index for better query performance on ad_history
CREATE INDEX IF NOT EXISTS idx_users_ad_history ON public.users USING gin(ad_history);

-- Example usage:
-- UPDATE users SET ad_history = '["ad-02-smart-sensors-mike-2024"]'::jsonb WHERE user_id = 'xxx';
-- SELECT ad_history FROM users WHERE user_id = 'xxx';
