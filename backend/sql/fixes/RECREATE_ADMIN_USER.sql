-- ================================================================
-- 🔧 RECRÉATION DE L'UTILISATEUR SUPER ADMIN
-- ================================================================
-- Ce script recrée le compte super administrateur après suppression accidentelle
-- des utilisateurs dans Supabase.
--
-- UTILISATEUR À CRÉER:
-- - Nom: Dominic Désy
-- - Email: dominic.desy@intelia.com
-- - Pays: Canada
-- - Langue: Français (fr)
-- - Rôle: super_admin
--
-- ✅ PRÊT À EXÉCUTER dans Supabase Dashboard → SQL Editor
-- ================================================================

-- ÉTAPE 1: Créer l'utilisateur dans auth.users
-- Note: Vous devrez créer le mot de passe via l'interface Supabase
-- après exécution de ce script, ou utiliser l'API admin

-- IMPORTANT: Ce script crée seulement l'entrée dans public.users
-- Pour créer l'utilisateur auth, suivez les instructions ci-dessous

-- ================================================================
-- INSTRUCTIONS PRÉALABLES (VIA SUPABASE DASHBOARD):
-- ================================================================
-- 1. Allez dans Authentication → Users
-- 2. Cliquez sur "Add User" → "Create new user"
-- 3. Email: dominic.desy@intelia.com
-- 4. Cochez "Auto Confirm User" (pour skip email verification)
-- 5. Définissez un mot de passe temporaire
-- 6. Copiez l'UUID généré (vous en aurez besoin pour la suite)
-- 7. Ensuite, exécutez ce script en remplaçant 'YOUR_AUTH_USER_ID'
--    par l'UUID copié
-- ================================================================

-- ALTERNATIVE: Si vous préférez tout faire via SQL, décommentez cette section:
/*
-- Créer l'utilisateur dans auth.users via une fonction admin
DO $$
DECLARE
  new_user_id uuid;
BEGIN
  -- Générer un UUID pour le nouvel utilisateur
  new_user_id := gen_random_uuid();

  -- Insérer dans auth.users
  INSERT INTO auth.users (
    id,
    instance_id,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change_token_new,
    recovery_token
  ) VALUES (
    new_user_id,
    '00000000-0000-0000-0000-000000000000', -- Instance ID par défaut
    'dominic.desy@intelia.com',
    crypt('CHANGEZ_CE_MOT_DE_PASSE', gen_salt('bf')), -- ⚠️ CHANGEZ LE MOT DE PASSE!
    NOW(), -- Email déjà confirmé
    jsonb_build_object(
      'first_name', 'Dominic',
      'last_name', 'Désy',
      'full_name', 'Dominic Désy',
      'country', 'Canada',
      'preferred_language', 'fr'
    ),
    NOW(),
    NOW(),
    '',
    '',
    ''
  );

  RAISE NOTICE 'Utilisateur créé avec ID: %', new_user_id;
END $$;
*/

-- ================================================================
-- ÉTAPE 2: Créer le profil dans public.users
-- ================================================================
-- ⚠️ REMPLACEZ 'YOUR_AUTH_USER_ID' par l'UUID de l'utilisateur créé ci-dessus

INSERT INTO public.users (
  id,
  auth_user_id,
  email,
  email_verified,
  first_name,
  last_name,
  full_name,
  country,
  user_type,
  language,
  created_at,
  updated_at
) VALUES (
  'YOUR_AUTH_USER_ID'::uuid,  -- ⚠️ REMPLACEZ PAR L'UUID RÉEL
  'YOUR_AUTH_USER_ID'::uuid,  -- ⚠️ REMPLACEZ PAR L'UUID RÉEL
  'dominic.desy@intelia.com',
  TRUE,                        -- Email vérifié
  'Dominic',
  'Désy',
  'Dominic Désy',
  'Canada',
  'super_admin',               -- ✅ Rôle super admin
  'fr',                        -- Français
  NOW(),
  NOW()
)
ON CONFLICT (id) DO UPDATE SET
  user_type = 'super_admin',   -- Forcer le rôle super admin si déjà existant
  email = EXCLUDED.email,
  first_name = EXCLUDED.first_name,
  last_name = EXCLUDED.last_name,
  full_name = EXCLUDED.full_name,
  country = EXCLUDED.country,
  language = EXCLUDED.language,
  updated_at = NOW();

-- ================================================================
-- ✅ VÉRIFICATION
-- ================================================================
-- Vérifier que l'utilisateur a été créé avec le bon rôle

SELECT
  id,
  email,
  first_name,
  last_name,
  full_name,
  country,
  user_type,
  language,
  email_verified,
  created_at
FROM public.users
WHERE email = 'dominic.desy@intelia.com';

-- Vérifier que is_admin est correctement dérivé (devrait être TRUE)
-- Note: is_admin n'est pas stocké en DB, il est calculé côté backend
-- depuis user_type IN ('admin', 'super_admin')

-- ================================================================
-- 📋 ÉTAPES POST-CRÉATION
-- ================================================================
-- 1. ✅ Vérifiez que l'utilisateur apparaît dans Authentication → Users
-- 2. ✅ Vérifiez que le profil existe dans Table Editor → users
-- 3. ✅ Testez la connexion avec l'email et le mot de passe
-- 4. ✅ Vérifiez les permissions admin dans l'application
-- 5. 🔒 CHANGEZ le mot de passe temporaire immédiatement!
-- ================================================================

-- ================================================================
-- 🎉 C'EST FAIT!
-- ================================================================
-- L'utilisateur Dominic Désy (dominic.desy@intelia.com) a été recréé
-- avec le rôle super_admin.
--
-- Le backend calculera automatiquement is_admin = TRUE car
-- user_type = 'super_admin'
--
-- IMPORTANT: N'oubliez pas de changer le mot de passe temporaire!
-- ================================================================
