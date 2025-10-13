-- ================================================================
-- 🔒 FIX SUPABASE SECURITY WARNINGS
-- ================================================================
-- Ce script corrige 3 warnings de sécurité en ajoutant SET search_path = ''
-- aux fonctions pour prévenir les attaques par search path injection.
--
-- ✅ PRÊT À EXÉCUTER - Aucune modification nécessaire
-- ✅ Zéro downtime - Les fonctions sont remplacées atomiquement
-- ✅ Zéro changement fonctionnel - Seulement l'ajout de sécurité
--
-- INSTRUCTIONS:
-- 1. Ouvrez Supabase Dashboard → SQL Editor
-- 2. Copiez-collez ce fichier complet
-- 3. Cliquez sur "Run" (ou F5)
-- 4. Vérifiez que les 3 fonctions sont affichées dans les résultats
-- 5. Retournez dans Database → Linter pour vérifier que les warnings
--    sont résolus
-- ================================================================

-- Fix 1: handle_new_user
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

-- Fix 2: notify_user_created
CREATE OR REPLACE FUNCTION public.notify_user_created()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  request_id bigint;
BEGIN
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

-- Fix 3: update_updated_at_column
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
-- ✅ VÉRIFICATION
-- ================================================================
-- Cette requête affiche les fonctions avec leur search_path configuré.
-- Vous devriez voir "{\"SET search_path = ''\"}" pour chaque fonction.

SELECT
  proname AS "Fonction",
  CASE
    WHEN proconfig IS NULL THEN '❌ Non sécurisé'
    ELSE '✅ Sécurisé: ' || array_to_string(proconfig, ', ')
  END AS "Statut"
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('handle_new_user', 'notify_user_created', 'update_updated_at_column')
ORDER BY proname;

-- ================================================================
-- 🎉 C'EST FAIT!
-- ================================================================
-- Si vous voyez 3 fonctions avec "✅ Sécurisé" ci-dessus,
-- les corrections sont appliquées avec succès.
--
-- Prochaine étape:
-- Database → Linter → Vérifier que les warnings ont disparu
-- ================================================================
