# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend - ARCHITECTURE MODULAIRE PURE
Point d'entrée minimaliste avec délégation complète aux modules

Version: 2.1.6 - Use native docker login for authentication
"""

import os
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# === IMPORTS MODULAIRES ===
from config.config import (
    validate_config,
    BASE_PATH,
    ALLOWED_ORIGINS,
    STARTUP_TIMEOUT,
    SUPPORTED_LANGUAGES,
)
from utils.imports_and_dependencies import require_critical_dependencies
from utils.monitoring import create_health_monitor
from utils.utilities import setup_logging
from api.endpoints import create_router

# === DEBUG DEPLOYMENT - MESSAGES VISIBLES ===
print("=" * 80)
print("INTELIA EXPERT BACKEND - MAIN MODULE LOADED")
print("INTELIA EXPERT BACKEND - MAIN MODULE LOADED")
print(" TIMESTAMP CHARGEMENT:", time.time())
print("=" * 80)

# Configuration
load_dotenv()
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Message de log immédiat
logger.critical(
    " VERSION FINALE DÉTECTÉE - main.py version 4.0.4-translation-service-fixed"
)
logger.info(" Tous les endpoints sont maintenant dans le router !")
logger.info(" Service de traduction initialisé au démarrage !")
logger.critical(" TIMESTAMP LOGGER: %s", time.time())

# Services globaux (injectés dans les endpoints)
services = {}

# ============================================================================
# GESTION DU CYCLE DE VIE - VERSION FINALE AVEC TRADUCTION
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie avec injection correcte des services"""

    # MESSAGE CRITIQUE AU DÉMARRAGE
    logger.info(" DÉMARRAGE VERSION FINALE - ARCHITECTURE CENTRALISÉE ")
    logger.critical(" TIMESTAMP LIFESPAN: %s ", time.time())
    print("INTELIA EXPERT BACKEND - MAIN MODULE LOADED")

    logger.info(" Démarrage Intelia Expert Backend - Architecture Modulaire")

    try:
        # 1. Validation configuration
        config_valid, config_errors = validate_config()
        if not config_valid:
            logger.error(f"Configuration invalide: {config_errors}")
            for error in config_errors:
                logger.warning(f"Config: {error}")
        else:
            logger.info("[OK] Configuration validée")

        # 2. Vérifier dépendances critiques
        logger.info("Validation des dépendances critiques...")
        require_critical_dependencies()
        logger.info(
            "[OK] Dépendances critiques validées"
        )  # 3. Vérification des bibliothèques de détection de langue
        logger.info("Checking language detection libraries...")
        try:
            from utils.language_detection import (
                FASTTEXT_LANGDETECT_AVAILABLE,
                LANGDETECT_AVAILABLE,
            )

            if FASTTEXT_LANGDETECT_AVAILABLE:
                logger.info(
                    "Language detection: fasttext-langdetect available (primary)"
                )
            elif LANGDETECT_AVAILABLE:
                logger.info("Language detection: langdetect available (fallback only)")
            else:
                logger.warning("Warning: No language detection library available")

        except Exception as e:
            logger.warning(f"Warning: Language detection check error: {e}")

        # 4. NOUVEAU: Initialisation du service de traduction universel
        logger.info("Initialisation du service de traduction universel...")
        try:
            from utils.translation_service import init_global_translation_service

            # Chemin absolu vers les dictionnaires
            dict_path = Path(__file__).parent / "config"

            logger.info(f"Chemin dictionnaires: {dict_path}")

            # Initialiser le service global
            translation_service = init_global_translation_service(
                dict_path=str(dict_path),
                supported_languages=SUPPORTED_LANGUAGES,
                enable_google_fallback=os.getenv(
                    "ENABLE_GOOGLE_TRANSLATE", "false"
                ).lower()
                == "true",
                google_api_key=os.getenv("GOOGLE_TRANSLATE_API_KEY"),
                enable_technical_exclusion=True,
            )

            if translation_service:
                # CORRECTION: Précharger les dictionnaires pour toutes les langues supportées
                logger.info(
                    f"Préchargement des dictionnaires pour {len(SUPPORTED_LANGUAGES)} langues..."
                )
                preload_results = translation_service.preload_languages(
                    list(SUPPORTED_LANGUAGES)
                )

                # Comptabiliser les succès
                loaded_count = sum(1 for success in preload_results.values() if success)
                failed_langs = [
                    lang for lang, success in preload_results.items() if not success
                ]

                # Vérifier que les dictionnaires sont bien chargés
                num_dicts = len(translation_service._language_dictionaries)
                logger.info(
                    f"[OK] Service de traduction initialisé - {num_dicts} dictionnaires chargés ({loaded_count}/{len(SUPPORTED_LANGUAGES)} langues)"
                )

                if failed_langs:
                    logger.warning(
                        f"Warning: Langues non chargées: {', '.join(failed_langs)}"
                    )

                # Vérifier les domaines disponibles pour debug
                try:
                    available_domains = translation_service.get_available_domains()
                    logger.info(
                        f" Domaines disponibles: {len(available_domains)} domaines"
                    )
                    if available_domains:
                        logger.debug(
                            f"Domaines: {', '.join(list(available_domains)[:5])}"
                        )
                except Exception as domain_err:
                    logger.warning(f"Impossible de lister les domaines: {domain_err}")

                services["translation_service"] = translation_service
            else:
                logger.warning("Warning: Service de traduction retourné None")

        except ImportError as e:
            logger.error(f"[ERROR] Import error service traduction: {e}")
        except Exception as e:
            logger.error(f"[ERROR] Erreur initialisation service traduction: {e}")
            import traceback

            logger.debug(f"Traceback traduction: {traceback.format_exc()}")

        # 5. Créer health monitor
        logger.info("Initialisation SystemHealthMonitor...")
        health_monitor = await create_health_monitor()
        services["health_monitor"] = health_monitor

        # 6. Validation startup complète
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
                logger.error(
                    "[ERROR] Erreurs critiques détectées - Arrêt de l'application"
                )
                logger.error(f"Erreurs critiques: {critical_errors}")
                raise RuntimeError(f"Critical startup errors: {critical_errors}")
            else:
                logger.warning(
                    "Warning: Erreurs de services externes uniquement - Continuons"
                )
                logger.warning(f"Services dégradés: {errors}")

        elif validation_result["overall_status"] == "degraded":
            logger.warning("Warning: Application démarrée en mode dégradé")
            for warning in validation_result.get("warnings", []):
                logger.warning(f"  - {warning}")
        else:
            logger.info("[OK] Application démarrée avec succès")

        # 7. Vérifications post-startup des services
        logger.info("Vérification des services initialisés...")

        # Vérification explicite du cache
        cache_core = health_monitor.get_service("cache_core")
        if cache_core:
            cache_initialized = getattr(cache_core, "is_initialized", False)
            cache_enabled = getattr(cache_core, "enabled", False)

            if cache_initialized and cache_enabled:
                logger.info("[OK] Cache Core opérationnel")
            elif cache_core:
                logger.warning("Warning: Cache Core présent mais non opérationnel")
            else:
                logger.warning("Warning: Cache Core non initialisé - mode sans cache")
        else:
            logger.warning("Warning: Cache Core non disponible - mode sans cache")

        # Vérification RAG Engine
        rag_engine = health_monitor.get_service("rag_engine_enhanced")
        if rag_engine and getattr(rag_engine, "is_initialized", False):
            logger.info("[OK] RAG Engine opérationnel")
        else:
            logger.warning("Warning: RAG Engine non disponible")

        # Vérification service de traduction
        translation_service = services.get("translation_service")
        if translation_service:
            logger.info("[OK] Service de traduction opérationnel")
        else:
            logger.warning("Warning: Service de traduction non disponible")

        # Log statut des intégrations avancées
        langsmith_status = validation_result.get("langsmith_validation", {})
        if langsmith_status.get("status") == "configured":
            logger.info(f" LangSmith actif - Projet: {langsmith_status.get('project')}")

        rrf_status = validation_result.get("rrf_validation", {})
        if rrf_status.get("status") == "configured":
            logger.info(
                f" RRF Intelligent actif - Learning: {rrf_status.get('learning_mode')}"
            )

        # 8. CORRECTION FINALE : Re-créer le router avec les services initialisés
        logger.info(" INJECTION DES SERVICES - ARCHITECTURE CENTRALISÉE ")
        logger.info("Mise à jour du router avec services initialisés...")

        # Créer le nouveau router avec les services maintenant disponibles
        updated_router = create_router(services)

        # Remplacer les routes existantes
        app.router.routes.clear()
        app.include_router(updated_router)

        logger.info("[OK] ROUTER CENTRALISÉ MIS À JOUR AVEC SERVICES INJECTÉS [OK]")
        logger.info("[OK] Router mis à jour avec services injectés")

        # 9. Application prête
        logger.info(f" API disponible sur {BASE_PATH}")
        logger.info(" Services initialisés:")
        for service_name, service in services.items():
            service_status = "[OK] OK" if service else "[ERROR] FAILED"
            logger.info(
                f"  - {service_name}: {type(service).__name__} {service_status}"
            )

        # Log final du mode de fonctionnement
        if validation_result["overall_status"] == "healthy":
            logger.info(" Mode: COMPLET (tous services opérationnels)")
        elif validation_result["overall_status"] == "degraded":
            logger.info(" Mode: DÉGRADÉ (services essentiels seulement)")
        else:
            logger.info(" Mode: MINIMAL (fonctionnalités de base)")

        logger.critical(" APPLICATION VERSION FINALE PRÊTE - ARCHITECTURE CENTRALISÉE ")
        print("INTELIA EXPERT BACKEND - MAIN MODULE LOADED")

        yield

    except asyncio.TimeoutError:
        logger.error(f"[ERROR] Timeout startup après {STARTUP_TIMEOUT}s")
        logger.warning("Démarrage en mode minimal suite au timeout")
        yield

    except Exception as e:
        logger.error(f"[ERROR] Erreur au démarrage: {e}")
        logger.warning("Tentative de démarrage en mode minimal...")

        if "health_monitor" not in services:
            try:
                minimal_monitor = await create_health_monitor()
                services["health_monitor"] = minimal_monitor
                logger.info("[OK] Health monitor minimal créé")
            except Exception as monitor_e:
                logger.error(f"Impossible de créer health monitor: {monitor_e}")

        yield

    finally:
        # Nettoyage amélioré
        logger.info(" Nettoyage des ressources...")
        logger.info(" SHUTDOWN VERSION FINALE ")

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
                        logger.info("[OK] Cache Core nettoyé")
                    except Exception as e:
                        cleanup_errors.append(f"Cache cleanup: {e}")

                # Cleanup RAG engine avec timeout
                rag_engine = all_services.get("rag_engine_enhanced")
                if rag_engine and hasattr(rag_engine, "cleanup"):
                    try:
                        await asyncio.wait_for(rag_engine.cleanup(), timeout=5.0)
                        logger.info("[OK] RAG Engine nettoyé")
                    except Exception as e:
                        cleanup_errors.append(f"RAG cleanup: {e}")

                # Cleanup agent RAG
                agent_rag = all_services.get("agent_rag_engine")
                if agent_rag and hasattr(agent_rag, "cleanup"):
                    try:
                        await asyncio.wait_for(agent_rag.cleanup(), timeout=3.0)
                        logger.info("[OK] Agent RAG nettoyé")
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

        logger.info("[OK] Application arrêtée proprement")


