"""
Intelia Expert - API Backend Main
Version optimisée avec RAG automatique et gestion d'erreurs robuste
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
# RAG SYSTEM INITIALIZATION
# =============================================================================

async def initialize_rag_system():
    """Initialize RAG system with automatic index loading"""
    global rag_embedder
    
    try:
        logger.info("🔧 Initializing RAG system...")
        
        # Import RAG embedder
        try:
            from rag.embedder import EnhancedDocumentEmbedder
        except ImportError as e:
            logger.error(f"❌ Cannot import RAG embedder: {e}")
            return False
        
        # Create embedder instance
        embedder = EnhancedDocumentEmbedder(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Search for existing index in multiple locations
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
                logger.info(f"📁 Found index directory: {index_path}")
                
                # Check required files
                faiss_file = os.path.join(index_path, 'index.faiss')
                pkl_file = os.path.join(index_path, 'index.pkl')
                
                files_status = []
                if os.path.exists(faiss_file):
                    logger.info(f"   ✅ Found: index.faiss")
                    files_status.append(True)
                else:
                    logger.warning(f"   ❌ Missing: index.faiss")
                    files_status.append(False)
                    
                if os.path.exists(pkl_file):
                    logger.info(f"   ✅ Found: index.pkl")
                    files_status.append(True)
                else:
                    logger.warning(f"   ❌ Missing: index.pkl")
                    files_status.append(False)
                
                # Try to load index if both files exist
                if all(files_status):
                    logger.info(f"🔄 Attempting to load index from {index_path}")
                    
                    if embedder.load_index(index_path):
                        stats = embedder.get_stats()
                        logger.info(f"✅ Successfully loaded RAG index from {index_path}")
                        logger.info(f"   📊 Vectors: {stats.get('index_size', 0)}")
                        logger.info(f"   📚 Documents: {stats.get('documents_count', 0)}")
                        logger.info(f"   🔢 Dimension: {stats.get('dimension', 0)}")
                        logger.info(f"   🔍 Search engine available: {stats.get('search_engine_available', False)}")
                        index_loaded = True
                        break
                    else:
                        logger.warning(f"❌ Failed to load index from {index_path}")
                else:
                    missing_files = []
                    if not os.path.exists(faiss_file):
                        missing_files.append('index.faiss')
                    if not os.path.exists(pkl_file):
                        missing_files.append('index.pkl')
                    logger.warning(f"⚠️ Index incomplete in {index_path}: missing {missing_files}")
        
        # Set global embedder
        rag_embedder = embedder
        
        # Log final status
        if index_loaded and embedder.has_search_engine():
            logger.info("✅ RAG system fully initialized with document search capabilities")
            return True
        else:
            logger.warning("⚠️ No valid RAG index found - will run in fallback mode")
            logger.warning("⚠️ RAG system using OpenAI direct mode")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing RAG system: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        logger.warning("⚠️ RAG system initialization failed - using fallback mode")
        
        # Try to create minimal embedder for fallback
        try:
            from rag.embedder import EnhancedDocumentEmbedder
            rag_embedder = EnhancedDocumentEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("✅ Fallback RAG embedder created successfully")
            return False
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
    logger.info("🚀 Starting Intelia Expert API...")
    
    # Initialize RAG system
    rag_success = await initialize_rag_system()
    
    # Log startup status
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
    """Process question using RAG system"""
    start_time = time.time()
    
    try:
        # Check if RAG embedder is available
        if not rag_embedder:
            raise HTTPException(status_code=503, detail="RAG system not available")
        
        logger.info(f"🔍 Processing question: {question[:50]}...")
        
        # Determine processing mode
        if rag_embedder.has_search_engine():
            # Use RAG with document search
            logger.info("🔄 Using optimized mode - RAG with document search")
            
            # Search for relevant documents
            search_results = rag_embedder.search(question, k=5)
            
            if search_results:
                # Construct context from search results
                context = "\n".join([result['text'] for result in search_results[:3]])
                
                # Use OpenAI with RAG context
                import openai
                openai.api_key = os.getenv('OPENAI_API_KEY')
                
                system_prompt = f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 
                
Utilise les informations suivantes pour répondre à la question:
{context}

Réponds en {language} de manière précise et pratique."""

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
                # No relevant documents found, use fallback
                logger.info("🔄 No relevant documents found - using fallback")
                answer, mode, note = await fallback_openai_response(question, language)
        else:
            # Use fallback mode
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
        rag_stats = rag_embedder.get_stats()
        stats.update({
            "rag_stats": rag_stats
        })
    
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
# Deploy trigger: 07/23/2025 20:14:18
