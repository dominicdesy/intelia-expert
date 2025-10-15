-- Migration: Add facebook_profile column to users table
-- Date: 2025-10-15
-- Description: Store Facebook profile URL extracted from OAuth data

-- Add facebook_profile column as TEXT
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS facebook_profile TEXT;

-- Add comment to document the column
COMMENT ON COLUMN public.users.facebook_profile IS
'Facebook profile URL. Format: https://facebook.com/{user_id}. Extracted automatically from OAuth avatar_url.';

-- Example usage:
-- UPDATE users SET facebook_profile = 'https://facebook.com/10161563757712721' WHERE user_id = 'xxx';
