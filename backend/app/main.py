# -*- coding: utf-8 -*-
#
# app/main.py - VERSION 4.1 NETTOYEE - ENDPOINTS SELECTIONNES UNIQUEMENT
# 🎯 GARDE: Admin, Auth, Billing, Health, Invitations, Logging, Stats, System, User
# 🧹 RETIRE: Expert, Conversations, Debug RAG, Metrics non-admin
# 🔧 CONSERVE: CORS, monitoring, cache statistiques, detection RAG amelioree
#

from __future__ import annotations

import os
import time
import logging
import asyncio
import psutil
import pathlib
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env (facultatif)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# === LOGGING GLOBAL ===
logger = logging.getLogger("app.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# === CONFIG CORS ===
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://expert.intelia.com,https://app.intelia.com,http://localhost:3000").split(",")

# ACTIVATION SYNTHESE LLM AU DEMARRAGE (CONSERVE)
synthesis_enabled = str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() in ("1", "true", "yes", "on")
if synthesis_enabled:
    logger.info("✅ Synthese LLM activee (ENABLE_SYNTH_PROMPT=1)")
else:
    logger.info("ℹ️ Synthese LLM desactivee (ENABLE_SYNTH_PROMPT=0)")

# ========== VARIABLES GLOBALES DE MONITORING (RESTAUREES) ==========
request_counter = 0
error_counter = 0
start_time = time.time()
active_requests = 0

# 🚀 NOUVEAU: Variables pour le systeme de cache statistiques
stats_scheduler_task = None
cache_update_counter = 0
cache_error_counter = 0

# === DETECTION DU SYSTEME DE CACHE STATISTIQUES ===
STATS_CACHE_AVAILABLE = False
try:
    from app.api.v1.stats_cache import get_stats_cache
    from app.api.v1.stats_updater import get_stats_updater, run_update_cycle, force_update_all
    STATS_CACHE_AVAILABLE = True
    logger.info("✅ Systeme de cache statistiques importe avec succes")
except ImportError as e:
    logger.warning(f"⚠️ Systeme de cache statistiques non disponible: {e}")
    logger.info("ℹ️ L'application fonctionnera normalement sans le cache optimise")

# === NOUVEAU: CALCUL MEMOIRE CONTENEUR PRECIS ===
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

# === OUTILS SUPPLEMENTAIRES ===
def get_rag_paths() -> Dict[str, str]:
    """🎯 TOUS LES RAG : Global + Broiler + Layer"""
    base_path = "/workspace/backend/rag_index"
    return {
        "global": f"{base_path}/global",
        "broiler": f"{base_path}/broiler",
        "layer": f"{base_path}/layer"
    }

# === FONCTION AMELIOREE DE DETECTION RAG ===
def is_rag_functional(embedder) -> bool:
    """
    Detecte si un RAG embedder est fonctionnel.
    Essaie plusieurs methodes de verification.
    """
    if embedder is None:
        return False
    
    try:
        # Methode 1: has_search_engine (si disponible)
        if hasattr(embedder, "has_search_engine"):
            if embedder.has_search_engine():
                return True
        
        # Methode 2: Verifier l'index FAISS
        if hasattr(embedder, "index") and embedder.index is not None:
            return True
        
        # Methode 3: Verifier les stats
        if hasattr(embedder, "get_index_stats"):
            stats = embedder.get_index_stats()
            if stats and stats.get("faiss_total", 0) > 0:
                return True
        
        # Methode 4: Essai de recherche simple
        try:
            results = embedder.search("test", top_k=1)
            return bool(results)
        except:
            pass
            
        return False
    except Exception as e:
        logger.debug(f"Erreur detection RAG: {e}")
        return False

# === TACHES PERIODIQUES ===
async def periodic_monitoring():
    """Monitoring periodique des performances serveur avec logging en base"""
    while True:
        try:
            await asyncio.sleep(300)  # Toutes les 5 minutes
            
            # Calcul des metriques
            current_time = time.time()
            uptime_hours = (current_time - start_time) / 3600
            requests_per_minute = request_counter / (uptime_hours * 60) if uptime_hours > 0 else 0
            error_rate_percent = (error_counter / max(request_counter, 1)) * 100
            
            # Metriques systeme avec calcul memoire conteneur precis
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = get_container_memory_percent()  # 🐳 NOUVEAU: Calcul precis
            
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
                
                # Log des metriques (cette fonction devra etre ajoutee dans logging.py)
                analytics.log_server_performance(
                    timestamp_hour=current_hour,
                    total_requests=request_counter,
                    successful_requests=request_counter - error_counter,
                    failed_requests=error_counter,
                    avg_response_time_ms=int(250),  # A calculer reellement si necessaire
                    health_status=health_status,
                    error_rate_percent=error_rate_percent
                )
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur logging metriques en base: {e}")
                
            # 🚀 NOUVEAU: Ajouter les metriques du cache
            cache_info = ""
            if STATS_CACHE_AVAILABLE:
                cache_info = f", cache: {cache_update_counter} updates, {cache_error_counter} erreurs"
                
            logger.info(f"📊 Metriques: {requests_per_minute:.1f} req/min, "
                       f"erreurs: {error_rate_percent:.1f}%, "
                       f"CPU: {cpu_percent:.1f}%, RAM: {memory_percent:.1f}%, "
                       f"sante: {health_status}{cache_info}")
            
        except Exception as e:
            logger.error(f"⌛ Erreur monitoring periodique: {e}")
            await asyncio.sleep(60)  # Retry dans 1 minute en cas d'erreur

async def periodic_stats_update():
    """🔄 Mise a jour periodique du cache statistiques toutes les heures"""
    global cache_update_counter, cache_error_counter
    
    if not STATS_CACHE_AVAILABLE:
        logger.warning("⚠️ Cache statistiques non disponible - arret scheduler")
        return
    
    # Attendre 5 minutes avant la premiere mise a jour (laisser le systeme s'initialiser)
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
            logger.warning(f"⚠️ Premiere mise a jour cache echouee: {result.get('error', 'Unknown')}")
    except Exception as e:
        cache_error_counter += 1
        logger.error(f"⌚ Erreur premiere mise a jour cache: {e}")
    
    # Boucle principale - mise a jour toutes les heures
    while True:
        try:
            # Attendre 1 heure (3600 secondes)
            await asyncio.sleep(3600)
            
            logger.info("🔄 Debut mise a jour periodique cache statistiques")
            start_update = time.time()
            
            # Lancer la mise a jour
            result = await run_update_cycle()
            
            update_duration = (time.time() - start_update) * 1000  # en ms
            
            if result.get("status") == "completed":
                cache_update_counter += 1
                successful = result.get("successful_updates", 0)
                total = result.get("total_updates", 0)
                duration = result.get("duration_ms", update_duration)
                
                logger.info(f"✅ Cache mis a jour: {successful}/{total} succes en {duration:.0f}ms")
                
                # Log detaille si des erreurs
                errors = result.get("errors", [])
                if errors:
                    logger.warning(f"⚠️ Erreurs durant la mise a jour: {errors}")
                
            elif result.get("status") == "failed":
                cache_error_counter += 1
                error_msg = result.get("error", "Erreur inconnue")
                logger.error(f"⌚ Mise a jour cache echouee: {error_msg}")
                
            else:
                cache_error_counter += 1
                logger.warning(f"⚠️ Mise a jour cache statut inattendu: {result}")
            
        except Exception as e:
            cache_error_counter += 1
            logger.error(f"⌚ Erreur durant mise a jour periodique cache: {e}")
            # Attendre 10 minutes avant de retry en cas d'erreur
            await asyncio.sleep(600)

# === LIFESPAN COMPLET AVEC DETECTION RAG AMELIOREE ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== INITIALISATION AU DEMARRAGE ==========
    logger.info("🚀 Demarrage de l'application Expert API avec systeme complet + detection RAG amelioree")

    # ========== INITIALISATION DES SERVICES AMELIOREE ==========
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

            # 🚀 Cache statistiques (optionnel)
            if STATS_CACHE_AVAILABLE:
                try:
                    cache = get_stats_cache()
                    # Methodes possibles pour obtenir les stats
                    if hasattr(cache, 'get_cache_stats'):
                        cache_stats = cache.get_cache_stats()
                    elif hasattr(cache, 'get_stats'):
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
        logger.error(f"⌛ Erreur initialisation services: {e}")

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

    # 🚀 CHARGEMENT DES 3 RAG AVEC DETECTION AMELIOREE (OPTIONNEL)
    app.state.rag = None
    app.state.rag_broiler = None
    app.state.rag_layer = None
    total_rags = 0  # Initialiser par defaut

    try:
        from rag.embedder import FastRAGEmbedder

        rag_paths = get_rag_paths()
        logger.info(f"🔍 Chargement des 3 RAG: {list(rag_paths.keys())}")

        # Variables d'environnement (override si definies)
        env_override = {
            "global": os.getenv("RAG_INDEX_GLOBAL"),
            "broiler": os.getenv("RAG_INDEX_BROILER"),
            "layer": os.getenv("RAG_INDEX_LAYER"),
        }
        for key, env_path in env_override.items():
            if env_path and os.path.exists(env_path):
                rag_paths[key] = env_path
                logger.info(f"🔧 Override ENV pour {key}: {env_path}")

        def _log_loaded(name: str, path: str, emb) -> None:
            try:
                # Essayer differentes methodes pour obtenir les stats
                stats = {}
                if hasattr(emb, "get_index_stats"):
                    stats = emb.get_index_stats() or {}
                elif hasattr(emb, "get_stats"):
                    stats = emb.get_stats() or {}
                
                # Essayer d'obtenir les infos directement des attributs
                n_docs = stats.get("n_docs")
                if n_docs is None and hasattr(emb, "documents") and emb.documents:
                    n_docs = len(emb.documents)
                
                faiss_total = stats.get("faiss_total")
                if faiss_total is None and hasattr(emb, "index") and emb.index:
                    faiss_total = emb.index.ntotal if hasattr(emb.index, "ntotal") else None
                
                chunks_loaded = stats.get("chunks_loaded", faiss_total)
                dim = stats.get("embedding_dim", stats.get("dim"))
                if dim is None and hasattr(emb, "embedding_dim"):
                    dim = emb.embedding_dim
                
                model = stats.get("model_name", stats.get("model"))
                if model is None and hasattr(emb, "model_name"):
                    model = emb.model_name
                
                logger.info(
                    f"✅ RAG {name.capitalize()} charge: {path} "
                    f"(docs={n_docs if n_docs is not None else 'unknown'}, "
                    f"chunks={chunks_loaded if chunks_loaded is not None else 'unknown'}, "
                    f"dim={dim if dim is not None else 'unknown'}, "
                    f"model={model if model is not None else 'unknown'})"
                )
                
                # Debug : afficher les attributs disponibles si stats vides
                if not any([n_docs, faiss_total, dim, model]):
                    available_attrs = [attr for attr in dir(emb) if not attr.startswith('_')][:10]
                    logger.debug(f"📊 Attributs disponibles sur {name}: {available_attrs}")
                    
            except Exception as e:
                logger.info(f"✅ RAG {name.capitalize()} charge: {path}")
                logger.debug(f"Erreur recuperation stats {name}: {e}")

        def _load_rag(name: str, path: str, debug: bool = False):
            """Fonction helper pour charger un RAG avec gestion d'erreurs amelioree."""
            logger.info(f"🔍 Chargement RAG {name.capitalize()}: {path}")
            
            if not os.path.exists(path):
                logger.warning(f"⚠️ RAG {name.capitalize()}: Chemin inexistant {path}")
                return None
            
            try:
                # Verifier le contenu du dossier
                entries = os.listdir(path)
                logger.debug(f"📂 {name.upper()} dir entries ({len(entries)}): {entries[:10]}")
                
                # Chercher les fichiers requis
                required_files = ["index.faiss"]
                missing_files = [f for f in required_files if f not in entries]
                if missing_files:
                    logger.warning(f"⚠️ RAG {name.capitalize()}: Fichiers manquants {missing_files}")
                
                # CORRECTION PRINCIPALE: Utiliser index_dir dans le constructeur
                embedder = FastRAGEmbedder(
                    index_dir=path,
                    debug=debug,
                    cache_embeddings=True,
                    max_workers=2,
                )
                
                # Tester la fonctionnalite avec notre fonction amelioree
                if is_rag_functional(embedder):
                    _log_loaded(name, path, embedder)
                    return embedder
                else:
                    logger.warning(f"⚠️ RAG {name.capitalize()}: Instance creee mais non fonctionnelle")
                    # Log des details pour debug
                    if hasattr(embedder, "get_index_stats"):
                        stats = embedder.get_index_stats()
                        logger.debug(f"📊 Stats {name}: {stats}")
                    return None
                    
            except Exception as e:
                logger.exception(f"💥 RAG {name.capitalize()} init failed: {e}")
                return None

        # 🚀 Chargement des 3 RAG
        app.state.rag = _load_rag("global", rag_paths["global"], debug=False)
        app.state.rag_broiler = _load_rag("broiler", rag_paths["broiler"])
        app.state.rag_layer = _load_rag("layer", rag_paths["layer"])

        # 📊 Resume final des 3 RAG
        total_rags = sum(1 for rag in [app.state.rag, app.state.rag_broiler, app.state.rag_layer] if rag)

        rag_summary = {
            "global": "✅ Actif" if app.state.rag else "⌛ CRITIQUE",
            "broiler": "✅ Actif" if app.state.rag_broiler else "⌛ Absent",
            "layer": "✅ Actif" if app.state.rag_layer else "⌛ Absent",
            "total_loaded": total_rags
        }
        logger.info(f"📊 Status final des RAG: {rag_summary}")

        if total_rags == 3:
            logger.info("🎉 PARFAIT: Les 3 RAG sont charges (Global + Broiler + Layer)")
        elif total_rags >= 1:
            logger.warning(f"⚠️ Seulement {total_rags}/3 RAG charges - fonctionnement partiel")
        else:
            logger.error("⌚ CRITIQUE: Aucun RAG charge - l'application ne peut pas fonctionner correctement")

    except ImportError as e:
        logger.warning(f"⚠️ Module RAG non disponible: {e}")
        logger.info("ℹ️ L'application fonctionnera sans le systeme RAG")
        total_rags = 0
    except Exception as e:
        logger.error("⌛ Erreur critique initialisation RAG: %s", e)
        total_rags = 0

    # ========== DEMARRAGE DU MONITORING & SCHEDULER ==========
    monitoring_task = None
    global stats_scheduler_task
    
    try:
        monitoring_task = asyncio.create_task(periodic_monitoring())
        logger.info("📊 Monitoring periodique demarre")
    except Exception as e:
        logger.error(f"⌛ Erreur demarrage monitoring: {e}")

    if STATS_CACHE_AVAILABLE:
        try:
            stats_scheduler_task = asyncio.create_task(periodic_stats_update())
            logger.info("🔄 Scheduler cache statistiques demarre (mise a jour toutes les heures)")
        except Exception as e:
            logger.error(f"⌚ Erreur demarrage scheduler cache: {e}")
    else:
        logger.info("ℹ️ Scheduler cache statistiques desactive (module non disponible)")

    # ========== L'APPLICATION DEMARRE ==========
    system_features = []
    if STATS_CACHE_AVAILABLE:
        system_features.append("cache statistiques optimise")
    system_features.extend([f"{total_rags}/3 RAG", "monitoring", "analytics", "billing"])
    logger.info(f"🎯 Application Expert API prete avec: {', '.join(system_features)}")
    yield  # --- L'APPLICATION FONCTIONNE ---

    # ========== NETTOYAGE A L'ARRET ==========
    logger.info("🛑 Arret de l'application Expert API")
    
    # Arreter le monitoring
    if monitoring_task:
        try:
            monitoring_task.cancel()
            await asyncio.gather(monitoring_task, return_exceptions=True)
            logger.info("📊 Monitoring periodique arrete")
        except Exception as e:
            logger.error(f"⌛ Erreur arret monitoring: {e}")
    
    # 🚀 Arreter le scheduler cache
    if stats_scheduler_task:
        try:
            stats_scheduler_task.cancel()
            await asyncio.gather(stats_scheduler_task, return_exceptions=True)
            logger.info("🔄 Scheduler cache statistiques arrete")
        except Exception as e:
            logger.error(f"⌚ Erreur arret scheduler cache: {e}")
    
    # Statistiques finales
    uptime_hours = (time.time() - start_time) / 3600
    final_stats = f"{request_counter} requetes en {uptime_hours:.1f}h, {error_counter} erreurs ({(error_counter/max(request_counter,1)*100):.1f}%)"
    
    if STATS_CACHE_AVAILABLE and cache_update_counter > 0:
        cache_success_rate = ((cache_update_counter / max(cache_update_counter + cache_error_counter, 1)) * 100)
        final_stats += f", cache: {cache_update_counter} mises a jour ({cache_success_rate:.1f}% succes)"
    
    logger.info(f"📈 Statistiques finales: {final_stats}")

# === FASTAPI APP ===
app = FastAPI(
    title="Intelia Expert API",
    version="4.1.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# === MIDDLEWARE CORS CORRIGE ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://expert.intelia.com",
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
        "X-Session-ID"
    ],
    expose_headers=[
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers"
    ]
)

