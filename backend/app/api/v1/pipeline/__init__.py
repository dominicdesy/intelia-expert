# app/api/v1/pipeline/__init__.py
"""
Public API for the v1.pipeline package.

We expose function-level entry points matching the current implementation:
- handle(): main orchestrator (dialogue_manager)
- compute_completeness(): completeness & clarifications (clarification_manager)
- normalize(): entity normalization (context_extractor)
- answer_with_rag(): RAG retrieval (rag_engine)

Backward-compatibility shims:
- DialogueManager.handle -> handle
- ClarificationManager.compute -> compute_completeness
- ContextExtractor.normalize -> normalize
- RAGEngine.answer -> answer_with_rag
"""

from .dialogue_manager import handle as handle
from .clarification_manager import compute_completeness as compute_completeness
from .context_extractor import normalize as normalize
from .rag_engine import answer_with_rag as answer_with_rag

# --- Backward-compat shims (keep old imports working) ---

class DialogueManager:
    @staticmethod
    def handle(session_id, question, lang: str = "fr"):
        return handle(session_id, question, lang)

class ClarificationManager:
    @staticmethod
    def compute(intent, entities):
        return compute_completeness(intent, entities)

class ContextExtractor:
    @staticmethod
    def normalize(context):
        return normalize(context)

class RAGEngine:
    @staticmethod
    def answer(question, entities, intent=None):
        return answer_with_rag(question, entities, intent)

__all__ = [
    # New API (functions)
    "handle",
    "compute_completeness",
    "normalize",
    "answer_with_rag",
    # Legacy API (shim classes)
    "DialogueManager",
    "ClarificationManager",
    "ContextExtractor",
    "RAGEngine",
]
