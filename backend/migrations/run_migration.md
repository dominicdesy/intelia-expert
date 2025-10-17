# WebAuthn Migration Guide

## How to Run the Migration on Supabase

### Option 1: Via Supabase Dashboard (Recommended)

1. **Go to Supabase Dashboard**
   - Navigate to https://app.supabase.com
   - Select your project

2. **Open SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "+ New query"

3. **Copy and Paste Migration**
   - Open `add_webauthn_credentials.sql`
   - Copy the entire content
   - Paste into the SQL Editor

4. **Execute Migration**
   - Click "Run" or press `Ctrl+Enter`
   - Verify success message

5. **Verify Table Creation**
   - Go to "Table Editor" in left sidebar
   - Look for `webauthn_credentials` table
   - Check that it has the correct columns

### Option 2: Via psql Command Line

```bash
# Connect to Supabase PostgreSQL
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run migration
\i backend/migrations/add_webauthn_credentials.sql

# Verify
\dt public.webauthn_credentials
```

### Option 3: Via Python Script

```python
from app.core.database import get_supabase_client

# Read migration file
with open('backend/migrations/add_webauthn_credentials.sql', 'r') as f:
    migration_sql = f.read()

# Execute migration
supabase = get_supabase_client()
supabase.rpc('exec_sql', {'query': migration_sql}).execute()
```

## Verify Migration Success

After running the migration, verify:

1. **Table exists**: `public.webauthn_credentials`
2. **Columns created**:
   - id (UUID)
   - user_id (UUID, foreign key to auth.users)
   - credential_id (TEXT, unique)
   - public_key (TEXT)
   - counter (INTEGER)
   - device_type (TEXT)
   - device_name (TEXT)
   - transports (TEXT[])
   - backup_eligible (BOOLEAN)
   - backup_state (BOOLEAN)
   - created_at (TIMESTAMPTZ)
   - last_used_at (TIMESTAMPTZ)

3. **Indexes created**:
   - idx_webauthn_user_id
   - idx_webauthn_credential_id
   - idx_webauthn_created_at

4. **RLS Policies**:
   - Users can view own webauthn credentials
   - Users can insert own webauthn credentials
   - Users can update own webauthn credentials
   - Users can delete own webauthn credentials

## Test the Migration

```sql
-- Test 1: Verify table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'webauthn_credentials'
ORDER BY ordinal_position;

-- Test 2: Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename = 'webauthn_credentials';

-- Test 3: List all policies
SELECT policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'webauthn_credentials';
```

## Environment Variables

After migration, set these environment variables in your backend:

```bash
# For development (localhost)
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME="Intelia Expert (Dev)"
WEBAUTHN_ORIGIN=http://localhost:3000

# For production
WEBAUTHN_RP_ID=expert.intelia.com
WEBAUTHN_RP_NAME="Intelia Expert"
WEBAUTHN_ORIGIN=https://expert.intelia.com
```

## Rollback (if needed)

If you need to rollback the migration:

```sql
-- Drop table (cascades to all dependencies)
DROP TABLE IF EXISTS public.webauthn_credentials CASCADE;
```

## Troubleshooting

### Error: "relation already exists"
- Table already created, migration was run before
- Safe to ignore or drop table first

### Error: "permission denied"
- Need admin/postgres role
- Use Supabase dashboard instead

### Error: "auth.users does not exist"
- Supabase not properly initialized
- Check that authentication is enabled in project settings
