-- ============================================================================
-- RESTAURER le quota normal du plan FREE après les tests
-- Date: 2025-01-18
-- Description: Remet le quota FREE à 100 questions/mois (valeur normale)
-- ============================================================================

-- Restaurer le quota du plan FREE à 100
UPDATE billing_plans
SET monthly_quota = 100
WHERE plan_name = 'free';

-- Mettre à jour aussi le tracking mensuel pour les utilisateurs FREE existants
UPDATE monthly_usage_tracking
SET monthly_quota = 100
WHERE user_email IN (
    SELECT user_email
    FROM stripe_subscriptions
    WHERE plan_name = 'free'
    AND status = 'active'
)
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
AND monthly_quota = 3; -- Seulement ceux qui ont 3 (tests)

-- Vérification
SELECT
    'billing_plans' as source,
    plan_name,
    monthly_quota::text || ' questions' as quota,
    'N/A' as month
FROM billing_plans
WHERE plan_name = 'free'

UNION ALL

SELECT
    'monthly_usage_tracking' as source,
    user_email,
    monthly_quota::text || ' questions' as quota,
    month_year
FROM monthly_usage_tracking
WHERE user_email IN (
    SELECT user_email
    FROM stripe_subscriptions
    WHERE plan_name = 'free'
    AND status = 'active'
)
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
ORDER BY source, quota;

-- Message de confirmation
DO $$
DECLARE
    users_updated INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_updated
    FROM monthly_usage_tracking
    WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
    AND monthly_quota = 100
    AND user_email IN (
        SELECT user_email
        FROM stripe_subscriptions
        WHERE plan_name = 'free'
        AND status = 'active'
    );

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ Quota du plan FREE restauré à 100 questions/mois';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Utilisateurs mis à jour: %', users_updated;
    RAISE NOTICE '✨ Le plan FREE est maintenant à sa valeur normale';
    RAISE NOTICE '========================================';
END $$;
