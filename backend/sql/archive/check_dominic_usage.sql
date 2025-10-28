-- Vérifier l'usage actuel de dominic.desy@icloud.com
SELECT
    user_email,
    month_year,
    questions_used,
    monthly_quota,
    questions_used || '/' || monthly_quota as usage,
    current_status,
    last_question_at
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM');

-- Vérifier le plan actif
SELECT
    ss.user_email,
    ss.plan_name,
    ss.status,
    bp.monthly_quota as plan_quota,
    ubi.quota_enforcement
FROM stripe_subscriptions ss
LEFT JOIN billing_plans bp ON ss.plan_name = bp.plan_name
LEFT JOIN user_billing_info ubi ON ss.user_email = ubi.user_email
WHERE ss.user_email = 'dominic.desy@icloud.com'
AND ss.status = 'active';

-- Vérifier user_billing_info
SELECT
    user_email,
    plan_name,
    custom_monthly_quota,
    quota_enforcement,
    billing_enabled
FROM user_billing_info
WHERE user_email = 'dominic.desy@icloud.com';
