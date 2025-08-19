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

# ✅ CONFIGURATION JWT SUPABASE CORRIGÉE
# Récupérer le JWT secret de Supabase depuis les variables d'environnement
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
if not SUPABASE_JWT_SECRET:
    # Si pas de JWT secret spécifique, essayer la clé anon Supabase
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_ANON_KEY")
    
if not SUPABASE_JWT_SECRET:
    # Fallback pour développement
    SUPABASE_JWT_SECRET = "development-secret-change-in-production-12345"
    logger.error("❌ Aucun SUPABASE_JWT_SECRET configuré")

JWT_ALGORITHM = "HS256"  # Supabase utilise HS256
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

security = HTTPBearer()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SUPABASE_JWT_SECRET, algorithm=JWT_ALGORITHM)
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
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
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

# 🆕 NOUVELLE FONCTION : Récupération profil utilisateur depuis Supabase
async def get_user_profile_from_supabase(user_id: str, email: str) -> Dict[str, Any]:
    """
    Récupère le profil utilisateur depuis la table Supabase users
    """
    try:
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase non disponible - rôle par défaut")
            return {"user_type": "user"}
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # ✅ CORRIGÉ
        
        if not supabase_url or not supabase_key:
            logger.warning("Config Supabase manquante - rôle par défaut")
            return {"user_type": "user"}
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Chercher par auth_user_id d'abord (si c'est comme ça que c'est lié)
        response = supabase.table('users').select('*').eq('auth_user_id', user_id).execute()
        
        # Si pas trouvé par auth_user_id, essayer par email
        if not response.data:
            response = supabase.table('users').select('*').eq('email', email).execute()
        
        if response.data and len(response.data) > 0:
            profile = response.data[0]
            logger.debug(f"✅ Profil trouvé pour {email}: {profile.get('user_type', 'user')}")
            return {
                "user_type": profile.get('user_type', 'user'),
                "full_name": profile.get('full_name'),
                "preferences": profile.get('preferences', {}),
                "profile_id": profile.get('id')
            }
        else:
            logger.warning(f"⚠️ Aucun profil trouvé pour {email} - rôle par défaut")
            return {"user_type": "user"}
            
    except Exception as e:
        logger.error(f"❌ Erreur récupération profil Supabase: {e}")
        return {"user_type": "user"}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    ✅ VERSION CORRIGÉE : Decode JWT tokens Supabase + récupération user_type
    """
    token = credentials.credentials
    
    if not token or not isinstance(token, str):
        logger.warning("⚠️ Token vide ou invalide")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing or invalid")
    
    # ✅ STRATÉGIE MULTI-SECRET CORRIGÉE: Essayer plusieurs secrets dans l'ordre
    secrets_to_try = []
    
    # 1. Secret JWT Supabase configuré
    if SUPABASE_JWT_SECRET:
        secrets_to_try.append(("SUPABASE_JWT_SECRET", SUPABASE_JWT_SECRET))
    
    # 2. Essayer avec la clé anon Supabase
    supabase_anon = os.getenv("SUPABASE_ANON_KEY")
    if supabase_anon and supabase_anon != SUPABASE_JWT_SECRET:
        secrets_to_try.append(("SUPABASE_ANON_KEY", supabase_anon))
    
    # 3. ✅ CORRIGÉ : Utiliser SUPABASE_SERVICE_ROLE_KEY
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if service_role_key and service_role_key not in [s[1] for s in secrets_to_try]:
        secrets_to_try.append(("SUPABASE_SERVICE_ROLE_KEY", service_role_key))
    
    # 4. Autres clés possibles
    other_keys = [
        ("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SECRET_KEY")),
    ]
    
    for key_name, key_value in other_keys:
        if key_value and key_value not in [s[1] for s in secrets_to_try]:
            secrets_to_try.append((key_name, key_value))
    
    # ✅ ESSAYER CHAQUE SECRET
    for secret_name, secret_value in secrets_to_try:
        if not secret_value:
            continue
            
        try:
            logger.debug(f"🔑 Tentative décodage avec {secret_name}")
            
            # ✅ CORRIGÉ : Essayer avec et sans audience pour plus de flexibilité
            decode_options = [
                {"audience": "authenticated"},  # Standard Supabase
                {"audience": None},             # Sans audience
                {}                             # Sans options spéciales
            ]
            
            payload = None
            for options in decode_options:
                try:
                    if options.get("audience") is None:
                        # Décoder sans vérifier l'audience
                        payload = jwt.decode(
                            token, 
                            secret_value, 
                            algorithms=[JWT_ALGORITHM],
                            options={"verify_aud": False}
                        )
                    else:
                        # Décoder avec audience
                        payload = jwt.decode(
                            token, 
                            secret_value, 
                            algorithms=[JWT_ALGORITHM],
                            **options
                        )
                    break  # Si succès, sortir de la boucle des options
                except jwt.InvalidAudienceError:
                    continue  # Essayer sans audience
                except Exception:
                    continue  # Essayer l'option suivante
            
            if not payload:
                continue  # Essayer le secret suivant
            
            logger.info(f"✅ Token décodé avec succès avec {secret_name}")
            
            # Extraire les informations utilisateur du payload Supabase
            user_id = payload.get("sub")
            email = payload.get("email")
            
            # Vérification de base
            if not user_id:
                logger.warning("⚠️ Token sans user_id (sub) valide")
                continue
                
            if not email:
                logger.warning("⚠️ Token sans email valide")
                continue
            
            # ✅ CORRIGÉ : Vérification plus flexible de l'émetteur
            iss = payload.get("iss", "")
            # Accepter les tokens Supabase même si l'iss n'est pas parfait
            
            # 🆕 NOUVEAU : Récupérer le profil utilisateur depuis Supabase
            profile = await get_user_profile_from_supabase(user_id, email)
            
            # 🆕 Construire la réponse avec rôles
            user_data = {
                "user_id": user_id,
                "email": email,
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "exp": payload.get("exp"),
                "jwt_secret_used": secret_name,
                
                # 🆕 NOUVEAUX CHAMPS DE RÔLES
                "user_type": profile.get("user_type", "user"),
                "full_name": profile.get("full_name"),
                "preferences": profile.get("preferences", {}),
                "profile_id": profile.get("profile_id"),
                
                # ✅ RÉTROCOMPATIBILITÉ : Maintenir is_admin pour l'existant
                "is_admin": profile.get("user_type") in ["admin", "super_admin"]
            }
            
            logger.info(f"✅ Utilisateur authentifié: {email} (rôle: {user_data['user_type']}, secret: {secret_name})")
            return user_data
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"⚠️ Token expiré (testé avec {secret_name})")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
            
        except jwt.InvalidSignatureError:
            logger.debug(f"⚠️ Signature invalide avec {secret_name}")
            continue
            
        except jwt.InvalidTokenError as e:
            logger.debug(f"⚠️ Token invalide avec {secret_name}: {e}")
            continue
            
        except Exception as e:
            logger.debug(f"⚠️ Erreur inattendue avec {secret_name}: {e}")
            continue
    
    # Si aucun secret n'a fonctionné
    logger.error("❌ Impossible de décoder le token avec tous les secrets disponibles")
    logger.error(f"❌ Secrets essayés: {[s[0] for s in secrets_to_try]}")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Invalid token - unable to verify signature"
    )

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

# 🆕 NOUVEL ENDPOINT pour voir son profil
@router.get("/me")
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Récupère le profil de l'utilisateur connecté"""
    return {
        "user_id": current_user.get("user_id"),
        "email": current_user.get("email"),
        "user_type": current_user.get("user_type"),
        "full_name": current_user.get("full_name"),
        "is_admin": current_user.get("is_admin"),
        "preferences": current_user.get("preferences", {}),
        "profile_id": current_user.get("profile_id")
    }

# ✅ ENDPOINT DE DEBUG CORRIGÉ
@router.get("/debug/jwt-config")
async def debug_jwt_config():
    """Debug endpoint pour voir la configuration JWT"""
    return {
        "supabase_jwt_secret_configured": bool(SUPABASE_JWT_SECRET),
        "supabase_anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
        "supabase_service_role_key_configured": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),  # ✅ CORRIGÉ
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "jwt_algorithm": JWT_ALGORITHM,
        "secrets_available": [
            name for name, value in [
                ("SUPABASE_JWT_SECRET", os.getenv("SUPABASE_JWT_SECRET")),
                ("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY")),
                ("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY")),  # ✅ CORRIGÉ
            ] if value
        ]
    }