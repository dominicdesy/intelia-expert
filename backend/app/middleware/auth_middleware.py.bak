# app/middleware/auth_middleware.py
"""
Middleware d'authentification globale pour l'API Intelia Expert
Version mise à jour avec support des nouveaux endpoints auth
"""

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

# Import de la fonction d'auth existante
from app.api.v1.auth import get_current_user, security

logger = logging.getLogger(__name__)

# 🆕 ENDPOINTS PUBLICS COMPLETS (pas d'auth requise)
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
    
    # === NOUVEAUX ENDPOINTS AUTH PUBLICS ===
    "/api/v1/auth/login",           # ✅ Login public
    "/api/v1/auth/register",        # ✅ Registration publique
    "/api/v1/auth/debug/jwt-config", # ✅ Debug public
    
    # === CONVERSATIONS PUBLIQUES ===
    "/api/v1/conversations/test-public",
    "/api/v1/conversations/test-public-post",
    
    # === ENDPOINTS SANS PREFIX /api (compatibilité) ===
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
    "/metrics",                     # Monitoring
    "/admin/stats",                 # Stats admin publiques
    "/health/complete",             # Health check complet
    
    # === AUTH ENDPOINTS SANS PREFIX (compatibilité) ===
    "/auth/login",
    "/auth/register",
    "/auth/debug/jwt-config",
    
    # === CONVERSATIONS SANS PREFIX ===
    "/v1/conversations/test-public",
    "/v1/conversations/test-public-post"
}

# 🔒 PATTERNS D'ENDPOINTS PROTÉGÉS (authentification requise)
PROTECTED_PATTERNS = [
    # === ENDPOINTS BUSINESS CORE ===
    "/api/v1/billing/",             # Facturation
    "/api/v1/logging/analytics/",   # Analytics
    "/api/v1/conversations/",       # Conversations (sauf test-public)
    "/api/v1/expert/ask",           # Questions expert
    "/api/v1/admin/",               # Administration
    "/api/v1/invitations/",         # Invitations
    
    # === NOUVEAUX ENDPOINTS AUTH PROTÉGÉS ===
    "/api/v1/auth/verify",          # Vérification token
    "/api/v1/auth/logout",          # Déconnexion
    "/api/v1/auth/update-profile",  # Mise à jour profil
    "/api/v1/auth/me",              # Profil utilisateur
    "/api/v1/auth/delete-data",     # Suppression données RGPD
    "/api/v1/auth/export-user",     # Export données RGPD
    
    # === PATTERNS SANS PREFIX (compatibilité) ===
    "/v1/billing/",
    "/v1/logging/analytics/",
    "/v1/conversations/",
    "/v1/expert/ask",
    "/v1/admin/",
    "/v1/invitations/",
    "/auth/verify",
    "/auth/logout",
    "/auth/update-profile",
    "/auth/me",
    "/auth/delete-data",
    "/auth/export-user",
]

# ❌ PATTERNS D'ENDPOINTS INEXISTANTS (retourner 404 au lieu de 405)
NONEXISTENT_PATTERNS = [
    "/api/v1/analytics/",           # N'existe pas
    "/api/v1/user/",                # N'existe pas
    "/api/v1/stats/",               # N'existe pas
    "/api/v1/profile/",             # N'existe pas (utiliser /auth/)
    "/api/v1/account/",             # N'existe pas (utiliser /auth/)
    "/api/v1/users/",               # N'existe pas (utiliser /auth/)
    
    # Patterns sans prefix
    "/v1/analytics/",
    "/v1/user/",
    "/v1/stats/",
    "/v1/profile/",
    "/v1/account/",
    "/v1/users/",
]

# 🆕 PATTERNS PUBLICS ÉTENDUS (pour la fonction is_public_endpoint)
EXTENDED_PUBLIC_PATTERNS = [
    # === DOCUMENTATION ET MONITORING ===
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/health",
    "/metrics",
    "/static/",
    
    # === AUTH PUBLICS ===
    "/auth/login",
    "/auth/register",
    "/auth/debug",
    
    # === RAG ET TESTS ===
    "/rag/",
    "/cors-test",
    
    # === API PATTERNS ===
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json", 
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/debug",
    "/api/rag/",
    "/api/cors-test",
    "/api/v1/system-status",
    "/api/v1/debug",
    "/api/v1/ask-public",
    "/api/v1/conversations/test-public",
    "/api/ask-public",
    
    # === PATTERNS SANS VERSION ===
    "/v1/conversations/test-public",
    "/v1/ask-public",
    "/ask-public",
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
            logger.debug(f"🔍 Missing or invalid auth header for {request.url.path}")
            raise HTTPException(
                status_code=401, 
                detail="Missing or invalid authorization header"
            )
        
        # Créer l'objet credentials comme attendu par get_current_user
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.replace("Bearer ", "")
        )
        
        # Utiliser la fonction existante (maintient la logique multi-secret)
        user_info = await get_current_user(credentials)
        
        logger.debug(f"✅ Token verified for user: {user_info.get('email')}")
        return user_info
        
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        logger.error(f"❌ Token verification failed: {e}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token"
        )

