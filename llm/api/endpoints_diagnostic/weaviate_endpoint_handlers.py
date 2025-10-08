# -*- coding: utf-8 -*-
"""
Weaviate endpoint handlers - Extracted from weaviate_routes.py for better modularity
Handles Weaviate status and Digital Ocean diagnostic functionality
"""

import os
import time
import asyncio
import socket
import logging
from utils.types import Dict, Any, Optional, Callable
from urllib.parse import urlparse

from utils.utilities import safe_get_attribute
from api.endpoints import safe_serialize_for_json
from .helpers import get_collections_info, get_rag_engine_from_health_monitor

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS FOR WEAVIATE STATUS
# ============================================================================


def get_weaviate_client_from_service(get_service: Callable) -> Optional[Any]:
    """
    Get Weaviate client from health monitor service

    Args:
        get_service: Function to get service by name

    Returns:
        Weaviate client instance or None
    """
    health_monitor = get_service("health_monitor")
    if not health_monitor:
        return None

    rag_engine = get_rag_engine_from_health_monitor(health_monitor)
    if not rag_engine:
        return None

    return safe_get_attribute(rag_engine, "weaviate_client")


async def check_weaviate_ready(weaviate_client: Any) -> bool:
    """
    Check if Weaviate client is ready

    Args:
        weaviate_client: Weaviate client instance

    Returns:
        True if ready, False otherwise
    """
    try:
        is_ready = await asyncio.get_event_loop().run_in_executor(
            None, weaviate_client.is_ready
        )
        return is_ready
    except Exception as e:
        logger.error(f"Error checking Weaviate ready: {e}")
        return False


async def get_weaviate_collections_info(weaviate_client: Any) -> Dict[str, Any]:
    """
    Get collections info from Weaviate client

    Args:
        weaviate_client: Weaviate client instance

    Returns:
        Dict with collections info or error
    """
    try:
        collections_info = await get_collections_info(weaviate_client)
        return collections_info
    except Exception as e:
        logger.error(f"Error getting collections info: {e}")
        return {"error": str(e)}


def analyze_weaviate_health(total_documents: int) -> tuple:
    """
    Analyze Weaviate health based on document count

    Args:
        total_documents: Total number of documents

    Returns:
        Tuple of (issues_list, status_string)
    """
    issues = []

    if total_documents == 0:
        issues.append("CRITIQUE: Aucun document trouvé dans Weaviate")
    elif total_documents < 100:
        issues.append(f"ATTENTION: Peu de documents ({total_documents})")

    status = "healthy" if len(issues) == 0 else "issues_detected"
    return issues, status


# ============================================================================
# HELPER FUNCTIONS FOR DIGITAL OCEAN DIAGNOSTIC
# ============================================================================


def get_environment_vars_info() -> Dict[str, Any]:
    """
    Get environment variables info for Weaviate

    Returns:
        Dict with environment variables info
    """
    return {
        "weaviate_url": os.getenv("WEAVIATE_URL", "NON DÉFINIE"),
        "weaviate_api_key_present": bool(os.getenv("WEAVIATE_API_KEY")),
        "weaviate_api_key_length": len(os.getenv("WEAVIATE_API_KEY", "")),
        "openai_api_key_present": bool(os.getenv("OPENAI_API_KEY")),
        "openai_api_key_length": len(os.getenv("OPENAI_API_KEY", "")),
    }


def parse_weaviate_url(weaviate_url: str) -> Dict[str, Any]:
    """
    Parse Weaviate URL and extract components

    Args:
        weaviate_url: Weaviate URL string

    Returns:
        Dict with parsed URL components or error
    """
    try:
        parsed_url = urlparse(weaviate_url)
        return {
            "scheme": parsed_url.scheme,
            "hostname": parsed_url.hostname,
            "port": parsed_url.port or (443 if parsed_url.scheme == "https" else 80),
            "path": parsed_url.path,
            "is_cloud": "weaviate.network" in weaviate_url
            or "weaviate.cloud" in weaviate_url,
        }
    except Exception as e:
        return {"error": str(e)}


