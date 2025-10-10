# -*- coding: utf-8 -*-
"""
Semantic Scholar API fetcher

API Docs: https://api.semanticscholar.org/api-docs/
Rate limit: 10 requests/second (no API key needed)
Coverage: 200M+ academic papers
"""

import logging
from typing import List, Dict, Any
from .base_fetcher import BaseFetcher
from ..models import ExternalDocument

logger = logging.getLogger(__name__)


class SemanticScholarFetcher(BaseFetcher):
    """
    Fetcher for Semantic Scholar Academic Graph API

    Features:
    - Large academic coverage (200M+ papers)
    - Rich metadata (citations, influential citations, embeddings)
    - No API key required
    - Good for general scientific literature
    """

    def __init__(self):
        super().__init__(
            name="semantic_scholar",
            base_url="https://api.semanticscholar.org/graph/v1",
            rate_limit=10.0,  # 10 requests/second
            timeout=30,
            max_retries=3
        )

    async def _make_request(
        self,
        query: str,
        max_results: int,
        min_year: int
    ) -> Dict[str, Any]:
        """
        Make request to Semantic Scholar API

        Args:
            query: Search query
            max_results: Maximum results
            min_year: Minimum publication year

        Returns:
            API response JSON
        """
        url = f"{self.base_url}/paper/search"

        # Build search query with year filter
        search_query = f"{query} poultry production"

        params = {
            "query": search_query,
            "limit": min(max_results, 100),  # API max is 100
            "fields": "title,abstract,authors,year,citationCount,url,externalIds,venue,publicationTypes",
            "year": f"{min_year}-"  # Filter by year
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def _parse_response(
        self,
        response: Dict[str, Any],
        query: str
    ) -> List[ExternalDocument]:
        """
        Parse Semantic Scholar API response

        Args:
            response: API response JSON
            query: Original query

        Returns:
            List of ExternalDocument objects
        """
        documents = []

        data = response.get("data", [])
        if not data:
            logger.info(f"[{self.name}] No results in response")
            return documents

        for paper in data:
            try:
                # Extract basic fields
                title = paper.get("title", "").strip()
                abstract = paper.get("abstract", "").strip()
                year = paper.get("year")
                citation_count = paper.get("citationCount", 0)
                venue = paper.get("venue", "")
                url = paper.get("url", "")

                # Skip if missing critical fields
                if not title or not abstract or not year:
                    continue

                # Extract authors
                authors = []
                for author in paper.get("authors", []):
                    author_name = author.get("name", "")
                    if author_name:
                        authors.append(author_name)

                # Extract DOI from externalIds
                external_ids = paper.get("externalIds", {})
                doi = external_ids.get("DOI")
                pmid = external_ids.get("PubMed")
                pmcid = external_ids.get("PubMedCentral")

                # Create document
                doc = ExternalDocument(
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    year=year,
                    source=self.name,
                    url=url,
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                    citation_count=citation_count,
                    journal=venue,
                    language="en"  # Semantic Scholar is primarily English
                )

                documents.append(doc)

            except Exception as e:
                logger.warning(f"[{self.name}] Failed to parse paper: {e}")
                continue

        logger.info(f"[{self.name}] Parsed {len(documents)} documents")
        return documents
