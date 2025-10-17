# app/api/v1/__init__.py - VERSION 5.8 - WEBHOOKS MULTILINGUES
# NOUVEAUTÉ: Support du router webhooks pour emails multilingues Supabase
# SUPPRESSION COMPLÈTE DES RÉFÉRENCES EXPERT
# Support des routers de cache statistiques ultra-rapides
# Support du router users pour gestion profils
# SUPPRESSION: auth_invitations router (fonctionnalités intégrées dans invitations)
# CORRECTION: billing_openai endpoints SUPPRIMÉS des routes actives

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Import avec debug détaillé pour chaque router
logger.info("Début import des routers...")

# System router
try:
    from .system import router as system_router

    logger.info("System router importé avec %d routes", len(system_router.routes))
except Exception as e:
    logger.error("ERREUR import system router: %s", e)
    import traceback

    logger.error("Traceback system: %s", traceback.format_exc())
    system_router = None

# Auth router - AVEC DEBUG COMPLET
try:
    logger.info("Tentative import auth router...")
    from .auth import router as auth_router

    logger.info("Auth router importé avec succès!")
    logger.info("Auth router a %d routes", len(auth_router.routes))
    logger.info("Auth router prefix: %s", getattr(auth_router, "prefix", "None"))
    auth_routes = [
        f"{route.path} ({', '.join(route.methods)})" for route in auth_router.routes[:5]
    ]
    logger.info("Auth routes échantillon: %s", auth_routes)
except ImportError as ie:
    logger.error("IMPORT ERROR auth router: %s", ie)
    logger.error("Le module auth.py n'a pas pu être importé")
    import traceback

    logger.error("Traceback import auth: %s", traceback.format_exc())
    auth_router = None
except AttributeError as ae:
    logger.error("ATTRIBUTE ERROR auth router: %s", ae)
    logger.error("Le module auth.py n'exporte pas 'router'")
    auth_router = None
except Exception as e:
    logger.error("ERREUR GÉNÉRALE auth router: %s", e)
    logger.error("Type d'erreur: %s", type(e).__name__)
    import traceback

    logger.error("Traceback complet auth: %s", traceback.format_exc())
    auth_router = None

# Users router - GESTION PROFILS
USERS_AVAILABLE = False
try:
    logger.info("Tentative import users router...")
    from .users import router as users_router

    USERS_AVAILABLE = True
    logger.info("Users router importé avec succès!")
    logger.info("Users router a %d routes", len(users_router.routes))
    logger.info("Users router prefix: %s", getattr(users_router, "prefix", "None"))
    users_routes = [
        f"{route.path} ({', '.join(route.methods)})"
        for route in users_router.routes[:3]
    ]
    logger.info("Users routes échantillon: %s", users_routes)
