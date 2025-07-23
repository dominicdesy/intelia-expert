"""
Intelia Expert API - CORRECTED RAG Path
File: backend/app/main.py
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORRECTED: RAG path calculation for DigitalOcean workspace structure
current_dir = os.path.dirname(os.path.abspath(__file__))
logger.info(f"🔍 Current backend app directory: {current_dir}")

# DigitalOcean structure: /workspace/backend/app/ -> /workspace/rag/
# Go up 2 levels: backend/app/ -> backend/ -> workspace/, then to rag/
workspace_root = os.path.join(current_dir, '..', '..')
workspace_root = os.path.abspath(workspace_root)
rag_path = os.path.join(workspace_root, 'rag')

logger.info(f"🔍 Calculated workspace root: {workspace_root}")
logger.info(f"🔍 Looking for RAG system at: {rag_path}")

if os.path.exists(rag_path):
    sys.path.insert(0, rag_path)
    logger.info(f"✅ RAG path added to sys.path: {rag_path}")
    
    # List RAG files for debugging
    try:
        rag_files = [f for f in os.listdir(rag_path) if f.endswith('.py')]
        logger.info(f"📁 RAG Python files found: {rag_files}")
    except Exception as e:
        logger.error(f"❌ Cannot list RAG directory: {e}")
else:
    logger.error(f"❌ RAG directory not found at: {rag_path}")
    # Try alternative paths
    alternative_paths = [
        "/workspace/rag",
        os.path.join(os.getcwd(), "rag"),
        os.path.join(os.getcwd(), "..", "rag")
    ]
    for alt_path in alternative_paths:
        if os.path.exists(alt_path):
            logger.info(f"🔍 Found RAG at alternative path: {alt_path}")
            rag_path = alt_path
            sys.path.insert(0, rag_path)
            break

# FastAPI app
app = FastAPI(
    title="Intelia Expert API",
    description="Assistant IA spécialisé en santé et nutrition animale",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test RAG imports with detailed error handling
rag_modules_available = {}

def test_rag_import(module_name):
    """Test individual RAG module import"""
    try:
        if module_name == "intelligent_retriever":
            from intelligent_retriever import IntelligentRetriever
            rag_modules_available[module_name] = True
            logger.info(f"✅ Successfully imported {module_name}")
            return True
    except ImportError as e:
        logger.warning(f"⚠️ Could not import {module_name}: {e}")
        rag_modules_available[module_name] = False
        return False
    except Exception as e:
        logger.error(f"❌ Error importing {module_name}: {e}")
        rag_modules_available[module_name] = False
        return False

def test_rag_launch_script():
    """Test RAG launch script import"""
    try:
        from launch_script import RAGSystem
        rag_modules_available["launch_script"] = True
        logger.info("✅ Successfully imported launch_script")
        return True
    except ImportError as e:
        logger.warning(f"⚠️ Could not import launch_script: {e}")
        rag_modules_available["launch_script"] = False
        return False
    except Exception as e:
        logger.error(f"❌ Error importing launch_script: {e}")
        rag_modules_available["launch_script"] = False
        return False

# Test all RAG imports
test_rag_import("intelligent_retriever")
test_rag_launch_script()

# Import routers with better error handling
try:
    from app.api.v1 import expert, auth, admin, health, system
    logger.info("✅ All API routers imported successfully")
except ImportError as e:
    logger.error(f"❌ Router import error: {e}")

# Basic endpoints
@app.get("/")
def read_root():
    return {
        "message": "Intelia Expert API",
        "status": "Production Ready - RAG Integration",
        "version": "0.1.0",
        "rag_status": rag_modules_available,
        "workspace_info": {
            "workspace_root": workspace_root,
            "rag_path": rag_path,
            "rag_exists": os.path.exists(rag_path)
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "expert": "/api/v1/expert/ask",
            "system": "/api/v1/system/health",
            "rag_debug": "/api/v1/debug/rag"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "intelia-expert-backend",
        "rag_system": "checking",
        "rag_modules": rag_modules_available,
        "timestamp": "2025-07-23"
    }

# Debug endpoint for RAG system
@app.get("/api/v1/debug/rag")
def debug_rag():
    """Debug RAG system status with detailed path info"""
    
    # Check multiple possible RAG locations
    possible_paths = [
        rag_path,
        "/workspace/rag",
        os.path.join(os.getcwd(), "rag"),
        os.path.join(os.getcwd(), "..", "rag"),
        os.path.join(os.getcwd(), "..", "..", "rag")
    ]
    
    path_status = {}
    for path in possible_paths:
        path_status[path] = {
            "exists": os.path.exists(path),
            "files": []
        }
        if os.path.exists(path):
            try:
                files = [f for f in os.listdir(path) if f.endswith('.py')]
                path_status[path]["files"] = files
            except:
                path_status[path]["files"] = ["error_reading_directory"]
    
    return {
        "rag_path": rag_path,
        "rag_path_exists": os.path.exists(rag_path),
        "rag_modules_status": rag_modules_available,
        "sys_path_rag": rag_path in sys.path,
        "current_working_directory": os.getcwd(),
        "backend_app_directory": current_dir,
        "workspace_root": workspace_root,
        "all_possible_paths": path_status,
        "sys_path": sys.path[:5]  # First 5 entries
    }

# Include API routers with error handling
def include_router_safely(router, prefix, tags, name):
    """Safely include router with error handling"""
    try:
        app.include_router(router, prefix=prefix, tags=tags)
        logger.info(f"✅ {name} router included successfully")
        return True
    except Exception as e:
        logger.error(f"❌ {name} router error: {e}")
        return False

# Include routers
include_router_safely(expert.router, "/api/v1/expert", ["Expert RAG System"], "Expert")
include_router_safely(auth.router, "/api/v1/auth", ["Authentication"], "Auth")
include_router_safely(admin.router, "/api/v1/admin", ["Administration"], "Admin")
include_router_safely(system.router, "/api/v1/system", ["System"], "System")

# Health check with detailed status
@app.get("/api/v1/status")
def detailed_status():
    """Detailed system status including RAG diagnostics"""
    try:
        return {
            "api_status": "running",
            "rag_system": {
                "path": rag_path,
                "exists": os.path.exists(rag_path),
                "available": rag_modules_available,
                "total_modules": len(rag_modules_available),
                "working_modules": sum(rag_modules_available.values())
            },
            "workspace": {
                "root": workspace_root,
                "current_dir": os.getcwd(),
                "backend_dir": current_dir
            },
            "endpoints_loaded": {
                "expert": "/api/v1/expert/ask",
                "feedback": "/api/v1/expert/feedback", 
                "history": "/api/v1/expert/history",
                "auth": "/api/v1/auth/login",
                "admin": "/api/v1/admin/dashboard"
            },
            "environment": {
                "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
                "claude_key_set": bool(os.getenv("CLAUDE_API_KEY")),
                "working_directory": os.getcwd()
            }
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"api_status": "error", "error": str(e)}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "message": "Check /docs for available endpoints",
            "debug": "Try /api/v1/debug/rag for RAG diagnostics"
        }
    )

# Startup event with detailed RAG diagnostics
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Intelia Expert API starting up...")
    logger.info(f"📊 RAG system diagnostics:")
    logger.info(f"   - Current directory: {os.getcwd()}")
    logger.info(f"   - Backend app directory: {current_dir}")
    logger.info(f"   - Workspace root: {workspace_root}")
    logger.info(f"   - RAG path: {rag_path}")
    logger.info(f"   - RAG path exists: {os.path.exists(rag_path)}")
    logger.info(f"   - Available modules: {rag_modules_available}")
    
    if os.path.exists(rag_path):
        try:
            files = [f for f in os.listdir(rag_path) if f.endswith('.py')]
            logger.info(f"   - Python files in RAG: {files}")
        except Exception as e:
            logger.error(f"   - Error reading RAG directory: {e}")
    
    logger.info("🎯 Intelia Expert API ready!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "false") == "true",
        log_level="info"
    )
