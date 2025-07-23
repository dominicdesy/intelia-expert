# backend/app/main.py
"""
Intelia Expert Backend - Point d'entrée principal
Configuration sécurisée + Système RAG intégré
Structure adaptée pour le dossier backend/ de DigitalOcean
"""

import logging
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import de notre gestionnaire de configuration sécurisé
from core.config.config import config_manager, validate_startup, get_config

# Ajouter le répertoire backend au path pour accéder aux modules rag et core
backend_dir = Path(__file__).parent.parent  # backend/app/ -> backend/
sys.path.insert(0, str(backend_dir))

# Imports RAG avec gestion d'erreur robuste
RAG_MODULES_AVAILABLE = False
rag_system = None

try:
    # Import depuis backend/rag/
    from rag.embedder import EnhancedDocumentEmbedder
    RAG_MODULES_AVAILABLE = True
    print("✅ RAG modules imported successfully")
except ImportError as e:
    print(f"⚠️ RAG modules not available: {e}")
    print(f"   Backend directory: {backend_dir}")
    print(f"   Python path: {sys.path}")

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, get_config('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_rag_system():
    """Initialiser le système RAG avec les chemins backend/"""
    global rag_system
    
    if not RAG_MODULES_AVAILABLE:
        logger.warning("⚠️ RAG modules not available - running in fallback mode")
        return False
    
    try:
        openai_key = config_manager.get_openai_key()
        if not openai_key:
            logger.error("❌ OpenAI API key not configured")
            return False
        
        logger.info("🔧 Initializing RAG system...")
        
        # Initialiser l'embedder
        embedder = EnhancedDocumentEmbedder(
            api_key=openai_key,
            use_hybrid_search=True,
            use_intelligent_routing=True
        )
        
        # Chemins pour l'index dans le contexte backend/
        possible_index_paths = [
            str(backend_dir / 'rag_index'),  # backend/rag_index/
            '/tmp/rag_index',                 # Production DigitalOcean
            './rag_index',                    # Relatif
            str(Path.cwd() / 'rag_index')    # Depuis working directory
        ]
        
        logger.info(f"🔍 Searching for RAG index in paths: {possible_index_paths}")
        
        index_loaded = False
        for index_path in possible_index_paths:
            index_path_obj = Path(index_path)
            if index_path_obj.exists():
                logger.info(f"📁 Found index directory: {index_path}")
                
                # Vérifier les fichiers requis
                required_files = ['index.faiss', 'index.pkl']
                missing_files = []
                
                for req_file in required_files:
                    file_path = index_path_obj / req_file
                    if file_path.exists():
                        logger.info(f"   ✅ Found: {req_file}")
                    else:
                        missing_files.append(req_file)
                        logger.warning(f"   ❌ Missing: {req_file}")
                
                if not missing_files:
                    try:
                        # Tenter de charger l'index
                        if hasattr(embedder, 'search_engine') and embedder.search_engine:
                            embedder.search_engine.load_index(str(index_path))
                            logger.info(f"✅ RAG index loaded successfully from {index_path}")
                            rag_system = embedder
                            index_loaded = True
                            break
                        else:
                            logger.warning("⚠️ Embedder search_engine not available")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load index from {index_path}: {e}")
                        continue
                else:
                    logger.warning(f"⚠️ Index incomplete in {index_path}: missing {missing_files}")
            else:
                logger.debug(f"📂 Index path not found: {index_path}")
        
        if not index_loaded:
            logger.warning("⚠️ No valid RAG index found - will run without document search")
            # Essayer d'initialiser quand même pour les fallbacks
            rag_system = embedder
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing RAG system: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

def create_application() -> FastAPI:
    """Créer l'application FastAPI avec configuration sécurisée et RAG"""
    
    # Validation de la configuration au démarrage
    if not validate_startup():
        logger.error("❌ Configuration validation failed - cannot start application")
        raise RuntimeError("Invalid configuration")
    
    # Initialiser le système RAG
    rag_initialized = initialize_rag_system()
    if rag_initialized:
        logger.info("✅ RAG system initialized successfully")
    else:
        logger.warning("⚠️ RAG system not fully initialized - using fallback mode")
    
    # Création de l'application
    app = FastAPI(
        title="Intelia Expert API",
        description="Assistant IA Expert pour la Santé et Nutrition Animale avec RAG",
        version="2.0.0",
        debug=get_config('DEBUG', False)
    )
    
    # Configuration CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_config('ALLOWED_ORIGINS', ['*']),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes de base
    @app.get("/")
    async def root():
        """Point d'entrée racine avec informations système"""
        status = config_manager.get_status_report()
        return {
            "message": "Intelia Expert API with RAG",
            "status": "running",
            "environment": status['environment'],
            "config_source": status['config_source'],
            "api_version": "2.0.0",
            "rag_modules": RAG_MODULES_AVAILABLE,
            "rag_system": "initialized" if rag_system else "not_available"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check pour monitoring"""
        try:
            validation = config_manager.validate_configuration()
            status = config_manager.get_status_report()
            
            health_status = {
                "status": "healthy",
                "timestamp": "2025-07-23T21:00:00Z",
                "services": {
                    "api": "running",
                    "configuration": "loaded" if validation['openai_key_present'] else "limited",
                    "rag_modules": "available" if RAG_MODULES_AVAILABLE else "not_available",
                    "rag_system": "ready" if rag_system else "fallback",
                    "database": "connected" if validation['database_configured'] else "disconnected"
                },
                "config": {
                    "source": status['config_source'],
                    "environment": status['environment']
                }
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": "2025-07-23T21:00:00Z"
                }
            )
    
    @app.post("/api/v1/expert/ask")
    async def ask_expert(question: dict):
        """Endpoint principal pour les questions avec RAG intégré"""
        global rag_system
        
        openai_key = config_manager.get_openai_key()
        if not openai_key:
            raise HTTPException(
                status_code=503, 
                detail="Service non disponible - clé API OpenAI non configurée"
            )
        
        user_question = question.get('text', '').strip()
        if not user_question:
            raise HTTPException(
                status_code=400,
                detail="Le texte de la question est requis"
            )
        
        logger.info(f"🔍 Processing question: {user_question[:100]}...")
        
        try:
            # Mode RAG complet si disponible
            if rag_system and RAG_MODULES_AVAILABLE:
                try:
                    # Rechercher dans la base documentaire
                    if hasattr(rag_system, 'search_documents'):
                        search_results = rag_system.search_documents(user_question, k=5)
                        
                        if search_results and len(search_results) > 0:
                            # Construire le contexte
                            context_pieces = []
                            sources = []
                            
                            for doc, score in search_results:
                                if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                                    context_pieces.append(doc.page_content[:1000])  # Limiter la taille
                                    source = doc.metadata.get('source_file', 'document')
                                    if source not in sources:
                                        sources.append(source)
                            
                            context = "\n\n---\n\n".join(context_pieces)
                            
                            # Générer la réponse avec OpenAI
                            try:
                                from openai import OpenAI
                                client = OpenAI(api_key=openai_key)
                                
                                system_prompt = """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 

Réponds de manière professionnelle et précise en te basant UNIQUEMENT sur le contexte documentaire fourni.

Règles importantes:
- Utilise seulement les informations du contexte documentaire
- Si les données spécifiques (températures, poids, FCR) sont mentionnées, cite-les exactement
- Si l'information n'est pas dans le contexte, dis-le clairement
- Réponds dans la même langue que la question
- Sois concis mais complet (maximum 400 mots)"""

                                user_prompt = f"""Contexte documentaire:
{context}

Question: {user_question}

Réponds en te basant uniquement sur le contexte documentaire ci-dessus."""

                                response = client.chat.completions.create(
                                    model="gpt-4o",
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": user_prompt}
                                    ],
                                    max_tokens=600,
                                    temperature=0.1
                                )
                                
                                answer = response.choices[0].message.content
                                
                                return {
                                    "question": user_question,
                                    "answer": answer,
                                    "sources": sources,
                                    "documents_found": len(search_results),
                                    "mode": "rag_with_documents",
                                    "config_source": config_manager.config_source
                                }
                                
                            except Exception as openai_error:
                                logger.error(f"❌ OpenAI API error: {openai_error}")
                                raise HTTPException(
                                    status_code=500,
                                    detail=f"Erreur lors de la génération de la réponse: {str(openai_error)}"
                                )
                        
                        else:
                            # Aucun document trouvé - fallback
                            logger.info("📄 No relevant documents found in RAG index")
                            
                except Exception as rag_error:
                    logger.error(f"❌ RAG search error: {rag_error}")
                    # Continue vers le fallback
            
            # Mode fallback : OpenAI direct sans RAG
            logger.info("🔄 Using fallback mode - direct OpenAI")
            
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                
                system_prompt = """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308.

Réponds de manière professionnelle en te basant sur tes connaissances générales en aviculture.

Sujets d'expertise:
- Gestion des poulets Ross 308 (températures, croissance, FCR)
- Santé aviaire et prévention des maladies
- Nutrition et alimentation
- Conditions d'élevage optimales

Réponds dans la même langue que la question."""

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_question}
                    ],
                    max_tokens=500,
                    temperature=0.2
                )
                
                return {
                    "question": user_question,
                    "answer": response.choices[0].message.content,
                    "mode": "fallback_openai",
                    "note": "Réponse basée sur les connaissances générales (recherche documentaire non disponible)",
                    "config_source": config_manager.config_source
                }
                
            except Exception as fallback_error:
                logger.error(f"❌ Fallback OpenAI error: {fallback_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur système: {str(fallback_error)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Erreur inattendue lors du traitement de la question"
            )
    
    @app.get("/api/v1/expert/status")
    async def expert_status():
        """Status détaillé du système expert"""
        validation = config_manager.validate_configuration()
        
        return {
            "api_available": validation['openai_key_present'],
            "rag_modules_imported": RAG_MODULES_AVAILABLE,
            "rag_system_initialized": rag_system is not None,
            "search_available": rag_system is not None and hasattr(rag_system, 'search_documents'),
            "documents_path": get_config('RAG_DOCUMENTS_PATH'),
            "index_path": get_config('RAG_INDEX_PATH'),
            "model": "gpt-4o" if validation['openai_key_present'] else None,
            "backend_directory": str(backend_dir),
            "mode": "full_rag" if (rag_system and RAG_MODULES_AVAILABLE) else "fallback"
        }
    
    logger.info(f"✅ Application created successfully")
    logger.info(f"📊 Configuration source: {config_manager.config_source}")
    logger.info(f"🌍 Environment: {get_config('ENVIRONMENT')}")
    logger.info(f"🤖 RAG modules: {'Available' if RAG_MODULES_AVAILABLE else 'Not available'}")
    logger.info(f"🔍 RAG system: {'Ready' if rag_system else 'Fallback mode'}")
    logger.info(f"📁 Backend directory: {backend_dir}")
    
    return app

# Créer l'application
app = create_application()

def main():
    """Point d'entrée principal pour le développement local"""
    logger.info("🚀 Starting Intelia Expert Backend with integrated RAG system")
    
    config = {
        "host": "0.0.0.0",
        "port": int(get_config('PORT', 8080)),
        "reload": get_config('DEBUG', False),
        "workers": 1 if get_config('DEBUG', False) else get_config('MAX_WORKERS', 4),
        "log_level": get_config('LOG_LEVEL', 'info').lower(),
    }
    
    logger.info(f"🔧 Server config: {config}")
    uvicorn.run("main:app", **config)

if __name__ == "__main__":
    main()