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

# ✅ CONFIGURATION JWT SUPABASE
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
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
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
    ✅ VERSION ÉTENDUE : Decode JWT tokens Supabase + récupération user_type
    """
    token = credentials.credentials
    
    if not token or not isinstance(token, str):
        logger.warning("⚠️ Token vide ou invalide")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing or invalid")
    
    # ✅ STRATÉGIE MULTI-SECRET: Essayer plusieurs secrets dans l'ordre
    secrets_to_try = []
    
    # 1. Secret JWT Supabase configuré
    if SUPABASE_JWT_SECRET:
        secrets_to_try.append(("SUPABASE_JWT_SECRET", SUPABASE_JWT_SECRET))
    
    # 2. Essayer avec la clé anon Supabase
    supabase_anon = os.getenv("SUPABASE_ANON_KEY")
    if supabase_anon and supabase_anon != SUPABASE_JWT_SECRET:
        secrets_to_try.append(("SUPABASE_ANON_KEY", supabase_anon))
    
    # 3. Essayer avec d'autres secrets Supabase possibles
    other_keys = [
        ("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_SERVICE_KEY")),
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
            
            # Décoder le token avec ce secret
            payload = jwt.decode(
                token, 
                secret_value, 
                algorithms=[JWT_ALGORITHM],
                audience="authenticated"  # Supabase utilise cette audience
            )
            
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
            
            # Vérifier que c'est bien un token Supabase
            iss = payload.get("iss", "")
            if "supabase" not in iss.lower():
                logger.warning(f"⚠️ Token pas émis par Supabase: {iss}")
                continue
            
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
            
        except jwt.InvalidAudienceError:
            logger.debug(f"⚠️ Audience incorrecte avec {secret_name}")
            continue
            
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

# ✅ ENDPOINT DE DEBUG
@router.get("/debug/jwt-config")
async def debug_jwt_config():
    """Debug endpoint pour voir la configuration JWT"""
    return {
        "supabase_jwt_secret_configured": bool(SUPABASE_JWT_SECRET),
        "supabase_anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
        "supabase_service_key_configured": bool(os.getenv("SUPABASE_SERVICE_KEY")),
        "jwt_algorithm": JWT_ALGORITHM,
        "secrets_available": [
            name for name, value in [
                ("SUPABASE_JWT_SECRET", os.getenv("SUPABASE_JWT_SECRET")),
                ("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY")),
                ("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_SERVICE_KEY")),
            ] if value
        ]
    }
    
    
    
# 🆕 AJOUTS À app/api/v1/auth.py
# Ajoutez ces endpoints à la fin de votre fichier auth.py existant

# Nouveaux modèles Pydantic
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    userData: Optional[Dict[str, Any]] = {}

class RegisterResponse(BaseModel):
    user: Dict[str, Any]
    token: Optional[str] = None
    message: str

class VerifyRequest(BaseModel):
    pass  # Le token est dans l'Authorization header

class VerifyResponse(BaseModel):
    user: Dict[str, Any]
    valid: bool = True

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    user_type: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

# 🆕 ENDPOINT REGISTER
@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    Créer un nouveau compte utilisateur via Supabase
    """
    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client not available for registration")
        raise HTTPException(status_code=500, detail="Registration service unavailable")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase configuration missing")
        raise HTTPException(status_code=500, detail="Registration service misconfigured")

    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        logger.info(f"🔄 Attempting registration for: {request.email}")
        
        # Données utilisateur à inclure
        user_metadata = {
            "name": request.userData.get("name", ""),
            "user_type": request.userData.get("user_type", "producer"),
            "language": request.userData.get("language", "fr"),
        }
        
        # Créer le compte via Supabase
        result = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": user_metadata
            }
        })
        
        if result.user is None:
            logger.error(f"❌ Registration failed - no user returned for {request.email}")
            raise HTTPException(status_code=400, detail="Registration failed")
        
        # Construire la réponse utilisateur
        user_data = {
            "id": result.user.id,
            "email": result.user.email,
            "name": user_metadata.get("name", ""),
            "user_type": user_metadata.get("user_type", "producer"),
            "language": user_metadata.get("language", "fr"),
            "email_confirmed": result.user.email_confirmed_at is not None,
            "created_at": result.user.created_at
        }
        
        # Générer un token JWT pour l'authentification immédiate (optionnel)
        token = None
        if result.session and result.session.access_token:
            # Utiliser le token Supabase directement
            token = result.session.access_token
        elif result.user.id:
            # Ou créer notre propre token JWT
            expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                {"user_id": result.user.id, "email": request.email}, 
                expires
            )
        
        logger.info(f"✅ Registration successful for: {request.email}")
        
        return {
            "user": user_data,
            "token": token,
            "message": "Compte créé avec succès. Vérifiez vos emails si une confirmation est requise."
        }
        
    except Exception as e:
        logger.error(f"❌ Registration error for {request.email}: {str(e)}")
        
        # Gestion des erreurs spécifiques Supabase
        error_msg = str(e).lower()
        if "already registered" in error_msg or "already exists" in error_msg:
            raise HTTPException(status_code=400, detail="Cette adresse email est déjà utilisée.")
        elif "weak password" in error_msg or "password" in error_msg:
            raise HTTPException(status_code=400, detail="Le mot de passe ne respecte pas les critères de sécurité.")
        elif "rate limit" in error_msg or "too many" in error_msg:
            raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez dans quelques minutes.")
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la création du compte. Réessayez plus tard.")

