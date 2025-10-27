# -*- coding: utf-8 -*-
"""
api/endpoints_chat/helpers.py - Helper functions for chat endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_chat/helpers.py - Helper functions for chat endpoints
Version 5.0.1
"""

import logging
from utils.types import Any, Dict

logger = logging.getLogger(__name__)


def get_rag_engine_from_services(services: Dict[str, Any]) -> Any:
    """
    Helper pour récupérer le RAG Engine depuis les services

    Args:
        services: Dictionnaire des services

    Returns:
        Instance du RAG Engine ou None si non disponible
    """
    health_monitor = services.get("health_monitor")
    if health_monitor:
        return health_monitor.get_service("rag_engine_enhanced")
    return None


def get_service_from_dict(services: Dict[str, Any], name: str) -> Any:
    """
    Helper pour récupérer un service depuis le dictionnaire

    Args:
        services: Dictionnaire des services
        name: Nom du service

    Returns:
        Instance du service ou None
    """
    return services.get(name)
