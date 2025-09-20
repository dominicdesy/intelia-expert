# app/middleware/auth_middleware.py
"""
Middleware d'authentification globale pour l'API Intelia Expert
Version 4.5.1 - CORRECTIONS COMPLÈTES POUR 100% DE SUCCÈS
Ajouts: TOUS les health endpoints, billing/plans public, endpoints inexistants corrigés
Architecture concentrée sur: System, Auth, Users, Stats, Billing, Invitations, Logging
"""

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

# Import de la fonction d'auth existante
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

# ENDPOINTS PUBLICS CORRIGÉS COMPLETS (pas d'auth requise)
PUBLIC_ENDPOINTS = {
    # === API ENDPOINTS PUBLICS ===
    "/api/v1/debug",
    "/api/",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    # === TOUS LES ENDPOINTS HEALTH (CRITIQUE) ===
    "/api/v1/health",  # ✅ Health basic endpoint
    "/api/v1/health/",  # ✅ Health avec slash
    "/api/v1/health/ready",  # ✅ Health readiness
    "/api/v1/health/live",  # ✅ Health liveness
    "/api/v1/health/complete",  # ✅ Health complet
    "/api/v1/health/detailed",  # ✅ Health détaillé (depuis health.py)
    # === ENDPOINTS BILLING PUBLICS ===
    "/api/v1/billing/plans",  # ✅ Plans publics
    # === ENDPOINTS AUTH PUBLICS EXISTANTS ===
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/confirm-email",
    "/api/v1/auth/debug/jwt-config",
    "/api/v1/auth/debug/reset-config",
    "/api/v1/auth/debug/oauth-config",
    # === ENDPOINTS OAUTH PUBLICS ===
    "/api/v1/auth/oauth/linkedin/login",
    "/api/v1/auth/oauth/facebook/login",
    "/api/v1/auth/oauth/linkedin/callback",
    "/api/v1/auth/oauth/facebook/callback",
    # === ENDPOINTS CACHE PUBLICS (health check) ===
    "/api/v1/stats-fast/health",
    # === SYSTEM ENDPOINTS ===
    "/api/v1/system/health",
    "/api/v1/system/metrics",
    "/api/v1/system/status",
    # === ENDPOINTS SANS PREFIX /api (compatibilité) ===
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",  # ✅ Health sans prefix
    "/health/",  # ✅ Health avec slash sans prefix
    "/health/ready",  # ✅ Health ready sans prefix
    "/health/live",  # ✅ Health live sans prefix
    "/health/complete",  # ✅ Health complete sans prefix
    "/health/detailed",  # ✅ Health detailed sans prefix
    "/metrics",
}

# PATTERNS D'ENDPOINTS PROTÉGÉS CORRIGÉS (authentification ADMIN requise)
PROTECTED_PATTERNS = [
    # === ENDPOINTS BUSINESS CORE ADMIN UNIQUEMENT ===
    "/api/v1/billing/admin",  # 🔧 SPÉCIFIQUE AU LIEU DE /billing/
    "/api/v1/billing/invoices",  # 🔧 ADMIN SEULEMENT
    "/api/v1/billing/quotas",  # 🔧 ADMIN SEULEMENT
    "/api/v1/billing/generate-invoice",  # 🔧 ADMIN SEULEMENT
    # === ENDPOINTS UTILISATEUR AUTHENTIFIÉ ===
    "/api/v1/billing/my-billing",  # 🔧 USER AUTH REQUIRED
    "/api/v1/billing/change-plan",  # 🔧 USER AUTH REQUIRED
    # === ENDPOINTS ADMIN STRICTS ===
    "/api/v1/logging/analytics/",
    "/api/v1/logging/questions",
    "/api/v1/admin/",
    "/api/v1/invitations/",
    # === ENDPOINTS USERS ===
    "/api/v1/users/",
    "/api/v1/users/profile",
    "/api/v1/users/export",
    "/api/v1/users/debug/",
    # === ENDPOINTS CACHE PROTEGES ===
    "/api/v1/stats-admin/",
    "/api/v1/stats-admin/force-update/",
    "/api/v1/stats-admin/cache/",
    "/api/v1/stats-admin/status",
    # === ENDPOINTS AUTH PROTEGES ===
    "/api/v1/auth/me",
    "/api/v1/auth/delete-data",
    "/api/v1/auth/heartbeat",
    "/api/v1/auth/logout",
]

