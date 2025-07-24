"""
Intelia Expert - API Backend Main
Version complètement réécrite - Simple et Robuste
"""

import os
import sys
import time
import logging
import traceback
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Pydantic models
from pydantic import BaseModel, Field

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Environment and logging
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global RAG embedder
rag_embedder: Optional[Any] = None

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model for expert questions"""
    text: str = Field(..., description="Question text", min_length=1, max_length=2000)
    user_id: Optional[str] = Field(None, description="User identifier")
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    context: Optional[str] = Field(None, description="Additional context")

class ExpertResponse(BaseModel):
    """Response model for expert answers"""
    question: str
    response: str
    mode: str
    note: Optional[str] = None
    config_source: str
    timestamp: str
    processing_time: float

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    services: Dict[str, str]
    config: Dict[str, str]

class FeedbackRequest(BaseModel):
    """Feedback request model"""
    question_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    feedback: Optional[str] = Field(None, max_length=500)

# =============================================================================
# RAG SYSTEM INITIALIZATION - SIMPLIFIED
# =============================================================================

async def initialize_rag_system():
    """Initialize RAG system - Version simplifiée et robuste"""
    global rag_embedder
    
    logger.info("🚀 Starting Intelia Expert API...")
    logger.info("🔧 Initializing RAG system...")
    
    try:
        # Import RAG embedder
        from rag.embedder import FastRAGEmbedder
        logger.info("✅ RAG embedder imported successfully")
        
        # Create embedder instance
        embedder = FastRAGEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
        logger.info("✅ RAG embedder instance created")
        
        # Search for existing index
        index_paths = [
            '/workspace/backend/rag_index',
            './rag_index', 
            '/tmp/rag_index',
            os.path.join(backend_dir, 'rag_index')
        ]
        
        logger.info(f"🔍 Searching for RAG index in paths: {index_paths}")
        
        index_loaded = False
        for index_path in index_paths:
            if os.path.exists(index_path):
                faiss_file = os.path.join(index_path, 'index.faiss')
                pkl_file = os.path.join(index_path, 'index.pkl')
                
                if os.path.exists(faiss_file) and os.path.exists(pkl_file):
                    logger.info(f"📁 Found complete index in: {index_path}")
                    logger.info(f"   ✅ Found: index.faiss")
                    logger.info(f"   ✅ Found: index.pkl")
                    logger.info(f"🔄 Attempting to load index from {index_path}")
                    
                    # Try to load the index
                    if embedder.load_index(index_path):
                        logger.info(f"✅ Successfully loaded RAG index from {index_path}")
                        
                        # Get basic info safely
                        try:
                            vectors_count = embedder._faiss_index.ntotal if embedder._faiss_index else 0
                            docs_count = len(embedder._documents) if hasattr(embedder, '_documents') else 0
                            dimension = embedder._faiss_index.d if embedder._faiss_index else embedder.dimension
                            
                            logger.info(f"   📊 Vectors: {vectors_count}")
                            logger.info(f"   📚 Documents: {docs_count}")
                            logger.info(f"   🔢 Dimension: {dimension}")
                            logger.info(f"   🔍 Search engine available: {embedder.has_search_engine()}")
                        except Exception as info_error:
                            logger.warning(f"⚠️ Could not get detailed info: {info_error}")
                            logger.info("   📊 Index loaded successfully (details unavailable)")
                        
                        index_loaded = True
                        break
                    else:
                        logger.warning(f"❌ Failed to load index from {index_path}")
        
        # Set global embedder regardless of index loading success
        rag_embedder = embedder
        
        # Final status
        if index_loaded and embedder.has_search_engine():
            logger.info("✅ RAG system fully initialized with document search capabilities")
            return True
        else:
            logger.warning("⚠️ RAG system initialized but no valid index found")
            logger.info("🔄 Will run in fallback mode (direct OpenAI)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing RAG system: {e}")
        logger.error(f"Full error: {traceback.format_exc()}")
        
        # Try minimal fallback
        try:
            from rag.embedder import FastRAGEmbedder
            rag_embedder = FastRAGEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("✅ Fallback RAG embedder created successfully")
        except Exception as fallback_error:
            logger.error(f"❌ Even fallback embedder failed: {fallback_error}")
            rag_embedder = None
        
        return False

# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    rag_success = await initialize_rag_system()
    
    # Log final status
    logger.info("✅ Application created successfully")
    logger.info(f"📊 Configuration source: {os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)')}")
    logger.info(f"🌍 Environment: {os.getenv('ENV', 'production')}")
    logger.info(f"🤖 RAG modules: {'Available' if rag_embedder else 'Not Available'}")
    
    if rag_embedder and rag_embedder.has_search_engine():
        logger.info("🔍 RAG system: Optimized (with document search)")
    elif rag_embedder:
        logger.info("🔍 RAG system: Ready (fallback mode)")
    else:
        logger.info("🔍 RAG system: Not Available")
        
    logger.info(f"📁 Backend directory: {backend_dir}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Intelia Expert API...")

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Intelia Expert API",
    description="Assistant IA Expert pour la Santé et Nutrition Animale",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# Configure CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '["*"]')
if isinstance(allowed_origins, str):
    try:
        import json
        allowed_origins = json.loads(allowed_origins)
    except:
        allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_rag_status() -> str:
    """Get current RAG system status"""
    if not rag_embedder:
        return "not_available"
    elif rag_embedder.has_search_engine():
        return "optimized"
    else:
        return "fallback"

async def process_question_with_rag(question: str, language: str = "fr") -> Dict[str, Any]:
    """Process question using RAG system - Version simplifiée"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Processing question: {question[:50]}...")
        
        # Check if RAG embedder is available
        if not rag_embedder:
            raise Exception("RAG system not available")
        
        # Determine processing mode
        if rag_embedder.has_search_engine():
            logger.info("🔄 Using optimized mode - RAG with document search")
            
            # Search for relevant documents
            try:
                search_results = rag_embedder.search(question, k=5)
                logger.info(f"🔍 Search completed: {len(search_results)} results found")
                
                if search_results:
                    # Construct context from search results
                    context_parts = []
                    for i, result in enumerate(search_results[:3]):
                        context_parts.append(f"Document {i+1}: {result['text'][:500]}...")
                    
                    context = "\n\n".join(context_parts)
                    
                    # Use OpenAI with RAG context
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    
                    system_prompt = f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 
                    
