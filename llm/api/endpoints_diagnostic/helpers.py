# -*- coding: utf-8 -*-
"""
Helper functions for diagnostic endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Helper functions for diagnostic endpoints

Extracted from endpoints_diagnostic.py to eliminate duplication
"""

import asyncio
import logging
from utils.types import Dict, Any

logger = logging.getLogger(__name__)


def get_service_from_dict(services: Dict[str, Any], name: str) -> Any:
    """
    Get service from services dictionary

    Args:
        services: Services dictionary
        name: Service name

    Returns:
        Service instance or None
    """
    return services.get(name)


def get_collection_safely(weaviate_client, collection_name: str):
    """
    Récupère une collection de manière sécurisée

    Args:
        weaviate_client: Weaviate client instance
        collection_name: Name of collection to retrieve

    Returns:
        Collection object or None
    """
    try:
        if hasattr(weaviate_client, "collections"):
            return weaviate_client.collections.get(collection_name)
        return None
    except Exception as e:
        logger.warning(f"Erreur récupération collection {collection_name}: {e}")
        return None


async def get_collections_info(weaviate_client) -> Dict[str, Any]:
    """
    Récupère les informations des collections de manière robuste

    Args:
        weaviate_client: Weaviate client instance

    Returns:
        Dictionary with collection information
    """
    collections_info = {}
    collection_names = []

    try:
        if not hasattr(weaviate_client, "collections"):
            return {"error": "Weaviate v3 non supporté"}

        # Récupérer la liste des collections
        collections_data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: weaviate_client.collections.list_all()
        )

        # Traiter selon le type de retour
        if isinstance(collections_data, dict):
            collection_names = list(collections_data.keys())
        else:
            collection_names = list(collections_data)

        # Récupérer les infos de chaque collection
        for collection_name in collection_names:
            try:
                collection = weaviate_client.collections.get(collection_name)
                count_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda c=collection: c.aggregate.over_all(total_count=True),
                )
                doc_count = getattr(count_result, "total_count", 0)

                collections_info[collection_name] = {
                    "document_count": doc_count,
                    "name": collection_name,
                    "accessible": True,
                }

            except Exception as e:
                collections_info[collection_name] = {
                    "error": str(e),
                    "document_count": 0,
                    "accessible": False,
                }

    except Exception as e:
        return {"error": f"Erreur récupération collections: {e}"}

    return collections_info


def get_rag_engine_from_health_monitor(health_monitor):
    """
    Get RAG engine from health monitor

    Args:
        health_monitor: Health monitor service

    Returns:
        RAG engine instance or None
    """
    if not health_monitor:
        return None

    try:
        return health_monitor.get_service("rag_engine_enhanced")
    except Exception as e:
        logger.error(f"Error getting RAG engine: {e}")
        return None


__all__ = [
    "get_service_from_dict",
    "get_collection_safely",
    "get_collections_info",
    "get_rag_engine_from_health_monitor",
]
