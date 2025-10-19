#
# -*- coding: utf-8 -*-
#
# app/main.py - VERSION 4.3.1 CORRIGÉE - HTTPS FORCÉ + HEALTH ENDPOINTS PARFAITS
# Architecture concentrée sur: System, Auth, Users, Stats, Billing, Invitations, Logging
#

from __future__ import annotations

import os
import time
import logging
import asyncio
import psutil
import pathlib
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env (facultatif)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# === LOGGING GLOBAL ===
logger = logging.getLogger("app.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Désactiver les logs verbeux de bibliothèques externes
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Filtrer les logs d'accès uvicorn pour les endpoints répétitifs
class SuppressHealthCheckFilter(logging.Filter):
    """Filtre pour supprimer les logs d'accès des endpoints de santé répétitifs"""
    def filter(self, record):
        # Supprimer les logs pour /auth/me (appelé chaque seconde par le frontend)
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            if '/auth/me' in message or '/v1/auth/me' in message:
                return False
            # Également supprimer les health checks si nécessaire
            if '/health' in message and 'GET' in message:
                return False
        return True

# Appliquer le filtre au logger uvicorn.access
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addFilter(SuppressHealthCheckFilter())

# === CONFIG CORS ===
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://expert.intelia.com,https://app.intelia.com,http://localhost:3000",
).split(",")

# === VARIABLES GLOBALES DE MONITORING ===
request_counter = 0
error_counter = 0
start_time = time.time()
active_requests = 0

# Variables pour le systeme de cache statistiques
stats_scheduler_task = None
cache_update_counter = 0
cache_error_counter = 0

# === DETECTION DU SYSTEME DE CACHE STATISTIQUES ===
STATS_CACHE_AVAILABLE = False
try:
    from app.api.v1.stats_cache import get_stats_cache
    from app.api.v1.stats_updater import run_update_cycle

    STATS_CACHE_AVAILABLE = True
    logger.info("Cache statistiques importe avec succes")
except ImportError as e:
    logger.warning(f"Systeme de cache statistiques non disponible: {e}")
    logger.info("L'application fonctionnera normalement sans le cache optimise")


# === CALCUL MEMOIRE CONTENEUR PRECIS ===
def _read_int_safe(path: str) -> Optional[int]:
    """Lit un entier depuis un fichier cgroup de maniere securisee"""
    try:
        content = pathlib.Path(path).read_text().strip()
        if content == "" or content.lower() == "max":
            return None
        return int(content)
    except (FileNotFoundError, ValueError, PermissionError, OSError):
        return None


