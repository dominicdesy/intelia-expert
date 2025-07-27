"""
Intelia Expert - API Backend Complète
Multi-langue + Performance + Sécurité + Tous Endpoints
Version 2.1.3 - HYBRID: Direct Endpoints + Router Fallback
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
    },
    "pt": {
        "system_base": """Você é um especialista veterinário em saúde e nutrição animal, particularmente para frangos de corte Ross 308.""",
        "context_instruction": "Use as seguintes informações para responder à pergunta:",
        "response_instruction": "Responda em português de forma precisa e prática, baseando-se nos documentos fornecidos.",
        "fallback_instruction": "Responda às perguntas de forma precisa e prática em português. Use seu conhecimento para dar conselhos baseados nas melhores práticas do setor."
    },
    "de": {
        "system_base": """Sie sind ein Veterinärexperte für Tiergesundheit und -ernährung, insbesondere für Ross 308 Masthähnchen.""",
        "context_instruction": "Verwenden Sie die folgenden Informationen, um die Frage zu beantworten:",
        "response_instruction": "Antworten Sie auf Deutsch präzise und praktisch, basierend auf den bereitgestellten Dokumenten.",
        "fallback_instruction": "Beantworten Sie Fragen präzise und praktisch auf Deutsch. Nutzen Sie Ihr Wissen, um Ratschläge auf Basis der besten Branchenpraktiken zu geben."
    },
    "nl": {
        "system_base": """U bent een veterinaire expert gespecialiseerd in diergezondheid en voeding, met name voor Ross 308 vleeskuikens.""",
        "context_instruction": "Gebruik de volgende informatie om de vraag te beantwoorden:",
        "response_instruction": "Antwoord in het Nederlands precies en praktisch, gebaseerd op de verstrekte documenten.",
        "fallback_instruction": "Beantwoord vragen precies en praktisch in het Nederlands. Gebruik uw kennis om advies te geven gebaseerd op de beste praktijken in de sector."
    },
    "pl": {
        "system_base": """Jesteś ekspertem weterynarii specjalizującym się w zdrowiu i żywieniu zwierząt, szczególnie w przypadku kurczaków brojlerów Ross 308.""",
        "context_instruction": "Użyj następujących informacji, aby odpowiedzieć na pytanie:",
        "response_instruction": "Odpowiedz po polsku precyzyjnie i praktycznie, opierając się na dostarczonych dokumentach.",
        "fallback_instruction": "Odpowiadaj na pytania precyzyjnie i praktycznie po polsku. Wykorzystuj swoją wiedzę, aby udzielać porad opartych na najlepszych praktykach w branży."
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
        },
        "pt": {
            "professional": "Você está respondendo a um profissional de saúde animal. Forneça detalhes técnicos aprofundados.",
            "producer": "Você está respondendo a um produtor agrícola. Foque em conselhos práticos e acessíveis."
        },
        "de": {
            "professional": "Sie antworten einem Tiergesundheitsexperten. Geben Sie detaillierte technische Informationen.",
            "producer": "Sie antworten einem landwirtschaftlichen Produzenten. Konzentrieren Sie sich auf praktische und zugängliche Ratschläge."
        },
        "nl": {
            "professional": "U reageert op een diergezondheidsprofessional. Geef diepgaande technische details.",
            "producer": "U reageert op een landbouwproducent. Focus op praktisch en toegankelijk advies."
        },
        "pl": {
            "professional": "Odpowiadasz specjaliście ds. zdrowia zwierząt. Podaj szczegółowe informacje techniczne.",
            "producer": "Odpowiadasz producentowi rolnemu. Skup się na praktycznych i dostępnych poradach."
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
    language: Optional[str] = Field("fr", description="Response language (fr, en, es, pt, de, nl, pl)")
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
        from rag.embedder import FastRAGEmbedder
        logger.info("✅ RAG embedder imported successfully")
        
        # Create optimized embedder instance
        embedder = FastRAGEmbedder(
            api_key=os.getenv('OPENAI_API_KEY'),
            cache_embeddings=True,  # Enable caching
            max_workers=2  # Limit concurrent processing
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
        try:
            from rag.embedder import FastRAGEmbedder
            rag_embedder = FastRAGEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("✅ Fallback RAG embedder created successfully")
        except Exception as fallback_error:
            logger.error(f"❌ Even fallback embedder failed: {fallback_error}")
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
    """Process question using RAG system - OPTIMIZED VERSION"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Processing question: {question[:50]}... (User: {user.email if user else 'Anonymous'}, Lang: {language}, Mode: {speed_mode})")
        
        if not rag_embedder:
            raise Exception("RAG system not available")
        
        sources = []
        
        # Configure performance based on speed mode
        performance_config = {
            "fast": {"model": "gpt-3.5-turbo", "k": 2, "max_tokens": 300, "timeout": 8},
            "balanced": {"model": "gpt-3.5-turbo", "k": 3, "max_tokens": 500, "timeout": 12},
            "quality": {"model": "gpt-4o-mini", "k": 5, "max_tokens": 800, "timeout": 20}
        }
        
        config = performance_config.get(speed_mode, performance_config["balanced"])
        
        # Determine processing mode based on user type and RAG availability
        if rag_embedder.has_search_engine():
            logger.info(f"🔄 Using optimized mode - RAG with document search (k={config['k']})")
            
            try:
                # Search for relevant documents with optimized k
                search_results = rag_embedder.search(question, k=config["k"])
                logger.info(f"🔍 Search completed: {len(search_results)} results found")
                
                if search_results:
                    # Prepare context and sources - OPTIMIZED
                    context_parts = []
                    sources = []
                    
                    for i, result in enumerate(search_results[:config["k"]]):
                        # Limit context size for speed
                        context_chunk = result['text'][:400] + "..." if len(result['text']) > 400 else result['text']
                        context_parts.append(f"Document {i+1}: {context_chunk}")
                        sources.append({
                            "index": result['index'],
                            "score": result['score'],
                            "preview": result['text'][:150] + "..."
                        })
                    
                    context = "\n\n".join(context_parts)
                    
                    # Use OpenAI with RAG context - MULTI-LANGUAGE + OPTIMIZED
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    
                    # Get localized prompts
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
        
        # Save conversation if user is authenticated
        if user:
            await save_conversation(user.id, question, answer, mode, sources)
        
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
    """Fallback response using OpenAI directly - MULTI-LANGUAGE + OPTIMIZED"""
    try:
        import openai
        
        if config is None:
            config = {"model": "gpt-3.5-turbo", "max_tokens": 500, "timeout": 12}
        
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Get localized prompts
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
        
        # Ultimate static fallback
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
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Intelia Expert API...")
    
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    logger.info("✅ Application created successfully")
    logger.info("📊 Multi-language support: FR, EN, ES, PT, DE, NL, PL")
    logger.info("⚡ Performance modes: fast, balanced, quality")
    logger.info(f"🗄️ Database: {'Available' if supabase_success else 'Not Available'}")
    logger.info(f"🤖 RAG modules: {'Available' if rag_embedder else 'Not Available'}")
    
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
    description="Assistant IA Expert pour la Santé et Nutrition Animale - Multi-langue Optimisé",
    version="2.1.3",
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

