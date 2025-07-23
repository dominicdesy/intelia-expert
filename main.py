# main.py
"""
Intelia Expert Backend - Point d'entrée principal
Configuration sécurisée pour développement local et production cloud
"""

import logging
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import de notre gestionnaire de configuration sécurisé
from core.config.config import config_manager, validate_startup, get_config

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, get_config('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """Créer l'application FastAPI avec configuration sécurisée"""
    
    # Validation de la configuration au démarrage
    if not validate_startup():
        logger.error("❌ Configuration validation failed - cannot start application")
        raise RuntimeError("Invalid configuration")
    
    # Création de l'application
    app = FastAPI(
        title="Intelia Expert API",
        description="Assistant IA Expert pour la Santé et Nutrition Animale",
        version="1.0.0",
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
            "message": "Intelia Expert API",
            "status": "running",
            "environment": status['environment'],
            "config_source": status['config_source'],
            "api_version": "1.0.0"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check pour monitoring"""
        try:
            validation = config_manager.validate_configuration()
            status = config_manager.get_status_report()
            
            # Vérifier les composants critiques
            health_status = {
                "status": "healthy" if all(validation.values()) else "degraded",
                "timestamp": "2025-07-23T19:31:06Z",
                "services": {
                    "api": "running",
                    "configuration": "loaded" if validation['openai_key_present'] else "limited",
                    "rag_system": "ready" if validation['rag_paths_accessible'] else "initializing",
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
                    "timestamp": "2025-07-23T19:31:06Z"
                }
            )
    
    @app.get("/config/status")
    async def config_status():
        """Endpoint pour vérifier la configuration (utile pour debugging)"""
        if not get_config('DEBUG', False):
            raise HTTPException(status_code=404, detail="Endpoint not available in production")
        
        status = config_manager.get_status_report()
        
        # Masquer les informations sensibles
        safe_status = {
            **status,
            'api_keys': {
                'openai_configured': status['api_keys']['openai_configured'],
                'anthropic_configured': status['api_keys']['anthropic_configured'],
            }
        }
        
        return safe_status
    
    # Routes RAG (placeholders pour l'instant)
    @app.post("/api/v1/expert/ask")
    async def ask_expert(question: dict):
        """Endpoint principal pour les questions RAG"""
        openai_key = config_manager.get_openai_key()
        
        if not openai_key:
            raise HTTPException(
                status_code=503, 
                detail="RAG system not available - OpenAI API key not configured"
            )
        
        # TODO: Implémenter la logique RAG
        return {
            "question": question.get('text', ''),
            "answer": "RAG system is configured and ready. Implementation coming soon.",
            "config_source": config_manager.config_source,
            "rag_available": True
        }
    
    @app.get("/api/v1/expert/status")
    async def expert_status():
        """Status du système expert RAG"""
        validation = config_manager.validate_configuration()
        
        return {
            "rag_available": validation['openai_key_present'],
            "index_ready": validation['rag_paths_accessible'],
            "documents_path": get_config('RAG_DOCUMENTS_PATH'),
            "index_path": get_config('RAG_INDEX_PATH'),
            "model": "gpt-4o" if validation['openai_key_present'] else None
        }
    
    logger.info(f"✅ Application created successfully")
    logger.info(f"📊 Configuration source: {config_manager.config_source}")
    logger.info(f"🌍 Environment: {get_config('ENVIRONMENT')}")
    
    return app

# Créer l'application
app = create_application()

def main():
    """Point d'entrée principal pour le développement local"""
    logger.info("🚀 Starting Intelia Expert Backend")
    
    # Configuration du serveur
    config = {
        "host": "0.0.0.0",
        "port": int(get_config('PORT', 8080)),
        "reload": get_config('DEBUG', False),
        "workers": 1 if get_config('DEBUG', False) else get_config('MAX_WORKERS', 4),
        "log_level": get_config('LOG_LEVEL', 'info').lower(),
    }
    
    logger.info(f"🔧 Server config: {config}")
    
    # Démarrer le serveur
    uvicorn.run("main:app", **config)

if __name__ == "__main__":
    main()