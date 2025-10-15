-- ================================================================
-- BACKFILL FACEBOOK PROFILES FOR EXISTING USERS
-- ================================================================
-- This script extracts Facebook profile URLs from existing users who
-- signed up via Facebook OAuth BEFORE the automatic extraction was added.
--
-- WHAT IT DOES:
-- - Reads raw_user_meta_data from auth.users for all existing users
-- - Extracts Facebook user ID from avatar_url (asid= parameter)
-- - Constructs Facebook profile URL: https://facebook.com/{user_id}
-- - Updates public.users.facebook_profile column
--
-- PREREQUISITES:
-- - facebook_profile column must exist
-- - update_handle_new_user_facebook_extraction.sql must be applied
--
-- ⚠️ IMPORTANT: This is a one-time migration for existing data
-- ⚠️ New users will get facebook_profile automatically via trigger
--
-- ✅ READY TO EXECUTE in Supabase Dashboard → SQL Editor
-- ================================================================

-- Update existing users who have Facebook avatar URLs
UPDATE public.users
SET
  facebook_profile = 'https://facebook.com/' ||
    substring(
      (SELECT raw_user_meta_data->>'avatar_url'
       FROM auth.users
       WHERE auth.users.id = public.users.auth_user_id)
      from 'asid=([0-9]+)'
    ),
  updated_at = NOW()
WHERE
  -- Only update users who don't have facebook_profile yet
  facebook_profile IS NULL
  -- And who have a Facebook avatar URL
  AND EXISTS (
    SELECT 1
    FROM auth.users
    WHERE auth.users.id = public.users.auth_user_id
      AND raw_user_meta_data->>'avatar_url' LIKE '%fbsbx.com%'
      AND raw_user_meta_data->>'avatar_url' LIKE '%asid=%'
  );

-- ================================================================
-- ✅ VERIFICATION
-- ================================================================
-- Check how many users now have Facebook profiles

SELECT
  COUNT(*) FILTER (WHERE facebook_profile IS NOT NULL) AS users_with_facebook,
  COUNT(*) FILTER (WHERE facebook_profile IS NULL) AS users_without_facebook,
  COUNT(*) AS total_users
FROM public.users;

-- Display sample of extracted Facebook profiles
SELECT
  id,
  email,
  full_name,
  facebook_profile,
  updated_at
FROM public.users
WHERE facebook_profile IS NOT NULL
ORDER BY updated_at DESC
LIMIT 10;

-- ================================================================
-- 🎉 DONE!
-- ================================================================
-- Existing Facebook users now have their profile URLs extracted.
-- New Facebook signups will get their URLs automatically via trigger.
-- ================================================================