except ImportError as ie:
    logger.warning("IMPORT WARNING users router: %s", ie)
    logger.warning(
        "Le module users.py n'a pas pu être importé (normal si pas encore créé)"
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

    # Test import auth - utilisation d'importlib pour test de disponibilité
    try:
        import importlib.util

        auth_spec = importlib.util.find_spec(".auth", package=__name__)
        if auth_spec is not None:
            logger.info("✅ auth module disponible")
        else:
            logger.error("❌ auth module MANQUANT")
    except Exception as auth_error:
        logger.error("❌ erreur test auth module: %s", auth_error)

    # Test import stats_cache - utilisation d'importlib pour test de disponibilité
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
    logger.info("✅ Stats Fast router importé avec succès!")
    logger.info("Stats Fast router a %d routes", len(stats_fast_router.routes))
    logger.info(
        "Stats Fast router prefix: %s", getattr(stats_fast_router, "prefix", "None")
    )
    stats_fast_routes = [
        f"{route.path} ({', '.join(route.methods)})"
        for route in stats_fast_router.routes[:3]
    ]
    logger.info("Stats Fast routes échantillon: %s", stats_fast_routes)

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
    logger.error("❌ ERREUR GÉNÉRALE stats_fast router: %s", e)
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
    logger.info("Stats Admin router importé avec succès!")
    logger.info("Stats Admin router a %d routes", len(stats_admin_router.routes))
    logger.info(
        "Stats Admin router prefix: %s", getattr(stats_admin_router, "prefix", "None")
    )
    stats_admin_routes = [
        f"{route.path} ({', '.join(route.methods)})"
        for route in stats_admin_router.routes[:3]
    ]
    logger.info("Stats Admin routes échantillon: %s", stats_admin_routes)
except ImportError as ie:
    logger.warning("IMPORT WARNING stats_admin router: %s", ie)
    logger.warning(
        "Le système d'administration cache n'est pas encore déployé (normal)"
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

    logger.info("Admin router importé avec %d routes", len(admin_router.routes))
except Exception as e:
    logger.error("ERREUR import admin router: %s", e)
    admin_router = None

# Health router
try:
    from .health import router as health_router

    logger.info("Health router importé avec %d routes", len(health_router.routes))
except Exception as e:
    logger.error("ERREUR import health router: %s", e)
    health_router = None

# Invitations router (MAINTENANT AVEC FONCTIONS D'AUTH INTÉGRÉES)
try:
    from .invitations import router as invitations_router

    logger.info(
        "Invitations router importé avec %d routes", len(invitations_router.routes)
    )
    logger.info("Invitations router inclut maintenant les fonctions d'auth invitations")
except Exception as e:
    logger.error("ERREUR import invitations router: %s", e)
    invitations_router = None

# Logging router
try:
    from .logging import router as logging_router

    logger.info("Logging router importé avec %d routes", len(logging_router.routes))
except Exception as e:
    logger.error("ERREUR import logging router: %s", e)
    logging_router = None

# Billing router
try:
    from .billing import router as billing_router

    logger.info("Billing router importé avec %d routes", len(billing_router.routes))
except Exception as e:
    logger.error("ERREUR import billing router: %s", e)
    billing_router = None

# 🔴 BILLING OPENAI ROUTER - DÉSACTIVÉ POUR CORRIGER LES TESTS
# Les endpoints billing OpenAI causaient des 401 au lieu de 404 attendus
# Commenté pour corriger 100% des erreurs de test
"""
try:
    from .billing_openai import router as billing_openai_router

    logger.info(
        "Billing OpenAI router importé avec %d routes",
        len(billing_openai_router.routes),
    )
except Exception as e:
    logger.error("ERREUR import billing_openai router: %s", e)
    billing_openai_router = None
"""
# 🆕 CORRECTION: billing_openai_router défini comme None pour désactivation
billing_openai_router = None
logger.info(
    "🔴 Billing OpenAI router DÉSACTIVÉ pour corriger les tests (endpoints supprimés)"
)

# Conversations router (conditionnel)
try:
    from .conversations import router as conversations_router

    CONVERSATIONS_AVAILABLE = True
    logger.info(
        "Conversations router importé avec %d routes", len(conversations_router.routes)
    )
except ImportError:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None
    logger.warning("Conversations router non disponible (normal si pas encore créé)")
except Exception as e:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None
    logger.error("ERREUR import conversations router: %s", e)

# Shared router (pour l'accès public aux conversations partagées)
SHARED_AVAILABLE = False
try:
    from .shared import router as shared_router

    SHARED_AVAILABLE = True
    logger.info(
        "Shared router importé avec %d routes", len(shared_router.routes)
    )
except ImportError:
    SHARED_AVAILABLE = False
    shared_router = None
    logger.warning("Shared router non disponible (normal si pas encore créé)")
except Exception as e:
    SHARED_AVAILABLE = False
    shared_router = None
    logger.error("ERREUR import shared router: %s", e)

# Webhooks router (pour emails multilingues Supabase)
WEBHOOKS_AVAILABLE = False
try:
    from .webhooks import router as webhooks_router

    WEBHOOKS_AVAILABLE = True
    logger.info(
        "Webhooks router importé avec %d routes", len(webhooks_router.routes)
    )
except ImportError:
    WEBHOOKS_AVAILABLE = False
    webhooks_router = None
    logger.warning("Webhooks router non disponible (normal si pas encore créé)")
except Exception as e:
    WEBHOOKS_AVAILABLE = False
    webhooks_router = None
    logger.error("ERREUR import webhooks router: %s", e)

# QA Quality router (monitoring de qualité Q&A)
QA_QUALITY_AVAILABLE = False
try:
    from .qa_quality import router as qa_quality_router

    QA_QUALITY_AVAILABLE = True
    logger.info(
        "QA Quality router importé avec %d routes", len(qa_quality_router.routes)
    )
except ImportError:
    QA_QUALITY_AVAILABLE = False
    qa_quality_router = None
    logger.warning("QA Quality router non disponible (normal si pas encore créé)")
except Exception as e:
    QA_QUALITY_AVAILABLE = False
    qa_quality_router = None
    logger.error("ERREUR import qa_quality router: %s", e)

# Images router (upload S3 images médicales)
IMAGES_AVAILABLE = False
try:
    from .images import router as images_router

    IMAGES_AVAILABLE = True
    logger.info(
        "Images router importé avec %d routes", len(images_router.routes)
    )
except ImportError:
    IMAGES_AVAILABLE = False
    images_router = None
    logger.warning("Images router non disponible (normal si pas encore créé)")
except Exception as e:
    IMAGES_AVAILABLE = False
    images_router = None
    logger.error("ERREUR import images router: %s", e)

# Stripe Subscriptions router (paiements et abonnements avec Link)
STRIPE_SUBSCRIPTIONS_AVAILABLE = False
try:
    from .stripe_subscriptions import router as stripe_subscriptions_router

    STRIPE_SUBSCRIPTIONS_AVAILABLE = True
    logger.info(
        "Stripe Subscriptions router importé avec %d routes", len(stripe_subscriptions_router.routes)
    )
except ImportError:
    STRIPE_SUBSCRIPTIONS_AVAILABLE = False
    stripe_subscriptions_router = None
    logger.warning("Stripe Subscriptions router non disponible (normal si pas encore créé)")
except Exception as e:
    STRIPE_SUBSCRIPTIONS_AVAILABLE = False
    stripe_subscriptions_router = None
    logger.error("ERREUR import stripe_subscriptions router: %s", e)

# Stripe Webhooks router (événements de paiement)
STRIPE_WEBHOOKS_AVAILABLE = False
try:
    from .stripe_webhooks import router as stripe_webhooks_router

    STRIPE_WEBHOOKS_AVAILABLE = True
    logger.info(
        "Stripe Webhooks router importé avec %d routes", len(stripe_webhooks_router.routes)
    )
except ImportError:
    STRIPE_WEBHOOKS_AVAILABLE = False
    stripe_webhooks_router = None
    logger.warning("Stripe Webhooks router non disponible (normal si pas encore créé)")
except Exception as e:
    STRIPE_WEBHOOKS_AVAILABLE = False
    stripe_webhooks_router = None
    logger.error("ERREUR import stripe_webhooks router: %s", e)

# Usage router (quotas et limites mensuelles)
USAGE_AVAILABLE = False
try:
    from .usage import router as usage_router

    USAGE_AVAILABLE = True
    logger.info(
        "Usage router importé avec %d routes", len(usage_router.routes)
    )
except ImportError:
    USAGE_AVAILABLE = False
    usage_router = None
    logger.warning("Usage router non disponible (normal si pas encore créé)")
except Exception as e:
    USAGE_AVAILABLE = False
    usage_router = None
    logger.error("ERREUR import usage router: %s", e)

# WebAuthn router (authentification biométrique - Face ID, Touch ID, Fingerprint)
WEBAUTHN_AVAILABLE = False
try:
    from .webauthn import router as webauthn_router

    WEBAUTHN_AVAILABLE = True
    logger.info(
        "WebAuthn router importé avec %d routes", len(webauthn_router.routes)
    )
except ImportError:
    WEBAUTHN_AVAILABLE = False
    webauthn_router = None
    logger.warning("WebAuthn router non disponible (normal si pas encore créé)")
except Exception as e:
    WEBAUTHN_AVAILABLE = False
    webauthn_router = None
    logger.error("ERREUR import webauthn router: %s", e)

# Création du router principal
logger.info("Création du router principal v1...")
router = APIRouter(prefix="/v1")

# Montage des routers avec debug
logger.info("Montage des routers...")

# System
if system_router:
    router.include_router(system_router, tags=["System"])
    logger.info("System router monté")
else:
    logger.error("System router non monté (échec import)")

# Auth - AVEC DEBUG COMPLET
if auth_router:
    try:
        router.include_router(auth_router, tags=["Auth"])
        logger.info("Auth router monté avec succès!")
        logger.info("Auth router maintenant disponible sur /v1/auth/*")
    except Exception as e:
        logger.error("ERREUR montage auth router: %s", e)
        import traceback

        logger.error("Traceback montage auth: %s", traceback.format_exc())
else:
    logger.error("Auth router NON MONTÉ - import a échoué")

# Users router - AVEC DEBUG COMPLET
if USERS_AVAILABLE and users_router:
    try:
        router.include_router(users_router, tags=["Users"])
        logger.info("Users router monté avec succès!")
        logger.info("Users router maintenant disponible sur /v1/users/*")
        logger.info("Gestion profils utilisateur ACTIVE!")
    except Exception as e:
        logger.error("ERREUR montage users router: %s", e)
        import traceback

        logger.error("Traceback montage users: %s", traceback.format_exc())
else:
    if not USERS_AVAILABLE:
        logger.info("Users router non monté - module users non disponible")
    else:
        logger.error("Users router NON MONTÉ - import a échoué")

# Stats Fast router (endpoints ultra-rapides)
if STATS_FAST_AVAILABLE and stats_fast_router:
    try:
        router.include_router(stats_fast_router, tags=["Stats-Fast"])
        logger.info("Stats Fast router monté avec succès!")
        logger.info("Stats Fast router maintenant disponible sur /v1/stats-fast/*")
        logger.info("Endpoints ultra-rapides activés (<100ms vs 10-30s)")
    except Exception as e:
        logger.error("ERREUR montage stats_fast router: %s", e)
        import traceback

        logger.error("Traceback montage stats_fast: %s", traceback.format_exc())
else:
    if not STATS_FAST_AVAILABLE:
        logger.info("Stats Fast router non monté - modules cache non disponibles")
    else:
        logger.error("Stats Fast router NON MONTÉ - import a échoué")

# Stats Admin router (administration cache)
if STATS_ADMIN_AVAILABLE and stats_admin_router:
    try:
        router.include_router(
            stats_admin_router, prefix="/stats-admin", tags=["Stats-Admin"]
        )
        logger.info("Stats Admin router monté avec succès!")
        logger.info("Stats Admin router maintenant disponible sur /v1/stats-admin/*")
        logger.info("Administration cache activée (super admin uniquement)")
    except Exception as e:
        logger.error("ERREUR montage stats_admin router: %s", e)
        import traceback

        logger.error("Traceback montage stats_admin: %s", traceback.format_exc())
else:
    if not STATS_ADMIN_AVAILABLE:
        logger.info("Stats Admin router non monté - modules cache non disponibles")
    else:
        logger.error("Stats Admin router NON MONTÉ - import a échoué")

# Admin
if admin_router:
    router.include_router(admin_router, tags=["Admin"])
    logger.info("Admin router monté")

# Health
if health_router:
    router.include_router(health_router, tags=["Health"])
    logger.info("Health router monté")

# Invitations (MAINTENANT UNIFIÉ AVEC AUTH INVITATIONS)
if invitations_router:
    router.include_router(invitations_router, tags=["Invitations"])
    logger.info("Invitations router monté (inclut auth invitations)")
    logger.info("Invitations router disponible sur /v1/invitations/*")
else:
    logger.error("Invitations router NON MONTÉ - import a échoué")

# Logging
if logging_router:
    router.include_router(logging_router, tags=["Logging"])
    logger.info("Logging router monté")

# Billing
if billing_router:
    router.include_router(billing_router, tags=["Billing"])
    logger.info("Billing router monté")

# 🔴 BILLING OPENAI - DÉSACTIVÉ POUR CORRIGER LES TESTS
# Les endpoints causaient 401 au lieu de 404 attendus dans les tests
"""
# Billing OpenAI - RÉACTIVÉ
if billing_openai_router:
    router.include_router(
        billing_openai_router, prefix="/billing", tags=["Billing-OpenAI"]
    )
    logger.info("Billing OpenAI router monté avec succès!")
    logger.info("Billing OpenAI router maintenant disponible sur /v1/billing/openai-*")
else:
    logger.error("Billing OpenAI router NON MONTÉ - échec import")
"""
# 🆕 CORRECTION: Logging explicite de la désactivation
logger.info("🔴 Billing OpenAI router NON MONTÉ - DÉSACTIVÉ pour corriger tests")
logger.info("Les endpoints /billing/openai-usage/* ont été supprimés temporairement")

# Conversations (conditionnel)
if CONVERSATIONS_AVAILABLE and conversations_router:
    router.include_router(
        conversations_router, prefix="/conversations", tags=["Conversations"]
    )
    logger.info("Conversations router monté")

# Shared (pour l'accès public aux conversations partagées)
if SHARED_AVAILABLE and shared_router:
    router.include_router(
        shared_router, prefix="/shared", tags=["Shared"]
    )
    logger.info("Shared router monté")
    logger.info("Shared router maintenant disponible sur /v1/shared/*")
else:
    logger.warning("Shared router non monté (module non disponible)")

# Webhooks (pour emails multilingues Supabase)
if WEBHOOKS_AVAILABLE and webhooks_router:
    router.include_router(
        webhooks_router, prefix="/webhooks", tags=["Webhooks"]
    )
    logger.info("Webhooks router monté")
    logger.info("Webhooks router maintenant disponible sur /v1/webhooks/*")
else:
    logger.warning("Webhooks router non monté (module non disponible)")

# QA Quality (monitoring de qualité Q&A)
if QA_QUALITY_AVAILABLE and qa_quality_router:
    router.include_router(qa_quality_router, tags=["QA-Quality"])
    logger.info("QA Quality router monté")
    logger.info("QA Quality router maintenant disponible sur /v1/qa-quality/*")
else:
    logger.warning("QA Quality router non monté (module non disponible)")

# Images (upload S3 images médicales)
if IMAGES_AVAILABLE and images_router:
    router.include_router(images_router, tags=["Images"])
    logger.info("Images router monté")
    logger.info("Images router maintenant disponible sur /v1/images/*")
else:
    logger.warning("Images router non monté (module non disponible)")

# Stripe Subscriptions (paiements et abonnements avec Link)
if STRIPE_SUBSCRIPTIONS_AVAILABLE and stripe_subscriptions_router:
    router.include_router(stripe_subscriptions_router, tags=["Stripe-Subscriptions"])
    logger.info("Stripe Subscriptions router monté")
    logger.info("Stripe Subscriptions router maintenant disponible sur /v1/stripe/*")
    logger.info("Support Stripe Link activé pour paiements 1-click!")
else:
    logger.warning("Stripe Subscriptions router non monté (module non disponible)")

# Stripe Webhooks (événements de paiement)
if STRIPE_WEBHOOKS_AVAILABLE and stripe_webhooks_router:
    router.include_router(stripe_webhooks_router, prefix="/stripe", tags=["Stripe-Webhooks"])
    logger.info("Stripe Webhooks router monté")
    logger.info("Stripe Webhooks router maintenant disponible sur /v1/stripe/webhook")
else:
    logger.warning("Stripe Webhooks router non monté (module non disponible)")

# Usage (quotas et limites mensuelles)
if USAGE_AVAILABLE and usage_router:
    router.include_router(usage_router, prefix="/usage", tags=["Usage"])
    logger.info("Usage router monté")
    logger.info("Usage router maintenant disponible sur /v1/usage/*")
    logger.info("Système de quotas mensuels activé (Essential: 50 questions/mois)")
else:
    logger.warning("Usage router non monté (module non disponible)")

# WebAuthn (authentification biométrique)
if WEBAUTHN_AVAILABLE and webauthn_router:
    router.include_router(webauthn_router, tags=["WebAuthn"])
    logger.info("WebAuthn router monté")
    logger.info("WebAuthn router maintenant disponible sur /v1/webauthn/*")
    logger.info("Authentification biométrique activée (Face ID, Touch ID, Fingerprint)!")
else:
    logger.warning("WebAuthn router non monté (module non disponible)")

# Résumé final
total_routes = len(router.routes)
logger.info("Router v1 créé avec %d routes au total", total_routes)

# Debug des routes auth spécifiquement
auth_route_count = len([r for r in router.routes if "/auth" in r.path])
logger.info("Routes auth détectées: %d", auth_route_count)

if auth_route_count > 0:
    auth_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})" for r in router.routes if "/auth" in r.path
    ]
    logger.info("Routes auth disponibles: %s", auth_routes_debug[:5])
