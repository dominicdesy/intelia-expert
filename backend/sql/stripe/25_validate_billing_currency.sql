-- ============================================================================
-- VALIDATION SCRIPT FOR BILLING CURRENCY MIGRATION
-- Execute this to check if migration was successful
-- ============================================================================

-- Check if billing_currency column exists
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_billing_info'
  AND column_name = 'billing_currency';

-- If column exists, show sample data
-- (This will error if column doesn't exist - that's expected)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'user_billing_info'
          AND column_name = 'billing_currency'
    ) THEN
        RAISE NOTICE '✓ Column billing_currency exists';

        -- Show users without billing_currency
        RAISE NOTICE 'Checking users without billing_currency...';
        PERFORM COUNT(*) FROM user_billing_info WHERE billing_currency IS NULL;

    ELSE
        RAISE NOTICE '✗ Column billing_currency does NOT exist - migration not yet applied';
    END IF;
END $$;

-- Check if suggest_billing_currency function exists
SELECT
    routine_name,
    routine_type,
    data_type as return_type
FROM information_schema.routines
WHERE routine_name = 'suggest_billing_currency'
  AND routine_schema = 'public';

-- Test the suggest_billing_currency function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.routines
        WHERE routine_name = 'suggest_billing_currency'
    ) THEN
        RAISE NOTICE '✓ Function suggest_billing_currency exists';
        RAISE NOTICE 'Testing function...';
        RAISE NOTICE 'US → %', suggest_billing_currency('US');
        RAISE NOTICE 'CN → %', suggest_billing_currency('CN');
        RAISE NOTICE 'IN → %', suggest_billing_currency('IN');
        RAISE NOTICE 'BR → %', suggest_billing_currency('BR');
        RAISE NOTICE 'FR → %', suggest_billing_currency('FR');
    ELSE
        RAISE NOTICE '✗ Function suggest_billing_currency does NOT exist';
    END IF;
END $$;

-- Check if index exists
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'user_billing_info'
  AND indexname = 'idx_user_billing_currency';

-- Summary
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'user_billing_info' AND column_name = 'billing_currency'
        ) THEN '✓ PASSED'
        ELSE '✗ FAILED'
    END as column_check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.routines
            WHERE routine_name = 'suggest_billing_currency'
        ) THEN '✓ PASSED'
        ELSE '✗ FAILED'
    END as function_check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'user_billing_info' AND indexname = 'idx_user_billing_currency'
        ) THEN '✓ PASSED'
        ELSE '✗ FAILED'
    END as index_check;
