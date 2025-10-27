# -*- coding: utf-8 -*-
"""
api/endpoints_health.py - Compatibility layer for refactored health endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_health.py - Compatibility layer for refactored health endpoints

REFACTORED VERSION:
Original file (443 lines) has been split into focused modules.

New structure:
    api/endpoints_health/
    ├── __init__.py                 # Main entry point
    ├── helpers.py                  # Shared helper functions
    ├── basic_health.py             # Basic health check endpoint
    ├── status_routes.py            # Status endpoints (rag, dependencies, cache)
    └── metrics_routes.py           # Metrics and testing endpoints

This file now serves as a thin compatibility layer to maintain backward compatibility
with existing imports.
"""

import warnings

# Import from refactored package
from .endpoints_health import create_health_endpoints

# Deprecation warning
warnings.warn(
    "Importing from api.endpoints_health is supported but the implementation "
    "has been refactored into api.endpoints_health package. "
    "Consider updating imports to: from api.endpoints_health import create_health_endpoints",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
__all__ = ["create_health_endpoints"]
