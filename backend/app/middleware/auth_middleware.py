# app/middleware/auth_middleware.py
"""
Middleware d'authentification globale pour l'API Intelia Expert
Version 5.0 - ARCHITECTURE SIMPLIFIÉE
Suppression: Gestion des endpoints inexistants (laissée à FastAPI)
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

# ENDPOINTS PUBLICS (pas d'auth requise)
PUBLIC_ENDPOINTS = {
    # === API ENDPOINTS PUBLICS ===
    "/api/v1/debug",
    "/api/",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    # === TOUS LES ENDPOINTS HEALTH ===
    "/api/v1/health",
    "/api/v1/health/",
    "/api/v1/health/ready",
    "/api/v1/health/live",
    "/api/v1/health/complete",
    "/api/v1/health/detailed",
    # === ENDPOINTS BILLING PUBLICS ===
    "/api/v1/billing/plans",
    # === ENDPOINTS AUTH PUBLICS ===
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/confirm-email",
    # === ENDPOINTS OAUTH PUBLICS ===
    "/api/v1/auth/oauth/linkedin/login",
    "/api/v1/auth/oauth/facebook/login",
    "/api/v1/auth/oauth/linkedin/callback",
    "/api/v1/auth/oauth/facebook/callback",
    # === ENDPOINTS STRIPE WEBHOOKS PUBLICS ===
    "/api/v1/stripe/webhook",
    "/api/v1/stripe/webhook/",
    "/api/v1/stripe/webhook/test",
    "/api/v1/stripe/webhook/test/",
    # === ENDPOINTS CACHE PUBLICS ===
    "/api/v1/stats-fast/health",
    # === SYSTEM ENDPOINTS (health et status publics uniquement) ===
    "/api/v1/system/health",
    "/api/v1/system/status",
    # === ENDPOINTS QA QUALITY PUBLICS (cron avec secret) ===
    "/api/v1/qa-quality/cron",
    # === ENDPOINTS SANS PREFIX /api ===
    "/",
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
}

# PATTERNS D'ENDPOINTS PROTÉGÉS (authentification ADMIN requise)
PROTECTED_PATTERNS = [
    # === ENDPOINTS BILLING ADMIN ===
    "/api/v1/billing/admin",
    "/api/v1/billing/invoices",
    "/api/v1/billing/quotas",
    "/api/v1/billing/generate-invoice",
    "/api/v1/billing/openai-usage/",  # 🔒 NOUVEAU: Tous les endpoints OpenAI usage
    # === ENDPOINTS ADMIN STRICTS ===
    "/api/v1/logging/questions",
    "/api/v1/admin/",
    # === ENDPOINTS CACHE ADMIN ===
    "/api/v1/stats-admin/",
    "/api/v1/stats-admin/force-update/",
    "/api/v1/stats-admin/cache/",
    "/api/v1/stats-admin/status",
    # === ENDPOINTS AUTH PROTÉGÉS (admin only) ===
    "/api/v1/auth/delete-data",
    "/api/v1/auth/debug/",  # 🔒 NOUVEAU: Tous les endpoints debug auth
    # === ENDPOINTS SYSTEM PROTÉGÉS (admin only) ===
    "/api/v1/system/metrics",  # 🔒 NOUVEAU: Métriques système
    # === ENDPOINTS QA QUALITY (admin only) ===
    "/api/v1/qa-quality/",  # 🔒 NOUVEAU: Monitoring de qualité Q&A
]

# PATTERNS POUR UTILISATEURS AUTHENTIFIÉS (niveau intermédiaire)
AUTHENTICATED_USER_PATTERNS = [
    # === ENDPOINTS AUTH UTILISATEURS ===
    "/api/v1/auth/me",
    "/api/v1/auth/heartbeat",
    "/api/v1/auth/logout",
    # === ENDPOINTS USERS (profil personnel) ===
    "/api/v1/users/profile",
    "/api/v1/users/export",
    "/api/v1/users/debug/",
    # === ENDPOINTS LOGGING/ANALYTICS (sessions personnelles) ===
    "/api/v1/logging/analytics/my-sessions",
    # === ENDPOINTS STATS-FAST ===
    "/api/v1/stats-fast/",
    "/api/v1/stats-fast/dashboard",
    "/api/v1/stats-fast/questions",
    "/api/v1/stats-fast/invitations",
    "/api/v1/stats-fast/openai-costs/",
    "/api/v1/stats-fast/performance",
    "/api/v1/stats-fast/my-analytics",
    # === ENDPOINTS BILLING UTILISATEUR ===
    "/api/v1/billing/my-billing",
    "/api/v1/billing/change-plan",
    # === ENDPOINTS CONVERSATIONS (sauvegarde personnelle) ===
    "/api/v1/conversations/save",
    "/api/v1/conversations/user/",
    "/api/v1/conversations/",  # Tous les endpoints conversations (get messages, feedback, etc.)
    # === ENDPOINTS INVITATIONS (tous les utilisateurs authentifiés) ===
    "/api/v1/invitations/",
]

# PATTERNS PUBLICS ÉTENDUS (pour les vérifications par pattern)
EXTENDED_PUBLIC_PATTERNS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",
    "/static/",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/confirm-email",
    "/api/v1/auth/oauth/",
    "/api/v1/stats-fast/health",
    "/api/v1/billing/plans",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/debug",
]


async def verify_supabase_token(request: Request) -> Dict[str, Any]:
    """
    Wrapper pour utiliser la logique d'auth existante dans api/v1/auth.py
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.debug(f"Missing or invalid auth header for {request.url.path}")
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=auth_header.replace("Bearer ", "")
        )

        user_info = await get_current_user(credentials)
        logger.debug(f"Token verified for user: {user_info.get('email')}")
        return user_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Authentification optionnelle - ne lève pas d'erreur si pas de token
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
    """
    # Vérification exacte d'abord
    if path in PUBLIC_ENDPOINTS:
        return True

    # Vérification par patterns pour les endpoints dynamiques
    return any(path.startswith(pattern) for pattern in EXTENDED_PUBLIC_PATTERNS)


def is_protected_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint nécessite une authentification ADMIN
    """
    return any(path.startswith(pattern) for pattern in PROTECTED_PATTERNS)


