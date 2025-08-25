"""
backend.rag
~~~~~~~~~~~

Initialisation du package RAG.

Objectifs :
- Éviter les imports lourds (ex: torch via sentence-transformers) au *module import time*
- Centraliser la sélection du backend d'embeddings via variables d'env
- Ré-exporter les principales classes (Retriever, Embedder/FastRAGEmbedder) si présentes
- Fournir de petites utilitaires (méthode courante, normalisation, etc.)

Variables d'environnement supportées :
- EMBEDDINGS_PROVIDER / EMBEDDING_METHOD : "OpenAI" | "FastEmbed" | "SentenceTransformers" | "TF-IDF"
- OPENAI_EMBEDDING_MODEL (ex: "text-embedding-3-small")

Par défaut en production, on recommande "OpenAI" (léger, pas de torch).
"""

from __future__ import annotations

import os
import logging
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# --- Normalisation & valeurs par défaut ---------------------------------------------------------

_AllowedMethod = Literal[
    "OpenAI",
    "FastEmbed",
    "SentenceTransformers",
    "TF-IDF",
]

_ENV_KEYS = ("EMBEDDINGS_PROVIDER", "EMBEDDING_METHOD")

_DEFAULT_METHOD: _AllowedMethod = "OpenAI"  # recommandé en prod (léger, sans torch)


def _normalize_method(value: Optional[str]) -> _AllowedMethod:
    if not value:
        return _DEFAULT_METHOD

    v = value.strip().lower().replace("_", "-")
    # alias usuels
    aliases = {
        "openai": "OpenAI",
        "oai": "OpenAI",
        "fastembed": "FastEmbed",
        "fast-embed": "FastEmbed",
        "onnx": "FastEmbed",
        "sentence-transformers": "SentenceTransformers",
        "st": "SentenceTransformers",
        "sentencetransformers": "SentenceTransformers",
        "tfidf": "TF-IDF",
        "tf-idf": "TF-IDF",
    }
    return aliases.get(v, "OpenAI")  # fallback sûr


def _ensure_env_default():
    # Si aucune des deux variables n'est définie, on force un défaut sûr.
    if not any(os.environ.get(k) for k in _ENV_KEYS):
        os.environ["EMBEDDINGS_PROVIDER"] = _DEFAULT_METHOD


_ensure_env_default()


def current_embedding_method() -> _AllowedMethod:
    """Retourne la méthode d'embeddings courante (normalisée)."""
    return _normalize_method(os.environ.get("EMBEDDINGS_PROVIDER") or os.environ.get("EMBEDDING_METHOD"))


def is_torch_free() -> bool:
    """
    Heuristique simple : True si la méthode active n'implique pas torch.
    Utile pour des décisions de runtime (logs, warnings, etc.).
    """
    return current_embedding_method() in ("OpenAI", "FastEmbed", "TF-IDF")


# --- Ré-export souple des classes clés (sans imports lourds au chargement) ----------------------

# On importe *légèrement* et sous try/except pour ne pas casser si les fichiers évoluent.
# Ces imports ne doivent pas déclencher d'import torch au module import time.
# (Assurez-vous que retriever/embedder n'importent pas sentence-transformers en top-level.)

try:
    # Exemple : votre retriever principal
    from .retriever import Retriever  # type: ignore
except Exception as e:  # pragma: no cover
    logger.debug("backend.rag: Retriever non importé au boot (%s)", e)
    Retriever = None  # type: ignore


# Certains projets ont `Embedder` ou `FastRAGEmbedder` :
_EmbedderExportName = None
try:
    # Essayez d'abord un nom "FastRAGEmbedder"
    from .embedder import FastRAGEmbedder as _Embedder  # type: ignore
    _EmbedderExportName = "FastRAGEmbedder"
except Exception:
    try:
        from .embedder import Embedder as _Embedder  # type: ignore
        _EmbedderExportName = "Embedder"
    except Exception as e:  # pragma: no cover
        logger.debug("backend.rag: Embedder non importé au boot (%s)", e)
        _Embedder = None  # type: ignore


# Exporte un nom stable si on a trouvé quelque chose
if _EmbedderExportName:
    globals()[_EmbedderExportName] = _Embedder  # type: ignore


__all__ = [
    "current_embedding_method",
    "is_torch_free",
    # exports conditionnels :
    *(["Retriever"] if "Retriever" in globals() and Retriever is not None else []),
    *([_EmbedderExportName] if _EmbedderExportName else []),
]

# --- Helpers facultatifs pour instancier sans surprendre le code appelant -----------------------

def get_retriever(*args, **kwargs):
    """
    Fabrique un Retriever en respectant la méthode d'embeddings définie par ENV.

    NB : On suppose que votre `Retriever` lit lui-même EMBEDDINGS_PROVIDER/EMBEDDING_METHOD
    lors du chargement d'un index ou de la vectorisation. Si vous avez prévu un paramètre
    explicite (ex: method="OpenAI"), vous pouvez passer `method=current_embedding_method()`
    via kwargs ici.
    """
    if Retriever is None:
        raise RuntimeError("Retriever n'est pas disponible. Vérifiez backend/rag/retriever.py.")
    # Si votre Retriever accepte `method` ou `method_override`, décommentez l'une des lignes :
    # kwargs.setdefault("method", current_embedding_method())
    # kwargs.setdefault("method_override", current_embedding_method())
    return Retriever(*args, **kwargs)  # type: ignore


def get_embedder(*args, **kwargs):
    """
    Fabrique l'embedder si disponible en gérant la compatibilité avec les nouveaux paramètres.
    Retourne None si l'embedder n'est pas disponible.
    
    Accepte et transmet les paramètres de compatibilité :
    - cache_embeddings
    - cache_max_entries  
    - max_workers
    """
    if _Embedder is None:
        return None
    
    # Gestion de la compatibilité : on passe tous les kwargs à l'embedder
    # qui se chargera de gérer les paramètres de compatibilité via **_ignored_kwargs
    kwargs.setdefault("method_override", current_embedding_method())
    
    return _Embedder(*args, **kwargs)  # type: ignore