# -*- coding: utf-8 -*-
"""
Central service registry for API endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Central service registry for API endpoints

Consolidates duplicate get_service() implementations found across:
- api/endpoints_chat.py
- api/endpoints.py
- api/endpoints_health.py
- api/endpoints_diagnostic.py

This module provides a consistent way to access services from FastAPI
app state throughout the API layer.

Usage:
    from api.service_registry import get_service, ServiceNotAvailableError

    # In endpoint functions
    @router.get("/example")
    async def example(request: Request):
        rag_engine = get_service(request.app.state, "rag_engine")
        # ... use rag_engine ...
"""

import logging
from utils.types import Any, Dict, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ServiceNotAvailableError(HTTPException):
    """
    Exception raised when a required service is not available

    Returns HTTP 503 Service Unavailable
    """

    def __init__(self, service_name: str, detail: Optional[str] = None):
        if detail is None:
            detail = f"Service '{service_name}' is not available"
        super().__init__(status_code=503, detail=detail)
        self.service_name = service_name


def get_service(
    app_state: Any, service_name: str, raise_on_missing: bool = True
) -> Any:
    """
    Universal service accessor for FastAPI endpoints

    Args:
        app_state: FastAPI app.state object
        service_name: Name of the service to retrieve
        raise_on_missing: If True, raise ServiceNotAvailableError when service not found

    Returns:
        The requested service instance

    Raises:
        ServiceNotAvailableError: When service not found and raise_on_missing=True

    Example:
        >>> from fastapi import Request
        >>> @router.get("/query")
        >>> async def query_endpoint(request: Request):
        >>>     rag_engine = get_service(request.app.state, "rag_engine")
        >>>     result = await rag_engine.generate_response(query)
        >>>     return result
    """
    # Try __dict__ attribute access first (most common)
    if hasattr(app_state, "__dict__"):
        service = app_state.__dict__.get(service_name)
        if service is not None:
            return service

    # Try direct attribute access
    if hasattr(app_state, service_name):
        service = getattr(app_state, service_name)
        if service is not None:
            return service

    # Service not found
    if raise_on_missing:
        logger.error(f"Service '{service_name}' not found in app state")
        raise ServiceNotAvailableError(service_name)

    return None


def get_service_from_dict(
    services: Dict[str, Any], service_name: str, raise_on_missing: bool = True
) -> Any:
    """
    Get service from a dictionary (used in endpoint factories)

    Args:
        services: Dictionary of service instances
        service_name: Name of the service to retrieve
        raise_on_missing: If True, raise ServiceNotAvailableError when service not found

    Returns:
        The requested service instance

    Raises:
        ServiceNotAvailableError: When service not found and raise_on_missing=True

    Example:
        >>> def create_endpoints(services: Dict[str, Any]):
        >>>     def get_service(name: str):
        >>>         return get_service_from_dict(services, name)
        >>>
        >>>     @router.get("/endpoint")
        >>>     async def endpoint():
        >>>         rag = get_service("rag_engine")
        >>>         return await rag.query(...)
    """
    service = services.get(service_name)

    if service is None and raise_on_missing:
        logger.error(f"Service '{service_name}' not found in services dict")
        raise ServiceNotAvailableError(service_name)

    return service


def get_rag_engine_from_health_monitor(health_monitor: Any) -> Optional[Any]:
    """
    Get RAG engine from health monitor

    This is a common pattern used across multiple endpoints where
    the RAG engine is accessed via the health monitor.

    Args:
        health_monitor: Health monitor service instance

    Returns:
        RAG engine instance or None if not available

    Example:
        >>> health_monitor = get_service(request.app.state, "health_monitor")
        >>> rag_engine = get_rag_engine_from_health_monitor(health_monitor)
        >>> if rag_engine:
        >>>     result = await rag_engine.query(...)
    """
    if health_monitor is None:
        return None

    try:
        if hasattr(health_monitor, "get_service"):
            return health_monitor.get_service("rag_engine_enhanced")
    except Exception as e:
        logger.warning(f"Failed to get RAG engine from health monitor: {e}")

    return None


__all__ = [
    "get_service",
    "get_service_from_dict",
    "get_rag_engine_from_health_monitor",
    "ServiceNotAvailableError",
]