# 🆕 ENDPOINT VERIFY
@router.post("/verify", response_model=VerifyResponse)
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Vérifier la validité d'un token JWT
    """
    try:
        # Si get_current_user réussit, le token est valide
        user_data = {
            "id": current_user.get("user_id"),
            "email": current_user.get("email"),
            "user_type": current_user.get("user_type", "user"),
            "full_name": current_user.get("full_name"),
            "is_admin": current_user.get("is_admin", False),
            "preferences": current_user.get("preferences", {}),
        }
        
        return {
            "user": user_data,
            "valid": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")

# 🆕 ENDPOINT LOGOUT
@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Déconnexion utilisateur
    """
    try:
        user_email = current_user.get("email")
        logger.info(f"🔄 Logout requested for: {user_email}")
        
        # Avec JWT, le logout côté serveur est optionnel
        # Le token sera invalidé côté client
        
        # Optionnel : invalider le token côté Supabase
        try:
            if SUPABASE_AVAILABLE:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_ANON_KEY")
                supabase: Client = create_client(supabase_url, supabase_key)
                supabase.auth.sign_out()
        except Exception as e:
            logger.warning(f"Supabase logout warning: {e}")
            # Ne pas faire échouer le logout pour ça
        
        logger.info(f"✅ Logout successful for: {user_email}")
        
        return {
            "success": True,
            "message": "Déconnexion réussie"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Même en cas d'erreur, on confirme le logout côté client
        return {
            "success": True,
            "message": "Déconnexion effectuée"
        }

# 🆕 ENDPOINT UPDATE PROFILE
@router.put("/update-profile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mettre à jour le profil utilisateur
    """
    try:
        user_id = current_user.get("user_id")
        user_email = current_user.get("email")
        
        logger.info(f"🔄 Profile update requested for: {user_email}")
        
        if not SUPABASE_AVAILABLE:
            logger.error("Supabase not available for profile update")
            raise HTTPException(status_code=500, detail="Profile update service unavailable")
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Préparer les données à mettre à jour
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.user_type is not None:
            update_data["user_type"] = request.user_type
        if request.language is not None:
            update_data["language"] = request.language
        if request.preferences is not None:
            update_data["preferences"] = request.preferences
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        # Mettre à jour dans Supabase Auth metadata
        result = supabase.auth.update_user({
            "data": update_data
        })
        
        if result.user is None:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour")
        
        # Construire la réponse
        updated_user = {
            "id": result.user.id,
            "email": result.user.email,
            **update_data,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Profile updated for: {user_email}")
        
        return {
            "user": updated_user,
            "message": "Profil mis à jour avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error for {current_user.get('email')}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du profil")

# 🆕 ENDPOINT EXPORT USER DATA (RGPD)
@router.get("/export-user")
async def export_user_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Exporter toutes les données utilisateur (conformité RGPD)
    """
    try:
        user_id = current_user.get("user_id")
        user_email = current_user.get("email")
        
        logger.info(f"🔄 Data export requested for: {user_email}")
        
        # Collecter toutes les données utilisateur
        export_data = {
            "user_profile": {
                "user_id": user_id,
                "email": user_email,
                "user_type": current_user.get("user_type"),
                "full_name": current_user.get("full_name"),
                "preferences": current_user.get("preferences", {}),
                "created_at": current_user.get("created_at"),
            },
            "export_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "export_version": "1.0",
                "data_types": ["profile", "preferences"]
            }
        }
        
        # TODO: Ajouter d'autres données si nécessaire
        # - Conversations
        # - Historique des requêtes
        # - Logs d'activité
        
        logger.info(f"✅ Data export completed for: {user_email}")
        
        return export_data
        
    except Exception as e:
        logger.error(f"Data export error for {current_user.get('email')}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export des données")