# =============================================================================
# OPTIONAL ROUTER INCLUSION - NON-BLOCKING
# =============================================================================

logger.info("🔄 Attempting to include external routers (optional)...")

registered_routers = []

# =============================================================================
# INCLUDE ROUTERS - STRUCTURE V1 DIRECTE
# =============================================================================

logger.info("🔄 Enregistrement des routers v1...")

registered_routers = []

# Import et enregistrement des routers avec la structure v1 exacte
def register_router_safe(module_name, router_name, prefix="/api/v1"):
    """Register router safely with error handling"""
    try:
        module = __import__(f'app.api.v1.{module_name}', fromlist=['router'])
        router = getattr(module, 'router')
        app.include_router(router, prefix=prefix)
        registered_routers.append(router_name)
        logger.info(f"✅ {router_name.capitalize()} router enregistré à {prefix}/{module_name}")
        return True
    except ImportError as e:
        logger.warning(f"⚠️ {router_name.capitalize()} router import failed: {e}")
        return False
    except AttributeError as e:
        logger.warning(f"⚠️ {router_name.capitalize()} router has no 'router' attribute: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ {router_name.capitalize()} router registration failed: {e}")
        return False

# Register each router
register_router_safe('expert', 'expert')
register_router_safe('admin', 'admin') 
register_router_safe('auth', 'auth')
register_router_safe('health', 'health')
register_router_safe('logging', 'logging')
register_router_safe('system', 'system')

