# app/middleware/auth_middleware.py
"""
Middleware d'authentification globale pour l'API Intelia Expert
Version 4.1 - Ajout du support des endpoints users
Support des endpoints de cache ultra-rapides
Support des endpoints /api/v1/auth/ (vrais endpoints du backend)
CORS compatible avec credentials: 'include'
"""

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

# Import de la fonction d'auth existante
from app.api.v1.auth import get_current_user, security

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
    "/api/v1/auth/login",              # VRAI endpoint backend
    "/api/v1/auth/debug/jwt-config",   # VRAI endpoint backend
    "/api/v1/auth/test-direct",        # VRAI endpoint backend
    
    # === ENDPOINTS CACHE PUBLICS (health check) ===
    "/api/v1/stats-fast/health",          # Health check du cache
    "/api/v1/stats/test",                  # Test du systeme cache (si montes dans main.py)
    
    # === AUTH TEMPORAIRE (auth-temp) ===
    "/api/auth-temp/login",            # Auth temp
    "/api/auth-temp/me",               # Auth temp
    "/api/auth-temp/test",             # Auth temp
    
    # === SYSTEM ENDPOINTS ===
    "/api/v1/system/health",           # System health
    "/api/v1/system/metrics",          # System metrics
    "/api/v1/system/status",           # System status
    "/api/deployment-debug",           # Deployment debug
    
    # === CONVERSATIONS PUBLIQUES ===
    "/api/v1/conversations/test-public",
    "/api/v1/conversations/test-public-post",
    
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
    "/metrics",                        # Monitoring
    "/admin/stats",                    # Stats admin publiques
    "/health/complete",                # Health check complet
    "/deployment-debug",               # Debug deployment
    
    # === CACHE ENDPOINTS PUBLICS SANS PREFIX ===
    "/v1/stats-fast/health",              # Health check cache
    "/v1/stats/test",                     # Test cache
    "/admin/cache/status",                # Status cache (si public dans main.py)
    
    # === AUTH ENDPOINTS SANS PREFIX (compatibilite) ===
    "/v1/auth/login",                  # Version directe
    "/v1/auth/debug/jwt-config",       # Version directe
    "/v1/auth/test-direct",            # Version directe
    "/auth-temp/login",                # Auth temp sans /api
    "/auth-temp/me",                   # Auth temp sans /api
    "/auth-temp/test",                 # Auth temp sans /api
    
    # === CONVERSATIONS SANS PREFIX ===
    "/v1/conversations/test-public",
    "/v1/conversations/test-public-post"
}

# PATTERNS D'ENDPOINTS PROTEGES ETENDUS (authentification requise)
PROTECTED_PATTERNS = [
    # === ENDPOINTS BUSINESS CORE ===
    "/api/v1/billing/",                # Facturation
    "/api/v1/logging/analytics/",      # Analytics
    "/api/v1/logging/questions",       # Questions (ancien endpoint)
    "/api/v1/conversations/",          # Conversations (sauf test-public)
    "/api/v1/expert/ask",              # Questions expert
    "/api/v1/admin/",                  # Administration
    "/api/v1/invitations/",            # Invitations
    
    # === NOUVEAU: ENDPOINTS USERS (AJOUTE) ===
    "/api/v1/users/",                  # Gestion profils utilisateur
    "/api/v1/users/profile",           # Profil utilisateur specifique
    "/api/v1/users/export",            # Export donnees utilisateur
    "/api/v1/users/debug/",            # Debug endpoints users
    
    # === ENDPOINTS CACHE PROTEGES (super admin) ===
    "/api/v1/stats-fast/",                # Endpoints ultra-rapides (admin+)
    "/api/v1/stats-admin/",               # Administration cache (super admin)
    "/api/v1/stats-fast/dashboard",       # Dashboard rapide
    "/api/v1/stats-fast/questions",      # Questions rapides
    "/api/v1/stats-fast/invitations/stats", # Invitations rapides
    "/api/v1/stats-fast/openai-costs/",  # Couts OpenAI rapides
    "/api/v1/stats-fast/performance",    # Performance rapide
    "/api/v1/stats-fast/my-analytics",   # Analytics personnelles
    "/api/v1/stats-admin/force-update/", # Force update cache
    "/api/v1/stats-admin/cache/",        # Controle cache
    "/api/v1/stats-admin/status",        # Status admin cache
    "/api/admin/cache/",                  # Controle admin dans main.py
    
    # === ENDPOINTS AUTH PROTEGES CORRIGES - VRAIS ENDPOINTS ===
    "/api/v1/auth/me",                 # Profil utilisateur (VRAI endpoint)
    "/api/v1/auth/delete-data",        # Suppression donnees RGPD (VRAI endpoint)
    
    # === AUTH TEMPORAIRE PROTEGE ===
    "/api/auth-temp/me",               # Auth temp - profil
    
    # === PATTERNS SANS PREFIX (compatibilite) ===
    "/v1/billing/",
    "/v1/logging/analytics/",
    "/v1/logging/questions",           # Questions
    "/v1/conversations/",
    "/v1/expert/ask",
    "/v1/admin/",
    "/v1/invitations/",
    
    # === NOUVEAU: USERS SANS PREFIX (AJOUTE) ===
    "/v1/users/",                      # Gestion profils utilisateur
    "/v1/users/profile",               # Profil utilisateur specifique
    "/v1/users/export",                # Export donnees utilisateur
    "/v1/users/debug/",                # Debug endpoints users
    
    # === CACHE SANS PREFIX ===
    "/v1/stats-fast/",                    # Endpoints cache rapides
    "/v1/stats-admin/",                   # Admin cache
    "/admin/cache/",                      # Admin cache direct
    
    "/v1/auth/me",                     # Sans /api
    "/v1/auth/delete-data",            # Sans /api
    "/auth-temp/me",                   # Auth temp sans /api
]

