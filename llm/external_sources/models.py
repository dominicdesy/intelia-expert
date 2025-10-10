# -*- coding: utf-8 -*-
"""
Data models for external source documents and search results
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ExternalDocument:
    """
    Represents a document from an external source

    Attributes:
        title: Document title
        abstract: Document abstract/summary
        authors: List of author names
        year: Publication year
        source: Source name (semantic_scholar, pubmed, europe_pmc, fao)
        url: Document URL
        doi: DOI identifier (if available)
        pmid: PubMed ID (if available)
        pmcid: PubMed Central ID (if available)
        citation_count: Number of citations
        journal: Journal/venue name
        language: Document language (en, fr, es, etc.)
        full_text: Full text content (if available)
        relevance_score: Semantic similarity to query (0.0-1.0)
        composite_score: Final ranking score (0.0-1.0)
    """
    title: str
    abstract: str
    authors: List[str]
    year: int
    source: str
    url: str

    # Optional identifiers
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None

    # Metadata
    citation_count: int = 0
    journal: Optional[str] = None
    language: str = "en"
    full_text: Optional[str] = None

    # Scoring
    relevance_score: float = 0.0
    composite_score: float = 0.0

    # Internal
    fetched_at: datetime = field(default_factory=datetime.now)

    def get_content(self) -> str:
        """Get document content (full text if available, else abstract)"""
        if self.full_text:
            return self.full_text
        return self.abstract

    def get_unique_id(self) -> str:
        """Get unique identifier for deduplication"""
        # Prefer DOI, then PMID, then PMCID, then title+year
        if self.doi:
            return f"doi:{self.doi}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        if self.pmcid:
            return f"pmcid:{self.pmcid}"
        return f"title:{self.title.lower().strip()}:{self.year}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "year": self.year,
            "source": self.source,
            "url": self.url,
            "doi": self.doi,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "citation_count": self.citation_count,
            "journal": self.journal,
            "language": self.language,
            "relevance_score": self.relevance_score,
            "composite_score": self.composite_score,
            "fetched_at": self.fetched_at.isoformat()
        }


@dataclass
class ExternalSearchResult:
    """
    Result from searching external sources

    Attributes:
        found: Whether any results were found
        best_document: Top-ranked document (if found)
        all_documents: All ranked documents (top 5)
        sources_searched: Number of sources searched
        sources_succeeded: Number of sources that returned results
        total_results: Total results before deduplication
        unique_results: Unique results after deduplication
        search_duration_ms: Search duration in milliseconds
        query: Original query
        error: Error message (if search failed)
    """
    found: bool
    best_document: Optional[ExternalDocument] = None
    all_documents: List[ExternalDocument] = field(default_factory=list)
    sources_searched: int = 0
    sources_succeeded: int = 0
    total_results: int = 0
    unique_results: int = 0
    search_duration_ms: float = 0.0
    query: str = ""
    error: Optional[str] = None

    def has_answer(self) -> bool:
        """Check if result has a usable answer"""
        return self.found and self.best_document is not None

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for logging/monitoring"""
        return {
            "found": self.found,
            "sources_searched": self.sources_searched,
            "sources_succeeded": self.sources_succeeded,
            "total_results": self.total_results,
            "unique_results": self.unique_results,
            "search_duration_ms": self.search_duration_ms,
            "query": self.query,
            "error": self.error
        }
