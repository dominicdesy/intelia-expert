-- ============================================================================
-- ADD BILLING CURRENCY PREFERENCE
-- Allow users to choose their preferred billing currency for Stripe
-- ============================================================================

-- Add billing_currency column to user_billing_info
ALTER TABLE user_billing_info
ADD COLUMN IF NOT EXISTS billing_currency VARCHAR(3) DEFAULT NULL
    CHECK (billing_currency IN ('USD', 'EUR', 'CAD'));

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_billing_currency
ON user_billing_info(billing_currency);

-- Add comment
COMMENT ON COLUMN user_billing_info.billing_currency IS
'User preferred billing currency for Stripe payments (USD, EUR, or CAD). NULL if not yet selected.';

-- ============================================================================
-- FUNCTION: Get suggested billing currency based on country
-- ============================================================================

CREATE OR REPLACE FUNCTION suggest_billing_currency(p_country_code VARCHAR(2))
RETURNS VARCHAR(3) AS $$
BEGIN
    -- Eurozone countries → EUR
    IF p_country_code IN (
        'AT', 'BE', 'CY', 'EE', 'FI', 'FR', 'DE', 'GR', 'IE', 'IT',
        'LV', 'LT', 'LU', 'MT', 'NL', 'PT', 'SK', 'SI', 'ES'
    ) THEN
        RETURN 'EUR';

    -- Canada → CAD
    ELSIF p_country_code = 'CA' THEN
        RETURN 'CAD';

    -- All others → USD (including USA, UK, Australia, Asia, Africa, etc.)
    ELSE
        RETURN 'USD';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION suggest_billing_currency IS
'Suggests billing currency (EUR, CAD, USD) based on country code';

-- ============================================================================
-- EXAMPLES
-- ============================================================================

-- Test suggestions
SELECT 'US' as country, suggest_billing_currency('US') as suggested_currency
UNION ALL
SELECT 'CA' as country, suggest_billing_currency('CA') as suggested_currency
UNION ALL
SELECT 'FR' as country, suggest_billing_currency('FR') as suggested_currency
UNION ALL
SELECT 'GB' as country, suggest_billing_currency('GB') as suggested_currency
UNION ALL
SELECT 'JP' as country, suggest_billing_currency('JP') as suggested_currency;

-- Check existing users without billing_currency
SELECT
    COUNT(*) as users_without_currency,
    COUNT(*) FILTER (WHERE plan_name != 'essential') as paid_users_without_currency
FROM user_billing_info
WHERE billing_currency IS NULL;

-- Show distribution of billing currencies (after users select them)
SELECT
    billing_currency,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM user_billing_info
WHERE billing_currency IS NOT NULL
GROUP BY billing_currency
ORDER BY user_count DESC;
