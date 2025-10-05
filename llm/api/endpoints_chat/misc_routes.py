# -*- coding: utf-8 -*-
"""
api/endpoints_chat/misc_routes.py - Miscellaneous endpoints
Version 5.0.1 - OOD, test-json-system, and conversation-stats endpoints
"""

import time
import asyncio
import logging
from utils.types import Any, Callable
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

from config.config import BASE_PATH, STREAM_CHUNK_LEN
from utils.utilities import (
    sse_event,
    smart_chunk_text,
    get_out_of_domain_message,
)
from ..endpoints import safe_serialize_for_json
from ..chat_handlers import ChatHandlers

logger = logging.getLogger(__name__)


def create_misc_routes(get_service: Callable[[str], Any]) -> APIRouter:
    """
    Crée les endpoints divers (OOD, tests, stats)

    Args:
        get_service: Fonction pour récupérer un service par nom

    Returns:
        APIRouter configuré avec les endpoints divers
    """
    router = APIRouter()

    def get_rag_engine():
        """Helper pour récupérer le RAG Engine"""
        health_monitor = get_service("health_monitor")
        if health_monitor:
            return health_monitor.get_service("rag_engine_enhanced")
        return None

    @router.post(f"{BASE_PATH}/ood")
    async def ood_endpoint(request: Request):
        """Point de terminaison pour messages hors domaine"""
        try:
            body = await request.json()
            language = body.get("language", "fr")
            message = get_out_of_domain_message(language)

            async def ood_response():
                yield sse_event(
                    {
                        "type": "start",
                        "reason": "out_of_domain",
                        "architecture": "query-router-v5.0.1",
                    }
                )

                chunks = smart_chunk_text(message, STREAM_CHUNK_LEN)
                for chunk in chunks:
                    yield sse_event({"type": "chunk", "content": chunk})
                    await asyncio.sleep(0.05)

                yield sse_event(
                    {
                        "type": "end",
                        "confidence": 1.0,
                        "architecture": "query-router-v5.0.1",
                    }
                )

            return StreamingResponse(ood_response(), media_type="text/plain")

        except Exception as e:
            logger.error(f"Erreur OOD endpoint: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    @router.post(f"{BASE_PATH}/chat/test-json-system")
    async def test_json_system():
        """Test complet du système JSON intégré"""
        try:
            test_results = {}
            rag_engine = get_rag_engine()

            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            # Créer chat_handlers pour les tests
            health_monitor = get_service("health_monitor")
            services_dict = {
                "health_monitor": health_monitor,
            }
            chat_handlers = ChatHandlers(services_dict)

            # Test validation
            try:
                test_json = {
                    "title": "Test Ross 308 Performance",
                    "text": "Performance objectives for Ross 308 broilers at 35 days.",
                    "metadata": {"genetic_line": "ross308"},
                    "tables": [],
                }

                if hasattr(rag_engine, "validate_json_document"):
                    validation_result = await rag_engine.validate_json_document(
                        test_json
                    )
                    test_results["json_validation"] = {
                        "success": True,
                        "valid": validation_result.get("valid", False),
                        "errors": validation_result.get("errors", []),
                    }
                else:
                    test_results["json_validation"] = {
                        "success": False,
                        "reason": "Méthode non disponible",
                    }
            except Exception as e:
                test_results["json_validation"] = {"success": False, "error": str(e)}

            # Test search
            try:
                if hasattr(rag_engine, "search_json_enhanced"):
                    search_results = await rag_engine.search_json_enhanced(
                        query="Ross 308 poids 35 jours", genetic_line="ross308"
                    )
                    test_results["json_search"] = {
                        "success": True,
                        "results_count": len(search_results),
                        "has_results": len(search_results) > 0,
                    }
                else:
                    test_results["json_search"] = {
                        "success": False,
                        "reason": "Méthode non disponible",
                    }
            except Exception as e:
                test_results["json_search"] = {"success": False, "error": str(e)}

            # Test génération
            try:
                generation_result = await chat_handlers.generate_rag_response(
                    query="Quel est le poids cible Ross 308 à 35 jours ?",
                    tenant_id="test",
                    language="fr",
                    use_json_search=True,
                    genetic_line_filter="ross308",
                )

                metadata = getattr(generation_result, "metadata", {})
                json_system_info = metadata.get("json_system", {})

                test_results["json_generation"] = {
                    "success": True,
                    "json_system_used": json_system_info.get("used", False),
                    "json_results_count": json_system_info.get("results_count", 0),
                    "confidence": getattr(generation_result, "confidence", 0),
                    "has_answer": bool(getattr(generation_result, "answer", "")),
                    "preprocessing_enabled": True,
                }
            except Exception as e:
                test_results["json_generation"] = {"success": False, "error": str(e)}

            successful_tests = sum(
                1 for result in test_results.values() if result.get("success", False)
            )
            total_tests = len(test_results)

            analysis = {
                "timestamp": time.time(),
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": (
                    successful_tests / total_tests if total_tests > 0 else 0
                ),
                "test_results": test_results,
                "system_health": (
                    "OK"
                    if successful_tests == total_tests
                    else "DEGRADED" if successful_tests > 0 else "FAILED"
                ),
                "version": "5.0.1_metrics_fixed",
            }

            return safe_serialize_for_json(analysis)

        except Exception as e:
            logger.error(f"Erreur test_json_system: {e}")
            return {"error": str(e), "timestamp": time.time()}

    @router.get(f"{BASE_PATH}/chat/conversation-stats")
    async def conversation_stats():
        """Statistiques des conversations en mémoire"""
        try:
            from ..utils import conversation_memory

            stats = conversation_memory.get_stats()

            detailed_stats = {**stats, "recent_tenants": [], "memory_usage_bytes": 0}

            recent_count = 0
            for tenant_id, tenant_data in conversation_memory.items():
                if recent_count >= 5:
                    break

                if isinstance(tenant_data, dict):
                    detailed_stats["recent_tenants"].append(
                        {
                            "tenant_id": tenant_id[:8] + "...",
                            "conversation_count": len(tenant_data.get("data", [])),
                            "last_query_preview": tenant_data.get("last_query", "")[:50]
                            + "...",
                            "last_update": tenant_data.get("ts", 0),
                        }
                    )
                    recent_count += 1

            try:
                import sys

                detailed_stats["memory_usage_bytes"] = sys.getsizeof(
                    conversation_memory
                )
            except Exception:
                detailed_stats["memory_usage_bytes"] = "unknown"

            return safe_serialize_for_json(detailed_stats)

        except Exception as e:
            logger.error(f"Erreur conversation_stats: {e}")
            return {"error": str(e), "timestamp": time.time()}

    return router
