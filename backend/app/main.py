"""
Intelia Expert - API Backend avec Logging Intégré
Version 2.3.0 - FIXED: Logging endpoints ajoutés
"""

import os
import sys
import time
import logging
import traceback
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import json

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Pydantic models
from pydantic import BaseModel, Field

# Supabase
try:
    from supabase import create_client, Client
    import jwt
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Environment and logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
rag_embedder: Optional[Any] = None
supabase: Optional[Client] = None
security = HTTPBearer()

# =============================================================================
# IMPORT LOGGING SYSTEM
# =============================================================================

# Import du système de logging
try:
    from logging import router as logging_router
    LOGGING_AVAILABLE = True
    logger.info("✅ Système de logging importé avec succès")
except ImportError as e:
    LOGGING_AVAILABLE = False
    logging_router = None
    logger.error(f"❌ Erreur import logging: {e}")

# =============================================================================
# MULTI-LANGUAGE SUPPORT - 7 LANGUES
# =============================================================================

LANGUAGE_PROMPTS = {
    "fr": {
        "system_base": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308.""",
        "context_instruction": "Utilise les informations suivantes pour répondre à la question:",
        "response_instruction": "Réponds en français de manière précise et pratique, en te basant sur les documents fournis.",
        "fallback_instruction": "Réponds aux questions de manière précise et pratique en français. Utilise tes connaissances pour donner des conseils basés sur les meilleures pratiques du secteur."
    },
    "en": {
        "system_base": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.""",
        "context_instruction": "Use the following information to answer the question:",
        "response_instruction": "Respond in English precisely and practically, based on the provided documents.",
        "fallback_instruction": "Answer questions precisely and practically in English. Use your knowledge to provide advice based on industry best practices."
    },
    "es": {
        "system_base": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.""",
        "context_instruction": "Utiliza la siguiente información para responder a la pregunta:",
        "response_instruction": "Responde en español de manera precisa y práctica, basándote en los documentos proporcionados.",
        "fallback_instruction": "Responde a las preguntas de manera precisa y práctica en español. Usa tu conocimiento para dar consejos basados en las mejores prácticas del sector."
    }
}

def get_language_prompt(language: str, prompt_type: str) -> str:
    """Get localized prompt for specified language and type."""
    lang = language.lower()
    if lang not in LANGUAGE_PROMPTS:
        lang = "en"  # Default to English
    return LANGUAGE_PROMPTS[lang].get(prompt_type, LANGUAGE_PROMPTS["en"][prompt_type])

def get_user_context_prompt(user_type: str, language: str) -> str:
    """Get user-specific context prompt in the requested language."""
    if not user_type:
        return ""
    
    contexts = {
        "fr": {
            "professional": "Tu réponds à un professionnel de la santé animale. Donne des détails techniques approfondis.",
            "producer": "Tu réponds à un producteur agricole. Privilégie des conseils pratiques et accessibles."
        },
        "en": {
            "professional": "You are responding to an animal health professional. Provide in-depth technical details.",
            "producer": "You are responding to an agricultural producer. Focus on practical and accessible advice."
        },
        "es": {
            "professional": "Estás respondiendo a un profesional de la salud animal. Proporciona detalles técnicos profundos.",
            "producer": "Estás respondiendo a un productor agrícola. Enfócate en consejos prácticos y accesibles."
        }
    }
    
    lang = language.lower()
    if lang not in contexts:
        lang = "en"
        
    return contexts[lang].get(user_type, "")

# =============================================================================
# SUPABASE INITIALIZATION
# =============================================================================

def initialize_supabase():
    """Initialize Supabase client"""
    global supabase
    
    if not SUPABASE_AVAILABLE:
        logger.warning("⚠️ Supabase libraries not available")
        return False
    
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials not found in environment")
            return False
        
        logger.info(f"🔗 Connecting to Supabase: {supabase_url[:50]}...")
        
        supabase = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client created successfully")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ Error initializing Supabase: {e}")
        return False

# =============================================================================
# PYDANTIC MODELS (ÉTENDUS POUR LOGGING)
# =============================================================================

class UserProfile(BaseModel):
    """User profile model"""
    id: str
    email: str
    user_type: str = Field(..., description="'producer' or 'professional'")
    created_at: datetime
    last_active: Optional[datetime] = None
    preferences: Optional[Dict[str, Any]] = {}

class QuestionRequest(BaseModel):
    """Request model for expert questions"""
    text: str = Field(..., description="Question text", min_length=1, max_length=2000)
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    context: Optional[str] = Field(None, description="Additional context")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode: fast, balanced, quality")

class ExpertResponse(BaseModel):
    """Response model for expert answers"""
    question: str
    response: str
    mode: str
    note: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []
    config_source: str
    timestamp: str
    processing_time: float
    language: str

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    services: Dict[str, str]
    config: Dict[str, str]
    database_status: str
    rag_status: str

class FeedbackRequest(BaseModel):
    """Feedback request model"""
    question_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    feedback: Optional[str] = Field(None, max_length=500)

class AuthRequest(BaseModel):
    """Authentication request"""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class RegisterRequest(BaseModel):
    """Registration request"""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password", min_length=8)
    user_type: str = Field(..., description="'producer' or 'professional'")
    full_name: Optional[str] = Field(None, description="User full name")

# =============================================================================
# AUTHENTICATION & AUTHORIZATION
# =============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """Get current authenticated user"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        token = credentials.credentials
        jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
        
        if not jwt_secret:
            raise HTTPException(status_code=503, detail="JWT secret not configured")
        
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        user_id = payload.get('sub')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_data = result.data[0]
        
        return UserProfile(**user_data)
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# =============================================================================
# RAG SYSTEM INITIALIZATION
# =============================================================================

async def initialize_rag_system():
    """Initialize RAG system"""
    global rag_embedder
    
    logger.info("🔧 Initializing RAG system...")
    
    try:
        from rag.embedder import FastRAGEmbedder
        logger.info("✅ RAG embedder imported successfully")
        
        embedder = FastRAGEmbedder(
            api_key=os.getenv('OPENAI_API_KEY'),
            cache_embeddings=True,
            max_workers=2
        )
        logger.info("✅ RAG embedder instance created")
        
        # Search for existing index
        index_paths = [
            '/workspace/backend/rag_index',
            './rag_index', 
            '/tmp/rag_index',
            os.path.join(backend_dir, 'rag_index')
        ]
        
        index_loaded = False
        for index_path in index_paths:
            if os.path.exists(index_path):
                faiss_file = os.path.join(index_path, 'index.faiss')
                pkl_file = os.path.join(index_path, 'index.pkl')
                
                if os.path.exists(faiss_file) and os.path.exists(pkl_file):
                    logger.info(f"📁 Found complete index in: {index_path}")
                    
                    if embedder.load_index(index_path):
                        logger.info(f"✅ Successfully loaded RAG index from {index_path}")
                        index_loaded = True
                        break
        
        rag_embedder = embedder
        
        if index_loaded and embedder.has_search_engine():
            logger.info("✅ RAG system fully initialized with document search capabilities")
            return True
        else:
            logger.warning("⚠️ RAG system initialized but no valid index found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing RAG system: {e}")
        try:
            from rag.embedder import FastRAGEmbedder
            rag_embedder = FastRAGEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("✅ Fallback RAG embedder created successfully")
        except Exception as fallback_error:
            logger.error(f"❌ Even fallback embedder failed: {fallback_error}")
            rag_embedder = None
        return False

# =============================================================================
# QUESTION PROCESSING AVEC LOGGING
# =============================================================================

async def process_question_with_rag(
    question: str, 
    user: Optional[UserProfile] = None, 
    language: str = "fr",
    speed_mode: str = "balanced"
) -> Dict[str, Any]:
    """Process question using RAG system with integrated logging"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Processing question: {question[:50]}... (Lang: {language}, Mode: {speed_mode})")
        
        sources = []
        
        # Configure performance based on speed mode
        performance_config = {
            "fast": {"model": "gpt-3.5-turbo", "k": 2, "max_tokens": 300, "timeout": 8},
            "balanced": {"model": "gpt-3.5-turbo", "k": 3, "max_tokens": 500, "timeout": 12},
            "quality": {"model": "gpt-4o-mini", "k": 5, "max_tokens": 800, "timeout": 20}
        }
        
        config = performance_config.get(speed_mode, performance_config["balanced"])
        
        # Use RAG if available, otherwise fallback
        if rag_embedder and rag_embedder.has_search_engine():
            logger.info(f"🔄 Using RAG with document search (k={config['k']})")
            
            try:
                search_results = rag_embedder.search(question, k=config["k"])
                logger.info(f"🔍 Search completed: {len(search_results)} results found")
                
                if search_results:
                    context_parts = []
                    sources = []
                    
                    for i, result in enumerate(search_results[:config["k"]]):
                        context_chunk = result['text'][:400] + "..." if len(result['text']) > 400 else result['text']
                        context_parts.append(f"Document {i+1}: {context_chunk}")
                        sources.append({
                            "index": result['index'],
                            "score": result['score'],
                            "preview": result['text'][:150] + "..."
                        })
                    
                    context = "\n\n".join(context_parts)
                    
                    # Use OpenAI with RAG context
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    
                    system_base = get_language_prompt(language, "system_base")
                    context_instruction = get_language_prompt(language, "context_instruction")
                    response_instruction = get_language_prompt(language, "response_instruction")
                    user_context = get_user_context_prompt(user.user_type if user else None, language)
                    
                    system_prompt = f"""{system_base}
                    
{user_context}

{context_instruction}

{context}

{response_instruction}"""

                    response = openai.chat.completions.create(
                        model=config["model"],
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": question}
                        ],
                        temperature=0.7,
                        max_tokens=config["max_tokens"],
                        timeout=config["timeout"]
                    )
                    
                    answer = response.choices[0].message.content
                    mode = "rag_enhanced"
                    note = f"Réponse basée sur la recherche documentaire ({len(search_results)} documents trouvés)"
                    
                else:
                    logger.info("🔄 No relevant documents found - using fallback")
                    answer, mode, note = await fallback_openai_response(question, user, language, config)
                    
            except Exception as search_error:
                logger.error(f"❌ Search error: {search_error}")
                answer, mode, note = await fallback_openai_response(question, user, language, config)
        else:
            logger.info("🔄 Using fallback mode - direct OpenAI")
            answer, mode, note = await fallback_openai_response(question, user, language, config)
        
        processing_time = time.time() - start_time
        
        result = {
            "question": question,
            "response": answer,
            "mode": mode,
            "note": note,
            "sources": sources,
            "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "processing_time": round(processing_time, 2),
            "language": language
        }
        
        # ✅ NOUVEAU: LOG LA CONVERSATION SI LOGGING DISPONIBLE
        if LOGGING_AVAILABLE and user:
            try:
                from logging import ConversationCreate, logger_instance
                
                conversation_data = ConversationCreate(
                    user_id=user.id,
                    question=question,
                    response=answer,
                    conversation_id=result["timestamp"],
                    confidence_score=0.9 if mode == "rag_enhanced" else 0.7,
                    response_time_ms=int(processing_time * 1000),
                    language=language,
                    rag_used=(mode == "rag_enhanced")
                )
                
                logger_instance.save_conversation(conversation_data)
                logger.info(f"✅ Conversation loggée: {result['timestamp']}")
                
            except Exception as log_error:
                logger.warning(f"⚠️ Erreur logging conversation: {log_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}")
        processing_time = time.time() - start_time
        
        # Emergency fallback
        try:
            config = {"model": "gpt-3.5-turbo", "max_tokens": 300, "timeout": 8}
            answer, mode, note = await fallback_openai_response(question, user, language, config)
            return {
                "question": question,
                "response": answer,
                "mode": f"{mode}_emergency",
                "note": f"Mode d'urgence activé: {str(e)}",
                "sources": [],
                "config_source": "Emergency Fallback",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "processing_time": round(processing_time, 2),
                "language": language
            }
        except Exception as emergency_error:
            logger.error(f"❌ Emergency fallback failed: {emergency_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Service temporairement indisponible: {str(e)}"
            )

async def fallback_openai_response(question: str, user: Optional[UserProfile] = None, language: str = "fr", config: dict = None) -> tuple:
    """Fallback response using OpenAI directly"""
    try:
        import openai
        
        if config is None:
            config = {"model": "gpt-3.5-turbo", "max_tokens": 500, "timeout": 12}
        
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        system_base = get_language_prompt(language, "system_base")
        fallback_instruction = get_language_prompt(language, "fallback_instruction")
        user_context = get_user_context_prompt(user.user_type if user else None, language)
        
        system_prompt = f"""{system_base}

{user_context}

{fallback_instruction}"""

        response = openai.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=config["max_tokens"],
            timeout=config["timeout"]
        )
        
        answer = response.choices[0].message.content
        mode = "fallback_openai"
        note = "Réponse basée sur les connaissances générales (recherche documentaire non disponible)"
        
        return answer, mode, note
    
    except Exception as e:
        logger.warning(f"⚠️ OpenAI fallback failed: {e}")
        
        fallback_responses = {
            "fr": "Je suis temporairement indisponible. Veuillez réessayer plus tard ou contactez le support technique.",
            "en": "I am temporarily unavailable. Please try again later or contact technical support.",
            "es": "Estoy temporalmente no disponible. Inténtelo de nuevo más tarde o póngase en contacto con el soporte técnico."
        }
        
        answer = fallback_responses.get(language, fallback_responses["en"])
        mode = "static_fallback"
        note = "Mode de secours statique - service indisponible"
        
        return answer, mode, note

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

# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Intelia Expert API with Logging...")
    
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    logger.info("✅ Application created successfully")
    logger.info("📊 Multi-language support: FR, EN, ES")
    logger.info("⚡ Performance modes: fast, balanced, quality")
    logger.info(f"🗄️ Database: {'Available' if supabase_success else 'Not Available'}")
    logger.info(f"🤖 RAG modules: {'Available' if rag_embedder else 'Not Available'}")
    logger.info(f"📝 Logging system: {'Available' if LOGGING_AVAILABLE else 'Not Available'}")
    
    if rag_embedder and rag_embedder.has_search_engine():
        logger.info("🔍 RAG system: Optimized (with document search)")
    elif rag_embedder:
        logger.info("🔍 RAG system: Ready (fallback mode)")
    else:
        logger.info("🔍 RAG system: Not Available")
    
    yield
    
    logger.info("🛑 Shutting down Intelia Expert API...")

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Intelia Expert API",
    description="Assistant IA Expert pour la Santé et Nutrition Animale avec Logging",
    version="2.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://expert.intelia.com",
        "https://expert-app-cngws.ondigitalocean.app",
        "http://localhost:3000",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# =============================================================================
# INCLUSION DU ROUTER DE LOGGING
# =============================================================================

if LOGGING_AVAILABLE:
    app.include_router(logging_router, prefix="/v1")
    logger.info("✅ Logging router intégré avec succès")
else:
    logger.warning("⚠️ Logging router non disponible")

# =============================================================================
# API ENDPOINTS - ROUTAGE CORRIGÉ (/v1/ au lieu de /api/v1/)
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Intelia Expert API - Logging Intégré v2.3.0",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
        "api_version": "2.3.0",
        "database": supabase is not None,
        "rag_system": get_rag_status(),
        "logging_system": LOGGING_AVAILABLE,
        "supported_languages": ["fr", "en", "es"],
        "performance_modes": ["fast", "balanced", "quality"],
        "cors_configured": True,
        "available_endpoints": [
            "/v1/expert/ask-public",
            "/v1/expert/ask", 
            "/v1/expert/feedback",
            "/v1/logging/conversation",
            "/v1/logging/conversation/{id}/feedback",
            "/v1/logging/user/{id}/conversations",
            "/v1/logging/analytics",
            "/v1/auth/login",
            "/v1/auth/register",
            "/health",
            "/docs"
        ]
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if supabase else "disconnected"
    
    return HealthResponse(
        status="healthy",
        timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        services={
            "api": "running",
            "configuration": "loaded",
            "database": db_status,
            "rag_system": get_rag_status(),
            "logging_system": "available" if LOGGING_AVAILABLE else "unavailable"
        },
        config={
            "source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "environment": os.getenv('ENV', 'production')
        },
        database_status=db_status,
        rag_status=get_rag_status()
    )

# =============================================================================
# EXPERT SYSTEM ENDPOINTS - ROUTAGE CORRIGÉ (/v1/ au lieu de /api/v1/)
# =============================================================================

@app.post("/v1/expert/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask a question without authentication"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Le texte de la question est requis")
    
    try:
        result = await process_question_with_rag(
            question=request.text,
            user=None,
            language=request.language or "fr",
            speed_mode=request.speed_mode or "fast"
        )
        
        # Remove sources for public access
        result["sources"] = []
        result["note"] = result.get("note", "") + " (Accès public - fonctionnalités limitées)"
        
        return ExpertResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in ask_expert_public: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/v1/expert/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest, user: UserProfile = Depends(get_current_user)):
    """Ask a question to the expert system - Full features"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Le texte de la question est requis")
    
    try:
        result = await process_question_with_rag(
            question=request.text,
            user=user,
            language=request.language or "fr",
            speed_mode=request.speed_mode or "balanced"
        )
        
        return ExpertResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in ask_expert: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/v1/expert/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit feedback for a question/answer"""
    try:
        logger.info(f"📝 Feedback received: rating={feedback.rating}")
        
        return {
            "status": "received",
            "message": "Merci pour votre retour !",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"❌ Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du feedback")

# =============================================================================
# AUTHENTICATION ENDPOINTS - ROUTAGE CORRIGÉ (/v1/ au lieu de /api/v1/)
# =============================================================================

@app.post("/v1/auth/register")
async def register(request: RegisterRequest):
    """Register new user"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if auth_response.user:
            # Create user profile
            user_data = {
                "email": request.email,
                "user_type": request.user_type,
                "full_name": request.full_name,
                "auth_user_id": auth_response.user.id,
                "created_at": datetime.utcnow().isoformat(),
                "preferences": {}
            }
            
            result = supabase.table('users').insert(user_data).execute()
            
            return {
                "message": "User registered successfully",
                "user_id": result.data[0]['id'],
                "email": request.email,
                "user_type": request.user_type
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")
            
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/auth/login")
async def login(request: AuthRequest):
    """User login"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Login with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if auth_response.user and auth_response.session:
            # Get user profile
            result = supabase.table('users').select('*').eq('id', auth_response.user.id).execute()
            
            if result.data:
                user_data = result.data[0]
                return {
                    "access_token": auth_response.session.access_token,
                    "token_type": "bearer",
                    "user": user_data
                }
            else:
                raise HTTPException(status_code=404, detail="User profile not found")
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/v1/auth/logout")
async def logout(user: UserProfile = Depends(get_current_user)):
    """User logout"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        return {"message": "Logged out"}

@app.get("/v1/auth/profile")
async def get_profile(user: UserProfile = Depends(get_current_user)):
    """Get user profile"""
    return user

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
            "path": str(request.url.path),
            "api_version": "2.3.0"
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
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Starting Intelia Expert API on {host}:{port}")
    logger.info(f"📋 Version: 2.3.0 - Logging Integrated")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )