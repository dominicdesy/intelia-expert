# -*- coding: utf-8 -*-
# app/main.py - VERSION 4.2

from __future__ import annotations

import os
import time
import json
import logging
import asyncio
import psutil
import pathlib
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict

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

# === CONFIG CORS ===
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://expert.intelia.com,https://app.intelia.com,http://localhost:3000",
).split(",")

# ACTIVATION SYNTHESE LLM AU DEMARRAGE (CONSERVE)
synthesis_enabled = str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() in (
    "1", "true", "yes", "on",
)
if synthesis_enabled:
    logger.info("✅ Synthese LLM activee (ENABLE_SYNTH_PROMPT=1)")
else:
    logger.info("ℹ️ Synthese LLM desactivee (ENABLE_SYNTH_PROMPT=0)")

# ========== VARIABLES GLOBALES DE MONITORING ==========
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
    logger.info("✅ Systeme de cache statistiques importe avec succes")
except ImportError as e:
    logger.warning(f"⚠️ Systeme de cache statistiques non disponible: {e}")
    logger.info("ℹ️ L'application fonctionnera normalement sans le cache optimise")


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
                logger.warning(f"⚠️ Erreur logging metriques en base: {e}")

            # Ajouter les metriques du cache
            cache_info = ""
            if STATS_CACHE_AVAILABLE:
                cache_info = f", cache: {cache_update_counter} updates, {cache_error_counter} erreurs"

            logger.info(
                f"📊 Metriques: {requests_per_minute:.1f} req/min, "
                f"erreurs: {error_rate_percent:.1f}%, "
                f"CPU: {cpu_percent:.1f}%, RAM: {memory_percent:.1f}%, "
                f"sante: {health_status}{cache_info}"
            )

        except Exception as e:
            logger.error(f"⏰ Erreur monitoring periodique: {e}")
            await asyncio.sleep(60)  # Retry dans 1 minute en cas d'erreur


async def periodic_stats_update():
    """Mise a jour periodique du cache statistiques toutes les heures"""
    global cache_update_counter, cache_error_counter

    if not STATS_CACHE_AVAILABLE:
        logger.warning("⚠️ Cache statistiques non disponible - arret scheduler")
        return

    # Attendre 5 minutes avant la premiere mise a jour
    await asyncio.sleep(300)

    # Premiere mise a jour au demarrage
    logger.info("🚀 Lancement premiere mise a jour cache statistiques au demarrage")
    try:
        result = await run_update_cycle()
        if result.get("status") == "completed":
            cache_update_counter += 1
            logger.info("✅ Premiere mise a jour cache reussie au demarrage")
        else:
            cache_error_counter += 1
            logger.warning(
                f"⚠️ Premiere mise a jour cache echouee: {result.get('error', 'Unknown')}"
            )
    except Exception as e:
        cache_error_counter += 1
        logger.error(f"⚰ Erreur premiere mise a jour cache: {e}")

    # Boucle principale - mise a jour toutes les heures
    while True:
        try:
            await asyncio.sleep(3600)  # 1 heure

            logger.info("🔄 Debut mise a jour periodique cache statistiques")
            start_update = time.time()

            result = await run_update_cycle()
            update_duration = (time.time() - start_update) * 1000  # en ms

            if result.get("status") == "completed":
                cache_update_counter += 1
                successful = result.get("successful_updates", 0)
                total = result.get("total_updates", 0)
                duration = result.get("duration_ms", update_duration)

                logger.info(
                    f"✅ Cache mis a jour: {successful}/{total} succes en {duration:.0f}ms"
                )

                errors = result.get("errors", [])
                if errors:
                    logger.warning(f"⚠️ Erreurs durant la mise a jour: {errors}")

            elif result.get("status") == "failed":
                cache_error_counter += 1
                error_msg = result.get("error", "Erreur inconnue")
                logger.error(f"⚰ Mise a jour cache echouee: {error_msg}")

            else:
                cache_error_counter += 1
                logger.warning(f"⚠️ Mise a jour cache statut inattendu: {result}")

        except Exception as e:
            cache_error_counter += 1
            logger.error(f"⚰ Erreur durant mise a jour periodique cache: {e}")
            await asyncio.sleep(600)  # Attendre 10 minutes avant retry


