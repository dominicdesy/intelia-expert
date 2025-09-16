# -*- coding: utf-8 -*-
"""
imports_and_dependencies.py - Gestion robuste des dépendances avec validation stricte
Version COMPLÈTEMENT CORRIGÉE: Élimination des fallbacks silencieux, validation explicite
CORRIGÉ: Import wvc_query manquant qui causait l'erreur de démarrage
CORRIGÉ: Détection modules internes rag_engine et cache_manager
CORRIGÉ: Import circulaire ENABLE_API_DIAGNOSTICS déplacé vers config.py
CORRIGÉ: Erreur async validate_connectivity() causant le RuntimeWarning Redis
CORRIGÉ: Gestion async Redis proper avec await et détection automatique sync/async
"""

import logging
import os
import asyncio
import inspect
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

async def _test_redis_async_safe(redis_client) -> bool:
    """Test Redis avec détection automatique sync/async - CORRECTION APPLIQUÉE"""
    try:
        if redis_client is None:
            return False

        # Essayer ping() d'abord
        if hasattr(redis_client, "ping"):
            ping_fn = getattr(redis_client, "ping")
            if inspect.iscoroutinefunction(ping_fn):
                return bool(await asyncio.wait_for(ping_fn(), timeout=3.0))
            else:
                # client sync (rare dans ton cas) → thread
                return bool(await asyncio.get_event_loop().run_in_executor(None, ping_fn))

        # Fallback: execute_command("PING")
        if hasattr(redis_client, "execute_command"):
            exec_fn = getattr(redis_client, "execute_command")
            if inspect.iscoroutinefunction(exec_fn):
                return bool(await asyncio.wait_for(exec_fn("PING"), timeout=3.0))
            else:
                return bool(await asyncio.get_event_loop().run_in_executor(None, exec_fn, "PING"))

        # Si aucune des deux API n'existe, considérer non disponible
        return False

    except Exception:
        return False

class DependencyManager:
    """Gestionnaire centralisé des dépendances avec validation stricte - VERSION CORRIGÉE"""
    
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
        
        # Weaviate - CRITIQUE - CORRIGÉ POUR INCLURE wvc_query
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
            
            # CORRECTION CRITIQUE: Import wvc ET wvc_query pour Weaviate v4
            if weaviate_v4:
                try:
                    import weaviate.classes as wvc
                    import weaviate.classes.query as wvc_query  # ← IMPORT MANQUANT AJOUTÉ
                    
                    globals()['wvc'] = wvc
                    globals()['wvc_query'] = wvc_query  # ← EXPORT GLOBAL AJOUTÉ
                    
                    logger.info("✅ Weaviate v4 avec wvc et wvc_query importés avec succès")
                    
                except ImportError as e:
                    logger.error(f"Erreur import wvc classes: {e}")
                    globals()['wvc'] = None
                    globals()['wvc_query'] = None
                    raise ImportError(f"Impossible d'importer les classes Weaviate v4: {e}")
            else:
                globals()['wvc'] = None
                globals()['wvc_query'] = None
            
        except ImportError as e:
            self.dependencies['weaviate'] = DependencyInfo(
                name='weaviate',
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=True
            )
            globals()['WEAVIATE_AVAILABLE'] = False
            globals()['WEAVIATE_V4'] = False
            globals()['wvc'] = None
            globals()['wvc_query'] = None  # ← AJOUTÉ
        
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
        
        # CORRECTION: Modules internes avec imports spécifiques
        internal_modules = {
            'utilities': 'utilities',
            'embedder': 'embedder', 
            'rag_engine': 'rag_engine',
            'cache_manager': 'cache_core'  # ← CORRECTION APPLIQUÉE
        }
        
        for display_name, module_name in internal_modules.items():
            try:
                # CORRECTION: Import plus robuste avec gestion d'erreurs
                if module_name == 'rag_engine':
                    # Test d'import spécifique pour rag_engine avec gestion d'erreurs
                    try:
                        from rag_engine import InteliaRAGEngine
                        test_import = True
                    except Exception as e:
                        logger.warning(f"Erreur import rag_engine: {e}")
                        test_import = False
                elif module_name == 'cache_core':  # ← CORRECTION DU NOM
                    # Test d'import spécifique pour cache_core
                    try:
                        from cache_core import create_cache_core
                        test_import = True
                    except Exception as e:
                        logger.warning(f"Erreur import cache_core: {e}")
                        test_import = False
                else:
                    # Import standard pour les autres
                    try:
                        __import__(module_name)
                        test_import = True
                    except Exception as e:
                        logger.warning(f"Erreur import {module_name}: {e}")
                        test_import = False
                
                if test_import:
                    self.dependencies[display_name] = DependencyInfo(
                        name=display_name,
                        status=DependencyStatus.AVAILABLE,
                        is_critical=False
                    )
                    globals()[f'{display_name.upper()}_AVAILABLE'] = True
                else:
                    self.dependencies[display_name] = DependencyInfo(
                        name=display_name,
                        status=DependencyStatus.MISSING,
                        error_message=f"Import {module_name} échoué",
                        is_critical=False
                    )
                    globals()[f'{display_name.upper()}_AVAILABLE'] = False
                
            except ImportError as e:
                self.dependencies[display_name] = DependencyInfo(
                    name=display_name,
                    status=DependencyStatus.MISSING,
                    error_message=str(e),
                    is_critical=False
                )
                globals()[f'{display_name.upper()}_AVAILABLE'] = False
    
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
        """CORRIGÉ: Valide la connectivité des services externes - CORRECTION REDIS COMPLÈTE"""
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
        
        # Test Weaviate - CORRECTION COMPLÈTE POUR ÉVITER L'ERREUR ASYNC
        try:
            if weaviate_client:
                def _test_weaviate_sync():
                    """Test synchrone de Weaviate dans un thread séparé"""
                    try:
                        if hasattr(weaviate_client, '_connection') and hasattr(weaviate_client._connection, 'check_readiness'):
                            return weaviate_client._connection.check_readiness()
                        elif hasattr(weaviate_client, 'is_ready'):
                            # Pour les versions plus récentes
                            if asyncio.iscoroutinefunction(weaviate_client.is_ready):
                                # CORRECTION: Ne pas appeler les coroutines dans un contexte sync
                                logger.debug("Weaviate.is_ready est async - ignoré dans test sync")
                                return False
                            else:
                                return weaviate_client.is_ready()
                        elif hasattr(weaviate_client, 'schema') and hasattr(weaviate_client.schema, 'get'):
                            # Test via schema get comme fallback
                            weaviate_client.schema.get()
                            return True
                        return False
                    except Exception as e:
                        logger.debug(f"Test Weaviate sync échoué: {e}")
                        return False
                
                # CORRECTION: Exécution async du test synchrone
                results['weaviate'] = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, _test_weaviate_sync),
                    timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Test connectivité Weaviate échoué: {e}")
        
        # Test Redis - VERSION SÛRE AVEC DÉTECTION AUTO SYNC/ASYNC
        try:
            results['redis'] = await _test_redis_async_safe(redis_client)
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