# ============================================================================
# CRÉATION DE L'APPLICATION - VERSION FINALE SIMPLIFIÉE
# ============================================================================

# MESSAGE DEBUG CRÉATION APP
logger.info(" CRÉATION FASTAPI APP - VERSION FINALE ")

# Créer l'application FastAPI
app = FastAPI(
    title="Intelia Expert Backend",
    description="API RAG Enhanced avec LangSmith et RRF Intelligent - Architecture Centralisée",
    version="4.0.4-translation-service-fixed",
    lifespan=lifespan,
)

logger.info("[OK] FASTAPI APP CRÉÉE AVEC ARCHITECTURE CENTRALISÉE [OK]")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting middleware (10 requêtes/minute/utilisateur)
logger.info("Initialisation du rate limiting...")
try:
    from api.middleware.rate_limiter import RateLimiter

    # Essayer de récupérer le client Redis si disponible
    redis_client = None
    try:
        from cache.cache_core import RedisCacheCore

        cache = RedisCacheCore()
        if hasattr(cache, "client") and cache.client:
            redis_client = cache.client
            logger.info("[OK] Rate limiting avec Redis activé")
        else:
            logger.info("Warning: Rate limiting en mémoire (Redis indisponible)")
    except Exception as redis_err:
        logger.warning(f"Warning: Redis non disponible pour rate limiting: {redis_err}")
        logger.info("Warning: Rate limiting en mémoire activé (fallback)")

    app.add_middleware(RateLimiter, redis_client=redis_client)
    logger.info("[OK] Rate limiting middleware activé (10 req/min/user)")
except Exception as e:
    logger.error(f"[ERROR] Erreur lors de l'activation du rate limiting: {e}")
    logger.warning("Warning: Application démarrée sans rate limiting")

# ARCHITECTURE FINALE: Router initial vide, sera mis à jour dans lifespan
initial_router = create_router({})  # Router vide au démarrage
app.include_router(initial_router)

logger.info(" ROUTER INITIAL AJOUTÉ - TOUS ENDPOINTS DANS LE ROUTER ")

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.critical(" DÉMARRAGE SERVEUR VERSION FINALE SUR %s:%s", host, port)
    logger.info(f" Démarrage serveur sur {host}:{port}")
    logger.info(" Architecture modulaire centralisée activée")
    logger.info(" Mode dégradé supporté pour cache/Redis")
    logger.info(" Injection des services corrigée")
    logger.info(" Service de traduction initialisé au démarrage")
    logger.info(" VERSION FINALE: 4.0.4-translation-service-fixed ")

    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
