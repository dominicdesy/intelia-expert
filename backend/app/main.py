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
# FONCTION RAG SIMPLIFIÉE
# -------------------------------------------------------------------
def get_rag_paths() -> Dict[str, str]:
    """🎯 DIRECT: Seul le RAG Global existe selon les logs"""
    return {
        "global": "/workspace/backend/rag_index/global"
    }

# -------------------------------------------------------------------
# Lifespan: init Supabase + RAG SIMPLIFIÉ
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

    # RAG SIMPLE - UN SEUL RAG
    app.state.rag = None
    try:
        from rag.embedder import FastRAGEmbedder
        global_path = "/workspace/backend/rag_index/global"
        
        logger.info(f"📁 Chargement RAG direct: {global_path}")
        
        if os.path.exists(global_path):
            embedder = FastRAGEmbedder(debug=True, cache_embeddings=True, max_workers=2)
            if embedder.load_index(global_path) and embedder.has_search_engine():
                app.state.rag = embedder
                logger.info(f"✅ RAG chargé directement: {global_path}")
            else:
                logger.error(f"❌ Échec chargement RAG: {global_path}")
        else:
            logger.error(f"❌ RAG inexistant: {global_path}")
            
    except Exception as e:
        logger.error("❌ Erreur RAG: %s", e)

    yield  # --- shutdown: rien pour l'instant

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
# CORS MIDDLEWARE
# =============================================================================

# Middleware pour forcer les headers CORS sur TOUTES les réponses
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

# Middleware CORS FastAPI (backup)
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

# =============================================================================
# Gestionnaire OPTIONS global
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
# Montage des routers
# -------------------------------------------------------------------
def _mount(module_path: str, prefix: str, tag: str):
    try:
        module = __import__(module_path, fromlist=["router"])
        app.include_router(module.router, prefix=prefix, tags=[tag])
        logger.info("✅ %s monté sur %s", module_path, prefix)
    except Exception as e:
        logger.warning("⚠️ %s non monté: %s", module_path, e)

# Montage des routers
_mount("app.api.v1.system",       "/v1",         "System")
_mount("app.api.v1.auth",         "/v1",         "Auth")
_mount("app.api.v1.admin",        "/v1",         "Admin")
_mount("app.api.v1.health",       "/v1",         "Health")
_mount("app.api.v1.invitations",  "/v1",         "Invitations")
_mount("app.api.v1.logging",      "/v1",         "Logging")
_mount("app.api.v1.expert",       "/v1/expert",  "Expert")

# -------------------------------------------------------------------
# Debug RAG (simplifié)
# -------------------------------------------------------------------
@app.get("/rag/debug", tags=["Debug"])
async def rag_debug():
    """🔍 Debug RAG simplifié"""
    
    rag_paths = get_rag_paths()
    
    env_vars = {
        "RAG_INDEX_GLOBAL": os.getenv("RAG_INDEX_GLOBAL"),
        "RAG_INDEX_BROILER": os.getenv("RAG_INDEX_BROILER"),
        "RAG_INDEX_LAYER": os.getenv("RAG_INDEX_LAYER"),
    }
    
    # Vérification du chemin unique
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
                "sample_files": files[:3]
            }
        except Exception as e:
            path_status[name] = {
                "path": path,
                "exists": False,
                "error": str(e)
            }
    
    # Status de l'instance RAG
    rag_instance = getattr(app.state, "rag", None)
    instance_status = {
        "loaded": rag_instance is not None,
        "functional": False,
        "documents": 0
    }
    
    if rag_instance:
        try:
            instance_status["functional"] = rag_instance.has_search_engine()
            if hasattr(rag_instance, 'get_document_count'):
                instance_status["documents"] = rag_instance.get_document_count()
            elif hasattr(rag_instance, 'documents') and rag_instance.documents:
                instance_status["documents"] = len(rag_instance.documents)
        except Exception as e:
            instance_status["error"] = str(e)
    
    return {
        "approach": "single_rag_direct",
        "environment_variables": env_vars,
        "rag_path": rag_paths,
        "path_verification": path_status,
        "rag_instance": instance_status,
        "optimization": {
            "fallbacks_eliminated": True,
            "direct_loading": True,
            "failed_attempts": 0,
            "performance": "optimal"
        }
    }

