# Migration: Add ad_history to users table

## Purpose
Store ad rotation history in the user profile to ensure ad rotation works even in private browsing mode where all local storage (cookies, localStorage, IndexedDB) is cleared on browser close.

## How to apply this migration

### Option 1: Supabase Dashboard (Recommended)
1. Go to https://supabase.com/dashboard
2. Select your project: **Intelia Expert**
3. Go to **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy and paste the contents of `add_ad_history_to_users.sql`
6. Click **Run** (or press Ctrl+Enter)
7. Verify success: "Success. No rows returned"

### Option 2: psql Command Line
```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres" -f add_ad_history_to_users.sql
```

## Verification

After running the migration, verify it worked:

```sql
-- Check that the column exists
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'ad_history';

-- Expected result:
-- column_name | data_type | column_default
-- ad_history  | jsonb     | '[]'::jsonb
```

## Rollback (if needed)

If you need to remove this column:

```sql
-- Remove the column
ALTER TABLE public.users DROP COLUMN IF EXISTS ad_history;

-- Remove the index
DROP INDEX IF EXISTS idx_users_ad_history;
```

## What this enables

- Ad rotation history persists across browser sessions
- Works in private/incognito mode
- Guarantees users see different ads on each visit
- No reliance on client-side storage (cookies/localStorage/IndexedDB)
- Backend-driven ad rotation logic

## Example data

```json
{
  "ad_history": [
    "ad-02-smart-sensors-mike-2024",
    "ad-01-poultry-ai",
    "ad-02-smart-sensors-mike-2024"
  ]
}
```

The array stores the last 10 ads shown, newest first.