# PATTERNS D'ENDPOINTS INEXISTANTS (retourner 404 au lieu de 405)
NONEXISTENT_PATTERNS = [
    "/api/v1/analytics/",              # N'existe pas
    "/api/v1/user/",                   # N'existe pas - utiliser /v1/users/
    "/api/v1/profile/",                # N'existe pas (utiliser /v1/users/profile)
    "/api/v1/account/",                # N'existe pas (utiliser /v1/users/profile)
    
    # ANCIENS ENDPOINTS CACHE INCORRECTS
    "/api/v1/stats/",                  # Ancien - maintenant /v1/stats-fast/ et /v1/stats-admin/
    "/api/v1/cache/",                  # N'existe pas - utiliser /v1/stats-admin/
    "/api/stats/",                     # Ancien pattern
    
    # ANCIENS ENDPOINTS AUTH INCORRECTS (n'existent plus)
    "/api/auth/login",                 # Ancien - maintenant /v1/auth/login
    "/api/auth/register",              # Ancien - n'existe pas
    "/api/auth/me",                    # Ancien - maintenant /v1/auth/me
    "/api/auth/debug/jwt-config",      # Ancien - maintenant /v1/auth/debug/jwt-config
    
    # Patterns sans prefix
    "/v1/analytics/",
    "/v1/user/",                       # Ancien - utiliser /v1/users/
    "/v1/profile/",                    # Ancien - utiliser /v1/users/profile
    "/v1/account/",                    # Ancien - utiliser /v1/users/profile
    "/v1/stats/",                      # Utiliser /v1/stats-fast/ ou /v1/stats-admin/
    "/v1/cache/",                      # Utiliser /v1/stats-admin/
    "/stats/",                         # Ancien
    "/cache/",                         # Ancien
    "/auth/login",                     # Ancien sans /api
    "/auth/register",                  # Ancien sans /api
    "/auth/me",                        # Ancien sans /api
    "/auth/debug/jwt-config",          # Ancien sans /api
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
    "/v1/auth/login",                  # Pattern login
    "/v1/auth/debug",                  # Pattern debug
    "/v1/auth/test-direct",            # Pattern test
    "/auth-temp/",                     # Pattern auth temporaire
    
    # === PATTERNS CACHE PUBLICS ===
    "/v1/stats-fast/health",              # Health check cache
    "/v1/stats/test",                     # Test cache
    "/admin/cache/status",                # Status cache public (si configure)
    
    # === RAG ET TESTS ===
    "/rag/",
    "/cors-test",
    
    # === API PATTERNS ===
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json", 
    "/api/v1/auth/login",              # Pattern login avec /api
    "/api/v1/auth/debug",              # Pattern debug avec /api
    "/api/v1/auth/test-direct",        # Pattern test avec /api
    "/api/auth-temp/",                 # Pattern auth temp avec /api
    
    # === PATTERNS CACHE AVEC /API ===
    "/api/v1/stats-fast/health",          # Health cache
    "/api/v1/stats/test",                 # Test cache
    "/api/admin/cache/status",            # Status cache avec /api
    
    "/api/rag/",
    "/api/cors-test",
    "/api/v1/system",                  # Pattern system
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
                status_code=401, 
                detail="Missing or invalid authorization header"
            )
        
        # Creer l'objet credentials comme attendu par get_current_user
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.replace("Bearer ", "")
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
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token"
        )

