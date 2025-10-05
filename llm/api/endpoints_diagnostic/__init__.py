# -*- coding: utf-8 -*-
"""
Diagnostic endpoints package

Refactored from monolithic endpoints_diagnostic.py (1369 lines)
Split into focused route modules for better maintainability.
"""

from fastapi import APIRouter
from utils.types import Dict, Any

from .weaviate_routes import create_weaviate_routes
from .search_routes import create_search_routes
from .rag_routes import create_rag_routes
from .helpers import get_service_from_dict


def create_diagnostic_endpoints(services: Dict[str, Any]) -> APIRouter:
    """
    Create diagnostic endpoints router

    Args:
        services: Dictionary of service instances

    Returns:
        APIRouter with all diagnostic endpoints registered
    """
    router = APIRouter()

    # Helper closure for service access
    def get_service(name: str) -> Any:
        return get_service_from_dict(services, name)

    # Register route modules
    router.include_router(create_weaviate_routes(get_service))
    router.include_router(create_search_routes(get_service))
    router.include_router(create_rag_routes(get_service))

    return router


__all__ = ["create_diagnostic_endpoints"]
