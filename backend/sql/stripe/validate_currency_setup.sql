-- ============================================================================
-- VALIDATION: Currency Setup Diagnostic Script
-- Exécutez ces commandes pour vérifier si le système de devises est configuré
-- ============================================================================

-- 1. Vérifier si la colonne billing_currency existe
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_billing_info'
  AND column_name = 'billing_currency';

-- Résultat attendu:
-- column_name: billing_currency
-- data_type: character varying
-- is_nullable: YES
-- Si AUCUNE ligne → La colonne n'existe PAS (migration 24 pas exécutée)


-- 2. Vérifier si la fonction suggest_billing_currency existe
SELECT
    proname as function_name,
    pg_get_function_arguments(oid) as arguments,
    pg_get_functiondef(oid) as definition_preview
FROM pg_proc
WHERE proname = 'suggest_billing_currency';

-- Résultat attendu:
-- function_name: suggest_billing_currency
-- arguments: p_country_code character varying
-- Si AUCUNE ligne → La fonction n'existe PAS (migration 24 pas exécutée)


-- 3. Tester la fonction avec quelques pays
SELECT
    'Canada (CA)' as test_case,
    suggest_billing_currency('CA') as suggested_currency,
    'USD' as expected
UNION ALL
SELECT
    'France (FR)',
    suggest_billing_currency('FR'),
    'EUR'
UNION ALL
SELECT
    'United States (US)',
    suggest_billing_currency('US'),
    'USD'
UNION ALL
SELECT
    'China (CN)',
    suggest_billing_currency('CN'),
    'CNY';

-- Si erreur "function suggest_billing_currency does not exist"
-- → La migration 24 n'a PAS été exécutée


-- 4. Vérifier l'index sur billing_currency
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'user_billing_info'
  AND indexname = 'idx_user_billing_currency';

-- Résultat attendu:
-- indexname: idx_user_billing_currency
-- Si AUCUNE ligne → Index manquant (migration 24 pas complète)


-- 5. Vérifier la contrainte CHECK sur billing_currency
SELECT
    con.conname as constraint_name,
    pg_get_constraintdef(con.oid) as constraint_definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
WHERE rel.relname = 'user_billing_info'
  AND con.conname LIKE '%billing_currency%';

-- Résultat attendu:
-- constraint_name contenant "billing_currency"
-- constraint_definition: CHECK billing_currency IN ('USD', 'EUR', ...)


-- 6. Compter les utilisateurs avec/sans devise
SELECT
    COUNT(*) as total_users,
    COUNT(billing_currency) as users_with_currency,
    COUNT(*) - COUNT(billing_currency) as users_without_currency,
    COUNT(*) FILTER (WHERE billing_currency IS NULL AND plan_name != 'essential') as paid_users_without_currency
FROM user_billing_info;

-- Résultat attendu:
-- total_users: nombre total d'utilisateurs
-- users_with_currency: utilisateurs ayant choisi une devise
-- users_without_currency: utilisateurs sans devise (normal au début)


-- 7. Distribution des devises actuellement sélectionnées
SELECT
    billing_currency,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) as percentage
FROM user_billing_info
WHERE billing_currency IS NOT NULL
GROUP BY billing_currency
ORDER BY user_count DESC;

-- Résultat: distribution des devises choisies par les utilisateurs


-- ============================================================================
-- DIAGNOSTIC SUMMARY
-- ============================================================================
-- Si TOUTES les requêtes ci-dessus retournent des résultats attendus:
--   ✅ La BD est correctement configurée
--
-- Si les requêtes 1-2 retournent AUCUNE ligne:
--   ❌ La migration 24_add_billing_currency_preference.sql n'a PAS été exécutée
--   → Exécuter: psql <DATABASE_URL> -f backend/sql/stripe/24_add_billing_currency_preference.sql
--
-- Si la requête 3 retourne une erreur "function does not exist":
--   ❌ La fonction suggest_billing_currency n'existe pas
--   → Exécuter: psql <DATABASE_URL> -f backend/sql/stripe/24_add_billing_currency_preference.sql
-- ============================================================================
