import os
from app.api.v1.utils.integrations import VectorStoreClient
from app.api.v1.utils.openai_utils import safe_chat_completion

class RAGEngine:
    """
    Retrieval-Augmented Generation engine with fallback if no vector results.
    """
    def __init__(self):
        self.vector_client = VectorStoreClient()

    def generate_answer(self, question, context):
        docs = self.vector_client.query(question)
        if not docs:
            # Fallback: prompt GPT without retrieved docs
            fallback_prompt = (
                "Vous êtes un assistant avicole. "
                "Je n'ai pas trouvé de documentation précise pour cette question, mais essayez d'aider au mieux.\n"
                f"Question: {question}\nContexte: {context}"
            )
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": fallback_prompt}],
                temperature=0.0,
                max_tokens=512
            )
            return resp.choices[0].message.content.strip()
        # Else, provide docs as context to GPT
        doc_content = "\n".join(str(d) for d in docs)
        rag_prompt = (
            "Vous êtes un assistant avicole. "
            "Utilisez uniquement les informations suivantes pour répondre de façon précise et factuelle.\n"
            f"DOCUMENTS:\n{doc_content}\n"
            f"QUESTION: {question}\nContexte: {context}"
        )
        resp = safe_chat_completion(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": rag_prompt}],
            temperature=0.0,
            max_tokens=512
        )
        return resp.choices[0].message.content.strip()
