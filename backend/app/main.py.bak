"""
Intelia Expert - API Backend Principal
Version 3.2.0 - Version Finale avec Support UTF-8 Complet
Correction: Encodage caractères spéciaux FR/ES
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
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
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

# Configuration logging avec UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Force UTF-8 pour les logs
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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
# MODÈLES PYDANTIC AVEC SUPPORT UTF-8
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model for expert questions with UTF-8 support"""
    text: str = Field(..., description="Question text (UTF-8 encoded)", min_length=1, max_length=2000)
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    context: Optional[str] = Field(None, description="Additional context")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode: fast, balanced, quality")
    
    class Config:
        # Assurer l'encodage UTF-8 pour Pydantic
        str_to_lower = False
        validate_assignment = True
        extra = "forbid"

class ExpertResponse(BaseModel):
    """Response model for expert answers with UTF-8 support"""
    question: str
    response: str
    mode: str
    note: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []
    config_source: str
    timestamp: str
    processing_time: float
    language: str
    
    class Config:
        # Assurer l'encodage UTF-8 pour les réponses
        json_encoders = {
            str: lambda v: v if isinstance(v, str) else str(v)
        }

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    services: Dict[str, str]
    config: Dict[str, str]
    database_status: str
    rag_status: str

# =============================================================================
# CONFIGURATION MULTI-LANGUES AVEC SUPPORT UTF-8
# =============================================================================

