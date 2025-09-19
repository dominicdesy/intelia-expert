# -*- coding: utf-8 -*-


"""

main.py - Intelia Expert Backend - ARCHITECTURE MODULAIRE PURE
Point d'entrée minimaliste avec délégation complète aux modules

"""


import os
import asyncio
import logging
import time
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

# === DEBUG DEPLOYMENT - MESSAGES VISIBLES ===
print("=" * 80)
print("🔥 VERSION FINALE MAIN.PY CHARGÉE - TOUS ENDPOINTS DANS ROUTER")
print("🔥 VERSION: 4.0.3-endpoints-centralized")
print("🔥 TIMESTAMP CHARGEMENT:", time.time())
print("=" * 80)

# Configuration
load_dotenv()
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Message de log immédiat
logger.critical(
    "🚨 VERSION FINALE DÉTECTÉE - main.py version 4.0.3-endpoints-centralized"
)
logger.critical("🚨 Tous les endpoints sont maintenant dans le router !")
logger.critical("🚨 TIMESTAMP LOGGER: %s", time.time())

# Services globaux (injectés dans les endpoints)
services = {}

# ============================================================================
# GESTION DU CYCLE DE VIE - VERSION FINALE
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie avec injection correcte des services"""

    # MESSAGE CRITIQUE AU DÉMARRAGE
    logger.critical("🔥🔥🔥 DÉMARRAGE VERSION FINALE - ARCHITECTURE CENTRALISÉE 🔥🔥🔥")
    logger.critical("🔥🔥🔥 TIMESTAMP LIFESPAN: %s 🔥🔥🔥", time.time())
    print("🔥🔥🔥 LIFESPAN DÉMARRÉ - VERSION FINALE 🔥🔥🔥")

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

        # 3. Pré-chargement du modèle FastText pour détection multilingue
        logger.info("Pré-chargement du modèle FastText...")
        try:
            from utils.utilities import _load_fasttext_model
            from config.config import FASTTEXT_MODEL_PATH
            import os

            # Vérifier si le modèle existe, sinon le télécharger
            if not os.path.exists(FASTTEXT_MODEL_PATH):
                logger.info(f"Téléchargement du modèle FastText: {FASTTEXT_MODEL_PATH}")

                # Télécharger selon le type de modèle dans la variable d'environnement
                if "lid" in FASTTEXT_MODEL_PATH.lower() or "176" in FASTTEXT_MODEL_PATH:
                    # Modèle de détection de langue - téléchargement direct
                    logger.info(
                        "Téléchargement direct du modèle de détection de langue..."
                    )
                    import urllib.request

                    # URL directe du modèle de détection de langue FastText
                    model_url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
                    logger.info("Téléchargement depuis l'URL officielle FastText...")

                    urllib.request.urlretrieve(model_url, FASTTEXT_MODEL_PATH)
                    logger.info(f"Modèle téléchargé vers: {FASTTEXT_MODEL_PATH}")

                else:
                    # Modèle d'embeddings - utiliser fasttext.util
                    import fasttext.util

                    if "en" in FASTTEXT_MODEL_PATH:
                        logger.info("Téléchargement du modèle d'embeddings anglais...")
                        fasttext.util.download_model("en", if_exists="ignore")
                        if not os.path.exists(FASTTEXT_MODEL_PATH) and os.path.exists(
                            "cc.en.300.bin"
                        ):
                            import shutil

                            shutil.copy("cc.en.300.bin", FASTTEXT_MODEL_PATH)
                            logger.info(f"Modèle copié vers: {FASTTEXT_MODEL_PATH}")

            # Maintenant essayer de charger le modèle
            fasttext_model = _load_fasttext_model()
            if fasttext_model:
                logger.info("✅ Modèle FastText pré-chargé avec succès")
            else:
                logger.warning(
                    "⚠️ Modèle FastText non disponible - détection langue dégradée"
                )

        except Exception as e:
            logger.warning(f"⚠️ Erreur pré-chargement FastText: {e}")
            # Log plus détaillé pour diagnostic
            import traceback

            logger.debug(f"Traceback FastText: {traceback.format_exc()}")

        # 4. Créer health monitor
        logger.info("Initialisation SystemHealthMonitor...")
        health_monitor = await create_health_monitor()
        services["health_monitor"] = health_monitor

        # 5. Validation startup complète
        logger.info("Validation startup requirements...")
        validation_result = await asyncio.wait_for(
            health_monitor.validate_startup_requirements(), timeout=STARTUP_TIMEOUT
        )

        # CHANGEMENT PRINCIPAL: Ne pas arrêter l'app si seul le cache échoue
        if validation_result["overall_status"] == "failed":
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

        # 6. CORRECTION FINALE : Re-créer le router avec les services initialisés
        logger.critical("🔧 INJECTION DES SERVICES - ARCHITECTURE CENTRALISÉE 🔧")
        logger.info("Mise à jour du router avec services initialisés...")

        # Créer le nouveau router avec les services maintenant disponibles
        updated_router = create_router(services)

        # Remplacer les routes existantes
        app.router.routes.clear()
        app.include_router(updated_router)

        logger.critical("✅ ROUTER CENTRALISÉ MIS À JOUR AVEC SERVICES INJECTÉS ✅")
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

        logger.critical(
            "🎉 APPLICATION VERSION FINALE PRÊTE - ARCHITECTURE CENTRALISÉE 🎉"
        )
        print("🎉 APPLICATION VERSION FINALE PRÊTE 🎉")

        yield

    except asyncio.TimeoutError:
        logger.error(f"❌ Timeout startup après {STARTUP_TIMEOUT}s")
        logger.warning("Démarrage en mode minimal suite au timeout")
        yield

    except Exception as e:
        logger.error(f"❌ Erreur au démarrage: {e}")
        logger.warning("Tentative de démarrage en mode minimal...")

        if "health_monitor" not in services:
            try:
                minimal_monitor = await create_health_monitor()
                services["health_monitor"] = minimal_monitor
                logger.info("✅ Health monitor minimal créé")
            except Exception as monitor_e:
                logger.error(f"Impossible de créer health monitor: {monitor_e}")

        yield

    finally:
        # Nettoyage amélioré
        logger.info("🧹 Nettoyage des ressources...")
        logger.critical("🔥 SHUTDOWN VERSION FINALE 🔥")

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
# CRÉATION DE L'APPLICATION - VERSION FINALE SIMPLIFIÉE
# ============================================================================

# MESSAGE DEBUG CRÉATION APP
logger.critical("🗂️ CRÉATION FASTAPI APP - VERSION FINALE 🗂️")

# Créer l'application FastAPI
app = FastAPI(
    title="Intelia Expert Backend",
    description="API RAG Enhanced avec LangSmith et RRF Intelligent - Architecture Centralisée",
    version="4.0.3-endpoints-centralized",
    lifespan=lifespan,
)

logger.critical("✅ FASTAPI APP CRÉÉE AVEC ARCHITECTURE CENTRALISÉE ✅")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ARCHITECTURE FINALE: Router initial vide, sera mis à jour dans lifespan
initial_router = create_router({})  # Router vide au démarrage
app.include_router(initial_router)

logger.critical("🔗 ROUTER INITIAL AJOUTÉ - TOUS ENDPOINTS DANS LE ROUTER 🔗")

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.critical("🚀 DÉMARRAGE SERVEUR VERSION FINALE SUR %s:%s", host, port)
    logger.info(f"🚀 Démarrage serveur sur {host}:{port}")
    logger.info("🔧 Architecture modulaire centralisée activée")
    logger.info("🛡️ Mode dégradé supporté pour cache/Redis")
    logger.info("🔧 Injection des services corrigée")
    logger.critical("🔥 VERSION FINALE: 4.0.3-endpoints-centralized 🔥")

    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