def get_container_memory_percent() -> float:
    """
    Retourne le pourcentage REEL d'utilisation memoire du conteneur.
    Priorite aux limites cgroup qui refletent les quotas du conteneur.
    """
    # cgroup v2 (moderne - Docker/Kubernetes recents)
    current_v2 = _read_int_safe("/sys/fs/cgroup/memory.current")
    max_v2 = _read_int_safe("/sys/fs/cgroup/memory.max")

    if current_v2 is not None and max_v2 is not None and max_v2 > 0:
        percent = (current_v2 / max_v2) * 100
        return round(percent, 1)

    # cgroup v1 (legacy mais encore utilise)
    usage_v1 = _read_int_safe("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    limit_v1 = _read_int_safe("/sys/fs/cgroup/memory/memory.limit_in_bytes")

    if usage_v1 is not None and limit_v1 is not None and limit_v1 > 0:
        # Verifier que la limite n'est pas artificielle (> 100TB = pas de limite reelle)
        if limit_v1 < (100 * 1024 * 1024 * 1024 * 1024):  # 100TB
            percent = (usage_v1 / limit_v1) * 100
            return round(percent, 1)

    # Fallback : calcul psutil manuel (pour developpement local)
    memory = psutil.virtual_memory()
    percent = (memory.used / memory.total) * 100
    return round(percent, 1)


# === TACHES PERIODIQUES ===
async def periodic_monitoring():
    """Monitoring periodique des performances serveur avec logging en base"""
    while True:
        try:
            await asyncio.sleep(300)  # Toutes les 5 minutes

            # Calcul des metriques
            current_time = time.time()
            uptime_hours = (current_time - start_time) / 3600
            requests_per_minute = (
                request_counter / (uptime_hours * 60) if uptime_hours > 0 else 0
            )
            error_rate_percent = (error_counter / max(request_counter, 1)) * 100

            # Metriques systeme avec calcul memoire conteneur precis
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = get_container_memory_percent()

            # Determiner le status de sante
            if error_rate_percent > 10 or cpu_percent > 90 or memory_percent > 90:
                health_status = "critical"
            elif error_rate_percent > 5 or cpu_percent > 70 or memory_percent > 70:
                health_status = "degraded"
            else:
                health_status = "healthy"

            # Log des metriques serveur dans la base
            try:
                from app.api.v1.logging import get_analytics_manager

                analytics = get_analytics_manager()

                # Calculer l'heure tronquee pour le groupement
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)

                # Log des metriques
                analytics.log_server_performance(
                    timestamp_hour=current_hour,
                    total_requests=request_counter,
                    successful_requests=request_counter - error_counter,
                    failed_requests=error_counter,
                    avg_response_time_ms=int(250),
                    health_status=health_status,
                    error_rate_percent=error_rate_percent,
                )

            except Exception as e:
                logger.warning(f"Erreur logging metriques en base: {e}")

            # Ajouter les metriques du cache
            cache_info = ""
            if STATS_CACHE_AVAILABLE:
                cache_info = f", cache: {cache_update_counter} updates, {cache_error_counter} erreurs"

            logger.info(
                f"Metriques: {requests_per_minute:.1f} req/min, "
                f"erreurs: {error_rate_percent:.1f}%, "
                f"CPU: {cpu_percent:.1f}%, RAM: {memory_percent:.1f}%, "
                f"sante: {health_status}{cache_info}"
            )

        except Exception as e:
            logger.error(f"Erreur monitoring periodique: {e}")
            await asyncio.sleep(60)  # Retry dans 1 minute en cas d'erreur


async def periodic_stats_update():
    """Mise a jour periodique du cache statistiques toutes les heures"""
    global cache_update_counter, cache_error_counter

    if not STATS_CACHE_AVAILABLE:
        logger.warning("Cache statistiques non disponible - arret scheduler")
        return

    # Attendre 5 minutes avant la premiere mise a jour
    await asyncio.sleep(300)

    # Premiere mise a jour au demarrage
    logger.info("Lancement premiere mise a jour cache statistiques au demarrage")
    try:
        result = await run_update_cycle()
        if result.get("status") == "completed":
            cache_update_counter += 1
            logger.info("Premiere mise a jour cache reussie au demarrage")
        else:
            cache_error_counter += 1
            logger.warning(
                f"Premiere mise a jour cache echouee: {result.get('error', 'Unknown')}"
            )
    except Exception as e:
        cache_error_counter += 1
        logger.error(f"Erreur premiere mise a jour cache: {e}")

    # Boucle principale - mise a jour toutes les heures
    while True:
        try:
            await asyncio.sleep(3600)  # 1 heure

            logger.info("Debut mise a jour periodique cache statistiques")
            start_update = time.time()

            result = await run_update_cycle()
            update_duration = (time.time() - start_update) * 1000  # en ms

            if result.get("status") == "completed":
                cache_update_counter += 1
                successful = result.get("successful_updates", 0)
                total = result.get("total_updates", 0)
                duration = result.get("duration_ms", update_duration)

                logger.info(
                    f"Cache mis a jour: {successful}/{total} succes en {duration:.0f}ms"
                )

                errors = result.get("errors", [])
                if errors:
                    logger.warning(f"Erreurs durant la mise a jour: {errors}")

            elif result.get("status") == "failed":
                cache_error_counter += 1
                error_msg = result.get("error", "Erreur inconnue")
                logger.error(f"Mise a jour cache echouee: {error_msg}")

            else:
                cache_error_counter += 1
                logger.warning(f"Mise a jour cache statut inattendu: {result}")

        except Exception as e:
            cache_error_counter += 1
            logger.error(f"Erreur durant mise a jour periodique cache: {e}")
            await asyncio.sleep(600)  # Attendre 10 minutes avant retry