async def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Authentification optionnelle - ne leve pas d'erreur si pas de token
    Utile pour les endpoints qui peuvent fonctionner avec ou sans auth
    """
    try:
        return await verify_supabase_token(request)
    except HTTPException:
        logger.debug(f"Optional auth failed for {request.url.path} - continuing without auth")
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
    Verifie si un endpoint necessite une authentification
    
    Args:
        path: Chemin de l'endpoint a verifier
        
    Returns:
        bool: True si l'endpoint necessite une authentification
    """
    for pattern in PROTECTED_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"Protected pattern match: {path} -> {pattern}")
            return True
    
    logger.debug(f"Not a protected endpoint: {path}")
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
        "https://expert-app-cngws.ondigitalocean.app", 
        "http://localhost:3000",
        "http://localhost:8080"
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

# Fonction pour verifier les permissions cache
def has_cache_admin_permission(user_info: Dict[str, Any]) -> bool:
    """
    Verifie si l'utilisateur a les permissions pour les endpoints d'administration cache
    
    Args:
        user_info: Informations utilisateur depuis le token
        
    Returns:
        bool: True si l'utilisateur peut acceder aux endpoints admin cache
    """
    user_type = user_info.get("user_type", "user")
    is_admin = user_info.get("is_admin", False)
    
    # Super admin ou admin avec flag explicite
    return user_type in ["super_admin", "admin"] or is_admin

def has_cache_view_permission(user_info: Dict[str, Any]) -> bool:
    """
    Verifie si l'utilisateur peut voir les statistiques en cache
    
    Args:
        user_info: Informations utilisateur depuis le token
        
    Returns:
        bool: True si l'utilisateur peut voir les stats
    """
    user_type = user_info.get("user_type", "user")
    
    # Admin+ ou utilisateur avec permissions analytics
    return user_type in ["super_admin", "admin", "moderator"]

