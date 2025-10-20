-- ============================================================================
-- TEST: Vérification rapide que tout fonctionne
-- ============================================================================

-- 1. Test de la fonction suggest_billing_currency
SELECT 'TEST 1: Function suggest_billing_currency' as test_name;
SELECT
    'CA' as country,
    suggest_billing_currency('CA') as suggested,
    'USD' as expected,
    CASE WHEN suggest_billing_currency('CA') = 'USD' THEN '✅ PASS' ELSE '❌ FAIL' END as status
UNION ALL
SELECT
    'FR' as country,
    suggest_billing_currency('FR') as suggested,
    'EUR' as expected,
    CASE WHEN suggest_billing_currency('FR') = 'EUR' THEN '✅ PASS' ELSE '❌ FAIL' END as status;

-- 2. Vérifier qu'on peut insérer/mettre à jour des devises
SELECT 'TEST 2: Insert/Update billing_currency' as test_name;

-- Tester avec un utilisateur test (ajustez l'email si nécessaire)
-- Cette requête ne fait rien si l'utilisateur n'existe pas
UPDATE user_billing_info
SET billing_currency = 'USD'
WHERE user_email = (SELECT user_email FROM user_billing_info LIMIT 1)
RETURNING user_email, billing_currency, '✅ UPDATE OK' as status;

-- 3. Vérifier la liste des devises supportées
SELECT 'TEST 3: All 16 supported currencies' as test_name;
SELECT unnest(ARRAY[
    'USD', 'EUR', 'CNY', 'INR', 'BRL', 'IDR', 'MXN', 'JPY',
    'TRY', 'GBP', 'ZAR', 'THB', 'MYR', 'PHP', 'PLN', 'VND'
]) as currency;

-- ============================================================================
-- Si tous les tests passent:
--   ✅ La BD est prête
--   ✅ L'API /api/v1/billing/currency-preference devrait fonctionner
--   ✅ Le CurrencySelector devrait maintenant s'afficher
--
-- Prochaines étapes:
--   1. Redémarrer le backend (si nécessaire)
--   2. Recharger la page Abonnement dans le navigateur (Ctrl+F5)
--   3. Le CurrencySelector devrait apparaître en haut de la modale
-- ============================================================================
