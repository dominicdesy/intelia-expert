# -*- coding: utf-8 -*-
"""
semantic_reranker.py - Re-Ranking Sémantique des Documents Récupérés

VERSION 1.0 - Améliore drastiquement Context Precision
Problème résolu: Recherche vectorielle retourne documents non pertinents
Solution: Re-ranking avec cross-encoder (+ précis que cosine similarity)

Exemple:
Query: "Quels sont les symptômes de Newcastle?"
Documents récupérés (Weaviate): 12 docs sur litière, ventilation, fibres...
Après re-ranking: Garde seulement les 2-3 docs pertinents sur Newcastle

Impact attendu sur RAGAS:
- Context Precision: 2.06% → 40-50%
- Context Recall: Stable ou amélioration
- Faithfulness: Amélioration indirecte (meilleur contexte)
"""

import logging
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SemanticReRanker:
    """
    Re-ranker sémantique utilisant cross-encoder

    Principe:
    1. Recherche vectorielle récupère 15-20 documents (recall élevé)
    2. Cross-encoder score chaque paire (query, document) avec précision
    3. Filtrage des scores faibles (< threshold)
    4. Tri et sélection top_k meilleurs

    Avantages vs cosine similarity:
    - Cross-encoder voit query + doc ensemble (pas séparément)
    - Capture interactions sémantiques fines
    - 20-30% plus précis sur tâches de ranking
    """

    def __init__(
        self,
        model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        score_threshold: float = 0.3,
        enable_caching: bool = True
    ):
        """
        Initialize semantic re-ranker

        Args:
            model_name: HuggingFace cross-encoder model
                Options:
                - 'cross-encoder/ms-marco-MiniLM-L-6-v2' (Fast, 80MB, multilingual)
                - 'cross-encoder/ms-marco-MiniLM-L-12-v2' (Better, 140MB)
                - 'cross-encoder/ms-marco-electra-base' (Best, 420MB)
            score_threshold: Minimum relevance score (0-1)
                - 0.3: Liberal (keep more docs)
                - 0.5: Balanced
                - 0.7: Strict (only very relevant)
            enable_caching: Cache scores for identical (query, doc) pairs
        """
        self.model_name = model_name
        self.score_threshold = score_threshold
        self.enable_caching = enable_caching
        self._model = None  # Lazy loading
        self._score_cache = {} if enable_caching else None

        logger.info(
            f"✅ SemanticReRanker initialized: model={model_name}, "
            f"threshold={score_threshold}, cache={enable_caching}"
        )

    @property
    def model(self):
        """Lazy load cross-encoder model"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"📥 Loading cross-encoder model: {self.model_name}...")
                self._model = CrossEncoder(self.model_name)
                logger.info("✅ Cross-encoder loaded successfully")
            except ImportError:
                logger.error(
                    "❌ sentence-transformers not installed! "
                    "Install with: pip install sentence-transformers"
                )
                raise
            except Exception as e:
                logger.error(f"❌ Failed to load cross-encoder: {e}")
                raise

        return self._model

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = 5,
        return_scores: bool = False
    ) -> List[str] | List[Tuple[str, float]]:
        """
        Re-rank documents by relevance to query

        Args:
            query: User query
            documents: List of document contents (from Weaviate)
            top_k: Number of top documents to return (None = all above threshold)
            return_scores: If True, return (doc, score) tuples

        Returns:
            If return_scores=False: List[str] of top_k documents
            If return_scores=True: List[Tuple[str, float]] of (document, score)

        Example:
            >>> reranker = SemanticReRanker()
            >>> docs = ["Doc about Newcastle disease...", "Doc about ventilation...", ...]
            >>> relevant_docs = reranker.rerank("Newcastle symptoms?", docs, top_k=3)
            >>> print(relevant_docs)
            ["Doc about Newcastle disease...", "Doc about Newcastle prevention..."]
        """
        if not documents:
            logger.warning("⚠️ Empty documents list - nothing to rerank")
            return []

        try:
            # Build (query, doc) pairs
            pairs = [(query, doc) for doc in documents]

            # Check cache for scores
            scores = []
            if self.enable_caching:
                uncached_pairs = []
                uncached_indices = []

                for idx, (q, d) in enumerate(pairs):
                    cache_key = (q, d[:200])  # Cache first 200 chars
                    if cache_key in self._score_cache:
                        scores.append(self._score_cache[cache_key])
                    else:
                        uncached_pairs.append((q, d))
                        uncached_indices.append(idx)

                # Predict only uncached
                if uncached_pairs:
                    new_scores = self.model.predict(uncached_pairs)
                    # Insert new scores at correct positions
                    for idx, score in zip(uncached_indices, new_scores):
                        scores.insert(idx, score)
                        # Cache new score
                        cache_key = (uncached_pairs[0][0], uncached_pairs[0][1][:200])
                        self._score_cache[cache_key] = score

            else:
                # Predict all scores
                scores = self.model.predict(pairs)

            logger.debug(f"📊 Scored {len(documents)} documents")

            # Combine documents with scores
            doc_score_pairs = list(zip(documents, scores))

            # Filter by threshold
            filtered = [
                (doc, float(score))
                for doc, score in doc_score_pairs
                if score >= self.score_threshold
            ]

            logger.info(
                f"🔍 Re-ranking: {len(documents)} docs → "
                f"{len(filtered)} above threshold ({self.score_threshold})"
            )

            # Sort by score (descending)
            filtered.sort(key=lambda x: x[1], reverse=True)

            # Select top_k
            if top_k is not None:
                filtered = filtered[:top_k]

            logger.info(f"✅ Returning top {len(filtered)} documents")

            # Return format
            if return_scores:
                return filtered
            else:
                return [doc for doc, score in filtered]

        except Exception as e:
            logger.error(f"❌ Re-ranking error: {e}", exc_info=True)
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
            List of document dicts, re-ranked and with 'rerank_score' added

        Example:
            >>> docs = [
            ...     {"content": "Newcastle...", "source": "medical.pdf", "page": 42},
            ...     {"content": "Ventilation...", "source": "housing.pdf", "page": 15}
            ... ]
            >>> ranked = reranker.rerank_with_metadata("Newcastle?", docs)
            >>> print(ranked[0]['rerank_score'])
            0.87
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
                doc_copy['rerank_score'] = score
                results.append(doc_copy)

        return results

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        if not self.enable_caching:
            return {"enabled": False}

        return {
            "enabled": True,
            "size": len(self._score_cache),
            "model": self.model_name
        }

    def clear_cache(self):
        """Clear score cache"""
        if self.enable_caching:
            self._score_cache.clear()
            logger.info("🗑️ Re-ranker cache cleared")


# Singleton instance (optional)
_reranker_instance = None


def get_reranker(
    model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2',
    score_threshold: float = 0.3
) -> SemanticReRanker:
    """
    Get singleton reranker instance

    Args:
        model_name: Cross-encoder model
        score_threshold: Minimum score

    Returns:
        SemanticReRanker instance
    """
    global _reranker_instance

    if _reranker_instance is None:
        _reranker_instance = SemanticReRanker(
            model_name=model_name,
            score_threshold=score_threshold
        )

    return _reranker_instance