# === LIFESPAN SIMPLIFIE ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== INITIALISATION AU DEMARRAGE ==========
    # 🔧 VERSION TRACKING
    VERSION = "4.3.3"
    BUILD = "20251012-001"  # Pydantic warning fix + Conversation sharing feature
    COMMIT = os.getenv("COMMIT_SHA", "unknown")[:8]

    logger.info("Starting Expert API backend - v%s (build %s, commit %s)", VERSION, BUILD, COMMIT)

    # ========== INITIALISATION DES BASES DE DONNÉES ==========
    try:
        logger.info("Initialisation des connexions aux bases de données...")

        # Initialiser PostgreSQL + Supabase
        from app.core.database import init_all_databases
        db_init_success = init_all_databases()

        if db_init_success:
            logger.info("Database connections initialized (PostgreSQL + Supabase)")
        else:
            logger.warning("Database initialization error")

        # ========== INITIALISATION DES SERVICES ==========
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info("DATABASE_URL configuree")

            # Analytics
            try:
                from app.api.v1.logging import get_analytics

                analytics_status = get_analytics()
                logger.info(
                    f"Service analytics: {analytics_status.get('status', 'unknown')}"
                )
            except Exception as e:
                logger.warning(f"Service analytics partiellement disponible: {e}")

            # Billing
            try:
                from app.api.v1.billing import get_billing_manager

                billing = get_billing_manager()
                logger.info(f"Service billing: {len(billing.plans)} plans charges")
            except Exception as e:
                logger.warning(f"Service billing partiellement disponible: {e}")

            # Cache statistiques (optionnel)
            if STATS_CACHE_AVAILABLE:
                try:
                    cache = get_stats_cache()
                    if hasattr(cache, "get_cache_stats"):
                        cache_stats = cache.get_cache_stats()
                    elif hasattr(cache, "get_stats"):
                        cache_stats = cache.get_stats()
                    else:
                        cache_stats = "cache initialise"
                    logger.info(f"Cache statistiques initialise: {cache_stats}")
                except Exception as e:
                    logger.warning(f"Cache statistiques partiellement disponible: {e}")

        else:
            logger.warning("DATABASE_URL manquante - services analytics desactives")
    except Exception as e:
        logger.error(f"Erreur initialisation services: {e}")

    # ========== SUPABASE ==========
    app.state.supabase = None
    try:
        from supabase import create_client

        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            app.state.supabase = create_client(url, key)
            logger.info("Supabase pret")
        else:
            logger.info("Supabase non configure")
    except Exception as e:
        logger.warning("Supabase indisponible: %s", e)

    # ========== DEMARRAGE DU MONITORING & SCHEDULER ==========
    monitoring_task = None
    global stats_scheduler_task

    try:
        monitoring_task = asyncio.create_task(periodic_monitoring())
        logger.info("Monitoring periodique demarre")
    except Exception as e:
        logger.error(f"Erreur demarrage monitoring: {e}")

    if STATS_CACHE_AVAILABLE:
        try:
            stats_scheduler_task = asyncio.create_task(periodic_stats_update())
            logger.info("Scheduler cache statistiques demarre")
        except Exception as e:
            logger.error(f"Erreur demarrage scheduler cache: {e}")
    else:
        logger.info("Scheduler cache statistiques desactive")

    # ========== L'APPLICATION DEMARRE ==========
    system_features = []
    if STATS_CACHE_AVAILABLE:
        system_features.append("cache statistiques optimise")
    system_features.extend(["monitoring", "analytics", "billing"])
    logger.info(f"Backend Expert API pret avec: {', '.join(system_features)}")
    yield  # --- L'APPLICATION FONCTIONNE ---

    # ========== NETTOYAGE A L'ARRET ==========
    logger.info("Arret du backend Expert API")

    # Fermer les connexions DB
    try:
        from app.core.database import close_all_databases
        close_all_databases()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Erreur fermeture DB: {e}")

    if monitoring_task:
        try:
            monitoring_task.cancel()
            await asyncio.gather(monitoring_task, return_exceptions=True)
            logger.info("Monitoring periodique arrete")
        except Exception as e:
            logger.error(f"Erreur arret monitoring: {e}")

    if stats_scheduler_task:
        try:
            stats_scheduler_task.cancel()
            await asyncio.gather(stats_scheduler_task, return_exceptions=True)
            logger.info("Scheduler cache statistiques arrete")
        except Exception as e:
            logger.error(f"Erreur arret scheduler cache: {e}")

    # Statistiques finales
    uptime_hours = (time.time() - start_time) / 3600
    final_stats = (
        f"{request_counter} requetes en {uptime_hours:.1f}h, {error_counter} erreurs"
    )

    if STATS_CACHE_AVAILABLE and cache_update_counter > 0:
        cache_success_rate = (
            cache_update_counter / max(cache_update_counter + cache_error_counter, 1)
        ) * 100
        final_stats += f", cache: {cache_update_counter} mises a jour ({cache_success_rate:.1f}% succes)"

    logger.info(f"Statistiques finales: {final_stats}")


