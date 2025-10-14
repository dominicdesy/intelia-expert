-- ================================================================
-- 🔧 FIX HANDLE_NEW_USER - SAUVEGARDER TOUS LES CHAMPS DU PROFIL
-- ================================================================
-- Ce script corrige le trigger handle_new_user pour extraire et sauvegarder
-- TOUS les champs du profil depuis raw_user_meta_data (first_name, last_name,
-- country, phone, company_name, language, etc.)
--
-- PROBLÈME:
-- - Le trigger actuel n'insère que id, email, email_verified
-- - Les données first_name, last_name, country sont perdues
-- - Le backend essaie d'insérer après mais échoue à cause de ON CONFLICT DO NOTHING
--
-- SOLUTION:
-- - Extraire tous les champs depuis NEW.raw_user_meta_data (JSON)
-- - Insérer une entrée complète dans public.users
-- - Inclure tous les champs: first_name, last_name, country, phone, etc.
--
-- ✅ PRÊT À EXÉCUTER dans Supabase Dashboard → SQL Editor
-- ✅ Zéro downtime - Le trigger est remplacé atomiquement
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

-- ================================================================
-- ✅ VÉRIFICATION
-- ================================================================
-- Cette requête affiche la définition du trigger pour vérifier qu'il
-- extrait bien les champs depuis raw_user_meta_data

SELECT
  proname AS "Fonction",
  prosrc AS "Code SQL"
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname = 'handle_new_user';

-- ================================================================
-- 🧪 TEST (OPTIONNEL)
-- ================================================================
-- Pour tester que le trigger fonctionne correctement, vous pouvez:
-- 1. Créer un nouvel utilisateur via l'interface Supabase
-- 2. Vérifier que tous les champs sont bien sauvegardés:
--
-- SELECT
--   id,
--   email,
--   first_name,
--   last_name,
--   country,
--   user_type,
--   language,
--   created_at
-- FROM public.users
-- ORDER BY created_at DESC
-- LIMIT 5;

-- ================================================================
-- 🎉 C'EST FAIT!
-- ================================================================
-- Le trigger handle_new_user() va maintenant :
-- ✅ Extraire first_name, last_name, country depuis raw_user_meta_data
-- ✅ Sauvegarder tous les champs du profil dans public.users
-- ✅ Empêcher la perte de données lors de l'inscription
--
-- NOTE IMPORTANTE:
-- Les utilisateurs créés AVANT cette correction auront des champs vides.
-- Pour les corriger, vous pouvez exécuter une migration de données
-- qui lit raw_user_meta_data de auth.users et met à jour public.users.
-- ================================================================