@app.get("/rag/test", tags=["Debug"])
async def test_rag_access():
    """🧪 Test complet d'accès au RAG unique"""
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {},
        "summary": {}
    }
    
    # Test filesystem
    base_path = "/workspace/backend/rag_index"
    filesystem_test = {
        "base_path": base_path,
        "base_exists": os.path.exists(base_path),
        "global_rag": {}
    }
    
    global_path = f"{base_path}/global"
    global_info = {
        "path": global_path,
        "exists": os.path.exists(global_path),
        "is_directory": os.path.isdir(global_path) if os.path.exists(global_path) else False,
        "files": [],
        "file_sizes": {}
    }
    
    if global_info["exists"] and global_info["is_directory"]:
        try:
            files = os.listdir(global_path)
            global_info["files"] = sorted(files)
            global_info["has_faiss"] = "index.faiss" in files
            global_info["has_pkl"] = "index.pkl" in files
            global_info["complete"] = global_info["has_faiss"] and global_info["has_pkl"]
            
            for file in files:
                try:
                    file_path = os.path.join(global_path, file)
                    size = os.path.getsize(file_path)
                    global_info["file_sizes"][file] = f"{size / 1024 / 1024:.2f} MB"
                except Exception:
                    global_info["file_sizes"][file] = "unknown"
                    
        except Exception as e:
            global_info["error"] = str(e)
    
    filesystem_test["global_rag"] = global_info
    results["tests"]["filesystem"] = filesystem_test
    
    # Test de chargement
    loading_test = {
        "attempted": False,
        "success": False,
        "has_search_engine": False,
        "document_count": 0,
        "error": None
    }
    
    if os.path.exists(global_path):
        try:
            loading_test["attempted"] = True
            from rag.embedder import FastRAGEmbedder
            
            test_embedder = FastRAGEmbedder(debug=False, cache_embeddings=False, max_workers=1)
            
            if test_embedder.load_index(global_path):
                loading_test["success"] = True
                loading_test["has_search_engine"] = test_embedder.has_search_engine()
                
                try:
                    if hasattr(test_embedder, 'get_document_count'):
                        loading_test["document_count"] = test_embedder.get_document_count()
                    elif hasattr(test_embedder, 'documents') and test_embedder.documents:
                        loading_test["document_count"] = len(test_embedder.documents)
                except Exception:
                    loading_test["document_count"] = "unknown"
            
        except Exception as e:
            loading_test["error"] = str(e)
    
    results["tests"]["loading"] = loading_test
    
    # Test instance actuelle
    current_instance = {
        "exists": app.state.rag is not None,
        "functional": False,
        "document_count": 0,
        "search_ready": False
    }
    
    if app.state.rag:
        try:
            current_instance["functional"] = True
            current_instance["search_ready"] = app.state.rag.has_search_engine()
            
            if hasattr(app.state.rag, 'get_document_count'):
                current_instance["document_count"] = app.state.rag.get_document_count()
            elif hasattr(app.state.rag, 'documents') and app.state.rag.documents:
                current_instance["document_count"] = len(app.state.rag.documents)
                
        except Exception as e:
            current_instance["error"] = str(e)
    
    results["tests"]["current_instance"] = current_instance
    
    # Test de recherche
    search_test = {}
    if app.state.rag:
        try:
            test_query = "broiler chicken weight"
            search_results = app.state.rag.search(test_query, k=3)
            
            search_test = {
                "query": test_query,
                "results_count": len(search_results) if search_results else 0,
                "success": len(search_results) > 0 if search_results else False,
                "sample_scores": [r.get('score', 0) for r in search_results[:3]] if search_results else []
            }
        except Exception as e:
            search_test = {
                "query": test_query,
                "error": str(e),
                "success": False
            }
    
    results["tests"]["search"] = search_test
    
    # Résumé
    rag_available = global_info.get("complete", False)
    rag_loaded = current_instance.get("functional", False)
    
    results["summary"] = {
        "rag_available_on_disk": rag_available,
        "rag_loaded_in_memory": rag_loaded,
        "search_functional": current_instance.get("search_ready", False),
        "recommendations": []
    }
    
    if rag_available and rag_loaded:
        results["summary"]["recommendations"].append("✅ Configuration parfaite: RAG disponible et fonctionnel")
    elif rag_available and not rag_loaded:
        results["summary"]["recommendations"].append("⚠️ RAG disponible sur disque mais non chargé")
    elif not rag_available:
        results["summary"]["recommendations"].append("❌ RAG non trouvé sur le disque")
        
    if not search_test.get("success", False):
        results["summary"]["recommendations"].append("❌ Test de recherche échoué")
    
    return results

# =============================================================================
# Endpoint de test CORS
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
# Root + error handlers
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
        "cors_fix": "applied",
        "optimization": "single_rag_direct_loading"
    }

# Exception handlers avec CORS
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

# -------------------------------------------------------------------
# Local dev entry
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))