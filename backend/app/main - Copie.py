"""
Intelia Expert - API Backend Complète
Architecture Option A: Supabase Backend + RAG + Specs Compliant
SUPPRIMÉ: Microsoft Graph, Compass, emails
AJOUTÉ: Supabase Auth/DB, endpoints manquants, profils utilisateurs
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
# SUPABASE INITIALIZATION
# =============================================================================

def initialize_supabase():
    """Initialize Supabase client"""
    global supabase
    
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Supabase credentials not found in environment")
            return False
            
        supabase = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing Supabase: {e}")
        return False

# =============================================================================
# PYDANTIC MODELS - SELON SPECS
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
    """Request model for expert questions - SPEC COMPLIANT"""
    text: str = Field(..., description="Question text", min_length=1, max_length=2000)
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    context: Optional[str] = Field(None, description="Additional context")

class ExpertResponse(BaseModel):
    """Response model for expert answers - SPEC COMPLIANT"""
    question: str
    response: str
    mode: str
    note: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []
    config_source: str
    timestamp: str
    processing_time: float

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
        # Verify JWT token
        token = credentials.credentials
        jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
        
        if not jwt_secret:
            raise HTTPException(status_code=503, detail="JWT secret not configured")
        
        # Decode token
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        user_id = payload.get('sub')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_data = result.data[0]
        
        # Update last active
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
# RAG SYSTEM INITIALIZATION - SAME AS BEFORE
# =============================================================================

async def initialize_rag_system():
    """Initialize RAG system - Version robuste"""
    global rag_embedder
    
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
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Intelia Expert API...")
    
    # Initialize services
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    # Log final status
    logger.info("✅ Application created successfully")
    logger.info(f"📊 Configuration source: {os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)')}")
    logger.info(f"🌍 Environment: {os.getenv('ENV', 'production')}")
    logger.info(f"🗄️ Database: {'Available' if supabase_success else 'Not Available'}")
    logger.info(f"🤖 RAG modules: {'Available' if rag_embedder else 'Not Available'}")
    
    if rag_embedder and rag_embedder.has_search_engine():
        logger.info("🔍 RAG system: Optimized (with document search)")
    elif rag_embedder:
        logger.info("🔍 RAG system: Ready (fallback mode)")
    else:
        logger.info("🔍 RAG system: Not Available")
    
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure selon vos besoins
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

async def process_question_with_rag(question: str, user: Optional[UserProfile] = None, language: str = "fr") -> Dict[str, Any]:
    """Process question using RAG system with user context"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Processing question: {question[:50]}... (User: {user.email if user else 'Anonymous'})")
        
        if not rag_embedder:
            raise Exception("RAG system not available")
        
        sources = []
        
        # Determine processing mode based on user type and RAG availability
        if rag_embedder.has_search_engine():
            logger.info("🔄 Using optimized mode - RAG with document search")
            
            try:
                # Search for relevant documents
                search_results = rag_embedder.search(question, k=5)
                logger.info(f"🔍 Search completed: {len(search_results)} results found")
                
                if search_results:
                    # Prepare context and sources
                    context_parts = []
                    sources = []
                    
                    for i, result in enumerate(search_results[:3]):
                        context_parts.append(f"Document {i+1}: {result['text'][:500]}...")
                        sources.append({
                            "index": result['index'],
                            "score": result['score'],
                            "preview": result['text'][:200] + "..."
                        })
                    
                    context = "\n\n".join(context_parts)
                    
                    # Use OpenAI with RAG context
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    
                    # Adapt prompt based on user type
                    user_context = ""
                    if user:
                        if user.user_type == "professional":
                            user_context = "Tu réponds à un professionnel de la santé animale. Donne des détails techniques approfondis."
                        elif user.user_type == "producer":
                            user_context = "Tu réponds à un producteur agricole. Privilégie des conseils pratiques et accessibles."
                    
                    system_prompt = f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308.
                    
{user_context}

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
                    answer, mode, note = await fallback_openai_response(question, user, language)
                    
            except Exception as search_error:
                logger.error(f"❌ Search error: {search_error}")
                answer, mode, note = await fallback_openai_response(question, user, language)
        else:
            logger.info("🔄 Using fallback mode - direct OpenAI")
            answer, mode, note = await fallback_openai_response(question, user, language)
        
        processing_time = time.time() - start_time
        
        result = {
            "question": question,
            "response": answer,
            "mode": mode,
            "note": note,
            "sources": sources,
            "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "processing_time": round(processing_time, 2)
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
            answer, mode, note = await fallback_openai_response(question, user, language)
            return {
                "question": question,
                "response": answer,
                "mode": f"{mode}_emergency",
                "note": f"Mode d'urgence activé: {str(e)}",
                "sources": [],
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

async def fallback_openai_response(question: str, user: Optional[UserProfile] = None, language: str = "fr") -> tuple:
    """Fallback response using OpenAI directly"""
    import openai
    
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    # Adapt prompt based on user type
    user_context = ""
    if user:
        if user.user_type == "professional":
            user_context = "Tu réponds à un professionnel de la santé animale. Donne des détails techniques approfondis."
        elif user.user_type == "producer":
            user_context = "Tu réponds à un producteur agricole. Privilégie des conseils pratiques et accessibles."
    
    system_prompt = f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308.

{user_context}

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
# API ENDPOINTS - SELON SPECS COMPLÈTES
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Intelia Expert API with RAG + Supabase",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables (PRODUCTION)'),
        "api_version": "2.0.0",
        "database": supabase is not None,
        "rag_system": get_rag_status()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - SPEC COMPLIANT"""
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
# AUTHENTICATION ENDPOINTS
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
                "id": auth_response.user.id,
                "email": request.email,
                "user_type": request.user_type,
                "full_name": request.full_name,
                "created_at": datetime.utcnow().isoformat(),
                "preferences": {}
            }
            
            supabase.table('users').insert(user_data).execute()
            
            return {
                "message": "User registered successfully",
                "user_id": auth_response.user.id,
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
# EXPERT SYSTEM ENDPOINTS - SELON SPECS
# =============================================================================

@app.post("/api/v1/expert/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest, user: UserProfile = Depends(get_current_user)):
    """Ask a question to the expert system - SPEC COMPLIANT"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Le texte de la question est requis")
    
    try:
        result = await process_question_with_rag(
            question=request.text,
            user=user,
            language=request.language or "fr"
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
    """Get conversation history - SPEC COMPLIANT"""
    try:
        history_data = await get_user_conversations(user.id, page, per_page)
        return HistoryResponse(**history_data)
    except Exception as e:
        logger.error(f"❌ Error getting history: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'historique")

@app.get("/api/v1/expert/topics", response_model=TopicsResponse)
async def get_topics(user: UserProfile = Depends(get_current_user)):
    """Get suggested topics - SPEC COMPLIANT"""
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
    """Get question suggestions - SPEC COMPLIANT"""
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
    """Submit feedback for a question/answer - SPEC COMPLIANT"""
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
# ADMIN ENDPOINTS
# =============================================================================

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
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"❌ Error getting admin stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

# =============================================================================
# PUBLIC ENDPOINTS (NO AUTH REQUIRED)
# =============================================================================

@app.post("/api/v1/expert/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask a question without authentication - Limited functionality"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Le texte de la question est requis")
    
    try:
        result = await process_question_with_rag(
            question=request.text,
            user=None,  # No user context
            language=request.language or "fr"
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

# Deploy trigger: 07/24/2025 03:00:00