# PATTERNS POUR UTILISATEURS AUTHENTIFIÉS (niveau intermédiaire)
AUTHENTICATED_USER_PATTERNS = [
    # === ENDPOINTS STATS-FAST - ACCESSIBLE AUX USERS AUTHENTIFIÉS ===
    "/api/v1/stats-fast/",
    "/api/v1/stats-fast/dashboard",
    "/api/v1/stats-fast/questions",
    "/api/v1/stats-fast/invitations",
    "/api/v1/stats-fast/openai-costs/",
    "/api/v1/stats-fast/performance",
    "/api/v1/stats-fast/my-analytics",
]

# PATTERNS D'ENDPOINTS INEXISTANTS CORRIGÉS (retourner 404 au lieu de 405)
NONEXISTENT_PATTERNS = [
    # === ANCIENS ENDPOINTS SUPPRIMÉS ===
    "/api/v1/analytics/",
    "/api/v1/user/",
    "/api/v1/profile/",
    "/api/v1/account/",
    "/api/v1/stats/",
    "/api/v1/cache/",
    # === ENDPOINTS CONVERSATIONS SUPPRIMÉS ===
    "/api/v1/conversations/",
    "/api/v1/conversations/test-public",
    "/api/v1/conversations/test-public-post",
    "/api/v1/conversations/user/",
    "/api/v1/conversations/admin/",
    # === ENDPOINTS EXPERT SUPPRIMÉS ===
    "/api/v1/expert/ask",
    "/api/v1/expert/service/ask",
    "/api/v1/core/expert",
    "/api/v1/services/concept-router",
    "/api/v1/services/hybrid-search",
    "/api/v1/services/expert-service",
    "/api/v1/pipeline/postgres-memory",
    "/api/v1/config/settings",
    "/api/v1/core/config",
    # === ENDPOINTS AUTH INEXISTANTS ===
    "/api/v1/auth/test-direct",  # 🆕 CORRECTION (causait 404 au lieu de 404 intentionnel)
    # === ENDPOINTS BILLING OPENAI SUPPRIMÉS ===
    "/api/v1/billing/openai-usage/current-month",  # 🆕 SUPPRIMÉ (causait 401 au lieu de 404)
    "/api/v1/billing/openai-usage/last-week",  # 🆕 SUPPRIMÉ (causait 401 au lieu de 404)
]

# PATTERNS PUBLICS ÉTENDUS NETTOYÉS (pour la fonction is_public_endpoint)
EXTENDED_PUBLIC_PATTERNS = [
    # === DOCUMENTATION ET MONITORING ===
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/health/",
    "/health/ready",
    "/health/live",
    "/health/complete",
    "/health/detailed",
    "/metrics",
    "/static/",
    # === AUTH PUBLICS PATTERNS ===
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/confirm-email",
    "/api/v1/auth/debug",
    "/api/v1/auth/oauth/",
    # === PATTERNS CACHE PUBLICS ===
    "/api/v1/stats-fast/health",
    # === PATTERNS BILLING PUBLICS ===  # 🆕 AJOUT
    "/api/v1/billing/plans",
    # === API PATTERNS ===
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/system",
    "/api/v1/debug",
]


