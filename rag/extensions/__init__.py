# -*- coding: utf-8 -*-
"""
Extensions module - Extensions optionnelles du système
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Extensions module - Extensions optionnelles du système
"""

try:
    from .agent_rag_extension import (
        InteliaAgentRAG,
        AgentResult,
        QueryComplexity,
        create_agent_rag_engine,
        process_query_with_agent,
    )

    AGENT_RAG_AVAILABLE = True
except ImportError:
    AGENT_RAG_AVAILABLE = False
    InteliaAgentRAG = None
    AgentResult = None
    QueryComplexity = None
    create_agent_rag_engine = None
    process_query_with_agent = None

__all__ = [
    "InteliaAgentRAG",
    "AgentResult",
    "QueryComplexity",
    "create_agent_rag_engine",
    "process_query_with_agent",
    "AGENT_RAG_AVAILABLE",
]
