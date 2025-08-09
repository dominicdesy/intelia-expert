# app/api/v1/pipeline/__init__.py
"""
Pipeline package: explicit exports without subpackage re-exports to avoid circular imports.
"""

from .dialogue_manager import DialogueManager
from .clarification_manager import ClarificationManager
from .context_extractor import ContextExtractor
from .rag_engine import RAGEngine

# Optional: module-level back-compat (ok)
from . import dialogue_manager as dialogue_manager
from . import clarification_manager as clarification_manager
from . import context_extractor as context_extractor
from . import rag_engine as rag_engine
from . import memory as memory
from . import postgres_memory as postgres_memory
from . import sqlite_memory as sqlite_memory

__all__ = [
    "DialogueManager",
    "ClarificationManager",
    "ContextExtractor",
    "RAGEngine",
    "dialogue_manager",
    "clarification_manager",
    "context_extractor",
    "rag_engine",
    "memory",
    "postgres_memory",
    "sqlite_memory",
]
