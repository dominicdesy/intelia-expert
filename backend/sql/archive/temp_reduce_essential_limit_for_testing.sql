-- ============================================================================
-- SCRIPT TEMPORAIRE: Réduire la limite Essential à 3 questions pour tests
-- Date: 2025-01-18
-- Description: Réduit temporairement le quota de 50 à 3 pour faciliter les tests
-- IMPORTANT: À ANNULER APRÈS LES TESTS avec temp_restore_essential_limit.sql
-- ============================================================================

-- 1. Mettre à jour la table billing_plans
UPDATE billing_plans
SET monthly_quota = 3
WHERE plan_name = 'essential';

-- 2. Mettre à jour tous les enregistrements monthly_usage_tracking existants
--    pour le mois en cours avec la nouvelle limite
UPDATE monthly_usage_tracking
SET monthly_quota = 3
WHERE user_email IN (
    SELECT user_email
    FROM stripe_subscriptions
    WHERE plan_name = 'essential'
    AND status = 'active'
)
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- 3. Mettre à jour aussi les utilisateurs sans abonnement actif mais qui ont un tracking
--    (pour couvrir tous les cas)
UPDATE monthly_usage_tracking
SET monthly_quota = 3
WHERE monthly_quota = 50
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- 4. Vérifier les changements
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
AND monthly_quota = 3
ORDER BY source, identifier
LIMIT 10;

-- Afficher un message de confirmation
DO $$
DECLARE
    users_updated INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_updated
    FROM monthly_usage_tracking
    WHERE month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
    AND monthly_quota = 3;

    RAISE NOTICE '✅ Limite Essential réduite à 3 questions pour tests';
    RAISE NOTICE '📊 Utilisateurs mis à jour: %', users_updated;
    RAISE NOTICE '⚠️  N''oubliez pas de restaurer à 50 après les tests !';
    RAISE NOTICE '📝 Utilisez: psql -f temp_restore_essential_limit.sql';
END $$;
