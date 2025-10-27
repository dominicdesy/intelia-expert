# -*- coding: utf-8 -*-
"""
Retrieval module - Récupération et recherche de documents
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Retrieval module - Récupération et recherche de documents
Architecture modulaire avec imports corrects
"""

from .embedder import OpenAIEmbedder
from .retriever import HybridWeaviateRetriever
from .hybrid_retriever import OptimizedHybridRetriever, hybrid_search

try:
    from .enhanced_rrf_fusion import IntelligentRRFFusion

    RRF_AVAILABLE = True
except ImportError:
    IntelligentRRFFusion = None
    RRF_AVAILABLE = False

__all__ = [
    "OpenAIEmbedder",
    "HybridWeaviateRetriever",
    "OptimizedHybridRetriever",
    "hybrid_search",
    "IntelligentRRFFusion",
    "RRF_AVAILABLE",
]
