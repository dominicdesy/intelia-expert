#!/usr/bin/env python3
"""
Script to run LLM metrics history migration
Creates the llm_metrics_history table in PostgreSQL
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment variables")
    sys.exit(1)

# Read migration SQL file
migration_file = Path(__file__).parent.parent / "sql" / "migrations" / "create_llm_metrics_history.sql"

if not migration_file.exists():
    print(f"❌ Migration file not found: {migration_file}")
    sys.exit(1)

with open(migration_file, "r", encoding="utf-8") as f:
    migration_sql = f.read()

print("📄 Migration SQL loaded from:", migration_file)


async def run_migration():
    """Execute the migration"""
    try:
        print("🔌 Connecting to PostgreSQL...")
        conn = await asyncpg.connect(DATABASE_URL)

        print("🚀 Running migration...")
        await conn.execute(migration_sql)

        print("✅ Migration completed successfully!")

        # Verify table was created
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'llm_metrics_history'
            );
        """)

        if result:
            print("✅ Table llm_metrics_history verified in database")

            # Show table structure
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'llm_metrics_history'
                ORDER BY ordinal_position;
            """)

            print("\n📊 Table structure:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']}")
        else:
            print("⚠️  Table not found after migration")

        await conn.close()
        print("\n🎉 Migration script completed!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Metrics History Migration")
    print("=" * 60)
    asyncio.run(run_migration())
