# -*- coding: utf-8 -*-
"""
imports_and_dependencies.py - Gestion robuste des dépendances avec validation stricte
Version corrigée: Élimination des fallbacks silencieux, validation explicite
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
            
            if weaviate_v4:
                try:
                    import weaviate.classes as wvc
                    import weaviate.classes.query as wvc_query
                    globals()['wvc'] = wvc
                    globals()['wvc_query'] = wvc_query
                except ImportError:
                    raise ImportError("Impossible d'importer les classes Weaviate v4")
            else:
                globals()['wvc'] = None
                globals()['wvc_query'] = None
            
            self.dependencies['weaviate'] = DependencyInfo(
                name='weaviate',
                status=DependencyStatus.AVAILABLE,
                version=weaviate_version,
                is_critical=True
            )
            
            # Export global pour compatibilité
            globals()['WEAVIATE_AVAILABLE'] = True
            globals()['WEAVIATE_V4'] = weaviate_v4
            globals()['weaviate'] = weaviate
            globals()['weaviate_version'] = weaviate_version
            
        except ImportError as e:
            self.dependencies['weaviate'] = DependencyInfo(
                name='weaviate',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=True
            )
            globals()['WEAVIATE_AVAILABLE'] = False
            globals()['WEAVIATE_V4'] = False
            globals()['weaviate'] = None
            globals()['weaviate_version'] = 'N/A'
        
        # Redis - Important pour cache
        try:
            import redis.asyncio as redis
            import hiredis
            redis_version = getattr(redis, '__version__', 'unknown')
            
            self.dependencies['redis'] = DependencyInfo(
                name='redis',
                status=DependencyStatus.AVAILABLE,
                version=redis_version,
                is_critical=False
            )
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
    
    def _load_optional_dependencies(self):
        """Charge les dépendances optionnelles"""
        optional_deps = {
            'voyageai': {'import_name': 'voyageai'},
            'sentence_transformers': {'import_name': 'sentence_transformers'},
            'unidecode': {'import_name': 'unidecode'},
            'transformers': {'import_name': 'transformers'},
            'langdetect': {'import_name': 'langdetect'}
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
            from intent_processor import create_intent_processor, IntentType, IntentResult
            self.dependencies['intent_processor'] = DependencyInfo(
                name='intent_processor',
                status=DependencyStatus.AVAILABLE,
                is_critical=False
            )
            globals()['INTENT_PROCESSOR_AVAILABLE'] = True
            globals()['IntentType'] = IntentType
            globals()['IntentResult'] = IntentResult
        except ImportError as e:
            self.dependencies['intent_processor'] = DependencyInfo(
                name='intent_processor',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=False
            )
            globals()['INTENT_PROCESSOR_AVAILABLE'] = False
            # PAS de fallback - le code doit gérer l'absence explicitement
        
        # Advanced Guardrails
        try:
            from advanced_guardrails import create_response_guardrails, VerificationLevel, GuardrailResult
            self.dependencies['guardrails'] = DependencyInfo(
                name='guardrails',
                status=DependencyStatus.AVAILABLE,
                is_critical=False
            )
            globals()['GUARDRAILS_AVAILABLE'] = True
            globals()['VerificationLevel'] = VerificationLevel
            globals()['GuardrailResult'] = GuardrailResult
        except ImportError as e:
            self.dependencies['guardrails'] = DependencyInfo(
                name='guardrails',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=False
            )
            globals()['GUARDRAILS_AVAILABLE'] = False
        
        # Cache externe
        try:
            from redis_cache_manager import RAGCacheManager
            self.dependencies['external_cache'] = DependencyInfo(
                name='external_cache',
                status=DependencyStatus.AVAILABLE,
                is_critical=False
            )
            globals()['EXTERNAL_CACHE_AVAILABLE'] = True
            globals()['RAGCacheManager'] = RAGCacheManager
        except ImportError as e:
            self.dependencies['external_cache'] = DependencyInfo(
                name='external_cache',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=False
            )
            globals()['EXTERNAL_CACHE_AVAILABLE'] = False
    
    async def validate_connectivity(self, redis_client=None, weaviate_client=None) -> Dict[str, bool]:
        """
        Validation de connectivité asynchrone robuste
        """
        connectivity = {}
        
        # Test Redis (async)
        if redis_client and self.dependencies['redis'].status == DependencyStatus.AVAILABLE:
            try:
                await asyncio.wait_for(redis_client.ping(), timeout=3.0)
                connectivity['redis'] = True
                self.dependencies['redis'].status = DependencyStatus.AVAILABLE
            except Exception as e:
                connectivity['redis'] = False
                self.dependencies['redis'].status = DependencyStatus.CONNECTION_FAILED
                self.dependencies['redis'].error_message = f"Connexion échouée: {e}"
                logger.warning(f"Redis connexion échouée: {e}")
        else:
            connectivity['redis'] = False
        
        # Test Weaviate
        if weaviate_client and self.dependencies['weaviate'].status == DependencyStatus.AVAILABLE:
            try:
                # Test asynchrone pour Weaviate
                def _test_weaviate():
                    return weaviate_client.is_ready()
                
                # Exécuter le test dans un thread pour éviter les blocages
                loop = asyncio.get_event_loop()
                is_ready = await asyncio.wait_for(
                    loop.run_in_executor(None, _test_weaviate),
                    timeout=5.0
                )
                
                connectivity['weaviate'] = is_ready
                if not is_ready:
                    self.dependencies['weaviate'].status = DependencyStatus.CONNECTION_FAILED
                    self.dependencies['weaviate'].error_message = "Service non prêt"
                    
            except Exception as e:
                connectivity['weaviate'] = False
                self.dependencies['weaviate'].status = DependencyStatus.CONNECTION_FAILED
                self.dependencies['weaviate'].error_message = f"Connexion échouée: {e}"
                logger.warning(f"Weaviate connexion échouée: {e}")
        else:
            connectivity['weaviate'] = False
        
        return connectivity
    
    def get_status_report(self) -> Dict[str, Any]:
        """Rapport de statut complet"""
        critical_missing = [
            dep.name for dep in self.dependencies.values()
            if dep.is_critical and dep.status != DependencyStatus.AVAILABLE
        ]
        
        optional_missing = [
            dep.name for dep in self.dependencies.values()
            if not dep.is_critical and dep.status != DependencyStatus.AVAILABLE
        ]
        
        return {
            'critical_dependencies_ok': len(critical_missing) == 0,
            'critical_missing': critical_missing,
            'optional_missing': optional_missing,
            'total_dependencies': len(self.dependencies),
            'available_count': len([d for d in self.dependencies.values() 
                                  if d.status == DependencyStatus.AVAILABLE]),
            'details': {
                name: {
                    'status': dep.status.value,
                    'version': dep.version,
                    'error': dep.error_message,
                    'critical': dep.is_critical
                }
                for name, dep in self.dependencies.items()
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

# Fonctions pour compatibilité avec l'ancien code
def get_dependencies_status() -> Dict[str, bool]:
    """Fonction de compatibilité"""
    return dependency_manager.get_legacy_status()

async def quick_connectivity_check(redis_client=None, weaviate_client=None) -> Dict[str, bool]:
    """Fonction de compatibilité pour test de connectivité"""
    return await dependency_manager.validate_connectivity(redis_client, weaviate_client)

def require_critical_dependencies():
    """Vérifie les dépendances critiques - à appeler au démarrage"""
    dependency_manager.require_critical_dependencies()

def get_full_status_report() -> Dict[str, Any]:
    """Rapport de statut complet pour debugging"""
    return dependency_manager.get_status_report()

# Log du statut au chargement
status_report = dependency_manager.get_status_report()
if status_report['critical_dependencies_ok']:
    logger.info("✅ Toutes les dépendances critiques sont disponibles")
else:
    logger.error(f"❌ Dépendances critiques manquantes: {status_report['critical_missing']}")

if status_report['optional_missing']:
    logger.warning(f"⚠️ Dépendances optionnelles manquantes: {status_report['optional_missing']}")

logger.info(f"Dépendances chargées: {status_report['available_count']}/{status_report['total_dependencies']}")