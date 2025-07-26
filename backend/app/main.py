"""
Intelia Expert - API Backend Complète
Multi-langue + Performance + Sécurité + Logging System
Version 2.1.0 - Réécrite et corrigée
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

# Supabase et JWT
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

# Environment loading
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
# IMPORT DES MODULES API - VERSION SÉCURISÉE
# =============================================================================

# Variables globales pour stocker les modules
expert = None
auth = None
admin = None
health = None
system = None
logging_router = None

logger.info("🔄 Importation des modules API...")

# Import sécurisé de chaque module
try:
    from app.api import expert as expert_module
    expert = expert_module
    logger.info("✅ Module expert importé avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import expert: {e}")
    expert = None

try:
    from app.api import auth as auth_module
    auth = auth_module
    logger.info("✅ Module auth importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ Module auth non trouvé: {e}")
    auth = None

try:
    from app.api import admin as admin_module
    admin = admin_module
    logger.info("✅ Module admin importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ Module admin non trouvé: {e}")
    admin = None

try:
    from app.api import health as health_module
    health = health_module
    logger.info("✅ Module health importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ Module health non trouvé: {e}")
    health = None

try:
    from app.api import system as system_module
    system = system_module
    logger.info("✅ Module system importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ Module system non trouvé: {e}")
    system = None

# Import du module logging avec un nom différent pour éviter les conflits
try:
    from app.api import logging as logging_module
    logging_router = logging_module
    logger.info("✅ Module logging importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ Module logging non trouvé: {e}")
    logging_router = None

# Résumé des imports
available_modules = []
if expert: available_modules.append("expert")
if auth: available_modules.append("auth") 
if admin: available_modules.append("admin")
if health: available_modules.append("health")
if system: available_modules.append("system")
if logging_router: available_modules.append("logging")

logger.info(f"📦 Modules disponibles: {', '.join(available_modules)}")

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
        
        # Test connection
        try:
            result = supabase.auth.get_session()
            logger.info("✅ Supabase connection tested successfully")
            return True
        except Exception as test_error:
            logger.warning(f"⚠️ Supabase client created but test failed: {test_error}")
            logger.info("✅ Supabase client initialized (will test on first real use)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error initializing Supabase: {e}")
        return False

# =============================================================================
# PYDANTIC MODELS
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

class HistoryResponse(BaseModel):
    """Response model for conversation history"""
    conversations: List[Dict[str, Any]]
    total_count: int
    page: int
    per_page: int

class TopicsResponse(BaseModel):
    """Response model for suggested topics"""
    topics: List[Dict[str, str]]
    popular_keywords: List[str]
    user_type_specific: bool

class SuggestionsResponse(BaseModel):
    """Response model for question suggestions"""
    suggestions: List[str]
    context_aware: bool
    based_on_history: bool

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    services: Dict[str, str]
    config: Dict[str, str]
    database_status: str
    rag_status: str
    logging_status: str

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
        
        supabase.table('users').update({
            'last_active': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        return UserProfile(**user_data)
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_optional_user(request: Request) -> Optional[UserProfile]:
    """Get user if authenticated, None otherwise"""
    try:
        auth_header = request.headers.get('authorization')
        if not auth_header:
            return None
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.replace("Bearer ", "")
        )
        return await get_current_user(credentials)
    except:
        return None

def require_user_type(allowed_types: List[str]):
    """Decorator to require specific user types"""
    def decorator(user: UserProfile = Depends(get_current_user)):
        if user.user_type not in allowed_types:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required user type: {', '.join(allowed_types)}"
            )
        return user
    return decorator

# =============================================================================
# RAG SYSTEM INITIALIZATION
# =============================================================================

async def initialize_rag_system():
    """Initialize RAG system - OPTIMIZED VERSION"""
    global rag_embedder
    
    logger.info("🔧 Initializing RAG system...")
    
    try:
        # Try to import RAG system
        try:
            from rag.embedder import FastRAGEmbedder
            logger.info("✅ RAG embedder imported successfully")
        except ImportError:
            logger.warning("⚠️ RAG embedder not available - creating fallback")
            rag_embedder = None
            return False
        
        # Create embedder instance
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
        
        logger.info(f"🔍 Searching for RAG index in paths: {index_paths}")
        
        index_loaded = False
        for index_path in index_paths:
            if os.path.exists(index_path):
                faiss_file = os.path.join(index_path, 'index.faiss')
                pkl_file = os.path.join(index_path, 'index.pkl')
                
                if os.path.exists(faiss_file) and os.path.exists(pkl_file):
                    logger.info(f"📁 Found complete index in: {index_path}")
                    logger.info(f"🔄 Attempting to load index from {index_path}")
                    
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
        rag_embedder = None
        return False

# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

async def save_conversation(user_id: str, question: str, response: str, mode: str, sources: List[Dict] = None):
    """Save conversation to database"""
    if not supabase:
        return
    
    try:
        conversation_data = {
            'user_id': user_id,
            'question': question,
            'response': response,
            'mode': mode,
            'sources': sources or [],
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('conversations').insert(conversation_data).execute()
        logger.info("✅ Conversation saved to database")
    except Exception as e:
        logger.error(f"❌ Error saving conversation: {e}")

async def get_user_conversations(user_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Get user conversation history"""
    if not supabase:
        return {"conversations": [], "total_count": 0}
    
    try:
        # Get total count
        count_result = supabase.table('conversations').select('id', count='exact').eq('user_id', user_id).execute()
        total_count = count_result.count or 0
        
        # Get paginated conversations
        start = (page - 1) * per_page
        result = supabase.table('conversations')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .range(start, start + per_page - 1)\
            .execute()
        
        return {
            "conversations": result.data or [],
            "total_count": total_count,
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        logger.error(f"❌ Error getting conversations: {e}")
        return {"conversations": [], "total_count": 0}

async def save_feedback(user_id: str, question_id: Optional[str], rating: int, feedback: Optional[str]):
    """Save user feedback"""
    if not supabase:
        return
    
    try:
        feedback_data = {
            'user_id': user_id,
            'question_id': question_id,
            'rating': rating,
            'feedback': feedback,
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('feedback').insert(feedback_data).execute()
        logger.info("✅ Feedback saved to database")
    except Exception as e:
        logger.error(f"❌ Error saving feedback: {e}")

# =============================================================================
# OPTIMIZED QUESTION PROCESSING
# =============================================================================

async def process_question_with_rag(
    question: str, 
    user: Optional[UserProfile] = None, 
    language: str = "fr",
    speed_mode: str = "balanced"
) -> Dict[str, Any]:
    """Process question using RAG system or fallback"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Processing question: {question[:50]}... (User: {user.email if user else 'Anonymous'}, Lang: {language}, Mode: {speed_mode})")
        
        # Use expert service if available, otherwise fallback
        if expert and hasattr(expert, 'router'):
            try:
                # Try to use expert service
                from app.services.expert_service import expert_service
                result = await expert_service.ask_expert(question, language)
                
                processing_time = time.time() - start_time
                
                return {
                    "question": question,
                    "response": result.get("response", "Service temporairement indisponible"),
                    "mode": "expert_service",
                    "note": "Réponse générée par le service expert",
                    "sources": [],
                    "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables'),
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "processing_time": round(processing_time, 2),
                    "language": language
                }
                
            except Exception as service_error:
                logger.warning(f"⚠️ Expert service failed: {service_error}")
                # Continue to fallback
        
        # Fallback response
        answer, mode, note = await fallback_openai_response(question, user, language)
        
        processing_time = time.time() - start_time
        
        result = {
            "question": question,
            "response": answer,
            "mode": mode,
            "note": note,
            "sources": [],
            "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables'),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "processing_time": round(processing_time, 2),
            "language": language
        }
        
        # Save conversation if user is authenticated
        if user:
            await save_conversation(user.id, question, answer, mode, [])
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}")
        processing_time = time.time() - start_time
        
        return {
            "question": question,
            "response": "Service temporairement indisponible. Veuillez réessayer plus tard.",
            "mode": "emergency_fallback",
            "note": f"Erreur: {str(e)}",
            "sources": [],
            "config_source": "Emergency Mode",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "processing_time": round(processing_time, 2),
            "language": language
        }

async def fallback_openai_response(question: str, user: Optional[UserProfile] = None, language: str = "fr") -> tuple:
    """Fallback response using basic logic"""
    try:
        # Try OpenAI if available
        import openai
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            openai.api_key = api_key
            
            system_base = get_language_prompt(language, "system_base")
            fallback_instruction = get_language_prompt(language, "fallback_instruction")
            user_context = get_user_context_prompt(user.user_type if user else None, language)
            
            system_prompt = f"""{system_base}
{user_context}
{fallback_instruction}"""

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=12
            )
            
            answer = response.choices[0].message.content
            mode = "openai_fallback"
            note = "Réponse générée par OpenAI (mode de secours)"
            
            return answer, mode, note
    
    except Exception as e:
        logger.warning(f"⚠️ OpenAI fallback failed: {e}")
    
    # Ultimate fallback
    fallback_responses = {
        "fr": "Je suis temporairement indisponible. Veuillez réessayer plus tard ou contactez le support technique.",
        "en": "I am temporarily unavailable. Please try again later or contact technical support.",
        "es": "Estoy temporalmente no disponible. Inténtelo de nuevo más tarde o póngase en contacto con el soporte técnico."
    }
    
    answer = fallback_responses.get(language, fallback_responses["en"])
    mode = "static_fallback"
    note = "Mode de secours statique"
    
    return answer, mode, note

# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Intelia Expert API...")
    
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    # Test logging system
    logging_available = logging_router is not None
    
    logger.info("✅ Application created successfully")
    logger.info("📊 Multi-language support: FR, EN, ES")
    logger.info("⚡ Performance modes: fast, balanced, quality")
    logger.info(f"🗄️ Database: {'Available' if supabase_success else 'Not Available'}")
    logger.info(f"🤖 RAG modules: {'Available' if rag_embedder else 'Not Available'}")
    logger.info(f"📝 Logging system: {'Available' if logging_available else 'Not Available'}")
    
    if rag_embedder and hasattr(rag_embedder, 'has_search_engine') and rag_embedder.has_search_engine():
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
    description="Assistant IA Expert pour la Santé et Nutrition Animale - Multi-langue Optimisé",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# INCLUDE ROUTERS - VERSION SÉCURISÉE
# =============================================================================

logger.info("🔄 Enregistrement des routers...")

# Router Expert (critique - doit exister)
if expert and hasattr(expert, 'router'):
    app.include_router(expert.router, prefix="/api/v1")
    logger.info("✅ Expert router enregistré à /api/v1/expert")
else:
    logger.error("❌ Expert router non disponible - service critique manquant")

# Router Auth (optionnel)
if auth and hasattr(auth, 'router'):
    app.include_router(auth.router, prefix="/api/v1")
    logger.info("✅ Auth router enregistré à /api/v1/auth")
else:
    logger.warning("⚠️ Auth router non disponible")

# Router Admin (optionnel)
if admin and hasattr(admin, 'router'):
    app.include_router(admin.router, prefix="/api/v1")
    logger.info("✅ Admin router enregistré à /api/v1/admin")
else:
    logger.warning("⚠️ Admin router non disponible")

# Router Health (optionnel)
if health and hasattr(health, 'router'):
    app.include_router(health.router, prefix="/api/v1")
    logger.info("✅ Health router enregistré à /api/v1/health")
else:
    logger.warning("⚠️ Health router non disponible")

# Router System (optionnel)
if system and hasattr(system, 'router'):
    app.include_router(system.router, prefix="/api/v1")
    logger.info("✅ System router enregistré à /api/v1/system")
else:
    logger.warning("⚠️ System router non disponible")

# Router Logging (optionnel)
if logging_router and hasattr(logging_router, 'router'):
    app.include_router(logging_router.router, prefix="/api/v1")
    logger.info("✅ Logging router enregistré à /api/v1/logging")
else:
    logger.warning("⚠️ Logging router non disponible")

# Compteur des routers enregistrés
registered_routers = 0
if expert and hasattr(expert, 'router'): registered_routers += 1
if auth and hasattr(auth, 'router'): registered_routers += 1
if admin and hasattr(admin, 'router'): registered_routers += 1
if health and hasattr(health, 'router'): registered_routers += 1
if system and hasattr(system, 'router'): registered_routers += 1
if logging_router and hasattr(logging_router, 'router'): registered_routers += 1

logger.info(f"📊 Total routers enregistrés: {registered_routers}/6")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_rag_status() -> str:
    """Get current RAG system status"""
    if not rag_embedder:
        return "not_available"
    elif hasattr(rag_embedder, 'has_search_engine') and rag_embedder.has_search_engine():
        return "optimized"
    else:
        return "fallback"

def get_logging_status() -> str:
    """Get current logging system status"""
    if logging_router is None:
        return "not_available"
    
    try:
        from app.api.logging import logger_instance
        return "available"
    except Exception:
        return "error"

# =============================================================================
# API ENDPOINTS - ROOT & HEALTH
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Intelia Expert API with Multi-Language RAG + Performance + Logging System",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
        "api_version": "2.1.0",
        "database": supabase is not None,
        "rag_system": get_rag_status(),
        "logging_system": get_logging_status(),
        "supported_languages": ["fr", "en", "es"],
        "performance_modes": ["fast", "balanced", "quality"],
        "available_modules": available_modules
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
            "logging_system": get_logging_status()
        },
        config={
            "source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "environment": os.getenv('ENV', 'production')
        },
        database_status=db_status,
        rag_status=get_rag_status(),
        logging_status=get_logging_status()
    )

# =============================================================================
# AUTHENTICATION ENDPOINTS - FALLBACK SI AUTH MODULE MANQUANT
# =============================================================================

if not auth:
    @app.post("/api/v1/auth/register")
    async def register(request: RegisterRequest):
        """Register new user - Fallback"""
        return {"message": "Registration not available - auth module missing", "status": "not_implemented"}

    @app.post("/api/v1/auth/login")
    async def login(request: AuthRequest):
        """User login - Fallback"""
        return {"message": "Login not available - auth module missing", "status": "not_implemented"}

    @app.post("/api/v1/auth/logout")
    async def logout():
        """User logout - Fallback"""
        return {"message": "Logout not available - auth module missing", "status": "not_implemented"}

    @app.get("/api/v1/auth/profile")
    async def get_profile():
        """Get user profile - Fallback"""
        return {"message": "Profile not available - auth module missing", "status": "not_implemented"}

# =============================================================================
# EXPERT SYSTEM ENDPOINTS - FALLBACK SI EXPERT MODULE MANQUANT
# =============================================================================

if not expert:
    @app.post("/api/v1/expert/ask-public", response_model=ExpertResponse)
    async def ask_expert_public(request: QuestionRequest):
        """Ask a question without authentication - Fallback"""
        try:
            result = await process_question_with_rag(
                question=request.text,
                user=None,
                language=request.language or "fr",
                speed_mode=request.speed_mode or "balanced"
            )
            
            # Remove sources for public access
            result["sources"] = []
            result["note"] = result.get("note", "") + " (Accès public - expert module indisponible)"
            
            return ExpertResponse(**result)
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in ask_expert_public: {e}")
            raise HTTPException(status_code=500, detail="Erreur interne du serveur")

    @app.post("/api/v1/expert/ask", response_model=ExpertResponse)
    async def ask_expert(request: QuestionRequest):
        """Ask a question to the expert system - Fallback without auth"""
        try:
            result = await process_question_with_rag(
                question=request.text,
                user=None,
                language=request.language or "fr",
                speed_mode=request.speed_mode or "balanced"
            )
            
            return ExpertResponse(**result)
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in ask_expert: {e}")
            raise HTTPException(status_code=500, detail="Erreur interne du serveur")

    @app.get("/api/v1/expert/topics", response_model=TopicsResponse)
    async def get_topics():
        """Get suggested topics - Fallback"""
        topics = [
            {"title": "Problèmes de croissance poulets", "category": "croissance"},
            {"title": "Conditions environnementales optimales", "category": "environnement"}, 
            {"title": "Mortalité élevée - causes", "category": "sante"},
            {"title": "Nutrition et alimentation", "category": "nutrition"},
            {"title": "Ventilation et température", "category": "environnement"}
        ]
        keywords = ["croissance", "température", "alimentation", "mortalité", "ventilation"]
        
        return TopicsResponse(
            topics=topics,
            popular_keywords=keywords,
            user_type_specific=False
        )

    @app.post("/api/v1/expert/feedback")
    async def submit_feedback(feedback: FeedbackRequest):
        """Submit feedback for a question/answer - Fallback"""
        logger.info(f"📝 Feedback received (fallback): rating={feedback.rating}")
        
        return {
            "status": "received",
            "message": "Merci pour votre retour ! (mode dégradé)",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }

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