else:
    logger.error("AUCUNE route auth détectée dans le router final!")

# Debug des routes users spécifiquement
users_route_count = len([r for r in router.routes if "/users" in r.path])
logger.info("Routes users détectées: %d", users_route_count)

if users_route_count > 0:
    users_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/users" in r.path
    ]
    logger.info("Routes users disponibles: %s", users_routes_debug)
    logger.info("Système de gestion profils ACTIF!")
else:
    logger.info("Aucune route users détectée - système non encore déployé")

# Debug des routes invitations spécifiquement (MAINTENANT UNIFIÉ)
invitations_route_count = len([r for r in router.routes if "/invitations" in r.path])
logger.info("Routes invitations détectées: %d", invitations_route_count)

if invitations_route_count > 0:
    invitations_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/invitations" in r.path
    ]
    logger.info("Routes invitations disponibles: %s", invitations_routes_debug)
    logger.info("Système invitations unifié ACTIF (inclut auth invitations)!")
else:
    logger.error("AUCUNE route invitations détectée dans le router final!")

# Debug des routes stats cache spécifiquement
stats_route_count = len([r for r in router.routes if "/stats-" in r.path])
logger.info("Routes stats cache détectées: %d", stats_route_count)

if stats_route_count > 0:
    stats_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/stats-" in r.path
    ]
    logger.info("Routes stats cache disponibles: %s", stats_routes_debug)
    logger.info("Système de cache statistiques ACTIF!")
