import json
import os
import psycopg2

class PostgresMemory:
    """
    Conversation memory backend using a managed PostgreSQL instance.
    Ensures correct decoding of JSON and always closes connections.
    """
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("DATABASE_URL")

    def get(self, session_id):
        """
        Get the context dict for a session_id. Always returns a dict.
        """
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT context FROM conversation_memory WHERE session_id=%s", (session_id,))
                row = cur.fetchone()
                if not row or not row[0]:
                    return {}
                val = row[0]
                if isinstance(val, dict):
                    return val
                try:
                    return json.loads(val)
                except Exception:
                    return {}

    def update(self, session_id, context: dict):
        """
        Upsert the context dict for a session_id.
        """
        ctx_json = json.dumps(context)
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversation_memory (session_id, context)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET context = EXCLUDED.context
                """, (session_id, ctx_json))
                conn.commit()

    def clear(self, session_id):
        """
        Delete the context for a session_id.
        """
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM conversation_memory WHERE session_id=%s", (session_id,))
                conn.commit()
