# -*- coding: utf-8 -*-
"""
Middleware package for Intelia Expert API
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Middleware package for Intelia Expert API
Contains authentication and other middleware components
"""

from .auth_middleware import (
    verify_supabase_token,
    optional_auth,
    auth_middleware,
    PUBLIC_ENDPOINTS,
)

__all__ = [
    "verify_supabase_token",
    "optional_auth",
    "auth_middleware",
    "PUBLIC_ENDPOINTS",
]
