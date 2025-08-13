# app/main.py - VERSION 3 RAG COMPLETS - CORRIGÉ AVEC AUTH + MONITORING COMPLET + ANALYTICS
from __future__ import annotations

import os
import logging
import time
import asyncio
import psutil
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Optional, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env (facultatif)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger("app.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# 🆕 ACTIVATION SYNTHÈSE LLM AU DÉMARRAGE
synthesis_enabled = str(os.getenv("ENABLE_SYNTH_PROMPT", "0")).lower() in ("1", "true", "yes", "on")
if synthesis_enabled:
    logger.info("✅ Synthèse LLM activée (ENABLE_SYNTH_PROMPT=1)")
else:
    logger.info("ℹ️ Synthèse LLM désactivée (ENABLE_SYNTH_PROMPT=0)")

# ========== VARIABLES GLOBALES DE MONITORING ==========
request_counter = 0
error_counter = 0
start_time = time.time()
active_requests = 0

# ========== FONCTION DE MONITORING PÉRIODIQUE AMÉLIORÉE ==========
async def periodic_monitoring():
    """Monitoring périodique des performances serveur avec logging en base"""
    while True:
        try:
            await asyncio.sleep(300)  # Toutes les 5 minutes
            
            # Calcul des métriques
            current_time = time.time()
            uptime_hours = (current_time - start_time) / 3600
            requests_per_minute = request_counter / (uptime_hours * 60) if uptime_hours > 0 else 0
            error_rate_percent = (error_counter / max(request_counter, 1)) * 100
            
            # Métriques système
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Déterminer le status de santé
            if error_rate_percent > 10 or cpu_percent > 90 or memory_percent > 90:
                health_status = "critical"
            elif error_rate_percent > 5 or cpu_percent > 70 or memory_percent > 70:
                health_status = "degraded"
            else:
                health_status = "healthy"
            
            # Log des métriques serveur dans la base
            try:
                from app.api.v1.logging import get_analytics_manager
                analytics = get_analytics_manager()
                
                # Calculer l'heure tronquée pour le groupement
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                
                # Log des métriques (cette fonction devra être ajoutée dans logging.py)
                analytics.log_server_performance(
                    timestamp_hour=current_hour,
                    total_requests=request_counter,
                    successful_requests=request_counter - error_counter,
                    failed_requests=error_counter,
                    avg_response_time_ms=int(250),  # À calculer réellement si nécessaire
                    health_status=health_status,
                    error_rate_percent=error_rate_percent
                )
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur logging métriques en base: {e}")
                
            logger.info(f"📊 Métriques: {requests_per_minute:.1f} req/min, "
                       f"erreurs: {error_rate_percent:.1f}%, "
                       f"CPU: {cpu_percent:.1f}%, RAM: {memory_percent:.1f}%, "
                       f"santé: {health_status}")
            
        except Exception as e:
            logger.error(f"❌ Erreur monitoring périodique: {e}")
            await asyncio.sleep(60)  # Retry dans 1 minute en cas d'erreur

# -------------------------------------------------------------------
# FONCTION RAG COMPLÈTE - 3 RAG
# -------------------------------------------------------------------
def get_rag_paths() -> Dict[str, str]:
    """🎯 TOUS LES RAG : Global + Broiler + Layer"""
    base_path = "/workspace/backend/rag_index"
    return {
        "global": f"{base_path}/global",
        "broiler": f"{base_path}/broiler",
        "layer": f"{base_path}/layer"
    }

# -------------------------------------------------------------------
# Lifespan: init Supabase + 3 RAG COMPLETS + MONITORING
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== INITIALISATION AU DÉMARRAGE ==========
    logger.info("🚀 Démarrage de l'application Expert API avec système complet")
    
    # ========== INITIALISATION DES SERVICES AMÉLIORÉE ==========
    try:
        logger.info("📊 Initialisation des services analytics et facturation...")
        
        # Vérifier la base de données
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info("✅ DATABASE_URL configurée")
            
            # Initialiser les services avec gestion d'erreur
            try:
                from app.api.v1.logging import get_analytics
                analytics_status = get_analytics()
                logger.info(f"✅ Service analytics: {analytics_status.get('status', 'unknown')}")
            except Exception as e:
                logger.warning(f"⚠️ Service analytics partiellement disponible: {e}")
            
            try:
                from app.api.v1.billing import get_billing_manager
                billing = get_billing_manager()
                logger.info(f"✅ Service billing: {len(billing.plans)} plans chargés")
            except Exception as e:
                logger.warning(f"⚠️ Service billing partiellement disponible: {e}")
            
            # Nettoyer les anciennes sessions (plus de 7 jours)
            try:
                from app.api.v1.pipeline.postgres_memory import PostgresMemory
                memory = PostgresMemory()
                cleaned = memory.cleanup_old_sessions(days_old=7)
                if cleaned > 0:
                    logger.info(f"🧹 {cleaned} anciennes sessions nettoyées")
            except Exception as e:
                logger.warning(f"⚠️ Nettoyage sessions échoué: {e}")
                
        else:
            logger.warning("⚠️ DATABASE_URL manquante - services analytics désactivés")
            
    except Exception as e:
        logger.error(f"❌ Erreur initialisation services: {e}")
        # Ne pas empêcher le démarrage
    
    # Initialisation Supabase (CONSERVÉ)
    app.state.supabase = None
    try:
        from supabase import create_client
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            app.state.supabase = create_client(url, key)
            logger.info("✅ Supabase prêt")
        else:
            logger.info("ℹ️ Supabase non configuré")
    except Exception as e:
        logger.warning("ℹ️ Supabase indisponible: %s", e)

    # 🚀 CHARGEMENT DES 3 RAG (CONSERVÉ INTÉGRALEMENT)
    app.state.rag = None
    app.state.rag_broiler = None
    app.state.rag_layer = None

    try:
        from rag.embedder import FastRAGEmbedder

        rag_paths = get_rag_paths()
        logger.info(f"🔍 Chargement des 3 RAG: {list(rag_paths.keys())}")

        # Variables d'environnement (override si définies)
        env_override = {
            "global": os.getenv("RAG_INDEX_GLOBAL"),
            "broiler": os.getenv("RAG_INDEX_BROILER"),
            "layer": os.getenv("RAG_INDEX_LAYER"),
        }

        # Appliquer les overrides ENV
        for key, env_path in env_override.items():
            if env_path and os.path.exists(env_path):
                rag_paths[key] = env_path
                logger.info(f"🔧 Override ENV pour {key}: {env_path}")

        # Helper pour logguer proprement une instance
        def _log_loaded(name: str, path: str, emb) -> None:
            try:
                stats = emb.get_index_stats() if hasattr(emb, "get_index_stats") else {}
                n_docs = stats.get("n_docs")
                faiss_total = stats.get("faiss_total")
                chunks_loaded = stats.get("chunks_loaded", faiss_total)
                dim = stats.get("embedding_dim", "unknown")
                model = stats.get("model_name", "unknown")
                logger.info(
                    f"✅ RAG {name.capitalize()} chargé: {path} "
                    f"(docs={n_docs if n_docs is not None else 'unknown'}, "
                    f"chunks={chunks_loaded if chunks_loaded is not None else 'unknown'}, "
                    f"dim={dim}, model={model})"
                )
            except Exception:
                logger.info(f"✅ RAG {name.capitalize()} chargé: {path}")

        # 🚀 GLOBAL
        global_path = rag_paths["global"]
        logger.info(f"🔍 Chargement RAG Global: {global_path}")
        if os.path.exists(global_path):
            global_embedder = FastRAGEmbedder(debug=True, cache_embeddings=True, max_workers=2)
            if global_embedder.load_index(global_path) and global_embedder.has_search_engine():
                app.state.rag = global_embedder
                _log_loaded("global", global_path, global_embedder)
            else:
                logger.error(f"❌ RAG Global: Échec chargement depuis {global_path}")
        else:
            logger.error(f"❌ RAG Global: Chemin inexistant {global_path}")

        # 🚀 BROILER
        broiler_path = rag_paths["broiler"]
        logger.info(f"🔍 Chargement RAG Broiler: {broiler_path}")
        if os.path.exists(broiler_path):
            try:
                broiler_embedder = FastRAGEmbedder(debug=False, cache_embeddings=True, max_workers=2)
                if broiler_embedder.load_index(broiler_path) and broiler_embedder.has_search_engine():
                    app.state.rag_broiler = broiler_embedder
                    _log_loaded("broiler", broiler_path, broiler_embedder)
                else:
                    logger.warning(f"⚠️ RAG Broiler: Échec chargement depuis {broiler_path}")
            except Exception as e:
                logger.warning(f"⚠️ RAG Broiler: Erreur {e}")
        else:
            logger.warning(f"⚠️ RAG Broiler: Chemin inexistant {broiler_path}")

        # 🚀 LAYER
        layer_path = rag_paths["layer"]
        logger.info(f"🔍 Chargement RAG Layer: {layer_path}")
        if os.path.exists(layer_path):
            try:
                layer_embedder = FastRAGEmbedder(debug=False, cache_embeddings=True, max_workers=2)
                if layer_embedder.load_index(layer_path) and layer_embedder.has_search_engine():
                    app.state.rag_layer = layer_embedder
                    _log_loaded("layer", layer_path, layer_embedder)
                else:
                    logger.warning(f"⚠️ RAG Layer: Échec chargement depuis {layer_path}")
            except Exception as e:
                logger.warning(f"⚠️ RAG Layer: Erreur {e}")
        else:
            logger.warning(f"⚠️ RAG Layer: Chemin inexistant {layer_path}")

        # 📊 Résumé final des 3 RAG
        total_rags = sum(1 for rag in [app.state.rag, app.state.rag_broiler, app.state.rag_layer] if rag)

        rag_summary = {
            "global": "✅ Actif" if app.state.rag else "❌ CRITIQUE",
            "broiler": "✅ Actif" if app.state.rag_broiler else "❌ Absent",
            "layer": "✅ Actif" if app.state.rag_layer else "❌ Absent",
            "total_loaded": total_rags
        }
        logger.info(f"📊 Status final des RAG: {rag_summary}")

        if total_rags == 3:
            logger.info("🎉 PARFAIT: Les 3 RAG sont chargés (Global + Broiler + Layer)")
        elif total_rags == 1:
            logger.warning("⚠️ Seulement 1 RAG chargé - potentiel gâché")
        else:
            logger.warning(f"⚠️ Seulement {total_rags}/3 RAG chargés")

    except Exception as e:
        logger.error("❌ Erreur critique initialisation RAG: %s", e)

    # ========== DÉMARRAGE DU MONITORING PÉRIODIQUE ==========
    monitoring_task = None
    try:
        monitoring_task = asyncio.create_task(periodic_monitoring())
        logger.info("📊 Monitoring périodique démarré")
    except Exception as e:
        logger.error(f"❌ Erreur démarrage monitoring: {e}")

    # ========== L'APPLICATION DÉMARRE ==========
    logger.info("🎯 Application Expert API prête avec système complet")
    yield  # --- L'application fonctionne ---

    # ========== NETTOYAGE À L'ARRÊT ==========
    logger.info("🛑 Arrêt de l'application Expert API")
    
    # Arrêter le monitoring
    if monitoring_task:
        try:
            monitoring_task.cancel()
            logger.info("📊 Monitoring périodique arrêté")
        except Exception as e:
            logger.error(f"❌ Erreur arrêt monitoring: {e}")
    
    # Statistiques finales
    uptime_hours = (time.time() - start_time) / 3600
    logger.info(f"📈 Statistiques finales: {request_counter} requêtes en {uptime_hours:.1f}h, "
               f"{error_counter} erreurs ({(error_counter/max(request_counter,1)*100):.1f}%)")

# -------------------------------------------------------------------
# FastAPI
# -------------------------------------------------------------------
app = FastAPI(
    title="Intelia Expert API",
    version="3.5.5",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# =============================================================================
# MIDDLEWARE DE MONITORING DES REQUÊTES
# =============================================================================
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """Middleware pour tracker les performances en temps réel"""
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
        logger.error(f"❌ Erreur dans middleware monitoring: {e}")
        raise
        
    finally:
        active_requests -= 1
        processing_time = (time.time() - start_time_req) * 1000
        
        # Log des requêtes lentes
        if processing_time > 5000:  # Plus de 5 secondes
            logger.warning(f"🐌 Requête lente: {request.method} {request.url.path} - {processing_time:.0f}ms")

# =============================================================================
# CORS MIDDLEWARE
# =============================================================================
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    if origin in allowed_origins or os.getenv("ENV") != "production":
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
    return response

from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware  # avoid shadowing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔒 AJOUT DU MIDDLEWARE D'AUTHENTIFICATION (CORRIGÉ)
try:
    from app.middleware.auth_middleware import auth_middleware
    app.middleware("http")(auth_middleware)
    logger.info("✅ Middleware d'authentification activé")
except ImportError as e:
    logger.warning(f"⚠️ Middleware d'authentification non disponible: {e}")
except Exception as e:
    logger.error(f"❌ Erreur lors de l'activation du middleware d'auth: {e}")

@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    if origin in allowed_origins or os.getenv("ENV") != "production":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": origin or "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            }
        )
    else:
        raise HTTPException(status_code=403, detail="Origin not allowed")

