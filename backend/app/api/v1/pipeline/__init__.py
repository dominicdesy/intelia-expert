# app/api/v1/pipeline/__init__.py
"""
Pipeline package: convenient, explicit exports.

You can now:
    from app.api.v1.pipeline import DialogueManager, ClarificationManager, ContextExtractor, RAGEngine
and still:
    from app.api.v1.pipeline import dialogue_manager  # module-level import (back-compat)
"""

# --- Class-level exports (recommended) ---
from .dialogue_manager import DialogueManager
from .clarification_manager import ClarificationManager
from .context_extractor import ContextExtractor
from .rag_engine import RAGEngine

# --- Module-level exports (back-compat) ---
from . import dialogue_manager as dialogue_manager
from . import clarification_manager as clarification_manager
from . import context_extractor as context_extractor
from . import rag_engine as rag_engine
from . import memory as memory
from . import postgres_memory as postgres_memory
from . import sqlite_memory as sqlite_memory

# --- Optional: re-export policy subpackage for convenience ---
# Allows: from app.api.v1.pipeline import policy
from . import policy as policy  # contains safety_rules

__all__ = [
    # Classes
    "DialogueManager",
    "ClarificationManager",
    "ContextExtractor",
    "RAGEngine",
    # Modules (back-compat)
    "dialogue_manager",
    "clarification_manager",
    "context_extractor",
    "rag_engine",
    "memory",
    "postgres_memory",
    "sqlite_memory",
    # Subpackages
    "policy",
]
