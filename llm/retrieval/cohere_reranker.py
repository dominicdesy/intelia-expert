# -*- coding: utf-8 -*-
"""
cohere_reranker.py - Cohere API Re-Ranking (Production-Grade)
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
cohere_reranker.py - Cohere API Re-Ranking (Production-Grade)

VERSION 1.0 - Alternative to MS-MARCO cross-encoder
Uses Cohere's rerank-multilingual-v3.0 model for superior re-ranking

Advantages over cross-encoder/ms-marco:
- Multilingual native support (French, Spanish, English)
- Better understanding of domain-specific terminology
- API-based (no local model loading, faster cold start)
- Production-grade reliability

Cost: ~$1 per 1000 searches (acceptable for production)

Example:
    Query: "Quel poids Ross 308 mâle 35 jours?"
    Docs: 50 documents from Weaviate
    Cohere filters: 50 → 5 most relevant documents
    Expected improvement: Context Precision +20-30%
"""

import logging
import os
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class CohereReRanker:
    """
    Re-ranker using Cohere API (rerank-multilingual-v3.0)

    Benefits:
    - Multilingual: French, Spanish, English native support
    - Domain understanding: Better than MS-MARCO for specialized terms
    - No local model: API-based, faster cold start
    - Production-grade: Reliable, scalable

    Cost:
    - $1 per 1000 searches (3000 docs max per search)
    - Typical usage: 100 searches/day = $3/month
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'rerank-multilingual-v3.0',
        enable_caching: bool = True
    ):
        """
        Initialize Cohere re-ranker

        Args:
            api_key: Cohere API key (defaults to COHERE_API_KEY env var)
            model: Cohere rerank model
                - 'rerank-multilingual-v3.0' (recommended, multilingual)
                - 'rerank-english-v3.0' (English only, slightly faster)
            enable_caching: Cache results for identical (query, doc) pairs
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self.model = model
        self.enable_caching = enable_caching
        self._client = None  # Lazy loading
        self._cache = {} if enable_caching else None

        if not self.api_key:
            logger.warning(
                "⚠️ COHERE_API_KEY not set! Cohere re-ranker will NOT work. "
                "Set environment variable: COHERE_API_KEY=your_key"
            )

        logger.info(
            f"✅ CohereReRanker initialized: model={model}, cache={enable_caching}"
        )

    @property
    def client(self):
        """Lazy load Cohere client"""
        if self._client is None:
            try:
                import cohere
                self._client = cohere.Client(api_key=self.api_key)
                logger.info("✅ Cohere client loaded successfully")
            except ImportError:
                logger.error(
                    "❌ cohere package not installed! "
                    "Install with: pip install cohere>=5.0.0"
                )
                raise
            except Exception as e:
                logger.error(f"❌ Failed to initialize Cohere client: {e}")
                raise

        return self._client

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = 5,
        return_scores: bool = False
    ) -> List[str] | List[Tuple[str, float]]:
        """
        Re-rank documents by relevance to query using Cohere API

        Args:
            query: User query
            documents: List of document contents (from Weaviate)
            top_k: Number of top documents to return (None = all)
            return_scores: If True, return (doc, score) tuples

        Returns:
            If return_scores=False: List[str] of top_k documents
            If return_scores=True: List[Tuple[str, float]] of (document, relevance_score)

        Example:
            >>> reranker = CohereReRanker()
            >>> docs = ["Doc about Ross 308...", "Doc about ventilation...", ...]
            >>> relevant_docs = reranker.rerank("Ross 308 weight?", docs, top_k=3)
            >>> print(relevant_docs)
            ["Doc about Ross 308 performance...", "Doc about Ross 308 nutrition..."]
        """
        if not documents:
            logger.warning("⚠️ Empty documents list - nothing to rerank")
            return []

        if not self.api_key:
            logger.error("❌ COHERE_API_KEY not set - cannot rerank!")
            # Fallback: return original documents
            if top_k:
                return documents[:top_k]
            return documents

        try:
            # Check cache
            cache_key = None
            if self.enable_caching:
                cache_key = (query, tuple(doc[:200] for doc in documents))
                if cache_key in self._cache:
                    cached_results = self._cache[cache_key]
                    logger.info(f"✅ Cache hit for query: {query[:50]}...")
                    if top_k:
                        cached_results = cached_results[:top_k]
                    if return_scores:
                        return cached_results
                    return [doc for doc, score in cached_results]

            logger.info(
                f"📡 Calling Cohere API: query='{query[:50]}...', "
                f"num_docs={len(documents)}, top_k={top_k}"
            )

            # Call Cohere rerank API
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_k if top_k else len(documents),
                return_documents=True
            )

            # Extract results
            results = [
                (result.document.text, result.relevance_score)
                for result in response.results
            ]

            logger.info(
                f"✅ Cohere re-ranking: {len(documents)} docs → {len(results)} relevant docs"
            )

            # Cache results
            if self.enable_caching and cache_key:
                self._cache[cache_key] = results

            # Return format
            if return_scores:
                return results
            else:
                return [doc for doc, score in results]

        except Exception as e:
            logger.error(f"❌ Cohere re-ranking error: {e}", exc_info=True)
            # Fallback: return original documents (no filtering)
            logger.warning("⚠️ Returning original documents (no re-ranking)")
            if top_k:
                return documents[:top_k]
            return documents

    def rerank_with_metadata(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        content_key: str = 'content',
        top_k: Optional[int] = 5
    ) -> List[Dict[str, Any]]:
        """
        Re-rank documents with metadata preservation

        Useful when documents are dicts with metadata (e.g., from Weaviate)

        Args:
            query: User query
            documents: List of document dicts (must have content_key)
            content_key: Key containing document text
            top_k: Number of top documents to return

        Returns:
            List of document dicts, re-ranked and with 'cohere_score' added

        Example:
            >>> docs = [
            ...     {"content": "Ross 308...", "source": "guide.pdf", "page": 42},
            ...     {"content": "Ventilation...", "source": "housing.pdf", "page": 15}
            ... ]
            >>> ranked = reranker.rerank_with_metadata("Ross 308?", docs)
            >>> print(ranked[0]['cohere_score'])
            0.92
        """
        if not documents:
            return []

        # Extract contents
        contents = [doc.get(content_key, "") for doc in documents]

        # Re-rank
        ranked_pairs = self.rerank(query, contents, top_k=top_k, return_scores=True)

        # Match back to original documents
        content_to_doc = {doc.get(content_key, ""): doc for doc in documents}

        # Build result with scores
        results = []
        for content, score in ranked_pairs:
            doc = content_to_doc.get(content)
            if doc:
                doc_copy = doc.copy()
                doc_copy['cohere_score'] = score
                results.append(doc_copy)

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enable_caching:
            return {"enabled": False}

        return {
            "enabled": True,
            "size": len(self._cache),
            "model": self.model
        }

    def clear_cache(self):
        """Clear cache"""
        if self.enable_caching:
            self._cache.clear()
            logger.info("🗑️ Cohere re-ranker cache cleared")


# Singleton instance (optional)
_cohere_reranker_instance = None


def get_cohere_reranker(
    api_key: Optional[str] = None,
    model: str = 'rerank-multilingual-v3.0'
) -> CohereReRanker:
    """
    Get singleton Cohere reranker instance

    Args:
        api_key: Cohere API key
        model: Cohere rerank model

    Returns:
        CohereReRanker instance
    """
    global _cohere_reranker_instance

    if _cohere_reranker_instance is None:
        _cohere_reranker_instance = CohereReRanker(
            api_key=api_key,
            model=model
        )

    return _cohere_reranker_instance
