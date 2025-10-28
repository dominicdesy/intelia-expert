-- Vérifier simplement l'usage de dominic.desy@icloud.com

-- 1. Monthly usage tracking
SELECT
    'USAGE TRACKING' as section,
    user_email,
    month_year,
    questions_used,
    monthly_quota,
    current_status
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
ORDER BY month_year DESC;

-- 2. Si aucun résultat, vérifier tous les mois
SELECT
    'TOUS LES MOIS' as section,
    user_email,
    month_year,
    questions_used,
    monthly_quota
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
ORDER BY month_year DESC;

-- 3. Vérifier le plan
SELECT
    'PLAN ACTIF' as section,
    plan_name,
    monthly_quota,
    active
FROM billing_plans
WHERE plan_name = 'free';