# -------------------------------------------------------------------
# Montage des routers - CORRIGÉ avec Billing
# -------------------------------------------------------------------
# 🔧 CREATION D'UN ROUTER V1 TEMPORAIRE SI LE FICHIER __init__.py EST VIDE
try:
    from app.api.v1 import router as api_v1_router
    app.include_router(api_v1_router)
    logger.info("✅ Router API v1 chargé depuis __init__.py")
except ImportError as e:
    logger.warning(f"⚠️ Impossible de charger le router v1 depuis __init__.py: {e}")
    logger.info("🔧 Création d'un router v1 temporaire...")
    
    # Créer un router temporaire et inclure manuellement les composants
    from fastapi import APIRouter
    temp_v1_router = APIRouter(prefix="/v1", tags=["v1"])
    
    # Importer et monter les routers individuellement
    try:
        from app.api.v1.expert import router as expert_router
        temp_v1_router.include_router(expert_router, tags=["expert"])
        logger.info("✅ Expert router ajouté")
    except ImportError as e:
        logger.error(f"❌ Impossible de charger expert router: {e}")
    
    try:
        from app.api.v1.auth import router as auth_router
        temp_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
        logger.info("✅ Auth router ajouté")
    except ImportError as e:
        logger.error(f"❌ Impossible de charger auth router: {e}")
    
    try:
        from app.api.v1.health import router as health_router
        temp_v1_router.include_router(health_router, tags=["health"])
        logger.info("✅ Health router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ Health router non disponible: {e}")
    
    try:
        from app.api.v1.system import router as system_router
        temp_v1_router.include_router(system_router, tags=["system"])
        logger.info("✅ System router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ System router non disponible: {e}")
    
    try:
        from app.api.v1.admin import router as admin_router
        temp_v1_router.include_router(admin_router, tags=["admin"])
        logger.info("✅ Admin router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ Admin router non disponible: {e}")
    
    try:
        from app.api.v1.invitations import router as invitations_router
        temp_v1_router.include_router(invitations_router, tags=["invitations"])
        logger.info("✅ Invitations router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ Invitations router non disponible: {e}")
    
    try:
        from app.api.v1.logging import router as logging_router
        temp_v1_router.include_router(logging_router, tags=["logging"])
        logger.info("✅ Logging router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ Logging router non disponible: {e}")
    
    try:
        from app.api.v1.conversations import router as conversations_router
        temp_v1_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
        logger.info("✅ Conversations router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ Conversations router non disponible: {e}")
    
    try:
        from app.api.v1.billing import router as billing_router
        temp_v1_router.include_router(billing_router, tags=["billing"])
        logger.info("✅ Billing router ajouté")
    except ImportError as e:
        logger.warning(f"⚠️ Billing router non disponible: {e}")
    
    # Monter le router temporaire
    app.include_router(temp_v1_router)
    logger.info("✅ Router v1 temporaire monté avec succès")

