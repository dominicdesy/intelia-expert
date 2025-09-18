# -*- coding: utf-8 -*-

"""
main.py - Intelia Expert Backend - ARCHITECTURE MODULAIRE PURE
Point d'entrée minimaliste avec délégation complète aux modules
VERSION CORRIGÉE: Injection des services réparée pour le cache
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# === IMPORTS MODULAIRES ===
from config.config import validate_config, BASE_PATH, ALLOWED_ORIGINS, STARTUP_TIMEOUT
from utils.imports_and_dependencies import require_critical_dependencies
from utils.monitoring import create_health_monitor
from utils.utilities import setup_logging
from api.endpoints import create_router

# Configuration
load_dotenv()
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Services globaux (injectés dans les endpoints)
services = {}

# ============================================================================
# GESTION DU CYCLE DE VIE - VERSION CORRIGÉE INJECTION SERVICES
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie avec injection correcte des services"""

    logger.info("🚀 Démarrage Intelia Expert Backend - Architecture Modulaire")

    try:
        # 1. Validation configuration
        config_valid, config_errors = validate_config()
        if not config_valid:
            logger.error(f"Configuration invalide: {config_errors}")
            for error in config_errors:
                logger.warning(f"Config: {error}")
        else:
            logger.info("✅ Configuration validée")

        # 2. Vérifier dépendances critiques
        logger.info("Validation des dépendances critiques...")
        require_critical_dependencies()
        logger.info("✅ Dépendances critiques validées")

        # 3. Créer health monitor
        logger.info("Initialisation SystemHealthMonitor...")
        health_monitor = await create_health_monitor()
        services["health_monitor"] = health_monitor

        # 4. Validation startup complète - CORRECTION CACHE
        logger.info("Validation startup requirements...")
        validation_result = await asyncio.wait_for(
            health_monitor.validate_startup_requirements(), timeout=STARTUP_TIMEOUT
        )

        # CHANGEMENT PRINCIPAL: Ne pas arrêter l'app si seul le cache échoue
        if validation_result["overall_status"] == "failed":
            # Vérifier si ce sont des erreurs critiques ou juste du cache/redis
            errors = validation_result.get("errors", [])
            critical_errors = [
                err
                for err in errors
                if not any(
                    keyword in err.lower()
                    for keyword in ["cache", "redis", "connexion", "timeout", "network"]
                )
            ]

            if critical_errors:
                logger.error("❌ Erreurs critiques détectées - Arrêt de l'application")
                logger.error(f"Erreurs critiques: {critical_errors}")
                raise RuntimeError(f"Critical startup errors: {critical_errors}")
            else:
                logger.warning("⚠️ Erreurs de services externes uniquement - Continuons")
                logger.warning(f"Services dégradés: {errors}")

        elif validation_result["overall_status"] == "degraded":
            logger.warning("⚠️ Application démarrée en mode dégradé")
            for warning in validation_result.get("warnings", []):
                logger.warning(f"  - {warning}")

        else:
            logger.info("✅ Application démarrée avec succès")

        # 5. Vérifications post-startup des services
        logger.info("Vérification des services initialisés...")

        # Vérification explicite du cache
        cache_core = health_monitor.get_service("cache_core")
        if cache_core:
            cache_initialized = getattr(cache_core, "initialized", False)
            cache_enabled = getattr(cache_core, "enabled", False)

            if cache_initialized and cache_enabled:
                logger.info("✅ Cache Core opérationnel")
            elif cache_core:
                logger.warning("⚠️ Cache Core présent mais non opérationnel")
            else:
                logger.warning("⚠️ Cache Core non initialisé - mode sans cache")
        else:
            logger.warning("⚠️ Cache Core non disponible - mode sans cache")

        # Vérification RAG Engine
        rag_engine = health_monitor.get_service("rag_engine_enhanced")
        if rag_engine and getattr(rag_engine, "is_initialized", False):
            logger.info("✅ RAG Engine opérationnel")
        else:
            logger.warning("⚠️ RAG Engine non disponible")

        # Log statut des intégrations avancées
        langsmith_status = validation_result.get("langsmith_validation", {})
        if langsmith_status.get("status") == "configured":
            logger.info(
                f"🧠 LangSmith actif - Projet: {langsmith_status.get('project')}"
            )

        rrf_status = validation_result.get("rrf_validation", {})
        if rrf_status.get("status") == "configured":
            logger.info(
                f"⚡ RRF Intelligent actif - Learning: {rrf_status.get('learning_mode')}"
            )

        # 6. CORRECTION CRITIQUE : Re-créer le router avec les services initialisés
        logger.info("Mise à jour du router avec services initialisés...")

        # Créer le nouveau router avec les services maintenant disponibles
        updated_router = create_router(services)

        # Remplacer les routes existantes
        app.router.routes.clear()
        app.include_router(updated_router)

        logger.info("✅ Router mis à jour avec services injectés")

        # 7. Application prête
        logger.info(f"🌐 API disponible sur {BASE_PATH}")
        logger.info("📊 Services initialisés:")
        for service_name, service in services.items():
            service_status = "✅ OK" if service else "❌ FAILED"
            logger.info(
                f"  - {service_name}: {type(service).__name__} {service_status}"
            )

        # Log final du mode de fonctionnement
        if validation_result["overall_status"] == "healthy":
            logger.info("🎯 Mode: COMPLET (tous services opérationnels)")
        elif validation_result["overall_status"] == "degraded":
            logger.info("🔶 Mode: DÉGRADÉ (services essentiels seulement)")
        else:
            logger.info("🔶 Mode: MINIMAL (fonctionnalités de base)")

        yield

    except asyncio.TimeoutError:
        logger.error(f"❌ Timeout startup après {STARTUP_TIMEOUT}s")
        # Ne pas raise - permettre le démarrage en mode minimal
        logger.warning("Démarrage en mode minimal suite au timeout")
        yield

    except Exception as e:
        logger.error(f"❌ Erreur au démarrage: {e}")
        logger.warning("Tentative de démarrage en mode minimal...")

        # Créer un health monitor minimal si possible
        if "health_monitor" not in services:
            try:
                minimal_monitor = await create_health_monitor()
                services["health_monitor"] = minimal_monitor
                logger.info("✅ Health monitor minimal créé")
            except Exception as monitor_e:
                logger.error(f"Impossible de créer health monitor: {monitor_e}")

        # Permettre le démarrage même avec des erreurs
        yield

    finally:
        # Nettoyage amélioré
        logger.info("🧹 Nettoyage des ressources...")

        try:
            # Cleanup des services via health monitor
            health_monitor = services.get("health_monitor")
            if health_monitor:
                all_services = health_monitor.get_all_services()
                cleanup_errors = []

                # Cleanup cache avec timeout
                cache_core = all_services.get("cache_core")
                if cache_core and hasattr(cache_core, "cleanup"):
                    try:
                        await asyncio.wait_for(cache_core.cleanup(), timeout=5.0)
                        logger.info("✅ Cache Core nettoyé")
                    except Exception as e:
                        cleanup_errors.append(f"Cache cleanup: {e}")

                # Cleanup RAG engine avec timeout
                rag_engine = all_services.get("rag_engine_enhanced")
                if rag_engine and hasattr(rag_engine, "cleanup"):
                    try:
                        await asyncio.wait_for(rag_engine.cleanup(), timeout=5.0)
                        logger.info("✅ RAG Engine nettoyé")
                    except Exception as e:
                        cleanup_errors.append(f"RAG cleanup: {e}")

                # Cleanup agent RAG
                agent_rag = all_services.get("agent_rag_engine")
                if agent_rag and hasattr(agent_rag, "cleanup"):
                    try:
                        await asyncio.wait_for(agent_rag.cleanup(), timeout=3.0)
                        logger.info("✅ Agent RAG nettoyé")
                    except Exception as e:
                        cleanup_errors.append(f"Agent RAG cleanup: {e}")

                if cleanup_errors:
                    logger.warning(
                        f"Erreurs de nettoyage (non critiques): {cleanup_errors}"
                    )

            # Nettoyer les services globaux
            services.clear()

        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")

        logger.info("✅ Application arrêtée proprement")


