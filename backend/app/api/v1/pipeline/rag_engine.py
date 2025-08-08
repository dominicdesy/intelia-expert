import os
from typing import Dict, Any, List
from app.api.v1.utils.integrations import VectorStoreClient
from app.api.v1.utils.openai_utils import safe_chat_completion

class RAGEngine:
    """
    Wraps the Retrieval-Augmented Generation call.
    """
    def __init__(self):
        # Initialize the vector store client without placeholder params
        self.vector_client = VectorStoreClient()

    def generate_answer(self, question: str, context: Dict[str, Any]) -> str:
        # 1. Retrieval
        docs: List[Any] = self.vector_client.query(question)
        # 2. Prompt construction
        prompt = (
            f"Contexte: {context}\n"
            f"Documents: {docs}\n"
            f"Question: {question}\nRéponse:"
        )
        # 3. ChatCompletion with retry
        response = safe_chat_completion(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
