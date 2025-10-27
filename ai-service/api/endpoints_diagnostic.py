# -*- coding: utf-8 -*-
"""
api/endpoints_diagnostic.py - Compatibility layer for refactored diagnostic endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_diagnostic.py - Compatibility layer for refactored diagnostic endpoints

REFACTORED VERSION:
Original file (1369 lines) has been split into focused modules.

New structure:
    api/endpoints_diagnostic/
    ├── __init__.py                 # Main entry point
    ├── helpers.py                  # Shared helper functions
    ├── weaviate_routes.py          # Weaviate diagnostic routes
    ├── search_routes.py            # Search and document routes
    └── rag_routes.py               # RAG system diagnostic routes

This file now serves as a thin compatibility layer to maintain backward compatibility
with existing imports.
"""

import warnings

# Import from refactored package
from .endpoints_diagnostic import create_diagnostic_endpoints

# Deprecation warning
warnings.warn(
    "Importing from api.endpoints_diagnostic is supported but the implementation "
    "has been refactored into api.endpoints_diagnostic package. "
    "Consider updating imports to: from api.endpoints_diagnostic import create_diagnostic_endpoints",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
__all__ = ["create_diagnostic_endpoints"]
