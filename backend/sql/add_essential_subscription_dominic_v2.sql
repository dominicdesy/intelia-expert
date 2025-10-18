-- ============================================================================
-- Ajouter un abonnement Essential pour dominic.desy@icloud.com (VERSION 2)
-- Date: 2025-01-18
-- Description: Version robuste avec gestion complète des erreurs
-- ============================================================================

-- Étape 0a: Vérifier si user_billing_info existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_billing_info') THEN
        RAISE EXCEPTION 'Table user_billing_info n''existe pas !';
    END IF;
    RAISE NOTICE '✓ Table user_billing_info trouvée';
END $$;

-- Étape 0b: Créer l'entrée user_billing_info
DO $$
BEGIN
    -- Vérifier si l'utilisateur existe déjà
    IF EXISTS (SELECT 1 FROM user_billing_info WHERE user_email = 'dominic.desy@icloud.com') THEN
        RAISE NOTICE '→ Utilisateur existe déjà dans user_billing_info, mise à jour...';

        UPDATE user_billing_info
        SET
            plan_name = 'essential',
            quota_enforcement = TRUE,
            billing_enabled = TRUE,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_email = 'dominic.desy@icloud.com';

        RAISE NOTICE '✓ Utilisateur mis à jour dans user_billing_info';
    ELSE
        RAISE NOTICE '→ Création de l''utilisateur dans user_billing_info...';

        -- Insérer le nouvel utilisateur
        INSERT INTO user_billing_info (
            user_email,
            plan_name,
            quota_enforcement,
            billing_enabled,
            created_at,
            updated_at
        )
        VALUES (
            'dominic.desy@icloud.com',
            'essential',
            TRUE,
            TRUE,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );

        RAISE NOTICE '✓ Utilisateur créé dans user_billing_info';
    END IF;

    -- Vérifier que l'insertion a réussi
    IF NOT EXISTS (SELECT 1 FROM user_billing_info WHERE user_email = 'dominic.desy@icloud.com') THEN
        RAISE EXCEPTION 'Échec de l''insertion dans user_billing_info !';
    END IF;
END $$;

-- Étape 1: Créer ou mettre à jour le customer Stripe
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
    'cus_test_' || substring(md5(random()::text || CURRENT_TIMESTAMP::text), 1, 14),
    'Dominic Desy',
    'CA',
    'CAD',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (user_email)
DO UPDATE SET
    updated_at = CURRENT_TIMESTAMP,
    country_code = 'CA',
    currency = 'CAD';

-- Étape 2: Annuler les anciens abonnements actifs
UPDATE stripe_subscriptions
SET
    status = 'canceled',
    canceled_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active';

-- Étape 3: Créer le nouvel abonnement Essential
DO $$
DECLARE
    v_customer_id VARCHAR(255);
    v_subscription_id VARCHAR(255);
BEGIN
    -- Récupérer le customer_id
    SELECT stripe_customer_id INTO v_customer_id
    FROM stripe_customers
    WHERE user_email = 'dominic.desy@icloud.com';

    IF v_customer_id IS NULL THEN
        RAISE EXCEPTION 'Customer Stripe introuvable pour dominic.desy@icloud.com';
    END IF;

    RAISE NOTICE '→ Customer ID: %', v_customer_id;

    -- Générer un ID unique pour l'abonnement
    v_subscription_id := 'sub_test_' || substring(md5(random()::text || CURRENT_TIMESTAMP::text), 1, 14);

    -- Insérer l'abonnement
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
    VALUES (
        'dominic.desy@icloud.com',
        v_subscription_id,
        v_customer_id,
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
    );

    RAISE NOTICE '✓ Abonnement créé: %', v_subscription_id;
END $$;

-- Étape 4: Créer ou mettre à jour le tracking mensuel
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
ON CONFLICT (user_email, month_year)
DO UPDATE SET
    monthly_quota = 3,
    current_status = 'active',
    updated_at = CURRENT_TIMESTAMP;

-- Étape 5: Vérification complète
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'VÉRIFICATION COMPLÈTE';
    RAISE NOTICE '========================================';

    -- Vérifier user_billing_info
    SELECT COUNT(*) INTO v_count FROM user_billing_info WHERE user_email = 'dominic.desy@icloud.com';
    IF v_count > 0 THEN
        RAISE NOTICE '✅ user_billing_info: OK';
    ELSE
        RAISE EXCEPTION '❌ user_billing_info: MANQUANT';
    END IF;

    -- Vérifier stripe_customers
    SELECT COUNT(*) INTO v_count FROM stripe_customers WHERE user_email = 'dominic.desy@icloud.com';
    IF v_count > 0 THEN
        RAISE NOTICE '✅ stripe_customers: OK';
    ELSE
        RAISE EXCEPTION '❌ stripe_customers: MANQUANT';
    END IF;

    -- Vérifier stripe_subscriptions
    SELECT COUNT(*) INTO v_count FROM stripe_subscriptions
    WHERE user_email = 'dominic.desy@icloud.com' AND status = 'active';
    IF v_count > 0 THEN
        RAISE NOTICE '✅ stripe_subscriptions: OK (actif)';
    ELSE
        RAISE EXCEPTION '❌ stripe_subscriptions: MANQUANT ou inactif';
    END IF;

    -- Vérifier monthly_usage_tracking
    SELECT COUNT(*) INTO v_count FROM monthly_usage_tracking
    WHERE user_email = 'dominic.desy@icloud.com'
    AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
    IF v_count > 0 THEN
        RAISE NOTICE '✅ monthly_usage_tracking: OK';
    ELSE
        RAISE EXCEPTION '❌ monthly_usage_tracking: MANQUANT';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '🎉 SUCCÈS COMPLET !';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Plan: Essential (gratuit)';
    RAISE NOTICE 'Quota: 3 questions/mois (test)';
    RAISE NOTICE 'Statut: Active';
    RAISE NOTICE '========================================';
END $$;

-- Afficher les données
SELECT
    '1. USER_BILLING_INFO' as table_name,
    user_email as col1,
    plan_name as col2,
    quota_enforcement::text as col3,
    billing_enabled::text as col4
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    '2. STRIPE_CUSTOMERS' as table_name,
    user_email,
    stripe_customer_id,
    country_code,
    currency
FROM stripe_customers
WHERE user_email = 'dominic.desy@icloud.com'

UNION ALL

SELECT
    '3. STRIPE_SUBSCRIPTIONS' as table_name,
    user_email,
    stripe_subscription_id,
    plan_name || ' (' || status || ')' as col3,
    'Expires: ' || current_period_end::date::text as col4
FROM stripe_subscriptions
WHERE user_email = 'dominic.desy@icloud.com'
AND status = 'active'

UNION ALL

SELECT
    '4. MONTHLY_USAGE_TRACKING' as table_name,
    user_email,
    month_year,
    questions_used || '/' || monthly_quota as col3,
    current_status as col4
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
