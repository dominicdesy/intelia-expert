"""
Intelia Expert API - Complete with RAG Integration
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

# Add RAG system to path
rag_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../rag'))
if rag_path not in sys.path:
    sys.path.append(rag_path)

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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
try:
    from app.api.v1 import expert, auth, admin, health, system
    logger.info("✅ All routers imported successfully")
except ImportError as e:
    logger.error(f"❌ Router import error: {e}")
    # Continue without failing - we'll add basic endpoints

# Basic endpoints
@app.get("/")
def read_root():
    return {
        "message": "Intelia Expert API",
        "status": "Production Ready - RAG Enabled",
        "version": "0.1.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "expert": "/api/v1/expert/ask",
            "system": "/api/v1/system/health"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "intelia-expert-backend",
        "rag_system": "enabled",
        "timestamp": "2025-07-23"
    }

# Include API routers
try:
    # Expert endpoints (RAG)
    app.include_router(
        expert.router,
        prefix="/api/v1/expert",
        tags=["Expert RAG System"]
    )
    logger.info("✅ Expert RAG router included")
except Exception as e:
    logger.error(f"❌ Expert router error: {e}")

try:
    # Auth endpoints
    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Authentication"]
    )
    logger.info("✅ Auth router included")
except Exception as e:
    logger.error(f"❌ Auth router error: {e}")

try:
    # Admin endpoints  
    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["Administration"]
    )
    logger.info("✅ Admin router included")
except Exception as e:
    logger.error(f"❌ Admin router error: {e}")

try:
    # System endpoints
    app.include_router(
        system.router,
        prefix="/api/v1/system",
        tags=["System"]
    )
    logger.info("✅ System router included")
except Exception as e:
    logger.error(f"❌ System router error: {e}")

# Health check with detailed status
@app.get("/api/v1/status")
def detailed_status():
    """Detailed system status"""
    try:
        # Check RAG system availability
        rag_status = "unknown"
        try:
            from intelligent_retriever import IntelligentRetriever
            rag_status = "available"
        except ImportError:
            rag_status = "not_found"
        
        return {
            "api_status": "running",
            "rag_system": rag_status,
            "endpoints_loaded": {
                "expert": "/api/v1/expert/ask",
                "feedback": "/api/v1/expert/feedback", 
                "history": "/api/v1/expert/history",
                "auth": "/api/v1/auth/login",
                "admin": "/api/v1/admin/dashboard"
            },
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug": os.getenv("DEBUG", "false") == "true"
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
            "available_endpoints": [
                "/api/v1/expert/ask",
                "/api/v1/expert/feedback",
                "/api/v1/auth/login",
                "/health"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Please check logs or contact support"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Intelia Expert API starting up...")
    logger.info("📊 Checking RAG system availability...")
    
    # Try to initialize RAG system
    try:
        # Test RAG imports
        from intelligent_retriever import IntelligentRetriever
        logger.info("✅ RAG system imports successful")
    except ImportError as e:
        logger.warning(f"⚠️ RAG system import warning: {e}")
    
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
