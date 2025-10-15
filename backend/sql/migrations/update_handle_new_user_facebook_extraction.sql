-- ================================================================
-- UPDATE HANDLE_NEW_USER - EXTRACT FACEBOOK PROFILE URL
-- ================================================================
-- This script updates the handle_new_user trigger to automatically extract
-- the Facebook profile URL from OAuth avatar_url metadata when users sign
-- in with Facebook.
--
-- WHAT IT DOES:
-- - Extracts Facebook user ID from avatar_url (asid= parameter)
-- - Constructs Facebook profile URL: https://facebook.com/{user_id}
-- - Saves to facebook_profile column in public.users
-- - Fully automatic - no user action required
--
-- PREREQUISITES:
-- - facebook_profile column must exist (run add_facebook_profile_to_users.sql first)
--
-- ✅ READY TO EXECUTE in Supabase Dashboard → SQL Editor
-- ✅ Zero downtime - Trigger is replaced atomically
-- ================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_avatar_url TEXT;
  v_facebook_id TEXT;
  v_facebook_profile TEXT;
BEGIN
  -- Extract avatar_url from raw_user_meta_data
  v_avatar_url := NEW.raw_user_meta_data->>'avatar_url';

  -- Extract Facebook ID from avatar URL if present
  -- Format: https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10161563757712721&...
  IF v_avatar_url IS NOT NULL AND v_avatar_url LIKE '%fbsbx.com%' AND v_avatar_url LIKE '%asid=%' THEN
    -- Extract the value between 'asid=' and the next '&' (or end of string)
    v_facebook_id := substring(v_avatar_url from 'asid=([0-9]+)');

    IF v_facebook_id IS NOT NULL THEN
      v_facebook_profile := 'https://facebook.com/' || v_facebook_id;
    END IF;
  END IF;

  -- Insert user profile with all extracted metadata
  INSERT INTO public.users (
    id,
    auth_user_id,
    email,
    email_verified,
    first_name,
    last_name,
    full_name,
    country,
    phone,
    company_name,
    user_type,
    language,
    facebook_profile,
    created_at
  )
  VALUES (
    NEW.id,
    NEW.id,
    NEW.email,
    NEW.email_confirmed_at IS NOT NULL,
    -- Extract first_name from raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'first_name', NULL),
    -- Extract last_name from raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'last_name', NULL),
    -- Extract full_name from raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'full_name', NULL),
    -- Extract country from raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'country', NULL),
    -- Extract phone from raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'phone', NULL),
    -- Extract company from raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'company', NULL),
    -- user_type defaults to 'user'
    'user',
    -- Extract preferred_language from raw_user_meta_data, default 'en'
    COALESCE(NEW.raw_user_meta_data->>'preferred_language', 'en'),
    -- Facebook profile URL (extracted above)
    v_facebook_profile,
    -- created_at
    NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    -- If user already exists (shouldn't happen), update fields
    first_name = COALESCE(EXCLUDED.first_name, public.users.first_name),
    last_name = COALESCE(EXCLUDED.last_name, public.users.last_name),
    full_name = COALESCE(EXCLUDED.full_name, public.users.full_name),
    country = COALESCE(EXCLUDED.country, public.users.country),
    phone = COALESCE(EXCLUDED.phone, public.users.phone),
    company_name = COALESCE(EXCLUDED.company_name, public.users.company_name),
    language = COALESCE(EXCLUDED.language, public.users.language),
    facebook_profile = COALESCE(EXCLUDED.facebook_profile, public.users.facebook_profile),
    updated_at = NOW();

  RETURN NEW;
END;
$$;

-- ================================================================
-- ✅ VERIFICATION
-- ================================================================
-- Display the trigger definition to verify it extracts Facebook ID

SELECT
  proname AS "Function",
  prosrc AS "SQL Code"
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname = 'handle_new_user';

-- ================================================================
-- 🧪 TEST (OPTIONAL)
-- ================================================================
-- To test that the trigger works correctly:
-- 1. Create a new user via Facebook OAuth
-- 2. Verify that facebook_profile is saved:
--
-- SELECT
--   id,
--   email,
--   full_name,
--   facebook_profile,
--   created_at
-- FROM public.users
-- WHERE facebook_profile IS NOT NULL
-- ORDER BY created_at DESC
-- LIMIT 5;

-- ================================================================
-- 🎉 DONE!
-- ================================================================
-- The handle_new_user() trigger will now:
-- ✅ Extract Facebook user ID from avatar_url (asid= parameter)
-- ✅ Construct Facebook profile URL: https://facebook.com/{user_id}
-- ✅ Save to facebook_profile column automatically
-- ✅ Work for all new Facebook OAuth signups
--
-- IMPORTANT NOTE:
-- Users who signed up BEFORE this fix will not have facebook_profile.
-- To backfill existing users, run the backfill migration.
-- ================================================================