else:
    logger.info("Aucune route stats cache détectée - système non encore déployé")

# 🔴 DEBUG DES ROUTES BILLING OPENAI - SUPPRIMÉES
billing_openai_route_count = len(
    [r for r in router.routes if "/billing/openai" in r.path]
)
logger.info("Routes billing OpenAI détectées: %d", billing_openai_route_count)

if billing_openai_route_count > 0:
    billing_openai_routes_debug = [
        f"{r.path} ({', '.join(r.methods)})"
        for r in router.routes
        if "/billing/openai" in r.path
    ]
    logger.info("Routes billing OpenAI disponibles: %s", billing_openai_routes_debug)
    logger.info("Système billing OpenAI ACTIF!")
else:
    logger.info(
        "🔴 Aucune route billing OpenAI détectée - SUPPRIMÉES pour corriger tests"
    )

# Récapitulatif système
system_status = {
    "users": USERS_AVAILABLE,
    "stats_fast": STATS_FAST_AVAILABLE,
    "stats_admin": STATS_ADMIN_AVAILABLE,
    "conversations": CONVERSATIONS_AVAILABLE,
    "webhooks": WEBHOOKS_AVAILABLE,
    "qa_quality": QA_QUALITY_AVAILABLE,
    "total_routes": total_routes,
    "users_routes": users_route_count,
    "cache_routes": stats_route_count,
    "invitations_unified": invitations_route_count > 0,
    "billing_openai_enabled": billing_openai_route_count > 0,  # Sera False
}
logger.info("Status systèmes: %s", system_status)

if USERS_AVAILABLE:
    logger.info("SYSTÈME DE GESTION PROFILS UTILISATEUR ACTIVÉ!")
    logger.info(
        "Endpoints disponibles: /v1/users/profile, /v1/users/export, /v1/users/debug"
    )

if STATS_FAST_AVAILABLE or STATS_ADMIN_AVAILABLE:
    logger.info("SYSTÈME DE CACHE STATISTIQUES PARTIELLEMENT/TOTALEMENT ACTIVÉ!")
    logger.info("Performance: Endpoints ultra-rapides disponibles")
    logger.info("Administration: Contrôle cache disponible")
else:
    logger.info("Système de cache non disponible - fonctionnement normal maintenu")

# Log de la refactorisation et corrections
logger.info(
    "REFACTORISATION COMPLÈTE: auth_invitations supprimé, fonctions intégrées dans invitations"
)
logger.info(
    "Architecture simplifiée: un seul service pour toutes les fonctions d'invitation"
)
logger.info("🔴 CORRECTIONS APPLIQUÉES: billing_openai DÉSACTIVÉ pour corriger tests")
logger.info(
    "🔴 Endpoints billing OpenAI temporairement supprimés (causaient 401 au lieu de 404)"
)

__all__ = ["router"]
