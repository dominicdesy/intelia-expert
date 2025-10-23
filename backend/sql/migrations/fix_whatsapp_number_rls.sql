-- Fix RLS policies to allow regular users to update their whatsapp_number
--
-- PROBLÈME IDENTIFIÉ:
-- Les politiques RLS actuelles utilisent: auth.uid() = id
-- Mais votre table users utilise le champ: auth_user_id
--
-- C'est pourquoi ça ne fonctionne que pour les super admins (qui utilisent
-- la service role key qui bypass RLS) mais pas pour les utilisateurs réguliers
-- (qui sont soumis aux politiques RLS).

-- 1. Drop the incorrect policies
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;

-- 2. Recreate with correct field: auth_user_id
CREATE POLICY "Users can view own profile"
ON users
FOR SELECT
USING (auth.uid() = auth_user_id);

CREATE POLICY "Users can update own profile"
ON users
FOR UPDATE
USING (auth.uid() = auth_user_id)
WITH CHECK (auth.uid() = auth_user_id);

-- 3. Verify the policies were created correctly
-- Run this to check:
-- SELECT policyname, cmd, qual, with_check
-- FROM pg_policies
-- WHERE tablename = 'users'
-- AND policyname IN ('Users can view own profile', 'Users can update own profile');

-- Expected result should show:
-- - qual: (auth.uid() = auth_user_id)  ✅ NOT (auth.uid() = id) ❌

COMMENT ON TABLE users IS 'Users table with RLS - users can view/update their own profile via auth_user_id';
