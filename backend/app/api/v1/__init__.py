# app/api/v1/__init__.py - VERSION 5.4 CORRIGÉE
# CONSERVATION INTÉGRALE DU CODE ORIGINAL + CORRECTIONS ERREURS IMPORT
# Support des routers de cache statistiques ultra-rapides
# NOUVEAU: Support du router users pour gestion profils
# SUPPRESSION: auth_invitations router (fonctionnalités intégrées dans invitations)
# CORRECTION: billing_openai et expert désactivés temporairement

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Import avec debug detaille pour chaque router
logger.info("Debut import des routers...")

# System router
try:
    from .system import router as system_router

    logger.info("System router importe avec %d routes", len(system_router.routes))
except Exception as e:
    logger.error("ERREUR import system router: %s", e)
    import traceback

    logger.error("Traceback system: %s", traceback.format_exc())
    system_router = None

# Auth router - AVEC DEBUG COMPLET
try:
    logger.info("Tentative import auth router...")
    from .auth import router as auth_router

    logger.info("Auth router importe avec succes!")
    logger.info("Auth router a %d routes", len(auth_router.routes))
    logger.info("Auth router prefix: %s", getattr(auth_router, "prefix", "None"))
    auth_routes = [
        f"{route.path} ({', '.join(route.methods)})" for route in auth_router.routes[:5]
    ]
    logger.info("Auth routes echantillon: %s", auth_routes)
except ImportError as ie:
    logger.error("IMPORT ERROR auth router: %s", ie)
    logger.error("Le module auth.py n'a pas pu etre importe")
    import traceback

    logger.error("Traceback import auth: %s", traceback.format_exc())
    auth_router = None
except AttributeError as ae:
    logger.error("ATTRIBUTE ERROR auth router: %s", ae)
    logger.error("Le module auth.py n'exporte pas 'router'")
    auth_router = None
except Exception as e:
    logger.error("ERREUR GENERALE auth router: %s", e)
    logger.error("Type d'erreur: %s", type(e).__name__)
    import traceback

    logger.error("Traceback complet auth: %s", traceback.format_exc())
    auth_router = None

# NOUVEAU: Users router - GESTION PROFILS
USERS_AVAILABLE = False
try:
    logger.info("Tentative import users router...")
    from .users import router as users_router

    USERS_AVAILABLE = True
    logger.info("Users router importe avec succes!")
    logger.info("Users router a %d routes", len(users_router.routes))
    logger.info("Users router prefix: %s", getattr(users_router, "prefix", "None"))
    users_routes = [
        f"{route.path} ({', '.join(route.methods)})"
        for route in users_router.routes[:3]
    ]
    logger.info("Users routes echantillon: %s", users_routes)
except ImportError as ie:
    logger.warning("IMPORT WARNING users router: %s", ie)
    logger.warning(
        "Le module users.py n'a pas pu etre importe (normal si pas encore cree)"
    )
    users_router = None
    USERS_AVAILABLE = False
except AttributeError as ae:
    logger.error("ATTRIBUTE ERROR users router: %s", ae)
    logger.error("Le module users.py n'exporte pas 'router'")
    users_router = None
    USERS_AVAILABLE = False
except Exception as e:
    logger.error("ERREUR users router: %s", e)
    import traceback

    logger.error("Traceback users: %s", traceback.format_exc())
    users_router = None
    USERS_AVAILABLE = False

# Stats Fast router (endpoints ultra-rapides)
STATS_FAST_AVAILABLE = False
try:
    logger.info("Tentative import stats_fast router...")

    # Test préalable des dépendances
    try:
        import aiohttp

        logger.info("✅ aiohttp disponible (version: %s)", aiohttp.__version__)
    except ImportError as aiohttp_error:
        logger.error("❌ aiohttp MANQUANT: %s", aiohttp_error)

    # Test import auth - CORRECTION: utilisation d'importlib pour test de disponibilité
    try:
        import importlib.util

        auth_spec = importlib.util.find_spec(".auth", package=__name__)
        if auth_spec is not None:
            logger.info("✅ auth module disponible")
        else:
            logger.error("❌ auth module MANQUANT")
    except Exception as auth_error:
        logger.error("❌ erreur test auth module: %s", auth_error)

    # Test import stats_cache - CORRECTION: utilisation d'importlib pour test de disponibilité
    try:
        stats_cache_spec = importlib.util.find_spec(".stats_cache", package=__name__)
        if stats_cache_spec is not None:
            logger.info("✅ stats_cache module disponible")
        else:
            logger.error("❌ stats_cache module MANQUANT")
    except Exception as cache_error:
        logger.error("❌ erreur test stats_cache module: %s", cache_error)

    # Import principal stats_fast
    from .stats_fast import router as stats_fast_router

    STATS_FAST_AVAILABLE = True
    logger.info("✅ Stats Fast router importe avec succes!")
    logger.info("Stats Fast router a %d routes", len(stats_fast_router.routes))
    logger.info(
        "Stats Fast router prefix: %s", getattr(stats_fast_router, "prefix", "None")
    )
    stats_fast_routes = [
        f"{route.path} ({', '.join(route.methods)})"
        for route in stats_fast_router.routes[:3]
    ]
    logger.info("Stats Fast routes echantillon: %s", stats_fast_routes)

