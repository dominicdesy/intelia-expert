-- Lister tous les plans existants dans billing_plans
SELECT
    plan_name,
    display_name,
    monthly_quota,
    price_per_month,
    active,
    created_at
FROM billing_plans
ORDER BY price_per_month, plan_name;

-- Compter le nombre de plans
SELECT COUNT(*) as total_plans FROM billing_plans;
