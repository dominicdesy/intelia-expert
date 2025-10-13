-- ================================================================
-- FIX: Secure search_path for database functions
-- ================================================================
-- Addresses Supabase security warnings:
-- - function_search_path_mutable for handle_new_user
-- - function_search_path_mutable for notify_user_created
-- - function_search_path_mutable for update_updated_at_column
--
-- SECURITY ISSUE: Functions without a fixed search_path can be
-- exploited through search path injection attacks.
--
-- Date: 2025-01-13
-- ================================================================

-- Fix 1: handle_new_user function
-- This function is typically a trigger that creates a profile when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.user_profiles (
    user_id,
    email,
    full_name,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NOW(),
    NOW()
  );
  RETURN NEW;
END;
$$;

-- Fix 2: notify_user_created function
-- This function is typically used to send notifications when a user is created
CREATE OR REPLACE FUNCTION public.notify_user_created()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  -- Add your notification logic here
  -- Example: INSERT INTO notifications or call pg_notify
  PERFORM pg_notify(
    'user_created',
    json_build_object(
      'user_id', NEW.id,
      'email', NEW.email,
      'created_at', NEW.created_at
    )::text
  );
  RETURN NEW;
END;
$$;

-- Fix 3: update_updated_at_column function
-- This function is a common trigger to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- ================================================================
-- IMPORTANT NOTES:
-- ================================================================
-- 1. Review the function logic above to ensure it matches your
--    current implementation before executing this script
-- 2. You can verify current function definitions with:
--    SELECT pg_get_functiondef(oid)
--    FROM pg_proc
--    WHERE proname IN ('handle_new_user', 'notify_user_created', 'update_updated_at_column');
-- 3. After running this script, re-run the Supabase linter to
--    verify the warnings are resolved
-- ================================================================

-- Verification query to check search_path is now set
SELECT
  proname AS function_name,
  proconfig AS settings
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('handle_new_user', 'notify_user_created', 'update_updated_at_column');