except ImportError as ie:
    logger.error("❌ IMPORT ERROR stats_fast router: %s", ie)
    logger.error("Cause probable: Module manquant ou erreur de syntaxe")
    import traceback

    logger.error("Traceback ImportError: %s", traceback.format_exc())
    stats_fast_router = None
    STATS_FAST_AVAILABLE = False

except ModuleNotFoundError as mnf:
    logger.error("❌ MODULE NOT FOUND stats_fast: %s", mnf)
    logger.error("Vérifiez que aiohttp est installé: pip install aiohttp")
    stats_fast_router = None
    STATS_FAST_AVAILABLE = False

except Exception as e:
    logger.error("❌ ERREUR GENERALE stats_fast router: %s", e)
    logger.error("Type d'erreur: %s", type(e).__name__)
    import traceback

    logger.error("Traceback complet: %s", traceback.format_exc())
    stats_fast_router = None
    STATS_FAST_AVAILABLE = False

# Stats Admin router (administration cache)
STATS_ADMIN_AVAILABLE = False
try:
    logger.info("Tentative import stats_admin router...")
    from .stats_admin import router as stats_admin_router

    STATS_ADMIN_AVAILABLE = True
    logger.info("Stats Admin router importe avec succes!")
    logger.info("Stats Admin router a %d routes", len(stats_admin_router.routes))
    logger.info(
        "Stats Admin router prefix: %s", getattr(stats_admin_router, "prefix", "None")
    )
    stats_admin_routes = [
        f"{route.path} ({', '.join(route.methods)})"
        for route in stats_admin_router.routes[:3]
    ]
    logger.info("Stats Admin routes echantillon: %s", stats_admin_routes)
except ImportError as ie:
    logger.warning("IMPORT WARNING stats_admin router: %s", ie)
    logger.warning(
        "Le systeme d'administration cache n'est pas encore deploye (normal)"
    )
    stats_admin_router = None
    STATS_ADMIN_AVAILABLE = False
except Exception as e:
    logger.error("ERREUR stats_admin router: %s", e)
    import traceback

    logger.error("Traceback stats_admin: %s", traceback.format_exc())
    stats_admin_router = None
    STATS_ADMIN_AVAILABLE = False

# Admin router
try:
    from .admin import router as admin_router

    logger.info("Admin router importe avec %d routes", len(admin_router.routes))
except Exception as e:
    logger.error("ERREUR import admin router: %s", e)
    admin_router = None

# Health router
try:
    from .health import router as health_router

    logger.info("Health router importe avec %d routes", len(health_router.routes))
except Exception as e:
    logger.error("ERREUR import health router: %s", e)
    health_router = None

# Invitations router (MAINTENANT AVEC FONCTIONS D'AUTH INTÉGRÉES)
try:
    from .invitations import router as invitations_router

    logger.info(
        "Invitations router importe avec %d routes", len(invitations_router.routes)
    )
    logger.info("Invitations router inclut maintenant les fonctions d'auth invitations")
except Exception as e:
    logger.error("ERREUR import invitations router: %s", e)
    invitations_router = None

# Logging router
try:
    from .logging import router as logging_router

    logger.info("Logging router importe avec %d routes", len(logging_router.routes))
except Exception as e:
    logger.error("ERREUR import logging router: %s", e)
    logging_router = None

# Billing router
try:
    from .billing import router as billing_router

    logger.info("Billing router importe avec %d routes", len(billing_router.routes))
except Exception as e:
    logger.error("ERREUR import billing router: %s", e)
    billing_router = None

# CORRECTION: Billing OpenAI router - DÉSACTIVÉ TEMPORAIREMENT
# Le module utils est manquant, donc on désactive temporairement
billing_openai_router = None
logger.info("Billing OpenAI router désactivé temporairement (module utils manquant)")

