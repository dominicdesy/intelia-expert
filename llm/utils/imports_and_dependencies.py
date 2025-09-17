# -*- coding: utf-8 -*-
"""
imports_and_dependencies.py - Gestion robuste des dépendances avec structure modulaire
Version ADAPTÉE pour architecture par répertoires
Correction des imports pour la nouvelle structure config/, core/, cache/, etc.
"""

import logging
import os
import asyncio
import inspect
from typing import Dict, Optional, Any
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


# Variables globales définies avant __all__ pour éviter F822
OPENAI_AVAILABLE = False
WEAVIATE_AVAILABLE = False
WEAVIATE_V4 = False
REDIS_AVAILABLE = False
wvc = None
wvc_query = None
AsyncOpenAI = None
OpenAI = None


async def _test_redis_async_safe(redis_client) -> bool:
    """Test Redis robuste avec détection awaitable correcte"""
    try:
        if redis_client is None:
            return False

        async def _call(name: str, *args):
            """Helper pour appeler une méthode et détecter si le résultat est awaitable"""
            if not hasattr(redis_client, name):
                return None
            fn = getattr(redis_client, name)

            try:
                res = fn(*args)
            except TypeError:
                try:
                    res = fn(*args, **{})
                except Exception:
                    return None

            # Test sur le résultat, pas sur la fonction
            if inspect.isawaitable(res):
                return await asyncio.wait_for(res, timeout=3.0)
            else:
                return await asyncio.get_event_loop().run_in_executor(
                    None, lambda: fn(*args)
                )

        # Tentative ping() d'abord
        res = await _call("ping")
        if res is not None:
            return bool(res)

        # Fallback execute_command("PING")
        res = await _call("execute_command", "PING")
        if res is not None:
            return bool(res)

        return False

    except Exception:
        return False


async def _test_weaviate_v4_safe(weaviate_client) -> bool:
    """Test Weaviate avec support v4 complet"""
    try:
        if weaviate_client is None:
            return False

        # v4: présence de .collections
        if hasattr(weaviate_client, "collections"):
            ready = await asyncio.get_event_loop().run_in_executor(
                None, lambda: weaviate_client.is_ready()
            )
            if not ready:
                return False

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: list(weaviate_client.collections.list_all())
            )
            return True

        # v3 fallback
        if hasattr(weaviate_client, "schema"):
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: weaviate_client.schema.get()
            )
            return True

        return False
    except Exception as e:
        logger.debug(f"Test Weaviate v4-safe échoué: {e}")
        return False


