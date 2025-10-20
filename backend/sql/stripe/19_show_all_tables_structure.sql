-- Afficher la structure de TOUTES les tables liées au billing

-- 1. billing_plans
SELECT 'billing_plans' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'billing_plans'
ORDER BY ordinal_position;

-- Voir les données
SELECT * FROM billing_plans ORDER BY price_per_month;

-----------------------------------------------------------

-- 2. stripe_pricing_tiers
SELECT 'stripe_pricing_tiers' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'stripe_pricing_tiers'
ORDER BY ordinal_position;

-- Voir les données
SELECT * FROM stripe_pricing_tiers ORDER BY plan_name, tier_level;

-----------------------------------------------------------

-- 3. stripe_country_tiers
SELECT 'stripe_country_tiers' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'stripe_country_tiers'
ORDER BY ordinal_position;

-- Voir les données
SELECT * FROM stripe_country_tiers WHERE active = TRUE ORDER BY tier_level, country_code LIMIT 10;

-----------------------------------------------------------

-- 4. stripe_country_pricing (prix custom)
SELECT 'stripe_country_pricing' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'stripe_country_pricing'
ORDER BY ordinal_position;

-- Voir les données
SELECT * FROM stripe_country_pricing WHERE active = TRUE LIMIT 10;

-----------------------------------------------------------

-- 5. stripe_currency_rates
SELECT 'stripe_currency_rates' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'stripe_currency_rates'
ORDER BY ordinal_position;

-- Voir les données
SELECT * FROM stripe_currency_rates ORDER BY currency_code;

-----------------------------------------------------------

-- 6. user_billing_info (lien users ↔ plans)
SELECT 'user_billing_info' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'user_billing_info'
ORDER BY ordinal_position;

-- Voir un échantillon
SELECT user_id, plan_name, questions_asked, questions_limit, stripe_customer_id, stripe_subscription_id
FROM user_billing_info
LIMIT 5;

-----------------------------------------------------------

-- RÉSUMÉ: Compter les lignes dans chaque table
SELECT
    'billing_plans' as table_name,
    COUNT(*) as row_count
FROM billing_plans
UNION ALL
SELECT
    'stripe_pricing_tiers',
    COUNT(*)
FROM stripe_pricing_tiers
UNION ALL
SELECT
    'stripe_country_tiers',
    COUNT(*)
FROM stripe_country_tiers WHERE active = TRUE
UNION ALL
SELECT
    'stripe_country_pricing (custom)',
    COUNT(*)
FROM stripe_country_pricing WHERE active = TRUE
UNION ALL
SELECT
    'stripe_currency_rates',
    COUNT(*)
FROM stripe_currency_rates
UNION ALL
SELECT
    'user_billing_info',
    COUNT(*)
FROM user_billing_info;