# CORRECTION: Expert router - DÉSACTIVÉ (SERVICE EXTERNALISÉ)
# Expert et expert_service ne doivent plus être utilisés selon votre indication
expert_router = None
logger.info("Expert router désactivé (service externalisé vers expert.intelia.com)")

# Conversations router (conditionnel)
try:
    from .conversations import router as conversations_router

    CONVERSATIONS_AVAILABLE = True
    logger.info(
        "Conversations router importe avec %d routes", len(conversations_router.routes)
    )
except ImportError:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None
    logger.warning("Conversations router non disponible (normal si pas encore cree)")
except Exception as e:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None
    logger.error("ERREUR import conversations router: %s", e)

# Creation du router principal
logger.info("Creation du router principal v1...")
router = APIRouter(prefix="/v1")

# Montage des routers avec debug
logger.info("Montage des routers...")

# System
if system_router:
    router.include_router(system_router, tags=["System"])
    logger.info("System router monte")
else:
    logger.error("System router non monte (echec import)")

# Auth - AVEC DEBUG COMPLET
if auth_router:
    try:
        router.include_router(auth_router, tags=["Auth"])
        logger.info("Auth router monte avec succes!")
        logger.info("Auth router maintenant disponible sur /v1/auth/*")
    except Exception as e:
        logger.error("ERREUR montage auth router: %s", e)
        import traceback

        logger.error("Traceback montage auth: %s", traceback.format_exc())
else:
    logger.error("Auth router NON MONTE - import a echoue")

# NOUVEAU: Users router - AVEC DEBUG COMPLET
if USERS_AVAILABLE and users_router:
    try:
        router.include_router(users_router, tags=["Users"])
        logger.info("Users router monte avec succes!")
        logger.info("Users router maintenant disponible sur /v1/users/*")
        logger.info("Gestion profils utilisateur ACTIVE!")
    except Exception as e:
        logger.error("ERREUR montage users router: %s", e)
        import traceback

        logger.error("Traceback montage users: %s", traceback.format_exc())
else:
    if not USERS_AVAILABLE:
        logger.info("Users router non monte - module users non disponible")
    else:
        logger.error("Users router NON MONTE - import a echoue")

# Stats Fast router (endpoints ultra-rapides)
if STATS_FAST_AVAILABLE and stats_fast_router:
    try:
        router.include_router(stats_fast_router, tags=["Stats-Fast"])
        logger.info("Stats Fast router monte avec succes!")
        logger.info("Stats Fast router maintenant disponible sur /v1/stats-fast/*")
        logger.info("Endpoints ultra-rapides actives (<100ms vs 10-30s)")
    except Exception as e:
        logger.error("ERREUR montage stats_fast router: %s", e)
        import traceback

        logger.error("Traceback montage stats_fast: %s", traceback.format_exc())
else:
    if not STATS_FAST_AVAILABLE:
        logger.info("Stats Fast router non monte - modules cache non disponibles")
    else:
        logger.error("Stats Fast router NON MONTE - import a echoue")

# Stats Admin router (administration cache)
if STATS_ADMIN_AVAILABLE and stats_admin_router:
    try:
        router.include_router(
            stats_admin_router, prefix="/stats-admin", tags=["Stats-Admin"]
        )
        logger.info("Stats Admin router monte avec succes!")
        logger.info("Stats Admin router maintenant disponible sur /v1/stats-admin/*")
        logger.info("Administration cache activee (super admin uniquement)")
    except Exception as e:
        logger.error("ERREUR montage stats_admin router: %s", e)
        import traceback

        logger.error("Traceback montage stats_admin: %s", traceback.format_exc())
else:
    if not STATS_ADMIN_AVAILABLE:
        logger.info("Stats Admin router non monte - modules cache non disponibles")
    else:
        logger.error("Stats Admin router NON MONTE - import a echoue")

# Admin
if admin_router:
    router.include_router(admin_router, tags=["Admin"])
    logger.info("Admin router monte")

# Health
if health_router:
    router.include_router(health_router, tags=["Health"])
    logger.info("Health router monte")

# Invitations (MAINTENANT UNIFIÉ AVEC AUTH INVITATIONS)
if invitations_router:
    router.include_router(invitations_router, tags=["Invitations"])
    logger.info("Invitations router monte (inclut auth invitations)")
    logger.info("Invitations router disponible sur /v1/invitations/*")
else:
    logger.error("Invitations router NON MONTE - import a echoue")

# Logging
if logging_router:
    router.include_router(logging_router, tags=["Logging"])
    logger.info("Logging router monte")

