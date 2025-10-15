# Migration: Add facebook_profile to users table

## Purpose
Store Facebook profile URL extracted automatically from OAuth data when users sign in with Facebook.

## How to apply this migration

### Option 1: Supabase Dashboard (Recommended)
1. Go to https://supabase.com/dashboard
2. Select your project: **Intelia Expert**
3. Go to **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy and paste the contents of `add_facebook_profile_to_users.sql`
6. Click **Run** (or press Ctrl+Enter)
7. Verify success: "Success. No rows returned"

### Option 2: psql Command Line
```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres" -f add_facebook_profile_to_users.sql
```

## Verification

After running the migration, verify it worked:

```sql
-- Check that the column exists
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'facebook_profile';

-- Expected result:
-- column_name      | data_type | column_default
-- facebook_profile | text      | null
```

## Rollback (if needed)

If you need to remove this column:

```sql
-- Remove the column
ALTER TABLE public.users DROP COLUMN IF EXISTS facebook_profile;
```

## What this enables

- Automatic extraction of Facebook profile URL from OAuth data
- URL format: `https://facebook.com/{user_id}`
- Extracted from `avatar_url` field: `asid=10161563757712721`
- Stored in `users.facebook_profile` column
- No user action required - fully automatic

## Example data

```json
{
  "facebook_profile": "https://facebook.com/10161563757712721"
}
```

The URL is constructed from the Facebook user ID extracted from the OAuth avatar URL.