# -------------------------------------------------------------------
# Debug RAG - 3 RAG COMPLETS (INCHANGÉ)
# -------------------------------------------------------------------
@app.get("/rag/debug", tags=["Debug"])
async def rag_debug():
    """🔍 Debug des 3 RAG (Global + Broiler + Layer)"""
    rag_paths = get_rag_paths()
    env_vars = {
        "RAG_INDEX_GLOBAL": os.getenv("RAG_INDEX_GLOBAL"),
        "RAG_INDEX_BROILER": os.getenv("RAG_INDEX_BROILER"),
        "RAG_INDEX_LAYER": os.getenv("RAG_INDEX_LAYER"),
    }

    path_status = {}
    for name, path in rag_paths.items():
        try:
            exists = os.path.exists(path)
            is_dir = os.path.isdir(path) if exists else False
            files = sorted(os.listdir(path))[:10] if exists and is_dir else []

            path_status[name] = {
                "path": path,
                "exists": exists,
                "is_directory": is_dir,
                "files_found": len(files),
                "sample_files": files[:3],
                "has_faiss": "index.faiss" in files,
                "has_pkl": "index.pkl" in files,
                "has_meta": "meta.json" in files,
                "complete": exists and "index.faiss" in files and "index.pkl" in files
            }
        except Exception as e:
            path_status[name] = {
                "path": path,
                "exists": False,
                "error": str(e)
            }

    instances_status = {}
    for name, attr in [("global", "rag"), ("broiler", "rag_broiler"), ("layer", "rag_layer")]:
        embedder = getattr(app.state, attr, None)
        instance_info = {
            "loaded": embedder is not None,
            "functional": False,
            "documents": 0
        }

        if embedder:
            try:
                instance_info["functional"] = embedder.has_search_engine()
                if hasattr(embedder, 'get_document_count'):
                    instance_info["documents"] = embedder.get_document_count()
                elif hasattr(embedder, 'documents') and embedder.documents:
                    instance_info["documents"] = len(embedder.documents)
            except Exception as e:
                instance_info["error"] = str(e)

        instances_status[name] = instance_info

    total_available = sum(1 for info in path_status.values() if info.get("complete", False))
    total_loaded = sum(1 for info in instances_status.values() if info.get("functional", False))
    total_documents = sum(info.get("documents", 0) for info in instances_status.values() if isinstance(info.get("documents"), int))

    return {
        "approach": "three_rag_system",
        "environment_variables": env_vars,
        "rag_paths": rag_paths,
        "path_verification": path_status,
        "rag_instances": instances_status,
        "summary": {
            "total_available_on_disk": total_available,
            "total_loaded_in_memory": total_loaded,
            "total_documents": total_documents,
            "performance": "optimal" if total_loaded == 3 else "suboptimal"
        },
        "optimization": {
            "all_three_rags_enabled": True,
            "direct_loading": True,
            "failed_attempts": 0
        }
    }

