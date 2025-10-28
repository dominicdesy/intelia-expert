-- ============================================================================
-- SCRIPT COMPLET: Créer le plan Essential + abonnement pour dominic.desy@icloud.com
-- Date: 2025-01-18
-- Description: Version finale qui crée TOUT ce qui manque
-- ============================================================================

-- ÉTAPE 0A: Créer le plan "essential" dans billing_plans s'il n'existe pas
INSERT INTO billing_plans (
    plan_name,
    display_name,
    monthly_quota,
    price_per_month,
    active
)
VALUES (
    'essential',
    'Essential',
    3, -- Quota de test (normalement 50)
    0.00,
    TRUE
)
ON CONFLICT (plan_name)
DO UPDATE SET
    monthly_quota = 3, -- Mise à jour temporaire pour tests
    active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ÉTAPE 0B: Créer l'entrée user_billing_info
INSERT INTO user_billing_info (user_email, plan_name, quota_enforcement, billing_enabled)
VALUES ('dominic.desy@icloud.com', 'essential', TRUE, TRUE)
ON CONFLICT (user_email)
DO UPDATE SET
    plan_name = 'essential',
    quota_enforcement = TRUE,
    billing_enabled = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ÉTAPE 1: Créer ou mettre à jour le customer Stripe
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
    currency = 'CAD',
    updated_at = CURRENT_TIMESTAMP;

-- ÉTAPE 2: Annuler les anciens abonnements actifs
UPDATE stripe_subscriptions
SET
    status = 'canceled',
    canceled_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active';

-- ÉTAPE 3: Créer le nouvel abonnement Essential
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
    'essential',
    'CA',
    0.00,
    'CAD',
    'active',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP + INTERVAL '1 month',
    FALSE
FROM stripe_customers sc
WHERE sc.user_email = 'dominic.desy@icloud.com';

-- ÉTAPE 4: Créer ou mettre à jour le tracking mensuel
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
    3, -- Quota de test (normalement 50)
    'active',
    FALSE
)
ON CONFLICT (user_email, month_year)
DO UPDATE SET
    monthly_quota = 3,
    current_status = 'active',
    updated_at = CURRENT_TIMESTAMP;

-- ÉTAPE 5: Vérification finale
SELECT '=== RÉSUMÉ ===' as section;

SELECT
    '1. BILLING_PLANS' as check_name,
    CASE WHEN COUNT(*) > 0 THEN '✅ OK' ELSE '❌ MANQUANT' END as status
FROM billing_plans
WHERE plan_name = 'essential'

UNION ALL

SELECT
    '2. USER_BILLING_INFO',
    CASE WHEN COUNT(*) > 0 THEN '✅ OK' ELSE '❌ MANQUANT' END
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    '3. STRIPE_CUSTOMERS',
    CASE WHEN COUNT(*) > 0 THEN '✅ OK' ELSE '❌ MANQUANT' END
FROM stripe_customers
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    '4. STRIPE_SUBSCRIPTIONS',
    CASE WHEN COUNT(*) > 0 THEN '✅ OK (actif)' ELSE '❌ MANQUANT' END
FROM stripe_subscriptions
WHERE user_email = 'dominic.desy@icloud.com' AND status = 'active'

UNION ALL

SELECT
    '5. MONTHLY_USAGE_TRACKING',
    CASE WHEN COUNT(*) > 0 THEN '✅ OK' ELSE '❌ MANQUANT' END
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- Afficher les détails complets
SELECT '=== DÉTAILS ===' as section;

SELECT
    'billing_plans' as table_name,
    plan_name as col1,
    display_name as col2,
    monthly_quota::text as col3,
    price_per_month::text || ' $' as col4
FROM billing_plans
WHERE plan_name = 'essential'

UNION ALL

SELECT
    'user_billing_info',
    user_email,
    plan_name,
    COALESCE(custom_monthly_quota::text, 'NULL (from plan)'),
    quota_enforcement::text
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    'stripe_customers',
    user_email,
    stripe_customer_id,
    country_code,
    currency
FROM stripe_customers
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    'stripe_subscriptions',
    user_email,
    stripe_subscription_id,
    plan_name,
    status
FROM stripe_subscriptions
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active'

UNION ALL

SELECT
    'monthly_usage_tracking',
    user_email,
    month_year,
    questions_used || '/' || monthly_quota,
    current_status
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- Message final
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ ABONNEMENT ESSENTIAL CRÉÉ AVEC SUCCÈS';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Email: dominic.desy@icloud.com';
    RAISE NOTICE 'Plan: Essential (gratuit)';
    RAISE NOTICE 'Quota: 3 questions/mois (test)';
    RAISE NOTICE 'Statut: Active';
    RAISE NOTICE '========================================';
END $$;
