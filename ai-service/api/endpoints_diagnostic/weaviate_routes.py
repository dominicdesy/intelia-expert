# -*- coding: utf-8 -*-
"""
Weaviate diagnostic routes
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Weaviate diagnostic routes
Contains endpoints for Weaviate status and connectivity diagnostics
"""

import os
import time
import asyncio
import socket
import logging
from utils.types import Callable
from urllib.parse import urlparse
from fastapi import APIRouter

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute
from api.endpoints import safe_serialize_for_json

from .helpers import (
    get_collections_info,
    get_rag_engine_from_health_monitor,
)

logger = logging.getLogger(__name__)


def create_weaviate_routes(get_service: Callable) -> APIRouter:
    """
    Create weaviate diagnostic routes

    Args:
        get_service: Function to retrieve services

    Returns:
        APIRouter instance with weaviate endpoints
    """
    router = APIRouter()

    @router.get(f"{BASE_PATH}/diagnostic/weaviate-status")
    async def weaviate_status():
        """Statut détaillé de Weaviate avec comptage documents et collections"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {
                    "error": "Health monitor non disponible",
                    "timestamp": time.time(),
                }

            rag_engine = get_rag_engine_from_health_monitor(health_monitor)
            if not rag_engine:
                return {"error": "RAG Engine non disponible", "timestamp": time.time()}

            weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
            if not weaviate_client:
                return {
                    "error": "Client Weaviate non disponible",
                    "timestamp": time.time(),
                }

            result = {
                "timestamp": time.time(),
                "client_available": True,
                "collections": {},
                "total_documents": 0,
                "weaviate_version": "unknown",
                "issues": [],
            }

            try:
                # Tester la connexion
                is_ready = await asyncio.get_event_loop().run_in_executor(
                    None, weaviate_client.is_ready
                )
                result["is_ready"] = is_ready

                if not is_ready:
                    result["issues"].append("Weaviate n'est pas ready")
                    return safe_serialize_for_json(result)

                # Récupérer les collections avec la fonction corrigée
                result["weaviate_version"] = "v4"
                collections_info = await get_collections_info(weaviate_client)

                if "error" in collections_info:
                    result["issues"].append(collections_info["error"])
                    result["weaviate_version"] = "v4-error"
                else:
                    result["collections"] = collections_info
                    result["total_documents"] = sum(
                        info.get("document_count", 0)
                        for info in collections_info.values()
                    )

                # Vérifications de santé
                if result["total_documents"] == 0:
                    result["issues"].append(
                        "CRITIQUE: Aucun document trouvé dans Weaviate"
                    )
                elif result["total_documents"] < 100:
                    result["issues"].append(
                        f"ATTENTION: Peu de documents ({result['total_documents']})"
                    )

                result["status"] = (
                    "healthy" if len(result["issues"]) == 0 else "issues_detected"
                )

            except Exception as e:
                result["error"] = str(e)
                result["issues"].append(f"Erreur diagnostic Weaviate: {e}")
                result["status"] = "error"

            return safe_serialize_for_json(result)

        except Exception as e:
            logger.error(f"Erreur weaviate_status: {e}")
            return {"error": str(e), "timestamp": time.time(), "status": "error"}

    @router.get(f"{BASE_PATH}/diagnostic/weaviate-digitalocean")
    async def weaviate_digitalocean_diagnostic():
        """Diagnostic complet Weaviate pour Digital Ocean App Platform"""

        diagnostic_results = {
            "timestamp": time.time(),
            "platform": "Digital Ocean App Platform",
            "diagnostic_version": "1.0",
            "steps": {},
            "summary": {},
            "recommendations": [],
        }

        try:
            # 1. Variables d'environnement
            diagnostic_results["steps"]["environment_vars"] = {
                "weaviate_url": os.getenv("WEAVIATE_URL", "NON DÉFINIE"),
                "weaviate_api_key_present": bool(os.getenv("WEAVIATE_API_KEY")),
                "weaviate_api_key_length": len(os.getenv("WEAVIATE_API_KEY", "")),
                "openai_api_key_present": bool(os.getenv("OPENAI_API_KEY")),
                "openai_api_key_length": len(os.getenv("OPENAI_API_KEY", "")),
            }

            weaviate_url = os.getenv("WEAVIATE_URL")

            if not weaviate_url:
                diagnostic_results["summary"][
                    "critical_error"
                ] = "WEAVIATE_URL non définie"
                diagnostic_results["recommendations"].append(
                    "Configurer WEAVIATE_URL dans les variables d'environnement Digital Ocean"
                )
                return safe_serialize_for_json(diagnostic_results)

            # 2. Parse de l'URL
            try:
                parsed_url = urlparse(weaviate_url)
                diagnostic_results["steps"]["url_parsing"] = {
                    "scheme": parsed_url.scheme,
                    "hostname": parsed_url.hostname,
                    "port": parsed_url.port
                    or (443 if parsed_url.scheme == "https" else 80),
                    "path": parsed_url.path,
                    "is_cloud": "weaviate.network" in weaviate_url
                    or "weaviate.cloud" in weaviate_url,
                }
            except Exception as e:
                diagnostic_results["steps"]["url_parsing"] = {"error": str(e)}

            # 3. Test de résolution DNS
            try:
                hostname = parsed_url.hostname
                if hostname:
                    start_time = time.time()
                    ip_address = socket.gethostbyname(hostname)
                    dns_time = time.time() - start_time
                    diagnostic_results["steps"]["dns_resolution"] = {
                        "status": "success",
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "resolution_time_ms": round(dns_time * 1000, 2),
                    }
                else:
                    diagnostic_results["steps"]["dns_resolution"] = {
                        "error": "Hostname non trouvé dans l'URL"
                    }
            except Exception as e:
                diagnostic_results["steps"]["dns_resolution"] = {
                    "status": "failed",
                    "error": str(e),
                }

            # 4. Test de connectivité TCP
            try:
                hostname = parsed_url.hostname
                port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)

                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                result = sock.connect_ex((hostname, port))
                sock.close()
                tcp_time = time.time() - start_time

                diagnostic_results["steps"]["tcp_connectivity"] = {
                    "status": "success" if result == 0 else "failed",
                    "hostname": hostname,
                    "port": port,
                    "connection_time_ms": round(tcp_time * 1000, 2),
                    "error_code": result if result != 0 else None,
                }
            except Exception as e:
                diagnostic_results["steps"]["tcp_connectivity"] = {
                    "status": "failed",
                    "error": str(e),
                }

            # 5. Test de connexion Python Weaviate
            try:
                # Utiliser le client existant du service si disponible
                health_monitor = get_service("health_monitor")
                existing_client = None

                if health_monitor:
                    rag_engine = get_rag_engine_from_health_monitor(health_monitor)
                    if rag_engine:
                        existing_client = safe_get_attribute(
                            rag_engine, "weaviate_client"
                        )

                if existing_client:
                    # Test avec le client existant
                    try:
                        is_ready = await asyncio.wait_for(
                            asyncio.to_thread(lambda: existing_client.is_ready()),
                            timeout=15.0,
                        )

                        diagnostic_results["steps"]["python_weaviate_connection"] = {
                            "status": "success" if is_ready else "failed",
                            "client_type": "existing_service_client",
                            "is_ready": is_ready,
                            "test_method": "service_client",
                        }

                        # Test des capacités si connecté
                        if is_ready:
                            try:
                                if hasattr(existing_client, "collections"):
                                    collections = await asyncio.to_thread(
                                        lambda: list(
                                            existing_client.collections.list_all()
                                        )
                                    )
                                    diagnostic_results["steps"][
                                        "python_weaviate_connection"
                                    ]["collections_count"] = len(collections)
                                    diagnostic_results["steps"][
                                        "python_weaviate_connection"
                                    ]["collections_accessible"] = True
                                else:
                                    diagnostic_results["steps"][
                                        "python_weaviate_connection"
                                    ]["weaviate_version"] = "v3_or_older"
                            except Exception as collections_error:
                                diagnostic_results["steps"][
                                    "python_weaviate_connection"
                                ]["collections_error"] = str(collections_error)

                    except asyncio.TimeoutError:
                        diagnostic_results["steps"]["python_weaviate_connection"] = {
                            "status": "timeout",
                            "error": "Timeout de 15 secondes dépassé",
                            "test_method": "service_client",
                        }
                    except Exception as e:
                        diagnostic_results["steps"]["python_weaviate_connection"] = {
                            "status": "failed",
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "test_method": "service_client",
                        }

                else:
                    diagnostic_results["steps"]["python_weaviate_connection"] = {
                        "status": "skipped",
                        "reason": "Aucun client Weaviate disponible dans les services",
                    }

            except Exception as e:
                diagnostic_results["steps"]["python_weaviate_connection"] = {
                    "status": "failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

            # 6. Analyse des résultats et recommandations
            diagnostic_results["summary"] = _analyze_do_diagnostic_results(
                diagnostic_results["steps"]
            )
            diagnostic_results["recommendations"] = _generate_do_recommendations(
                diagnostic_results["steps"], diagnostic_results["summary"]
            )

        except Exception as e:
            diagnostic_results["critical_error"] = {
                "error": str(e),
                "error_type": type(e).__name__,
            }

        return safe_serialize_for_json(diagnostic_results)

    return router


def _analyze_do_diagnostic_results(steps: dict) -> dict:
    """Analyse les résultats du diagnostic Digital Ocean"""
    summary = {
        "overall_status": "unknown",
        "critical_issues": [],
        "warnings": [],
        "working_components": [],
    }

    # Analyse des variables d'environnement
    env_vars = steps.get("environment_vars", {})
    if (
        not env_vars.get("weaviate_url")
        or env_vars.get("weaviate_url") == "NON DÉFINIE"
    ):
        summary["critical_issues"].append("WEAVIATE_URL non configurée")
    else:
        summary["working_components"].append("WEAVIATE_URL configurée")

    if not env_vars.get("weaviate_api_key_present"):
        summary["critical_issues"].append("WEAVIATE_API_KEY non configurée")
    else:
        summary["working_components"].append("WEAVIATE_API_KEY présente")

    # Analyse de la connectivité
    dns = steps.get("dns_resolution", {})
    if dns.get("status") == "success":
        summary["working_components"].append("Résolution DNS")
    elif dns.get("status") == "failed":
        summary["critical_issues"].append("Résolution DNS échouée")

    tcp = steps.get("tcp_connectivity", {})
    if tcp.get("status") == "success":
        summary["working_components"].append("Connectivité TCP")
    elif tcp.get("status") == "failed":
        summary["critical_issues"].append("Connectivité TCP échouée")

    python_conn = steps.get("python_weaviate_connection", {})
    if python_conn.get("status") == "success" and python_conn.get("is_ready"):
        summary["working_components"].append("Connexion Python Weaviate fonctionnelle")
    elif python_conn.get("status") == "failed":
        summary["critical_issues"].append("Connexion Python Weaviate échouée")
    elif python_conn.get("status") == "timeout":
        summary["critical_issues"].append("Timeout connexion Python Weaviate")

    # Détermination du statut global
    if summary["critical_issues"]:
        summary["overall_status"] = "critical"
    elif summary["warnings"]:
        summary["overall_status"] = "warning"
    elif summary["working_components"]:
        summary["overall_status"] = "healthy"
    else:
        summary["overall_status"] = "unknown"

    return summary


def _generate_do_recommendations(steps: dict, summary: dict) -> list:
    """Génère des recommandations basées sur les résultats"""
    recommendations = []

    env_vars = steps.get("environment_vars", {})

    if (
        not env_vars.get("weaviate_url")
        or env_vars.get("weaviate_url") == "NON DÉFINIE"
    ):
        recommendations.append(
            {
                "priority": "critical",
                "action": "Configurer WEAVIATE_URL",
                "details": "Ajouter WEAVIATE_URL dans les variables d'environnement Digital Ocean App Platform",
                "example": "https://votre-cluster.weaviate.network",
            }
        )

    if not env_vars.get("weaviate_api_key_present"):
        recommendations.append(
            {
                "priority": "critical",
                "action": "Configurer WEAVIATE_API_KEY",
                "details": "Ajouter WEAVIATE_API_KEY dans les variables d'environnement Digital Ocean",
                "note": "Clé API disponible dans votre console Weaviate Cloud",
            }
        )

    dns = steps.get("dns_resolution", {})
    if dns.get("status") == "failed":
        recommendations.append(
            {
                "priority": "high",
                "action": "Vérifier la connectivité réseau",
                "details": "Le serveur Digital Ocean ne peut pas résoudre le hostname Weaviate",
                "solutions": [
                    "Vérifier que l'URL Weaviate est correcte",
                    "Vérifier la configuration réseau Digital Ocean",
                    "Tester depuis un autre environnement",
                ],
            }
        )

    tcp = steps.get("tcp_connectivity", {})
    if tcp.get("status") == "failed":
        recommendations.append(
            {
                "priority": "high",
                "action": "Résoudre le problème de connectivité TCP",
                "details": f"Impossible de se connecter au port {tcp.get('port', 'inconnu')}",
                "solutions": [
                    "Vérifier que Weaviate est accessible depuis Internet",
                    "Vérifier les règles de firewall",
                    "Vérifier la configuration réseau Digital Ocean",
                ],
            }
        )

    python_conn = steps.get("python_weaviate_connection", {})
    if python_conn.get("status") == "timeout":
        recommendations.append(
            {
                "priority": "medium",
                "action": "Optimiser les timeouts",
                "details": "La connexion Python Weaviate dépasse le timeout de 15s",
                "solutions": [
                    "Vérifier la latence réseau",
                    "Augmenter les timeouts dans la configuration",
                    "Vérifier les performances de l'instance Weaviate",
                ],
            }
        )

    return recommendations
