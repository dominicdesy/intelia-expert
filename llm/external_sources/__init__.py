# -*- coding: utf-8 -*-
"""
External sources package for query-driven document ingestion
"""

from .manager import ExternalSourceManager
from .models import ExternalDocument, ExternalSearchResult

__all__ = [
    "ExternalSourceManager",
    "ExternalDocument",
    "ExternalSearchResult"
]