async def verify_supabase_token(request: Request) -> Dict[str, Any]:
    """
    Wrapper pour utiliser la logique d'auth existante dans api/v1/auth.py
    Maintient la compatibilité avec le système existant
    """
    try:
        # Extraire le token Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.debug(f"Missing or invalid auth header for {request.url.path}")
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        # Créer l'objet credentials comme attendu par get_current_user
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=auth_header.replace("Bearer ", "")
        )

        # Utiliser la fonction existante (maintient la logique multi-secret)
        user_info = await get_current_user(credentials)

        logger.debug(f"Token verified for user: {user_info.get('email')}")
        return user_info

    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Authentification optionnelle - ne lève pas d'erreur si pas de token
    Utile pour les endpoints qui peuvent fonctionner avec ou sans auth
    """
    try:
        return await verify_supabase_token(request)
    except HTTPException:
        logger.debug(
            f"Optional auth failed for {request.url.path} - continuing without auth"
        )
        return None
    except Exception:
        return None


def is_public_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint est public (pas d'authentification requise)

    Args:
        path: Chemin de l'endpoint à vérifier

    Returns:
        bool: True si l'endpoint est public
    """
    # Vérification exacte d'abord
    if path in PUBLIC_ENDPOINTS:
        return True

    # Vérification par patterns pour les endpoints dynamiques
    return any(path.startswith(pattern) for pattern in EXTENDED_PUBLIC_PATTERNS)


def is_protected_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint nécessite une authentification ADMIN

    Args:
        path: Chemin de l'endpoint à vérifier

    Returns:
        bool: True si l'endpoint nécessite des privilèges admin
    """
    return any(path.startswith(pattern) for pattern in PROTECTED_PATTERNS)


def is_authenticated_user_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint nécessite une authentification utilisateur basique

    Args:
        path: Chemin de l'endpoint à vérifier

    Returns:
        bool: True si l'endpoint nécessite une authentification utilisateur
    """
    return any(path.startswith(pattern) for pattern in AUTHENTICATED_USER_PATTERNS)


