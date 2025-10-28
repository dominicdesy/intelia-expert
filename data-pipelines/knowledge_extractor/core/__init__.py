"""
Module principal du système d'extraction de connaissances
Contient les composants de base pour l'analyse et l'enrichissement
"""

from .models import (
    DocumentContext,
    ChunkMetadata,
    KnowledgeChunk,
    ValidationResult,
    ProcessingResult,
)
from .llm_client import LLMClient
from .document_analyzer import DocumentAnalyzer
from .content_segmenter import ContentSegmenter
from .knowledge_enricher import KnowledgeEnricher
from .intent_manager import IntentManager

__all__ = [
    "DocumentContext",
    "ChunkMetadata",
    "KnowledgeChunk",
    "ValidationResult",
    "ProcessingResult",
    "LLMClient",
    "DocumentAnalyzer",
    "ContentSegmenter",
    "KnowledgeEnricher",
    "IntentManager",
]

__version__ = "2.0.0"