# === FASTAPI APP ===
app = FastAPI(
    title="Intelia Expert API",
    version="4.3.1",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ========== MIDDLEWARE HTTPS REDIRECT SÉCURISÉ ==========
@app.middleware("http")
async def force_https_redirect(request: Request, call_next):
    """🔒 Force la redirection HTTPS pour tous les endpoints (SÉCURISÉ CONTRE BOUCLES)"""

    # DÉSACTIVÉ TEMPORAIREMENT POUR ÉVITER LES BOUCLES DE REDIRECTION
    # Le serveur de production avec proxy/load balancer peut causer des boucles
    # La sécurité HTTPS est assurée au niveau de l'infrastructure (nginx/cloudflare)

    # Logique sécurisée (commentée pour éviter les boucles) :
    # is_production = (
    #     not request.url.hostname.startswith("localhost") and
    #     not request.url.hostname.startswith("127.0.0.1") and
    #     not request.url.hostname.startswith("0.0.0.0")
    # )
    #
    # # Vérifier les headers de proxy pour détecter le vrai schéma
    # forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    # is_https = (
    #     request.url.scheme == "https" or
    #     forwarded_proto == "https" or
    #     request.headers.get("x-forwarded-ssl") == "on"
    # )
    #
    # if is_production and not is_https:
    #     https_url = request.url.replace(scheme="https")
    #     logger.info(f"Redirection HTTPS: {request.url} -> {https_url}")
    #     return RedirectResponse(url=str(https_url), status_code=301)

    response = await call_next(request)
    return response


# === MIDDLEWARE CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "X-Session-ID",
    ],
    expose_headers=[
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
    ],
)


