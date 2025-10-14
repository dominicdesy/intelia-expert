-- ================================================================
-- 🚀 FIX COMPLET - PROFILS UTILISATEURS
-- ================================================================
-- Script tout-en-un pour corriger le problème des champs de profil vides.
--
-- CE SCRIPT FAIT:
-- 1. Corrige le trigger handle_new_user() pour les futurs utilisateurs
-- 2. Migre les données pour les utilisateurs existants
-- 3. Vérifie que tout fonctionne correctement
--
-- EXÉCUTION:
-- 1. Ouvrir Supabase Dashboard → SQL Editor
-- 2. Copier-coller CE FICHIER COMPLET
-- 3. Cliquer sur "Run" (ou F5)
-- 4. Vérifier les résultats affichés
--
-- ✅ Sécurisé - Zéro downtime - Aucun changement fonctionnel
-- ================================================================

-- ================================================================
-- PARTIE 1: CORRIGER LE TRIGGER handle_new_user()
-- ================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  -- Extraire les métadonnées utilisateur depuis raw_user_meta_data (JSON)
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
    created_at
  )
  VALUES (
    NEW.id,
    NEW.id,
    NEW.email,
    NEW.email_confirmed_at IS NOT NULL,
    -- Extraire first_name depuis raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'first_name', NULL),
    -- Extraire last_name depuis raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'last_name', NULL),
    -- Extraire full_name depuis raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'full_name', NULL),
    -- Extraire country depuis raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'country', NULL),
    -- Extraire phone depuis raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'phone', NULL),
    -- Extraire company depuis raw_user_meta_data
    COALESCE(NEW.raw_user_meta_data->>'company', NULL),
    -- user_type par défaut à 'user'
    'user',
    -- Extraire preferred_language depuis raw_user_meta_data, par défaut 'en'
    COALESCE(NEW.raw_user_meta_data->>'preferred_language', 'en'),
    -- created_at
    NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    -- Si l'utilisateur existe déjà (ne devrait pas arriver), mettre à jour les champs
    first_name = COALESCE(EXCLUDED.first_name, public.users.first_name),
    last_name = COALESCE(EXCLUDED.last_name, public.users.last_name),
    full_name = COALESCE(EXCLUDED.full_name, public.users.full_name),
    country = COALESCE(EXCLUDED.country, public.users.country),
    phone = COALESCE(EXCLUDED.phone, public.users.phone),
    company_name = COALESCE(EXCLUDED.company_name, public.users.company_name),
    language = COALESCE(EXCLUDED.language, public.users.language),
    updated_at = NOW();

  RETURN NEW;
END;
$$;

SELECT '✅ PARTIE 1 TERMINÉE: Trigger handle_new_user() mis à jour' as "Status";

-- ================================================================
-- PARTIE 2: ANALYSE - Combien d'utilisateurs seront corrigés ?
-- ================================================================

SELECT
  COUNT(*) as "Utilisateurs à corriger",
  'Utilisateurs avec données dans raw_user_meta_data mais champs vides dans public.users' as "Description"
FROM public.users u
INNER JOIN auth.users au ON u.auth_user_id = au.id
WHERE
  (u.first_name IS NULL AND au.raw_user_meta_data->>'first_name' IS NOT NULL)
  OR (u.last_name IS NULL AND au.raw_user_meta_data->>'last_name' IS NOT NULL)
  OR (u.country IS NULL AND au.raw_user_meta_data->>'country' IS NOT NULL)
  OR (u.full_name IS NULL AND au.raw_user_meta_data->>'full_name' IS NOT NULL)
  OR (u.phone IS NULL AND au.raw_user_meta_data->>'phone' IS NOT NULL)
  OR (u.company_name IS NULL AND au.raw_user_meta_data->>'company' IS NOT NULL);

-- ================================================================
-- PARTIE 3: DÉTAIL - Quels utilisateurs seront corrigés ?
-- ================================================================

