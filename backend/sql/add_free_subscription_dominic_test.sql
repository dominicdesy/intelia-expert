-- ============================================================================
-- Attribuer le plan FREE à dominic.desy@icloud.com avec quota de test (3 questions)
-- Date: 2025-01-18
-- Description: Utilise le plan "free" existant et réduit temporairement le quota à 3
-- ============================================================================

-- ÉTAPE 1: Réduire temporairement le quota du plan FREE à 3 pour tests
UPDATE billing_plans
SET monthly_quota = 3
WHERE plan_name = 'free';

-- ÉTAPE 2: Créer l'entrée user_billing_info
INSERT INTO user_billing_info (user_email, plan_name, quota_enforcement, billing_enabled)
VALUES ('dominic.desy@icloud.com', 'free', TRUE, TRUE)
ON CONFLICT (user_email)
DO UPDATE SET
    plan_name = 'free',
    quota_enforcement = TRUE,
    billing_enabled = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ÉTAPE 3: Créer ou mettre à jour le customer Stripe
INSERT INTO stripe_customers (
    user_email,
    stripe_customer_id,
    customer_name,
    country_code,
    currency
)
VALUES (
    'dominic.desy@icloud.com',
    'cus_test_' || substring(md5(random()::text || CURRENT_TIMESTAMP::text), 1, 14),
    'Dominic Desy',
    'CA',
    'CAD'
)
ON CONFLICT (user_email)
DO UPDATE SET
    country_code = 'CA',
    currency = 'CAD';

-- ÉTAPE 4: Annuler les anciens abonnements actifs
UPDATE stripe_subscriptions
SET
    status = 'canceled',
    canceled_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active';

-- ÉTAPE 5: Créer le nouvel abonnement FREE
INSERT INTO stripe_subscriptions (
    user_email,
    stripe_subscription_id,
    stripe_customer_id,
    plan_name,
    region_code,
    price_monthly,
    currency,
    status,
    current_period_start,
    current_period_end,
    cancel_at_period_end
)
SELECT
    'dominic.desy@icloud.com',
    'sub_test_' || substring(md5(random()::text || CURRENT_TIMESTAMP::text), 1, 14),
    sc.stripe_customer_id,
    'free',
    'CA',
    0.00,
    'CAD',
    'active',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP + INTERVAL '1 month',
    FALSE
FROM stripe_customers sc
WHERE sc.user_email = 'dominic.desy@icloud.com';

-- ÉTAPE 6: Créer ou mettre à jour le tracking mensuel
INSERT INTO monthly_usage_tracking (
    user_email,
    month_year,
    questions_used,
    questions_successful,
    questions_failed,
    total_cost_usd,
    openai_cost_usd,
    monthly_quota,
    current_status,
    warning_sent
)
VALUES (
    'dominic.desy@icloud.com',
    TO_CHAR(CURRENT_DATE, 'YYYY-MM'),
    0,
    0,
    0,
    0.00,
    0.00,
    3, -- Quota de test
    'active',
    FALSE
)
ON CONFLICT (user_email, month_year)
DO UPDATE SET
    monthly_quota = 3,
    questions_used = 0,
    current_status = 'active';

-- ÉTAPE 7: Vérification finale
SELECT '========================================' as result
UNION ALL SELECT '✅ VÉRIFICATION COMPLÈTE'
UNION ALL SELECT '========================================'
UNION ALL SELECT '';

SELECT
    check_name,
    status
FROM (
    SELECT '1. BILLING_PLANS (free)' as check_name,
           CASE WHEN COUNT(*) > 0 THEN '✅ OK - Quota: ' || MAX(monthly_quota)::text ELSE '❌ MANQUANT' END as status
    FROM billing_plans WHERE plan_name = 'free'

    UNION ALL

    SELECT '2. USER_BILLING_INFO',
           CASE WHEN COUNT(*) > 0 THEN '✅ OK - Plan: ' || MAX(plan_name) ELSE '❌ MANQUANT' END
    FROM user_billing_info WHERE user_email = 'dominic.desy@icloud.com'

    UNION ALL

    SELECT '3. STRIPE_CUSTOMERS',
           CASE WHEN COUNT(*) > 0 THEN '✅ OK - ID: ' || MAX(stripe_customer_id) ELSE '❌ MANQUANT' END
    FROM stripe_customers WHERE user_email = 'dominic.desy@icloud.com'

    UNION ALL

    SELECT '4. STRIPE_SUBSCRIPTIONS',
           CASE WHEN COUNT(*) > 0 THEN '✅ OK - Status: ' || MAX(status) ELSE '❌ MANQUANT' END
    FROM stripe_subscriptions
    WHERE user_email = 'dominic.desy@icloud.com' AND status = 'active'

    UNION ALL

    SELECT '5. MONTHLY_USAGE_TRACKING',
           CASE WHEN COUNT(*) > 0 THEN '✅ OK - Usage: ' || MAX(questions_used)::text || '/' || MAX(monthly_quota)::text ELSE '❌ MANQUANT' END
    FROM monthly_usage_tracking
    WHERE user_email = 'dominic.desy@icloud.com'
    AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
) checks;

-- Afficher les détails complets
SELECT '' as separator
UNION ALL SELECT '========================================'
UNION ALL SELECT '📊 DÉTAILS COMPLETS'
UNION ALL SELECT '========================================'
UNION ALL SELECT '';

SELECT
    'billing_plans' as table_name,
    plan_name as col1,
    display_name as col2,
    monthly_quota::text || ' questions' as col3,
    price_per_month::text || ' $' as col4
FROM billing_plans
WHERE plan_name = 'free'

UNION ALL SELECT '---', '---', '---', '---', '---'

UNION ALL

SELECT
    'user_billing_info',
    user_email,
    plan_name,
    COALESCE(custom_monthly_quota::text, 'from billing_plans'),
    'enforcement: ' || quota_enforcement::text
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL SELECT '---', '---', '---', '---', '---'

UNION ALL

SELECT
    'stripe_subscriptions',
    user_email,
    LEFT(stripe_subscription_id, 20) || '...',
    plan_name,
    status
FROM stripe_subscriptions
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active'

UNION ALL SELECT '---', '---', '---', '---', '---'

UNION ALL

SELECT
    'monthly_usage_tracking',
    user_email,
    month_year,
    questions_used || '/' || monthly_quota || ' questions',
    current_status
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- Message final
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ CONFIGURATION TERMINÉE AVEC SUCCÈS';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Email: dominic.desy@icloud.com';
    RAISE NOTICE 'Plan: FREE (gratuit)';
    RAISE NOTICE 'Quota: 3 questions/mois (TEST)';
    RAISE NOTICE 'Statut: Active';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  RAPPEL IMPORTANT:';
    RAISE NOTICE 'Le quota du plan FREE a été réduit à 3 pour TOUS les utilisateurs FREE!';
    RAISE NOTICE 'Après les tests, restaurez à 100 avec:';
    RAISE NOTICE '  UPDATE billing_plans SET monthly_quota = 100 WHERE plan_name = ''free'';';
    RAISE NOTICE '========================================';
END $$;