async def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Authentification optionnelle - ne lève pas d'erreur si pas de token
    Utile pour les endpoints qui peuvent fonctionner avec ou sans auth
    """
    try:
        return await verify_supabase_token(request)
    except HTTPException:
        logger.debug(f"🔍 Optional auth failed for {request.url.path} - continuing without auth")
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
        logger.debug(f"✅ Exact public endpoint match: {path}")
        return True
    
    # Puis vérification par patterns
    for pattern in EXTENDED_PUBLIC_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"✅ Public pattern match: {path} -> {pattern}")
            return True
    
    logger.debug(f"🔒 Not a public endpoint: {path}")
    return False

def is_protected_endpoint(path: str) -> bool:
    """
    Vérifie si un endpoint nécessite une authentification
    
    Args:
        path: Chemin de l'endpoint à vérifier
        
    Returns:
        bool: True si l'endpoint nécessite une authentification
    """
    for pattern in PROTECTED_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"🔒 Protected pattern match: {path} -> {pattern}")
            return True
    
    logger.debug(f"🔓 Not a protected endpoint: {path}")
    return False

def is_nonexistent_endpoint(path: str) -> bool:
    """
    Vérifie si c'est un endpoint qui n'existe pas (pour retourner 404)
    Évite les erreurs 405 Method Not Allowed pour des endpoints inexistants
    
    Args:
        path: Chemin de l'endpoint à vérifier
        
    Returns:
        bool: True si l'endpoint n'existe pas
    """
    for pattern in NONEXISTENT_PATTERNS:
        if path.startswith(pattern):
            logger.debug(f"❌ Nonexistent pattern match: {path} -> {pattern}")
            return True
    
    return False

def create_cors_headers() -> Dict[str, str]:
    """
    Crée les headers CORS standard pour les réponses
    
    Returns:
        Dict: Headers CORS complets
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent",
        "Access-Control-Allow-Credentials": "true",
    }

async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification globale pour l'API Intelia Expert
    
    Logique:
    1. Gère les endpoints inexistants (404)
    2. Skip l'auth pour les endpoints publics et OPTIONS
    3. Vérifie l'auth pour les endpoints protégés
    4. Laisse passer les autres endpoints (FastAPI gère les 404)
    
    Args:
        request: Request FastAPI
        call_next: Fonction suivante dans la chaîne
        
    Returns:
        Response: Réponse HTTP appropriée
    """
    
    # 📊 LOG DE DEBUG DÉTAILLÉ
    logger.debug(
        f"🔍 Auth middleware - Method: {request.method}, "
        f"Path: {request.url.path}, "
        f"Headers: {dict(request.headers)}"
    )
    
    # 🚨 ÉTAPE 1: Gérer les endpoints inexistants AVANT toute autre logique
    if is_nonexistent_endpoint(request.url.path):
        logger.warning(f"❌ Endpoint inexistant détecté: {request.url.path}")
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Not Found", 
                "error": "endpoint_not_found",
                "path": request.url.path
            },
            headers=create_cors_headers()
        )
    
    # ✅ ÉTAPE 2: Skip l'auth pour les endpoints publics et requêtes OPTIONS
    if is_public_endpoint(request.url.path) or request.method == "OPTIONS":
        logger.debug(f"✅ Public endpoint ou OPTIONS - Skip auth: {request.url.path}")
        
        # Pour OPTIONS, retourner directement les headers CORS
        if request.method == "OPTIONS":
            return JSONResponse(
                status_code=200,
                content={"message": "OK"},
                headers=create_cors_headers()
            )
        
        # Pour les endpoints publics, continuer sans auth
        return await call_next(request)
    
    # 🔒 ÉTAPE 3: Vérifier l'auth pour les endpoints protégés
    if is_protected_endpoint(request.url.path):
        try:
            logger.debug(f"🔒 Protected endpoint detected: {request.url.path}")
            
            # Vérifier le token d'authentification
            user_info = await verify_supabase_token(request)
            
            # Ajouter les infos utilisateur à la request pour les endpoints suivants
            request.state.user = user_info
            
            logger.info(
                f"✅ User authenticated: {user_info.get('email')} "
                f"(type: {user_info.get('user_type')}) "
                f"for {request.url.path}"
            )
            
            # Continuer vers l'endpoint
            return await call_next(request)
            
        except HTTPException as e:
            logger.warning(
                f"🔒 Auth failed for {request.url.path}: "
                f"Status {e.status_code} - {e.detail}"
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail, 
                    "error": "authentication_failed",
                    "path": request.url.path
                },
                headers=create_cors_headers()
            )
            
        except Exception as e:
            logger.error(f"❌ Auth middleware unexpected error for {request.url.path}: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication failed", 
                    "error": "internal_auth_error",
                    "path": request.url.path
                },
                headers=create_cors_headers()
            )
    
    # 🔄 ÉTAPE 4: Pour tous les autres endpoints (non protégés, non publics)
    # Laisser passer - FastAPI gérera naturellement les 404 pour les routes inexistantes
    logger.debug(f"🔄 Endpoint non-protégé - Passage libre: {request.url.path}")
    
    # Ajouter une authentification optionnelle pour ces endpoints
    try:
        user_info = await optional_auth(request)
        if user_info:
            request.state.user = user_info
            logger.debug(f"🔍 Optional auth successful for {request.url.path}")
    except Exception:
        # Ignorer les erreurs d'auth optionnelle
        pass
    
    return await call_next(request)

# 🆕 FONCTION UTILITAIRE POUR LES ENDPOINTS
def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Récupère l'utilisateur authentifié depuis request.state
    À utiliser dans les endpoints qui nécessitent une authentification
    
    Args:
        request: Request FastAPI
        
    Returns:
        Dict: Informations utilisateur
        
    Raises:
        HTTPException: Si pas d'utilisateur authentifié
    """
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return request.state.user

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Récupère l'utilisateur authentifié si disponible, sinon None
    À utiliser dans les endpoints avec authentification optionnelle
    
    Args:
        request: Request FastAPI
        
    Returns:
        Optional[Dict]: Informations utilisateur ou None
    """
    return getattr(request.state, 'user', None)

# 🔧 FONCTION DE DEBUG
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
        "sample_public_endpoints": list(PUBLIC_ENDPOINTS)[:5],
        "sample_protected_patterns": PROTECTED_PATTERNS[:5],
        "middleware_version": "2.0-auth-enhanced"
    }