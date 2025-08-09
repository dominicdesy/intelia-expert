# app/main.py
from __future__ import annotations

import os
import logging
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

# -------------------------------------------------------------------
# Lifespan: init Supabase (optionnel) + RAG (ENV + fallbacks)
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Supabase (optionnel)
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

    # RAG
    app.state.rag = None
    try:
        from rag.embedder import FastRAGEmbedder
        emb = FastRAGEmbedder(debug=True, cache_embeddings=True, max_workers=2)

        # 1) Essaye via variables d'env (RAG_INDEX_DIR / RAG_INDEX_GLOBAL ...)
        ready = False
        try:
            if hasattr(emb, "load_from_env"):
                ready = bool(emb.load_from_env())
        except Exception:
            ready = False

        # 2) Fallbacks si ENV non fournie/incorrecte
        if not (ready and emb.has_search_engine()):
            candidate_paths = [
                # racine du repo (DO App Platform: source dir = root)
                "/workspace/rag_index/global",
                # DO App Platform: source dir = backend
                "/workspace/backend/rag_index/global",
                # Exécution Docker (WORKDIR=/app)
                "/app/rag_index/global",
            ]
            for p in candidate_paths:
                if os.path.exists(p) and emb.load_index(p) and emb.has_search_engine():
                    ready = True
                    break

        app.state.rag = emb
        logger.info("✅ RAG prêt" if (ready and emb.has_search_engine()) else "⚠️ RAG en mode fallback (index introuvable)")
    except Exception as e:
        logger.error("❌ RAG non initialisé: %s", e)

    yield  # --- shutdown: rien pour l'instant


# -------------------------------------------------------------------
# FastAPI
# -------------------------------------------------------------------
app = FastAPI(
    title="Intelia Expert API",
    version="3.5.5",
    root_path="/api",   # IMPORTANT: toutes les routes publiées sous /api/...
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# =============================================================================
# 🔥 CORRECTION CORS CRITIQUE
# =============================================================================

# Middleware pour forcer les headers CORS sur TOUTES les réponses
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    # Traiter la requête
    response = await call_next(request)
    
    # Ajouter les headers CORS à TOUTES les réponses
    origin = request.headers.get("Origin")
    allowed_origins = [
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    
    # Vérifier si l'origin est autorisée ou autoriser tout en développement
    if origin in allowed_origins or os.getenv("ENV") != "production":
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
    
    return response

# Middleware CORS FastAPI (backup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
        "*"  # TEMPORAIRE pour debug
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Gestionnaire OPTIONS global pour preflight CORS
# =============================================================================

@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Gestionnaire OPTIONS global pour toutes les routes"""
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
# Montage des routers — tous en /api/v1/... | expert en /api/v1/expert/...
# -------------------------------------------------------------------
def _mount(module_path: str, prefix: str, tag: str):
    try:
        module = __import__(module_path, fromlist=["router"])
        app.include_router(module.router, prefix=prefix, tags=[tag])
        logger.info("✅ %s monté sur %s", module_path, prefix)
    except Exception as e:
        logger.warning("⚠️ %s non monté: %s", module_path, e)

# NOTE: imports ABSOLUS depuis 'app.'
_mount("app.api.v1.system",       "/v1",         "System")
_mount("app.api.v1.auth",         "/v1",         "Auth")
_mount("app.api.v1.admin",        "/v1",         "Admin")
_mount("app.api.v1.health",       "/v1",         "Health")
_mount("app.api.v1.invitations",  "/v1",         "Invitations")
_mount("app.api.v1.logging",      "/v1",         "Logging")
_mount("app.api.v1.expert",       "/v1/expert",  "Expert")   # <- /api/v1/expert/...

# -------------------------------------------------------------------
# Debug RAG (inspection des chemins)
# -------------------------------------------------------------------
@app.get("/rag/debug", tags=["Debug"])
async def rag_debug():
    env = {
        "RAG_INDEX_DIR": os.getenv("RAG_INDEX_DIR"),
        "RAG_INDEX_GLOBAL": os.getenv("RAG_INDEX_GLOBAL"),
        "RAG_INDEX_BROILER": os.getenv("RAG_INDEX_BROILER"),
        "RAG_INDEX_LAYER": os.getenv("RAG_INDEX_LAYER"),
    }
    candidates = [
        env.get("RAG_INDEX_GLOBAL"),
        "/workspace/rag_index/global",
        "/workspace/backend/rag_index/global",
        "/app/rag_index/global",
    ]
    checks: List[Dict[str, Any]] = []
    for p in [c for c in candidates if c]:
        try:
            exists = os.path.exists(p)
            listing = sorted(os.listdir(p))[:10] if exists else []
        except Exception as e:
            exists, listing = False, [f"<error: {e}>"]
        checks.append({"path": p, "exists": exists, "list": listing})
    status = "optimized" if getattr(app.state, "rag", None) and app.state.rag.has_search_engine() else "fallback"
    return {"env": env, "checks": checks, "rag_status": status}

# =============================================================================
# 🔧 CORRECTION: Endpoint de test CORS
# =============================================================================

@app.get("/cors-test", tags=["Debug"])
async def cors_test(request: Request):
    """Endpoint pour tester CORS"""
    return {
        "message": "CORS test successful",
        "origin": request.headers.get("Origin"),
        "user_agent": request.headers.get("User-Agent"),
        "timestamp": datetime.utcnow().isoformat(),
        "headers_received": dict(request.headers)
    }

# -------------------------------------------------------------------
# Root + error handlers avec CORS
# -------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    def rag_status() -> str:
        rag = getattr(app.state, "rag", None)
        try:
            return "optimized" if (rag and rag.has_search_engine()) else "fallback"
        except Exception:
            return "fallback"

    return {
        "status": "running",
        "version": "3.5.5",
        "environment": os.getenv("ENV", "production"),
        "database": bool(getattr(app.state, "supabase", None)),
        "rag": rag_status(),
        "cors_fix": "applied",  # Indicateur que la correction CORS est active
    }

# =============================================================================
# Exception handlers avec CORS forcé
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    # Créer la réponse d'erreur
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat() + "Z"},
        headers={"content-type": "application/json; charset=utf-8"},
    )
    
    # Forcer les headers CORS même sur les erreurs
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
    
    # Créer la réponse d'erreur
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.utcnow().isoformat() + "Z"},
        headers={"content-type": "application/json; charset=utf-8"},
    )
    
    # Forcer les headers CORS même sur les erreurs 500
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

# -------------------------------------------------------------------
# Local dev entry
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))