# === LIFESPAN RAPIDE SANS RAG ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== INITIALISATION AU DEMARRAGE ==========
    logger.info("🚀 Demarrage backend Expert API - RAG externalisé")

    # ========== INITIALISATION DES SERVICES ==========
    try:
        logger.info("📊 Initialisation des services analytics et facturation...")
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info("✅ DATABASE_URL configuree")

            # Analytics
            try:
                from app.api.v1.logging import get_analytics
                analytics_status = get_analytics()
                logger.info(f"✅ Service analytics: {analytics_status.get('status', 'unknown')}")
            except Exception as e:
                logger.warning(f"⚠️ Service analytics partiellement disponible: {e}")

            # Billing
            try:
                from app.api.v1.billing import get_billing_manager
                billing = get_billing_manager()
                logger.info(f"✅ Service billing: {len(billing.plans)} plans charges")
            except Exception as e:
                logger.warning(f"⚠️ Service billing partiellement disponible: {e}")

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
                    logger.info(f"✅ Cache statistiques initialise: {cache_stats}")
                except Exception as e:
                    logger.warning(f"⚠️ Cache statistiques partiellement disponible: {e}")

            # Nettoyage sessions
            try:
                from app.api.v1.pipeline.postgres_memory import PostgresMemory
                memory = PostgresMemory()
                cleaned = memory.cleanup_old_sessions(days_old=7)
                if cleaned > 0:
                    logger.info(f"🧹 {cleaned} anciennes sessions nettoyees")
            except Exception as e:
                logger.warning(f"⚠️ Nettoyage sessions echoue: {e}")
        else:
            logger.warning("⚠️ DATABASE_URL manquante - services analytics desactives")
    except Exception as e:
        logger.error(f"💀 Erreur initialisation services: {e}")

    # ========== SUPABASE ==========
    app.state.supabase = None
    try:
        from supabase import create_client
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            app.state.supabase = create_client(url, key)
            logger.info("✅ Supabase pret")
        else:
            logger.info("ℹ️ Supabase non configure")
    except Exception as e:
        logger.warning("ℹ️ Supabase indisponible: %s", e)

    # ========== RAG EXTERNALISÉ ==========
    app.state.rag = None
    app.state.rag_broiler = None  
    app.state.rag_layer = None
    logger.info("ℹ️ RAG externalisé vers expert.intelia.com/llm - aucun chargement local")

    # ========== DEMARRAGE DU MONITORING & SCHEDULER ==========
    monitoring_task = None
    global stats_scheduler_task

    try:
        monitoring_task = asyncio.create_task(periodic_monitoring())
        logger.info("📊 Monitoring periodique demarre")
    except Exception as e:
        logger.error(f"💀 Erreur demarrage monitoring: {e}")

    if STATS_CACHE_AVAILABLE:
        try:
            stats_scheduler_task = asyncio.create_task(periodic_stats_update())
            logger.info("🔄 Scheduler cache statistiques demarre")
        except Exception as e:
            logger.error(f"⚰ Erreur demarrage scheduler cache: {e}")
    else:
        logger.info("ℹ️ Scheduler cache statistiques desactive")

    # ========== L'APPLICATION DEMARRE ==========
    system_features = []
    if STATS_CACHE_AVAILABLE:
        system_features.append("cache statistiques optimise")
    system_features.extend(["RAG externe", "monitoring", "analytics", "billing"])
    logger.info(f"🎯 Backend Expert API pret avec: {', '.join(system_features)}")
    yield  # --- L'APPLICATION FONCTIONNE ---

    # ========== NETTOYAGE A L'ARRET ==========
    logger.info("🛑 Arret du backend Expert API")

    if monitoring_task:
        try:
            monitoring_task.cancel()
            await asyncio.gather(monitoring_task, return_exceptions=True)
            logger.info("📊 Monitoring periodique arrete")
        except Exception as e:
            logger.error(f"💀 Erreur arret monitoring: {e}")

    if stats_scheduler_task:
        try:
            stats_scheduler_task.cancel()
            await asyncio.gather(stats_scheduler_task, return_exceptions=True)
            logger.info("🔄 Scheduler cache statistiques arrete")
        except Exception as e:
            logger.error(f"⚰ Erreur arret scheduler cache: {e}")

    # Statistiques finales
    uptime_hours = (time.time() - start_time) / 3600
    final_stats = f"{request_counter} requetes en {uptime_hours:.1f}h, {error_counter} erreurs"

    if STATS_CACHE_AVAILABLE and cache_update_counter > 0:
        cache_success_rate = (cache_update_counter / max(cache_update_counter + cache_error_counter, 1)) * 100
        final_stats += f", cache: {cache_update_counter} mises a jour ({cache_success_rate:.1f}% succes)"

    logger.info(f"📈 Statistiques finales: {final_stats}")


