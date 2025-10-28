-- ============================================================================
-- Attribuer le plan FREE à dominic.desy@icloud.com avec quota de 3 (VERSION SAFE)
-- Date: 2025-01-18
-- Description: Version sans updated_at pour éviter les erreurs de colonnes
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
    billing_enabled = TRUE;

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

-- ÉTAPE 4: Annuler les anciens abonnements actifs (si existants)
UPDATE stripe_subscriptions
SET
    status = 'canceled',
    canceled_at = CURRENT_TIMESTAMP
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
    3,
    'active',
    FALSE
)
ON CONFLICT (user_email, month_year)
DO UPDATE SET
    monthly_quota = 3,
    questions_used = 0,
    current_status = 'active';

-- ÉTAPE 7: Vérification finale avec résultats clairs
DO $$
DECLARE
    v_billing_plan INTEGER;
    v_user_billing INTEGER;
    v_stripe_customer INTEGER;
    v_stripe_sub INTEGER;
    v_tracking INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_billing_plan FROM billing_plans WHERE plan_name = 'free' AND monthly_quota = 3;
    SELECT COUNT(*) INTO v_user_billing FROM user_billing_info WHERE user_email = 'dominic.desy@icloud.com';
    SELECT COUNT(*) INTO v_stripe_customer FROM stripe_customers WHERE user_email = 'dominic.desy@icloud.com';
    SELECT COUNT(*) INTO v_stripe_sub FROM stripe_subscriptions WHERE user_email = 'dominic.desy@icloud.com' AND status = 'active';
    SELECT COUNT(*) INTO v_tracking FROM monthly_usage_tracking WHERE user_email = 'dominic.desy@icloud.com' AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'VÉRIFICATION COMPLÈTE';
    RAISE NOTICE '========================================';

    IF v_billing_plan > 0 THEN
        RAISE NOTICE '✅ billing_plans: OK (quota = 3)';
    ELSE
        RAISE NOTICE '❌ billing_plans: ERREUR';
    END IF;

    IF v_user_billing > 0 THEN
        RAISE NOTICE '✅ user_billing_info: OK';
    ELSE
        RAISE NOTICE '❌ user_billing_info: MANQUANT';
    END IF;

    IF v_stripe_customer > 0 THEN
        RAISE NOTICE '✅ stripe_customers: OK';
    ELSE
        RAISE NOTICE '❌ stripe_customers: MANQUANT';
    END IF;

    IF v_stripe_sub > 0 THEN
        RAISE NOTICE '✅ stripe_subscriptions: OK (actif)';
    ELSE
        RAISE NOTICE '❌ stripe_subscriptions: MANQUANT';
    END IF;

    IF v_tracking > 0 THEN
        RAISE NOTICE '✅ monthly_usage_tracking: OK (0/3)';
    ELSE
        RAISE NOTICE '❌ monthly_usage_tracking: MANQUANT';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ CONFIGURATION TERMINÉE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Email: dominic.desy@icloud.com';
    RAISE NOTICE 'Plan: FREE';
    RAISE NOTICE 'Quota: 3 questions/mois (TEST)';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  RAPPEL: Restaurer après tests avec:';
    RAISE NOTICE 'psql -f restore_free_plan_quota.sql';
    RAISE NOTICE '========================================';
END $$;

-- Afficher les données créées
SELECT
    'billing_plans' as table_name,
    plan_name,
    monthly_quota::text || ' questions',
    price_per_month::text || ' $',
    active::text
FROM billing_plans
WHERE plan_name = 'free'

UNION ALL

SELECT
    'user_billing_info',
    user_email,
    plan_name,
    quota_enforcement::text,
    billing_enabled::text
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    'stripe_subscriptions',
    user_email,
    plan_name,
    status,
    current_period_end::date::text
FROM stripe_subscriptions
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active'

UNION ALL

SELECT
    'monthly_usage_tracking',
    user_email,
    month_year,
    questions_used::text || '/' || monthly_quota::text,
    current_status
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
