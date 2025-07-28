"""
Intelia Expert - API Backend Principal
Version 3.0.0 - Architecture Propre et Modulaire
"""

import os
import sys
import time
import logging
import traceback
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime
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
    jwt = None

# Configuration du path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# VARIABLES GLOBALES
# =============================================================================

rag_embedder: Optional[Any] = None
supabase: Optional[Client] = None
security = HTTPBearer()

# =============================================================================
# IMPORT DES ROUTERS
# =============================================================================

# Import logging router
try:
    from app.api.v1.logging import router as logging_router
    LOGGING_AVAILABLE = True
    logger.info("✅ Module logging importé")
except ImportError as e:
    LOGGING_AVAILABLE = False
    logging_router = None
    logger.warning(f"⚠️ Module logging non disponible: {e}")

# Import expert router
try:
    from app.api.v1.expert import router as expert_router
    EXPERT_ROUTER_AVAILABLE = True
    logger.info("✅ Module expert importé")
except ImportError as e:
    EXPERT_ROUTER_AVAILABLE = False
    expert_router = None
    logger.warning(f"⚠️ Module expert non disponible: {e}")

# Import auth router
try:
    from app.api.v1.auth import router as auth_router
    AUTH_ROUTER_AVAILABLE = True
    logger.info("✅ Module auth importé")
except ImportError as e:
    AUTH_ROUTER_AVAILABLE = False
    auth_router = None
    logger.warning(f"⚠️ Module auth non disponible: {e}")

# Import admin router
try:
    from app.api.v1.admin import router as admin_router
    ADMIN_ROUTER_AVAILABLE = True
    logger.info("✅ Module admin importé")
except ImportError as e:
    ADMIN_ROUTER_AVAILABLE = False
    admin_router = None
    logger.warning(f"⚠️ Module admin non disponible: {e}")

# Import health router
try:
    from app.api.v1.health import router as health_router
    HEALTH_ROUTER_AVAILABLE = True
    logger.info("✅ Module health importé")
except ImportError as e:
    HEALTH_ROUTER_AVAILABLE = False
    health_router = None
    logger.warning(f"⚠️ Module health non disponible: {e}")

# Import system router
try:
    from app.api.v1.system import router as system_router
    SYSTEM_ROUTER_AVAILABLE = True
    logger.info("✅ Module system importé")
except ImportError as e:
    SYSTEM_ROUTER_AVAILABLE = False
    system_router = None
    logger.warning(f"⚠️ Module system non disponible: {e}")

# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

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

# =============================================================================
# CONFIGURATION MULTI-LANGUES
# =============================================================================