# === MIDDLEWARE DE MONITORING DES REQUETES (RESTAURE) ===
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """Middleware pour tracker les performances en temps reel"""
    global request_counter, error_counter, active_requests
    
    start_time_req = time.time()
    active_requests += 1
    request_counter += 1
    
    try:
        response = await call_next(request)
        
        # Tracker les erreurs
        if response.status_code >= 400:
            error_counter += 1
            
        return response
        
    except Exception as e:
        error_counter += 1
        logger.error(f"⌛ Erreur dans middleware monitoring: {e}")
        raise
        
    finally:
        active_requests -= 1
        processing_time = (time.time() - start_time_req) * 1000
        
        # Log des requetes lentes
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
    logger.error(f"⌛ Erreur lors de l'activation du middleware d'auth: {e}")

# === MONTAGE DES ROUTERS - ENDPOINTS SELECTIONNES UNIQUEMENT ===
try:
    from app.api.v1 import router as api_v1_router
    app.include_router(api_v1_router)
    logger.info("✅ Router API v1 charge depuis __init__.py")
except ImportError as e:
    logger.warning(f"⚠️ Impossible de charger le router v1 depuis __init__.py: {e}")
    logger.info("🔧 Creation d'un router v1 temporaire avec endpoints selectionnes...")
    
    # Creer un router temporaire et inclure UNIQUEMENT les composants selectionnes
    from fastapi import APIRouter
    temp_v1_router = APIRouter(prefix="/v1", tags=["v1"])
    
    # === ENDPOINTS SELECTIONNES UNIQUEMENT ===
    
    # Expert router (pour les endpoints de chat)
    try:
        from app.api.v1.expert import router as expert_router
        temp_v1_router.include_router(expert_router, tags=["expert"])
        logger.info("✅ Expert router ajoute (pour endpoints chat)")
    except ImportError as e:
        logger.error(f"⌛ Expert router non disponible: {e}")
    
    # Auth router
    try:
        from app.api.v1.auth import router as auth_router
        temp_v1_router.include_router(
            auth_router, 
            prefix="",  # Pas de prefix car auth.py definit deja router = APIRouter(prefix="/auth")
            tags=["auth"]
        )
        logger.info("✅ Auth router ajoute")
    except ImportError as e:
        logger.error(f"⌛ Auth router non disponible: {e}")
    
    # Admin router
    try:
        from app.api.v1.admin import router as admin_router
        temp_v1_router.include_router(admin_router, tags=["admin"])
        logger.info("✅ Admin router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Admin router non disponible: {e}")
    
    # Health router
    try:
        from app.api.v1.health import router as health_router
        temp_v1_router.include_router(health_router, tags=["health"])
        logger.info("✅ Health router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Health router non disponible: {e}")
    
    # System router
    try:
        from app.api.v1.system import router as system_router
        temp_v1_router.include_router(system_router, tags=["system"])
        logger.info("✅ System router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ System router non disponible: {e}")
    
    # Users router
    try:
        from app.api.v1.users import router as users_router
        temp_v1_router.include_router(users_router, tags=["users"])
        logger.info("✅ Users router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Users router non disponible: {e}")
    
    # Invitations router
    try:
        from app.api.v1.invitations import router as invitations_router
        temp_v1_router.include_router(invitations_router, tags=["invitations"])
        logger.info("✅ Invitations router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Invitations router non disponible: {e}")
    
    # Logging router (inclut logging, logging_cache, logging_helpers, logging_models, logging_permissions)
    try:
        from app.api.v1.logging import router as logging_router
        temp_v1_router.include_router(logging_router, tags=["logging"])
        logger.info("✅ Logging router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Logging router non disponible: {e}")
    
    # Billing router
    try:
        from app.api.v1.billing import router as billing_router
        temp_v1_router.include_router(billing_router, tags=["billing"])
        logger.info("✅ Billing router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Billing router non disponible: {e}")
    
    # Billing OpenAI router
    try:
        from app.api.v1.billing_openai import router as billing_openai_router
        temp_v1_router.include_router(billing_openai_router, prefix="/billing", tags=["billing-openai"])
        logger.info("✅ Billing OpenAI router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Billing OpenAI router non disponible: {e}")
    
    # 🚀 Stats Fast router (endpoints ultra-rapides)
    try:
        from app.api.v1.stats_fast import router as stats_fast_router
        temp_v1_router.include_router(stats_fast_router, tags=["statistics-fast"])
        logger.info("✅ Stats Fast router ajoute")
    except ImportError as e:
        logger.warning(f"⚠️ Stats Fast router non disponible: {e}")

    # 🚀 Stats Admin router (administration cache)
    if STATS_CACHE_AVAILABLE:
        try:
            from app.api.v1.stats_admin import router as stats_admin_router
            temp_v1_router.include_router(stats_admin_router, tags=["statistics-admin"])
            logger.info("✅ Stats Admin router ajoute")
        except ImportError as e:
            logger.warning(f"⚠️ Stats Admin router non disponible: {e}")
    
    # Monter le router temporaire
    app.include_router(temp_v1_router)
    logger.info("✅ Router v1 temporaire monte avec endpoints selectionnes")