def is_authenticated_user_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint nécessite une authentification utilisateur basique
    """
    return any(path.startswith(pattern) for pattern in AUTHENTICATED_USER_PATTERNS)


def create_cors_headers(origin: Optional[str] = None) -> Dict[str, str]:
    """
    Crée les headers CORS appropriés
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
    Middleware d'authentification principal - VERSION SIMPLIFIÉE

    Flux de traitement:
    1. Skip l'auth pour les endpoints publics et OPTIONS
    2. Authentification admin pour les endpoints protégés
    3. Authentification utilisateur pour les endpoints intermédiaires
    4. Authentification optionnelle pour le reste (FastAPI gère les 404)
    """

    logger.debug(
        f"Auth middleware - Method: {request.method}, "
        f"Path: {request.url.path}, "
        f"Auth Header: {'Present' if request.headers.get('Authorization') else 'Missing'}"
    )

    request_origin = request.headers.get("Origin")

    # ÉTAPE 1: Requêtes OPTIONS (CORS preflight)
    if request.method == "OPTIONS":
        logger.debug(f"OPTIONS request - returning CORS headers: {request.url.path}")
        return JSONResponse(
            status_code=200,
            content={"message": "OK"},
            headers=create_cors_headers(request_origin),
        )

    # ÉTAPE 2: Endpoints publics (pas d'auth requise)
    if is_public_endpoint(request.url.path):
        logger.debug(f"Public endpoint - skip auth: {request.url.path}")
        response = await call_next(request)

        # Ajouter headers CORS
        for key, value in create_cors_headers(request_origin).items():
            response.headers[key] = value

        return response

    # ÉTAPE 3: Endpoints protégés (auth admin requise)
    if is_protected_endpoint(request.url.path):
        logger.debug(f"Protected endpoint (admin required): {request.url.path}")

        try:
            user_info = await verify_supabase_token(request)

            # Vérifier privilèges admin
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
            response = await call_next(request)

            # Ajouter headers CORS
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

    # ÉTAPE 4: Endpoints utilisateur authentifié
    if is_authenticated_user_endpoint(request.url.path):
        logger.debug(f"Authenticated user endpoint: {request.url.path}")

        try:
            user_info = await verify_supabase_token(request)
            request.state.user = user_info
            response = await call_next(request)

            # Ajouter headers CORS
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

    # ÉTAPE 5: Autres endpoints - FastAPI gère naturellement les 404
    logger.debug(f"Uncategorized endpoint - passing through: {request.url.path}")

    # Authentification optionnelle
    user_info = await optional_auth(request)
    if user_info:
        request.state.user = user_info

    response = await call_next(request)

    # Ajouter headers CORS
    for key, value in create_cors_headers(request_origin).items():
        response.headers[key] = value

    return response


def get_authenticated_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Récupère l'utilisateur authentifié si disponible, sinon None
    """
    return getattr(request.state, "user", None)


def debug_middleware_config() -> Dict[str, Any]:
    """
    Retourne la configuration actuelle du middleware pour debug
    """
    return {
        "middleware_version": "5.0-simplified",
        "public_endpoints_count": len(PUBLIC_ENDPOINTS),
        "protected_patterns_count": len(PROTECTED_PATTERNS),
        "authenticated_user_patterns_count": len(AUTHENTICATED_USER_PATTERNS),
        "extended_public_patterns_count": len(EXTENDED_PUBLIC_PATTERNS),
        "key_changes": [
            "REMOVED: NONEXISTENT_PATTERNS - FastAPI now handles 404s naturally",
            "SIMPLIFIED: Cleaner logic flow without endpoint existence checking",
            "MAINTAINED: All authentication and authorization logic intact",
            "IMPROVED: Better separation of concerns",
        ],
        "supported_services": [
            "System (health, metrics, status)",
            "Auth (login, JWT, OAuth)",
            "Users (profiles, GDPR)",
            "Stats (fast cache + admin)",
            "Billing (invoicing + OpenAI)",
            "Invitations (team management)",
            "Logging/Analytics (usage tracking)",
        ],
    }
