# -*- coding: utf-8 -*-
"""
Configuration module - Configuration centralisée du projet
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Configuration module - Configuration centralisée du projet
"""

from .config import (
    # Core
    RAG_ENABLED,
    CACHE_ENABLED,
    EXTERNAL_CACHE_AVAILABLE,
    # API Keys
    OPENAI_API_KEY,
    WEAVIATE_URL,
    REDIS_URL,
    # LangSmith
    LANGSMITH_ENABLED,
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT,
    # RRF Intelligent
    ENABLE_INTELLIGENT_RRF,
    RRF_LEARNING_MODE,
    RRF_GENETIC_BOOST,
    # RAG Config
    RAG_SIMILARITY_TOP_K,
    RAG_CONFIDENCE_THRESHOLD,
    HYBRID_SEARCH_ENABLED,
    # Cache Config
    CACHE_TOTAL_MEMORY_LIMIT_MB,
    ENABLE_SEMANTIC_CACHE,
    # Fonctions
    validate_config,
    get_config_status,
)

__all__ = [
    "RAG_ENABLED",
    "CACHE_ENABLED",
    "EXTERNAL_CACHE_AVAILABLE",
    "OPENAI_API_KEY",
    "WEAVIATE_URL",
    "REDIS_URL",
    "LANGSMITH_ENABLED",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "ENABLE_INTELLIGENT_RRF",
    "RRF_LEARNING_MODE",
    "RRF_GENETIC_BOOST",
    "RAG_SIMILARITY_TOP_K",
    "RAG_CONFIDENCE_THRESHOLD",
    "HYBRID_SEARCH_ENABLED",
    "CACHE_TOTAL_MEMORY_LIMIT_MB",
    "ENABLE_SEMANTIC_CACHE",
    "validate_config",
    "get_config_status",
]