LANGUAGE_PROMPTS = {
    "fr": {
        "system_base": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308.""",
        "context_instruction": "Utilise les informations suivantes pour répondre à la question:",
        "response_instruction": "Réponds en français de manière précise et pratique, en te basant sur les documents fournis.",
        "fallback_instruction": "Réponds aux questions de manière précise et pratique en français."
    },
    "en": {
        "system_base": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.""",
        "context_instruction": "Use the following information to answer the question:",
        "response_instruction": "Respond in English precisely and practically, based on the provided documents.",
        "fallback_instruction": "Answer questions precisely and practically in English."
    },
    "es": {
        "system_base": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.""",
        "context_instruction": "Utiliza la siguiente información para responder a la pregunta:",
        "response_instruction": "Responde en español de manera precisa y práctica, basándote en los documentos proporcionados.",
        "fallback_instruction": "Responde a las preguntas de manera precisa y práctica en español."
    }
}

def get_language_prompt(language: str, prompt_type: str) -> str:
    """Get localized prompt for specified language and type."""
    lang = language.lower() if language else "fr"
    if lang not in LANGUAGE_PROMPTS:
        lang = "fr"
    return LANGUAGE_PROMPTS[lang].get(prompt_type, LANGUAGE_PROMPTS["fr"][prompt_type])

# =============================================================================
# INITIALISATION SUPABASE
# =============================================================================

def initialize_supabase():
    """Initialize Supabase client"""
    global supabase
    
    if not SUPABASE_AVAILABLE:
        logger.warning("⚠️ Bibliothèques Supabase non disponibles")
        return False
    
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Credentials Supabase non trouvés")
            return False
        
        logger.info(f"🔗 Connexion à Supabase...")
        supabase = create_client(supabase_url, supabase_key)
        logger.info("✅ Client Supabase créé avec succès")
        return True
            
    except Exception as e:
        logger.error(f"❌ Erreur initialisation Supabase: {e}")
        return False

# =============================================================================
# INITIALISATION RAG
# =============================================================================

async def initialize_rag_system():
    """Initialize RAG system"""
    global rag_embedder
    
    logger.info("🔧 Initialisation du système RAG...")
    
    try:
        from rag.embedder import FastRAGEmbedder
        logger.info("✅ Module RAG embedder importé")
        
        embedder = FastRAGEmbedder(
            api_key=os.getenv('OPENAI_API_KEY'),
            cache_embeddings=True,
            max_workers=2
        )
        logger.info("✅ Instance RAG embedder créée")
        
        # Recherche de l'index existant
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
                    logger.info(f"📁 Index trouvé dans: {index_path}")
                    
                    if embedder.load_index(index_path):
                        logger.info(f"✅ Index RAG chargé depuis {index_path}")
                        index_loaded = True
                        break
        
        rag_embedder = embedder
        
        if index_loaded and embedder.has_search_engine():
            logger.info("✅ Système RAG initialisé avec recherche documentaire")
            return True
        else:
            logger.warning("⚠️ Système RAG initialisé mais sans index valide")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur initialisation RAG: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

# =============================================================================
# TRAITEMENT DES QUESTIONS AVEC RAG
# =============================================================================

async def process_question_with_rag(
    question: str, 
    user: Optional[Any] = None, 
    language: str = "fr",
    speed_mode: str = "balanced"
) -> Dict[str, Any]:
    """Process question using RAG system"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Traitement question: {question[:50]}... (Lang: {language}, Mode: {speed_mode})")
        
        sources = []
        
        # Configuration selon le mode
        performance_config = {
            "fast": {"model": "gpt-3.5-turbo", "k": 2, "max_tokens": 300, "timeout": 8},
            "balanced": {"model": "gpt-3.5-turbo", "k": 3, "max_tokens": 500, "timeout": 12},
            "quality": {"model": "gpt-4o-mini", "k": 5, "max_tokens": 800, "timeout": 20}
        }
        
        config = performance_config.get(speed_mode, performance_config["balanced"])
        
        # Utiliser RAG si disponible
        if rag_embedder and rag_embedder.has_search_engine():
            logger.info(f"🔄 Utilisation RAG avec recherche documentaire (k={config['k']})")
            
            try:
                search_results = rag_embedder.search(question, k=config["k"])
                logger.info(f"🔍 Recherche terminée: {len(search_results)} résultats")
                
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
                    
                    # Utiliser OpenAI avec contexte RAG
                    import openai
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    
                    system_base = get_language_prompt(language, "system_base")
                    context_instruction = get_language_prompt(language, "context_instruction")
                    response_instruction = get_language_prompt(language, "response_instruction")
                    
                    system_prompt = f"""{system_base}

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
                    note = f"Réponse basée sur {len(search_results)} documents"
                    
                else:
                    logger.info("🔄 Aucun document pertinent trouvé - utilisation fallback")
                    answer, mode, note = await fallback_openai_response(question, language, config)
                    
            except Exception as search_error:
                logger.error(f"❌ Erreur recherche: {search_error}")
                answer, mode, note = await fallback_openai_response(question, language, config)
        else:
            logger.info("🔄 Mode fallback - OpenAI direct")
            answer, mode, note = await fallback_openai_response(question, language, config)
        
        processing_time = time.time() - start_time
        
        return {
            "question": question,
            "response": answer,
            "mode": mode,
            "note": note,
            "sources": sources,
            "config_source": os.getenv('CONFIG_SOURCE', 'Environment Variables'),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "processing_time": round(processing_time, 2),
            "language": language
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement question: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de traitement: {str(e)}")

async def fallback_openai_response(question: str, language: str = "fr", config: dict = None) -> tuple:
    """Fallback response using OpenAI directly"""
    try:
        import openai
        
        if config is None:
            config = {"model": "gpt-3.5-turbo", "max_tokens": 500, "timeout": 12}
        
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        system_base = get_language_prompt(language, "system_base")
        fallback_instruction = get_language_prompt(language, "fallback_instruction")
        
        system_prompt = f"{system_base}\n\n{fallback_instruction}"

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
        note = "Réponse sans recherche documentaire"
        
        return answer, mode, note
    
    except Exception as e:
        logger.warning(f"⚠️ Erreur OpenAI fallback: {e}")
        
        fallback_responses = {
            "fr": "Je suis temporairement indisponible. Veuillez réessayer plus tard.",
            "en": "I am temporarily unavailable. Please try again later.",
            "es": "Estoy temporalmente no disponible. Inténtelo de nuevo más tarde."
        }
        
        answer = fallback_responses.get(language, fallback_responses["fr"])
        mode = "static_fallback"
        note = "Service temporairement indisponible"
        
        return answer, mode, note

# =============================================================================
# FONCTIONS HELPER
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
# GESTION DU CYCLE DE VIE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Démarrage Intelia Expert API v3.0.0...")
    
    # Initialisation des services
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    # Exposer le RAG dans app.state pour les routers
    app.state.rag_embedder = rag_embedder
    app.state.process_question_with_rag = process_question_with_rag
    app.state.get_rag_status = get_rag_status
    
    # Logs de statut
    logger.info("✅ Application créée avec succès")
    logger.info("📊 Support multi-langues: FR, EN, ES")
    logger.info("⚡ Modes de performance: fast, balanced, quality")
    logger.info(f"🗄️ Base de données: {'Disponible' if supabase_success else 'Non disponible'}")
    logger.info(f"🤖 Modules RAG: {'Disponibles' if rag_embedder else 'Non disponibles'}")
    
    if rag_embedder and rag_embedder.has_search_engine():
        logger.info("🔍 Système RAG: Optimisé (avec recherche documentaire)")
    elif rag_embedder:
        logger.info("🔍 Système RAG: Prêt (mode fallback)")
    else:
        logger.info("🔍 Système RAG: Non disponible")
    
    yield
    
    logger.info("🛑 Arrêt de Intelia Expert API...")

# =============================================================================
# APPLICATION FASTAPI
# =============================================================================

app = FastAPI(
    title="Intelia Expert API",
    description="Assistant IA Expert pour la Santé et Nutrition Animale",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configuration CORS
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
# MONTAGE DES ROUTERS AVEC PRÉFIXES CORRECTS
# =============================================================================

# NOTE ARCHITECTURE:
# - Les routers sont montés avec des préfixes complets incluant /api
# - URLs finales: /api/v1/expert/ask-public, /api/v1/auth/login, etc.
# - Pas besoin de reverse proxy pour ajouter /api (simplicité)
# - URLs identiques en développement et production

# Router logging
if LOGGING_AVAILABLE and logging_router:
    try:
        app.include_router(logging_router, prefix="/api/v1")
        logger.info("✅ Router logging monté sur /api/v1")
    except Exception as e:
        logger.error(f"❌ Erreur montage router logging: {e}")

# Router expert - CORRECTION PRINCIPALE
if EXPERT_ROUTER_AVAILABLE and expert_router:
    try:
        app.include_router(expert_router, prefix="/api/v1/expert")
        logger.info("✅ Router expert monté sur /api/v1/expert")
        
        # Configurer les références RAG pour le router expert
        if hasattr(expert_router, 'setup_rag_references'):
            expert_router.setup_rag_references(app)
            logger.info("✅ Références RAG configurées pour router expert")
    except Exception as e:
        logger.error(f"❌ Erreur montage router expert: {e}")

# Router auth
if AUTH_ROUTER_AVAILABLE and auth_router:
    try:
        app.include_router(auth_router, prefix="/api/v1/auth")
        logger.info("✅ Router auth monté sur /api/v1/auth")
    except Exception as e:
        logger.error(f"❌ Erreur montage router auth: {e}")

# Router admin
if ADMIN_ROUTER_AVAILABLE and admin_router:
    try:
        app.include_router(admin_router, prefix="/api/v1/admin")
        logger.info("✅ Router admin monté sur /api/v1/admin")
    except Exception as e:
        logger.error(f"❌ Erreur montage router admin: {e}")

# Router health  
if HEALTH_ROUTER_AVAILABLE and health_router:
    try:
        app.include_router(health_router, prefix="/api/v1")
        logger.info("✅ Router health monté sur /api/v1")
    except Exception as e:
        logger.error(f"❌ Erreur montage router health: {e}")

# Router system
if SYSTEM_ROUTER_AVAILABLE and system_router:
    try:
        app.include_router(system_router, prefix="/api/v1/system")
        logger.info("✅ Router system monté sur /api/v1/system")
    except Exception as e:
        logger.error(f"❌ Erreur montage router system: {e}")

# =============================================================================
# ENDPOINTS DE BASE
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Endpoint racine"""
    return {
        "message": "Intelia Expert API v3.0.0",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "api_version": "3.0.0",
        "database": supabase is not None,
        "rag_system": get_rag_status(),
        "routers": {
            "logging": LOGGING_AVAILABLE,
            "expert": EXPERT_ROUTER_AVAILABLE,
            "auth": AUTH_ROUTER_AVAILABLE,
            "admin": ADMIN_ROUTER_AVAILABLE,
            "health": HEALTH_ROUTER_AVAILABLE,
            "system": SYSTEM_ROUTER_AVAILABLE
        },
        "supported_languages": ["fr", "en", "es"],
        "available_endpoints": [
            "/api/v1/expert/ask-public",
            "/api/v1/expert/topics",
            "/api/v1/health",
            "/docs",
            "/debug/routers"
        ]
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        services={
            "api": "running",
            "database": "connected" if supabase else "disconnected",
            "rag_system": get_rag_status()
        },
        config={
            "environment": os.getenv('ENV', 'production')
        },
        database_status="connected" if supabase else "disconnected",
        rag_status=get_rag_status()
    )

# =============================================================================
# ENDPOINTS DE DEBUG
# =============================================================================

@app.get("/debug/routers")
async def debug_routers():
    """Debug endpoint pour voir les routers chargés"""
    return {
        "routers_status": {
            "logging": LOGGING_AVAILABLE,
            "expert": EXPERT_ROUTER_AVAILABLE,
            "auth": AUTH_ROUTER_AVAILABLE,
            "admin": ADMIN_ROUTER_AVAILABLE,
            "health": HEALTH_ROUTER_AVAILABLE,
            "system": SYSTEM_ROUTER_AVAILABLE
        },
        "available_routes": [
            {
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, 'methods') else ["GET"],
                "name": getattr(route, 'name', 'unnamed')
            } for route in app.routes
        ],
        "expert_routes": [
            {
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, 'methods') else ["GET"]
            } for route in app.routes if '/expert/' in str(getattr(route, 'path', ''))
        ],
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0"
    }

@app.get("/debug/structure")
async def debug_structure():
    """Debug endpoint pour voir la structure du projet"""
    try:
        structure = {}
        
        # Lister les modules
        api_v1_path = os.path.join(backend_dir, "app", "api", "v1")
        if os.path.exists(api_v1_path):
            structure["api_v1_modules"] = [
                f for f in os.listdir(api_v1_path) 
                if f.endswith('.py') and not f.startswith('__')
            ]
        
        rag_path = os.path.join(backend_dir, "rag")
        if os.path.exists(rag_path):
            structure["rag_modules"] = [
                f for f in os.listdir(rag_path) 
                if f.endswith('.py') and not f.startswith('__')
            ]
        
        return {
            "project_structure": structure,
            "backend_dir": backend_dir,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# GESTIONNAIRES D'ERREURS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire d'exceptions HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'exceptions générales"""
    logger.error(f"❌ Exception non gérée: {exc}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erreur interne du serveur",
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path)
        }
    )

# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Démarrage de Intelia Expert API sur {host}:{port}")
    logger.info(f"📋 Version: 3.0.0 - Architecture Propre + Préfixes Corrigés")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )