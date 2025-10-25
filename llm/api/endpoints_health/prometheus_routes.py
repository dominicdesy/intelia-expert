# -*- coding: utf-8 -*-
"""
api/endpoints_health/prometheus_routes.py - Prometheus metrics endpoint
"""

import logging
from fastapi import APIRouter, Response
from utils.types import Callable

logger = logging.getLogger(__name__)


def create_prometheus_routes(get_service: Callable) -> APIRouter:
    """Creates Prometheus metrics endpoint"""

    router = APIRouter()

    @router.get("/metrics")
    async def prometheus_metrics():
        """
        Export Prometheus metrics for Grafana

        Returns metrics in Prometheus text format:
        - LLM costs and token usage
        - RAG performance
        - System metrics
        """
        try:
            from monitoring.prometheus_metrics import generate_metrics, get_content_type

            # Generate Prometheus format
            metrics_output = generate_metrics()
            return Response(content=metrics_output, media_type=get_content_type())

        except Exception as e:
            logger.error(f"Error generating Prometheus metrics: {e}")
            return Response(
                content=f"# Error generating metrics: {str(e)}\n",
                media_type="text/plain; charset=utf-8"
            )

    return router
