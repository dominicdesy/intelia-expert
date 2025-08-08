from typing import Dict, Any

class ConversationMemory:
    """
    Simple in-memory session store. For production, replace with Redis or a database.
    """
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}

    def get(self, session_id: str) -> Dict[str, Any]:
        return self.store.get(session_id, {})

    def update(self, session_id: str, new_context: Dict[str, Any]) -> None:
        existing = self.store.get(session_id, {})
        existing.update(new_context)
        self.store[session_id] = existing

    def clear(self, session_id: str) -> None:
        if session_id in self.store:
            del self.store[session_id]