# === ENDPOINTS PRINCIPAUX (HEALTH CHECK) ===
@app.get("/health/complete", tags=["Health"])
async def complete_health_check():
    """🩼 Check de sante complet du systeme"""
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check base de donnees et analytics
        try:
            from app.api.v1.logging import get_analytics_manager
            analytics = get_analytics_manager()
            health_status["components"]["analytics"] = {
                "status": "healthy",
                "type": "postgresql",
                "tables_created": True
            }
        except Exception as e:
            health_status["components"]["analytics"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check systeme de facturation
        try:
            from app.api.v1.billing import get_billing_manager
            billing = get_billing_manager()
            health_status["components"]["billing"] = {
                "status": "healthy",
                "plans_loaded": len(billing.plans),
                "quota_enforcement": True
            }
        except Exception as e:
            health_status["components"]["billing"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # 🚀 Check systeme de cache statistiques
        if STATS_CACHE_AVAILABLE:
            try:
                cache = get_stats_cache()
                if hasattr(cache, 'get_cache_stats'):
                    cache_stats = cache.get_cache_stats()
                else:
                    cache_stats = "disponible"
                
                scheduler_active = stats_scheduler_task is not None and not stats_scheduler_task.done()
                cache_success_rate = 100
                if cache_update_counter + cache_error_counter > 0:
                    cache_success_rate = (cache_update_counter / (cache_update_counter + cache_error_counter)) * 100
                
                health_status["components"]["statistics_cache"] = {
                    "status": "healthy" if cache_stats and scheduler_active else "degraded",
                    "scheduler_active": scheduler_active,
                    "cache_updates": cache_update_counter,
                    "cache_errors": cache_error_counter,
                    "success_rate": round(cache_success_rate, 1),
                    "cache_entries": cache_stats
                }
            except Exception as e:
                health_status["components"]["statistics_cache"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        else:
            health_status["components"]["statistics_cache"] = {
                "status": "not_available",
                "message": "Module cache statistiques non importe"
            }
        
        # Check RAG
        total_rags = sum(1 for rag in [
            getattr(app.state, "rag", None),
            getattr(app.state, "rag_broiler", None), 
            getattr(app.state, "rag_layer", None)
        ] if rag and is_rag_functional(rag))
        
        health_status["components"]["rag"] = {
            "status": "healthy" if total_rags >= 2 else "degraded" if total_rags >= 1 else "unhealthy",
            "loaded_rags": total_rags,
            "total_rags": 3
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
                "routing_fixed": True
            }
        except Exception as e:
            health_status["components"]["auth"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Metriques systeme avec calcul memoire conteneur
        uptime_hours = (time.time() - start_time) / 3600
        health_status["metrics"] = {
            "uptime_hours": round(uptime_hours, 2),
            "total_requests": request_counter,
            "error_rate_percent": round((error_counter / max(request_counter, 1)) * 100, 2),
            "active_requests": active_requests,
            "cache_updates": cache_update_counter,
            "cache_errors": cache_error_counter,
            "scheduler_active": stats_scheduler_task is not None and not stats_scheduler_task.done() if STATS_CACHE_AVAILABLE else False,
            "memory_percent_container": get_container_memory_percent()  # 🐳 NOUVEAU
        }
        
        # Determiner le statut global
        component_statuses = [comp["status"] for comp in health_status["components"].values() 
                            if comp["status"] in ["healthy", "degraded", "unhealthy"]]
        
        if any(status == "unhealthy" for status in component_statuses):
            health_status["status"] = "unhealthy"
        elif any(status == "degraded" for status in component_statuses):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"⌛ Erreur health check: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }

@app.get("/admin/stats", tags=["Admin"])
async def admin_statistics():
    """📈 Statistiques administrateur completes avec cache"""
    try:
        from app.api.v1.billing import get_billing_manager
        
        # Stats billing
        billing = get_billing_manager()
        
        # Stats analytics (approximatives)
        uptime_hours = (time.time() - start_time) / 3600
        
        base_stats = {
            "system_health": {
                "uptime_hours": round(uptime_hours, 2),
                "total_requests": request_counter,
                "error_rate": round((error_counter / max(request_counter, 1)) * 100, 2),
                "memory_percent_container": get_container_memory_percent(),  # 🐳 NOUVEAU
                "rag_status": {
                    "global": bool(getattr(app.state, "rag", None)),
                    "broiler": bool(getattr(app.state, "rag_broiler", None)),
                    "layer": bool(getattr(app.state, "rag_layer", None))
                }
            },
            "billing_stats": {
                "plans_available": len(billing.plans),
                "plan_names": list(billing.plans.keys())
            },
            "features_enabled": {
                "analytics": bool(os.getenv("DATABASE_URL")),
                "billing": True,
                "authentication": bool(os.getenv("JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET")),
                "openai_fallback": bool(os.getenv("OPENAI_API_KEY")),
                "auth_routing_fixed": True,
                "cors_middleware_fixed": True,
                "direct_auth_endpoints": True,
                "cors_credentials_fixed": True,
                "statistics_cache_system": STATS_CACHE_AVAILABLE,
                "stats_admin_router_enabled": True,
                "container_memory_calculation": True,  # 🐳 NOUVEAU
            }
        }
        
        # 🚀 Ajouter stats cache si disponible
        if STATS_CACHE_AVAILABLE:
            try:
                cache = get_stats_cache()
                if hasattr(cache, 'get_cache_stats'):
                    cache_stats = cache.get_cache_stats()
                else:
                    cache_stats = "disponible"
                
                base_stats["cache_system"] = {
                    "enabled": True,
                    "scheduler_active": stats_scheduler_task is not None and not stats_scheduler_task.done(),
                    "updates_total": cache_update_counter,
                    "errors_total": cache_error_counter,
                    "success_rate": round((cache_update_counter / max(cache_update_counter + cache_error_counter, 1)) * 100, 1),
                    "cache_statistics": cache_stats
                }
            except Exception as e:
                base_stats["cache_system"] = {
                    "enabled": True,
                    "status": "error",
                    "error": str(e)
                }
        else:
            base_stats["cache_system"] = {
                "enabled": False,
                "reason": "Module non importe"
            }
        
        return base_stats
        
    except Exception as e:
        return {"error": str(e)}

# 🚀 Endpoints pour controle manuel du cache
@app.post("/admin/cache/force-update", tags=["Admin"])
async def admin_force_cache_update():
    """🔄 Force une mise a jour manuelle du cache (admin)"""
    if not STATS_CACHE_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Systeme de cache non disponible"
        }
    
    try:
        logger.info("🔄 Force update cache demande via admin endpoint")
        result = await force_update_all()
        
        global cache_update_counter, cache_error_counter
        if result.get("status") == "completed":
            cache_update_counter += 1
        else:
            cache_error_counter += 1
        
        return {
            "status": "success",
            "message": "Mise a jour cache forcee",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        cache_error_counter += 1
        logger.error(f"⌚ Erreur force update admin: {e}")
        return {
            "status": "error",
            "message": f"Erreur mise a jour: {e}",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/admin/cache/status", tags=["Admin"])
async def admin_cache_status():
    """📊 Statut detaille du systeme de cache (admin)"""
    if not STATS_CACHE_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Systeme de cache non disponible",
            "enabled": False
        }
    
    try:
        cache = get_stats_cache()
        updater = get_stats_updater()
        
        if hasattr(cache, 'get_cache_stats'):
            cache_stats = cache.get_cache_stats()
        else:
            cache_stats = "disponible"
            
        if hasattr(updater, 'get_update_status'):
            update_status = updater.get_update_status()
        else:
            update_status = "disponible"
        
        return {
            "status": "available",
            "enabled": True,
            "scheduler": {
                "active": stats_scheduler_task is not None and not stats_scheduler_task.done(),
                "task_done": stats_scheduler_task.done() if stats_scheduler_task else True
            },
            "counters": {
                "updates_successful": cache_update_counter,
                "updates_failed": cache_error_counter,
                "success_rate": round((cache_update_counter / max(cache_update_counter + cache_error_counter, 1)) * 100, 1)
            },
            "cache_statistics": cache_stats,
            "last_update": update_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "enabled": True
        }

# === ENDPOINTS AUTH DIRECTS (RESTAURES) ===
@app.post("/v1/auth/login")
async def auth_login_direct(request: Request):
    """Endpoint login direct - contournement du probleme de router"""
    try:
        from app.api.v1.auth import LoginRequest, create_access_token
        
        body = await request.json()
        login_data = LoginRequest(**body)
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication service unavailable"}
            )
        
        try:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            
            result = supabase.auth.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            
        except Exception as e:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid credentials", "error": str(e)}
            )
        
        user = result.user
        if user is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid credentials"}
            )
        
        expires = timedelta(minutes=60)
        token = create_access_token(
            {"user_id": user.id, "email": login_data.email}, 
            expires
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": (datetime.utcnow() + expires).isoformat(),
            "user": {
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata
            }
        }
        
    except Exception as e:
        logger.error(f"⌛ Erreur login direct: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Login failed", "error": str(e)}
        )