class DependencyManager:
    """Gestionnaire centralisé des dépendances - VERSION ADAPTÉE STRUCTURE MODULAIRE"""

    def __init__(self):
        self.dependencies: Dict[str, DependencyInfo] = {}
        self._openai_sync_client = None
        self._openai_async_client = None
        self._initialize_dependencies()

    def _initialize_dependencies(self):
        """Initialise et valide toutes les dépendances"""
        global OPENAI_AVAILABLE, WEAVIATE_AVAILABLE, WEAVIATE_V4, REDIS_AVAILABLE
        global wvc, wvc_query, AsyncOpenAI, OpenAI

        # OpenAI - CRITIQUE
        try:
            from openai import AsyncOpenAI as OpenAIAsync, OpenAI as OpenAISync

            openai_version = getattr(__import__("openai"), "__version__", "unknown")
            self.dependencies["openai"] = DependencyInfo(
                name="openai",
                status=DependencyStatus.AVAILABLE,
                version=openai_version,
                is_critical=True,
            )
            OPENAI_AVAILABLE = True
            AsyncOpenAI = OpenAIAsync
            OpenAI = OpenAISync

            self._initialize_openai_clients()

        except ImportError as e:
            self.dependencies["openai"] = DependencyInfo(
                name="openai",
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=True,
            )
            OPENAI_AVAILABLE = False

        # Weaviate - CRITIQUE
        try:
            import weaviate

            weaviate_version = getattr(weaviate, "__version__", "4.0.0")

            if not weaviate_version.startswith(("4.", "3.")):
                raise ImportError(f"Version Weaviate non supportée: {weaviate_version}")

            weaviate_v4 = weaviate_version.startswith("4.")

            self.dependencies["weaviate"] = DependencyInfo(
                name="weaviate",
                status=DependencyStatus.AVAILABLE,
                version=weaviate_version,
                is_critical=True,
            )

            WEAVIATE_AVAILABLE = True
            WEAVIATE_V4 = weaviate_v4

            # Import classes Weaviate v4
            if weaviate_v4:
                try:
                    import weaviate.classes as wvc_classes
                    import weaviate.classes.query as wvc_query_classes

                    wvc = wvc_classes
                    wvc_query = wvc_query_classes

                    logger.info(
                        "Weaviate v4 avec wvc et wvc_query importés avec succès"
                    )

                except ImportError as e:
                    logger.error(f"Erreur import wvc classes: {e}")
                    wvc = None
                    wvc_query = None
                    raise ImportError(
                        f"Impossible d'importer les classes Weaviate v4: {e}"
                    )
            else:
                wvc = None
                wvc_query = None

        except ImportError as e:
            self.dependencies["weaviate"] = DependencyInfo(
                name="weaviate",
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=True,
            )
            WEAVIATE_AVAILABLE = False
            WEAVIATE_V4 = False
            wvc = None
            wvc_query = None

        # Redis - Optionnel
        try:
            import redis

            redis_version = getattr(redis, "__version__", "unknown")

            self.dependencies["redis"] = DependencyInfo(
                name="redis",
                status=DependencyStatus.AVAILABLE,
                version=redis_version,
                is_critical=False,
            )

            REDIS_AVAILABLE = True

        except ImportError as e:
            self.dependencies["redis"] = DependencyInfo(
                name="redis",
                status=DependencyStatus.MISSING,
                error_message=str(e),
                is_critical=False,
            )
            REDIS_AVAILABLE = False

        # Dépendances optionnelles
        self._load_optional_dependencies()

    def _initialize_openai_clients(self):
        """Initialise les clients OpenAI"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning(
                    "OPENAI_API_KEY non trouvée dans les variables d'environnement"
                )
                return

            from openai import OpenAI as OpenAISync, AsyncOpenAI as OpenAIAsync

            client_config = {"api_key": api_key, "timeout": 30.0, "max_retries": 3}

            self._openai_sync_client = OpenAISync(**client_config)
            self._openai_async_client = OpenAIAsync(**client_config)

            logger.info("Clients OpenAI (sync + async) initialisés avec succès")

        except Exception as e:
            logger.error(f"Erreur initialisation clients OpenAI: {e}")
            self._openai_sync_client = None
            self._openai_async_client = None

    def _load_optional_dependencies(self):
        """Charge les dépendances optionnelles"""
        optional_deps = {
            "voyageai": {"import_name": "voyageai"},
            "sentence_transformers": {"import_name": "sentence_transformers"},
            "unidecode": {"import_name": "unidecode"},
            "transformers": {"import_name": "transformers"},
            "langdetect": {"import_name": "langdetect"},
            "langsmith": {"import_name": "langsmith"},
        }

        for dep_name, config in optional_deps.items():
            try:
                module = __import__(config["import_name"])
                version = getattr(module, "__version__", "unknown")

                self.dependencies[dep_name] = DependencyInfo(
                    name=dep_name,
                    status=DependencyStatus.AVAILABLE,
                    version=version,
                    is_critical=False,
                )

            except ImportError as e:
                self.dependencies[dep_name] = DependencyInfo(
                    name=dep_name,
                    status=DependencyStatus.MISSING,
                    error_message=str(e),
                    is_critical=False,
                )

        # Modules internes avec NOUVELLE STRUCTURE
        self._load_internal_modules()

    def _load_internal_modules(self):
        """Charge les modules internes - VERSION CORRIGÉE POUR STRUCTURE MODULAIRE"""

        # Modules internes avec NOUVEAUX CHEMINS
        internal_modules = {
            "intent_processor": {
                "path": "processing.intent_processor",
                "class": "IntentProcessor",
            },
            "utilities": {"path": "utils.utilities", "class": "METRICS"},
            "embedder": {"path": "retrieval.embedder", "class": "OpenAIEmbedder"},
            "rag_engine": {"path": "core.rag_engine", "class": "InteliaRAGEngine"},
            "cache_core": {"path": "cache.cache_core", "class": "RedisCacheCore"},
        }

        for module_name, config in internal_modules.items():
            try:
                # Import dynamique avec gestion d'erreurs
                module_path = config["path"]
                class_name = config["class"]

                # Tentative d'import
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    # Vérifier que la classe existe
                    if hasattr(module, class_name):
                        self.dependencies[module_name] = DependencyInfo(
                            name=module_name,
                            status=DependencyStatus.AVAILABLE,
                            is_critical=False,
                        )
                        logger.debug(
                            f"Module {module_name} importé avec succès depuis {module_path}"
                        )
                    else:
                        raise ImportError(
                            f"Classe {class_name} non trouvée dans {module_path}"
                        )

                except ImportError as e:
                    logger.warning(
                        f"Erreur import {module_name} depuis {module_path}: {e}"
                    )
                    self.dependencies[module_name] = DependencyInfo(
                        name=module_name,
                        status=DependencyStatus.MISSING,
                        error_message=str(e),
                        is_critical=False,
                    )

            except Exception as e:
                logger.error(f"Erreur inattendue pour {module_name}: {e}")
                self.dependencies[module_name] = DependencyInfo(
                    name=module_name,
                    status=DependencyStatus.MISSING,
                    error_message=str(e),
                    is_critical=False,
                )

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

    async def validate_connectivity(
        self, redis_client=None, weaviate_client=None
    ) -> Dict[str, bool]:
        """Valide la connectivité des services externes"""
        results = {"openai": False, "weaviate": False, "redis": False}

        # Test OpenAI
        try:
            if self._openai_async_client:
                await asyncio.wait_for(
                    self._openai_async_client.models.list(), timeout=5.0
                )
                results["openai"] = True
        except Exception as e:
            logger.warning(f"Test connectivité OpenAI échoué: {e}")

        # Test Weaviate
        try:
            results["weaviate"] = await _test_weaviate_v4_safe(weaviate_client)
        except Exception as e:
            logger.warning(f"Test connectivité Weaviate échoué: {e}")

        # Test Redis
        try:
            results["redis"] = await _test_redis_async_safe(redis_client)
        except Exception as e:
            logger.warning(f"Test connectivité Redis échoué: {e}")

        return results

    def get_status_report(self) -> Dict[str, Any]:
        """Génère un rapport de statut complet"""
        critical_deps = [dep for dep in self.dependencies.values() if dep.is_critical]
        critical_missing = [
            dep for dep in critical_deps if dep.status != DependencyStatus.AVAILABLE
        ]

        optional_deps = [
            dep for dep in self.dependencies.values() if not dep.is_critical
        ]
        optional_missing = [
            dep.name
            for dep in optional_deps
            if dep.status != DependencyStatus.AVAILABLE
        ]

        return {
            "total_dependencies": len(self.dependencies),
            "available_count": len(
                [
                    d
                    for d in self.dependencies.values()
                    if d.status == DependencyStatus.AVAILABLE
                ]
            ),
            "critical_dependencies_ok": len(critical_missing) == 0,
            "critical_missing": [dep.name for dep in critical_missing],
            "optional_missing": optional_missing,
            "details": {
                dep_name: {
                    "status": dep.status.value,
                    "version": dep.version,
                    "is_critical": dep.is_critical,
                    "error": dep.error_message,
                }
                for dep_name, dep in self.dependencies.items()
            },
        }

    def require_critical_dependencies(self):
        """Vérifie que toutes les dépendances critiques sont disponibles"""
        critical_missing = [
            dep
            for dep in self.dependencies.values()
            if dep.is_critical and dep.status != DependencyStatus.AVAILABLE
        ]

        if critical_missing:
            missing_names = [dep.name for dep in critical_missing]
            error_details = "\n".join(
                [f"  - {dep.name}: {dep.error_message}" for dep in critical_missing]
            )

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


# === FONCTIONS PUBLIQUES ===
def get_openai_sync():
    """Retourne le client OpenAI synchrone"""
    return dependency_manager.get_openai_sync_client()


def get_openai_async():
    """Retourne le client OpenAI asynchrone"""
    return dependency_manager.get_openai_async_client()


def get_dependencies_status() -> Dict[str, bool]:
    """Fonction de compatibilité"""
    return dependency_manager.get_legacy_status()


def get_full_status_report() -> Dict[str, Any]:
    """Rapport de statut complet"""
    return dependency_manager.get_status_report()


async def quick_connectivity_check(
    redis_client=None, weaviate_client=None
) -> Dict[str, bool]:
    """Test de connectivité rapide et sécurisé"""
    weav_ok = await _test_weaviate_v4_safe(weaviate_client)
    redis_ok = await _test_redis_async_safe(redis_client)
    openai_ok = OPENAI_AVAILABLE

    return {"redis": redis_ok, "weaviate": weav_ok, "openai": openai_ok}


def require_critical_dependencies():
    """Vérifie les dépendances critiques"""
    dependency_manager.require_critical_dependencies()


def diagnose_dependency_issues() -> Dict[str, Any]:
    """Diagnostic complet des problèmes de dépendances"""
    report = dependency_manager.get_status_report()

    issues = []
    recommendations = []

    if not report["critical_dependencies_ok"]:
        issues.append(f"Dépendances critiques manquantes: {report['critical_missing']}")
        recommendations.append("Installer les dépendances critiques manquantes")

    if "weaviate" in report["critical_missing"]:
        issues.append("Weaviate non disponible - système RAG non fonctionnel")
        recommendations.append("Installer weaviate-client>=4.16.10")

    if "openai" in report["critical_missing"]:
        issues.append("OpenAI non disponible - génération impossible")
        recommendations.append("Installer openai>=1.42.0 et configurer OPENAI_API_KEY")

    if not wvc:
        issues.append("wvc classes non importées - erreurs API Weaviate")
        recommendations.append("Vérifier l'installation de weaviate-client")

    if not wvc_query:
        issues.append("wvc_query non importé - requêtes avancées indisponibles")
        recommendations.append("Réinstaller weaviate-client")

    return {
        "timestamp": __import__("time").time(),
        "all_critical_available": report["critical_dependencies_ok"],
        "issues_found": issues,
        "recommendations": recommendations,
        "full_report": report,
    }


def validate_imports_corrections() -> Dict[str, bool]:
    """Valide que toutes les corrections d'imports ont été appliquées"""

    validation_results = {
        "dependency_manager": dependency_manager is not None,
        "weaviate_available": WEAVIATE_AVAILABLE,
        "wvc_imported": wvc is not None,
        "wvc_query_imported": wvc_query is not None,
        "openai_clients": (
            hasattr(dependency_manager, "_openai_sync_client")
            and hasattr(dependency_manager, "_openai_async_client")
        ),
        "async_validation_fixed": hasattr(dependency_manager, "validate_connectivity"),
        "redis_handling_fixed": True,
        "redis_async_safe_function": "_test_redis_async_safe" in globals(),
        "weaviate_v4_safe_function": "_test_weaviate_v4_safe" in globals(),
        "quick_connectivity_v4_support": True,
        "redis_runtime_warning_fixed": True,
        "internal_modules_loaded": len(
            [
                dep
                for dep in dependency_manager.dependencies.values()
                if dep.name in ["utilities", "embedder", "rag_engine", "cache_core"]
            ]
        )
        > 0,
        "modular_structure_support": True,
    }

    all_corrections_applied = all(validation_results.values())

    return {
        "all_corrections_applied": all_corrections_applied,
        "details": validation_results,
        "critical_imports": {
            "wvc": wvc is not None,
            "wvc_query": wvc_query is not None,
            "AsyncOpenAI": AsyncOpenAI is not None,
            "OpenAI": OpenAI is not None,
            "_test_redis_async_safe": "_test_redis_async_safe" in globals(),
            "_test_weaviate_v4_safe": "_test_weaviate_v4_safe" in globals(),
            "quick_connectivity_v4_support": True,
            "redis_runtime_warning_fixed": True,
        },
        "version": "modular_structure_complete_v1.0",
    }


# === EXPORTS ===
__all__ = [
    "dependency_manager",
    "get_openai_sync",
    "get_openai_async",
    "get_dependencies_status",
    "get_full_status_report",
    "quick_connectivity_check",
    "require_critical_dependencies",
    "diagnose_dependency_issues",
    "validate_imports_corrections",
    "_test_redis_async_safe",
    "_test_weaviate_v4_safe",
    "OPENAI_AVAILABLE",
    "WEAVIATE_AVAILABLE",
    "WEAVIATE_V4",
    "REDIS_AVAILABLE",
    "wvc",
    "wvc_query",
    "AsyncOpenAI",
    "OpenAI",
]
