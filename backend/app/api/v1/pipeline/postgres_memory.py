import os
import json
import threading
import psycopg2
from typing import Dict, Any

class PostgresMemory:
    """
    Session store backed by a managed PostgreSQL database.
    Table schema:
      CREATE TABLE IF NOT EXISTS conversation_memory (
        session_id TEXT PRIMARY KEY,
        context JSONB,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
      );
    """
    def __init__(self, dsn: str = None):
        self._lock = threading.Lock()
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self.conn = psycopg2.connect(self.dsn, sslmode="require")
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_memory (
                        session_id TEXT PRIMARY KEY,
                        context JSONB,
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

    def get(self, session_id: str) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT context FROM conversation_memory WHERE session_id = %s",
                (session_id,)
            )
            row = cur.fetchone()
        if not row or row[0] is None:
            return {}
        return row[0]

    def update(self, session_id: str, new_context: Dict[str, Any]) -> None:
        with self._lock:
            existing = self.get(session_id)
            existing.update(new_context)
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO conversation_memory (session_id, context) VALUES (%s, %s) "
                        "ON CONFLICT (session_id) DO UPDATE SET context = EXCLUDED.context, updated_at = NOW()",
                        (session_id, json.dumps(existing))
                    )

    def clear(self, session_id: str) -> None:
        with self._lock:
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM conversation_memory WHERE session_id = %s",
                        (session_id,)
                    )
