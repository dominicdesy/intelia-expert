# app/middleware/auth_middleware.py
"""
Middleware d'authentification globale pour l'API Intelia Expert
Version 4.3 - NETTOYAGE ENDPOINTS SUPPRIMÉS
Suppression de: ask-public, rag/*, conversations, expert
CORS compatible avec credentials: 'include'
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

# ENDPOINTS PUBLICS NETTOYES (pas d'auth requise)
PUBLIC_ENDPOINTS = {
    # === API ENDPOINTS PUBLICS ===
    "/api/v1/debug",
    "/api/",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/health",
    # === ENDPOINTS AUTH PUBLICS CORRIGES - VRAIS ENDPOINTS ===
    "/api/v1/auth/login",
    "/api/v1/auth/debug/jwt-config",
    "/api/v1/auth/test-direct",
    # === ENDPOINTS CACHE PUBLICS (health check) ===
    "/api/v1/stats-fast/health",
    # === SYSTEM ENDPOINTS ===
    "/api/v1/system/health",
    "/api/v1/system/metrics",
    "/api/v1/system/status",
    # === ENDPOINTS SANS PREFIX /api (compatibilite) ===
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",
}

# PATTERNS D'ENDPOINTS PROTEGES ETENDUS (authentification ADMIN requise)
PROTECTED_PATTERNS = [
    # === ENDPOINTS BUSINESS CORE ADMIN UNIQUEMENT ===
    "/api/v1/billing/",
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

# PATTERNS D'ENDPOINTS INEXISTANTS (retourner 404 au lieu de 405)
NONEXISTENT_PATTERNS = [
    "/api/v1/analytics/",
    "/api/v1/user/",
    "/api/v1/profile/",
    "/api/v1/account/",
    "/api/v1/stats/",
    "/api/v1/cache/",
    "/api/v1/conversations/",
    "/api/v1/conversations/test-public",
    "/api/v1/conversations/test-public-post",
    "/api/v1/conversations/user/",
    "/api/v1/conversations/admin/",
]

# PATTERNS PUBLICS ETENDUS NETTOYES (pour la fonction is_public_endpoint)
EXTENDED_PUBLIC_PATTERNS = [
    # === DOCUMENTATION ET MONITORING ===
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",
    "/static/",
    # === AUTH PUBLICS PATTERNS ===
    "/api/v1/auth/login",
    "/api/v1/auth/debug",
    "/api/v1/auth/test-direct",
    # === PATTERNS CACHE PUBLICS ===
    "/api/v1/stats-fast/health",
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
    Maintient la compatibilite avec le systeme existant
    """
    try:
        # Extraire le token Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.debug(f"Missing or invalid auth header for {request.url.path}")
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        # Creer l'objet credentials comme attendu par get_current_user
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
    Authentification optionnelle - ne leve pas d'erreur si pas de token
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
    Verifie si un endpoint est public (pas d'authentification requise)

    Args:
        path: Chemin de l'endpoint a verifier

    Returns:
        bool: True si l'endpoint est public
    """
    # Verification exacte d'abord
    if path in PUBLIC_ENDPOINTS:
        logger.debug(f"Exact public endpoint match: {path}")
        return True

    # Puis verification par patterns
    for pattern in EXTENDED_PUBLIC_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"Public pattern match: {path} -> {pattern}")
            return True

    logger.debug(f"Not a public endpoint: {path}")
    return False


def is_protected_endpoint(path: str) -> bool:
    """
    Verifie si un endpoint necessite une authentification ADMIN

    Args:
        path: Chemin de l'endpoint a verifier

    Returns:
        bool: True si l'endpoint necessite une authentification admin
    """
    for pattern in PROTECTED_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"Admin protected pattern match: {path} -> {pattern}")
            return True

    logger.debug(f"Not an admin protected endpoint: {path}")
    return False


def is_authenticated_user_endpoint(path: str) -> bool:
    """
    Verifie si un endpoint necessite une authentification utilisateur basique

    Args:
        path: Chemin de l'endpoint a verifier

    Returns:
        bool: True si l'endpoint necessite une authentification utilisateur
    """
    for pattern in AUTHENTICATED_USER_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"User authenticated pattern match: {path} -> {pattern}")
            return True

    logger.debug(f"Not a user authenticated endpoint: {path}")
    return False


def is_nonexistent_endpoint(path: str) -> bool:
    """
    Verifie si c'est un endpoint qui n'existe pas (pour retourner 404)
    Evite les erreurs 405 Method Not Allowed pour des endpoints inexistants

    Args:
        path: Chemin de l'endpoint a verifier

    Returns:
        bool: True si l'endpoint n'existe pas
    """
    for pattern in NONEXISTENT_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"Nonexistent pattern match: {path} -> {pattern}")
            return True

    return False


def create_cors_headers(origin: str = None) -> Dict[str, str]:
    """
    CORS CORRIGE - Compatible avec credentials: 'include'
    Cree les headers CORS standard pour les reponses

    Args:
        origin: Origin de la requete (pour eviter le wildcard avec credentials)

    Returns:
        Dict: Headers CORS complets
    """
    # Liste des origins autorises
    allowed_origins = [
        "https://expert.intelia.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Determiner l'origin a utiliser
    cors_origin = "*"  # Par defaut
    cors_credentials = "false"  # Par defaut

    if origin and origin in allowed_origins:
        cors_origin = origin  # Origin specifique pour credentials
        cors_credentials = "true"  # Credentials autorisees pour origins specifiques

    return {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent",
        "Access-Control-Allow-Credentials": cors_credentials,
    }


# Fonctions pour verifier les permissions
def has_admin_permission(user_info: Dict[str, Any]) -> bool:
    """
    Verifie si l'utilisateur a les permissions admin

    Args:
        user_info: Informations utilisateur depuis le token

    Returns:
        bool: True si l'utilisateur peut acceder aux endpoints admin
    """
    user_type = user_info.get("user_type", "user")
    is_admin = user_info.get("is_admin", False)

    # Super admin ou admin avec flag explicite
    return user_type in ["super_admin", "admin"] or is_admin


def is_authenticated_user(user_info: Dict[str, Any]) -> bool:
    """
    Verifie si l'utilisateur est authentifié

    Args:
        user_info: Informations utilisateur depuis le token

    Returns:
        bool: True si l'utilisateur est authentifié validement
    """
    # Tout utilisateur avec un token valide peut accéder aux endpoints utilisateur
    return bool(user_info and user_info.get("email"))


async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification globale pour l'API Intelia Expert - VERSION 4.3 NETTOYÉE

    Logique:
    1. Gere les endpoints inexistants (404) - Inclut maintenant ask-public, rag, conversations, expert
    2. Skip l'auth pour les endpoints publics et OPTIONS
    3. Authentification basique pour les endpoints utilisateur (stats-fast)
    4. Authentification admin pour les endpoints protégés (admin uniquement)
    5. Support complet des endpoints users
    6. Laisse passer les autres endpoints (FastAPI gere les 404)

    Args:
        request: Request FastAPI
        call_next: Fonction suivante dans la chaine

    Returns:
        Response: Reponse HTTP appropriee
    """

    # LOG DE DEBUG DETAILLE
    logger.debug(
        f"Auth middleware - Method: {request.method}, "
        f"Path: {request.url.path}, "
        f"Auth Header: {'Present' if request.headers.get('Authorization') else 'Missing'}, "
        f"Origin: {request.headers.get('Origin', 'None')}"
    )

    # Recuperer l'origin de la requete pour CORS
    request_origin = request.headers.get("Origin")

    # ETAPE 1: Gerer les endpoints inexistants AVANT toute autre logique
    if is_nonexistent_endpoint(request.url.path):
        logger.warning(f"Endpoint inexistant detecte: {request.url.path}")

        # Messages spécialisés selon le type d'endpoint supprimé
        suggestion = "Verifiez l'URL ou consultez /docs pour les endpoints disponibles"

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
        elif "/auth/" in request.url.path and "/v1/auth/" not in request.url.path:
            suggestion = (
                "Les endpoints auth sont maintenant sur /v1/auth/ et non /auth/"
            )
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
                    "/v1/billing/* (billing - admin only)",
                    "/v1/invitations/* (invitations - admin only)",
                    "/v1/logging/* (logging - admin only)",
                ],
            },
            headers=create_cors_headers(request_origin),
        )

    # ETAPE 2: Skip l'auth pour les endpoints publics et requetes OPTIONS
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

        # Ajouter les headers CORS aux reponses publiques
        for key, value in create_cors_headers(request_origin).items():
            response.headers[key] = value

        return response

    # ETAPE 3: Verifier l'auth pour les endpoints utilisateur authentifié
    if is_authenticated_user_endpoint(request.url.path):
        try:
            logger.debug(f"Authenticated user endpoint detected: {request.url.path}")

            # Verifier le token d'authentification
            user_info = await verify_supabase_token(request)

            # Vérifier que l'utilisateur est authentifié
            if not is_authenticated_user(user_info):
                logger.warning(
                    f"Invalid user authentication for {user_info.get('email')} on {request.url.path}"
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Valid authentication required",
                        "error": "authentication_required",
                        "path": request.url.path,
                    },
                    headers=create_cors_headers(request_origin),
                )

            # Ajouter les infos utilisateur a la request
            request.state.user = user_info

            logger.info(
                f"User authenticated: {user_info.get('email')} "
                f"(type: {user_info.get('user_type')}) "
                f"for {request.url.path}"
            )

            # Continuer vers l'endpoint
            response = await call_next(request)

            # Ajouter les headers CORS
            for key, value in create_cors_headers(request_origin).items():
                response.headers[key] = value

            return response

        except HTTPException as e:
            logger.warning(
                f"Auth failed for user endpoint {request.url.path}: "
                f"Status {e.status_code} - {e.detail}"
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "error": "authentication_failed",
                    "path": request.url.path,
                },
                headers=create_cors_headers(request_origin),
            )

        except Exception as e:
            logger.error(
                f"Auth middleware unexpected error for user endpoint {request.url.path}: {e}"
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication failed",
                    "error": "internal_auth_error",
                    "path": request.url.path,
                },
                headers=create_cors_headers(request_origin),
            )

    # ETAPE 4: Verifier l'auth ADMIN pour les endpoints proteges
    if is_protected_endpoint(request.url.path):
        try:
            logger.debug(f"Admin protected endpoint detected: {request.url.path}")

            # Verifier le token d'authentification
            user_info = await verify_supabase_token(request)

            # Verification pour les endpoints admin
            if not has_admin_permission(user_info):
                logger.warning(
                    f"Admin permission denied for {user_info.get('email')} on {request.url.path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Admin permissions required",
                        "error": "insufficient_permissions",
                        "required_permission": "admin",
                        "user_type": user_info.get("user_type"),
                        "path": request.url.path,
                    },
                    headers=create_cors_headers(request_origin),
                )

            # Ajouter les infos utilisateur a la request
            request.state.user = user_info

            logger.info(
                f"Admin authenticated: {user_info.get('email')} "
                f"(type: {user_info.get('user_type')}) "
                f"for {request.url.path}"
            )

            # Continuer vers l'endpoint
            response = await call_next(request)

            # Ajouter les headers CORS
            for key, value in create_cors_headers(request_origin).items():
                response.headers[key] = value

            return response

        except HTTPException as e:
            logger.warning(
                f"Admin auth failed for {request.url.path}: "
                f"Status {e.status_code} - {e.detail}"
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "error": "authentication_failed",
                    "path": request.url.path,
                },
                headers=create_cors_headers(request_origin),
            )

        except Exception as e:
            logger.error(
                f"Admin auth middleware unexpected error for {request.url.path}: {e}"
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication failed",
                    "error": "internal_auth_error",
                    "path": request.url.path,
                },
                headers=create_cors_headers(request_origin),
            )

    # ETAPE 5: Pour tous les autres endpoints (non proteges, non publics)
    # Laisser passer - FastAPI gerera naturellement les 404 pour les routes inexistantes
    logger.debug(f"Endpoint non-protege - Passage libre: {request.url.path}")

    # Ajouter une authentification optionnelle pour ces endpoints
    try:
        user_info = await optional_auth(request)
        if user_info:
            request.state.user = user_info
            logger.debug(f"Optional auth successful for {request.url.path}")
    except Exception:
        # Ignorer les erreurs d'auth optionnelle
        pass

    response = await call_next(request)

    # Ajouter les headers CORS a toutes les reponses
    for key, value in create_cors_headers(request_origin).items():
        response.headers[key] = value

    return response


# FONCTION UTILITAIRE POUR LES ENDPOINTS
def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Recupere l'utilisateur authentifie depuis request.state
    A utiliser dans les endpoints qui necessitent une authentification

    Args:
        request: Request FastAPI

    Returns:
        Dict: Informations utilisateur

    Raises:
        HTTPException: Si pas d'utilisateur authentifie
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    return request.state.user


def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Recupere l'utilisateur authentifie si disponible, sinon None
    A utiliser dans les endpoints avec authentification optionnelle

    Args:
        request: Request FastAPI

    Returns:
        Optional[Dict]: Informations utilisateur ou None
    """
    return getattr(request.state, "user", None)


# FONCTION DE DEBUG MISE A JOUR
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
        ],
        "middleware_version": "4.3-cleaned-endpoints",
        "key_changes": [
            "REMOVED: All ask-public endpoints",
            "REMOVED: All RAG endpoints (/rag/debug, /rag/test)",
            "REMOVED: All conversations endpoints (/conversations/*)",
            "REMOVED: All expert endpoints (/expert/*)",
            "FOCUSED: API now concentrates on core business services",
            "MAINTAINED: All authentication and authorization logic intact",
        ],
    }
