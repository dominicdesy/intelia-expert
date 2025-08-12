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
    "/auth/login",
    "/auth/debug/jwt-config"
}

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
        "/api/v1/ask-public"
    ]
    
    return any(path.startswith(pattern) for pattern in public_patterns)

async def auth_middleware(request: Request, call_next):
    """
    Middleware d'authentification globale
    Utilise la logique d'auth existante de api/v1/auth.py
    """
    
    # Skip l'auth pour les endpoints publics et OPTIONS
    if is_public_endpoint(request.url.path) or request.method == "OPTIONS":
        return await call_next(request)
    
    # Vérifier l'auth pour les autres endpoints
    try:
        user_info = await verify_supabase_token(request)
        
        # Ajouter les infos utilisateur à la request
        request.state.user = user_info
        
        logger.debug(f"✅ Utilisateur authentifié: {user_info.get('email')} pour {request.url.path}")
        
    except HTTPException as e:
        # Retourner une réponse JSON avec les bons headers CORS
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
    
    return await call_next(request)