logger.info(f"📊 External routers included: {', '.join(registered_routers) if registered_routers else 'None'}")

# =============================================================================
# API ENDPOINTS - ROOT & HEALTH (DIRECT)
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Intelia Expert API - Direct DigitalOcean Access",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
        "api_version": "2.1.3",
        "database": supabase is not None,
        "rag_system": get_rag_status(),
        "supported_languages": ["fr", "en", "es", "pt", "de", "nl", "pl"],
        "performance_modes": ["fast", "balanced", "quality"],
        "external_routers": registered_routers,
        "endpoint_mode": "direct_digitalocean",
        "frontend_url": "https://expert.intelia.com",
        "api_url": "https://expert-app-cngws.ondigitalocean.app",
        "cors_configured": True,
        "available_endpoints": [
            "/api/v1/expert/ask-public",
            "/api/v1/expert/ask", 
            "/api/v1/expert/topics",
            "/api/v1/expert/feedback",
            "/api/v1/expert/history",
            "/health",
            "/docs"
        ]
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint optimized for frontend"""
    return {
        "api_healthy": True,
        "database_connected": supabase is not None,
        "rag_available": get_rag_status() == "optimized",
        "endpoints_registered": len(registered_routers),
        "direct_access": True,
        "cors_enabled": True,
        "recommended_frontend_config": {
            "api_base_url": "https://expert-app-cngws.ondigitalocean.app",
            "endpoints": {
                "ask_public": "/api/v1/expert/ask-public",
                "ask_authenticated": "/api/v1/expert/ask",
                "topics": "/api/v1/expert/topics", 
                "feedback": "/api/v1/expert/feedback",
                "health": "/health"
            }
        }
    }
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if supabase else "disconnected"
    
    @app.get("/api/status")
async def api_status():
    """API status endpoint optimized for frontend"""
    return {
        "api_healthy": True,
        "database_connected": supabase is not None,
        "rag_available": get_rag_status() == "optimized",
        "endpoints_registered": len(registered_routers),
        "direct_access": True,
        "cors_enabled": True,
        "recommended_frontend_config": {
            "api_base_url": "https://expert-app-cngws.ondigitalocean.app",
            "endpoints": {
                "ask_public": "/api/v1/expert/ask-public",
                "ask_authenticated": "/api/v1/expert/ask",
                "topics": "/api/v1/expert/topics", 
                "feedback": "/api/v1/expert/feedback",
                "health": "/health"
            }
        }
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
            "external_routers": f"{len(registered_routers)} included"
        },
        config={
            "source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "environment": os.getenv('ENV', 'production')
        },
        database_status=db_status,
        rag_status=get_rag_status()
    )

# =============================================================================
# AUTHENTICATION ENDPOINTS (DIRECT)
# =============================================================================

@app.post("/api/v1/auth/register")
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

@app.post("/api/v1/auth/login")
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

@app.post("/api/v1/auth/logout")
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

@app.get("/api/v1/auth/profile")
async def get_profile(user: UserProfile = Depends(get_current_user)):
    """Get user profile"""
    return user

# =============================================================================
# EXPERT SYSTEM ENDPOINTS (DIRECT)
# =============================================================================

@app.post("/api/v1/expert/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask a question without authentication - Multi-language + Performance modes"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Le texte de la question est requis")
    
    try:
        result = await process_question_with_rag(
            question=request.text,
            user=None,
            language=request.language or "fr",
            speed_mode=request.speed_mode or "balanced"
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

@app.post("/api/v1/expert/ask", response_model=ExpertResponse)
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

@app.get("/api/v1/expert/history", response_model=HistoryResponse)
async def get_history(
    page: int = 1, 
    per_page: int = 20,
    user: UserProfile = Depends(get_current_user)
):
    """Get conversation history"""
    try:
        history_data = await get_user_conversations(user.id, page, per_page)
        return HistoryResponse(**history_data)
    except Exception as e:
        logger.error(f"❌ Error getting history: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'historique")

@app.get("/api/v1/expert/topics", response_model=TopicsResponse)
async def get_topics(user: UserProfile = Depends(get_current_user)):
    """Get suggested topics"""
    try:
        # Topics based on user type
        if user.user_type == "professional":
            topics = [
                {"title": "Protocoles de vaccination avancés", "category": "sante"},
                {"title": "Diagnostic différentiel maladies", "category": "diagnostic"},
                {"title": "Analyse performance comparative", "category": "performance"},
                {"title": "Résistance aux antibiotiques", "category": "medicaments"},
                {"title": "Nutrition de précision", "category": "nutrition"}
            ]
            keywords = ["diagnostic", "protocole", "analyse", "résistance", "précision"]
        else:  # producer
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
            user_type_specific=True
        )
    except Exception as e:
        logger.error(f"❌ Error getting topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des sujets")

@app.get("/api/v1/expert/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    context: Optional[str] = None,
    user: UserProfile = Depends(get_current_user)
):
    """Get question suggestions"""
    try:
        # Get recent conversations for context
        recent_convs = await get_user_conversations(user.id, 1, 5)
        has_history = len(recent_convs["conversations"]) > 0
        
        # Base suggestions by user type
        if user.user_type == "professional":
            suggestions = [
                "Quel protocole de vaccination recommandez-vous pour les Ross 308?",
                "Comment diagnostiquer une entérite nécrotique?",
                "Quels sont les standards de performance à 35 jours?",
                "Comment gérer la résistance aux coccidiostatiques?"
            ]
        else:  # producer
            suggestions = [
                "Quelle température maintenir au jour 14?",
                "Comment améliorer l'indice de conversion?",
                "Mes poulets mangent moins, que faire?",
                "Comment détecter un problème sanitaire?"
            ]
        
        return SuggestionsResponse(
            suggestions=suggestions,
            context_aware=context is not None,
            based_on_history=has_history
        )
    except Exception as e:
        logger.error(f"❌ Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des suggestions")

@app.post("/api/v1/expert/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    user: UserProfile = Depends(get_current_user)
):
    """Submit feedback for a question/answer"""
    try:
        await save_feedback(user.id, feedback.question_id, feedback.rating, feedback.feedback)
        
        logger.info(f"📝 Feedback received from {user.email}: rating={feedback.rating}")
        
        return {
            "status": "received",
            "message": "Merci pour votre retour !",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"❌ Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du feedback")

# =============================================================================
# ADMIN ENDPOINTS (DIRECT) - Only if admin router not available
# =============================================================================

if "admin" not in registered_routers:
    @app.get("/api/v1/admin/stats")
    async def get_admin_stats(user: UserProfile = Depends(require_user_type(["admin"]))):
        """Get system statistics - Admin only"""
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")
        
        try:
            # Get basic stats
            users_count = supabase.table('users').select('id', count='exact').execute().count or 0
            conversations_count = supabase.table('conversations').select('id', count='exact').execute().count or 0
            feedback_count = supabase.table('feedback').select('id', count='exact').execute().count or 0
            
            return {
                "system_status": get_rag_status(),
                "database_status": "connected",
                "users_count": users_count,
                "conversations_count": conversations_count,
                "feedback_count": feedback_count,
                "rag_available": rag_embedder is not None,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "endpoint_source": "direct"
            }
        except Exception as e:
            logger.error(f"❌ Error getting admin stats: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

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
            "api_version": "2.1.3"
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
    logger.info(f"📋 Mode: Hybrid (Direct endpoints + Optional routers)")
    logger.info(f"📊 External routers: {', '.join(registered_routers) if registered_routers else 'None'}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )