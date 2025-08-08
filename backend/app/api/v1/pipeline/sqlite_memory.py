import sqlite3
import json
import threading
from typing import Dict, Any

class SQLiteMemory:
    """
    Session store backed by SQLite.
    Table schema: sessions(session_id TEXT PRIMARY KEY, context TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP).
    """
    def __init__(self, db_path: str = "./sessions.db"):
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                context     TEXT,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def get(self, session_id: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT context FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return {}
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return {}

    def update(self, session_id: str, new_context: Dict[str, Any]) -> None:
        with self._lock:
            existing = self.get(session_id)
            existing.update(new_context)
            ctx_json = json.dumps(existing)
            self.conn.execute(
                "REPLACE INTO sessions (session_id, context) VALUES (?, ?)",
                (session_id, ctx_json)
            )
            self.conn.commit()

    def clear(self, session_id: str) -> None:
        with self._lock:
            self.conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            self.conn.commit()
