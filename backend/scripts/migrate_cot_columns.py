#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_cot_columns.py - Add CoT columns to messages table

Run this script on the server to add cot_thinking, cot_analysis, has_cot_structure
columns to the messages table for Chain-of-Thought analytics.

Usage:
    python scripts/migrate_cot_columns.py
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def run_migration():
    """Execute CoT columns migration"""
    try:
        print("🔗 Connecting to PostgreSQL...")
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 25060)),
            ssl="require",
        )
        print("✅ Connected successfully\n")

        # Read migration SQL
        migration_file = Path(__file__).parent.parent / "sql" / "migrations" / "add_cot_columns_to_messages.sql"
        with open(migration_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Split and execute only the ALTER TABLE and CREATE INDEX parts
        sql_commands = sql_content.split("-- Vérification")[0]

        print("🔧 Executing migration...")
        await conn.execute(sql_commands)
        print("✅ Migration executed successfully\n")

        # Verify columns were added
        print("📋 Verifying new columns...")
        result = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'messages'
              AND column_name IN ('cot_thinking', 'cot_analysis', 'has_cot_structure')
            ORDER BY column_name
        """
        )

        if result:
            print("\n✅ New columns added successfully:")
            for row in result:
                nullable = "YES" if row["is_nullable"] == "YES" else "NO"
                print(f"  - {row['column_name']}: {row['data_type']} (nullable: {nullable})")
        else:
            print("\n⚠️  Warning: Could not verify columns (they may already exist)")

        # Check if any existing messages need CoT parsing
        count = await conn.fetchval("SELECT COUNT(*) FROM messages WHERE role = 'assistant'")
        print(f"\n📊 Found {count} assistant messages in database")
        print("   (CoT will be extracted automatically for new messages)")

        await conn.close()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_migration())