# ============================================================================
# CRÉATION DE L'APPLICATION
# ============================================================================

# Créer l'application FastAPI
app = FastAPI(
    title="Intelia Expert Backend",
    description="API RAG Enhanced avec LangSmith et RRF Intelligent - Architecture Modulaire Robuste",
    version="4.0.0-modular-robust",
    lifespan=lifespan,
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# CORRECTION CRITIQUE: Créer un router initial vide, il sera mis à jour dans lifespan
# Le vrai router avec services sera créé dans la fonction lifespan
initial_router = create_router({})  # Router vide au démarrage
app.include_router(initial_router)

# ============================================================================
# ENDPOINTS DIRECTS (pour compatibilité et debug)
# ============================================================================


@app.get("/test-json")
async def test_json_direct():
    """Test simple de sérialisation JSON"""
    from utils.utilities import safe_serialize_for_json

    try:
        test_data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "timestamp": __import__("time").time(),
        }

        # Test de sérialisation
        safe_data = safe_serialize_for_json(test_data)

        return {
            "status": "success",
            "original_data": test_data,
            "serialized_data": safe_data,
            "json_test": "OK",
            "architecture": "modular-robust",
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "json_test": "FAILED"}


@app.get("/startup-info")
async def startup_info():
    """Informations sur le démarrage et les services"""
    try:
        health_monitor = services.get("health_monitor")
        if not health_monitor:
            return {"error": "Health monitor non disponible"}

        # Récupérer les informations de validation
        validation_report = getattr(health_monitor, "validation_report", {})

        return {
            "startup_status": validation_report.get("overall_status", "unknown"),
            "startup_duration": validation_report.get("startup_duration", 0),
            "services_available": (
                list(health_monitor.get_all_services().keys())
                if hasattr(health_monitor, "get_all_services")
                else []
            ),
            "errors": validation_report.get("errors", []),
            "warnings": validation_report.get("warnings", []),
            "cache_available": "cache_core"
            in (
                health_monitor.get_all_services()
                if hasattr(health_monitor, "get_all_services")
                else {}
            ),
            "timestamp": __import__("time").time(),
        }

    except Exception as e:
        return {"error": str(e), "timestamp": __import__("time").time()}


@app.get("/version")
async def version_info():
    """Endpoint de version pour vérifier les déploiements"""
    import time
    import importlib.util

    # Test d'import du cache pour diagnostic
    cache_import_status = "unknown"
    try:
        spec = importlib.util.find_spec("cache.cache_core")
        if spec is not None:
            cache_import_status = "success"
        else:
            cache_import_status = "failed: module not found"
    except Exception as e:
        cache_import_status = f"error: {str(e)}"

    return {
        "version": "4.0.2-services-injection-fixed",
        "timestamp": time.time(),
        "build_time": "2024-09-18-15:00",
        "corrections_deployed": True,
        "cache_import_test": cache_import_status,
        "health_monitor_available": "health_monitor" in services,
        "services_count": len(services),
        "services_list": list(services.keys()),
        "python_working_dir": os.getcwd(),
        "app_status": "running",
        "router_injection": "fixed",
    }


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🚀 Démarrage serveur sur {host}:{port}")
    logger.info("🔧 Architecture modulaire robuste activée")
    logger.info("🛡️ Mode dégradé supporté pour cache/Redis")
    logger.info("🔧 Injection des services corrigée")

    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
