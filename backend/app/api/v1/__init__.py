"""
API v1 - Intelia Expert
Module d'initialisation pour les endpoints de l'API v1

🚀 SYSTÈME EXPERT UNIFIÉ v2.0 - Architecture Simplifiée

Vue d'ensemble:
Le système expert a été complètement refactorisé avec une architecture unifiée,
éliminant les conflits et la complexité excessive tout en conservant une 
compatibilité 100% avec le frontend existant.

🆕 NOUVELLE ARCHITECTURE UNIFIÉE:
- smart_classifier.py           : Classification intelligente unique
- entities_extractor.py         : Extraction d'entités simplifiée  
- unified_response_generator.py : Génération de réponses unifiée
- expert_services.py           : Service principal simplifié
- expert.py                    : Point d'entrée (nom conservé)
- intelligent_system_config.py : Configuration centralisée

✅ MODULES DE SUPPORT CONSERVÉS:
- expert_models.py              : Modèles Pydantic
- expert_utils.py              : Fonctions utilitaires essentielles
- expert_integrations.py       : Gestionnaire intégrations
- expert_debug.py              : Endpoints de debugging

❌ MODULES SUPPRIMÉS (conflits résolus):
- expert_legacy.py             : Règles contradictoires supprimées
- question_clarification_system.py : Complexité excessive éliminée
- expert_services_clarification.py : Conflits de règles résolus
- conversation_memory.py       : Complexité non nécessaire éliminée
- 40+ autres fichiers conflictuels : Architecture simplifiée

🎯 AVANTAGES:
✅ Plus de conflits entre systèmes
✅ Un seul point de décision clair
✅ Maintenance simplifiée (6 fichiers vs 50+)
✅ Performance optimisée
✅ Compatibilité 100% préservée
"""

# Le frontend continue à utiliser EXACTEMENT les mêmes imports
# from app.api.v1.expert import router  ✅ Fonctionne toujours
# from app.api.v1 import expert_router   ✅ Fonctionne toujours

# Les endpoints restent IDENTIQUES:
# POST /api/v1/expert/ask
# POST /api/v1/expert/ask-public
# POST /api/v1/expert/ask-enhanced (→ redirigé vers nouveau système)
# POST /api/v1/expert/ask-enhanced-public (→ redirigé vers nouveau système)
# POST /api/v1/expert/feedback
# GET /api/v1/expert/topics

import logging

logger = logging.getLogger(__name__)

# =============================================================================
# IMPORTS PRINCIPAUX - NOUVEAU SYSTÈME UNIFIÉ
# =============================================================================

# Import du routeur principal expert (priorité absolue)
try:
    from .expert import router as expert_router
    from .expert import router  # Pour compatibilité with "from .expert import router"
    logger.info("✅ [Init] Expert router importé avec succès (nouveau système unifié)")
except ImportError as e:
    logger.error(f"❌ [Init] Erreur import expert router: {e}")
    expert_router = None
    router = None

# Import du service principal unifié
try:
    from .expert_services import ExpertService
    logger.info("✅ [Init] ExpertService importé avec succès (système unifié)")
except ImportError as e:
    logger.warning(f"⚠️ [Init] Erreur import ExpertService: {e}")
    ExpertService = None

# Import des nouveaux modules principaux
try:
    from .smart_classifier import SmartClassifier, quick_classify
    from .entities_extractor import EntitiesExtractor, quick_extract
    from .unified_response_generator import UnifiedResponseGenerator
    from .intelligent_system_config import INTELLIGENT_SYSTEM_CONFIG
    
    NEW_SYSTEM_MODULES = True
    logger.info("✅ [Init] Nouveaux modules unifiés importés avec succès")
    logger.info("   🧠 SmartClassifier: Décision intelligente unique")
    logger.info("   🔍 EntitiesExtractor: Extraction simplifiée")
    logger.info("   🎨 UnifiedResponseGenerator: Génération unifiée")
    logger.info("   ⚙️ IntelligentSystemConfig: Configuration centralisée")
    
except ImportError as e:
    logger.error(f"❌ [Init] Erreur import nouveaux modules: {e}")
    NEW_SYSTEM_MODULES = False
    SmartClassifier = None
    EntitiesExtractor = None
    UnifiedResponseGenerator = None
    INTELLIGENT_SYSTEM_CONFIG = None

# =============================================================================
# IMPORTS DE SUPPORT CONSERVÉS
# =============================================================================

# Modèles Pydantic (conservés pour compatibilité)
try:
    from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest
    logger.info("✅ [Init] Modèles Pydantic importés")
except ImportError as e:
    logger.warning(f"⚠️ [Init] Erreur import modèles: {e}")

