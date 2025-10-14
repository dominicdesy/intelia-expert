-- ================================================================
-- 🔄 MIGRATION - CORRIGER LES UTILISATEURS EXISTANTS
-- ================================================================
-- Ce script corrige les utilisateurs déjà créés AVANT la correction du
-- trigger handle_new_user. Il lit les données depuis auth.users.raw_user_meta_data
-- et met à jour les champs manquants dans public.users.
--
-- CAS D'USAGE:
-- - Utilisateurs créés avec des champs first_name, last_name, country vides
-- - Données présentes dans auth.users.raw_user_meta_data mais pas dans public.users
--
-- ✅ PRÊT À EXÉCUTER dans Supabase Dashboard → SQL Editor
-- ✅ Sécurisé - Ne met à jour que les champs NULL
-- ================================================================

-- Étape 1: Voir combien d'utilisateurs seront affectés
SELECT
  COUNT(*) as "Utilisateurs avec données manquantes"
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
-- Étape 2: Voir le détail des utilisateurs qui seront corrigés
-- ================================================================
SELECT
  u.email,
  u.first_name as "first_name_actuel",
  au.raw_user_meta_data->>'first_name' as "first_name_dans_metadata",
  u.last_name as "last_name_actuel",
  au.raw_user_meta_data->>'last_name' as "last_name_dans_metadata",
  u.country as "country_actuel",
  au.raw_user_meta_data->>'country' as "country_dans_metadata",
  u.full_name as "full_name_actuel",
  au.raw_user_meta_data->>'full_name' as "full_name_dans_metadata"
FROM public.users u
INNER JOIN auth.users au ON u.auth_user_id = au.id
WHERE
  (u.first_name IS NULL AND au.raw_user_meta_data->>'first_name' IS NOT NULL)
  OR (u.last_name IS NULL AND au.raw_user_meta_data->>'last_name' IS NOT NULL)
  OR (u.country IS NULL AND au.raw_user_meta_data->>'country' IS NOT NULL)
  OR (u.full_name IS NULL AND au.raw_user_meta_data->>'full_name' IS NOT NULL);

-- ================================================================
-- Étape 3: EXÉCUTER LA MIGRATION
-- ================================================================
-- Cette requête met à jour TOUS les utilisateurs qui ont des données
-- dans raw_user_meta_data mais pas dans public.users
-- ⚠️ Décommentez et exécutez cette requête après avoir vérifié les étapes 1 et 2

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

-- ================================================================
-- Étape 4: Vérifier que la migration a fonctionné
-- ================================================================
SELECT
  u.email,
  u.first_name,
  u.last_name,
  u.country,
  u.full_name,
  u.phone,
  u.company_name,
  u.language,
  u.updated_at
FROM public.users u
INNER JOIN auth.users au ON u.auth_user_id = au.id
WHERE
  au.raw_user_meta_data->>'first_name' IS NOT NULL
  OR au.raw_user_meta_data->>'last_name' IS NOT NULL
  OR au.raw_user_meta_data->>'country' IS NOT NULL
ORDER BY u.created_at DESC
LIMIT 10;

-- ================================================================
-- 🎉 MIGRATION TERMINÉE!
-- ================================================================
-- Les utilisateurs existants ont maintenant leurs données complètes :
-- ✅ first_name, last_name, country récupérés depuis raw_user_meta_data
-- ✅ full_name, phone, company_name également mis à jour
-- ✅ language défini (par défaut 'en' si non spécifié)
--
-- PROCHAINE ÉTAPE:
-- Les utilisateurs doivent se déconnecter et se reconnecter pour que
-- le frontend récupère les nouvelles données via /auth/me
-- ================================================================
