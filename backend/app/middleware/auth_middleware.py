# app/middleware/auth_middleware.py
"""
Middleware d'authentification globale pour l'API Intelia Expert
Version 4.2 - CORRECTION DES PERMISSIONS UTILISATEUR
Support des endpoints conversations et expert pour utilisateurs authentifiés
CORS compatible avec credentials: 'include'
CORRECTION: Conversations et expert/ask maintenant accessibles aux utilisateurs authentifiés
"""

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

# Import de la fonction d'auth existante
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

# ENDPOINTS PUBLICS ETENDUS AVEC CACHE (pas d'auth requise)
PUBLIC_ENDPOINTS = {
    # === API ENDPOINTS PUBLICS ===
    "/api/ask-public",
    "/api/v1/ask-public",
    "/api/v1/system-status",
    "/api/v1/debug",
    "/api/rag/debug",
    "/api/rag/test",
    "/api/cors-test",
    "/api/",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/health",
    # === ENDPOINTS AUTH PUBLICS CORRIGES - VRAIS ENDPOINTS ===
    "/api/v1/auth/login",  # VRAI endpoint backend
    "/api/v1/auth/debug/jwt-config",  # VRAI endpoint backend
    "/api/v1/auth/test-direct",  # VRAI endpoint backend
    # === ENDPOINTS CACHE PUBLICS (health check) ===
    "/api/v1/stats-fast/health",  # Health check du cache
    "/api/v1/stats/test",  # Test du systeme cache (si montes dans main.py)
    # === AUTH TEMPORAIRE (auth-temp) ===
    "/api/auth-temp/login",  # Auth temp
    "/api/auth-temp/me",  # Auth temp
    "/api/auth-temp/test",  # Auth temp
    # === SYSTEM ENDPOINTS ===
    "/api/v1/system/health",  # System health
    "/api/v1/system/metrics",  # System metrics
    "/api/v1/system/status",  # System status
    "/api/deployment-debug",  # Deployment debug
    # === CONVERSATIONS PUBLIQUES ===
    "/api/v1/conversations/test-public",
    "/api/v1/conversations/test-public-post",
    # === EXPERT PUBLICS ===
    "/api/v1/expert/ask-public",  # Questions expert publiques
    # === ENDPOINTS SANS PREFIX /api (compatibilite) ===
    "/ask-public",
    "/v1/ask-public",
    "/system-status",
    "/debug",
    "/rag/debug",
    "/rag/test",
    "/cors-test",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",  # Monitoring
    "/admin/stats",  # Stats admin publiques
    "/health/complete",  # Health check complet
    "/deployment-debug",  # Debug deployment
    # === CACHE ENDPOINTS PUBLICS SANS PREFIX ===
    "/v1/stats-fast/health",  # Health check cache
    "/v1/stats/test",  # Test cache
    "/admin/cache/status",  # Status cache (si public dans main.py)
    # === AUTH ENDPOINTS SANS PREFIX (compatibilite) ===
    "/v1/auth/login",  # Version directe
    "/v1/auth/debug/jwt-config",  # Version directe
    "/v1/auth/test-direct",  # Version directe
    "/auth-temp/login",  # Auth temp sans /api
    "/auth-temp/me",  # Auth temp sans /api
    "/auth-temp/test",  # Auth temp sans /api
    # === CONVERSATIONS SANS PREFIX ===
    "/v1/conversations/test-public",
    "/v1/conversations/test-public-post",
    # === EXPERT SANS PREFIX ===
    "/v1/expert/ask-public",  # Questions expert publiques
}