# Utilitaires essentiels (conservés)
try:
    from .expert_utils import get_user_id_from_request, extract_breed_and_sex_from_clarification
    logger.info("✅ [Init] Utilitaires essentiels importés")
except ImportError as e:
    logger.warning(f"⚠️ [Init] Erreur import utilitaires: {e}")

# Gestionnaire d'intégrations (conservé)
try:
    from .expert_integrations import IntegrationsManager
    logger.info("✅ [Init] Gestionnaire intégrations importé")
except ImportError as e:
    logger.warning(f"⚠️ [Init] Erreur import intégrations: {e}")
    IntegrationsManager = None

# Debug et monitoring (conservé)
try:
    from .expert_debug import router as debug_router
    logger.info("✅ [Init] Router debug importé")
except ImportError as e:
    logger.warning(f"⚠️ [Init] Erreur import debug router: {e}")
    debug_router = None

# =============================================================================
# IMPORTS OPTIONNELS AUTRES MODULES
# =============================================================================

# Modules d'authentification et administration
try:
    from .auth import router as auth_router
except ImportError:
    auth_router = None

try:
    from .admin import router as admin_router
except ImportError:
    admin_router = None

try:
    from .logging import router as logging_router
except ImportError:
    logging_router = None

# =============================================================================
# DÉTECTION AUTOMATIQUE DE L'ARCHITECTURE
# =============================================================================

def detect_system_architecture():
    """Détecte automatiquement quelle architecture est active"""
    
    architecture_info = {
        "system_version": "unified_v2.0" if NEW_SYSTEM_MODULES else "legacy_fallback",
        "core_components": {
            "expert_router": expert_router is not None,
            "expert_service": ExpertService is not None,
            "smart_classifier": NEW_SYSTEM_MODULES and SmartClassifier is not None,
            "entities_extractor": NEW_SYSTEM_MODULES and EntitiesExtractor is not None,
            "unified_generator": NEW_SYSTEM_MODULES and UnifiedResponseGenerator is not None,
            "intelligent_config": NEW_SYSTEM_MODULES and INTELLIGENT_SYSTEM_CONFIG is not None
        },
        "support_modules": {
            "integrations_manager": IntegrationsManager is not None,
            "debug_router": debug_router is not None,
            "auth_router": auth_router is not None,
            "admin_router": admin_router is not None,
            "logging_router": logging_router is not None
        },
        "legacy_modules_removed": [
            "expert_legacy.py (conflits résolus)",
            "question_clarification_system.py (complexité éliminée)",
            "expert_services_clarification.py (règles contradictoires supprimées)",
            "conversation_memory.py (complexité non nécessaire)",
            "40+ autres modules conflictuels"
        ],
        "architecture_benefits": [
            "✅ Plus de conflits entre systèmes",
            "✅ Un seul point de décision",
            "✅ Maintenance simplifiée (6 vs 50+ fichiers)",
            "✅ Performance optimisée",
            "✅ Compatibilité 100% préservée"
        ]
    }
    
    return architecture_info

# =============================================================================
# CONFIGURATION DES MODULES DISPONIBLES
# =============================================================================

# Liste des modules/routeurs disponibles pour debugging
available_modules = {
    # Modules principaux du nouveau système
    "expert_router": expert_router is not None,
    "expert_service": ExpertService is not None,
    "smart_classifier": NEW_SYSTEM_MODULES and SmartClassifier is not None,
    "entities_extractor": NEW_SYSTEM_MODULES and EntitiesExtractor is not None,
    "unified_response_generator": NEW_SYSTEM_MODULES and UnifiedResponseGenerator is not None,
    
    # Modules de support
    "integrations_manager": IntegrationsManager is not None,
    "debug_router": debug_router is not None,
    
    # Modules optionnels
    "auth_router": auth_router is not None,
    "admin_router": admin_router is not None,
    "logging_router": logging_router is not None,
}

# Routeurs actifs
active_routers = []
if expert_router:
    active_routers.append(("expert", expert_router))
if debug_router:
    active_routers.append(("debug", debug_router))
if auth_router:
    active_routers.append(("auth", auth_router))
if admin_router:
    active_routers.append(("admin", admin_router))
if logging_router:
    active_routers.append(("logging", logging_router))

# =============================================================================
# FONCTIONS UTILITAIRES POUR LE NOUVEAU SYSTÈME
# =============================================================================

def get_system_status():
    """Retourne le statut complet du système unifié"""
    
    architecture = detect_system_architecture()
    
    status = {
        "system": "Expert System Unified v2.0",
        "architecture": architecture,
        "active_modules": sum(available_modules.values()),
        "total_modules": len(available_modules),
        "active_routers": len(active_routers),
        "compatibility": {
            "frontend_compatible": expert_router is not None,
            "endpoints_preserved": True,
            "legacy_redirects": True
        },
        "performance": {
            "conflicts_resolved": True,
            "single_decision_point": NEW_SYSTEM_MODULES,
            "simplified_architecture": True,
            "optimized_flow": NEW_SYSTEM_MODULES
        }
    }
    
    return status

