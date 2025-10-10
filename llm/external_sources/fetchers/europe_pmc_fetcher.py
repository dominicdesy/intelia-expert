# -*- coding: utf-8 -*-
"""
Europe PMC API fetcher

API Docs: https://europepmc.org/RestfulWebService
Rate limit: 5 requests/second
Coverage: 40M+ life sciences publications (overlap with PubMed + European content)
"""

import logging
from typing import List, Dict, Any
from .base_fetcher import BaseFetcher
from ..models import ExternalDocument

logger = logging.getLogger(__name__)


class EuropePMCFetcher(BaseFetcher):
    """
    Fetcher for Europe PMC REST API

    Features:
    - Strong European coverage
    - Full-text access for many articles
    - Modern JSON API
    - No API key required
    """

    def __init__(self):
        super().__init__(
            name="europe_pmc",
            base_url="https://www.ebi.ac.uk/europepmc/webservices/rest",
            rate_limit=5.0,  # 5 requests/second
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
        Make request to Europe PMC API

        Args:
            query: Search query
            max_results: Maximum results
            min_year: Minimum publication year

        Returns:
            API response JSON
        """
        url = f"{self.base_url}/search"

        # Build search query with year and poultry filter
        search_query = f"({query}) AND (poultry) AND (PUB_YEAR:[{min_year} TO 3000])"

        params = {
            "query": search_query,
            "format": "json",
            "pageSize": min(max_results, 100),  # API max is 100
            "resultType": "core",
            "sort": "CITED desc"  # Sort by citations
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
        Parse Europe PMC API response

        Args:
            response: API response JSON
            query: Original query

        Returns:
            List of ExternalDocument objects
        """
        documents = []

        results = response.get("resultList", {}).get("result", [])
        if not results:
            logger.info(f"[{self.name}] No results in response")
            return documents

        for result in results:
            try:
                # Extract basic fields
                title = result.get("title", "").strip()
                abstract = result.get("abstractText", "").strip()

                # Extract year
                pub_year = result.get("pubYear")
                try:
                    year = int(pub_year) if pub_year else None
                except (ValueError, TypeError):
                    year = None

                # Skip if missing critical fields
                if not title or not abstract or not year:
                    continue

                # Extract authors
                authors = []
                author_string = result.get("authorString", "")
                if author_string:
                    # Author string is comma-separated
                    authors = [a.strip() for a in author_string.split(",") if a.strip()]

                # Extract identifiers
                pmid = result.get("pmid")
                pmcid = result.get("pmcid")
                doi = result.get("doi")

                # Extract citations
                citation_count = result.get("citedByCount", 0)

                # Extract journal
                journal = result.get("journalTitle", "")

                # Build URL
                if pmid:
                    url = f"https://europepmc.org/article/MED/{pmid}"
                elif pmcid:
                    url = f"https://europepmc.org/article/PMC/{pmcid}"
                elif doi:
                    url = f"https://doi.org/{doi}"
                else:
                    url = ""

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
                    journal=journal,
                    language="en"
                )

                documents.append(doc)

            except Exception as e:
                logger.warning(f"[{self.name}] Failed to parse result: {e}")
                continue

        logger.info(f"[{self.name}] Parsed {len(documents)} documents")
        return documents
