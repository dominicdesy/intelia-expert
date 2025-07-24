"""
Intelia Expert - API Backend Complète - OPTIMIZED VERSION
Multi-langue + Performance Boost
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
from supabase import create_client, Client
import jwt

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

# Global instances
rag_embedder: Optional[Any] = None
supabase: Optional[Client] = None
security = HTTPBearer()

# =============================================================================
# MULTI-LANGUAGE SUPPORT - PROMPTS OPTIMISÉS
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
# SUPABASE INITIALIZATION - SAME AS BEFORE
# =============================================================================

def initialize_supabase():
    """Initialize Supabase client - FIXED VERSION"""
    global supabase
    
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Supabase credentials not found in environment")
            return False
        
        logger.info(f"🔗 Connecting to Supabase: {supabase_url[:50]}...")
        
        # Create client without any proxy parameter
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
# PYDANTIC MODELS - SAME AS BEFORE
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
    """Request model for expert questions - ENHANCED"""
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

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    services: Dict[str, str]
    config: Dict[str, str]
    database_status: str
    rag_status: str

# =============================================================================
# AUTHENTICATION & AUTHORIZATION - SAME AS BEFORE
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

# =============================================================================
# RAG SYSTEM INITIALIZATION - OPTIMIZED
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
# OPTIMIZED QUESTION PROCESSING - MULTI-LANGUAGE + PERFORMANCE
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
            config = performance_config.get("fast", {"model": "gpt-3.5-turbo", "max_tokens": 300, "timeout": 8})
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

# =============================================================================
# DATABASE FUNCTIONS - SAME AS BEFORE
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

# =============================================================================
# LIFESPAN MANAGEMENT - SAME AS BEFORE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Intelia Expert API...")
    
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    logger.info("✅ Application created successfully")
                logger.info(f"📊 Multi-language support: FR, EN, ES, PT, DE, NL, PL")
    logger.info(f"⚡ Performance modes: fast, balanced, quality")
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
# API ENDPOINTS - ENHANCED WITH MULTI-LANGUAGE + PERFORMANCE
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Intelia Expert API with Multi-Language RAG + Performance Optimized",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
        "api_version": "2.1.0",
        "database": supabase is not None,
        "rag_system": get_rag_status(),
        "supported_languages": ["fr", "en", "es", "pt", "de", "nl", "pl"],
        "performance_modes": ["fast", "balanced", "quality"]
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
            "rag_system": get_rag_status()
        },
        config={
            "source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "environment": os.getenv('ENV', 'production')
        },
        database_status=db_status,
        rag_status=get_rag_status()
    )

# =============================================================================
# EXPERT SYSTEM ENDPOINTS - ENHANCED
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