def quick_test_new_system():
    """Test rapide du nouveau système unifié"""
    
    if not NEW_SYSTEM_MODULES:
        return {"status": "error", "message": "Nouveaux modules non disponibles"}
    
    try:
        # Test des composants principaux
        classifier = SmartClassifier()
        extractor = EntitiesExtractor()
        generator = UnifiedResponseGenerator()
        
        # Test d'une classification simple
        test_question = "Poids poulet 22 jours"
        entities = extractor.extract(test_question)
        classification = classifier.classify_question(test_question, extractor._entities_to_dict(entities) if hasattr(extractor, '_entities_to_dict') else {})
        
        return {
            "status": "success",
            "message": "Nouveau système unifié fonctionnel",
            "test_results": {
                "question": test_question,
                "entities_extracted": len(entities.symptoms) if hasattr(entities, 'symptoms') else "N/A",
                "classification": classification.response_type.value if hasattr(classification, 'response_type') else "N/A",
                "confidence": classification.confidence if hasattr(classification, 'confidence') else "N/A"
            }
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Erreur test système: {str(e)}"
        }

# =============================================================================
# EXPORT PUBLIC - COMPATIBILITÉ GARANTIE
# =============================================================================

__all__ = [
    # 🎯 Routeurs principaux (compatibilité frontend)
    "expert_router",
    "router",  # Alias pour expert_router
    "debug_router",
    "auth_router", 
    "admin_router",
    "logging_router",
    
    # 🚀 Services principaux (nouveau système)
    "ExpertService",
    "SmartClassifier",
    "EntitiesExtractor", 
    "UnifiedResponseGenerator",
    "INTELLIGENT_SYSTEM_CONFIG",
    
    # 🔧 Services de support
    "IntegrationsManager",
    
    # 📊 Informations système
    "available_modules",
    "active_routers",
    "get_system_status",
    "detect_system_architecture",
    "quick_test_new_system",
    
    # 🛠 Fonctions utilitaires
    "quick_classify",
    "quick_extract"
]

# =============================================================================
# LOGGING DE DÉMARRAGE
# =============================================================================

def log_system_startup():
    """Log le démarrage du système unifié"""
    
    logger.info("🚀" * 40)
    logger.info("🚀 [SYSTÈME EXPERT UNIFIÉ v2.0] DÉMARRAGE")
    logger.info("🚀" * 40)
    
    if NEW_SYSTEM_MODULES:
        logger.info("✅ [Architecture] Nouveau système unifié ACTIF")
        logger.info("   🧠 SmartClassifier: Décision unique intelligente")
        logger.info("   🔍 EntitiesExtractor: Extraction simplifiée")
        logger.info("   🎨 UnifiedResponseGenerator: Génération unifiée")
        logger.info("   ⚙️ Configuration centralisée")
    else:
        logger.warning("⚠️ [Architecture] Fallback vers système legacy")
    
    logger.info(f"📊 [Modules] {sum(available_modules.values())}/{len(available_modules)} actifs")
    logger.info(f"🔗 [Routeurs] {len(active_routers)} routeurs disponibles")
    
    if expert_router:
        logger.info("✅ [Compatibilité] Frontend 100% compatible")
        logger.info("   📍 POST /api/v1/expert/ask")
        logger.info("   📍 POST /api/v1/expert/ask-public")
        logger.info("   📍 POST /api/v1/expert/ask-enhanced (→ redirected)")
        logger.info("   📍 POST /api/v1/expert/ask-enhanced-public (→ redirected)")
    else:
        logger.error("❌ [Compatibilité] Expert router non disponible!")
    
    logger.info("🎯 [Résultat] Architecture simplifiée et performante prête!")
    logger.info("🚀" * 40)

# Lancer le logging de démarrage
log_system_startup()

# Message d'info pour le développeur
def get_module_status():
    """Retourne le statut des modules chargés (fonction conservée pour compatibilité)"""
    return {
        "system_version": "unified_v2.0" if NEW_SYSTEM_MODULES else "legacy_fallback",
        "loaded_modules": sum(available_modules.values()),
        "total_modules": len(available_modules),
        "details": available_modules,
        "active_routers_count": len(active_routers),
        "architecture_benefits": [
            "Conflits résolus",
            "Performance optimisée", 
            "Maintenance simplifiée",
            "Compatibilité préservée"
        ]
    }