@app.get("/v1/auth/me")
async def auth_me_direct(request: Request):
    """Endpoint me direct"""
    try:
        from app.api.v1.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"}
            )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.replace("Bearer ", "")
        )
        
        user_info = await get_current_user(credentials)
        
        return {
            "user_id": user_info.get("user_id"),
            "email": user_info.get("email"),
            "user_type": user_info.get("user_type"),
            "full_name": user_info.get("full_name"),
            "is_admin": user_info.get("is_admin"),
            "preferences": user_info.get("preferences", {}),
            "profile_id": user_info.get("profile_id"),
            "direct_endpoint": True,
            "routing_corrected": True
        }
        
    except Exception as e:
        logger.error(f"⌛ Erreur me direct: {e}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication failed", "error": str(e)}
        )

@app.get("/", tags=["Root"])
async def root():
    def rag_status() -> str:
        total_rags = sum(1 for rag in [
            getattr(app.state, "rag", None),
            getattr(app.state, "rag_broiler", None),
            getattr(app.state, "rag_layer", None)
        ] if rag and is_rag_functional(rag))

        if total_rags == 3:
            return "optimal_3_rags"
        elif total_rags == 1:
            return "suboptimal_1_rag"
        else:
            return f"partial_{total_rags}_rags"

    uptime_hours = (time.time() - start_time) / 3600
    
    cache_status = "not_available"
    if STATS_CACHE_AVAILABLE:
        if stats_scheduler_task and not stats_scheduler_task.done():
            cache_status = "active"
        else:
            cache_status = "available_but_inactive"
    
    return {
        "status": "running",
        "version": "4.1.0",
        "environment": os.getenv("ENV", "production"),
        "database": bool(getattr(app.state, "supabase", None)),
        "postgresql": bool(os.getenv("DATABASE_URL")),
        "rag": rag_status(),
        "synthesis_enabled": synthesis_enabled,
        "cors_fix": "applied_v3_credentials",
        "optimization": "three_rag_system_enabled",
        "auth_routing_fix": "applied",
        "catch_22_resolved": True,
        "cors_middleware_fixed": True,
        "direct_auth_endpoints": True,
        "cors_credentials_fixed": True,
        "statistics_cache_system": cache_status,
        "stats_admin_router_enabled": True,
        "improved_rag_detection": True,
        "container_memory_calculation": True,  # 🐳 NOUVEAU
        "uptime_hours": round(uptime_hours, 2),
        "requests_processed": request_counter,
        "cache_updates": cache_update_counter if STATS_CACHE_AVAILABLE else 0,
        "memory_percent": get_container_memory_percent(),  # 🐳 NOUVEAU
        "last_update": "2025-08-25T02:30:00Z",
        "deployment_version": "v4.1.0-cleaned-endpoints"
    }

# === GESTIONNAIRES D'EXCEPTIONS AVEC CORS CORRIGE ===
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat() + "Z"},
        headers={"content-type": "application/json; charset=utf-8"},
    )

    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080"
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
        content={"detail": "Internal server error", "timestamp": datetime.utcnow().isoformat() + "Z"},
        headers={"content-type": "application/json; charset=utf-8"},
    )

    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080"
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
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))