async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification globale pour l'API Intelia Expert - VERSION 4.1 AVEC USERS
    
    Logique:
    1. Gere les endpoints inexistants (404)
    2. Skip l'auth pour les endpoints publics et OPTIONS
    3. Verifie l'auth pour les endpoints proteges
    4. Gestion speciale pour les endpoints de cache
    5. NOUVEAU: Support complet des endpoints users
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
            suggestion = "Les endpoints stats sont maintenant sur /v1/stats-fast/ (ultra-rapides) et /v1/stats-admin/ (administration)"
        elif "/cache/" in request.url.path:
            suggestion = "Les endpoints cache sont sur /v1/stats-admin/ pour l'administration"
        elif "/auth/" in request.url.path and "/v1/auth/" not in request.url.path:
            suggestion = "Les endpoints auth sont maintenant sur /v1/auth/ et non /auth/"
        elif "/user/" in request.url.path or "/profile/" in request.url.path or "/account/" in request.url.path:
            suggestion = "Les endpoints utilisateur sont sur /v1/users/ (ex: /v1/users/profile)"
        
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Not Found", 
                "error": "endpoint_not_found",
                "path": request.url.path,
                "suggestion": suggestion,
                "available_user_endpoints": [
                    "/v1/users/profile (GET/PUT - gestion profil)",
                    "/v1/users/export (GET - export donnees)",
                    "/v1/users/debug/profile (GET - debug profil)"
                ] if "/user" in request.url.path or "/profile" in request.url.path else None
            },
            headers=create_cors_headers(request_origin)
        )
    
    # ETAPE 2: Skip l'auth pour les endpoints publics et requetes OPTIONS
    if is_public_endpoint(request.url.path) or request.method == "OPTIONS":
        logger.debug(f"Public endpoint ou OPTIONS - Skip auth: {request.url.path}")
        
        # Pour OPTIONS, retourner directement les headers CORS
        if request.method == "OPTIONS":
            return JSONResponse(
                status_code=200,
                content={"message": "OK"},
                headers=create_cors_headers(request_origin)
            )
        
        # Pour les endpoints publics, continuer sans auth
        response = await call_next(request)
        
        # Ajouter les headers CORS aux reponses publiques
        for key, value in create_cors_headers(request_origin).items():
            response.headers[key] = value
            
        return response
    
    # ETAPE 3: Verifier l'auth pour les endpoints proteges
    if is_protected_endpoint(request.url.path):
        try:
            logger.debug(f"Protected endpoint detected: {request.url.path}")
            
            # Verifier le token d'authentification
            user_info = await verify_supabase_token(request)
            
            # Verification speciale pour les endpoints cache admin
            if "/stats-admin/" in request.url.path or "/admin/cache/" in request.url.path:
                if not has_cache_admin_permission(user_info):
                    logger.warning(f"Cache admin permission denied for {user_info.get('email')} on {request.url.path}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Cache administration requires super_admin permissions",
                            "error": "insufficient_permissions",
                            "required_permission": "super_admin",
                            "user_type": user_info.get("user_type"),
                            "path": request.url.path
                        },
                        headers=create_cors_headers(request_origin)
                    )
            
            # Verification pour les endpoints stats-fast
            elif "/stats-fast/" in request.url.path:
                if not has_cache_view_permission(user_info):
                    logger.warning(f"Cache view permission denied for {user_info.get('email')} on {request.url.path}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Statistics access requires admin+ permissions",
                            "error": "insufficient_permissions", 
                            "required_permission": "admin",
                            "user_type": user_info.get("user_type"),
                            "path": request.url.path
                        },
                        headers=create_cors_headers(request_origin)
                    )
            
            # Ajouter les infos utilisateur a la request pour les endpoints suivants
            request.state.user = user_info
            
            logger.info(
                f"User authenticated: {user_info.get('email')} "
                f"(type: {user_info.get('user_type')}) "
                f"for {request.url.path}"
            )
            
            # Continuer vers l'endpoint
            response = await call_next(request)
            
            # Ajouter les headers CORS aux reponses protegees
            for key, value in create_cors_headers(request_origin).items():
                response.headers[key] = value
                
            return response
            
        except HTTPException as e:
            logger.warning(
                f"Auth failed for {request.url.path}: "
                f"Status {e.status_code} - {e.detail}"
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail, 
                    "error": "authentication_failed",
                    "path": request.url.path
                },
                headers=create_cors_headers(request_origin)
            )
            
        except Exception as e:
            logger.error(f"Auth middleware unexpected error for {request.url.path}: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication failed", 
                    "error": "internal_auth_error",
                    "path": request.url.path
                },
                headers=create_cors_headers(request_origin)
            )
    
    # ETAPE 4: Pour tous les autres endpoints (non proteges, non publics)
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
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
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
    return getattr(request.state, 'user', None)

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
        "nonexistent_patterns_count": len(NONEXISTENT_PATTERNS),
        "extended_public_patterns_count": len(EXTENDED_PUBLIC_PATTERNS),
        "sample_public_endpoints": list(PUBLIC_ENDPOINTS)[:15],
        "sample_protected_patterns": PROTECTED_PATTERNS[:15],
        "users_endpoints": {
            "protected_patterns": [
                "/api/v1/users/",
                "/api/v1/users/profile",
                "/api/v1/users/export",
                "/api/v1/users/debug/",
                "/v1/users/",
                "/v1/users/profile",
                "/v1/users/export",
                "/v1/users/debug/"
            ],
            "nonexistent_patterns": [
                "/api/v1/user/",
                "/api/v1/profile/",
                "/api/v1/account/",
                "/v1/user/",
                "/v1/profile/",
                "/v1/account/"
            ]
        },
        "middleware_version": "4.1-with-users-support",
        "key_changes": [
            "ADDED: Full support for /api/v1/users/* endpoints",
            "ADDED: /api/v1/users/profile as protected endpoint", 
            "ADDED: /api/v1/users/export as protected endpoint",
            "ADDED: /api/v1/users/debug/* as protected endpoints",
            "ADDED: Users patterns without /api prefix for compatibility",
            "UPDATED: Nonexistent patterns to redirect old user endpoints",
            "FIXED: Better error messages for old user endpoint patterns"
        ]
    }