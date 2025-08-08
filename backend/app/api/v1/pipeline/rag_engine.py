import os
from typing import Dict, Any, List
import openai
from app.api.v1.utils.integrations import VectorStoreClient

class RAGEngine:
    """
    Wraps the retrieval-augmented generation call.
    """
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.vector_client = VectorStoreClient(
            url=os.getenv("VECTOR_STORE_URL"),
            key=os.getenv("VECTOR_STORE_KEY")
        )

    def generate_answer(self, question: str, context: Dict[str, Any]) -> str:
        # Retrieve relevant documents from the vector store
        docs: List[Any] = self.vector_client.query(question)
        # Construct prompt
        prompt = (
            f"Contexte: {context}\n"
            f"Documents: {docs}\n"
            f"Question: {question}\n"
            "Réponse:"  
        )
        # Call OpenAI ChatCompletion
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