def test_dns_resolution(hostname: str) -> Dict[str, Any]:
    """
    Test DNS resolution for hostname

    Args:
        hostname: Hostname to resolve

    Returns:
        Dict with DNS resolution results
    """
    try:
        start_time = time.time()
        ip_address = socket.gethostbyname(hostname)
        dns_time = time.time() - start_time

        return {
            "status": "success",
            "hostname": hostname,
            "ip_address": ip_address,
            "resolution_time_ms": round(dns_time * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def test_tcp_connectivity(hostname: str, port: int) -> Dict[str, Any]:
    """
    Test TCP connectivity to hostname:port

    Args:
        hostname: Target hostname
        port: Target port

    Returns:
        Dict with TCP connectivity results
    """
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((hostname, port))
        sock.close()
        tcp_time = time.time() - start_time

        return {
            "status": "success" if result == 0 else "failed",
            "hostname": hostname,
            "port": port,
            "connection_time_ms": round(tcp_time * 1000, 2),
            "error_code": result if result != 0 else None,
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


async def test_python_weaviate_connection(weaviate_client: Any) -> Dict[str, Any]:
    """
    Test Python Weaviate client connection

    Args:
        weaviate_client: Weaviate client instance

    Returns:
        Dict with connection test results
    """
    try:
        is_ready = await asyncio.wait_for(
            asyncio.to_thread(lambda: weaviate_client.is_ready()),
            timeout=15.0,
        )

        result = {
            "status": "success" if is_ready else "failed",
            "client_type": "existing_service_client",
            "is_ready": is_ready,
            "test_method": "service_client",
        }

        # Test collections capability if ready
        if is_ready:
            try:
                if hasattr(weaviate_client, "collections"):
                    collections = await asyncio.to_thread(
                        lambda: list(weaviate_client.collections.list_all())
                    )
                    result["collections_count"] = len(collections)
                    result["collections_accessible"] = True
                else:
                    result["weaviate_version"] = "v3_or_older"
            except Exception as collections_error:
                result["collections_error"] = str(collections_error)

        return result

    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "error": "Timeout de 15 secondes dépassé",
            "test_method": "service_client",
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "test_method": "service_client",
        }


def analyze_do_diagnostic_results(steps: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse les résultats du diagnostic Digital Ocean

    Args:
        steps: Dict with diagnostic steps results

    Returns:
        Dict with analysis summary
    """
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


def generate_do_recommendations(steps: Dict[str, Any], summary: Dict[str, Any]) -> list:
    """
    Génère des recommandations basées sur les résultats

    Args:
        steps: Dict with diagnostic steps results
        summary: Dict with analysis summary

    Returns:
        List of recommendations
    """
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


# ============================================================================
# ENDPOINT HANDLERS
# ============================================================================


async def handle_weaviate_status(get_service: Callable) -> Dict[str, Any]:
    """
    Handle Weaviate status diagnostic endpoint

    Args:
        get_service: Function to get services

    Returns:
        Dict with Weaviate status and diagnostics
    """
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
            # Test connection readiness
            is_ready = await check_weaviate_ready(weaviate_client)
            result["is_ready"] = is_ready

            if not is_ready:
                result["issues"].append("Weaviate n'est pas ready")
                return safe_serialize_for_json(result)

            # Get collections info
            result["weaviate_version"] = "v4"
            collections_info = await get_weaviate_collections_info(weaviate_client)

            if "error" in collections_info:
                result["issues"].append(collections_info["error"])
                result["weaviate_version"] = "v4-error"
            else:
                result["collections"] = collections_info
                result["total_documents"] = sum(
                    info.get("document_count", 0) for info in collections_info.values()
                )

            # Analyze health
            issues, status = analyze_weaviate_health(result["total_documents"])
            result["issues"].extend(issues)
            result["status"] = status

        except Exception as e:
            result["error"] = str(e)
            result["issues"].append(f"Erreur diagnostic Weaviate: {e}")
            result["status"] = "error"

        return safe_serialize_for_json(result)

    except Exception as e:
        logger.error(f"Erreur weaviate_status: {e}")
        return {"error": str(e), "timestamp": time.time(), "status": "error"}


async def handle_weaviate_digitalocean_diagnostic(
    get_service: Callable,
) -> Dict[str, Any]:
    """
    Handle Weaviate Digital Ocean diagnostic endpoint

    Args:
        get_service: Function to get services

    Returns:
        Dict with comprehensive Digital Ocean diagnostic results
    """
    diagnostic_results = {
        "timestamp": time.time(),
        "platform": "Digital Ocean App Platform",
        "diagnostic_version": "1.0",
        "steps": {},
        "summary": {},
        "recommendations": [],
    }

    try:
        # 1. Environment variables
        diagnostic_results["steps"]["environment_vars"] = get_environment_vars_info()

        weaviate_url = os.getenv("WEAVIATE_URL")

        if not weaviate_url:
            diagnostic_results["summary"]["critical_error"] = "WEAVIATE_URL non définie"
            diagnostic_results["recommendations"].append(
                "Configurer WEAVIATE_URL dans les variables d'environnement Digital Ocean"
            )
            return safe_serialize_for_json(diagnostic_results)

        # 2. URL parsing
        parsed_url_info = parse_weaviate_url(weaviate_url)
        diagnostic_results["steps"]["url_parsing"] = parsed_url_info

        if "error" in parsed_url_info:
            return safe_serialize_for_json(diagnostic_results)

        parsed_url = urlparse(weaviate_url)

        # 3. DNS resolution test
        if parsed_url.hostname:
            diagnostic_results["steps"]["dns_resolution"] = test_dns_resolution(
                parsed_url.hostname
            )
        else:
            diagnostic_results["steps"]["dns_resolution"] = {
                "error": "Hostname non trouvé dans l'URL"
            }

        # 4. TCP connectivity test
        hostname = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
        diagnostic_results["steps"]["tcp_connectivity"] = test_tcp_connectivity(
            hostname, port
        )

        # 5. Python Weaviate connection test
        weaviate_client = get_weaviate_client_from_service(get_service)

        if weaviate_client:
            diagnostic_results["steps"]["python_weaviate_connection"] = (
                await test_python_weaviate_connection(weaviate_client)
            )
        else:
            diagnostic_results["steps"]["python_weaviate_connection"] = {
                "status": "skipped",
                "reason": "Aucun client Weaviate disponible dans les services",
            }

        # 6. Analysis and recommendations
        diagnostic_results["summary"] = analyze_do_diagnostic_results(
            diagnostic_results["steps"]
        )
        diagnostic_results["recommendations"] = generate_do_recommendations(
            diagnostic_results["steps"], diagnostic_results["summary"]
        )

    except Exception as e:
        diagnostic_results["critical_error"] = {
            "error": str(e),
            "error_type": type(e).__name__,
        }

    return safe_serialize_for_json(diagnostic_results)
