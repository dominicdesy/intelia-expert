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

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET")
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
    Decode JWT and return current user info.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"user_id": payload.get("user_id"), "email": payload.get("email")}
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        logger.warning("Invalid JWT token")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication credentials")


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
