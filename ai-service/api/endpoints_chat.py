# -*- coding: utf-8 -*-
"""
api/endpoints_chat.py - Compatibility layer for refactored chat endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_chat.py - Compatibility layer for refactored chat endpoints

REFACTORED VERSION:
Original file (773 lines) has been split into focused modules.

New structure:
    api/endpoints_chat/
    ├── __init__.py                 # Main entry point
    ├── helpers.py                  # Shared helper functions
    ├── json_routes.py              # JSON system endpoints (validate, ingest, search, upload)
    ├── chat_routes.py              # Main chat endpoints (chat, expert)
    └── misc_routes.py              # Misc endpoints (ood, test, stats)

This file now serves as a thin compatibility layer to maintain backward compatibility
with existing imports.
"""

import warnings

# Import from refactored package
from .endpoints_chat import create_chat_endpoints

# Deprecation warning
warnings.warn(
    "Importing from api.endpoints_chat is supported but the implementation "
    "has been refactored into api.endpoints_chat package. "
    "Consider updating imports to: from api.endpoints_chat import create_chat_endpoints",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
__all__ = ["create_chat_endpoints"]
