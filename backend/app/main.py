# app/main.py - VERSION 4.0 AVEC SYSTÈME DE CACHE STATISTIQUES INTÉGRÉ
# ✅ CONSERVATION INTÉGRALE DU CODE ORIGINAL + AJOUTS CACHE SAFE
# 🚀 NOUVEAU: Système de cache statistiques automatique
# 🔧 CORRECTION CORS POUR CREDENTIALS: 'INCLUDE' - VERSION FINALE CONSERVÉE
# 🎯 FIX: Ajout du router stats_admin manquant + lifespan corrigé

# tout en haut du fichier
import os
from pathlib import Path

def _rag_index_dir(name: str) -> str:
    """
    Résout le chemin de l'index RAG pour un espace donné.
    Priorité:
      1) ENV RAG_INDEX_DIR_<NAME> (ex: RAG_INDEX_DIR_GLOBAL)
      2) défaut /workspace/backend/rag_index/<name>
    """
    return os.getenv(f"RAG_INDEX_DIR_{name.upper()}", f"/workspace/backend/rag_index/{name}")

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# === LOGGING GLOBAL ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

# === CONFIG CORS ===
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://expert.intelia.com,https://app.intelia.com,http://localhost:3000").split(",")

app = FastAPI(
    title="Intelia Expert API",
    version="4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# === MIDDLEWARE CORS (conservé) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,      # 🔧 Important pour cookies/sessions
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ROUTERS IMPORTS (inchangés) ===
try:
    from app.api.v1.auth import router as auth_router
    app.include_router(auth_router, prefix="/v1/auth", tags=["auth"])
except Exception as e:
    logger.warning(f"⚠️ Router auth indisponible: {e}")

try:
    from app.api.v1.expert import router as expert_router
    app.include_router(expert_router, prefix="/v1/expert", tags=["expert"])
except Exception as e:
    logger.warning(f"⚠️ Router expert indisponible: {e}")

try:
    from app.api.v1.stats import router as stats_router
    app.include_router(stats_router, prefix="/v1/stats", tags=["stats"])
except Exception as e:
    logger.warning(f"⚠️ Router stats indisponible: {e}")

# Ajout du router d'admin statistiques si présent (conservé)
try:
    from app.api.v1.stats_admin import router as stats_admin_router
    app.include_router(stats_admin_router, prefix="/v1/stats-admin", tags=["stats-admin"])
except Exception as e:
    logger.info(f"ℹ️ Router stats-admin non chargé: {e}")

# === DÉTECTION DU SYSTÈME DE CACHE STATISTIQUES (conservé) ===
STATS_CACHE_AVAILABLE = False
try:
    from app.api.v1.stats_cache import get_stats_cache
    STATS_CACHE_AVAILABLE = True
except Exception as e:
    logger.info(f"ℹ️ Module cache statistiques indisponible: {e}")

# === OUTILS SUPPLÉMENTAIRES (inchangés) ===
def get_rag_paths() -> Dict[str, str]:
    """Conserve l'implémentation originale pour ne rien casser ailleurs."""
    base_path = "/workspace/backend/rag_index"
    return {
        "global": f"{base_path}/global",
        "broiler": f"{base_path}/broiler",
        "layer": f"{base_path}/layer",
    }

# === TÂCHES PÉRIODIQUES (inchangées) ===
async def periodic_monitoring():
    while True:
        try:
            logger.debug("🩺 Healthcheck périodique OK")
        except Exception as e:
            logger.warning(f"⚠️ Monitoring error: {e}")
        await asyncio.sleep(60)

async def periodic_stats_update():
    while True:
        try:
            cache = get_stats_cache()
            cache.refresh_all()
            logger.info("♻️ Cache statistiques régénéré")
        except Exception as e:
            logger.warning(f"⚠️ Échec régénération cache stats: {e}")
        await asyncio.sleep(3600)

# === LIFESPAN CORRIGÉ ===
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========== INITIALISATION AU DÉMARRAGE ==========
    logger.info("🚀 Démarrage de l'application Expert API avec système complet + cache statistiques")

    # ========== INITIALISATION DES SERVICES AMÉLIORÉE (CONSERVÉE) ==========
    try:
        logger.info("📊 Initialisation des services analytics et facturation...")
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info("✅ DATABASE_URL configurée")

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
                logger.info(f"✅ Service billing: {len(billing.plans)} plans chargés")
            except Exception as e:
                logger.warning(f"⚠️ Service billing partiellement disponible: {e}")

            # Cache statistiques (optionnel)
            try:
                if STATS_CACHE_AVAILABLE:
                    cache = get_stats_cache()
                    cache_stats = cache.get_cache_stats()
                    logger.info(f"✅ Cache statistiques initialisé: {cache_stats}")
                else:
                    logger.info("ℹ️ Cache statistiques non initialisé (module absent)")
            except Exception as e:
                logger.info(f"ℹ️ Cache statistiques non initialisé: {e}")

            # Nettoyage sessions
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
        logger.error(f"⌛ Erreur initialisation services: {e}")
        # ne pas bloquer le démarrage

    # ========== SUPABASE ==========
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

    # 🚀 CHARGEMENT DES 3 RAG (CONSERVÉ INTÉGRALEMENT, AVEC FIX)
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
        for key, env_path in env_override.items():
            if env_path and os.path.exists(env_path):
                rag_paths[key] = env_path
                logger.info(f"🔧 Override ENV pour {key}: {env_path}")

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
            global_embedder = FastRAGEmbedder(index_dir=global_path, debug=True, cache_embeddings=True, max_workers=2)
            if hasattr(global_embedder, "has_search_engine") and global_embedder.has_search_engine():
                app.state.rag = global_embedder
                _log_loaded("global", global_path, global_embedder)
            else:
                logger.error(f"⌛ RAG Global: Échec chargement depuis {global_path}")
        else:
            logger.error(f"⌛ RAG Global: Chemin inexistant {global_path}")

        # 🚀 BROILER
        broiler_path = rag_paths["broiler"]
        logger.info(f"🔍 Chargement RAG Broiler: {broiler_path}")
        if os.path.exists(broiler_path):
            try:
                broiler_embedder = FastRAGEmbedder(index_dir=broiler_path, debug=False, cache_embeddings=True, max_workers=2)
                if hasattr(broiler_embedder, "has_search_engine") and broiler_embedder.has_search_engine():
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
                layer_embedder = FastRAGEmbedder(index_dir=layer_path, debug=False, cache_embeddings=True, max_workers=2)
                if hasattr(layer_embedder, "has_search_engine") and layer_embedder.has_search_engine():
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
            "global": "✅ Actif" if app.state.rag else "⌛ CRITIQUE",
            "broiler": "✅ Actif" if app.state.rag_broiler else "⌛ Absent",
            "layer": "✅ Actif" if app.state.rag_layer else "⌛ Absent",
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
        logger.error("⌛ Erreur critique initialisation RAG: %s", e)

    # ========== DÉMARRAGE DU MONITORING & SCHEDULER (inchangé) ==========
    monitoring_task = None
    stats_scheduler_task = None
    
    try:
        monitoring_task = asyncio.create_task(periodic_monitoring())
        logger.info("📊 Monitoring périodique démarré")
    except Exception as e:
        logger.error(f"⌛ Erreur démarrage monitoring: {e}")

    if STATS_CACHE_AVAILABLE:
        try:
            stats_scheduler_task = asyncio.create_task(periodic_stats_update())
            logger.info("🔄 Scheduler cache statistiques démarré (mise à jour toutes les heures)")
        except Exception as e:
            logger.error(f"⌛ Erreur démarrage scheduler cache: {e}")
    else:
        logger.info("ℹ️ Scheduler cache statistiques désactivé (module non disponible)")

    # ========== L'APPLICATION DÉMARRE ==========
    system_features = []
    if STATS_CACHE_AVAILABLE:
        system_features.append("cache statistiques optimisé")
    system_features.extend(["3 RAG", "monitoring", "analytics", "billing"])
    logger.info(f"🎯 Application Expert API prête avec: {', '.join(system_features)}")
    yield  # --- L'APPLICATION FONCTIONNE ---

    # ========== NETTOYAGE ==========
    logger.info("🛑 Arrêt de l'application Expert API")
    if monitoring_task:
        try:
            monitoring_task.cancel()
            logger.info("📊 Monitoring périodique arrêté")
        except Exception as e:
            logger.error(f"⌛ Erreur arrêt monitoring: {e}")
    if stats_scheduler_task:
        try:
            stats_scheduler_task.cancel()
            logger.info("🔄 Scheduler cache statistiques arrêté")
        except Exception as e:
            logger.error(f"⌛ Erreur arrêt scheduler cache: {e}")

# === REGISTRATION DU LIFESPAN ===
app.router.lifespan_context = lifespan

# === ENDPOINT DE DEBUG RAG (conservé) ===
@app.get("/rag/debug")
def rag_debug():
    try:
        env_vars = {
            # nouveaux noms conseillés (déjà supportés par _rag_index_dir si tu les utilises)
            "RAG_INDEX_DIR_GLOBAL": os.getenv("RAG_INDEX_DIR_GLOBAL"),
            "RAG_INDEX_DIR_BROILER": os.getenv("RAG_INDEX_DIR_BROILER"),
            "RAG_INDEX_DIR_LAYER": os.getenv("RAG_INDEX_DIR_LAYER"),
            # compat héritée
            "RAG_INDEX_GLOBAL": os.getenv("RAG_INDEX_GLOBAL"),
            "RAG_INDEX_BROILER": os.getenv("RAG_INDEX_BROILER"),
            "RAG_INDEX_LAYER": os.getenv("RAG_INDEX_LAYER"),
        }
        rag_status = {
            "global": bool(getattr(app.state, "rag", None)),
            "broiler": bool(getattr(app.state, "rag_broiler", None)),
            "layer": bool(getattr(app.state, "rag_layer", None)),
        }
        return {"env": env_vars, "status": rag_status}
    except Exception as e:
        return {"error": str(e)}

# === HEALTHCHECK (conservé) ===
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# === MIDDLEWARE CORS FIX HEADERS (conservé) ===
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response: Response = await call_next(request)
    origin = request.headers.get("origin")
    allowed_origins = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

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