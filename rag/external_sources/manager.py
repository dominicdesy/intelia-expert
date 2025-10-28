# -*- coding: utf-8 -*-
"""
External Source Manager - Coordinates parallel search across multiple sources
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
External Source Manager - Coordinates parallel search across multiple sources
"""

import logging
import asyncio
import time
from typing import List, Optional, Set
from openai import AsyncOpenAI

from .models import ExternalDocument, ExternalSearchResult
from .fetchers import (
    SemanticScholarFetcher,
    PubMedFetcher,
    EuropePMCFetcher,
    FAOFetcher,
)

logger = logging.getLogger(__name__)


class ExternalSourceManager:
    """
    Manages parallel search across multiple external sources

    Features:
    - Parallel search (all sources simultaneously)
    - Intelligent deduplication (DOI, PMID, title+year)
    - Composite ranking (relevance + citations + recency + source)
    - Graceful error handling (continues if one source fails)
    """

    # Source reputation weights for ranking
    SOURCE_WEIGHTS = {
        "semantic_scholar": 1.0,  # Large academic coverage
        "pubmed": 1.0,  # Peer-reviewed biomedical
        "europe_pmc": 0.9,  # Peer-reviewed + some grey literature
        "fao": 0.8,  # Authoritative but not peer-reviewed
    }

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        pubmed_api_key: Optional[str] = None,
        enable_semantic_scholar: bool = True,
        enable_pubmed: bool = True,
        enable_europe_pmc: bool = True,
        enable_fao: bool = False,  # Disabled by default (placeholder)
    ):
        """
        Initialize External Source Manager

        Args:
            openai_api_key: OpenAI API key for embeddings
            pubmed_api_key: PubMed API key for higher rate limit (optional)
            enable_*: Enable/disable specific sources
        """
        self.openai_client = (
            AsyncOpenAI(api_key=openai_api_key) if openai_api_key else AsyncOpenAI()
        )

        # Initialize fetchers
        self.sources = []

        if enable_semantic_scholar:
            self.sources.append(SemanticScholarFetcher())

        if enable_pubmed:
            self.sources.append(PubMedFetcher(api_key=pubmed_api_key))

        if enable_europe_pmc:
            self.sources.append(EuropePMCFetcher())

        if enable_fao:
            self.sources.append(FAOFetcher())

        logger.info(
            f"✅ ExternalSourceManager initialized with {len(self.sources)} sources: "
            f"{[s.name for s in self.sources]}"
        )

    async def search(
        self,
        query: str,
        language: str = "en",
        max_results_per_source: int = 5,
        min_year: int = 2015,
    ) -> ExternalSearchResult:
        """
        Search all external sources in parallel

        Args:
            query: Search query
            language: Query language (for context)
            max_results_per_source: Max results from each source
            min_year: Minimum publication year

        Returns:
            ExternalSearchResult with best document and metadata
        """
        start_time = time.time()

        logger.info(
            f"🔍 Searching {len(self.sources)} external sources for: '{query[:60]}...'"
        )

        # 1. Search all sources in parallel
        search_tasks = [
            source.search(query, max_results_per_source, min_year)
            for source in self.sources
        ]

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # 2. Flatten results and handle exceptions
        all_docs = []
        sources_succeeded = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"❌ Source {self.sources[i].name} failed: {result}")
                continue

            if result:  # List of documents
                all_docs.extend(result)
                sources_succeeded += 1

        logger.info(
            f"✅ {sources_succeeded}/{len(self.sources)} sources succeeded, "
            f"found {len(all_docs)} total documents"
        )

        if not all_docs:
            duration_ms = (time.time() - start_time) * 1000
            return ExternalSearchResult(
                found=False,
                sources_searched=len(self.sources),
                sources_succeeded=sources_succeeded,
                total_results=0,
                unique_results=0,
                search_duration_ms=duration_ms,
                query=query,
                error="No documents found in any source",
            )

        # 3. Deduplicate documents
        unique_docs = self._deduplicate(all_docs)
        logger.info(f"🔄 Deduplication: {len(all_docs)} → {len(unique_docs)} unique")

        # 4. Calculate relevance scores using embeddings
        unique_docs = await self._calculate_relevance_scores(unique_docs, query)

        # 5. Rank documents by composite score
        ranked_docs = self._rank_documents(unique_docs)

        # 6. Build result
        duration_ms = (time.time() - start_time) * 1000

        return ExternalSearchResult(
            found=True,
            best_document=ranked_docs[0],
            all_documents=ranked_docs[:5],  # Top 5
            sources_searched=len(self.sources),
            sources_succeeded=sources_succeeded,
            total_results=len(all_docs),
            unique_results=len(unique_docs),
            search_duration_ms=duration_ms,
            query=query,
        )

    def _deduplicate(self, documents: List[ExternalDocument]) -> List[ExternalDocument]:
        """
        Remove duplicate documents across sources

        Uses three methods:
        1. Exact ID matching (DOI, PMID, PMCID)
        2. Title + Year matching
        3. Semantic similarity (future enhancement)

        Args:
            documents: List of documents from all sources

        Returns:
            Deduplicated list
        """
        seen_ids: Set[str] = set()
        seen_titles: Set[tuple] = set()
        unique = []

        for doc in documents:
            # Method 1: Check unique ID (DOI, PMID, PMCID)
            unique_id = doc.get_unique_id()
            if (
                unique_id.startswith("doi:")
                or unique_id.startswith("pmid:")
                or unique_id.startswith("pmcid:")
            ):
                if unique_id in seen_ids:
                    logger.debug(f"Duplicate (ID): {doc.title[:60]}")
                    continue
                seen_ids.add(unique_id)

            # Method 2: Check title + year
            title_normalized = doc.title.lower().strip()
            title_year = (title_normalized, doc.year)

            if title_year in seen_titles:
                logger.debug(f"Duplicate (title+year): {doc.title[:60]}")
                continue

            seen_titles.add(title_year)
            unique.append(doc)

        return unique

    async def _calculate_relevance_scores(
        self, documents: List[ExternalDocument], query: str
    ) -> List[ExternalDocument]:
        """
        Calculate relevance scores using OpenAI embeddings

        Args:
            documents: List of documents
            query: Original query

        Returns:
            Documents with updated relevance_score
        """
        try:
            # Generate query embedding
            query_response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small", input=query  # Faster and cheaper
            )
            query_embedding = query_response.data[0].embedding

            # Generate document embeddings (title + abstract)
            doc_texts = [
                f"{doc.title}. {doc.abstract[:500]}"  # Limit to 500 chars
                for doc in documents
            ]

            doc_response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small", input=doc_texts
            )

            # Calculate cosine similarity
            for i, doc in enumerate(documents):
                doc_embedding = doc_response.data[i].embedding

                # Cosine similarity
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                doc.relevance_score = similarity

            logger.info(
                f"✅ Calculated relevance scores for {len(documents)} documents"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate relevance scores: {e}")
            # Set default relevance score
            for doc in documents:
                doc.relevance_score = 0.5

        return documents

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _rank_documents(
        self, documents: List[ExternalDocument]
    ) -> List[ExternalDocument]:
        """
        Rank documents by composite score

        Composite score formula:
        - Relevance: 40% (semantic similarity to query)
        - Citations: 30% (normalized by year)
        - Recency: 20% (publication year)
        - Source: 10% (source reputation)

        Args:
            documents: List of documents with relevance scores

        Returns:
            Sorted list (highest score first)
        """
        current_year = 2025

        # Calculate max citations for normalization
        max_citations = max((doc.citation_count for doc in documents), default=1)

        for doc in documents:
            # 1. Relevance score (0.0-1.0)
            relevance = doc.relevance_score

            # 2. Citations score (0.0-1.0, normalized by age)
            years_since_pub = max(current_year - doc.year, 1)
            citations_per_year = doc.citation_count / years_since_pub
            max_citations_per_year = (
                max_citations / years_since_pub if max_citations > 0 else 1
            )
            citation_score = min(citations_per_year / max_citations_per_year, 1.0)

            # 3. Recency score (0.0-1.0)
            if doc.year >= 2024:
                recency_score = 1.0
            elif doc.year >= 2020:
                recency_score = 0.8
            elif doc.year >= 2015:
                recency_score = 0.5
            else:
                recency_score = 0.2

            # 4. Source reputation score (0.0-1.0)
            source_score = self.SOURCE_WEIGHTS.get(doc.source, 0.5)

            # Composite score
            doc.composite_score = (
                relevance * 0.40
                + citation_score * 0.30
                + recency_score * 0.20
                + source_score * 0.10
            )

        # Sort by composite score (descending)
        ranked = sorted(documents, key=lambda d: d.composite_score, reverse=True)

        logger.info(
            f"📊 Top document: '{ranked[0].title[:60]}...' "
            f"(score={ranked[0].composite_score:.3f}, "
            f"relevance={ranked[0].relevance_score:.3f}, "
            f"citations={ranked[0].citation_count})"
        )

        return ranked

    async def close(self):
        """Close all fetcher clients"""
        for source in self.sources:
            await source.close()
