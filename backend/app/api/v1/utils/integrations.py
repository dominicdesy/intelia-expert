# app/api/v1/utils/integrations.py
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

logger = logging.getLogger("app.api.v1.utils.integrations")

# ========== NOUVEAU: IMPORT DE LA FONCTION COMPLETE SÉCURISÉE ==========
try:
    from ..utils.openai_utils import complete
    OPENAI_UTILS_AVAILABLE = True
    logger.info("✅ OpenAI utils sécurisés importés pour integrations")
except ImportError as e:
    logger.warning(f"⚠️ OpenAI utils non disponibles dans integrations: {e}")
    OPENAI_UTILS_AVAILABLE = False

# --------------------------------------------------------------------
# Wrappers OpenAI (exemples; gardez vos propres fonctions si existantes)
# --------------------------------------------------------------------

async def safe_chat_create(**kwargs) -> Dict[str, Any]:
    """
    Wrapper chat completions MODIFIÉ pour utiliser la fonction complete() sécurisée.
    Conserve la compatibilité avec l'API existante.
    NOUVEAU: Gestion automatique max_completion_tokens via openai_utils.complete()
    """
    # ========== NOUVEAU: UTILISATION DE LA FONCTION COMPLETE SÉCURISÉE ==========
    if OPENAI_UTILS_AVAILABLE:
        try:
            # Extraire les paramètres de l'appel original
            messages = kwargs.get('messages', [])
            model = kwargs.get('model')
            temperature = kwargs.get('temperature', 0.2)
            max_tokens = kwargs.get('max_tokens')
            
            # Convertir messages en prompt pour complete()
            if messages:
                # Construire un prompt à partir des messages
                prompt_parts = []
                for msg in messages:
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role == 'system':
                        prompt_parts.append(f"Instructions: {content}")
                    elif role == 'user':
                        prompt_parts.append(f"Question: {content}")
                    elif role == 'assistant':
                        prompt_parts.append(f"Réponse: {content}")
                
                prompt = "\n\n".join(prompt_parts)
                
                if prompt.strip():
                    # Utiliser la nouvelle fonction complete() sécurisée
                    logger.debug("🔒 Utilisation complete() sécurisé avec gestion max_completion_tokens")
                    response_text = complete(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        model=model
                    )
                    
                    # Formatter en réponse compatible OpenAI
                    return {
                        "choices": [{
                            "message": {
                                "content": response_text,
                                "role": "assistant"
                            },
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": len(prompt.split()) * 1.3,  # Estimation
                            "completion_tokens": len(response_text.split()) * 1.3,
                            "total_tokens": len((prompt + response_text).split()) * 1.3
                        }
                    }
            
            logger.warning("⚠️ Aucun message valide trouvé, fallback vers httpx")
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur avec complete() sécurisé, fallback vers httpx: {e}")
    
    # ========== FALLBACK: CODE ORIGINAL HTTPX (INCHANGÉ) ==========
    logger.debug("📡 Fallback vers appel httpx direct")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY','')}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=kwargs)
        r.raise_for_status()
        return r.json()

async def safe_embedding_create(*, model: str, input: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Retourne directement la/les listes de floats (embedding(s)).
    CODE ORIGINAL INCHANGÉ - Les embeddings ne sont pas affectés par max_completion_tokens

    - Si input est str  -> retourne List[float]
    - Si input est list -> retourne List[List[float]]
    """
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY','')}",
        "Content-Type": "application/json"
    }
    payload = {"model": model, "input": input}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    # Normalisation en sortie:
    if not data or "data" not in data or not data["data"]:
        logger.error("❌ Embedding API returned empty data")
        return []  # le caller gérera

    vectors = [item.get("embedding") for item in data["data"] if item.get("embedding") is not None]
    if not vectors:
        logger.error("❌ Embedding API: no embedding vectors found")
        return []

    # Simplifier si un seul input
    return vectors[0] if isinstance(input, str) else vectors


# --------------------------------------------------------------------
# Client VectorStore (Faiss/Pinecone wrapper) - CODE ORIGINAL INCHANGÉ
# --------------------------------------------------------------------

class VectorStoreClient:
    """
    Client d'accès à l'index vectoriel. Le but ici est d'ACCEPTER 2 formats:
      - Liste de floats renvoyée par safe_embedding_create (chemin normal)
      - Réponse brute OpenAI (rare si on bypass le wrapper)
    """
    def __init__(self, index_backend: Any):
        self.index = index_backend  # ex. votre wrapper FAISS/Pinecone

    async def query(self, text: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retourne une liste de documents: [{id, score, text, meta}, ...]
        """
        try:
            model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            resp = await safe_embedding_create(model=model_name, input=text)

            emb: Optional[List[float]] = None

            # --- Cas 1: chemin normalisé (liste de floats)
            if isinstance(resp, list) and resp and all(isinstance(x, (int, float)) for x in resp):
                emb = resp

            # --- Cas 2: "à tout hasard" si quelqu'un appelle encore l'API brute ailleurs
            elif isinstance(resp, dict) and "data" in resp and resp["data"]:
                maybe = resp["data"][0].get("embedding")
                if isinstance(maybe, list):
                    emb = maybe

            # --- Cas 3: liste de listes (input = batch)
            elif isinstance(resp, list) and resp and isinstance(resp[0], list):
                emb = resp[0]

            if emb is None or not emb:
                logger.error("❌ Réponse OpenAI embedding vide ou malformée")
                return []

            # À ce stade emb est une List[float] exploitable
            # On interroge l'index (faiss/pinecone) — à adapter à votre backend
            results = self.index.search(emb, k=k)  # attendu: List[Dict]
            # Exemple attendu d'un item: {"id": "...", "score": 0.87, "text": "...", "meta": {...}}
            if not isinstance(results, list):
                logger.error("❌ Vector index returned a non-list result")
                return []

            return results

        except httpx.HTTPStatusError as he:
            logger.error("❌ OpenAI HTTP error (embeddings): %s", he)
            return []
        except Exception as e:
            logger.exception("❌ VectorStoreClient.query unexpected error: %s", e)
            return []
