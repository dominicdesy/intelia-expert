# -*- coding: utf-8 -*-
"""
embedder.py - Embedder OpenAI avec cache Redis externe optimisé
"""

import logging
from typing import List
from utils.utilities import METRICS
from utils.imports_and_dependencies import AsyncOpenAI

logger = logging.getLogger(__name__)

class OpenAIEmbedder:
    """Embedder OpenAI avec cache Redis externe optimisé"""
    
    def __init__(self, client: AsyncOpenAI, cache_manager = None, 
                 model: str = "text-embedding-3-small"):
        self.client = client
        self.cache_manager = cache_manager
        self.model = model
        
    async def embed_query(self, text: str) -> List[float]:
        # Vérifier le cache externe
        if self.cache_manager and self.cache_manager.enabled:
            cached_embedding = await self.cache_manager.get_embedding(text)
            if cached_embedding:
                METRICS.cache_hit("embedding")
                return cached_embedding
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            
            # Mettre en cache externe
            if self.cache_manager and self.cache_manager.enabled:
                await self.cache_manager.set_embedding(text, embedding)
            
            METRICS.cache_miss("embedding")
            return embedding
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            return []
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # Vérifier le cache pour chaque texte
        if self.cache_manager and self.cache_manager.enabled:
            for i, text in enumerate(texts):
                cached = await self.cache_manager.get_embedding(text)
                if cached:
                    results.append((i, cached))
                    METRICS.cache_hit("embedding")
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        # Générer les embeddings manquants
        if uncached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                    encoding_format="float"
                )
                new_embeddings = [item.embedding for item in response.data]
                
                # Ajouter aux résultats et mettre en cache
                for idx, embedding in zip(uncached_indices, new_embeddings):
                    if self.cache_manager and self.cache_manager.enabled:
                        await self.cache_manager.set_embedding(texts[idx], embedding)
                    results.append((idx, embedding))
                    METRICS.cache_miss("embedding")
            except Exception as e:
                logger.error(f"Erreur embeddings batch: {e}")
                return []
        
        # Trier par index original
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]