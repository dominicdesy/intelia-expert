# -*- coding: utf-8 -*-
"""
api/endpoints_health/__init__.py - Main entry point for health endpoints
Exports the factory function to create all health-related routes
"""

from utils.types import Dict, Any
from fastapi import APIRouter

from .basic_health import create_basic_health_routes
from .status_routes import create_status_routes
from .metrics_routes import create_metrics_routes
from .prometheus_routes import create_prometheus_routes


def create_health_endpoints(services: Dict[str, Any]) -> APIRouter:
    """
    Creates all health-related endpoints by combining modular route factories

    Args:
        services: Dictionary of service instances

    Returns:
        APIRouter: Combined router with all health endpoints
    """
    router = APIRouter()

    def get_service(name: str) -> Any:
        """Helper to retrieve a service from the services dictionary"""
        return services.get(name)

    # Include all health-related route modules
    router.include_router(create_basic_health_routes(get_service))
    router.include_router(create_status_routes(get_service))
    router.include_router(create_metrics_routes(get_service))
    router.include_router(create_prometheus_routes(get_service))

    return router


# Export the main factory function
__all__ = ["create_health_endpoints"]