# Billing
if billing_router:
    router.include_router(billing_router, tags=["Billing"])
    logger.info("Billing router monte")

# CORRECTION: Billing OpenAI - NON MONTÉ (désactivé)
# billing_openai_router est None, donc ne sera pas monté
logger.info("Billing OpenAI router NON MONTE - temporairement désactivé")

# Conversations (conditionnel)
if CONVERSATIONS_AVAILABLE and conversations_router:
    router.include_router(
        conversations_router, prefix="/conversations", tags=["Conversations"]
    )
    logger.info("Conversations router monte")

# CORRECTION: Expert - NON MONTÉ (désactivé)
# expert_router est None, donc ne sera pas monté
logger.info("Expert router NON MONTE - service externalisé")

# Resume final
total_routes = len(router.routes)
logger.info("Router v1 cree avec %d routes au total", total_routes)

# Debug des routes auth specifiquement
auth_route_count = len([r for r in router.routes if "/auth" in r.path])
logger.info("Routes auth detectees: %d", auth_route_count)

if auth_route_count > 0:
    auth_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})" for r in router.routes if "/auth" in r.path
    ]
    logger.info("Routes auth disponibles: %s", auth_routes_debug[:5])
else:
    logger.error("AUCUNE route auth detectee dans le router final!")

# NOUVEAU: Debug des routes users specifiquement
users_route_count = len([r for r in router.routes if "/users" in r.path])
logger.info("Routes users detectees: %d", users_route_count)

if users_route_count > 0:
    users_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/users" in r.path
    ]
    logger.info("Routes users disponibles: %s", users_routes_debug)
    logger.info("Systeme de gestion profils ACTIF!")
else:
    logger.info("Aucune route users detectee - systeme non encore deploye")

# Debug des routes invitations specifiquement (MAINTENANT UNIFIÉ)
invitations_route_count = len([r for r in router.routes if "/invitations" in r.path])
logger.info("Routes invitations detectees: %d", invitations_route_count)

if invitations_route_count > 0:
    invitations_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/invitations" in r.path
    ]
    logger.info("Routes invitations disponibles: %s", invitations_routes_debug)
    logger.info("Systeme invitations unifie ACTIF (inclut auth invitations)!")
else:
    logger.error("AUCUNE route invitations detectee dans le router final!")

# Debug des routes stats cache specifiquement
stats_route_count = len([r for r in router.routes if "/stats-" in r.path])
logger.info("Routes stats cache detectees: %d", stats_route_count)

if stats_route_count > 0:
    stats_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/stats-" in r.path
    ]
    logger.info("Routes stats cache disponibles: %s", stats_routes_debug)
    logger.info("Systeme de cache statistiques ACTIF!")
else:
    logger.info("Aucune route stats cache detectee - systeme non encore deploye")

# Recapitulatif systeme cache ET users
system_status = {
    "users": USERS_AVAILABLE,
    "stats_fast": STATS_FAST_AVAILABLE,
    "stats_admin": STATS_ADMIN_AVAILABLE,
    "conversations": CONVERSATIONS_AVAILABLE,
    "total_routes": total_routes,
    "users_routes": users_route_count,
    "cache_routes": stats_route_count,
    "invitations_unified": invitations_route_count > 0,
    "billing_openai_disabled": True,
    "expert_disabled": True,
}
logger.info("Status systemes: %s", system_status)

if USERS_AVAILABLE:
    logger.info("SYSTEME DE GESTION PROFILS UTILISATEUR ACTIVE!")
    logger.info(
        "Endpoints disponibles: /v1/users/profile, /v1/users/export, /v1/users/debug"
    )

if STATS_FAST_AVAILABLE or STATS_ADMIN_AVAILABLE:
    logger.info("SYSTEME DE CACHE STATISTIQUES PARTIELLEMENT/TOTALEMENT ACTIVE!")
    logger.info("Performance: Endpoints ultra-rapides disponibles")
    logger.info("Administration: Controle cache disponible")
else:
    logger.info("Systeme de cache non disponible - fonctionnement normal maintenu")

# Log de la refactorisation et corrections
logger.info(
    "REFACTORISATION COMPLETE: auth_invitations supprime, fonctions integrees dans invitations"
)
logger.info(
    "Architecture simplifiee: un seul service pour toutes les fonctions d'invitation"
)
logger.info(
    "CORRECTIONS APPLIQUÉES: billing_openai et expert temporairement désactivés"
)
logger.info("PROCHAINES ÉTAPES: Créer module utils pour billing_openai si nécessaire")

__all__ = ["router"]
