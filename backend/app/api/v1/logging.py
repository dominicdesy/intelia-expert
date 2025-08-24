# app/api/v1/logging.py
# -*- coding: utf-8 -*-
"""
🚀 SYSTÈME COMPLET DE LOGGING ET ANALYTICS - FICHIER PRINCIPAL
📊 Point d'entrée principal pour maintenir la compatibilité avec les imports existants
🔧 Réorganisé en modules pour une meilleure maintenabilité

NOUVELLE ARCHITECTURE:
├── logging.py (ce fichier) - Point d'entrée principal pour compatibilité
├── logging_models.py - Enums et classes
├── logging_permissions.py - Système de permissions
├── logging_cache.py - Cache intelligent
├── logging_manager.py - Gestionnaire analytics principal  
├── logging_helpers.py - Fonctions helper et singleton
└── logging_endpoints.py - Endpoints API

✅ COMPATIBILITÉ: Tous les imports existants continuent de fonctionner
"""
import logging

# ============================================================================
# 📦 IMPORTS DEPUIS LES MODULES DÉCOMPOSÉS
# ============================================================================

# Models et enums
from .logging_models import (
    LogLevel,
    ResponseSource, 
    UserRole,
    Permission,
    ROLE_PERMISSIONS
)

# Système de permissions
from .logging_permissions import (
    has_permission,
    require_permission,
    is_admin_user
)

# Cache intelligent
from .logging_cache import (
    get_cached_or_compute,
    clear_analytics_cache,
    get_cache_stats,
    cleanup_expired_cache,
    get_cache_memory_usage  # 🆕 NOUVEAU
)

# Gestionnaire principal
from .logging_manager import AnalyticsManager

# Fonctions helper et singleton
from .logging_helpers import (
    get_analytics_manager,
    reset_analytics_manager,
    get_analytics,
    log_server_performance,
    get_server_analytics,
    log_question_to_analytics,
    track_openai_call
)

# Router pour les endpoints
from .logging_endpoints import router

logger = logging.getLogger(__name__)

# ============================================================================
# 📋 EXPORTS PUBLICS POUR COMPATIBILITÉ
# ============================================================================

# Toutes les classes et fonctions importantes sont exportées
# pour maintenir la compatibilité avec les imports existants
__all__ = [
    # Enums et models
    'LogLevel',
    'ResponseSource', 
    'UserRole',
    'Permission',
    'ROLE_PERMISSIONS',
    
    # Permissions
    'has_permission',
    'require_permission', 
    'is_admin_user',
    
    # Cache
    'get_cached_or_compute',
    'clear_analytics_cache',
    'get_cache_stats',
    'cleanup_expired_cache',
    'get_cache_memory_usage',  # 🆕 NOUVEAU
    
    # Manager principal
    'AnalyticsManager',
    
    # Helpers et singleton
    'get_analytics_manager',
    'reset_analytics_manager',
    'get_analytics',
    'log_server_performance',
    'get_server_analytics', 
    'log_question_to_analytics',
    'track_openai_call',
    
    # Router
    'router'
]

# ============================================================================
# 📝 INFORMATIONS SUR LA NOUVELLE ARCHITECTURE
# ============================================================================

def get_module_info():
    """
    🆕 NOUVELLE FONCTION - Informations sur l'architecture modulaire
    Utile pour debugging et documentation
    """
    return {
        "status": "modular_architecture",
        "version": "2.0",
        "description": "Système de logging réorganisé en modules",
        "modules": {
            "logging_models.py": "Enums et classes de base",
            "logging_permissions.py": "Système de permissions et rôles",
            "logging_cache.py": "Cache intelligent avec TTL",
            "logging_manager.py": "Gestionnaire analytics principal",
            "logging_helpers.py": "Fonctions helper et singleton",
            "logging_endpoints.py": "Endpoints API FastAPI",
            "logging.py": "Point d'entrée principal (ce fichier)"
        },
        "compatibility": "100% compatible avec l'ancienne version",
        "benefits": [
            "Code plus maintenable",
            "Modules plus petits et focalisés", 
            "Tests plus faciles",
            "Imports plus clairs",
            "Réduction de la complexité"
        ]
    }

# ============================================================================
# ⚡ INITIALISATION ET LOGGING
# ============================================================================

logger.info("✅ Système de logging modulaire initialisé")
logger.info("📦 Tous les modules chargés avec succès")
logger.info("🔗 Compatibilité maintenue avec les imports existants")

# Message de transition pour les développeurs
def _log_architecture_info():
    """Log des informations sur la nouvelle architecture"""
    try:
        info = get_module_info()
        logger.info(f"🚀 Architecture modulaire {info['version']} active")
        logger.info(f"📋 {len(info['modules'])} modules chargés")
        logger.info("💡 Consultez get_module_info() pour plus de détails")
    except Exception as e:
        logger.warning(f"⚠️ Erreur log architecture info: {e}")

# Log automatique au démarrage
_log_architecture_info()

# ============================================================================
# 🔄 FONCTIONS DE COMPATIBILITÉ SUPPLÉMENTAIRES
# ============================================================================

def get_all_exports():
    """
    🆕 Fonction utile pour vérifier tous les exports disponibles
    Pratique pour debugging et documentation
    """
    return {
        "total_exports": len(__all__),
        "exports": __all__,
        "module_info": get_module_info()
    }

def validate_imports():
    """
    🆕 Validation que tous les imports fonctionnent correctement
    Utile pour les tests et le debugging
    """
    validation_results = {}
    
    try:
        # Tester les imports principaux
        validation_results["models"] = bool(LogLevel and ResponseSource and UserRole)
        validation_results["permissions"] = callable(has_permission) and callable(require_permission)
        validation_results["cache"] = callable(get_cached_or_compute) and callable(clear_analytics_cache)
        validation_results["manager"] = AnalyticsManager is not None
        validation_results["helpers"] = callable(get_analytics_manager) and callable(get_analytics)
        validation_results["router"] = router is not None
        
        validation_results["overall_status"] = all(validation_results.values())
        validation_results["validated_components"] = sum(1 for v in validation_results.values() if v)
        
    except Exception as e:
        validation_results["error"] = str(e)
        validation_results["overall_status"] = False
    
    return validation_results

# Log de validation automatique
try:
    validation = validate_imports()
    if validation["overall_status"]:
        logger.info(f"✅ Validation réussie: {validation['validated_components']} composants OK")
    else:
        logger.warning(f"⚠️ Validation partielle: {validation}")
except Exception as e:
    logger.error(f"❌ Erreur validation imports: {e}")

# ============================================================================
# 🎯 POINT D'ENTRÉE PRINCIPAL
# ============================================================================

# Ce fichier sert de point d'entrée principal pour maintenir la compatibilité
# Tous les imports existants comme "from app.api.v1.logging import ..." 
# continueront de fonctionner exactement comme avant.

# La seule différence visible est une meilleure organisation du code
# et potentiellement de meilleures performances grâce au cache amélioré.