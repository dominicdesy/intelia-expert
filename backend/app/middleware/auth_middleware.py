# app/middleware/auth_middleware.py
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

# Import de la fonction d'auth existante
from app.api.v1.auth import get_current_user, security

logger = logging.getLogger(__name__)

# Liste des endpoints publics (pas d'auth requise)
PUBLIC_ENDPOINTS = {
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
    "/api/v1/auth/login",
    "/api/v1/auth/debug/jwt-config",
    "/api/v1/conversations/test-public",
    "/api/v1/conversations/test-public-post",
    # Endpoints sans prefix /api aussi
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
    "/metrics",  # 🆕 Endpoint de monitoring
    "/admin/stats",  # 🆕 Stats admin
    "/health/complete",  # 🆕 Health check complet
    "/auth/login",
    "/auth/debug/jwt-config",
    "/v1/conversations/test-public",
    "/v1/conversations/test-public-post"
}

# 🔧 NOUVEAUX PATTERNS D'AUTHENTIFICATION SÉCURISÉE
PROTECTED_PATTERNS = [
    "/api/v1/billing/",           # 🔒 Billing nécessite auth
    "/api/v1/logging/analytics/", # 🔒 Analytics nécessitent auth
    "/api/v1/conversations/",     # 🔒 Conversations nécessitent auth
    "/api/v1/expert/ask",         # 🔒 Expert ask nécessite auth
    "/api/v1/admin/",             # 🔒 Admin nécessite auth
    "/api/v1/invitations/",       # 🔒 Invitations nécessitent auth
]

# 🆕 PATTERNS D'ENDPOINTS INEXISTANTS (pour retourner 404 au lieu de 405)
NONEXISTENT_PATTERNS = [
    "/api/v1/analytics/",         # ❌ N'existe pas - doit retourner 404
    "/api/v1/user/",              # ❌ N'existe pas - doit retourner 404
    "/api/v1/stats/",             # ❌ N'existe pas - doit retourner 404
]

async def verify_supabase_token(request: Request) -> Dict[str, Any]:
    """
    Wrapper pour utiliser la logique d'auth existante dans api/v1/auth.py
    """
    try:
        # Extraire le token Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        # Créer l'objet credentials comme attendu par get_current_user
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.replace("Bearer ", "")
        )
        
        # Utiliser la fonction existante
        user_info = await get_current_user(credentials)
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """Authentification optionnelle - ne lève pas d'erreur si pas de token"""
    try:
        return await verify_supabase_token(request)
    except:
        return None

def is_public_endpoint(path: str) -> bool:
    """Vérifie si un endpoint est public"""
    # Endpoints exacts
    if path in PUBLIC_ENDPOINTS:
        return True
    
    # Patterns pour endpoints publics
    public_patterns = [
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/health",
        "/metrics",
        "/auth/",
        "/static/",
        # Patterns avec prefix /api
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json", 
        "/api/v1/auth/",
        "/api/rag/",
        "/api/cors-test",
        "/api/v1/system-status",
        "/api/v1/debug",
        "/api/v1/ask-public",
        "/api/v1/conversations/test-public",
        "/v1/conversations/test-public"
    ]
    
    return any(path.startswith(pattern) for pattern in public_patterns)

def is_protected_endpoint(path: str) -> bool:
    """Vérifie si un endpoint nécessite une authentification"""
    return any(path.startswith(pattern) for pattern in PROTECTED_PATTERNS)

def is_nonexistent_endpoint(path: str) -> bool:
    """Vérifie si c'est un endpoint qui n'existe pas (pour retourner 404)"""
    return any(path.startswith(pattern) for pattern in NONEXISTENT_PATTERNS)

async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification globale CORRIGÉ
    """
    
    # 📝 LOG DE DEBUG
    logger.debug(f"🔍 Auth middleware - Path: {request.url.path}, Method: {request.method}")
    
    # 🚨 CORRECTION CRITIQUE : Gérer les endpoints inexistants AVANT toute autre logique
    if is_nonexistent_endpoint(request.url.path):
        logger.debug(f"❌ Endpoint inexistant détecté: {request.url.path}")
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found", "error": "endpoint_not_found"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    
    # ✅ Skip l'auth pour les endpoints publics et OPTIONS
    if is_public_endpoint(request.url.path) or request.method == "OPTIONS":
        logger.debug(f"✅ Public endpoint ou OPTIONS - Skip auth: {request.url.path}")
        return await call_next(request)
    
    # 🔒 Vérifier l'auth pour les endpoints protégés
    if is_protected_endpoint(request.url.path):
        try:
            user_info = await verify_supabase_token(request)
            
            # Ajouter les infos utilisateur à la request
            request.state.user = user_info
            
            logger.debug(f"✅ Utilisateur authentifié: {user_info.get('email')} pour {request.url.path}")
            
        except HTTPException as e:
            logger.debug(f"❌ Auth failed pour {request.url.path}: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail, "error": "authentication_failed"},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication failed", "error": "internal_auth_error"},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH", 
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Session-ID, Accept, Origin, User-Agent",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
    
    # 🔄 Pour tous les autres endpoints (non protégés, non publics), laisser passer
    # FastAPI gérera naturellement les 404 pour les routes qui n'existent pas
    logger.debug(f"🔄 Endpoint non-protégé - Passage libre: {request.url.path}")
    return await call_next(request)