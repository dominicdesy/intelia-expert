-- Vérifier les plans disponibles dans billing_plans
SELECT
    plan_name,
    display_name,
    monthly_quota,
    price_per_month,
    active
FROM billing_plans
ORDER BY price_per_month;

-- Vérifier si 'essential' existe
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM billing_plans WHERE plan_name = 'essential')
        THEN '✅ Plan "essential" existe'
        ELSE '❌ Plan "essential" MANQUANT - Il faut le créer !'
    END as status;
