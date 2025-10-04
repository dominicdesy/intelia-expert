# -*- coding: utf-8 -*-
"""
Core module - Modules centraux du système RAG
"""

# NOTE IMPORTANTE: InteliaRAGEngine n'est PAS importé ici pour éviter un import circulaire.
#
# PROBLÈME: rag_engine.py charge de nombreux sous-modules pendant son initialisation
# (rag_postgresql, comparison_handler, query_preprocessor, etc.). Si on importe
# InteliaRAGEngine dans __init__.py, cela crée un cycle:
#   __init__.py → rag_engine.py → [sous-modules] → (tentative d'import depuis core) → __init__.py
#
# SOLUTION: Importer directement depuis le module:
#   from core.rag_engine import InteliaRAGEngine
#
# Au lieu de:
#   from core import InteliaRAGEngine

from .data_models import RAGResult, RAGSource, Document
from .memory import ConversationMemory
from .query_enricher import (
    ConversationalQueryEnricher,
)  # ✅ NOUVEAU - Enrichissement conversationnel

__all__ = [
    "RAGResult",
    "RAGSource",
    "Document",
    "ConversationMemory",
    "ConversationalQueryEnricher",  # ✅ NOUVEAU
]
