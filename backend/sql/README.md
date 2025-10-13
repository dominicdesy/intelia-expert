# SQL Scripts Organization

This directory contains all SQL scripts organized by category.

## Directory Structure

```
sql/
├── schema/          # Database schema definitions
├── migrations/      # Database migrations
├── fixes/          # One-time fixes and patches
└── maintenance/    # Verification and maintenance scripts
```

## 📁 Categories

### schema/
Database schema creation and definition scripts:
- `db_schema_conversations_messages.sql` - Main conversations and messages schema
- `create_conversation_shares_table.sql` - Conversation sharing feature
- `create_messages_table_only.sql` - Messages table standalone

### migrations/
Migration scripts for evolving the database:
- `migration_to_conversations_messages.sql` - Migration to new architecture
- `create_conversation_shares.sql` - Add sharing feature
- `create_qa_quality_checks.sql` - Add QA quality tracking

### fixes/
One-time fix scripts (historical):
- `fix_missing_titles.sql` - Generate missing conversation titles (v1)
- `fix_missing_titles_v2.sql` - Generate missing conversation titles (v2, production)
- `fix_conversations_id_type.sql` - Fix conversation ID type mismatch

### maintenance/
Verification and maintenance scripts:
- `verify_complete_structure.sql` - Verify complete database structure
- `verify_migration_complete.sql` - Verify migration completion
- `verify_new_architecture.sql` - Verify new architecture
- `verify_digitalocean_tables.sql` - Verify Digital Ocean deployment
- `check_conversations_structure.sql` - Check conversations table structure
- `cleanup_digitalocean_final.sql` - Final cleanup script
- `cleanup_digitalocean_tables.sql` - Cleanup Digital Ocean tables
- `cleanup_old_tables.sql` - Remove obsolete tables

## 🔧 Usage

### Running Schema Scripts
```bash
psql $DATABASE_URL -f sql/schema/db_schema_conversations_messages.sql
```

### Running Migrations
```bash
psql $DATABASE_URL -f sql/migrations/migration_to_conversations_messages.sql
```

### Running Fixes
```bash
# One-time fixes - use with caution
psql $DATABASE_URL -f sql/fixes/fix_missing_titles_v2.sql
```

### Running Maintenance Scripts
```bash
# Verification
psql $DATABASE_URL -f sql/maintenance/verify_complete_structure.sql

# Cleanup (be careful!)
psql $DATABASE_URL -f sql/maintenance/cleanup_old_tables.sql
```

## ⚠️ Important Notes

- **Always backup before running scripts** (especially migrations and fixes)
- **Test in development first** before running in production
- **Fix scripts** are historical - may not be needed for new databases
- **Cleanup scripts** permanently delete data - review carefully

## 📝 Adding New Scripts

When adding new SQL scripts, follow this organization:
1. **Schema changes**: Add to `schema/` with descriptive name
2. **Database evolution**: Add to `migrations/` with timestamp prefix
3. **One-time fixes**: Add to `fixes/` with clear description
4. **Verification**: Add to `maintenance/` with `verify_` or `check_` prefix
5. **Cleanup**: Add to `maintenance/` with `cleanup_` prefix

## 🔗 Related Documentation

- [Database Schema Guide](../../docs/guides/DATABASE_SCHEMA.md)
- [Fix Missing Titles](../../docs/backend/FIX_MISSING_TITLES_README.md)
- [Conversation Sharing Guide](../../docs/guides/CONVERSATION_SHARING_GUIDE.md)
