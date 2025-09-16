# -*- coding: utf-8 -*-
"""
imports_and_dependencies.py - Gestion robuste des dépendances avec validation stricte
Version corrigée: Élimination des fallbacks silencieux, validation explicite
AJOUTÉ: Fonctions get_openai_sync et get_openai_async manquantes
"""

import logging
import os
import asyncio
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DependencyStatus(Enum):
    """Statuts possibles des dépendances"""
    AVAILABLE = "available"
    MISSING = "missing"
    VERSION_INCOMPATIBLE = "version_incompatible"
    CONNECTION_FAILED = "connection_failed"

@dataclass
class DependencyInfo:
    """Informations sur une dépendance"""
    name: str
    status: DependencyStatus
    version: Optional[str] = None
    error_message: Optional[str] = None
    is_critical: bool = False

class DependencyManager:
    """Gestionnaire centralisé des dépendances avec validation stricte"""
    
    def __init__(self):
        self.dependencies: Dict[str, DependencyInfo] = {}
        self._openai_sync_client = None
        self._openai_async_client = None
        self._initialize_dependencies()
    
    def _initialize_dependencies(self):
        """Initialise et valide toutes les dépendances"""
        
        # OpenAI - CRITIQUE
        try:
            from openai import AsyncOpenAI, OpenAI
            openai_version = getattr(__import__('openai'), '__version__', 'unknown')
            self.dependencies['openai'] = DependencyInfo(
                name='openai',
                status=DependencyStatus.AVAILABLE,
                version=openai_version,
                is_critical=True
            )
            # Export global pour compatibilité
            globals()['OPENAI_AVAILABLE'] = True
            globals()['AsyncOpenAI'] = AsyncOpenAI
            globals()['OpenAI'] = OpenAI
            
            # Initialiser les clients OpenAI
            self._initialize_openai_clients()
            
        except ImportError as e:
            self.dependencies['openai'] = DependencyInfo(
                name='openai',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=True
            )
            globals()['OPENAI_AVAILABLE'] = False
        
        # Weaviate - CRITIQUE
        try:
            import weaviate
            weaviate_version = getattr(weaviate, '__version__', '4.0.0')
            
            # Validation de version
            if not weaviate_version.startswith(('4.', '3.')):
                raise ImportError(f"Version Weaviate non supportée: {weaviate_version}")
            
            weaviate_v4 = weaviate_version.startswith('4.')
            
            self.dependencies['weaviate'] = DependencyInfo(
                name='weaviate',
                status=DependencyStatus.AVAILABLE,
                version=weaviate_version,
                is_critical=True
            )
            
            # Export global pour compatibilité
            globals()['WEAVIATE_AVAILABLE'] = True
            globals()['weaviate'] = weaviate
            globals()['WEAVIATE_V4'] = weaviate_v4
            
        except ImportError as e:
            self.dependencies['weaviate'] = DependencyInfo(
                name='weaviate',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=True
            )
            globals()['WEAVIATE_AVAILABLE'] = False
            globals()['WEAVIATE_V4'] = False
        
        # Redis - CRITIQUE pour cache
        try:
            import redis
            redis_version = getattr(redis, '__version__', 'unknown')
            
            self.dependencies['redis'] = DependencyInfo(
                name='redis',
                status=DependencyStatus.AVAILABLE,
                version=redis_version,
                is_critical=False  # Cache est optionnel
            )
            
            # Export global pour compatibilité
            globals()['REDIS_AVAILABLE'] = True
            globals()['redis'] = redis
            
        except ImportError as e:
            self.dependencies['redis'] = DependencyInfo(
                name='redis',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=False
            )
            globals()['REDIS_AVAILABLE'] = False
            globals()['redis'] = None
        
        # Dépendances optionnelles
        self._load_optional_dependencies()
    
    def _initialize_openai_clients(self):
        """Initialise les clients OpenAI avec la configuration depuis les variables d'environnement"""
        try:
            # Récupérer la clé API depuis les variables d'environnement
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY non trouvée dans les variables d'environnement")
                return
            
            from openai import OpenAI, AsyncOpenAI
            
            # Configuration commune
            client_config = {
                "api_key": api_key,
                "timeout": 30.0,
                "max_retries": 3
            }
            
            # Client synchrone
            self._openai_sync_client = OpenAI(**client_config)
            
            # Client asynchrone
            self._openai_async_client = AsyncOpenAI(**client_config)
            
            logger.info("✅ Clients OpenAI (sync + async) initialisés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation clients OpenAI: {e}")
            self._openai_sync_client = None
            self._openai_async_client = None
    
    def _load_optional_dependencies(self):
        """Charge les dépendances optionnelles"""
        optional_deps = {
            'voyageai': {'import_name': 'voyageai'},
            'sentence_transformers': {'import_name': 'sentence_transformers'},
            'unidecode': {'import_name': 'unidecode'},
            'transformers': {'import_name': 'transformers'},
            'langdetect': {'import_name': 'langdetect'},
            'langsmith': {'import_name': 'langsmith'}
        }
        
        for dep_name, config in optional_deps.items():
            try:
                module = __import__(config['import_name'])
                version = getattr(module, '__version__', 'unknown')
                
                self.dependencies[dep_name] = DependencyInfo(
                    name=dep_name,
                    status=DependencyStatus.AVAILABLE,
                    version=version,
                    is_critical=False
                )
                
                # Export global pour compatibilité
                globals()[f'{dep_name.upper()}_AVAILABLE'] = True
                
            except ImportError as e:
                self.dependencies[dep_name] = DependencyInfo(
                    name=dep_name,
                    status=DependencyStatus.MISSING,
                    error_message=str(e),
                    is_critical=False
                )
                globals()[f'{dep_name.upper()}_AVAILABLE'] = False
        
        # Imports spéciaux pour modules internes
        self._load_internal_modules()
    
    def _load_internal_modules(self):
        """Charge les modules internes avec validation stricte"""
        
        # Intent Processor
        try:
            from intent_processor import create_intent_processor
            self.dependencies['intent_processor'] = DependencyInfo(
                name='intent_processor',
                status=DependencyStatus.AVAILABLE,
                is_critical=False
            )
            globals()['INTENT_PROCESSOR_AVAILABLE'] = True
            
        except ImportError as e:
            self.dependencies['intent_processor'] = DependencyInfo(
                name='intent_processor',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=False
            )
            globals()['INTENT_PROCESSOR_AVAILABLE'] = False
        
        # Autres modules internes...
        internal_modules = ['utilities', 'embedder', 'rag_engine', 'cache_manager']
        
        for module_name in internal_modules:
            try:
                __import__(module_name)
                self.dependencies[module_name] = DependencyInfo(
                    name=module_name,
                    status=DependencyStatus.AVAILABLE,
                    is_critical=False
                )
                globals()[f'{module_name.upper()}_AVAILABLE'] = True
                
            except ImportError as e:
                self.dependencies[module_name] = DependencyInfo(
                    name=module_name,
                    status=DependencyStatus.MISSING,
                    error_message=str(e),
                    is_critical=False
                )
                globals()[f'{module_name.upper()}_AVAILABLE'] = False
    
    def get_openai_sync_client(self):
        """Retourne le client OpenAI synchrone"""
        if self._openai_sync_client is None:
            self._initialize_openai_clients()
        
        if self._openai_sync_client is None:
            raise RuntimeError("Client OpenAI synchrone non disponible")
        
        return self._openai_sync_client
    
    def get_openai_async_client(self):
        """Retourne le client OpenAI asynchrone"""
        if self._openai_async_client is None:
            self._initialize_openai_clients()
        
        if self._openai_async_client is None:
            raise RuntimeError("Client OpenAI asynchrone non disponible")
        
        return self._openai_async_client
    
    async def validate_connectivity(self, redis_client=None, weaviate_client=None) -> Dict[str, bool]:
        """Valide la connectivité des services externes"""
        results = {
            'openai': False,
            'weaviate': False,
            'redis': False
        }
        
        # Test OpenAI
        try:
            if self._openai_async_client:
                await asyncio.wait_for(
                    self._openai_async_client.models.list(),
                    timeout=5.0
                )
                results['openai'] = True
        except Exception as e:
            logger.warning(f"Test connectivité OpenAI échoué: {e}")
        
        # Test Weaviate
        try:
            if weaviate_client and hasattr(weaviate_client, 'is_ready'):
                results['weaviate'] = await asyncio.wait_for(
                    weaviate_client.is_ready(),
                    timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Test connectivité Weaviate échoué: {e}")
        
        # Test Redis
        try:
            if redis_client and hasattr(redis_client, 'ping'):
                await asyncio.wait_for(
                    redis_client.ping(),
                    timeout=5.0
                )
                results['redis'] = True
        except Exception as e:
            logger.warning(f"Test connectivité Redis échoué: {e}")
        
        return results
    
    def get_status_report(self) -> Dict[str, Any]:
        """Génère un rapport de statut complet"""
        critical_deps = [dep for dep in self.dependencies.values() if dep.is_critical]
        critical_missing = [dep for dep in critical_deps if dep.status != DependencyStatus.AVAILABLE]
        
        optional_deps = [dep for dep in self.dependencies.values() if not dep.is_critical]
        optional_missing = [dep.name for dep in optional_deps if dep.status != DependencyStatus.AVAILABLE]
        
        return {
            'total_dependencies': len(self.dependencies),
            'available_count': len([d for d in self.dependencies.values() if d.status == DependencyStatus.AVAILABLE]),
            'critical_dependencies_ok': len(critical_missing) == 0,
            'critical_missing': [dep.name for dep in critical_missing],
            'optional_missing': optional_missing,
            'details': {
                dep_name: {
                    'status': dep.status.value,
                    'version': dep.version,
                    'is_critical': dep.is_critical,
                    'error': dep.error_message
                }
                for dep_name, dep in self.dependencies.items()
            }
        }
    
    def require_critical_dependencies(self):
        """Vérifie que toutes les dépendances critiques sont disponibles"""
        critical_missing = [
            dep for dep in self.dependencies.values() 
            if dep.is_critical and dep.status != DependencyStatus.AVAILABLE
        ]
        
        if critical_missing:
            missing_names = [dep.name for dep in critical_missing]
            error_details = "\n".join([
                f"  - {dep.name}: {dep.error_message}"
                for dep in critical_missing
            ])
            
            raise RuntimeError(
                f"Dépendances critiques manquantes: {missing_names}\n"
                f"Détails:\n{error_details}"
            )
    
    def get_legacy_status(self) -> Dict[str, bool]:
        """Compatibilité avec l'ancien format get_dependencies_status()"""
        return {
            name: dep.status == DependencyStatus.AVAILABLE
            for name, dep in self.dependencies.items()
        }

# Instance globale
dependency_manager = DependencyManager()

# === FONCTIONS MANQUANTES CRITIQUES ===
def get_openai_sync():
    """Retourne le client OpenAI synchrone - FONCTION MANQUANTE CORRIGÉE"""
    return dependency_manager.get_openai_sync_client()

def get_openai_async():
    """Retourne le client OpenAI asynchrone - FONCTION MANQUANTE CORRIGÉE"""
    return dependency_manager.get_openai_async_client()

# Fonctions pour compatibilité avec l'ancien code
def get_dependencies_status() -> Dict[str, bool]:
    """Fonction de compatibilité"""
    return dependency_manager.get_legacy_status()

async def quick_connectivity_check(redis_client=None, weaviate_client=None) -> Dict[str, bool]:
    """Fonction de compatibilité pour test de connectivité"""
    return await dependency_manager.validate_connectivity(redis_client, weaviate_client)

def require_critical_dependencies():
    """Vérifie les dépendances critiques - À appeler au démarrage"""
    dependency_manager.require_critical_dependencies()

def get_full_status_report() -> Dict[str, Any]:
    """Rapport de statut complet pour debugging"""
    return dependency_manager.get_status_report()

# Variables globales exportées (compatibilité)
OPENAI_AVAILABLE = globals().get('OPENAI_AVAILABLE', False)
WEAVIATE_AVAILABLE = globals().get('WEAVIATE_AVAILABLE', False)
REDIS_AVAILABLE = globals().get('REDIS_AVAILABLE', False)
WEAVIATE_V4 = globals().get('WEAVIATE_V4', False)

# Log du statut au chargement
status_report = dependency_manager.get_status_report()
if status_report['critical_dependencies_ok']:
    logger.info("✅ Toutes les dépendances critiques sont disponibles")
else:
    logger.error(f"❌ Dépendances critiques manquantes: {status_report['critical_missing']}")

if status_report['optional_missing']:
    logger.warning(f"⚠️ Dépendances optionnelles manquantes: {status_report['optional_missing']}")

logger.info(f"Dépendances chargées: {status_report['available_count']}/{status_report['total_dependencies']}")

# Export pour le module
__all__ = [
    'dependency_manager',
    'get_openai_sync',
    'get_openai_async', 
    'get_dependencies_status',
    'quick_connectivity_check',
    'require_critical_dependencies',
    'get_full_status_report',
    'OPENAI_AVAILABLE',
    'WEAVIATE_AVAILABLE',
    'REDIS_AVAILABLE',
    'WEAVIATE_V4'
]