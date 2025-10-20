-- ============================================================================
-- ADD BILLING CURRENCY PREFERENCE
-- Allow users to choose their preferred billing currency for Stripe
-- ============================================================================

-- Add billing_currency column to user_billing_info
-- 16 supported currencies covering 87-90% of global poultry production
ALTER TABLE user_billing_info
ADD COLUMN IF NOT EXISTS billing_currency VARCHAR(3) DEFAULT NULL
    CHECK (billing_currency IN (
        'USD', 'EUR', 'CNY', 'INR', 'BRL', 'IDR', 'MXN', 'JPY',
        'TRY', 'GBP', 'ZAR', 'THB', 'MYR', 'PHP', 'PLN', 'VND'
    ));

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_billing_currency
ON user_billing_info(billing_currency);

-- Add comment
COMMENT ON COLUMN user_billing_info.billing_currency IS
'User preferred billing currency for Stripe payments. 16 supported currencies based on top poultry-producing countries: USD, EUR, CNY, INR, BRL, IDR, MXN, JPY, TRY, GBP, ZAR, THB, MYR, PHP, PLN, VND. NULL if not yet selected.';

-- ============================================================================
-- FUNCTION: Get suggested billing currency based on country
-- ============================================================================

CREATE OR REPLACE FUNCTION suggest_billing_currency(p_country_code VARCHAR(2))
RETURNS VARCHAR(3) AS $$
BEGIN
    -- Eurozone countries → EUR
    -- Includes major poultry producers: France, Germany, Spain, Italy, Netherlands, Poland
    IF p_country_code IN (
        'AT', 'BE', 'CY', 'EE', 'FI', 'FR', 'DE', 'GR', 'IE', 'IT',
        'LV', 'LT', 'LU', 'MT', 'NL', 'PT', 'SK', 'SI', 'ES'
    ) THEN
        RETURN 'EUR';

    -- Poland → Can use EUR or PLN, suggest PLN for local preference
    ELSIF p_country_code = 'PL' THEN
        RETURN 'PLN';

    -- United States → USD
    ELSIF p_country_code = 'US' THEN
        RETURN 'USD';

    -- China (Top #1 producer) → CNY
    ELSIF p_country_code = 'CN' THEN
        RETURN 'CNY';

    -- India (Top #2 eggs, #5 chicken) → INR
    ELSIF p_country_code = 'IN' THEN
        RETURN 'INR';

    -- Brazil (Top #3 chicken) → BRL
    ELSIF p_country_code = 'BR' THEN
        RETURN 'BRL';

    -- Indonesia (Top #3 eggs, #6 chicken) → IDR
    ELSIF p_country_code = 'ID' THEN
        RETURN 'IDR';

    -- Mexico (Top #6-7) → MXN
    ELSIF p_country_code = 'MX' THEN
        RETURN 'MXN';

    -- Japan (Top #8 eggs) → JPY
    ELSIF p_country_code = 'JP' THEN
        RETURN 'JPY';

    -- Turkey (Top #9-10) → TRY
    ELSIF p_country_code = 'TR' THEN
        RETURN 'TRY';

    -- United Kingdom → GBP
    ELSIF p_country_code = 'GB' THEN
        RETURN 'GBP';

    -- South Africa → ZAR
    ELSIF p_country_code = 'ZA' THEN
        RETURN 'ZAR';

    -- Thailand → THB
    ELSIF p_country_code = 'TH' THEN
        RETURN 'THB';

    -- Malaysia → MYR
    ELSIF p_country_code = 'MY' THEN
        RETURN 'MYR';

    -- Philippines → PHP
    ELSIF p_country_code = 'PH' THEN
        RETURN 'PHP';

    -- Vietnam → VND
    ELSIF p_country_code = 'VN' THEN
        RETURN 'VND';

    -- Latin America (not Brazil/Mexico) → USD
    -- AR, CL, CO, PE, VE, etc.
    ELSIF p_country_code IN ('AR', 'CL', 'CO', 'PE', 'VE', 'UY', 'PY', 'BO', 'EC') THEN
        RETURN 'USD';

    -- Southeast Asia (not covered above) → USD
    -- SG, KH, LA, MM, etc.
    ELSIF p_country_code IN ('SG', 'KH', 'LA', 'MM', 'BN') THEN
        RETURN 'USD';

    -- Middle East (not covered) → USD
    -- SA, AE, QA, KW, etc.
    ELSIF p_country_code IN ('SA', 'AE', 'QA', 'KW', 'OM', 'BH', 'JO', 'LB', 'IQ') THEN
        RETURN 'USD';

    -- Africa (not South Africa) → USD
    -- NG, KE, EG, MA, etc.
    ELSIF p_country_code IN ('NG', 'KE', 'EG', 'MA', 'TN', 'DZ', 'GH', 'CI', 'SN', 'UG', 'TZ', 'ET') THEN
        RETURN 'USD';

    -- Oceania → USD
    -- AU, NZ, PG, FJ, etc.
    ELSIF p_country_code IN ('AU', 'NZ', 'PG', 'FJ', 'NC', 'PF') THEN
        RETURN 'USD';

    -- Canada and other Americas → USD
    ELSIF p_country_code IN ('CA', 'CR', 'PA', 'GT', 'SV', 'HN', 'NI', 'DO', 'PR', 'JM', 'TT', 'BB') THEN
        RETURN 'USD';

    -- Eastern Europe (non-EU, non-Poland) → EUR (closest major currency)
    -- UA, BY, MD, etc.
    ELSIF p_country_code IN ('UA', 'BY', 'MD', 'RS', 'BA', 'MK', 'AL', 'ME', 'XK') THEN
        RETURN 'EUR';

    -- Russia and former Soviet (not covered) → EUR
    -- RU, KZ, UZ, etc.
    ELSIF p_country_code IN ('RU', 'KZ', 'UZ', 'TM', 'TJ', 'KG', 'AM', 'AZ', 'GE') THEN
        RETURN 'EUR';

    -- South Asia (not India) → INR (regional preference)
    -- PK, BD, LK, NP, etc.
    ELSIF p_country_code IN ('PK', 'BD', 'LK', 'NP', 'BT', 'MV', 'AF') THEN
        RETURN 'INR';

    -- East Asia (not China/Japan) → CNY (regional preference)
    -- KR, TW, HK, MO, MN
    ELSIF p_country_code IN ('KR', 'TW', 'HK', 'MO', 'MN', 'KP') THEN
        RETURN 'CNY';

    -- Default fallback → USD (global standard)
    ELSE
        RETURN 'USD';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION suggest_billing_currency IS
'Suggests billing currency based on country code. Covers 16 supported currencies (USD, EUR, CNY, INR, BRL, IDR, MXN, JPY, TRY, GBP, ZAR, THB, MYR, PHP, PLN, VND) with intelligent regional defaults.';

-- ============================================================================
-- EXAMPLES (Execute these manually AFTER the migration is complete)
-- ============================================================================

-- Test suggestions for all 16 supported currencies
-- NOTE: Run these queries manually to validate the migration
SELECT 'US' as country, suggest_billing_currency('US') as suggested_currency, 'Should be USD' as expected
UNION ALL
SELECT 'FR' as country, suggest_billing_currency('FR') as suggested_currency, 'Should be EUR' as expected
UNION ALL
SELECT 'DE' as country, suggest_billing_currency('DE') as suggested_currency, 'Should be EUR' as expected
UNION ALL
SELECT 'PL' as country, suggest_billing_currency('PL') as suggested_currency, 'Should be PLN' as expected
UNION ALL
SELECT 'CN' as country, suggest_billing_currency('CN') as suggested_currency, 'Should be CNY' as expected
UNION ALL
SELECT 'IN' as country, suggest_billing_currency('IN') as suggested_currency, 'Should be INR' as expected
UNION ALL
SELECT 'BR' as country, suggest_billing_currency('BR') as suggested_currency, 'Should be BRL' as expected
UNION ALL
SELECT 'ID' as country, suggest_billing_currency('ID') as suggested_currency, 'Should be IDR' as expected
UNION ALL
SELECT 'MX' as country, suggest_billing_currency('MX') as suggested_currency, 'Should be MXN' as expected
UNION ALL
SELECT 'JP' as country, suggest_billing_currency('JP') as suggested_currency, 'Should be JPY' as expected
UNION ALL
SELECT 'TR' as country, suggest_billing_currency('TR') as suggested_currency, 'Should be TRY' as expected
UNION ALL
SELECT 'GB' as country, suggest_billing_currency('GB') as suggested_currency, 'Should be GBP' as expected
UNION ALL
SELECT 'ZA' as country, suggest_billing_currency('ZA') as suggested_currency, 'Should be ZAR' as expected
UNION ALL
SELECT 'TH' as country, suggest_billing_currency('TH') as suggested_currency, 'Should be THB' as expected
UNION ALL
SELECT 'MY' as country, suggest_billing_currency('MY') as suggested_currency, 'Should be MYR' as expected
UNION ALL
SELECT 'PH' as country, suggest_billing_currency('PH') as suggested_currency, 'Should be PHP' as expected
UNION ALL
SELECT 'VN' as country, suggest_billing_currency('VN') as suggested_currency, 'Should be VND' as expected
UNION ALL
-- Test regional defaults
SELECT 'CA' as country, suggest_billing_currency('CA') as suggested_currency, 'Should be USD (Canada)' as expected
UNION ALL
SELECT 'AU' as country, suggest_billing_currency('AU') as suggested_currency, 'Should be USD (Australia)' as expected
UNION ALL
SELECT 'SG' as country, suggest_billing_currency('SG') as suggested_currency, 'Should be USD (Singapore)' as expected
UNION ALL
SELECT 'AE' as country, suggest_billing_currency('AE') as suggested_currency, 'Should be USD (UAE)' as expected
UNION ALL
SELECT 'KR' as country, suggest_billing_currency('KR') as suggested_currency, 'Should be CNY (Korea → regional)' as expected
UNION ALL
SELECT 'PK' as country, suggest_billing_currency('PK') as suggested_currency, 'Should be INR (Pakistan → regional)' as expected;

-- ============================================================================
-- VALIDATION QUERIES (Run these manually to check data)
-- ============================================================================

-- Check existing users without billing_currency
-- NOTE: This query is commented out to prevent execution errors during migration
-- Uncomment and run manually after migration is complete
/*
SELECT
    COUNT(*) as users_without_currency,
    COUNT(*) FILTER (WHERE plan_name != 'essential') as paid_users_without_currency
FROM user_billing_info
WHERE billing_currency IS NULL;
*/

-- Show distribution of billing currencies (after users select them)
-- NOTE: This query is commented out to prevent execution errors during migration
-- Uncomment and run manually after migration is complete
/*
SELECT
    billing_currency,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM user_billing_info
WHERE billing_currency IS NOT NULL
GROUP BY billing_currency
ORDER BY user_count DESC;
*/
