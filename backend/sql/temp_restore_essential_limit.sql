-- ============================================================================
-- SCRIPT: Restaurer la limite Essential à 50 questions (valeur normale)
-- Date: 2025-01-18
-- Description: Restaure le quota normal de 50 questions après les tests
-- ============================================================================

-- 1. Restaurer la table billing_plans
UPDATE billing_plans
SET monthly_quota = 50
WHERE plan_name = 'essential';

-- 2. Restaurer tous les enregistrements monthly_usage_tracking existants
--    pour le mois en cours avec la limite normale
UPDATE monthly_usage_tracking
SET monthly_quota = 50
WHERE user_email IN (
    SELECT user_email
    FROM stripe_subscriptions
    WHERE plan_name = 'essential'
    AND status = 'active'
)
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- 3. Restaurer aussi les utilisateurs sans abonnement actif mais qui ont un tracking à 3
--    (pour couvrir tous les cas de test)
UPDATE monthly_usage_tracking
SET monthly_quota = 50
WHERE monthly_quota = 3
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- 4. Vérifier la restauration
SELECT
    'billing_plans' as source,
    plan_name as identifier,
    monthly_quota::text as quota,
    'N/A' as month
FROM billing_plans
WHERE plan_name = 'essential'

UNION ALL

SELECT
    'monthly_usage_tracking' as source,
    user_email as identifier,
    monthly_quota::text as quota,
    month_year as month
FROM monthly_usage_tracking
WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
AND monthly_quota = 50
ORDER BY source, identifier
LIMIT 10;

-- Afficher un message de confirmation
DO $$
DECLARE
    users_restored INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_restored
    FROM monthly_usage_tracking
    WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
    AND monthly_quota = 50;

    RAISE NOTICE '✅ Limite Essential restaurée à 50 questions';
    RAISE NOTICE '📊 Utilisateurs restaurés: %', users_restored;
    RAISE NOTICE '✨ Tous les utilisateurs Essential ont maintenant 50 questions/mois';
END $$;
