# app/api/v1/__init__.py - VERSION 5.0 AVEC SYSTÈME DE CACHE STATISTIQUES
# ✅ CONSERVATION INTÉGRALE DU CODE ORIGINAL + AJOUTS CACHE SAFE
# 🚀 NOUVEAU: Support des routers de cache statistiques ultra-rapides
# 🔧 INTEGRATION SAFE: Imports conditionnels avec fallbacks

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Import avec debug détaillé pour chaque router
logger.info("📄 Début import des routers...")

# System router
try:
    from .system import router as system_router
    logger.info("✅ System router importé avec %d routes", len(system_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import system router: %s", e)
    import traceback
    logger.error("❌ Traceback system: %s", traceback.format_exc())
    system_router = None

# Auth router - AVEC DEBUG COMPLET
try:
    logger.info("📄 Tentative import auth router...")
    from .auth import router as auth_router
    logger.info("✅ Auth router importé avec succès!")
    logger.info("✅ Auth router a %d routes", len(auth_router.routes))
    logger.info("✅ Auth router prefix: %s", getattr(auth_router, 'prefix', 'None'))
    auth_routes = [f"{route.path} ({', '.join(route.methods)})" for route in auth_router.routes[:5]]
    logger.info("✅ Auth routes échantillon: %s", auth_routes)
except ImportError as ie:
    logger.error("❌ IMPORT ERROR auth router: %s", ie)
    logger.error("❌ Le module auth.py n'a pas pu être importé")
    import traceback
    logger.error("❌ Traceback import auth: %s", traceback.format_exc())
    auth_router = None
except AttributeError as ae:
    logger.error("❌ ATTRIBUTE ERROR auth router: %s", ae)
    logger.error("❌ Le module auth.py n'exporte pas 'router'")
    auth_router = None
except Exception as e:
    logger.error("❌ ERREUR GÉNÉRALE auth router: %s", e)
    logger.error("❌ Type d'erreur: %s", type(e).__name__)
    import traceback
    logger.error("❌ Traceback complet auth: %s", traceback.format_exc())
    auth_router = None

# 🆕 NOUVEAU: Auth invitations router
try:
    logger.info("📄 Tentative import auth_invitations router...")
    from .auth_invitations import router as auth_invitations_router
    logger.info("✅ Auth invitations router importé avec succès!")
    logger.info("✅ Auth invitations router a %d routes", len(auth_invitations_router.routes))
    logger.info("✅ Auth invitations router prefix: %s", getattr(auth_invitations_router, 'prefix', 'None'))
    auth_inv_routes = [f"{route.path} ({', '.join(route.methods)})" for route in auth_invitations_router.routes[:3]]
    logger.info("✅ Auth invitations routes échantillon: %s", auth_inv_routes)
except ImportError as ie:
    logger.error("❌ IMPORT ERROR auth_invitations router: %s", ie)
    logger.error("❌ Le module auth_invitations.py n'a pas pu être importé")
    import traceback
    logger.error("❌ Traceback import auth_invitations: %s", traceback.format_exc())
    auth_invitations_router = None
except AttributeError as ae:
    logger.error("❌ ATTRIBUTE ERROR auth_invitations router: %s", ae)
    logger.error("❌ Le module auth_invitations.py n'exporte pas 'router'")
    auth_invitations_router = None
except Exception as e:
    logger.error("❌ ERREUR GÉNÉRALE auth_invitations router: %s", e)
    logger.error("❌ Type d'erreur: %s", type(e).__name__)
    import traceback
    logger.error("❌ Traceback complet auth_invitations: %s", traceback.format_exc())
    auth_invitations_router = None

# 🚀 NOUVEAU: Stats Fast router (endpoints ultra-rapides)
STATS_FAST_AVAILABLE = False
try:
    logger.info("📄 Tentative import stats_fast router...")
    from .stats_fast import router as stats_fast_router
    STATS_FAST_AVAILABLE = True
    logger.info("✅ Stats Fast router importé avec succès!")
    logger.info("✅ Stats Fast router a %d routes", len(stats_fast_router.routes))
    logger.info("✅ Stats Fast router prefix: %s", getattr(stats_fast_router, 'prefix', 'None'))
    stats_fast_routes = [f"{route.path} ({', '.join(route.methods)})" for route in stats_fast_router.routes[:3]]
    logger.info("✅ Stats Fast routes échantillon: %s", stats_fast_routes)
except ImportError as ie:
    logger.warning("⚠️ IMPORT WARNING stats_fast router: %s", ie)
    logger.warning("⚠️ Le système de cache stats n'est pas encore déployé (normal)")
    stats_fast_router = None
    STATS_FAST_AVAILABLE = False
except Exception as e:
    logger.error("❌ ERREUR stats_fast router: %s", e)
    import traceback
    logger.error("❌ Traceback stats_fast: %s", traceback.format_exc())
    stats_fast_router = None
    STATS_FAST_AVAILABLE = False

# 🚀 NOUVEAU: Stats Admin router (administration cache)
STATS_ADMIN_AVAILABLE = False
try:
    logger.info("📄 Tentative import stats_admin router...")
    from .stats_admin import router as stats_admin_router
    STATS_ADMIN_AVAILABLE = True
    logger.info("✅ Stats Admin router importé avec succès!")
    logger.info("✅ Stats Admin router a %d routes", len(stats_admin_router.routes))
    logger.info("✅ Stats Admin router prefix: %s", getattr(stats_admin_router, 'prefix', 'None'))
    stats_admin_routes = [f"{route.path} ({', '.join(route.methods)})" for route in stats_admin_router.routes[:3]]
    logger.info("✅ Stats Admin routes échantillon: %s", stats_admin_routes)
except ImportError as ie:
    logger.warning("⚠️ IMPORT WARNING stats_admin router: %s", ie)
    logger.warning("⚠️ Le système d'administration cache n'est pas encore déployé (normal)")
    stats_admin_router = None
    STATS_ADMIN_AVAILABLE = False
except Exception as e:
    logger.error("❌ ERREUR stats_admin router: %s", e)
    import traceback
    logger.error("❌ Traceback stats_admin: %s", traceback.format_exc())
    stats_admin_router = None
    STATS_ADMIN_AVAILABLE = False

# Admin router
try:
    from .admin import router as admin_router
    logger.info("✅ Admin router importé avec %d routes", len(admin_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import admin router: %s", e)
    admin_router = None

# Health router
try:
    from .health import router as health_router
    logger.info("✅ Health router importé avec %d routes", len(health_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import health router: %s", e)
    health_router = None

# Invitations router
try:
    from .invitations import router as invitations_router
    logger.info("✅ Invitations router importé avec %d routes", len(invitations_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import invitations router: %s", e)
    invitations_router = None

# Logging router
try:
    from .logging import router as logging_router
    logger.info("✅ Logging router importé avec %d routes", len(logging_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import logging router: %s", e)
    logging_router = None

# Billing router
try:
    from .billing import router as billing_router
    logger.info("✅ Billing router importé avec %d routes", len(billing_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import billing router: %s", e)
    billing_router = None

# Billing OpenAI router
try:
    from .billing_openai import router as billing_openai_router
    logger.info("✅ Billing OpenAI router importé avec %d routes", len(billing_openai_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import billing_openai router: %s", e)
    billing_openai_router = None

# Expert router
try:
    from .expert import router as expert_router
    logger.info("✅ Expert router importé avec %d routes", len(expert_router.routes))
except Exception as e:
    logger.error("❌ ERREUR import expert router: %s", e)
    expert_router = None

# Conversations router (conditionnel)
try:
    from .conversations import router as conversations_router
    CONVERSATIONS_AVAILABLE = True
    logger.info("✅ Conversations router importé avec %d routes", len(conversations_router.routes))
except ImportError:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None
    logger.warning("⚠️ Conversations router non disponible (normal si pas encore créé)")
except Exception as e:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None
    logger.error("❌ ERREUR import conversations router: %s", e)

# Création du router principal
logger.info("📄 Création du router principal v1...")
router = APIRouter(prefix="/v1")

# Montage des routers avec debug
logger.info("📄 Montage des routers...")

# System
if system_router:
    router.include_router(system_router, tags=["System"])
    logger.info("✅ System router monté")
else:
    logger.error("❌ System router non monté (échec import)")

# Auth - AVEC DEBUG COMPLET
if auth_router:
    try:
        router.include_router(auth_router, tags=["Auth"])
        logger.info("✅ Auth router monté avec succès!")
        logger.info("✅ Auth router maintenant disponible sur /v1/auth/*")
    except Exception as e:
        logger.error("❌ ERREUR montage auth router: %s", e)
        import traceback
        logger.error("❌ Traceback montage auth: %s", traceback.format_exc())
else:
    logger.error("❌ Auth router NON MONTÉ - import a échoué")

# 🆕 NOUVEAU: Auth invitations - AVEC DEBUG COMPLET
if auth_invitations_router:
    try:
        router.include_router(auth_invitations_router, tags=["Auth-Invitations"])
        logger.info("✅ Auth invitations router monté avec succès!")
        logger.info("✅ Auth invitations router maintenant disponible sur /v1/auth/invitations/*")
    except Exception as e:
        logger.error("❌ ERREUR montage auth_invitations router: %s", e)
        import traceback
        logger.error("❌ Traceback montage auth_invitations: %s", traceback.format_exc())
else:
    logger.error("❌ Auth invitations router NON MONTÉ - import a échoué")

# 🚀 NOUVEAU: Stats Fast router (endpoints ultra-rapides)
if STATS_FAST_AVAILABLE and stats_fast_router:
    try:
        router.include_router(stats_fast_router, prefix="/stats-fast", tags=["Stats-Fast"])
        logger.info("✅ Stats Fast router monté avec succès!")
        logger.info("✅ Stats Fast router maintenant disponible sur /v1/stats-fast/*")
        logger.info("🚀 Endpoints ultra-rapides activés (<100ms vs 10-30s)")
    except Exception as e:
        logger.error("❌ ERREUR montage stats_fast router: %s", e)
        import traceback
        logger.error("❌ Traceback montage stats_fast: %s", traceback.format_exc())
else:
    if not STATS_FAST_AVAILABLE:
        logger.info("ℹ️ Stats Fast router non monté - modules cache non disponibles")
    else:
        logger.error("❌ Stats Fast router NON MONTÉ - import a échoué")

# 🚀 NOUVEAU: Stats Admin router (administration cache)
if STATS_ADMIN_AVAILABLE and stats_admin_router:
    try:
        router.include_router(stats_admin_router, prefix="/stats-admin", tags=["Stats-Admin"])
        logger.info("✅ Stats Admin router monté avec succès!")
        logger.info("✅ Stats Admin router maintenant disponible sur /v1/stats-admin/*")
        logger.info("🔧 Administration cache activée (super admin uniquement)")
    except Exception as e:
        logger.error("❌ ERREUR montage stats_admin router: %s", e)
        import traceback
        logger.error("❌ Traceback montage stats_admin: %s", traceback.format_exc())
else:
    if not STATS_ADMIN_AVAILABLE:
        logger.info("ℹ️ Stats Admin router non monté - modules cache non disponibles")
    else:
        logger.error("❌ Stats Admin router NON MONTÉ - import a échoué")

# Admin
if admin_router:
    router.include_router(admin_router, tags=["Admin"])
    logger.info("✅ Admin router monté")

# Health
if health_router:
    router.include_router(health_router, tags=["Health"])
    logger.info("✅ Health router monté")

# Invitations
if invitations_router:
    router.include_router(invitations_router, tags=["Invitations"])
    logger.info("✅ Invitations router monté")

# Logging
if logging_router:
    router.include_router(logging_router, tags=["Logging"])
    logger.info("✅ Logging router monté")

# Billing
if billing_router:
    router.include_router(billing_router, tags=["Billing"])
    logger.info("✅ Billing router monté")

# Billing OpenAI
if billing_openai_router:
    router.include_router(billing_openai_router, prefix="/billing", tags=["Billing-OpenAI"])
    logger.info("✅ Billing OpenAI router monté")

# Conversations (conditionnel)
if CONVERSATIONS_AVAILABLE and conversations_router:
    router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
    logger.info("✅ Conversations router monté")

# Expert
if expert_router:
    router.include_router(expert_router, prefix="/expert", tags=["Expert"])
    logger.info("✅ Expert router monté")

# Résumé final
total_routes = len(router.routes)
logger.info("🎯 Router v1 créé avec %d routes au total", total_routes)

# Debug des routes auth spécifiquement
auth_route_count = len([r for r in router.routes if '/auth' in r.path])
logger.info("🔍 Routes auth détectées: %d", auth_route_count)

if auth_route_count > 0:
    auth_routes_debug = [f"{r.path} ({', '.join(r.methods)})" for r in router.routes if '/auth' in r.path]
    logger.info("🔍 Routes auth disponibles: %s", auth_routes_debug[:5])
else:
    logger.error("❌ AUCUNE route auth détectée dans le router final!")

# 🆕 NOUVEAU: Debug des routes auth invitations spécifiquement
auth_inv_route_count = len([r for r in router.routes if '/auth/invitations' in r.path])
logger.info("🔍 Routes auth invitations détectées: %d", auth_inv_route_count)

if auth_inv_route_count > 0:
    auth_inv_routes_debug = [f"{r.path} ({', '.join(r.methods)})" for r in router.routes if '/auth/invitations' in r.path]
    logger.info("🔍 Routes auth invitations disponibles: %s", auth_inv_routes_debug)
else:
    logger.error("❌ AUCUNE route auth invitations détectée dans le router final!")

# 🚀 NOUVEAU: Debug des routes stats cache spécifiquement
stats_route_count = len([r for r in router.routes if '/stats-' in r.path])
logger.info("🔍 Routes stats cache détectées: %d", stats_route_count)

if stats_route_count > 0:
    stats_routes_debug = [f"{r.path} ({', '.join(r.methods)})" for r in router.routes if '/stats-' in r.path]
    logger.info("🔍 Routes stats cache disponibles: %s", stats_routes_debug)
    logger.info("🚀 Système de cache statistiques ACTIF!")
else:
    logger.info("ℹ️ Aucune route stats cache détectée - système non encore déployé")

# 📊 NOUVEAU: Récapitulatif système cache
cache_status = {
    "stats_fast": STATS_FAST_AVAILABLE,
    "stats_admin": STATS_ADMIN_AVAILABLE,
    "total_cache_routes": stats_route_count
}
logger.info("📊 Status système cache: %s", cache_status)

if STATS_FAST_AVAILABLE or STATS_ADMIN_AVAILABLE:
    logger.info("🎉 SYSTÈME DE CACHE STATISTIQUES PARTIELLEMENT/TOTALEMENT ACTIVÉ!")
    logger.info("⚡ Performance: Endpoints ultra-rapides disponibles")
    logger.info("🔧 Administration: Contrôle cache disponible")
else:
    logger.info("ℹ️ Système de cache non disponible - fonctionnement normal maintenu")

__all__ = ["router"]