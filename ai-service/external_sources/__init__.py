# -*- coding: utf-8 -*-
"""
External sources package for query-driven document ingestion
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
External sources package for query-driven document ingestion
"""

from .manager import ExternalSourceManager
from .models import ExternalDocument, ExternalSearchResult

__all__ = ["ExternalSourceManager", "ExternalDocument", "ExternalSearchResult"]