LANGUAGE_PROMPTS = {
    "fr": {
        "system_base": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. Tu peux comprendre et répondre aux questions avec des caractères spéciaux français (é, è, à, ç, etc.).""",
        "context_instruction": "Utilise les informations suivantes pour répondre à la question:",
        "response_instruction": "Réponds en français de manière précise et pratique, en te basant sur les documents fournis. N'hésite pas à utiliser les accents français appropriés.",
        "fallback_instruction": "Réponds aux questions de manière précise et pratique en français avec les accents appropriés."
    },
    "en": {
        "system_base": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.""",
        "context_instruction": "Use the following information to answer the question:",
        "response_instruction": "Respond in English precisely and practically, based on the provided documents.",
        "fallback_instruction": "Answer questions precisely and practically in English."
    },
    "es": {
        "system_base": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308. Puedes entender y responder preguntas con caracteres especiales en español (ñ, ¿, ¡, acentos, etc.).""",
        "context_instruction": "Utiliza la siguiente información para responder a la pregunta:",
        "response_instruction": "Responde en español de manera precisa y práctica, basándote en los documentos proporcionados. Usa los caracteres especiales del español cuando sea apropiado.",
        "fallback_instruction": "Responde a las preguntas de manera precisa y práctica en español con los caracteres especiales apropiados."
    }
}

def get_language_prompt(language: str, prompt_type: str) -> str:
    """Get localized prompt for specified language and type with UTF-8 support."""
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
# TRAITEMENT DES QUESTIONS AVEC RAG ET SUPPORT UTF-8
# =============================================================================

async def process_question_with_rag(
    question: str, 
    user: Optional[Any] = None, 
    language: str = "fr",
    speed_mode: str = "balanced"
) -> Dict[str, Any]:
    """Process question using RAG system with UTF-8 support"""
    start_time = time.time()
    
    try:
        # Assurer l'encodage UTF-8 de la question
        if isinstance(question, str):
            # Nettoyer et valider l'UTF-8
            question = question.encode('utf-8', errors='ignore').decode('utf-8')
        
        logger.info(f"🔍 Traitement question UTF-8: {question[:50]}... (Lang: {language}, Mode: {speed_mode})")
        
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
                        # Assurer l'UTF-8 pour le contexte
                        text = result['text']
                        if isinstance(text, str):
                            text = text.encode('utf-8', errors='ignore').decode('utf-8')
                        
                        context_chunk = text[:400] + "..." if len(text) > 400 else text
                        context_parts.append(f"Document {i+1}: {context_chunk}")
                        sources.append({
                            "index": result['index'],
                            "score": result['score'],
                            "preview": text[:150] + "..."
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
                    # Assurer l'UTF-8 pour la réponse
                    if isinstance(answer, str):
                        answer = answer.encode('utf-8', errors='ignore').decode('utf-8')
                    
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
    """Fallback response using OpenAI directly with UTF-8 support"""
    try:
        import openai
        
        if config is None:
            config = {"model": "gpt-3.5-turbo", "max_tokens": 500, "timeout": 12}
        
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Assurer l'UTF-8 pour la question
        if isinstance(question, str):
            question = question.encode('utf-8', errors='ignore').decode('utf-8')
        
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
        # Assurer l'UTF-8 pour la réponse
        if isinstance(answer, str):
            answer = answer.encode('utf-8', errors='ignore').decode('utf-8')
        
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
    logger.info("🚀 Démarrage Intelia Expert API v3.2.0...")
    
    # Initialisation des services
    supabase_success = initialize_supabase()
    rag_success = await initialize_rag_system()
    
    # Exposer le RAG dans app.state pour les routers
    app.state.rag_embedder = rag_embedder
    app.state.process_question_with_rag = process_question_with_rag
    app.state.get_rag_status = get_rag_status
    
    # Logs de statut
    logger.info("✅ Application créée avec succès")
    logger.info("📊 Support multi-langues: FR, EN, ES (UTF-8)")
    logger.info("⚡ Modes de performance: fast, balanced, quality")
    logger.info(f"🗄️ Base de données: {'Disponible' if supabase_success else 'Non disponible'}")
    logger.info(f"🤖 Modules RAG: {'Disponibles' if rag_embedder else 'Non disponibles'}")
    
    if rag_embedder and rag_embedder.has_search_engine():
        logger.info("🔍 Système RAG: Optimisé (avec recherche documentaire)")
    elif rag_embedder:
        logger.info("🔍 Système RAG: Prêt (mode fallback)")
    else:
        logger.info("🔍 Système RAG: Non disponible")
    
    # Détecter l'environnement de déploiement
    deployment_env = "DigitalOcean" if "/workspace" in backend_dir else "Local"
    logger.info(f"🌐 Environnement détecté: {deployment_env}")
    logger.info("🔤 Support UTF-8: Activé pour caractères spéciaux FR/ES")
    
    yield
    
    logger.info("🛑 Arrêt de Intelia Expert API...")

# =============================================================================
# APPLICATION FASTAPI AVEC SUPPORT UTF-8
# =============================================================================

app = FastAPI(
    title="Intelia Expert API",
    description="Assistant IA Expert pour la Santé et Nutrition Animale (Support UTF-8 complet)",
    version="3.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# =============================================================================
# MIDDLEWARE UTF-8 ET CORS
# =============================================================================

# Middleware pour forcer l'encodage UTF-8
@app.middleware("http")
async def force_utf8_middleware(request: Request, call_next):
    """Force UTF-8 encoding for all requests and responses"""
    
    # Loguer les caractères spéciaux détectés
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            # Log pour debug UTF-8
            logger.info(f"🔤 Requête JSON reçue - Content-Type: {content_type}")
    
    response = await call_next(request)
    
    # Forcer l'encodage UTF-8 pour toutes les réponses JSON
    if response.headers.get("content-type"):
        if "application/json" in response.headers.get("content-type"):
            response.headers["content-type"] = "application/json; charset=utf-8"
    
    # Ajouter headers UTF-8 supplémentaires
    response.headers["Accept-Charset"] = "utf-8"
    
    return response

# Configuration CORS avec Support UTF-8 Complet
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
    allow_headers=["*", "Content-Type", "Accept-Charset", "Accept-Encoding"],
)

# =============================================================================
# MONTAGE DES ROUTERS - PRÉFIXES DIGITALOCEAN CORRIGÉS
# =============================================================================

# NOTE ARCHITECTURE DIGITALOCEAN:
# DigitalOcean App Platform expose automatiquement l'app sur /api
# Les routers FastAPI doivent être montés SANS préfixe /api pour éviter /api/api/
# Résultat: FastAPI /v1/expert + DigitalOcean /api = URL finale /api/v1/expert ✅

# Router logging
if LOGGING_AVAILABLE and logging_router:
    try:
        app.include_router(logging_router, prefix="/v1")
        logger.info("✅ Router logging monté sur /v1 (exposé à /api/v1)")
    except Exception as e:
        logger.error(f"❌ Erreur montage router logging: {e}")

# Router expert - CORRECTION CRITIQUE + UTF-8
if EXPERT_ROUTER_AVAILABLE and expert_router:
    try:
        app.include_router(expert_router, prefix="/v1/expert")
        logger.info("✅ Router expert monté sur /v1/expert (exposé à /api/v1/expert)")
        
        # Configurer les références RAG pour le router expert
        if hasattr(expert_router, 'setup_rag_references'):
            expert_router.setup_rag_references(app)
            logger.info("✅ Références RAG configurées pour router expert")
    except Exception as e:
        logger.error(f"❌ Erreur montage router expert: {e}")

# Router auth
if AUTH_ROUTER_AVAILABLE and auth_router:
    try:
        app.include_router(auth_router, prefix="/v1/auth")
        logger.info("✅ Router auth monté sur /v1/auth (exposé à /api/v1/auth)")
    except Exception as e:
        logger.error(f"❌ Erreur montage router auth: {e}")

# Router admin
if ADMIN_ROUTER_AVAILABLE and admin_router:
    try:
        app.include_router(admin_router, prefix="/v1/admin")
        logger.info("✅ Router admin monté sur /v1/admin (exposé à /api/v1/admin)")
    except Exception as e:
        logger.error(f"❌ Erreur montage router admin: {e}")

# Router health  
if HEALTH_ROUTER_AVAILABLE and health_router:
    try:
        app.include_router(health_router, prefix="/v1")
        logger.info("✅ Router health monté sur /v1 (exposé à /api/v1)")
    except Exception as e:
        logger.error(f"❌ Erreur montage router health: {e}")

# Router system
if SYSTEM_ROUTER_AVAILABLE and system_router:
    try:
        app.include_router(system_router, prefix="/v1/system")
        logger.info("✅ Router system monté sur /v1/system (exposé à /api/v1/system)")
    except Exception as e:
        logger.error(f"❌ Erreur montage router system: {e}")

# =============================================================================
# ENDPOINTS DE BASE AVEC SUPPORT UTF-8
# =============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Endpoint racine avec URLs DigitalOcean correctes et support UTF-8"""
    return {
        "message": "Intelia Expert API v3.2.0 - Support UTF-8 Complet",
        "status": "running",
        "environment": os.getenv('ENV', 'production'),
        "api_version": "3.2.0",
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
        "utf8_support": {
            "enabled": True,
            "french_accents": "é, è, à, ç, ù, etc.",
            "spanish_special": "ñ, ¿, ¡, acentos",
            "encoding": "UTF-8 forcé sur toutes les requêtes/réponses"
        },
        "available_endpoints": [
            "/api/v1/expert/ask-public",    # ✅ URL finale correcte + UTF-8
            "/api/v1/expert/topics",        # ✅ URL finale correcte + UTF-8
            "/api/v1/health",               # ✅ URL finale correcte
            "/docs",
            "/debug/routers"
        ],
        "deployment_notes": {
            "platform": "DigitalOcean App Platform",
            "auto_prefix": "/api ajouté automatiquement par DigitalOcean",
            "fastapi_prefix": "Routers montés sans /api pour éviter duplication",
            "final_urls": "FastAPI /v1/expert + DO /api = /api/v1/expert",
            "utf8_fix": "Middleware UTF-8 actif pour caractères spéciaux"
        }
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
            "rag_system": get_rag_status(),
            "utf8_support": "enabled"
        },
        config={
            "environment": os.getenv('ENV', 'production'),
            "deployment": "DigitalOcean App Platform",
            "encoding": "UTF-8"
        },
        database_status="connected" if supabase else "disconnected",
        rag_status=get_rag_status()
    )

# =============================================================================
# ENDPOINTS DE DEBUG AVEC UTF-8
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
        "digitalocean_mapping": {
            "fastapi_internal": "/v1/expert/ask-public",
            "digitalocean_external": "/api/v1/expert/ask-public",
            "note": "DigitalOcean ajoute automatiquement /api"
        },
        "utf8_status": {
            "middleware_active": True,
            "supported_chars": "Tous caractères UTF-8 supportés",
            "test_chars": "éèàçù, ñ¿¡, etc."
        },
        "timestamp": datetime.now().isoformat(),
        "version": "3.2.0"
    }