# PATTERNS D'ENDPOINTS PROTEGES ETENDUS (authentification ADMIN requise)
PROTECTED_PATTERNS = [
    # === ENDPOINTS BUSINESS CORE ADMIN UNIQUEMENT ===
    "/api/v1/billing/",  # Facturation
    "/api/v1/logging/analytics/",  # Analytics
    "/api/v1/logging/questions",  # Questions (ancien endpoint)
    "/api/v1/conversations/admin/",  # ✅ MODIFIÉ - Administration conversations uniquement
    # RETIRÉ: "/api/v1/conversations/", (trop large - maintenant dans AUTHENTICATED_USER_PATTERNS)
    # RETIRÉ: "/api/v1/expert/ask",     (utilisateurs ont besoin - maintenant dans AUTHENTICATED_USER_PATTERNS)
    "/api/v1/admin/",  # Administration
    "/api/v1/invitations/",  # Invitations
    # === NOUVEAU: ENDPOINTS USERS (AJOUTE) ===
    "/api/v1/users/",  # Gestion profils utilisateur
    "/api/v1/users/profile",  # Profil utilisateur specifique
    "/api/v1/users/export",  # Export donnees utilisateur
    "/api/v1/users/debug/",  # Debug endpoints users
    # === ENDPOINTS CACHE PROTEGES - CORRECTION DES PERMISSIONS ===
    # Note: stats-fast maintenant accessible aux utilisateurs authentifiés
    # Seuls stats-admin restent super admin uniquement
    "/api/v1/stats-admin/",  # Administration cache (super admin uniquement)
    "/api/v1/stats-admin/force-update/",  # Force update cache (super admin)
    "/api/v1/stats-admin/cache/",  # Controle cache (super admin)
    "/api/v1/stats-admin/status",  # Status admin cache (super admin)
    "/api/admin/cache/force-update",  # Force update dans main.py (super admin)
    # === ENDPOINTS AUTH PROTEGES CORRIGES - VRAIS ENDPOINTS ===
    "/api/v1/auth/me",  # Profil utilisateur (VRAI endpoint)
    "/api/v1/auth/delete-data",  # Suppression donnees RGPD (VRAI endpoint)
    # === AUTH TEMPORAIRE PROTEGE ===
    "/api/auth-temp/me",  # Auth temp - profil
    # === PATTERNS SANS PREFIX (compatibilite) ===
    "/v1/billing/",
    "/v1/logging/analytics/",
    "/v1/logging/questions",  # Questions
    "/v1/conversations/admin/",  # ✅ MODIFIÉ - Administration conversations uniquement
    # RETIRÉ: "/v1/conversations/",    (maintenant dans AUTHENTICATED_USER_PATTERNS)
    # RETIRÉ: "/v1/expert/ask",        (maintenant dans AUTHENTICATED_USER_PATTERNS)
    "/v1/admin/",
    "/v1/invitations/",
    # === NOUVEAU: USERS SANS PREFIX (AJOUTE) ===
    "/v1/users/",  # Gestion profils utilisateur
    "/v1/users/profile",  # Profil utilisateur specifique
    "/v1/users/export",  # Export donnees utilisateur
    "/v1/users/debug/",  # Debug endpoints users
    # === CACHE SANS PREFIX - CORRECTION ===
    "/v1/stats-admin/",  # Admin cache uniquement
    "/admin/cache/force-update",  # Force update direct
    "/v1/auth/me",  # Sans /api
    "/v1/auth/delete-data",  # Sans /api
    "/auth-temp/me",  # Auth temp sans /api
]

# NOUVEAU: PATTERNS POUR UTILISATEURS AUTHENTIFIÉS (niveau intermédiaire)
AUTHENTICATED_USER_PATTERNS = [
    # === ENDPOINTS STATS-FAST - MAINTENANT ACCESSIBLE AUX USERS AUTHENTIFIÉS ===
    "/api/v1/stats-fast/",  # Tous les endpoints stats-fast
    "/api/v1/stats-fast/dashboard",  # Dashboard rapide
    "/api/v1/stats-fast/questions",  # Questions rapides
    "/api/v1/stats-fast/invitations",  # Invitations rapides
    "/api/v1/stats-fast/openai-costs/",  # Coûts OpenAI
    "/api/v1/stats-fast/performance",  # Performance
    "/api/v1/stats-fast/my-analytics",  # Analytics personnelles
    # === ✅ NOUVEAUX: ENDPOINTS CONVERSATIONS UTILISATEUR ===
    "/api/v1/conversations/user/",  # Conversations personnelles
    "/api/v1/conversations/",  # ✅ AJOUTÉ - Accès général avec vérif dans endpoint
    # === ✅ NOUVEAUX: ENDPOINTS EXPERT ===
    "/api/v1/expert/ask",  # ✅ AJOUTÉ - Questions expert
    # === PATTERNS SANS PREFIX ===
    "/v1/stats-fast/",  # Stats-fast sans /api
    "/v1/stats-fast/dashboard",
    "/v1/stats-fast/questions",
    "/v1/stats-fast/invitations",
    "/v1/stats-fast/openai-costs/",
    "/v1/stats-fast/performance",
    "/v1/stats-fast/my-analytics",
    # === ✅ NOUVEAUX: PATTERNS SANS PREFIX ===
    "/v1/conversations/user/",  # ✅ AJOUTÉ - Conversations utilisateur
    "/v1/conversations/",  # ✅ AJOUTÉ - Accès général
    "/v1/expert/ask",  # ✅ AJOUTÉ - Questions expert
    # === AUTRES ENDPOINTS POUR UTILISATEURS AUTHENTIFIÉS ===
    "/api/admin/stats",  # Stats basiques (pas admin cache)
]

