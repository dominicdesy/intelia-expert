# app/main.py
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env facultatif
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger("app.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _rag_status(obj: Optional[Any]) -> str:
    if not obj:
        return "not_available"
    try:
        return "optimized" if obj.has_search_engine() else "fallback"
    except Exception:
        return "fallback"

def _try_load_rag_indexes(embedder) -> bool:
    """
    Ordre de recherche des index :
      1) Variables d'env (RAG_INDEX_GLOBAL / RAG_INDEX_DIR)
      2) DO Buildpack: /workspace/rag_index/global
      3) Dockerfile:   /app/rag_index/global
    """
    # 1) ENV
    if embedder.load_from_env() and embedder.has_search_engine():
        return True

    # 2) DigitalOcean Buildpack path
    ws_path = "/workspace/rag_index/global"
    if os.path.exists(ws_path):
        logger.info("🔎 Trying DO path: %s", ws_path)
        if embedder.load_index(ws_path) and embedder.has_search_engine():
            return True

    # 3) Docker image path
    app_path = "/app/rag_index/global"
    if os.path.exists(app_path):
        logger.info("🔎 Trying Docker path: %s", app_path)
        if embedder.load_index(app_path) and embedder.has_search_engine():
            return True

    return False

# -----------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Supabase (optionnel)
    try:
        from supabase import create_client
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            app.state.supabase = create_client(url, key)
            logger.info("✅ Supabase prêt")
        else:
            app.state.supabase = None
            logger.info("ℹ️ Supabase non configuré (SUPABASE_URL / SUPABASE_ANON_KEY manquants)")
    except Exception as e:
        app.state.supabase = None
        logger.info("ℹ️ Supabase indisponible: %s", e)

    # RAG
    try:
        from rag.embedder import FastRAGEmbedder
        embedder = FastRAGEmbedder(debug=True, cache_embeddings=True, max_workers=2)
        ready = _try_load_rag_indexes(embedder)
        app.state.rag = embedder
        logger.info("✅ RAG prêt" if ready else "⚠️ RAG en mode fallback (index introuvable)")
    except Exception as e:
        app.state.rag = None
        logger.error("❌ RAG non initialisé: %s", e)

    yield
    # (aucun shutdown spécial)

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Intelia Expert API",
    version="3.5.5",
    root_path="/api",        # docs: /api/docs
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Routers (montage unique via app.api.v1)
# -----------------------------------------------------------------------------
from app.api.v1 import router as api_v1_router
app.include_router(api_v1_router)

# -----------------------------------------------------------------------------
# Root & Health
# -----------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    return {
        "status": "running",
        "version": "3.5.5",
        "environment": os.getenv("ENV", "production"),
        "database": "connected" if getattr(app.state, "supabase", None) else "disconnected",
        "rag": _rag_status(getattr(app.state, "rag", None)),
    }

@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "api": "running",
            "database": "connected" if getattr(app.state, "supabase", None) else "disconnected",
            "rag": _rag_status(getattr(app.state, "rag", None)),
        },
    }

# -----------------------------------------------------------------------------
# Error handlers (simples & UTF-8)
# -----------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat() + "Z"},
        headers={"content-type": "application/json; charset=utf-8"},
    )

@app.exception_handler(Exception)
async def generic_exc_handler(_: Request, exc: Exception):
    logger.exception("Unhandled: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.utcnow().isoformat() + "Z"},
        headers={"content-type": "application/json; charset=utf-8"},
    )

# -----------------------------------------------------------------------------
# Entry point local
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
