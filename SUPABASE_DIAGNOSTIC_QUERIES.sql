-- ========================================
-- DIAGNOSTIC SQL QUERIES FOR SUPABASE
-- Investigating why "Utilisateurs les plus actifs" is empty
-- ========================================

-- TEST 1: Check if conversations table has data
-- Expected: Should return rows with conversations
SELECT
    COUNT(*) as total_conversations,
    COUNT(DISTINCT user_id) as unique_users,
    MIN(created_at) as oldest_conversation,
    MAX(created_at) as newest_conversation
FROM conversations;

-- TEST 2: Check if conversations have non-null user_id
-- Expected: Should show how many conversations have user_id vs null
SELECT
    COUNT(*) FILTER (WHERE user_id IS NOT NULL) as conversations_with_user_id,
    COUNT(*) FILTER (WHERE user_id IS NULL) as conversations_without_user_id
FROM conversations;

-- TEST 3: Check if users table exists and has data
-- Expected: Should return rows with user information
SELECT
    COUNT(*) as total_users,
    COUNT(DISTINCT email) as unique_emails
FROM users;

-- TEST 4: Sample data from conversations table
-- Expected: See actual conversation data with user_id values
SELECT
    id,
    user_id,
    LEFT(question, 50) as question_preview,
    created_at
FROM conversations
ORDER BY created_at DESC
LIMIT 5;

-- TEST 5: Sample data from users table
-- Expected: See actual user data
SELECT
    id,
    email,
    first_name,
    last_name,
    user_type
FROM users
LIMIT 5;

-- TEST 6: Test the JOIN between conversations and users
-- Expected: Should return conversations with user details
SELECT
    c.id,
    c.user_id,
    u.email,
    u.first_name,
    u.last_name,
    LEFT(c.question, 30) as question_preview,
    c.created_at
FROM conversations c
LEFT JOIN users u ON u.id = c.user_id
ORDER BY c.created_at DESC
LIMIT 10;

-- TEST 7: Check data type compatibility
-- Expected: Should show if user_id and id have compatible types
SELECT
    table_name,
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE (table_name = 'conversations' AND column_name = 'user_id')
   OR (table_name = 'users' AND column_name = 'id');

-- TEST 8: Test the actual query used in stats_fast.py with recent data
-- Expected: Should return top users if data exists
SELECT
    COALESCE(u.email, c.user_id::text) as email,
    COALESCE(u.first_name, '') as first_name,
    COALESCE(u.last_name, '') as last_name,
    COUNT(*) as question_count,
    'free' as plan
FROM conversations c
LEFT JOIN users u ON u.id = c.user_id
WHERE c.created_at >= CURRENT_DATE - INTERVAL '30 days'
    AND c.user_id IS NOT NULL
    AND c.question IS NOT NULL
    AND c.response IS NOT NULL
GROUP BY c.user_id, u.email, u.first_name, u.last_name
ORDER BY question_count DESC
LIMIT 10;

-- TEST 9: Check if there are conversations in last 30 days
-- Expected: Should return count of recent conversations
SELECT
    COUNT(*) as conversations_last_30_days,
    COUNT(*) FILTER (WHERE user_id IS NOT NULL) as with_user_id,
    COUNT(*) FILTER (WHERE question IS NOT NULL) as with_question,
    COUNT(*) FILTER (WHERE response IS NOT NULL) as with_response
FROM conversations
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';

-- TEST 10: Simplified query without date filter
-- Expected: Should return all users with conversation counts
SELECT
    COALESCE(u.email, c.user_id::text) as email,
    COALESCE(u.first_name, '') as first_name,
    COALESCE(u.last_name, '') as last_name,
    COUNT(*) as question_count
FROM conversations c
LEFT JOIN users u ON u.id = c.user_id
WHERE c.user_id IS NOT NULL
    AND c.question IS NOT NULL
    AND c.response IS NOT NULL
GROUP BY c.user_id, u.email, u.first_name, u.last_name
ORDER BY question_count DESC
LIMIT 10;

-- TEST 11: Check if schema prefix matters
-- Expected: Compare results with and without schema prefix
SELECT 'With schema prefix' as test_type, COUNT(*) as result
FROM conversations c
LEFT JOIN public.users u ON u.id = c.user_id
WHERE c.user_id IS NOT NULL
UNION ALL
SELECT 'Without schema prefix', COUNT(*)
FROM conversations c
LEFT JOIN users u ON u.id = c.user_id
WHERE c.user_id IS NOT NULL;

-- ========================================
-- INSTRUCTIONS:
-- ========================================
-- 1. Run each query in Supabase SQL Editor
-- 2. Note which queries return empty results
-- 3. Note any error messages
-- 4. Pay special attention to:
--    - TEST 8 (actual query from backend)
--    - TEST 9 (date range check)
--    - TEST 10 (simplified without date)
--    - TEST 11 (schema prefix comparison)
-- ========================================