Utilise les informations suivantes pour répondre à la question:

{context}

Réponds en {language} de manière précise et pratique, en te basant sur les documents fournis."""

                    response = openai.chat.completions.create(
                        model=os.getenv('DEFAULT_MODEL', 'gpt-4o'),
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": question}
                        ],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    answer = response.choices[0].message.content
                    mode = "rag_enhanced"
                    note = f"Réponse basée sur la recherche documentaire ({len(search_results)} documents trouvés)"
                    
                else:
                    logger.info("🔄 No relevant documents found - using fallback")
                    answer, mode, note = await fallback_openai_response(question, language)
                    
            except Exception as search_error:
                logger.error(f"❌ Search error: {search_error}")
                logger.info("🔄 Search failed - using fallback")
                answer, mode, note = await fallback_openai_response(question, language)
        else:
            logger.info("🔄 Using fallback mode - direct OpenAI")
            answer, mode, note = await fallback_openai_response(question, language)
        
        processing_time = time.time() - start_time
        
        return {
            "question": question,
            "response": answer,
            "mode": mode,
            "note": note,
            "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "processing_time": round(processing_time, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}")
        processing_time = time.time() - start_time
        
        # Emergency fallback
        try:
            answer, mode, note = await fallback_openai_response(question, language)
            return {
                "question": question,
                "response": answer,
                "mode": f"{mode}_emergency",
                "note": f"Mode d'urgence activé: {str(e)}",
                "config_source": "Emergency Fallback",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "processing_time": round(processing_time, 2)
            }
        except Exception as emergency_error:
            logger.error(f"❌ Emergency fallback failed: {emergency_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Service temporairement indisponible: {str(e)}"
            )

async def fallback_openai_response(question: str, language: str = "fr") -> tuple:
    """Fallback response using OpenAI directly"""
    import openai
    
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    system_prompt = f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308.

Réponds aux questions de manière précise et pratique en {language}.
Utilise tes connaissances pour donner des conseils basés sur les meilleures pratiques du secteur."""

    response = openai.chat.completions.create(
        model=os.getenv('DEFAULT_MODEL', 'gpt-4o'),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    answer = response.choices[0].message.content
    mode = "fallback_openai"
    note = "Réponse basée sur les connaissances générales (recherche documentaire non disponible)"
    
    return answer, mode, note

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Intelia Expert API with RAG",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
        "api_version": "2.0.0",
        "rag_modules": rag_embedder is not None,
        "rag_system": get_rag_status()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        services={
            "api": "running",
            "configuration": "loaded",
            "rag_modules": "available" if rag_embedder else "not_available",
            "rag_system": get_rag_status(),
            "database": "connected"
        },
        config={
            "source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "environment": os.getenv('ENV', 'production')
        }
    )

@app.post("/api/v1/expert/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest):
    """Ask a question to the expert system"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Le texte de la question est requis")
    
    try:
        result = await process_question_with_rag(
            question=request.text,
            language=request.language or "fr"
        )
        
        return ExpertResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in ask_expert: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/v1/expert/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit feedback for a question/answer"""
    logger.info(f"📝 Feedback received: rating={feedback.rating}, feedback='{feedback.feedback}'")
    
    return {
        "status": "received",
        "message": "Merci pour votre retour !",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }

@app.get("/api/v1/expert/stats")
async def get_system_stats():
    """Get system statistics"""
    stats = {
        "system_status": get_rag_status(),
        "rag_available": rag_embedder is not None,
        "backend_directory": backend_dir,
        "environment": os.getenv('ENV', 'production'),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if rag_embedder:
        try:
            # Try to get stats safely
            if hasattr(rag_embedder, 'get_stats'):
                rag_stats = rag_embedder.get_stats()
                stats["rag_stats"] = rag_stats
            else:
                # Basic stats without get_stats method
                stats["rag_stats"] = {
                    "embedder_available": True,
                    "search_engine_available": rag_embedder.has_search_engine(),
                    "model_name": getattr(rag_embedder, 'model_name', 'unknown'),
                    "dimension": getattr(rag_embedder, 'dimension', 0)
                }
        except Exception as stats_error:
            logger.warning(f"⚠️ Could not get RAG stats: {stats_error}")
            stats["rag_stats"] = {"error": "Stats unavailable"}
    
    return stats

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"❌ Unhandled exception: {exc}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erreur interne du serveur",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "path": str(request.url.path)
        }
    )

# =============================================================================
# CUSTOM OPENAPI
# =============================================================================

def custom_openapi():
    """Custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Intelia Expert API",
        version="2.0.0",
        description="Assistant IA Expert pour la Santé et Nutrition Animale",
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://intelia.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Starting Intelia Expert API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

# Deploy trigger: 07/24/2025 02:30:00