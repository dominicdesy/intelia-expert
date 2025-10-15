# -*- coding: utf-8 -*-
"""
api/endpoints_chat/__init__.py - Main entry point for chat endpoints
Version 5.0.3 - Modular chat endpoints with factory pattern + Vision support + Temp image upload
"""

from utils.types import Dict, Any
from fastapi import APIRouter

from .json_routes import create_json_routes
from .chat_routes import create_chat_routes
from .misc_routes import create_misc_routes
from .vision_routes import create_vision_routes
from .temp_image_routes import create_temp_image_routes


def create_chat_endpoints(services: Dict[str, Any]) -> APIRouter:
    """
    Crée tous les endpoints de chat et streaming avec système JSON

    Cette fonction factory crée un router combiné avec tous les sous-modules:
    - JSON routes: validation, ingestion, search, upload
    - Chat routes: chat principal et expert
    - Misc routes: OOD, tests, stats
    - Vision routes: analyse d'images médicales avec Claude Vision
    - Temp image routes: upload temporaire d'images pour accumulation

    Args:
        services: Dictionnaire des services disponibles

    Returns:
        APIRouter configuré avec tous les endpoints de chat
    """
    # Router principal
    router = APIRouter()

    # Helper pour récupérer un service
    def get_service(name: str) -> Any:
        """Helper pour récupérer un service depuis le dictionnaire"""
        return services.get(name)

    # Créer les sous-routers
    json_router = create_json_routes(get_service)
    chat_router = create_chat_routes(get_service)
    misc_router = create_misc_routes(get_service)
    vision_router = create_vision_routes(get_service)
    temp_image_router = create_temp_image_routes(get_service)

    # Inclure tous les sous-routers dans le router principal
    router.include_router(json_router, tags=["JSON System"])
    router.include_router(chat_router, tags=["Chat"])
    router.include_router(misc_router, tags=["Miscellaneous"])
    router.include_router(vision_router, tags=["Vision"])
    router.include_router(temp_image_router, tags=["Temp Images"])

    return router


# Exporter la fonction principale
__all__ = ["create_chat_endpoints"]
