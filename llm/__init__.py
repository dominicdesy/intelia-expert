# -*- coding: utf-8 -*-
"""
Intelia Expert – Backend (package init)

Ce __init__ :
- Exporte les symboles publics (RAG, Intents, Prompt, OOD, Cache, Utils)
- Gère les dépendances optionnelles de façon sûre (Agent RAG)
- Fournit des helpers de base (get_version, setup_logging, load_env)

IMPORTANT:
- Évite les imports qui déclenchent des initialisations lourdes au niveau module.
- Laisse à l’application (ex: main.py) la responsabilité d’initialiser les engines.
"""

from __future__ import annotations
import logging
import os
from typing import Optional

__all__ = [
    # Version / helpers
    "get_version", "setup_logging", "load_env",

    # Intents
    "IntentType", "IntentResult", "IntentProcessor",
    "create_intent_processor", "process_query_with_intents",
    "get_intent_processor_health", "get_cache_key_from_intent",
    "get_semantic_fallback_keys", "should_use_strict_threshold",
    "get_guardrails_context", "test_query_processing", "SAMPLE_TEST_QUERIES",

    # RAG Engine
    "InteliaRAGEngine", "create_rag_engine", "RAGResult", "RAGSource",

    # Agent RAG (optionnel)
    "InteliaAgentRAG", "create_agent_rag_engine", "AgentResult", "QueryComplexity",

    # Prompting / OOD / Memory / Cache / Utils
    "PromptBuilder", "EnhancedOODDetector", "ConversationMemory",
    "METRICS", "RedisCacheManager",
]

# ---------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------
__version__ = "2.3.0"

def get_version() -> str:
    """Retourne la version du package."""
    return __version__

# ---------------------------------------------------------------------
# Helpers “safe” au niveau package
# ---------------------------------------------------------------------
def setup_logging(level: int | str = logging.INFO) -> None:
    """
    Configure un logging simple si rien n’est déjà configuré.
    N’écrase pas une config existante.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level)
    else:
        root.setLevel(level)

def load_env(env_file: Optional[str] = None) -> None:
    """
    Charge les variables d’environnement depuis un .env si présent.
    Ne plante pas si python-dotenv est absent.
    """
    if env_file is None:
        env_file = os.getenv("ENV_FILE", ".env")
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(env_file)
    except Exception:
        # Optionnel : pas critique si indisponible
        pass

# ---------------------------------------------------------------------
# Exports Intents
# ---------------------------------------------------------------------
# On importe d’abord les types (simples) pour réduire les risques de cycles.
from .intent_types import IntentType, IntentResult  # noqa: E402

# Le processeur importe lui-même utils en interne (compat maintenue).
from .intent_processor import (  # noqa: E402
    IntentProcessor,
    create_intent_processor,
    process_query_with_intents,
    get_intent_processor_health,
    get_cache_key_from_intent,
    get_semantic_fallback_keys,
    should_use_strict_threshold,
    get_guardrails_context,
    test_query_processing,
    SAMPLE_TEST_QUERIES,
)

# ---------------------------------------------------------------------
# Exports RAG Engine (cœur)
# ---------------------------------------------------------------------
from .rag_engine import (  # noqa: E402
    InteliaRAGEngine,
    create_rag_engine,
    RAGResult,
    RAGSource,
)

# ---------------------------------------------------------------------
# Agent RAG – optionnel (ne doit jamais faire planter l’import du package)
# ---------------------------------------------------------------------
try:
    from .agent_rag_extension import (  # noqa: E402
        InteliaAgentRAG,
        create_agent_rag_engine,
        AgentResult,
        QueryComplexity,
    )
except Exception:
    # Fournit des stubs légers pour ne pas casser l’autocomplétion/import
    class QueryComplexity:
        SIMPLE = "simple"
        COMPLEX = "complex"

    class AgentResult:  # minimal stub
        pass

    InteliaAgentRAG = None          # type: ignore
    create_agent_rag_engine = None  # type: ignore

# ---------------------------------------------------------------------
# Prompting / OOD / Memory / Cache / Utils
# ---------------------------------------------------------------------
from .prompt_builder import PromptBuilder  # noqa: E402
from .ood_detector import EnhancedOODDetector  # noqa: E402
from .memory import ConversationMemory  # noqa: E402
from .utilities import METRICS  # noqa: E402
from .redis_cache_manager import RedisCacheManager  # noqa: E402

# NOTE: D’autres modules (retriever, hybrid_retriever, embedder, etc.)
# peuvent être importés directement par les consommateurs si nécessaire,
# pour éviter d’alourdir l’espace de noms public ici.
