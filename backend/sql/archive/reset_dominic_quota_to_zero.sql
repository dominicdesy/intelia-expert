-- Réinitialiser le quota de dominic.desy@icloud.com à 0/3 pour tester

UPDATE monthly_usage_tracking
SET
    questions_used = 0,
    questions_successful = 0,
    questions_failed = 0,
    current_status = 'active',
    warning_sent = FALSE,
    limit_notifications_sent = 0,
    last_updated = CURRENT_TIMESTAMP
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = '2025-10';

-- Vérifier le résultat
SELECT
    user_email,
    month_year,
    questions_used,
    monthly_quota,
    current_status
FROM monthly_usage_tracking
WHERE user_email = 'dominic.desy@icloud.com'
AND month_year = '2025-10';