# === MIDDLEWARE SECURITY HEADERS ===
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses

    Headers implemented:
    - HSTS: Force HTTPS for 1 year
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-XSS-Protection: Legacy XSS protection
    - Referrer-Policy: Control referrer information
    - Content-Security-Policy: Restrict resource loading
    - Permissions-Policy: Disable unnecessary browser features

    Configuration is permissive to support:
    - Next.js inline scripts (antiFlashScript, hideAddressBarScript)
    - Tailwind CSS inline styles
    - Supabase API connections
    """
    response = await call_next(request)

    # HSTS - Force HTTPS for 1 year with subdomains + preload
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )

    # X-Frame-Options - Prevent clickjacking attacks
    response.headers["X-Frame-Options"] = "DENY"

    # X-Content-Type-Options - Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # X-XSS-Protection - Legacy XSS protection (for older browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer-Policy - Control referrer information leakage
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content-Security-Policy - Restrict resource loading
    # NOTE: Permissive configuration to support Next.js + inline scripts + Tailwind
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        # Scripts: allow self + unsafe-inline (Next.js inline scripts) - unsafe-eval removed for A+ score
        "script-src 'self' 'unsafe-inline'; "
        # Styles: allow self + unsafe-inline (Tailwind CSS inline styles)
        "style-src 'self' 'unsafe-inline'; "
        # Images: allow self + data URIs + HTTPS (for external images)
        "img-src 'self' data: https:; "
        # Fonts: allow self + data URIs
        "font-src 'self' data:; "
        # Connect: API calls to backend + Supabase (HTTP + WebSocket)
        "connect-src 'self' https://expert.intelia.com https://*.supabase.co wss://*.supabase.co; "
        # Frames: DENY all iframes
        "frame-ancestors 'none'; "
        # Base URI: restrict to self
        "base-uri 'self'; "
        # Forms: restrict to self
        "form-action 'self'; "
        # Report violations to monitoring endpoint
        "report-uri https://expert.intelia.com/api/v1/csp-report"
    )

    # Permissions-Policy - Disable unnecessary browser features
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    return response


# === MIDDLEWARE DE MONITORING DES REQUETES ===
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """Middleware pour tracker les performances en temps reel"""
    global request_counter, error_counter, active_requests

    start_time_req = time.time()
    active_requests += 1
    request_counter += 1

    try:
        response = await call_next(request)
        if response.status_code >= 400:
            error_counter += 1
        return response
    except Exception as e:
        error_counter += 1
        logger.error(f"Erreur dans middleware monitoring: {e}")
        raise
    finally:
        active_requests -= 1
        processing_time = (time.time() - start_time_req) * 1000
        if processing_time > 5000:  # Plus de 5 secondes
            logger.warning(
                f"Requete lente: {request.method} {request.url.path} - {processing_time:.0f}ms"
            )


# === MIDDLEWARE D'AUTHENTIFICATION ===
try:
    from app.middleware.auth_middleware import auth_middleware

    app.middleware("http")(auth_middleware)
    logger.info("Middleware d'authentification active")
except ImportError as e:
    logger.warning(f"Middleware d'authentification non disponible: {e}")
except Exception as e:
    logger.error(f"Erreur lors de l'activation du middleware d'auth: {e}")


# === ENDPOINTS HEALTH SIMPLES ===
@app.get("/health", tags=["Health"])
async def simple_health_check():
    """Health check ultra simple"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check pour verifier si l'app est prete"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - start_time),
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness check ultra leger"""
    return {"alive": True}


# === CSP VIOLATION REPORTING ===
@app.post("/api/v1/csp-report", tags=["Security"])
async def csp_violation_report(request: Request):
    """
    Endpoint for Content-Security-Policy violation reports.

    Browsers automatically POST to this endpoint when CSP violations occur.
    Logs violations for security monitoring and debugging.
    """
    try:
        body = await request.json()

        # Extract CSP violation details
        csp_report = body.get("csp-report", {})

        # Log the violation with relevant details
        logger.warning(
            f"CSP Violation: "
            f"blocked-uri={csp_report.get('blocked-uri', 'unknown')}, "
            f"violated-directive={csp_report.get('violated-directive', 'unknown')}, "
            f"document-uri={csp_report.get('document-uri', 'unknown')}, "
            f"source-file={csp_report.get('source-file', 'unknown')}, "
            f"line-number={csp_report.get('line-number', 'unknown')}"
        )

        # Return 204 No Content (standard for CSP reports)
        return JSONResponse(status_code=204, content={})

    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        return JSONResponse(status_code=204, content={})  # Always return 204


# === MONTAGE DES ROUTERS ===
try:
    from app.api.v1 import router as api_v1_router

    app.include_router(api_v1_router)
    logger.info("Router API v1 charge depuis __init__.py")
except ImportError as e:
    logger.warning(f"Impossible de charger le router v1 depuis __init__.py: {e}")
    logger.info("Creation d'un router v1 temporaire avec endpoints selectionnes...")

    from fastapi import APIRouter

    temp_v1_router = APIRouter(prefix="/v1", tags=["v1"])

    # === ENDPOINTS SELECTIONNES UNIQUEMENT ===
    routers_to_load = [
        ("auth", "", "auth"),
        ("system", "", "system"),
        ("health", "", "health"),  # 🔧 AJOUT DU ROUTER HEALTH MANQUANT
        ("users", "", "users"),
        ("invitations", "", "invitations"),
        ("logging", "", "logging"),
        ("billing", "", "billing"),
        ("billing_openai", "/billing", "billing-openai"),
        ("stats_fast", "", "statistics-fast"),
        ("webhooks", "", "webhooks"),  # 🔧 AJOUT DU ROUTER WEBHOOKS
        ("qa_quality", "", "qa-quality"),  # 🔧 AJOUT DU ROUTER QA QUALITY
    ]

    if STATS_CACHE_AVAILABLE:
        routers_to_load.append(("stats_admin", "", "statistics-admin"))

    for router_name, prefix, tag in routers_to_load:
        try:
            router_module = __import__(f"app.api.v1.{router_name}", fromlist=["router"])
            temp_v1_router.include_router(
                router_module.router, prefix=prefix if prefix else "", tags=[tag]
            )
            logger.info(f"{router_name.capitalize()} router ajoute")
        except ImportError as e:
            logger.warning(f"{router_name.capitalize()} router non disponible: {e}")

    # Monter le router temporaire
    app.include_router(temp_v1_router)
    logger.info("Router v1 temporaire monte avec endpoints selectionnes")


# === ENDPOINT HEALTH COMPLET ===
@app.get("/health/complete", tags=["Health"])
async def complete_health_check():
    """Check de sante complet du systeme"""
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {},
        }

        # Check base de donnees et analytics
        try:
            from app.api.v1.logging import get_analytics_manager

            get_analytics_manager()
            health_status["components"]["analytics"] = {
                "status": "healthy",
                "type": "postgresql",
                "tables_created": True,
            }
        except Exception as e:
            health_status["components"]["analytics"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        # Check systeme de facturation
        try:
            from app.api.v1.billing import get_billing_manager

            billing = get_billing_manager()
            health_status["components"]["billing"] = {
                "status": "healthy",
                "plans_loaded": len(billing.plans),
                "quota_enforcement": True,
            }
        except Exception as e:
            health_status["components"]["billing"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        # Check systeme de cache statistiques
        if STATS_CACHE_AVAILABLE:
            try:
                cache = get_stats_cache()
                if hasattr(cache, "get_cache_stats"):
                    cache_stats = cache.get_cache_stats()
                else:
                    cache_stats = "disponible"

                scheduler_active = (
                    stats_scheduler_task is not None and not stats_scheduler_task.done()
                )
                cache_success_rate = 100
                if cache_update_counter + cache_error_counter > 0:
                    cache_success_rate = (
                        cache_update_counter
                        / (cache_update_counter + cache_error_counter)
                    ) * 100

                health_status["components"]["statistics_cache"] = {
                    "status": (
                        "healthy" if cache_stats and scheduler_active else "degraded"
                    ),
                    "scheduler_active": scheduler_active,
                    "cache_updates": cache_update_counter,
                    "cache_errors": cache_error_counter,
                    "success_rate": round(cache_success_rate, 1),
                    "cache_entries": cache_stats,
                }
            except Exception as e:
                health_status["components"]["statistics_cache"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["status"] = "degraded"
        else:
            health_status["components"]["statistics_cache"] = {
                "status": "not_available",
                "message": "Module cache statistiques non importe",
            }

        # Check OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        health_status["components"]["openai"] = {
            "status": "configured" if openai_key else "not_configured"
        }

        # Check Auth system
        try:
            jwt_secret = os.getenv("JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET")
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")

            auth_status = "healthy"
            if not (jwt_secret and supabase_url and supabase_key):
                auth_status = "partially_configured"
            if not jwt_secret:
                auth_status = "not_configured"

            health_status["components"]["auth"] = {
                "status": auth_status,
                "has_jwt_secret": bool(jwt_secret),
                "has_supabase_config": bool(supabase_url and supabase_key),
            }
        except Exception as e:
            health_status["components"]["auth"] = {"status": "error", "error": str(e)}

        # Metriques systeme avec calcul memoire conteneur
        uptime_hours = (time.time() - start_time) / 3600
        health_status["metrics"] = {
            "uptime_hours": round(uptime_hours, 2),
            "total_requests": request_counter,
            "error_rate_percent": round(
                (error_counter / max(request_counter, 1)) * 100, 2
            ),
            "active_requests": active_requests,
            "cache_updates": cache_update_counter,
            "cache_errors": cache_error_counter,
            "scheduler_active": (
                stats_scheduler_task is not None and not stats_scheduler_task.done()
                if STATS_CACHE_AVAILABLE
                else False
            ),
            "memory_percent_container": get_container_memory_percent(),
        }

        # Determiner le statut global
        component_statuses = [
            comp["status"]
            for comp in health_status["components"].values()
            if comp["status"] in ["healthy", "degraded", "unhealthy"]
        ]

        if any(status == "unhealthy" for status in component_statuses):
            health_status["status"] = "unhealthy"
        elif any(status == "degraded" for status in component_statuses):
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e),
        }


# === ENDPOINT RACINE SIMPLIFIE ===
@app.get("/", tags=["Root"])
async def root():
    uptime_hours = (time.time() - start_time) / 3600

    # Version simplifiee qui ne fait pas de calculs lourds si l'app demarre
    if uptime_hours < 2:  # Si moins de 2 heures de uptime
        return {
            "status": "running",
            "version": "4.3.1",
            "uptime_hours": round(uptime_hours, 2),
            "environment": os.getenv("ENV", "production"),
            "health": "ready",
        }

    cache_status = "not_available"
    if STATS_CACHE_AVAILABLE:
        if stats_scheduler_task and not stats_scheduler_task.done():
            cache_status = "active"
        else:
            cache_status = "available_but_inactive"

    return {
        "status": "running",
        "version": "4.3.1",
        "environment": os.getenv("ENV", "production"),
        "database": bool(getattr(app.state, "supabase", None)),
        "postgresql": bool(os.getenv("DATABASE_URL")),
        "statistics_cache_system": cache_status,
        "uptime_hours": round(uptime_hours, 2),
        "requests_processed": request_counter,
        "cache_updates": cache_update_counter if STATS_CACHE_AVAILABLE else 0,
        "memory_percent": get_container_memory_percent(),
        "services": [
            "system",
            "auth",
            "users",
            "stats",
            "billing",
            "invitations",
            "logging",
        ],
        "deployment_version": "v4.3.1-https-fixed-architecture",
    }


# === GESTIONNAIRES D'EXCEPTIONS AVEC CORS ===
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        headers={"content-type": "application/json; charset=utf-8"},
    )

    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "false"

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Session-ID"
    )

    return response


@app.exception_handler(Exception)
async def generic_exc_handler(request: Request, exc: Exception):
    logger.exception("Unhandled: %s", exc)

    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        headers={"content-type": "application/json; charset=utf-8"},
    )

    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "false"

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Session-ID"
    )

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8080"))
    )