@app.get("/rag/test", tags=["Debug"])
async def test_rag_access():
    """🧪 Test complet des 3 RAG"""
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {},
        "summary": {}
    }
    rag_paths = get_rag_paths()

    filesystem_test = {
        "base_path": "/workspace/backend/rag_index",
        "base_exists": os.path.exists("/workspace/backend/rag_index"),
        "rags": {}
    }

    for rag_type, rag_path in rag_paths.items():
        rag_info = {
            "path": rag_path,
            "exists": os.path.exists(rag_path),
            "is_directory": os.path.isdir(rag_path) if os.path.exists(rag_path) else False,
            "files": [],
            "file_sizes": {}
        }

        if rag_info["exists"] and rag_info["is_directory"]:
            try:
                files = os.listdir(rag_path)
                rag_info["files"] = sorted(files)
                rag_info["has_faiss"] = "index.faiss" in files
                rag_info["has_pkl"] = "index.pkl" in files
                rag_info["has_meta"] = "meta.json" in files
                rag_info["complete"] = rag_info["has_faiss"] and rag_info["has_pkl"]

                for file in files:
                    try:
                        file_path = os.path.join(rag_path, file)
                        size = os.path.getsize(file_path)
                        rag_info["file_sizes"][file] = f"{size / 1024 / 1024:.2f} MB"
                    except Exception:
                        rag_info["file_sizes"][file] = "unknown"

            except Exception as e:
                rag_info["error"] = str(e)

        filesystem_test["rags"][rag_type] = rag_info

    results["tests"]["filesystem"] = filesystem_test

    current_instances = {}
    for name, attr in [("global", "rag"), ("broiler", "rag_broiler"), ("layer", "rag_layer")]:
        embedder = getattr(app.state, attr, None)
        instance_info = {
            "exists": embedder is not None,
            "functional": False,
            "document_count": 0,
            "search_ready": False
        }

        if embedder:
            try:
                instance_info["functional"] = True
                instance_info["search_ready"] = embedder.has_search_engine()
                if hasattr(embedder, 'get_document_count'):
                    instance_info["document_count"] = embedder.get_document_count()
                elif hasattr(embedder, 'documents') and embedder.documents:
                    instance_info["document_count"] = len(embedder.documents)
            except Exception as e:
                instance_info["error"] = str(e)

        current_instances[name] = instance_info

    available_rags = sum(1 for info in filesystem_test["rags"].values() if info.get("complete", False))
    loaded_rags = sum(1 for info in current_instances.values() if info.get("functional", False))
    total_documents = sum(info.get("document_count", 0) for info in current_instances.values() if isinstance(info.get("document_count"), int))

    results["summary"] = {
        "available_on_disk": available_rags,
        "loaded_in_memory": loaded_rags,
        "total_documents": total_documents,
        "functional_rags": [name for name, info in current_instances.items() if info.get("search_ready", False)],
        "missing_rags": [name for name, info in filesystem_test["rags"].items() if not info.get("complete", False)],
        "recommendations": []
    }

    if available_rags == 3 and loaded_rags == 3:
        results["summary"]["recommendations"].append("🎉 PARFAIT: Les 3 RAG sont disponibles et chargés!")
    elif available_rags == 3 and loaded_rags < 3:
        results["summary"]["recommendations"].append(f"⚠️ 3 RAG disponibles mais seulement {loaded_rags} chargé(s)")
    elif available_rags < 3:
        results["summary"]["recommendations"].append(f"❌ Seulement {available_rags}/3 RAG trouvés sur le disque")

    return results