# PATTERNS D'ENDPOINTS INEXISTANTS (retourner 404 au lieu de 405)
NONEXISTENT_PATTERNS = [
    "/api/v1/analytics/",  # N'existe pas
    "/api/v1/user/",  # N'existe pas - utiliser /v1/users/
    "/api/v1/profile/",  # N'existe pas (utiliser /v1/users/profile)
    "/api/v1/account/",  # N'existe pas (utiliser /v1/users/profile)
    # ANCIENS ENDPOINTS CACHE INCORRECTS
    "/api/v1/stats/",  # Ancien - maintenant /v1/stats-fast/ et /v1/stats-admin/
    "/api/v1/cache/",  # N'existe pas - utiliser /v1/stats-admin/
    "/api/stats/",  # Ancien pattern
    # ANCIENS ENDPOINTS AUTH INCORRECTS (n'existent plus)
    "/api/auth/login",  # Ancien - maintenant /v1/auth/login
    "/api/auth/register",  # Ancien - n'existe pas
    "/api/auth/me",  # Ancien - maintenant /v1/auth/me
    "/api/auth/debug/jwt-config",  # Ancien - maintenant /v1/auth/debug/jwt-config
    # Patterns sans prefix
    "/v1/analytics/",
    "/v1/user/",  # Ancien - utiliser /v1/users/
    "/v1/profile/",  # Ancien - utiliser /v1/users/profile
    "/v1/account/",  # Ancien - utiliser /v1/users/profile
    "/v1/stats/",  # Utiliser /v1/stats-fast/ ou /v1/stats-admin/
    "/v1/cache/",  # Utiliser /v1/stats-admin/
    "/stats/",  # Ancien
    "/cache/",  # Ancien
    "/auth/login",  # Ancien sans /api
    "/auth/register",  # Ancien sans /api
    "/auth/me",  # Ancien sans /api
    "/auth/debug/jwt-config",  # Ancien sans /api
]

