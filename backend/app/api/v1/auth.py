import os
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

# Optional Supabase import
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)

# ✅ CORRECTION: JWT configuration avec fallbacks robustes
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Fallback 1: Utiliser Supabase JWT secret
    JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
    
if not JWT_SECRET:
    # Fallback 2: Utiliser Supabase anon key comme base
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if supabase_key:
        JWT_SECRET = f"fallback_{supabase_key[:32]}"
        logger.warning("⚠️ Utilisation Supabase anon key comme JWT secret fallback")
    
if not JWT_SECRET:
    # Fallback 3: Secret par défaut pour développement (UNIQUEMENT)
    JWT_SECRET = "development-secret-change-in-production-12345"
    logger.error("❌ Aucun JWT_SECRET configuré, utilisation secret de développement")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

security = HTTPBearer()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return a JWT access token.
    """
    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client not available")
        raise HTTPException(status_code=500, detail="Authentication service unavailable")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    try:
        result = supabase.auth.sign_in(email=request.email, password=request.password)
    except Exception as e:
        logger.error("Supabase sign-in error: %s", e)
        raise HTTPException(status_code=500, detail="Authentication error")

    user = result.user
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"user_id": user.id, "email": request.email}, expires)
    return {"access_token": token, "expires_at": datetime.utcnow() + expires}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    ✅ CORRECTION: Decode JWT avec gestion d'erreur améliorée
    """
    token = credentials.credentials
    
    # ✅ VÉRIFICATION: JWT_SECRET existe
    if not JWT_SECRET:
        logger.error("❌ JWT_SECRET non configuré")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT configuration error")
    
    try:
        # ✅ VÉRIFICATION: Token n'est pas vide
        if not token or not isinstance(token, str):
            logger.warning("⚠️ Token vide ou invalide")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing or invalid")
        
        # ✅ CORRECTION: Decode avec JWT_SECRET garanti non-None
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        user_data = {
            "user_id": payload.get("user_id") or payload.get("sub"),
            "email": payload.get("email")
        }
        
        # ✅ VÉRIFICATION: Données utilisateur valides
        if not user_data.get("user_id"):
            logger.warning("⚠️ Token sans user_id valide")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
        return user_data
        
    except jwt.ExpiredSignatureError:
        logger.warning("⚠️ Token expiré")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.warning("⚠️ Token invalide")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Erreur JWT inattendue: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication error")

class DeleteDataResponse(BaseModel):
    success: bool
    message: str
    note: Optional[str]
    timestamp: datetime

@router.post("/delete-data", response_model=DeleteDataResponse)
async def delete_user_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Request data deletion for GDPR compliance.
    """
    user_id = current_user["user_id"]
    user_email = current_user["email"]
    logger.info("GDPR deletion requested for %s (%s)", user_email, user_id)
    # Here enqueue deletion job or log for manual process
    return {
        "success": True,
        "message": "Demande de suppression enregistrée",
        "note": "Vos données seront supprimées sous 30 jours",
        "timestamp": datetime.utcnow()
    }