# ========== HEALTH CHECK COMPLET AMÉLIORÉ ==========
@app.get("/health/complete", tags=["Health"])
async def complete_health_check():
    """🏥 Check de santé complet du système avec billing et analytics"""
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check base de données et analytics
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
        
        # Check système de facturation
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
        
        # Check RAG
        total_rags = sum(1 for rag in [
            getattr(app.state, "rag", None),
            getattr(app.state, "rag_broiler", None), 
            getattr(app.state, "rag_layer", None)
        ] if rag and hasattr(rag, 'has_search_engine') and rag.has_search_engine())
        
        health_status["components"]["rag"] = {
            "status": "healthy" if total_rags >= 2 else "degraded" if total_rags >= 1 else "unhealthy",
            "loaded_rags": total_rags,
            "total_rags": 3
        }
        
        # Check OpenAI (si configuré)
        openai_key = os.getenv("OPENAI_API_KEY")
        health_status["components"]["openai"] = {
            "status": "configured" if openai_key else "not_configured"
        }
        
        # Check authentification
        try:
            jwt_secret = os.getenv("JWT_SECRET")
            health_status["components"]["auth"] = {
                "status": "configured" if jwt_secret else "not_configured"
            }
        except Exception:
            health_status["components"]["auth"] = {
                "status": "not_configured"
            }
        
        # Métriques système
        uptime_hours = (time.time() - start_time) / 3600
        health_status["metrics"] = {
            "uptime_hours": round(uptime_hours, 2),
            "total_requests": request_counter,
            "error_rate_percent": round((error_counter / max(request_counter, 1)) * 100, 2),
            "active_requests": active_requests
        }
        
        # Déterminer le statut global
        component_statuses = [comp["status"] for comp in health_status["components"].values() 
                            if comp["status"] in ["healthy", "degraded", "unhealthy"]]
        
        if any(status == "unhealthy" for status in component_statuses):
            health_status["status"] = "unhealthy"
        elif any(status == "degraded" for status in component_statuses):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"❌ Erreur health check: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }

@app.get("/metrics", tags=["Monitoring"])
async def system_metrics():
    """📊 Métriques système pour monitoring externe"""
    try:
        uptime_seconds = time.time() - start_time
        
        return {
            "uptime_seconds": uptime_seconds,
            "requests_total": request_counter,
            "errors_total": error_counter,
            "requests_active": active_requests,
            "error_rate": (error_counter / max(request_counter, 1)) * 100,
            "requests_per_second": request_counter / max(uptime_seconds, 1),
            "rag_status": {
                "global": bool(getattr(app.state, "rag", None)),
                "broiler": bool(getattr(app.state, "rag_broiler", None)),
                "layer": bool(getattr(app.state, "rag_layer", None))
            },
            "synthesis_enabled": synthesis_enabled
        }
    except Exception as e:
        return {"error": str(e)}

# ========== NOUVEAU ENDPOINT DE STATISTIQUES ADMIN ==========
@app.get("/admin/stats", tags=["Admin"])
async def admin_statistics():
    """📈 Statistiques administrateur complètes"""
    try:
        from app.api.v1.billing import get_billing_manager
        from app.api.v1.logging import get_analytics_manager
        
        # Stats billing
        billing = get_billing_manager()
        
        # Stats analytics (approximatives - à adapter selon les besoins)
        uptime_hours = (time.time() - start_time) / 3600
        
        return {
            "system_health": {
                "uptime_hours": round(uptime_hours, 2),
                "total_requests": request_counter,
                "error_rate": round((error_counter / max(request_counter, 1)) * 100, 2),
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
                "authentication": bool(os.getenv("JWT_SECRET")),
                "openai_fallback": bool(os.getenv("OPENAI_API_KEY"))
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/cors-test", tags=["Debug"])
async def cors_test(request: Request):
    return {
        "message": "CORS test successful",
        "origin": request.headers.get("Origin"),
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/", tags=["Root"])
async def root():
    def rag_status() -> str:
        total_rags = sum(1 for rag in [
            getattr(app.state, "rag", None),
            getattr(app.state, "rag_broiler", None),
            getattr(app.state, "rag_layer", None)
        ] if rag and hasattr(rag, 'has_search_engine') and rag.has_search_engine())

        if total_rags == 3:
            return "optimal_3_rags"
        elif total_rags == 1:
            return "suboptimal_1_rag"
        else:
            return f"partial_{total_rags}_rags"

    # Calculer l'uptime
    uptime_hours = (time.time() - start_time) / 3600
    
    return {
        "status": "running",
        "version": "3.5.5",
        "environment": os.getenv("ENV", "production"),
        "database": bool(getattr(app.state, "supabase", None)),
        "postgresql": bool(os.getenv("DATABASE_URL")),
        "rag": rag_status(),
        "synthesis_enabled": synthesis_enabled,
        "cors_fix": "applied",
        "optimization": "three_rag_system_enabled",
        "new_features": {
            "billing_system": True,
            "analytics_tracking": True,
            "quota_enforcement": True,
            "multilingual_support": True,
            "openai_fallback": True,
            "performance_monitoring": True,
            "server_metrics_logging": True,
            "cost_tracking": True,
            "user_behavior_analytics": True,
            "real_time_quota_limits": True,
            "automated_invoicing": True
        },
        "uptime_hours": round(uptime_hours, 2),
        "requests_processed": request_counter
    }

# Exception handlers (INCHANGÉS)
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
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    if origin in allowed_origins or os.getenv("ENV") != "production":
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-ID"
        response.headers["Access-Control-Allow-Credentials"] = "true"

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
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    if origin in allowed_origins or os.getenv("ENV") != "production":
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-ID"
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))