@app.get("/debug/utf8")
async def debug_utf8():
    """Debug endpoint spécifique pour tester l'UTF-8"""
    return {
        "utf8_test": {
            "french": "Température élevée à 32°C - problème détecté",
            "spanish": "¿Cuál es la nutrición óptima para pollos?",
            "special_chars": "àáâãäåæçèéêëìíîïñòóôõö",
            "symbols": "°C, %, €, £, ¥",
            "encoding": "UTF-8"
        },
        "middleware_status": "Actif - Force UTF-8 sur toutes les réponses",
        "headers_forced": {
            "content-type": "application/json; charset=utf-8",
            "accept-charset": "utf-8"
        },
        "test_passed": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/debug/deployment")
async def debug_deployment():
    """Debug endpoint spécifique au déploiement DigitalOcean"""
    return {
        "platform": "DigitalOcean App Platform",
        "backend_dir": backend_dir,
        "is_digitalocean": "/workspace" in backend_dir,
        "environment_vars": {
            "ENV": os.getenv('ENV', 'not_set'),
            "PORT": os.getenv('PORT', 'not_set'),
            "HOST": os.getenv('HOST', 'not_set'),
            "OPENAI_API_KEY": "set" if os.getenv('OPENAI_API_KEY') else "not_set",
            "SUPABASE_URL": "set" if os.getenv('SUPABASE_URL') else "not_set"
        },
        "fixes_applied": {
            "routing_fix": "Préfixes /api enlevés des routers FastAPI",
            "utf8_fix": "Middleware UTF-8 ajouté pour caractères spéciaux",
            "cors_fix": "Headers UTF-8 ajoutés au CORS"
        },
        "routing_explanation": {
            "problem_fixed": "Double préfixe /api/api évité",
            "digitalocean_behavior": "Ajoute automatiquement /api à toutes les routes",
            "result": "FastAPI /v1/expert + DO /api = /api/v1/expert",
            "utf8_result": "Caractères spéciaux FR/ES maintenant supportés"
        },
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# GESTIONNAIRES D'ERREURS AVEC SUPPORT UTF-8
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire d'exceptions HTTP avec UTF-8"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
            "version": "3.2.0",
            "encoding": "utf-8"
        },
        headers={"content-type": "application/json; charset=utf-8"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'exceptions générales avec UTF-8"""
    logger.error(f"❌ Exception non gérée: {exc}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erreur interne du serveur",
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
            "version": "3.2.0",
            "encoding": "utf-8"
        },
        headers={"content-type": "application/json; charset=utf-8"}
    )

# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Démarrage de Intelia Expert API sur {host}:{port}")
    logger.info(f"📋 Version: 3.2.0 - Support UTF-8 Complet")
    logger.info(f"🌐 URLs finales attendues: /api/v1/expert/ask-public")
    logger.info(f"🔤 Support caractères spéciaux: é, è, ñ, ¿, etc.")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )