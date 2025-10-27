# -*- coding: utf-8 -*-
"""
PubMed E-utilities API fetcher
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
PubMed E-utilities API fetcher

API Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
Rate limit: 3 requests/second (10 with API key)
Coverage: 35M+ biomedical publications
"""

import logging
import defusedxml.ElementTree as ET
from typing import List, Dict, Any
from .base_fetcher import BaseFetcher
from ..models import ExternalDocument

logger = logging.getLogger(__name__)


class PubMedFetcher(BaseFetcher):
    """
    Fetcher for PubMed E-utilities API

    Features:
    - Focus on biomedical and life sciences (perfect for poultry health)
    - Peer-reviewed publications
    - MeSH terms for precise classification
    - Free API (optional key for higher rate limit)
    """

    def __init__(self, api_key: str = None):
        super().__init__(
            name="pubmed",
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            rate_limit=10.0 if api_key else 3.0,  # 10/s with key, 3/s without
            timeout=30,
            max_retries=3
        )
        self.api_key = api_key

    async def _make_request(
        self,
        query: str,
        max_results: int,
        min_year: int
    ) -> Dict[str, Any]:
        """
        Make request to PubMed E-utilities API

        Uses two-step process:
        1. ESearch: Search for PMIDs matching query
        2. EFetch: Fetch full metadata for PMIDs

        Args:
            query: Search query
            max_results: Maximum results
            min_year: Minimum publication year

        Returns:
            Combined results dict with PMIDs and metadata
        """
        # Step 1: ESearch - Get PMIDs with strict poultry filtering
        # NEW: More specific poultry terms AND exclude non-poultry animals
        poultry_terms = "(poultry[Title/Abstract] OR chicken[Title/Abstract] OR broiler[Title/Abstract] OR layer[Title/Abstract] OR avian[Title/Abstract])"
        exclude_terms = "NOT (cattle[Title/Abstract] OR bovine[Title/Abstract] OR cow[Title/Abstract] OR dairy[Title/Abstract] OR pig[Title/Abstract] OR swine[Title/Abstract])"

        search_query = f"{query} AND {poultry_terms} {exclude_terms} AND {min_year}:3000[DP]"

        search_url = f"{self.base_url}/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": search_query,
            "retmax": min(max_results, 100),  # API limit
            "retmode": "json",
            "sort": "relevance"
        }

        if self.api_key:
            search_params["api_key"] = self.api_key

        search_response = await self.client.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()

        # Extract PMIDs
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            logger.info(f"[{self.name}] No PMIDs found")
            return {"pmids": [], "articles": []}

        logger.info(f"[{self.name}] Found {len(pmids)} PMIDs")

        # Step 2: EFetch - Get full metadata for PMIDs
        fetch_url = f"{self.base_url}/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }

        if self.api_key:
            fetch_params["api_key"] = self.api_key

        # Rate limit between requests
        await self._rate_limit()

        fetch_response = await self.client.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status()

        # Parse XML response
        xml_content = fetch_response.text

        return {
            "pmids": pmids,
            "xml_content": xml_content
        }

    def _parse_response(
        self,
        response: Dict[str, Any],
        query: str
    ) -> List[ExternalDocument]:
        """
        Parse PubMed XML response

        Args:
            response: API response with XML content
            query: Original query

        Returns:
            List of ExternalDocument objects
        """
        documents = []

        xml_content = response.get("xml_content")
        if not xml_content:
            return documents

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"[{self.name}] XML parse error: {e}")
            return documents

        # Parse each article
        for article in root.findall(".//PubmedArticle"):
            try:
                # Extract PMID
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else None

                # Extract title
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""
                title = title.strip()

                # Extract abstract
                abstract_parts = []
                for abstract_text in article.findall(".//AbstractText"):
                    if abstract_text.text:
                        abstract_parts.append(abstract_text.text)
                abstract = " ".join(abstract_parts).strip()

                # Extract year
                year_elem = article.find(".//PubDate/Year")
                if year_elem is None:
                    year_elem = article.find(".//PubDate/MedlineDate")
                year = None
                if year_elem is not None and year_elem.text:
                    year_text = year_elem.text.strip()
                    try:
                        year = int(year_text[:4])  # Extract first 4 digits
                    except ValueError:
                        pass

                # Skip if missing critical fields
                if not title or not abstract or not year:
                    continue

                # Extract authors
                authors = []
                for author in article.findall(".//Author"):
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None and lastname.text:
                        author_name = lastname.text
                        if forename is not None and forename.text:
                            author_name = f"{forename.text} {lastname.text}"
                        authors.append(author_name)

                # Extract journal
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""

                # Extract DOI
                doi = None
                for article_id in article.findall(".//ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text
                        break

                # Build URL
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

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
                    citation_count=0,  # PubMed doesn't provide citation counts
                    journal=journal,
                    language="en"
                )

                documents.append(doc)

            except Exception as e:
                logger.warning(f"[{self.name}] Failed to parse article: {e}")
                continue

        logger.info(f"[{self.name}] Parsed {len(documents)} documents")
        return documents