# === FASTAPI APP ===
app = FastAPI(
    title="Intelia Expert API",
    version="4.2.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

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
        logger.error(f"💀 Erreur dans middleware monitoring: {e}")
        raise
    finally:
        active_requests -= 1
        processing_time = (time.time() - start_time_req) * 1000
        if processing_time > 5000:  # Plus de 5 secondes
            logger.warning(f"🌀 Requete lente: {request.method} {request.url.path} - {processing_time:.0f}ms")


# === MIDDLEWARE D'AUTHENTIFICATION ===
try:
    from app.middleware.auth_middleware import auth_middleware
    app.middleware("http")(auth_middleware)
    logger.info("✅ Middleware d'authentification active")
except ImportError as e:
    logger.warning(f"⚠️ Middleware d'authentification non disponible: {e}")
except Exception as e:
    logger.error(f"💀 Erreur lors de l'activation du middleware d'auth: {e}")


# === ENDPOINTS HEALTH SIMPLES POUR DIGITALOCEAN ===
@app.get("/health", tags=["Health"])
async def simple_health_check():
    """Health check ultra simple pour DigitalOcean App Platform"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check pour vérifier si l'app est prête"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - start_time)
    }

@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness check ultra léger"""
    return {"alive": True}


# === ENDPOINTS CHAT DIRECTS (HORS V1) ===
@app.post("/chat/stream", tags=["Chat"])
async def chat_stream_direct(request: Request):
    """Endpoint chat direct - proxy vers service LLM externe avec logging"""
    start_time_req = time.time()
    user_question = ""
    user_email = ""
    session_id = ""

    try:
        import httpx

        # Lire et parser le corps de la requete
        body_bytes = await request.body()

        # Parser le JSON pour transformation et extraction des donnees
        try:
            body_json = json.loads(body_bytes.decode("utf-8"))

            # Extraire les donnees pour le logging
            user_question = body_json.get("message_preview", body_json.get("question", ""))
            session_id = body_json.get("session_id", "")

            # Extraire user_email depuis l'auth header si possible
            auth_header = request.headers.get("Authorization")
            if auth_header:
                try:
                    from app.api.v1.auth import get_current_user_from_token
                    user_info = await get_current_user_from_token(auth_header.replace("Bearer ", ""))
                    user_email = user_info.get("email", "")
                except Exception:
                    user_email = "anonymous"

            # Transformation des données pour le service LLM
            if "message_preview" in body_json and "message" not in body_json:
                body_json["message"] = body_json.pop("message_preview")
                logger.info("Transformation: message_preview -> message")

            if "question" in body_json and "message" not in body_json:
                body_json["message"] = body_json.pop("question")
                logger.info("Transformation: question -> message")

            # Reconvertir en bytes
            body_bytes = json.dumps(body_json).encode("utf-8")
            logger.info(f"Question extraite: {user_question[:100]}...")

        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Impossible de parser/transformer le body JSON, envoi tel quel")

        # Headers a transferer
        headers = {
            "Content-Type": "application/json",
            "X-Frontend-Origin": "intelia",
            "User-Agent": "Intelia-Expert-Proxy/1.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        # Transferer tous les headers importants du frontend
        for header_name in ["Authorization", "Cookie", "X-Session-ID", "X-User-ID", "X-Tenant-ID"]:
            header_value = request.headers.get(header_name)
            if header_value:
                headers[header_name] = header_value

        # Transferer l'origine si presente
        origin = request.headers.get("Origin")
        if origin:
            headers["Origin"] = origin
            headers["Referer"] = origin

        # URL du service LLM externe
        target_url = "https://expert.intelia.com/llm/chat/stream"

        # Log pour debug
        logger.info(f"Proxy chat vers {target_url}")

        # Proxy vers le service LLM externe
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(target_url, content=body_bytes, headers=headers, timeout=60.0)

            logger.info(f"Reponse LLM service: {response.status_code}")

            if response.status_code == 200:
                # Collecter la réponse pour le logging
                response_chunks = []

                async def response_collector():
                    async for chunk in response.aiter_text():
                        response_chunks.append(chunk)
                        yield chunk

                # Streamer la réponse en collectant le contenu
                from fastapi.responses import StreamingResponse

                stream_response = StreamingResponse(
                    response_collector(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
                        "Access-Control-Allow-Credentials": "true",
                    },
                )

                # Programmer l'enregistrement en arrière-plan après le streaming
                async def log_interaction_async():
                    try:
                        # Reconstituer la réponse complète
                        full_response = "".join(response_chunks)

                        # Extraire le texte de la réponse depuis les événements SSE
                        extracted_response = ""
                        for line in full_response.split("\n"):
                            if line.startswith("data: "):
                                try:
                                    event_data = json.loads(line[6:])  # Enlever "data: "
                                    if event_data.get("type") == "final":
                                        extracted_response = event_data.get("answer", "")
                                        break
                                    elif event_data.get("type") == "delta":
                                        extracted_response += event_data.get("text", "")
                                except json.JSONDecodeError:
                                    continue

                        # Enregistrer dans la base de données
                        await log_user_question_async(
                            user_email=user_email or "anonymous",
                            question=user_question,
                            response_text=extracted_response,
                            response_source="llm_service",
                            processing_time_ms=int((time.time() - start_time_req) * 1000),
                            session_id=session_id,
                            language=(body_json.get("lang", "fr") if "body_json" in locals() else "fr"),
                        )

                        logger.info(f"Question enregistrée: {user_email} -> {len(user_question)} chars question, {len(extracted_response)} chars response")

                    except Exception as log_error:
                        logger.error(f"Erreur enregistrement question: {log_error}")

                # Lancer l'enregistrement en arrière-plan
                asyncio.create_task(log_interaction_async())

                return stream_response

            else:
                # Enregistrer l'erreur aussi
                processing_time = int((time.time() - start_time_req) * 1000)
                try:
                    error_content = response.text
                    await log_user_question_async(
                        user_email=user_email or "anonymous",
                        question=user_question,
                        response_text=f"Erreur LLM: {response.status_code}",
                        response_source="llm_service_error",
                        processing_time_ms=processing_time,
                        session_id=session_id,
                        status="error",
                    )
                except Exception as log_error:
                    logger.error(f"Erreur enregistrement erreur: {log_error}")

                logger.error(f"LLM service error {response.status_code}: {error_content}")

                return JSONResponse(
                    status_code=response.status_code,
                    content={
                        "detail": f"LLM service error: {response.status_code}",
                        "upstream_error": (response.text if response.text else "No details"),
                    },
                )

    except Exception as e:
        # Enregistrer l'erreur proxy aussi
        processing_time = int((time.time() - start_time_req) * 1000)
        try:
            await log_user_question_async(
                user_email=user_email or "anonymous",
                question=user_question,
                response_text=f"Erreur proxy: {str(e)}",
                response_source="proxy_error",
                processing_time_ms=processing_time,
                session_id=session_id,
                status="error",
            )
        except Exception as log_error:
            logger.error(f"Erreur enregistrement erreur proxy: {log_error}")

        logger.error(f"Erreur proxy chat direct: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Proxy error: {str(e)}"})


# Fonction utilitaire pour l'enregistrement asynchrone
async def log_user_question_async(
    user_email: str,
    question: str,
    response_text: str,
    response_source: str = "llm_service",
    processing_time_ms: int = 0,
    session_id: str = "",
    language: str = "fr",
    status: str = "completed",
):
    """Enregistre une question/réponse de manière asynchrone"""
    try:
        from app.api.v1.logging import get_analytics_manager
        analytics = get_analytics_manager()

        # Utiliser la méthode log_user_question si elle existe
        if hasattr(analytics, "log_user_question"):
            analytics.log_user_question(
                user_email=user_email,
                question=question,
                response_text=response_text,
                response_source=response_source,
                response_confidence=0.8,  # Score par défaut pour LLM
                processing_time_ms=processing_time_ms,
                session_id=session_id,
                language=language,
                status=status,
            )
        else:
            logger.warning("Méthode log_user_question non disponible dans analytics")

    except Exception as e:
        logger.error(f"Erreur log_user_question_async: {e}")


@app.get("/chat/health", tags=["Chat"])
async def chat_health_direct():
    """Health check du service LLM externe"""
    try:
        import httpx
        target_url = "https://expert.intelia.com/llm/health"
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=10.0)
            return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === MONTAGE DES ROUTERS ===
