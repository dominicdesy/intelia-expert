import os
from typing import Any, List
from supabase import create_client, Client


class VectorStoreClient:
    """
    Client for querying a vector database of documents.
    """
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        # Initialize actual client if available

    def query(self, text: str) -> List[Any]:
        # Placeholder: integrate with your vector store
        return []


class SupabaseClient:
    """
    Wrapper around Supabase for persistence/logging.
    """
    def __init__(self):
        self.client: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    def insert_log(self, table: str, record: Dict[str, Any]) -> Any:
        return self.client.table(table).insert(record).execute()
