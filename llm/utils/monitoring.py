# -*- coding: utf-8 -*-
"""
monitoring.py - Module de surveillance et monitoring du système
SystemHealthMonitor déplacé depuis main.py pour architecture modulaire
VERSION CORRIGÉE: Gestion robuste du cache et des erreurs de connectivité Weaviate + Agent RAG
"""

import time
import asyncio
import logging
from utils.types import Dict, Any

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
# SYSTEM HEALTH MONITOR - VERSION CORRIGÉE
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
        self._openai_validation_mode = "strict"  # strict, permissive, skip

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

                logger.info("Dépendances critiques validées")

            except Exception as e:
                validation_report["errors"].append(f"Dépendances critiques: {e}")
                raise StartupValidationError(f"Validation dépendances échouée: {e}")

            # 2. Validation de la configuration OpenAI - VERSION CORRIGÉE
            logger.info("Validation configuration OpenAI...")

            if not OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY non configurée - Mode dégradé")
                validation_report["warnings"].append("OPENAI_API_KEY non configurée")
                validation_report["configuration_validation"]["openai"] = "missing"
            else:
                # Validation robuste de la clé OpenAI
                openai_status = await self._validate_openai_config(OPENAI_API_KEY)
                validation_report["configuration_validation"]["openai"] = openai_status

                if openai_status["status"] == "valid":
                    logger.info("Configuration OpenAI validée")
                elif openai_status["status"] == "invalid":
                    # CHANGEMENT PRINCIPAL: Ne pas arrêter l'app, juste avertir
                    logger.warning(
                        f"Configuration OpenAI invalide: {openai_status['error']}"
                    )
                    validation_report["warnings"].append(
                        f"OpenAI invalide: {openai_status['error']}"
                    )
                    # Permettre à l'application de continuer en mode dégradé
                elif openai_status["status"] == "timeout":
                    logger.warning("Timeout validation OpenAI - Mode dégradé")
                    validation_report["warnings"].append("Timeout validation OpenAI")

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
                        logger.info("LangSmith configuré")
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
                logger.info("RRF Intelligent configuré")
            else:
                validation_report["rrf_validation"]["status"] = "disabled"

            # 5. Initialisation des services principaux - CORRECTION CACHE
            logger.info("Initialisation des services...")

            service_errors = await self._initialize_core_services()
            if service_errors:
                validation_report["warnings"].extend(service_errors)
                logger.warning(f"Certains services en mode dégradé: {service_errors}")

            # 6. Tests de connectivité - VERSION CORRIGÉE
            logger.info("Tests de connectivité...")

            connectivity_status = await self._test_service_connectivity_corrected()
            validation_report["service_connectivity"] = connectivity_status

            # Logging détaillé pour debugging
            logger.debug(f"Résultats connectivité détaillés: {connectivity_status}")

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

            # LOGIQUE DE STATUS MODIFIÉE: Plus permissive
            critical_errors = [
                err
                for err in validation_report["errors"]
                if "critique" in err.lower() or "critical" in err.lower()
            ]

            if critical_errors:
                validation_report["overall_status"] = "failed"
                logger.error(f"Erreurs critiques détectées: {critical_errors}")
            elif validation_report["warnings"]:
                validation_report["overall_status"] = "degraded"
                logger.warning(
                    f"Application en mode dégradé: {len(validation_report['warnings'])} avertissements"
                )
            else:
                validation_report["overall_status"] = "healthy"
                logger.info("Application en parfaite santé")

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

    async def _validate_openai_config(
        self, api_key: str, timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Validation robuste de la configuration OpenAI avec gestion d'erreurs complète"""

        if not api_key:
            return {"status": "missing", "error": "API key manquante"}

        # Validation basique du format de la clé
        if not api_key.startswith(("sk-", "sk-proj-")):
            return {"status": "invalid", "error": "Format de clé API invalide"}

        # Masquer la clé dans les logs (sécurité)
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.debug(f"Validation OpenAI avec clé: {masked_key}")

        try:
            from openai import AsyncOpenAI

            test_client = AsyncOpenAI(
                api_key=api_key,
                timeout=timeout,
                max_retries=1,  # Une seule tentative pour le startup
            )

            # Test simple avec gestion d'erreur appropriée
            await asyncio.wait_for(test_client.models.list(), timeout=timeout)

            return {
                "status": "valid",
                "api_key_format": "ok",
                "connectivity": "ok",
                "masked_key": masked_key,
            }

        except asyncio.TimeoutError:
            logger.warning(f"Timeout validation OpenAI après {timeout}s")
            return {
                "status": "timeout",
                "error": f"Timeout après {timeout}s",
                "masked_key": masked_key,
            }

        except ImportError as e:
            logger.error(f"Module OpenAI non disponible: {e}")
            return {
                "status": "missing_module",
                "error": f"Module OpenAI non installé: {e}",
                "masked_key": masked_key,
            }

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            # Classification des erreurs
            if (
                "401" in error_msg
                or "Unauthorized" in error_msg
                or "invalid_api_key" in error_msg
            ):
                logger.warning(f"Clé API OpenAI invalide: {masked_key}")
                return {
                    "status": "invalid",
                    "error": "Clé API invalide ou expirée",
                    "error_type": error_type,
                    "masked_key": masked_key,
                }
            elif "403" in error_msg or "Forbidden" in error_msg:
                return {
                    "status": "forbidden",
                    "error": "Accès refusé - vérifier les permissions",
                    "error_type": error_type,
                    "masked_key": masked_key,
                }
            elif "429" in error_msg or "rate_limit" in error_msg.lower():
                return {
                    "status": "rate_limited",
                    "error": "Limite de taux atteinte",
                    "error_type": error_type,
                    "masked_key": masked_key,
                }
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                return {
                    "status": "network_error",
                    "error": "Erreur de connectivité réseau",
                    "error_type": error_type,
                    "masked_key": masked_key,
                }
            else:
                logger.error(f"Erreur OpenAI inattendue: {error_type}: {error_msg}")
                return {
                    "status": "unknown_error",
                    "error": f"{error_type}: {error_msg}",
                    "error_type": error_type,
                    "masked_key": masked_key,
                }

    async def _initialize_core_services(self) -> list:
        """Initialise les services principaux - VERSION CORRIGÉE POUR LE CACHE + AGENT RAG"""
        errors = []

        try:
            # Cache Core - CORRECTION PRINCIPALE
            logger.info("  Initialisation Cache Core...")
            try:
                from cache.cache_core import create_cache_core

                # Créer l'instance de cache
                cache_core = create_cache_core()

                # CHANGEMENT CRITIQUE: Ajouter le cache_core aux services AVANT l'initialisation
                # Cela permet aux endpoints de le trouver même s'il n'est pas initialisé
                self._critical_services["cache_core"] = cache_core
                logger.info("Cache Core ajouté aux services")

                # Tentative d'initialisation avec timeout et gestion d'erreurs
                try:
                    initialization_success = await asyncio.wait_for(
                        cache_core.initialize(), timeout=15.0
                    )

                    if initialization_success and getattr(
                        cache_core, "is_initialized", False
                    ):
                        logger.info("Cache Core initialized avec succès")
                    else:
                        logger.warning(
                            "⚠️ Cache Core créé mais non initialisé - mode dégradé"
                        )
                        errors.append(
                            "Cache Core: Initialisation échouée - mode dégradé"
                        )

                except asyncio.TimeoutError:
                    logger.warning("Warning: Timeout initialisation Cache Core")
                    errors.append("Cache Core: Timeout initialisation")

                except Exception as init_e:
                    logger.warning(f"Warning: Error initialisation Cache Core: {init_e}")
                    errors.append(f"Cache Core: Erreur initialisation - {init_e}")

            except ImportError as e:
                logger.error(f"Error: Module Cache Core non disponible: {e}")
                errors.append(f"Cache Core: Module non disponible - {e}")

            except Exception as e:
                logger.error(f"Error: Erreur création Cache Core: {e}")
                errors.append(f"Cache Core: Erreur création - {e}")

            # RAG Engine Enhanced
            logger.info("  Initialisation RAG Engine Enhanced...")
            try:
                from core.rag_engine import InteliaRAGEngine

                rag_engine_enhanced = InteliaRAGEngine()
                await rag_engine_enhanced.initialize()

                self._critical_services["rag_engine_enhanced"] = rag_engine_enhanced

                if rag_engine_enhanced.is_initialized:
                    logger.info("RAG Engine Enhanced initialisé")

                    # Vérifier intégrations
                    status = rag_engine_enhanced.get_status()

                    # Log statut LangSmith
                    langsmith_status = safe_dict_get(status, "langsmith", {})
                    if safe_dict_get(langsmith_status, "enabled", False):
                        project = safe_dict_get(langsmith_status, "project", "")
                        logger.info(f"LangSmith actif - Projet: {project}")

                    # Log statut RRF Intelligent
                    rrf_status = safe_dict_get(status, "intelligent_rrf", {})
                    if safe_dict_get(rrf_status, "enabled", False):
                        learning_mode = safe_dict_get(
                            rrf_status, "learning_mode", False
                        )
                        logger.info(
                            f"RRF Intelligent actif - Learning: {learning_mode}"
                        )

                else:
                    logger.warning("Warning: RAG Engine en mode dégradé")

            except Exception as e:
                errors.append(f"RAG Engine: {e}")
                logger.error(f"RAG Engine erreur: {e}")

            # CORRECTION: Agent RAG (optionnel) - NOUVEAU CODE
            logger.info("  Initialisation Agent RAG...")
            try:
                from extensions.agent_rag_extension import create_agent_rag_engine

                # Récupérer le rag_engine déjà initialisé
                rag_engine = self._critical_services.get("rag_engine_enhanced")

                if rag_engine and getattr(rag_engine, "is_initialized", False):
                    # Passer le rag_engine au factory + await car c'est async
                    agent_rag_engine = await create_agent_rag_engine(rag_engine)
                    self._critical_services["agent_rag_engine"] = agent_rag_engine
                    logger.info("RAG Agent disponible")
                else:
                    logger.warning("Agent RAG: RAG Engine requis mais non initialisé")

            except ImportError:
                logger.info("Agent RAG non disponible (optionnel)")
            except Exception as e:
                logger.warning(f"Agent RAG erreur: {e}")

        except Exception as e:
            errors.append(f"Erreur initialisation services: {e}")
            logger.error(f"Erreur générale initialisation services: {e}")

        return errors

    async def _test_service_connectivity_corrected(self) -> Dict[str, bool]:
        """CORRECTION: Teste la connectivité aux services externes avec accès correct au client Weaviate"""

        # Récupérer les clients depuis les services initialisés
        redis_client = None
        weaviate_client = None

        # Redis - inchangé
        cache_core = self._critical_services.get("cache_core")
        if cache_core and getattr(cache_core, "is_initialized", False):
            redis_client = getattr(cache_core, "client", None)

        # CORRECTION WEAVIATE: Accès correct selon la nouvelle architecture
        rag_engine = self._critical_services.get("rag_engine_enhanced")
        if rag_engine:
            # OPTION 1: Weaviate directement dans RAG engine (si ajouté)
            weaviate_client = getattr(rag_engine, "weaviate_client", None)

            # OPTION 2: Si pas trouvé, chercher dans weaviate_core (NOUVEAU)
            if not weaviate_client:
                weaviate_core = getattr(rag_engine, "weaviate_core", None)
                if weaviate_core:
                    weaviate_client = getattr(weaviate_core, "weaviate_client", None)
                    logger.debug("Client Weaviate trouvé dans weaviate_core")
                else:
                    logger.debug("weaviate_core non trouvé dans RAG engine")
            else:
                logger.debug("Client Weaviate trouvé directement dans RAG engine")

        # Logging pour debugging
        logger.debug(f"Redis client: {redis_client is not None}")
        logger.debug(f"Weaviate client: {weaviate_client is not None}")
        if weaviate_client:
            logger.debug(f"Type Weaviate client: {type(weaviate_client)}")
            logger.debug(
                f"Weaviate has collections: {hasattr(weaviate_client, 'collections')}"
            )
            logger.debug(
                f"Weaviate has is_ready: {hasattr(weaviate_client, 'is_ready')}"
            )

        try:
            # Test direct de Weaviate pour debugging
            weaviate_test_result = await self._debug_weaviate_connectivity(
                weaviate_client
            )
            logger.debug(f"Test direct Weaviate: {weaviate_test_result}")

            connectivity = await asyncio.wait_for(
                quick_connectivity_check(redis_client, weaviate_client), timeout=10.0
            )

            # Log détaillé du résultat
            logger.debug(f"Résultat quick_connectivity_check: {connectivity}")

            return connectivity

        except asyncio.TimeoutError:
            logger.warning("Timeout test connectivité")
            return {"redis": False, "weaviate": False, "timeout": True}
        except Exception as e:
            logger.error(f"Erreur test connectivité: {e}")
            return {"redis": False, "weaviate": False, "error": str(e)}

    async def _debug_weaviate_connectivity(self, weaviate_client) -> Dict[str, Any]:
        """Debug avancé de la connectivité Weaviate"""
        debug_result = {
            "client_present": weaviate_client is not None,
            "client_type": str(type(weaviate_client)) if weaviate_client else None,
            "has_collections": False,
            "has_is_ready": False,
            "is_ready_result": None,
            "is_ready_error": None,
            "collections_test": None,
            "collections_error": None,
        }

        if not weaviate_client:
            return debug_result

        debug_result["has_collections"] = hasattr(weaviate_client, "collections")
        debug_result["has_is_ready"] = hasattr(weaviate_client, "is_ready")

        try:
            # Test is_ready
            if hasattr(weaviate_client, "is_ready"):
                is_ready = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: weaviate_client.is_ready()
                )
                debug_result["is_ready_result"] = is_ready

                if not is_ready:
                    debug_result["is_ready_error"] = "Weaviate not ready"
                    return debug_result
            else:
                debug_result["is_ready_error"] = "No is_ready method"

            # Test collections
            if hasattr(weaviate_client, "collections"):
                try:
                    collections = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: list(weaviate_client.collections.list_all())
                    )
                    debug_result["collections_test"] = (
                        f"Found {len(collections)} collections"
                    )
                except Exception as coll_e:
                    debug_result["collections_error"] = str(coll_e)
            else:
                debug_result["collections_error"] = "No collections method"

        except Exception as e:
            debug_result["is_ready_error"] = str(e)

        return debug_result

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
                        "modules": safe_dict_get(
                            safe_rag_status, "modules", {}
                        ),  # NOUVEAU
                        "capabilities": safe_dict_get(
                            safe_rag_status, "capabilities", {}
                        ),  # NOUVEAU
                    }

                    # NOUVEAU: Statut spécifique Weaviate
                    weaviate_core = getattr(rag_engine, "weaviate_core", None)
                    if weaviate_core:
                        weaviate_initialized = getattr(
                            weaviate_core, "is_initialized", False
                        )
                        weaviate_client = getattr(
                            weaviate_core, "weaviate_client", None
                        )

                        global_status["services"]["weaviate"] = {
                            "status": "healthy" if weaviate_initialized else "degraded",
                            "core_initialized": weaviate_initialized,
                            "client_connected": bool(weaviate_client),
                            "available": True,
                        }

                        # Obtenir les stats Weaviate si disponibles
                        if hasattr(weaviate_core, "get_stats"):
                            try:
                                weaviate_stats = weaviate_core.get_stats()
                                global_status["services"]["weaviate"]["stats"] = (
                                    safe_serialize_for_json(weaviate_stats)
                                )
                            except Exception as stats_e:
                                global_status["services"]["weaviate"]["stats_error"] = (
                                    str(stats_e)
                                )
                    else:
                        global_status["services"]["weaviate"] = {
                            "status": "missing",
                            "available": False,
                            "reason": "weaviate_core_not_initialized_in_rag_engine",
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

            # Cache - CORRECTION PRINCIPALE
            cache_core = self._critical_services.get("cache_core")
            if cache_core:
                try:
                    # Le cache_core existe, récupérer son statut
                    cache_initialized = getattr(cache_core, "is_initialized", False)
                    cache_enabled = getattr(cache_core, "enabled", False)

                    cache_health_data = {
                        "status": (
                            "healthy"
                            if (cache_initialized and cache_enabled)
                            else "degraded"
                        ),
                        "enabled": cache_enabled,
                        "initialized": cache_initialized,
                        "available": True,
                    }

                    # Essayer de récupérer les stats si disponibles
                    if hasattr(cache_core, "get_cache_stats"):
                        try:
                            cache_stats = await cache_core.get_cache_stats()
                            cache_health_data["stats"] = safe_serialize_for_json(
                                cache_stats
                            )
                        except Exception as stats_e:
                            cache_health_data["stats_error"] = str(stats_e)

                    global_status["services"]["cache"] = cache_health_data

                except Exception as e:
                    logger.error(f"Erreur statut cache: {e}")
                    global_status["services"]["cache"] = {
                        "status": "error",
                        "error": str(e),
                        "available": True,
                    }
            else:
                global_status["services"]["cache"] = {
                    "status": "missing",
                    "available": False,
                    "reason": "cache_core_not_found_in_services",
                }

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
                "monitoring_version": "1.0.4-agent-rag-fixed",
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
            return getattr(service, "is_initialized", False)
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
