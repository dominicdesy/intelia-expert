# -*- coding: utf-8 -*-
"""
Fetchers for external document sources
"""

from .base_fetcher import BaseFetcher
from .semantic_scholar_fetcher import SemanticScholarFetcher
from .pubmed_fetcher import PubMedFetcher
from .europe_pmc_fetcher import EuropePMCFetcher
from .fao_fetcher import FAOFetcher

__all__ = [
    "BaseFetcher",
    "SemanticScholarFetcher",
    "PubMedFetcher",
    "EuropePMCFetcher",
    "FAOFetcher"
]
