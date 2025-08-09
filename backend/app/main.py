# app/main.py
from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env (optionnel)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger("app.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# --- Globals (exposés via app.state) ---
_supabase: Optional[Any] = None
_rag: Optional[Any] = None

# -----------------------------------------------------------------------------
# Lifespan (startup/shutdown)
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase, _rag

    # 1) Supabase (optionnel)
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if url and key:
            _supabase = create_client(url, key)
            logger.info("✅ Supabase prêt")
        else:
            logger.info("ℹ️ Supabase non configuré")
    except Exception as e:
        _supabase = None
        logger.info("ℹ️ Supabase indisponible: %s", e)

    # 2) RAG Embedder
    try:
        from rag.embedder import FastRAGEmbedder
        embedder = FastRAGEmbedder(
            debug=True,               # mets False quand tout est stable
            cache_embeddings=True,
            max_workers=2,
        )
        ready = embedder.load_from_env()  # lit RAG_INDEX_* (Dockerfile)
        _rag = embedder
        logger.info("✅ RAG prêt" if (ready and embedder.has_search_engine()) else "⚠️ RAG en mode fallback")
    except Exception as e:
        _rag = None
        logger.error("❌ RAG non initialisé: %s", e)

    # Expose state pour autres modules/routers
    app.state.supabase = _supabase
    app.state.rag = _rag

    yield

    # (shutdown) — rien de spécial pour l’instant

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Intelia Expert API",
    version="3.5.5",
    root_path="/api",
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
# Routers (montage concis)
# -----------------------------------------------------------------------------
def _mount_router(module_path: str, prefix: str, tag: str):
    try:
        module = __import__(module_path, fromlist=["router"])
        app.include_router(module.router, prefix=prefix, tags=[tag])
        logger.info("✅ %s monté sur %s", module_path, prefix)
    except Exception as e:
        logger.warning("⚠️ %s non monté: %s", module_path, e)

routers = [
    ("api.v1.expert", "/v1/expert", "Expert"),
    ("api.v1.logging", "/v1", "Logging"),
    ("api.v1.auth", "/v1", "Auth"),
    ("api.v1.admin", "/v1", "Admin"),
    ("api.v1.health", "/v1", "Health"),
    ("api.v1.system", "/v1", "System"),
    ("api.v1.invitations", "/v1", "Invitations"),
]
for mod, prefix, tag in routers:
    _mount_router(mod, prefix, tag)

# -----------------------------------------------------------------------------
# Health/root
# -----------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    def rag_status() -> str:
        if not getattr(app.state, "rag", None):
            return "not_available"
        try:
            return "optimized" if app.state.rag.has_search_engine() else "fallback"
        except Exception:
            return "fallback"

    return {
        "status": "running",
        "version": "3.5.5",
        "environment": os.getenv("ENV", "production"),
        "database": bool(getattr(app.state, "supabase", None)),
        "rag": rag_status(),
    }

# -----------------------------------------------------------------------------
# Error handlers (sobres)
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
# Entrée locale (uvicorn)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
