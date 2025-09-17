# -*- coding: utf-8 -*-
"""
monitoring.py - Module de surveillance et monitoring du système
SystemHealthMonitor déplacé depuis main.py pour architecture modulaire
"""

import time
import asyncio
import logging
from typing import Dict, Any

# CORRECTION: Imports modulaires absolus au lieu d'imports relatifs
from config.config import (
    OPENAI_API_KEY,
    LANGSMITH_ENABLED,
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT,
    ENABLE_INTELLIGENT_RRF,
    RRF_LEARNING_MODE,
    RRF_GENETIC_BOOST,
    get_config_status,
)
from utils.imports_and_dependencies import (
    require_critical_dependencies,
    get_full_status_report,
    quick_connectivity_check,
)
from utils.utilities import safe_serialize_for_json, safe_get_attribute, safe_dict_get

logger = logging.getLogger(__name__)

# ============================================================================
# EXCEPTIONS DE MONITORING
# ============================================================================


class StartupValidationError(Exception):
    """Exception pour les erreurs de validation au démarrage"""
    pass


class MonitoringError(Exception):
    """Exception générale pour les erreurs de monitoring"""
    pass


# ============================================================================
# SYSTEM HEALTH MONITOR
# ============================================================================


class SystemHealthMonitor:
    """Moniteur de santé système robuste avec LangSmith et RRF"""

    def __init__(self):
        self.startup_time = time.time()
        self.last_health_check = 0.0
        self.health_status = "initializing"
        self.component_status = {}
        self.validation_report = {}
        self._critical_services = {}

    async def validate_startup_requirements(self, timeout: int = 30) -> Dict[str, Any]:
        """Valide tous les prérequis au démarrage avec gestion d'erreurs stricte"""
        validation_report = {
            "timestamp": time.time(),
            "startup_duration": 0.0,
            "critical_dependencies": {},
            "service_connectivity": {},
            "configuration_validation": {},
            "langsmith_validation": {},
            "rrf_validation": {},
            "overall_status": "unknown",
            "errors": [],
            "warnings": [],
        }

        start_time = time.time()

        try:
            # 1. Validation des dépendances critiques
            logger.info("Validation des dépendances critiques...")

            try:
                require_critical_dependencies()
                dependency_status = get_full_status_report()
                validation_report["critical_dependencies"] = dependency_status

                if not dependency_status["critical_dependencies_ok"]:
                    raise StartupValidationError(
                        f"Dépendances critiques manquantes: {dependency_status['critical_missing']}"
                    )

                logger.info("✅ Dépendances critiques validées")

            except Exception as e:
                validation_report["errors"].append(f"Dépendances critiques: {e}")
                raise StartupValidationError(f"Validation dépendances échouée: {e}")

            # 2. Validation de la configuration OpenAI
            logger.info("Validation configuration OpenAI...")

            if not OPENAI_API_KEY:
                raise StartupValidationError("OPENAI_API_KEY non configurée")

            try:
                from openai import AsyncOpenAI

                test_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

                # Test simple avec timeout
                await asyncio.wait_for(test_client.models.list(), timeout=10.0)
                validation_report["configuration_validation"]["openai"] = "ok"
                logger.info("✅ Configuration OpenAI validée")

            except Exception as e:
                validation_report["errors"].append(f"OpenAI: {e}")
                raise StartupValidationError(f"Configuration OpenAI invalide: {e}")

            # 3. Validation LangSmith
            logger.info("Validation configuration LangSmith...")

            if LANGSMITH_ENABLED:
                if not LANGSMITH_API_KEY:
                    validation_report["warnings"].append(
                        "LangSmith activé mais API key manquante"
                    )
                    validation_report["langsmith_validation"]["status"] = "disabled"
                else:
                    try:
                        validation_report["langsmith_validation"] = {
                            "enabled": True,
                            "api_key_present": bool(LANGSMITH_API_KEY),
                            "project": LANGSMITH_PROJECT,
                            "status": "configured",
                        }
                        logger.info("✅ LangSmith configuré")
                    except Exception as e:
                        validation_report["warnings"].append(f"LangSmith: {e}")
                        validation_report["langsmith_validation"]["status"] = "error"
            else:
                validation_report["langsmith_validation"]["status"] = "disabled"

            # 4. Validation RRF Intelligent
            logger.info("Validation RRF Intelligent...")

            if ENABLE_INTELLIGENT_RRF:
                validation_report["rrf_validation"] = {
                    "enabled": True,
                    "learning_mode": RRF_LEARNING_MODE,
                    "genetic_boost": RRF_GENETIC_BOOST,
                    "redis_required": True,
                    "status": "configured",
                }
                logger.info("✅ RRF Intelligent configuré")
            else:
                validation_report["rrf_validation"]["status"] = "disabled"

            # 5. Initialisation des services principaux
            logger.info("Initialisation des services...")

            service_errors = await self._initialize_core_services()
            if service_errors:
                validation_report["errors"].extend(service_errors)
                raise StartupValidationError(
                    f"Échec initialisation services: {service_errors}"
                )

            # 6. Tests de connectivité
            logger.info("Tests de connectivité...")

            connectivity_status = await self._test_service_connectivity()
            validation_report["service_connectivity"] = connectivity_status

            # Vérification connectivité critique
            if not connectivity_status.get("weaviate", False):
                validation_report["warnings"].append(
                    "Weaviate non accessible - mode dégradé"
                )

            if not connectivity_status.get("redis", False):
                validation_report["warnings"].append(
                    "Redis non accessible - cache désactivé"
                )
                if ENABLE_INTELLIGENT_RRF:
                    validation_report["warnings"].append(
                        "RRF Intelligent désactivé (Redis requis)"
                    )

            # 7. Validation finale
            validation_report["startup_duration"] = time.time() - start_time

            if validation_report["errors"]:
                validation_report["overall_status"] = "failed"
            elif validation_report["warnings"]:
                validation_report["overall_status"] = "degraded"
            else:
                validation_report["overall_status"] = "healthy"

            self.validation_report = validation_report
            return validation_report

        except StartupValidationError:
            validation_report["startup_duration"] = time.time() - start_time
            validation_report["overall_status"] = "failed"
            self.validation_report = validation_report
            raise
        except Exception as e:
            validation_report["errors"].append(f"Erreur validation inattendue: {e}")
            validation_report["startup_duration"] = time.time() - start_time
            validation_report["overall_status"] = "failed"
            self.validation_report = validation_report
            raise StartupValidationError(f"Validation échouée: {e}")

    async def _initialize_core_services(self) -> list:
        """Initialise les services principaux avec support LangSmith + RRF"""
        errors = []

        try:
            # Cache Core
            logger.info("  Initialisation Cache Core...")
            try:
                from cache.cache_core import create_cache_core

                cache_core = create_cache_core()
                await cache_core.initialize()

                self._critical_services["cache_core"] = cache_core

                if cache_core.initialized:
                    logger.info("✅ Cache Core initialisé")
                else:
                    logger.warning("⚠️ Cache Core en mode dégradé")

            except Exception as e:
                errors.append(f"Cache Core: {e}")
                logger.warning(f"Cache Core erreur: {e}")

            # RAG Engine Enhanced
            logger.info("  Initialisation RAG Engine Enhanced...")
            try:
                from core.rag_engine import InteliaRAGEngine

                rag_engine_enhanced = InteliaRAGEngine()
                await rag_engine_enhanced.initialize()

                self._critical_services["rag_engine_enhanced"] = rag_engine_enhanced

                if rag_engine_enhanced.is_initialized:
                    logger.info("✅ RAG Engine Enhanced initialisé")

                    # Vérifier intégrations
                    status = rag_engine_enhanced.get_status()

                    # Log statut LangSmith
                    langsmith_status = safe_dict_get(status, "langsmith", {})
                    if safe_dict_get(langsmith_status, "enabled", False):
                        project = safe_dict_get(langsmith_status, "project", "")
                        logger.info(f"✅ LangSmith actif - Projet: {project}")

                    # Log statut RRF Intelligent
                    rrf_status = safe_dict_get(status, "intelligent_rrf", {})
                    if safe_dict_get(rrf_status, "enabled", False):
                        learning_mode = safe_dict_get(
                            rrf_status, "learning_mode", False
                        )
                        logger.info(
                            f"✅ RRF Intelligent actif - Learning: {learning_mode}"
                        )

                else:
                    logger.warning("⚠️ RAG Engine en mode dégradé")

            except Exception as e:
                errors.append(f"RAG Engine: {e}")
                logger.error(f"RAG Engine erreur: {e}")

            # Agent RAG (optionnel)
            try:
                from extensions.agent_rag_extension import create_agent_rag_engine

                agent_rag_engine = create_agent_rag_engine()
                self._critical_services["agent_rag_engine"] = agent_rag_engine
                logger.info("✅ Agent RAG disponible")
            except ImportError:
                logger.info("Agent RAG non disponible (optionnel)")
            except Exception as e:
                logger.warning(f"Agent RAG erreur: {e}")

        except Exception as e:
            errors.append(f"Erreur initialisation services: {e}")

        return errors

    async def _test_service_connectivity(self) -> Dict[str, bool]:
        """Teste la connectivité aux services externes avec timeout"""

        # Récupérer les clients depuis les services initialisés
        redis_client = None
        weaviate_client = None

        cache_core = self._critical_services.get("cache_core")
        if cache_core and getattr(cache_core, "initialized", False):
            redis_client = getattr(cache_core, "client", None)

        rag_engine = self._critical_services.get("rag_engine_enhanced")
        if rag_engine:
            weaviate_client = getattr(rag_engine, "weaviate_client", None)

        try:
            connectivity = await asyncio.wait_for(
                quick_connectivity_check(redis_client, weaviate_client), timeout=10.0
            )
            return connectivity

        except asyncio.TimeoutError:
            logger.warning("Timeout test connectivité")
            return {"redis": False, "weaviate": False, "timeout": True}
        except Exception as e:
            logger.error(f"Erreur test connectivité: {e}")
            return {"redis": False, "weaviate": False, "error": str(e)}

    async def get_health_status(self) -> Dict[str, Any]:
        """Health check enrichi avec sérialisation JSON sécurisée"""
        current_time = time.time()

        # Statut global - SÉRIALISABLE
        global_status = {
            "overall_status": "healthy",
            "timestamp": current_time,
            "uptime_seconds": current_time - self.startup_time,
            "startup_validation": safe_serialize_for_json(self.validation_report),
            "services": {},
            "integrations": {},
            "warnings": [],
        }

        try:
            # Statut services avec sérialisation sécurisée

            # RAG Engine
            rag_engine = self._critical_services.get("rag_engine_enhanced")
            if rag_engine and safe_get_attribute(rag_engine, "is_initialized", False):
                try:
                    rag_status = rag_engine.get_status()

                    # Sérialisation sécurisée du statut RAG
                    safe_rag_status = safe_serialize_for_json(rag_status)

                    global_status["services"]["rag_engine"] = {
                        "status": (
                            "healthy"
                            if not getattr(rag_engine, "degraded_mode", False)
                            else "degraded"
                        ),
                        "approach": safe_dict_get(
                            safe_rag_status, "approach", "unknown"
                        ),
                        "optimizations": safe_dict_get(
                            safe_rag_status, "optimizations", {}
                        ),
                        "metrics": safe_dict_get(
                            safe_rag_status, "optimization_stats", {}
                        ),
                    }

                    # Intégrations spécialisées avec validation

                    # LangSmith - Sérialisation sécurisée
                    langsmith_info = safe_dict_get(safe_rag_status, "langsmith", {})
                    if isinstance(langsmith_info, dict):
                        global_status["integrations"]["langsmith"] = {
                            "available": safe_dict_get(
                                langsmith_info, "available", False
                            ),
                            "enabled": safe_dict_get(langsmith_info, "enabled", False),
                            "configured": safe_dict_get(
                                langsmith_info, "configured", False
                            ),
                            "project": str(
                                safe_dict_get(langsmith_info, "project", "")
                            ),
                            "traces_count": int(
                                safe_dict_get(langsmith_info, "traces_count", 0)
                            ),
                            "errors_count": int(
                                safe_dict_get(langsmith_info, "errors_count", 0)
                            ),
                        }

                        if langsmith_info.get("enabled") and not langsmith_info.get(
                            "configured"
                        ):
                            global_status["warnings"].append(
                                "LangSmith activé mais non configuré"
                            )

                    # RRF Intelligent - Sérialisation sécurisée
                    rrf_info = safe_dict_get(safe_rag_status, "intelligent_rrf", {})
                    if isinstance(rrf_info, dict):
                        global_status["integrations"]["intelligent_rrf"] = {
                            "available": safe_dict_get(rrf_info, "available", False),
                            "enabled": safe_dict_get(rrf_info, "enabled", False),
                            "configured": safe_dict_get(rrf_info, "configured", False),
                            "learning_mode": safe_dict_get(
                                rrf_info, "learning_mode", False
                            ),
                            "usage_count": int(
                                safe_dict_get(rrf_info, "usage_count", 0)
                            ),
                            "performance_stats": safe_dict_get(
                                rrf_info, "performance_stats", {}
                            ),
                        }

                        if rrf_info.get("enabled") and not rrf_info.get("configured"):
                            global_status["warnings"].append(
                                "RRF Intelligent activé mais non configuré"
                            )

                except Exception as e:
                    logger.error(f"Erreur récupération statut RAG: {e}")
                    global_status["services"]["rag_engine"] = {
                        "status": "error",
                        "reason": f"status_error: {str(e)}",
                    }
                    global_status["overall_status"] = "degraded"

            else:
                global_status["services"]["rag_engine"] = {
                    "status": "error",
                    "reason": "not_initialized",
                }
                global_status["overall_status"] = "degraded"

            # Cache - Sérialisation sécurisée
            cache_core = self._critical_services.get("cache_core")
            if cache_core and getattr(cache_core, "initialized", False):
                try:
                    if hasattr(cache_core, "get_health_status"):
                        cache_status = cache_core.get_health_status()
                        global_status["services"]["cache"] = safe_serialize_for_json(
                            cache_status
                        )
                    else:
                        global_status["services"]["cache"] = {"status": "unknown"}
                except Exception as e:
                    logger.error(f"Erreur statut cache: {e}")
                    global_status["services"]["cache"] = {
                        "status": "error",
                        "error": str(e),
                    }
            else:
                global_status["services"]["cache"] = {"status": "disabled"}

            # Agent RAG
            agent_rag = self._critical_services.get("agent_rag_engine")
            if agent_rag:
                global_status["services"]["agent_rag"] = {"status": "available"}
            else:
                global_status["services"]["agent_rag"] = {"status": "disabled"}

            # Configuration et environnement avec sérialisation
            try:
                config_status = get_config_status()
                global_status["configuration"] = safe_serialize_for_json(config_status)
            except Exception as e:
                logger.error(f"Erreur statut configuration: {e}")
                global_status["configuration"] = {"error": str(e)}

            # Environnement
            global_status["environment"] = {
                "platform": "digital_ocean",
                "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                "monitoring_version": "1.0.0",
            }

            # Déterminer statut global final
            if global_status["warnings"]:
                if global_status["overall_status"] == "healthy":
                    global_status["overall_status"] = "healthy_with_warnings"

            return global_status

        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": current_time,
                "safe_mode": True,
            }

    def get_service(self, service_name: str) -> Any:
        """Récupère un service initialisé"""
        return self._critical_services.get(service_name)

    def get_all_services(self) -> Dict[str, Any]:
        """Récupère tous les services initialisés"""
        return self._critical_services.copy()

    def is_service_healthy(self, service_name: str) -> bool:
        """Vérifie si un service est en bonne santé"""
        service = self._critical_services.get(service_name)
        if not service:
            return False

        # Vérifications spécifiques par service
        if service_name == "cache_core":
            return getattr(service, "initialized", False)
        elif service_name == "rag_engine_enhanced":
            return getattr(service, "is_initialized", False)
        else:
            return service is not None


# ============================================================================
# FONCTIONS UTILITAIRES DE MONITORING
# ============================================================================


async def create_health_monitor() -> SystemHealthMonitor:
    """Factory pour créer et initialiser un SystemHealthMonitor"""
    monitor = SystemHealthMonitor()
    return monitor


def get_system_info() -> Dict[str, Any]:
    """Récupère les informations système de base"""
    import sys
    import platform
    import os

    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "cpu_count": os.cpu_count(),
        "memory_available": "unknown",  # Peut être enrichi avec psutil si disponible
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "SystemHealthMonitor",
    "StartupValidationError",
    "MonitoringError",
    "create_health_monitor",
    "get_system_info",
]