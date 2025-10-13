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
-- Inserts new user into public.users table with email verification status
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.users (id, email, email_verified)
  VALUES (NEW.id, NEW.email, NEW.email_confirmed_at IS NOT NULL)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Fix 2: notify_user_created function
-- Calls webhook via pg_net to notify backend when a user is created
CREATE OR REPLACE FUNCTION public.notify_user_created()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  request_id bigint;
BEGIN
  -- Call webhook via pg_net
  SELECT net.http_post(
    url := 'https://expert.intelia.com/api/v1/webhooks/supabase/auth',
    headers := '{"Content-Type": "application/json"}'::jsonb,
    body := json_build_object(
      'type', 'INSERT',
      'table', 'auth.users',
      'record', json_build_object(
        'id', NEW.id,
        'email', NEW.email,
        'raw_user_meta_data', NEW.raw_user_meta_data,
        'created_at', NEW.created_at,
        'email_confirmed_at', NEW.email_confirmed_at
      )
    )::jsonb
  ) INTO request_id;

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
-- 1. This script contains the EXACT current implementation of your
--    functions with ONLY the addition of SET search_path = ''
-- 2. Safe to execute directly in Supabase SQL Editor
-- 3. After running this script, re-run the Supabase linter to
--    verify the warnings are resolved
-- 4. No downtime or user impact - functions are replaced atomically
-- ================================================================

-- Verification query to check search_path is now set
SELECT
  proname AS function_name,
  proconfig AS settings
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('handle_new_user', 'notify_user_created', 'update_updated_at_column');
