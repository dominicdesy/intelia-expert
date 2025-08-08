from typing import Dict, Any, List
from app.api.v1.pipeline.context_extractor import ContextExtractor
from app.api.v1.pipeline.clarification_manager import ClarificationManager
from app.api.v1.pipeline.memory import ConversationMemory
from app.api.v1.pipeline.rag_engine import RAGEngine
from app.api.v1.utils.config import COMPLETENESS_THRESHOLD
from app.api.v1.utils.response_generator import format_response

class DialogueManager:
    """
    Orchestrates question -> clarification loop -> RAG -> formatting.
    """
    def __init__(self):
        self.extractor = ContextExtractor()
        self.clarifier = ClarificationManager()
        self.memory = ConversationMemory()
        self.rag = RAGEngine()

    def handle(self, session_id: str, question: str, turn: int = 1) -> Dict[str, Any]:
        # 1. Extract context
        stored = self.memory.get(session_id)
        extracted, score, missing = self.extractor.extract(question)
        # Merge with stored context
        stored.update(extracted)

        # 2. Clarification needed?
        if score < COMPLETENESS_THRESHOLD:
            questions: List[str] = self.clarifier.generate(missing, turn)
            self.memory.update(session_id, stored)
            return {"type": "clarification", "questions": questions}

        # 3. Full answer via RAG
        answer: str = self.rag.generate_answer(question, stored)
        # 4. Format and clear memory
        formatted = format_response(answer, sources=None)
        self.memory.clear(session_id)
        return {"type": "answer", "response": formatted}
