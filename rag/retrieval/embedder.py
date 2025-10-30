# -*- coding: utf-8 -*-
"""
embedder.py - Embedder OpenAI avec cache Redis externe optimisé - CORRIGÉ
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
embedder.py - Embedder OpenAI avec cache Redis externe optimisé - CORRIGÉ
"""

import logging
import os
from typing import TYPE_CHECKING
from utils.types import List
from utils.utilities import METRICS
from utils.imports_and_dependencies import AsyncOpenAI

# Type-only import for annotations
if TYPE_CHECKING:
    from openai import AsyncOpenAI as AsyncOpenAIType
else:
    AsyncOpenAIType = AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """Embedder OpenAI avec cache Redis externe optimisé"""

    def __init__(
        self,
        client: AsyncOpenAIType,
        cache_manager=None,
        model: str = None,
    ):
        self.client = client
        self.cache_manager = cache_manager
        # CORRECTION CRITIQUE: Utiliser la variable d'environnement au lieu de hardcoder
        self.model = model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"
        )

        # Support dimensions réduites pour text-embedding-3-large/small
        # Native: 3072 (optimal) | Reduced: 1536 (50% storage, -2% quality)
        self.dimensions = None
        if "text-embedding-3" in self.model:
            self.dimensions = int(os.getenv("WEAVIATE_VECTOR_DIMENSIONS", "3072"))
            logger.info(
                f"Embedder initialisé avec {self.model} (dimensions: {self.dimensions})"
            )
        else:
            logger.info(f"Embedder initialisé avec {self.model}")

    async def get_embedding(self, text: str) -> List[float]:
        """CORRECTION: Méthode manquante appelée par rag_engine.py"""
        return await self.embed_query(text)

    async def embed_query(self, text: str) -> List[float]:
        # Vérifier le cache externe
        if self.cache_manager and self.cache_manager.enabled:
            try:
                # Utiliser la méthode appropriée selon le type de cache
                if hasattr(self.cache_manager, "semantic_cache"):
                    cached_embedding = (
                        await self.cache_manager.semantic_cache.get_embedding(text)
                    )
                else:
                    cached_embedding = await self.cache_manager.get_embedding(text)

                if cached_embedding:
                    METRICS.cache_hit("embedding")
                    return cached_embedding
            except Exception as e:
                logger.warning(f"Erreur lecture cache embedding: {e}")

        try:
            # Validation du client
            if not self.client:
                logger.error("Client OpenAI non initialisé")
                return []

            # Validation de la clé API
            if not hasattr(self.client, "api_key") or not self.client.api_key:
                logger.error("Clé API OpenAI manquante")
                return []

            # Appel API OpenAI avec gestion d'erreurs détaillée
            # Support dimensions réduites pour text-embedding-3-*
            params = {"model": self.model, "input": text, "encoding_format": "float"}
            if self.dimensions:
                params["dimensions"] = self.dimensions

            response = await self.client.embeddings.create(**params)

            if not response or not response.data or len(response.data) == 0:
                logger.error("Réponse OpenAI vide ou malformée")
                return []

            embedding = response.data[0].embedding

            # Mettre en cache externe avec gestion d'erreurs
            if self.cache_manager and self.cache_manager.enabled:
                try:
                    if hasattr(self.cache_manager, "semantic_cache"):
                        await self.cache_manager.semantic_cache.set_embedding(
                            text, embedding
                        )
                    else:
                        await self.cache_manager.set_embedding(text, embedding)
                except Exception as e:
                    logger.warning(f"Erreur mise en cache embedding: {e}")

            METRICS.cache_miss("embedding")
            logger.debug(
                f"Embedding généré pour: {text[:50]}... (longueur: {len(embedding)})"
            )
            return embedding

        except Exception as e:
            logger.error(f"Erreur embedding OpenAI: {e}")
            logger.error(f"Modèle utilisé: {self.model}")
            logger.error(f"Texte (longueur {len(text)}): {text[:100]}...")

            # Log détaillé pour diagnostic
            if hasattr(e, "response"):
                logger.error(f"Réponse HTTP: {e.response}")
            if hasattr(e, "status_code"):
                logger.error(f"Status code: {e.status_code}")

            return []

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []

        # Vérifier le cache pour chaque texte
        if self.cache_manager and self.cache_manager.enabled:
            for i, text in enumerate(texts):
                try:
                    if hasattr(self.cache_manager, "semantic_cache"):
                        cached = await self.cache_manager.semantic_cache.get_embedding(
                            text
                        )
                    else:
                        cached = await self.cache_manager.get_embedding(text)

                    if cached:
                        results.append((i, cached))
                        METRICS.cache_hit("embedding")
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(i)
                except Exception as e:
                    logger.warning(f"Erreur cache pour texte {i}: {e}")
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        # Générer les embeddings manquants
        if uncached_texts:
            try:
                # Validation du client
                if not self.client:
                    logger.error("Client OpenAI non initialisé pour batch")
                    return []

                # Support dimensions réduites pour batch
                params = {
                    "model": self.model,
                    "input": uncached_texts,
                    "encoding_format": "float",
                }
                if self.dimensions:
                    params["dimensions"] = self.dimensions

                response = await self.client.embeddings.create(**params)

                if not response or not response.data:
                    logger.error("Réponse batch OpenAI vide")
                    return []

                new_embeddings = [item.embedding for item in response.data]

                # Ajouter aux résultats et mettre en cache
                for idx, embedding in zip(uncached_indices, new_embeddings):
                    if self.cache_manager and self.cache_manager.enabled:
                        try:
                            if hasattr(self.cache_manager, "semantic_cache"):
                                await self.cache_manager.semantic_cache.set_embedding(
                                    texts[idx], embedding
                                )
                            else:
                                await self.cache_manager.set_embedding(
                                    texts[idx], embedding
                                )
                        except Exception as e:
                            logger.warning(f"Erreur cache batch pour {idx}: {e}")

                    results.append((idx, embedding))
                    METRICS.cache_miss("embedding")

                logger.debug(f"Embeddings batch générés: {len(new_embeddings)} textes")

            except Exception as e:
                logger.error(f"Erreur embeddings batch: {e}")
                logger.error(f"Nombre de textes: {len(uncached_texts)}")
                if hasattr(e, "response"):
                    logger.error(f"Réponse HTTP batch: {e.response}")
                return []

        # Trier par index original
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]