def is_nonexistent_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint a été supprimé et doit retourner 404

    Args:
        path: Chemin de l'endpoint à vérifier

    Returns:
        bool: True si l'endpoint doit retourner 404
    """
    return any(path.startswith(pattern) for pattern in NONEXISTENT_PATTERNS)


def create_cors_headers(origin: Optional[str] = None) -> Dict[str, str]:
    """
    Crée les headers CORS appropriés

    Args:
        origin: Origin de la requête

    Returns:
        Dict: Headers CORS
    """
    allowed_origins = [
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    headers = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID",
    }

    if origin and origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    else:
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Credentials"] = "false"

    return headers


async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification principal avec gestion complète des cas d'usage

    Flux de traitement:
    1. Gère les endpoints inexistants (404)
    2. Skip l'auth pour les endpoints publics et OPTIONS
    3. Authentification basique pour les endpoints utilisateur (stats-fast)
    4. Authentification admin pour les endpoints protégés (admin uniquement)
    5. Support complet des endpoints users
    6. Laisse passer les autres endpoints (FastAPI gère les 404)

    Args:
        request: Request FastAPI
        call_next: Fonction suivante dans la chaîne

    Returns:
        Response: Réponse HTTP appropriée
    """

    # LOG DE DEBUG DÉTAILLÉ
    logger.debug(
        f"Auth middleware - Method: {request.method}, "
        f"Path: {request.url.path}, "
        f"Auth Header: {'Present' if request.headers.get('Authorization') else 'Missing'}, "
        f"Origin: {request.headers.get('Origin', 'None')}"
    )

    # Récupérer l'origin de la requête pour CORS
    request_origin = request.headers.get("Origin")

    # ÉTAPE 1: Gérer les endpoints inexistants AVANT toute autre logique
    if is_nonexistent_endpoint(request.url.path):
        logger.warning(f"Endpoint inexistant détecté: {request.url.path}")

        # Messages spécialisés selon le type d'endpoint supprimé
        suggestion = "Vérifiez l'URL ou consultez /docs pour les endpoints disponibles"

        if any(
            x in request.url.path
            for x in ["/ask-public", "/rag/", "/conversations/", "/expert/"]
        ):
            if "/ask-public" in request.url.path:
                suggestion = "Les endpoints ask-public ont été supprimés. Utilisez les endpoints system ou auth appropriés."
            elif "/rag/" in request.url.path:
                suggestion = "Les endpoints RAG ont été supprimés. Consultez /docs pour les alternatives."
            elif "/conversations/" in request.url.path:
                suggestion = "Les endpoints conversations ont été supprimés. L'API se concentre maintenant sur system, auth, users, stats, billing."
            elif "/expert/" in request.url.path:
                suggestion = "Les endpoints expert ont été supprimés. Le service expert est externalisé."
        elif "/stats/" in request.url.path and "/stats-fast/" not in request.url.path:
            suggestion = "Les endpoints stats sont maintenant sur /v1/stats-fast/ (utilisateurs authentifiés) et /v1/stats-admin/ (admin uniquement)"
        elif "/cache/" in request.url.path:
            suggestion = (
                "Les endpoints cache sont sur /v1/stats-admin/ pour l'administration"
            )
        elif "/auth/test-direct" in request.url.path:
            suggestion = "L'endpoint /auth/test-direct a été supprimé. Utilisez /auth/login pour tester l'authentification."
        elif "/billing/openai-usage/" in request.url.path:
            suggestion = "Les endpoints billing OpenAI ont été supprimés ou déplacés. Consultez /docs pour les alternatives."
        elif any(x in request.url.path for x in ["/user/", "/profile/", "/account/"]):
            suggestion = (
                "Les endpoints utilisateur sont sur /v1/users/ (ex: /v1/users/profile)"
            )

        return JSONResponse(
            status_code=404,
            content={
                "detail": "Not Found",
                "error": "endpoint_not_found",
                "path": request.url.path,
                "suggestion": suggestion,
                "available_endpoints": [
                    "/v1/system/* (system endpoints)",
                    "/v1/auth/* (authentication)",
                    "/v1/users/* (user management)",
                    "/v1/stats-fast/* (statistics - authenticated users)",
                    "/v1/stats-admin/* (statistics - admin only)",
                    "/v1/billing/* (billing - admin/user)",
                    "/v1/invitations/* (invitations - admin only)",
                    "/v1/logging/* (logging - admin only)",
                ],
            },
            headers=create_cors_headers(request_origin),
        )

    # ÉTAPE 2: Skip l'auth pour les endpoints publics et requêtes OPTIONS
    if is_public_endpoint(request.url.path) or request.method == "OPTIONS":
        logger.debug(f"Public endpoint ou OPTIONS - Skip auth: {request.url.path}")

        # Pour OPTIONS, retourner directement les headers CORS
        if request.method == "OPTIONS":
            return JSONResponse(
                status_code=200,
                content={"message": "OK"},
                headers=create_cors_headers(request_origin),
            )

        # Pour les endpoints publics, continuer sans auth
        response = await call_next(request)

        # Ajouter les headers CORS aux réponses publiques
        for key, value in create_cors_headers(request_origin).items():
            response.headers[key] = value

        return response

    # ÉTAPE 3: Vérifier l'auth pour les endpoints utilisateur authentifié
    if is_authenticated_user_endpoint(request.url.path):
        logger.debug(f"Endpoint utilisateur authentifié: {request.url.path}")

        try:
            user_info = await verify_supabase_token(request)
            request.state.user = user_info

            # Continuer vers l'endpoint
            response = await call_next(request)

            # Ajouter les headers CORS
            for key, value in create_cors_headers(request_origin).items():
                response.headers[key] = value

            return response

        except HTTPException as e:
            logger.warning(
                f"Auth failed for authenticated endpoint {request.url.path}: {e.detail}"
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "error": "authentication_required",
                    "endpoint_type": "authenticated_user",
                },
                headers=create_cors_headers(request_origin),
            )

    # ÉTAPE 4: Vérifier l'auth ADMIN pour les endpoints protégés
    if is_protected_endpoint(request.url.path):
        logger.debug(f"Endpoint protégé (admin): {request.url.path}")

        try:
            user_info = await verify_supabase_token(request)

            # Vérifier les privilèges admin
            user_role = user_info.get("role", "user")
            is_admin = user_role in ["admin", "superuser"] or user_info.get(
                "is_admin", False
            )

            if not is_admin:
                logger.warning(
                    f"Access denied for non-admin user to {request.url.path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Access denied - admin privileges required",
                        "error": "insufficient_privileges",
                        "required_role": "admin",
                        "user_role": user_role,
                    },
                    headers=create_cors_headers(request_origin),
                )

            request.state.user = user_info

            # Continuer vers l'endpoint
            response = await call_next(request)

            # Ajouter les headers CORS
            for key, value in create_cors_headers(request_origin).items():
                response.headers[key] = value

            return response

        except HTTPException as e:
            logger.warning(
                f"Auth failed for protected endpoint {request.url.path}: {e.detail}"
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "error": "authentication_required",
                    "endpoint_type": "admin_protected",
                },
                headers=create_cors_headers(request_origin),
            )

    # ÉTAPE 5: Laisser passer les autres endpoints (FastAPI gère les 404 appropriés)
    logger.debug(f"Endpoint non catégorisé - laissé passer: {request.url.path}")

    # Authentification optionnelle pour les autres endpoints
    user_info = await optional_auth(request)
    if user_info:
        request.state.user = user_info

    response = await call_next(request)

    # Ajouter les headers CORS
    for key, value in create_cors_headers(request_origin).items():
        response.headers[key] = value

    return response