try:
    from app.api.v1 import router as api_v1_router
    app.include_router(api_v1_router)
    logger.info("✅ Router API v1 charge depuis __init__.py")
except ImportError as e:
    logger.warning(f"⚠️ Impossible de charger le router v1 depuis __init__.py: {e}")
    logger.info("🔧 Creation d'un router v1 temporaire avec endpoints selectionnes...")

    from fastapi import APIRouter
    temp_v1_router = APIRouter(prefix="/v1", tags=["v1"])

    # === ENDPOINTS SELECTIONNES UNIQUEMENT ===
    routers_to_load = [
        ("conversations", "/conversations", "conversations"),
        ("auth", "", "auth"),
        ("admin", "", "admin"),
        ("health", "", "health"),
        ("system", "", "system"),
        ("users", "", "users"),
        ("invitations", "", "invitations"),
        ("logging", "", "logging"),
        ("billing", "", "billing"),
        ("billing_openai", "/billing", "billing-openai"),
        ("stats_fast", "", "statistics-fast"),
    ]

    if STATS_CACHE_AVAILABLE:
        routers_to_load.append(("stats_admin", "", "statistics-admin"))

    for router_name, prefix, tag in routers_to_load:
        try:
            router_module = __import__(f"app.api.v1.{router_name}", fromlist=["router"])
            temp_v1_router.include_router(
                router_module.router, 
                prefix=prefix if prefix else "",
                tags=[tag]
            )
            logger.info(f"✅ {router_name.capitalize()} router ajoute")
        except ImportError as e:
            logger.warning(f"⚠️ {router_name.capitalize()} router non disponible: {e}")

    # Monter le router temporaire
    app.include_router(temp_v1_router)
    logger.info("✅ Router v1 temporaire monte avec endpoints selectionnes")


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
            health_status["components"]["analytics"] = {"status": "unhealthy", "error": str(e)}
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
            health_status["components"]["billing"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"

        # Check systeme de cache statistiques
        if STATS_CACHE_AVAILABLE:
            try:
                cache = get_stats_cache()
                if hasattr(cache, "get_cache_stats"):
                    cache_stats = cache.get_cache_stats()
                else:
                    cache_stats = "disponible"

                scheduler_active = stats_scheduler_task is not None and not stats_scheduler_task.done()
                cache_success_rate = 100
                if cache_update_counter + cache_error_counter > 0:
                    cache_success_rate = (cache_update_counter / (cache_update_counter + cache_error_counter)) * 100

                health_status["components"]["statistics_cache"] = {
                    "status": ("healthy" if cache_stats and scheduler_active else "degraded"),
                    "scheduler_active": scheduler_active,
                    "cache_updates": cache_update_counter,
                    "cache_errors": cache_error_counter,
                    "success_rate": round(cache_success_rate, 1),
                    "cache_entries": cache_stats,
                }
            except Exception as e:
                health_status["components"]["statistics_cache"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"
        else:
            health_status["components"]["statistics_cache"] = {
                "status": "not_available",
                "message": "Module cache statistiques non importe",
            }

        # Check RAG (externe)
        health_status["components"]["rag"] = {
            "status": "external", 
            "message": "RAG géré par expert.intelia.com/llm",
            "local_rags": 0,
            "external_endpoint": "https://expert.intelia.com/llm"
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
                "routing_fixed": True,
            }
        except Exception as e:
            health_status["components"]["auth"] = {"status": "error", "error": str(e)}

        # Metriques systeme avec calcul memoire conteneur
        uptime_hours = (time.time() - start_time) / 3600
        health_status["metrics"] = {
            "uptime_hours": round(uptime_hours, 2),
            "total_requests": request_counter,
            "error_rate_percent": round((error_counter / max(request_counter, 1)) * 100, 2),
            "active_requests": active_requests,
            "cache_updates": cache_update_counter,
            "cache_errors": cache_error_counter,
            "scheduler_active": (stats_scheduler_task is not None and not stats_scheduler_task.done() if STATS_CACHE_AVAILABLE else False),
            "memory_percent_container": get_container_memory_percent(),
        }

        # Determiner le statut global
        component_statuses = [
            comp["status"] for comp in health_status["components"].values()
            if comp["status"] in ["healthy", "degraded", "unhealthy"]
        ]

        if any(status == "unhealthy" for status in component_statuses):
            health_status["status"] = "unhealthy"
        elif any(status == "degraded" for status in component_statuses):
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"💀 Erreur health check: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e),
        }


# === ENDPOINT RACINE SIMPLIFIÉ ===
@app.get("/", tags=["Root"])
async def root():
    uptime_hours = (time.time() - start_time) / 3600

    # Version simplifiée qui ne fait pas de calculs lourds si l'app démarre
    if uptime_hours < 2:  # Si moins de 2 heures de uptime
        return {
            "status": "running",
            "version": "4.2.0",
            "uptime_hours": round(uptime_hours, 2),
            "environment": os.getenv("ENV", "production"),
            "rag_system": "external_llm_service",
            "health": "ready"
        }

    cache_status = "not_available"
    if STATS_CACHE_AVAILABLE:
        if stats_scheduler_task and not stats_scheduler_task.done():
            cache_status = "active"
        else:
            cache_status = "available_but_inactive"

    return {
        "status": "running",
        "version": "4.2.0",
        "environment": os.getenv("ENV", "production"),
        "database": bool(getattr(app.state, "supabase", None)),
        "postgresql": bool(os.getenv("DATABASE_URL")),
        "rag_system": "external_llm_service",
        "rag_endpoint": "https://expert.intelia.com/llm",
        "synthesis_enabled": synthesis_enabled,
        "cors_fix": "applied_v3_credentials",
        "auth_routing_fix": "applied",
        "statistics_cache_system": cache_status,
        "uptime_hours": round(uptime_hours, 2),
        "requests_processed": request_counter,
        "cache_updates": cache_update_counter if STATS_CACHE_AVAILABLE else 0,
        "memory_percent": get_container_memory_percent(),
        "last_update": "2025-09-17T15:30:00Z",
        "deployment_version": "v4.2.0-rag-externalized",
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

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-ID"

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

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-ID"

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8080")))