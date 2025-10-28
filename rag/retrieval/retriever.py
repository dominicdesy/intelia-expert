# -*- coding: utf-8 -*-
"""
retriever.py - Interface principale conservée pour compatibilité
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
retriever.py - Interface principale conservée pour compatibilité
Importe tout depuis les modules spécialisés
"""

# Imports depuis les modules spécialisés
from .retriever_core import HybridWeaviateRetriever
from .retriever_utils import (
    create_weaviate_retriever,
    retrieve,
    get_retrieval_metrics,
    test_retriever_capabilities,
    diagnose_retriever_issues,
    validate_retriever_corrections,
)

# Exposition de l'interface publique pour compatibilité
__all__ = [
    "HybridWeaviateRetriever",
    "create_weaviate_retriever",
    "retrieve",
    "get_retrieval_metrics",
    "test_retriever_capabilities",
    "diagnose_retriever_issues",
    "validate_retriever_corrections",
]
