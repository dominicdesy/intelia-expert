-- ============================================================================
-- Ajouter un abonnement Essential pour dominic.desy@icloud.com
-- Date: 2025-01-18
-- Description: Crée un abonnement Essential actif pour les tests
-- ============================================================================

-- 0. Créer ou mettre à jour l'entrée user_billing_info (OBLIGATOIRE pour foreign key)
INSERT INTO user_billing_info (
    user_email,
    plan_name,
    custom_monthly_quota,
    quota_enforcement,
    billing_enabled,
    created_at,
    updated_at
)
VALUES (
    'dominic.desy@icloud.com',
    'essential',
    NULL, -- Utilisera la valeur de billing_plans
    TRUE, -- Activer l'enforcement des quotas
    TRUE, -- Activer la facturation
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (user_email) DO UPDATE
SET
    plan_name = 'essential',
    quota_enforcement = TRUE,
    billing_enabled = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- 1. Vérifier si l'utilisateur a déjà un customer Stripe
DO $$
DECLARE
    customer_exists BOOLEAN;
    customer_id VARCHAR(255);
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM stripe_customers WHERE user_email = 'dominic.desy@icloud.com'
    ) INTO customer_exists;

    IF customer_exists THEN
        SELECT stripe_customer_id INTO customer_id
        FROM stripe_customers
        WHERE user_email = 'dominic.desy@icloud.com';
        RAISE NOTICE 'Customer Stripe existant: %', customer_id;
    ELSE
        RAISE NOTICE 'Aucun customer Stripe trouvé, création en cours...';
    END IF;
END $$;

-- 2. Créer ou mettre à jour le customer Stripe
INSERT INTO stripe_customers (
    user_email,
    stripe_customer_id,
    customer_name,
    country_code,
    currency,
    created_at,
    updated_at
)
VALUES (
    'dominic.desy@icloud.com',
    'cus_test_' || substring(md5(random()::text), 1, 14), -- ID test unique
    'Dominic Desy',
    'CA',
    'CAD',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (user_email) DO UPDATE
SET updated_at = CURRENT_TIMESTAMP;

-- 3. Supprimer tout ancien abonnement actif (si existant)
UPDATE stripe_subscriptions
SET
    status = 'canceled',
    canceled_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active';

-- 4. Créer le nouvel abonnement Essential
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
    cancel_at_period_end,
    created_at,
    updated_at
)
SELECT
    'dominic.desy@icloud.com',
    'sub_test_' || substring(md5(random()::text), 1, 14), -- ID test unique
    sc.stripe_customer_id,
    'essential',
    'CA',
    0.00,
    'CAD',
    'active',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP + INTERVAL '1 month',
    FALSE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM stripe_customers sc
WHERE sc.user_email = 'dominic.desy@icloud.com'
ON CONFLICT (stripe_subscription_id) DO NOTHING;

-- 5. Créer ou mettre à jour le tracking mensuel
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
    warning_sent,
    last_question_at,
    created_at,
    updated_at
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
    FALSE,
    NULL,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (user_email, month_year) DO UPDATE
SET
    monthly_quota = 3,
    current_status = 'active',
    updated_at = CURRENT_TIMESTAMP;

-- 6. Vérifier le résultat complet
SELECT
    '=== USER BILLING INFO ===' as section,
    user_email,
    plan_name,
    COALESCE(custom_monthly_quota::text, 'NULL (from billing_plans)') as quota,
    quota_enforcement::text as enforcement
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    '=== CUSTOMER ===' as section,
    user_email,
    stripe_customer_id,
    country_code,
    currency
FROM stripe_customers
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    '=== SUBSCRIPTION ===' as section,
    user_email,
    stripe_subscription_id,
    plan_name || ' (' || status || ')' as quota,
    'Expires: ' || current_period_end::date::text as enforcement
FROM stripe_subscriptions
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active'

UNION ALL

SELECT
    '=== USAGE TRACKING ===' as section,
    user_email,
    month_year,
    questions_used || '/' || monthly_quota as quota,
    current_status as enforcement
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- Afficher un message de confirmation
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ Abonnement Essential créé pour dominic.desy@icloud.com';
    RAISE NOTICE '📊 Plan: Essential (gratuit)';
    RAISE NOTICE '📈 Quota: 3 questions/mois (test - normalement 50)';
    RAISE NOTICE '🗓️  Période: 1 mois';
    RAISE NOTICE '✨ Statut: Active';
    RAISE NOTICE '';
END $$;