SELECT
  u.email as "Email",
  u.first_name as "Prénom actuel",
  au.raw_user_meta_data->>'first_name' as "Prénom dans metadata",
  u.last_name as "Nom actuel",
  au.raw_user_meta_data->>'last_name' as "Nom dans metadata",
  u.country as "Pays actuel",
  au.raw_user_meta_data->>'country' as "Pays dans metadata"
FROM public.users u
INNER JOIN auth.users au ON u.auth_user_id = au.id
WHERE
  (u.first_name IS NULL AND au.raw_user_meta_data->>'first_name' IS NOT NULL)
  OR (u.last_name IS NULL AND au.raw_user_meta_data->>'last_name' IS NOT NULL)
  OR (u.country IS NULL AND au.raw_user_meta_data->>'country' IS NOT NULL)
ORDER BY u.created_at DESC;

-- ================================================================
-- PARTIE 4: MIGRATION - Corriger les utilisateurs existants
-- ================================================================

UPDATE public.users u
SET
  first_name = COALESCE(u.first_name, au.raw_user_meta_data->>'first_name'),
  last_name = COALESCE(u.last_name, au.raw_user_meta_data->>'last_name'),
  full_name = COALESCE(u.full_name, au.raw_user_meta_data->>'full_name'),
  country = COALESCE(u.country, au.raw_user_meta_data->>'country'),
  phone = COALESCE(u.phone, au.raw_user_meta_data->>'phone'),
  company_name = COALESCE(u.company_name, au.raw_user_meta_data->>'company'),
  language = COALESCE(u.language, au.raw_user_meta_data->>'preferred_language', 'en'),
  updated_at = NOW()
FROM auth.users au
WHERE u.auth_user_id = au.id
  AND (
    (u.first_name IS NULL AND au.raw_user_meta_data->>'first_name' IS NOT NULL)
    OR (u.last_name IS NULL AND au.raw_user_meta_data->>'last_name' IS NOT NULL)
    OR (u.country IS NULL AND au.raw_user_meta_data->>'country' IS NOT NULL)
    OR (u.full_name IS NULL AND au.raw_user_meta_data->>'full_name' IS NOT NULL)
    OR (u.phone IS NULL AND au.raw_user_meta_data->>'phone' IS NOT NULL)
    OR (u.company_name IS NULL AND au.raw_user_meta_data->>'company' IS NOT NULL)
  );

SELECT '✅ PARTIE 4 TERMINÉE: Utilisateurs existants mis à jour' as "Status";

-- ================================================================
-- PARTIE 5: VÉRIFICATION - Les données sont-elles correctes ?
-- ================================================================

SELECT
  u.email as "Email",
  u.first_name as "Prénom",
  u.last_name as "Nom",
  u.country as "Pays",
  u.full_name as "Nom complet",
  u.phone as "Téléphone",
  u.company_name as "Entreprise",
  u.language as "Langue",
  u.updated_at as "Dernière mise à jour"
FROM public.users u
INNER JOIN auth.users au ON u.auth_user_id = au.id
WHERE
  au.raw_user_meta_data->>'first_name' IS NOT NULL
  OR au.raw_user_meta_data->>'last_name' IS NOT NULL
  OR au.raw_user_meta_data->>'country' IS NOT NULL
ORDER BY u.updated_at DESC
LIMIT 10;

-- ================================================================
-- 🎉 MIGRATION COMPLÈTE TERMINÉE!
-- ================================================================
-- RÉSULTATS:
-- ✅ Le trigger handle_new_user() extrait maintenant tous les champs
-- ✅ Les utilisateurs existants ont été mis à jour avec leurs données
-- ✅ Les futurs utilisateurs auront automatiquement tous leurs champs
--
-- PROCHAINE ÉTAPE:
-- Les utilisateurs doivent se DÉCONNECTER et se RECONNECTER pour que
-- le frontend récupère les nouvelles données via l'endpoint /auth/me
--
-- VÉRIFICATION MANUELLE (exemple pour John Smith):
-- SELECT * FROM public.users WHERE email = 'dominic.desy@icloud.com';
-- ================================================================

SELECT
  '🎉 MIGRATION TERMINÉE!' as "Status",
  'Les utilisateurs doivent se déconnecter et se reconnecter' as "Action requise";