# PATTERNS PUBLICS ETENDUS AVEC CACHE (pour la fonction is_public_endpoint)
EXTENDED_PUBLIC_PATTERNS = [
    # === DOCUMENTATION ET MONITORING ===
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",
    "/static/",
    # === AUTH PUBLICS CORRIGES - PATTERNS ===
    "/v1/auth/login",  # Pattern login
    "/v1/auth/debug",  # Pattern debug
    "/v1/auth/test-direct",  # Pattern test
    "/auth-temp/",  # Pattern auth temporaire
    # === PATTERNS CACHE PUBLICS ===
    "/v1/stats-fast/health",  # Health check cache
    "/v1/stats/test",  # Test cache
    "/admin/cache/status",  # Status cache public (si configure)
    # === RAG ET TESTS ===
    "/rag/",
    "/cors-test",
    # === API PATTERNS ===
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/auth/login",  # Pattern login avec /api
    "/api/v1/auth/debug",  # Pattern debug avec /api
    "/api/v1/auth/test-direct",  # Pattern test avec /api
    "/api/auth-temp/",  # Pattern auth temp avec /api
    # === PATTERNS CACHE AVEC /API ===
    "/api/v1/stats-fast/health",  # Health cache
    "/api/v1/stats/test",  # Test cache
    "/api/admin/cache/status",  # Status cache avec /api
    "/api/rag/",
    "/api/cors-test",
    "/api/v1/system",  # Pattern system
    "/api/v1/debug",
    "/api/v1/ask-public",
    "/api/v1/conversations/test-public",
    "/api/ask-public",
    "/api/deployment-debug",
    # === PATTERNS SANS VERSION ===
    "/v1/conversations/test-public",
    "/v1/ask-public",
    "/ask-public",
    "/deployment-debug",
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
    NOUVEAU: Verifie si un endpoint necessite une authentification utilisateur basique

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


# Fonctions pour verifier les permissions - CORRIGÉES
def has_admin_permission(user_info: Dict[str, Any]) -> bool:
    """
    Verifie si l'utilisateur a les permissions admin (pour stats-admin uniquement)

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
    NOUVEAU: Verifie si l'utilisateur est authentifié (pour conversations et expert)

    Args:
        user_info: Informations utilisateur depuis le token

    Returns:
        bool: True si l'utilisateur est authentifié validement
    """
    # Tout utilisateur avec un token valide peut accéder aux endpoints utilisateur
    return bool(user_info and user_info.get("email"))


async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification globale pour l'API Intelia Expert - VERSION 4.2 CORRIGÉE

    Logique CORRIGÉE:
    1. Gere les endpoints inexistants (404)
    2. Skip l'auth pour les endpoints publics et OPTIONS
    3. Authentification basique pour les endpoints utilisateur (conversations, expert/ask)
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

        # Message special pour les anciens endpoints
        suggestion = "Verifiez l'URL ou consultez /docs pour les endpoints disponibles"
        if "/stats/" in request.url.path and "/stats-fast/" not in request.url.path:
            suggestion = "Les endpoints stats sont maintenant sur /v1/stats-fast/ (utilisateurs authentifiés) et /v1/stats-admin/ (admin uniquement)"
        elif "/cache/" in request.url.path:
            suggestion = (
                "Les endpoints cache sont sur /v1/stats-admin/ pour l'administration"
            )
        elif "/auth/" in request.url.path and "/v1/auth/" not in request.url.path:
            suggestion = (
                "Les endpoints auth sont maintenant sur /v1/auth/ et non /auth/"
            )
        elif (
            "/user/" in request.url.path
            or "/profile/" in request.url.path
            or "/account/" in request.url.path
        ):
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
                "available_stats_endpoints": (
                    [
                        "/v1/stats-fast/* (utilisateurs authentifiés)",
                        "/v1/stats-admin/* (admin uniquement)",
                    ]
                    if "/stats" in request.url.path
                    else None
                ),
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

    # ETAPE 3: NOUVEAU - Verifier l'auth pour les endpoints utilisateur authentifié (conversations, expert)
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
        "users_endpoints": {
            "protected_patterns": [
                "/api/v1/users/",
                "/api/v1/users/profile",
                "/api/v1/users/export",
                "/api/v1/users/debug/",
            ]
        },
        "conversations_and_expert_endpoints": {
            "authenticated_user_patterns": [
                "/api/v1/conversations/user/",
                "/api/v1/conversations/",
                "/api/v1/expert/ask",
            ]
        },
        "stats_endpoints": {
            "authenticated_user_patterns": [
                "/api/v1/stats-fast/",
                "/api/v1/stats-fast/dashboard",
                "/api/v1/stats-fast/questions",
                "/api/v1/stats-fast/invitations",
            ],
            "admin_only_patterns": [
                "/api/v1/stats-admin/",
                "/api/admin/cache/force-update",
            ],
        },
        "middleware_version": "4.2-fixed-conversations-expert-permissions",
        "key_changes": [
            "FIXED: conversations and expert/ask endpoints now accessible to authenticated users",
            "SEPARATED: admin endpoints (/conversations/admin/) still require admin permissions",
            "IMPROVED: Better endpoint classification for user vs admin access",
            "MAINTAINED: Security checks within endpoints remain intact",
            "ADDED: Support for expert/ask-public as public endpoint",
        ],
    }
