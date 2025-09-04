# app/core/config/config.py
"""
Configuration sécurisée pour Intelia Expert Backend
Support développement local + déploiement cloud sécurisé
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestionnaire de configuration sécurisé avec fallback intelligent"""
    
    def __init__(self):
        self.config = {}
        self.config_source = None
        self._load_configuration()
    
    def _load_configuration(self):
        """Charge la configuration avec priorité sécurisée"""
        
        # PRIORITÉ 1: Variables d'environnement (PRODUCTION)
        if self._load_from_environment():
            self.config_source = "Environment Variables (PRODUCTION)"
            logger.info("✅ Configuration loaded from environment variables")
            return
        
        # PRIORITÉ 2: Secrets.toml local (DÉVELOPPEMENT)
        if self._load_from_secrets_toml():
            self.config_source = "secrets.toml (DEVELOPMENT)"
            logger.info("✅ Configuration loaded from secrets.toml")
            return
        
        # PRIORITÉ 3: Configuration par défaut (FALLBACK)
        self._load_default_config()
        self.config_source = "Default Configuration (LIMITED)"
        logger.warning("⚠️ Using default configuration - limited functionality")
    
    def _load_from_environment(self) -> bool:
        """Charge depuis les variables d'environnement (production)"""
        required_vars = ['OPENAI_API_KEY']
        
        # Vérifier si au moins une variable critique existe
        if not any(os.getenv(var) for var in required_vars):
            return False
        
        self.config = {
            # API Keys
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            
            # RAG Configuration
            'RAG_INDEX_PATH': os.getenv('RAG_INDEX_PATH', '/tmp/rag_index'),
            'RAG_DOCUMENTS_PATH': os.getenv('RAG_DOCUMENTS_PATH', '/tmp/documents'),
            
            # Database
            'DATABASE_URL': os.getenv('DATABASE_URL', 'sqlite:///./app.db'),
            'SUPABASE_URL': os.getenv('SUPABASE_URL'),
            'SUPABASE_KEY': os.getenv('SUPABASE_KEY'),
            
            # Application
            'ENVIRONMENT': os.getenv('ENVIRONMENT', 'production'),
            'DEBUG': os.getenv('DEBUG', 'false').lower() == 'true',
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            
            # Security
            'SECRET_KEY': os.getenv('SECRET_KEY', 'production-secret-key'),
            'ALLOWED_ORIGINS': os.getenv('ALLOWED_ORIGINS', '*').split(','),
            
            # Performance
            'MAX_WORKERS': int(os.getenv('MAX_WORKERS', '4')),
            'TIMEOUT': int(os.getenv('TIMEOUT', '30')),
        }
        
        return True
    
    def _load_from_secrets_toml(self) -> bool:
        """Charge depuis secrets.toml (développement local)"""
        # Chercher secrets.toml dans le dossier racine du projet
        possible_paths = [
            Path('../../../secrets.toml'),  # Depuis core/config/
            Path('../../secrets.toml'),     # Depuis core/
            Path('../secrets.toml'),        # Depuis app/
            Path('secrets.toml')             # Depuis racine
        ]
        
        secrets_path = None
        for path in possible_paths:
            if path.exists():
                secrets_path = path
                break
        
        if not secrets_path:
            logger.debug("secrets.toml not found in any expected location")
            return False
        
        try:
            # Parse manual du TOML (évite la dépendance tomllib)
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets_data = {}
                current_section = None
                
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Section header
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        continue
                    
                    # Key-value pair
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Si on est dans une section, utiliser la section default ou racine
                        if current_section == 'default' or current_section is None:
                            secrets_data[key] = value
            
            self.config = {
                # API Keys
                'OPENAI_API_KEY': secrets_data.get('OPENAI_API_KEY'),
                'ANTHROPIC_API_KEY': secrets_data.get('ANTHROPIC_API_KEY'),
                
                # RAG Configuration
                'RAG_INDEX_PATH': secrets_data.get('RAG_INDEX_PATH', './rag_index'),
                'RAG_DOCUMENTS_PATH': secrets_data.get('RAG_DOCUMENTS_PATH', './documents'),
                
                # Database
                'DATABASE_URL': secrets_data.get('DATABASE_URL', 'sqlite:///./test.db'),
                'SUPABASE_URL': secrets_data.get('SUPABASE_URL'),
                'SUPABASE_KEY': secrets_data.get('SUPABASE_KEY'),
                
                # Application
                'ENVIRONMENT': secrets_data.get('ENVIRONMENT', 'development'),
                'DEBUG': str(secrets_data.get('DEBUG', 'true')).lower() == 'true',
                'LOG_LEVEL': secrets_data.get('LOG_LEVEL', 'DEBUG'),
                
                # Security
                'SECRET_KEY': secrets_data.get('SECRET_KEY', 'dev-secret-key'),
                'ALLOWED_ORIGINS': ['http://localhost:3000', 'http://localhost:8080'],
                
                # Performance
                'MAX_WORKERS': int(secrets_data.get('MAX_WORKERS', '2')),
                'TIMEOUT': int(secrets_data.get('TIMEOUT', '30')),
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error reading secrets.toml: {e}")
            return False
    
    def _load_default_config(self):
        """Configuration par défaut (mode dégradé)"""
        self.config = {
            # API Keys - VIDES (mode dégradé)
            'OPENAI_API_KEY': None,
            'ANTHROPIC_API_KEY': None,
            
            # RAG Configuration
            'RAG_INDEX_PATH': './rag_index',
            'RAG_DOCUMENTS_PATH': './documents',
            
            # Database
            'DATABASE_URL': 'sqlite:///./fallback.db',
            
            # Application
            'ENVIRONMENT': 'development',
            'DEBUG': True,
            'LOG_LEVEL': 'WARNING',
            
            # Security
            'SECRET_KEY': 'fallback-insecure-key',
            'ALLOWED_ORIGINS': ['*'],
            
            # Performance
            'MAX_WORKERS': 1,
            'TIMEOUT': 30,
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration"""
        return self.config.get(key, default)
    
    def get_openai_key(self) -> Optional[str]:
        """Récupère la clé OpenAI avec validation"""
        key = self.get('OPENAI_API_KEY')
        if not key:
            logger.error("OpenAI API key not configured")
            return None
        
        if not key.startswith('sk-'):
            logger.warning("OpenAI API key format invalid")
        
        return key
    
    def is_production(self) -> bool:
        """Vérifie si on est en production"""
        return self.get('ENVIRONMENT') == 'production'
    
    def is_development(self) -> bool:
        """Vérifie si on est en développement"""
        return self.get('ENVIRONMENT') == 'development'
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Valide la configuration et retourne le status"""
        validation = {
            'openai_key_present': bool(self.get('OPENAI_API_KEY')),
            'openai_key_valid_format': False,
            'rag_paths_accessible': False,
            'database_configured': bool(self.get('DATABASE_URL')),
            'environment_set': bool(self.get('ENVIRONMENT')),
        }
        
        # Validation format clé OpenAI
        openai_key = self.get('OPENAI_API_KEY')
        if openai_key and openai_key.startswith('sk-'):
            validation['openai_key_valid_format'] = True
        
        # Validation chemins RAG
        try:
            index_path = Path(self.get('RAG_INDEX_PATH'))
            docs_path = Path(self.get('RAG_DOCUMENTS_PATH'))
            
            # Créer les dossiers s'ils n'existent pas
            index_path.mkdir(parents=True, exist_ok=True)
            docs_path.mkdir(parents=True, exist_ok=True)
            
            validation['rag_paths_accessible'] = True
        except Exception as e:
            logger.error(f"Cannot access RAG paths: {e}")
        
        return validation
    
    def get_status_report(self) -> Dict[str, Any]:
        """Génère un rapport de statut complet"""
        validation = self.validate_configuration()
        
        return {
            'config_source': self.config_source,
            'environment': self.get('ENVIRONMENT'),
            'debug_mode': self.get('DEBUG'),
            'validation': validation,
            'rag_config': {
                'index_path': self.get('RAG_INDEX_PATH'),
                'documents_path': self.get('RAG_DOCUMENTS_PATH'),
            },
            'api_keys': {
                'openai_configured': bool(self.get('OPENAI_API_KEY')),
                'anthropic_configured': bool(self.get('ANTHROPIC_API_KEY')),
            },
            'database': {
                'url': self.get('DATABASE_URL'),
                'supabase_configured': bool(self.get('SUPABASE_URL')),
            }
        }

# Instance globale
config_manager = ConfigManager()

# Fonctions de convenance
def get_config(key: str, default: Any = None) -> Any:
    """Fonction helper pour récupérer une config"""
    return config_manager.get(key, default)

def get_openai_key() -> Optional[str]:
    """Fonction helper pour récupérer la clé OpenAI"""
    return config_manager.get_openai_key()

def is_production() -> bool:
    """Fonction helper pour vérifier l'environnement"""
    return config_manager.is_production()

def validate_startup() -> bool:
    """Valide que la configuration permet de démarrer l'application"""
    validation = config_manager.validate_configuration()
    
    # Log du status de configuration
    status = config_manager.get_status_report()
    logger.info(f"Configuration source: {status['config_source']}")
    logger.info(f"Environment: {status['environment']}")
    
    # Vérifications critiques
    critical_checks = [
        'openai_key_present',
        'rag_paths_accessible',
        'database_configured'
    ]
    
    failed_checks = [check for check in critical_checks if not validation[check]]
    
    if failed_checks:
        logger.error(f"Critical configuration checks failed: {failed_checks}")
        for check in failed_checks:
            if check == 'openai_key_present':
                logger.error("❌ OpenAI API key not configured")
                logger.error("   Set OPENAI_API_KEY environment variable or add to secrets.toml")
            elif check == 'rag_paths_accessible':
                logger.error("❌ RAG paths not accessible")
                logger.error(f"   Index: {get_config('RAG_INDEX_PATH')}")
                logger.error(f"   Documents: {get_config('RAG_DOCUMENTS_PATH')}")
            elif check == 'database_configured':
                logger.error("❌ Database not configured")
        
        return False
    
    logger.info("✅ Configuration validation passed")
    return True

# Configuration export pour compatibilité
class Settings:
    """Classe de settings compatible avec FastAPI"""
    
    def __init__(self):
        self._config = config_manager
    
    @property
    def openai_api_key(self) -> Optional[str]:
        return self._config.get_openai_key()
    
    @property
    def rag_index_path(self) -> str:
        return self._config.get('RAG_INDEX_PATH')
    
    @property
    def rag_documents_path(self) -> str:
        return self._config.get('RAG_DOCUMENTS_PATH')
    
    @property
    def database_url(self) -> str:
        return self._config.get('DATABASE_URL')
    
    @property
    def environment(self) -> str:
        return self._config.get('ENVIRONMENT')
    
    @property
    def debug(self) -> bool:
        return self._config.get('DEBUG')
    
    @property
    def secret_key(self) -> str:
        return self._config.get('SECRET_KEY')

settings = Settings()