def get_authenticated_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Récupère l'utilisateur authentifié si disponible, sinon None
    À utiliser dans les endpoints avec authentification optionnelle

    Args:
        request: Request FastAPI

    Returns:
        Optional[Dict]: Informations utilisateur ou None
    """
    return getattr(request.state, "user", None)


# FONCTION DE DEBUG MISE À JOUR
def debug_middleware_config() -> Dict[str, Any]:
    """
    Retourne la configuration actuelle du middleware pour debug

    Returns:
        Dict: Configuration du middleware
    """
    return {
        "public_endpoints_count": len(PUBLIC_ENDPOINTS),
        "protected_patterns_count": len(PROTECTED_PATTERNS),
        "authenticated_user_patterns_count": len(AUTHENTICATED_USER_PATTERNS),
        "nonexistent_patterns_count": len(NONEXISTENT_PATTERNS),
        "extended_public_patterns_count": len(EXTENDED_PUBLIC_PATTERNS),
        "sample_public_endpoints": list(PUBLIC_ENDPOINTS)[:10],
        "sample_protected_patterns": PROTECTED_PATTERNS[:10],
        "sample_authenticated_user_patterns": AUTHENTICATED_USER_PATTERNS[:10],
        "supported_services": [
            "System (health, metrics, status)",
            "Auth (login, JWT, OAuth)",
            "Users (profiles, GDPR)",
            "Stats (fast cache + admin)",
            "Billing (invoicing + OpenAI)",
            "Invitations (team management)",
            "Logging/Analytics (usage tracking)",
        ],
        "removed_services": [
            "ask-public endpoints",
            "RAG endpoints (/rag/*)",
            "Conversations endpoints (/conversations/*)",
            "Expert endpoints (/expert/*)",
            "Obsolete billing OpenAI endpoints",
        ],
        "middleware_version": "4.5.1-health-endpoints-complete",
        "key_changes": [
            "ADDED: All health endpoints (/health, /health/ready, /health/live, /health/complete, /health/detailed)",
            "CORRECTED: /api/v1/billing/plans now PUBLIC",
            "CORRECTED: /api/v1/auth/test-direct marked as NONEXISTENT",
            "CORRECTED: Billing OpenAI endpoints marked as NONEXISTENT",
            "CORRECTED: Specific billing patterns instead of broad /billing/*",
            "MAINTAINED: All authentication and authorization logic intact",
        ],
    }
