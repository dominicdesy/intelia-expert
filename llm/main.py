# -*- coding: utf-8 -*-

"""

main.py - Intelia Expert Backend - ARCHITECTURE MODULAIRE PURE
Point d'entrée minimaliste avec délégation complète aux modules

"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# === IMPORTS MODULAIRES - CORRECTIONS ===
# AVANT (avec erreur):
# from .config.config import validate_config, BASE_PATH, ALLOWED_ORIGINS, STARTUP_TIMEOUT
# from .utils.imports_and_dependencies import require_critical_dependencies
# from .utils.monitoring import create_health_monitor
# from .utils.utilities import setup_logging
# from .api.endpoints import create_router

# APRÈS (corrigé):
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
# GESTION DU CYCLE DE VIE
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie avec architecture modulaire"""

    logger.info("🚀 Démarrage Intelia Expert Backend - Architecture Modulaire")

    try:
        # 1. Validation configuration
        config_valid, config_errors = validate_config()
        if not config_valid:
            logger.error(f"Configuration invalide: {config_errors}")
            for error in config_errors:
                logger.warning(f"Config: {error}")

        # 2. Vérifier dépendances critiques
        logger.info("Validation des dépendances critiques...")
        require_critical_dependencies()
        logger.info("✅ Dépendances critiques validées")

        # 3. Créer health monitor
        logger.info("Initialisation SystemHealthMonitor...")
        health_monitor = await create_health_monitor()
        services["health_monitor"] = health_monitor

        # 4. Validation startup complète
        logger.info("Validation startup requirements...")
        validation_result = await asyncio.wait_for(
            health_monitor.validate_startup_requirements(), timeout=STARTUP_TIMEOUT
        )

        if validation_result["overall_status"] == "failed":
            logger.error("❌ Validation startup échouée - Arrêt de l'application")
            raise RuntimeError(
                f"Startup validation failed: {validation_result['errors']}"
            )

        elif validation_result["overall_status"] == "degraded":
            logger.warning("⚠️ Application démarrée en mode dégradé")
            for warning in validation_result.get("warnings", []):
                logger.warning(f"  - {warning}")

        else:
            logger.info("✅ Application démarrée avec succès")

            # Log statut des intégrations
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

        # 5. Application prête
        logger.info(f"🌐 API disponible sur {BASE_PATH}")
        logger.info("📊 Services initialisés:")
        for service_name, service in services.items():
            logger.info(f"  - {service_name}: {type(service).__name__}")

        yield

    except asyncio.TimeoutError:
        logger.error(f"❌ Timeout startup après {STARTUP_TIMEOUT}s")
        raise RuntimeError("Startup timeout")

    except Exception as e:
        logger.error(f"❌ Erreur critique au démarrage: {e}")
        raise

    finally:
        # Nettoyage
        logger.info("🧹 Nettoyage des ressources...")

        try:
            # Cleanup des services via health monitor
            health_monitor = services.get("health_monitor")
            if health_monitor:
                all_services = health_monitor.get_all_services()

                # Cleanup cache
                cache_core = all_services.get("cache_core")
                if cache_core and hasattr(cache_core, "cleanup"):
                    await cache_core.cleanup()

                # Cleanup RAG engine
                rag_engine = all_services.get("rag_engine_enhanced")
                if rag_engine and hasattr(rag_engine, "cleanup"):
                    await rag_engine.cleanup()

                # Cleanup agent RAG
                agent_rag = all_services.get("agent_rag_engine")
                if agent_rag and hasattr(agent_rag, "cleanup"):
                    await agent_rag.cleanup()

            # Nettoyer les services globaux
            services.clear()

        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")

        logger.info("✅ Application arrêtée")


# ============================================================================
# CRÉATION DE L'APPLICATION
# ============================================================================

# Créer l'application FastAPI
app = FastAPI(
    title="Intelia Expert Backend",
    description="API RAG Enhanced avec LangSmith et RRF Intelligent - Architecture Modulaire",
    version="4.0.0-modular",
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

# Inclusion du router avec services injectés
router = create_router(services)
app.include_router(router)

# ============================================================================
# ENDPOINTS DIRECTS (pour compatibilité)
# ============================================================================

# ❌ SECTION SUPPRIMÉE - doublon de route /health retiré


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
            "architecture": "modular",
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "json_test": "FAILED"}


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🚀 Démarrage serveur sur {host}:{port}")
    logger.info("🔧 Architecture modulaire activée")

    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