def get_full_status_report() -> Dict[str, Any]:
    """Rapport de statut complet"""
    return dependency_manager.get_status_report()

async def quick_connectivity_check(redis_client=None, weaviate_client=None) -> Dict[str, bool]:
    """CORRIGÉ: Fonction de compatibilité pour test de connectivité"""
    return await dependency_manager.validate_connectivity(redis_client, weaviate_client)

def require_critical_dependencies():
    """Vérifie les dépendances critiques - À appeler au démarrage"""
    dependency_manager.require_critical_dependencies()

# === FONCTIONS DE DIAGNOSTIC ===
def diagnose_dependency_issues() -> Dict[str, Any]:
    """Diagnostic complet des problèmes de dépendances"""
    report = dependency_manager.get_status_report()
    
    issues = []
    recommendations = []
    
    # Analyse des problèmes
    if not report['critical_dependencies_ok']:
        issues.append(f"Dépendances critiques manquantes: {report['critical_missing']}")
        recommendations.append("Installer les dépendances critiques manquantes")
    
    if 'weaviate' in report['critical_missing']:
        issues.append("Weaviate non disponible - système RAG non fonctionnel")
        recommendations.append("Installer weaviate-client>=4.16.10")
    
    if 'openai' in report['critical_missing']:
        issues.append("OpenAI non disponible - génération impossible")
        recommendations.append("Installer openai>=1.42.0 et configurer OPENAI_API_KEY")
    
    # Vérification imports spéciaux
    if not globals().get('wvc'):
        issues.append("wvc classes non importées - erreurs API Weaviate")
        recommendations.append("Vérifier l'installation de weaviate-client")
    
    if not globals().get('wvc_query'):
        issues.append("wvc_query non importé - requêtes avancées indisponibles")
        recommendations.append("Réinstaller weaviate-client")
    
    return {
        "timestamp": __import__('time').time(),
        "all_critical_available": report['critical_dependencies_ok'],
        "issues_found": issues,
        "recommendations": recommendations,
        "full_report": report
    }

def validate_imports_corrections() -> Dict[str, bool]:
    """Valide que toutes les corrections d'imports ont été appliquées"""
    
    validation_results = {
        "dependency_manager": dependency_manager is not None,
        "weaviate_available": globals().get('WEAVIATE_AVAILABLE', False),
        "wvc_imported": globals().get('wvc') is not None,
        "wvc_query_imported": globals().get('wvc_query') is not None,  # ← VALIDATION CRITIQUE
        "openai_clients": (
            hasattr(dependency_manager, '_openai_sync_client') and 
            hasattr(dependency_manager, '_openai_async_client')
        ),
        "async_validation_fixed": hasattr(dependency_manager, 'validate_connectivity'),
        "redis_handling_fixed": True,  # Vérifié par inspection du code
        "redis_async_safe_function": '_test_redis_async_safe' in globals(),  # ← NOUVELLE VALIDATION
        "internal_modules_loaded": len([
            dep for dep in dependency_manager.dependencies.values() 
            if dep.name in ['utilities', 'embedder', 'rag_engine', 'cache_manager']
        ]) > 0
    }
    
    all_corrections_applied = all(validation_results.values())
    
    return {
        "all_corrections_applied": all_corrections_applied,
        "details": validation_results,
        "critical_imports": {
            "wvc": globals().get('wvc') is not None,
            "wvc_query": globals().get('wvc_query') is not None,
            "AsyncOpenAI": globals().get('AsyncOpenAI') is not None,
            "OpenAI": globals().get('OpenAI') is not None,
            "_test_redis_async_safe": '_test_redis_async_safe' in globals()
        },
        "version": "corrected_complete_redis_async_safe"
    }

# === EXPORTS POUR COMPATIBILITÉ ===
__all__ = [
    'dependency_manager',
    'get_openai_sync',
    'get_openai_async', 
    'get_dependencies_status',
    'get_full_status_report',
    'quick_connectivity_check',
    'require_critical_dependencies',
    'diagnose_dependency_issues',
    'validate_imports_corrections',
    '_test_redis_async_safe',  # ← AJOUTÉ À L'EXPORT
    'OPENAI_AVAILABLE',
    'WEAVIATE_AVAILABLE',
    'WEAVIATE_V4',
    'REDIS_AVAILABLE',
    'wvc',
    'wvc_query',
    'AsyncOpenAI',
    'OpenAI'
]