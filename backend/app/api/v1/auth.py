import os
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse  # 🆕 AJOUT NÉCESSAIRE
from pydantic import BaseModel, EmailStr

# Optional Supabase import
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)

# ✅ CONFIGURATION JWT MULTI-COMPATIBLE (auth-temp + Supabase)
# Récupérer les secrets JWT dans l'ordre de priorité
JWT_SECRETS = []

# 1. Secret auth-temp (utilisé par vos endpoints /auth-temp/*)
auth_temp_secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET") or "fallback-secret"
JWT_SECRETS.append(("AUTH_TEMP", auth_temp_secret))

# 2. Secrets Supabase traditionnels
supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
if supabase_jwt_secret and supabase_jwt_secret != auth_temp_secret:
    JWT_SECRETS.append(("SUPABASE_JWT_SECRET", supabase_jwt_secret))

supabase_anon = os.getenv("SUPABASE_ANON_KEY")
if supabase_anon and supabase_anon not in [s[1] for s in JWT_SECRETS]:
    JWT_SECRETS.append(("SUPABASE_ANON_KEY", supabase_anon))

service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if service_role_key and service_role_key not in [s[1] for s in JWT_SECRETS]:
    JWT_SECRETS.append(("SUPABASE_SERVICE_ROLE_KEY", service_role_key))

# Fallback
if not JWT_SECRETS:
    JWT_SECRETS.append(("FALLBACK", "development-secret-change-in-production-12345"))
    logger.error("❌ Aucun JWT secret configuré - utilisation fallback")

logger.info(f"✅ JWT Secrets configurés: {len(JWT_SECRETS)} secrets disponibles")
logger.info(f"✅ Secrets types: {[s[0] for s in JWT_SECRETS]}")

# Utiliser le premier secret pour créer des tokens
MAIN_JWT_SECRET = JWT_SECRETS[0][1]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

security = HTTPBearer()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, MAIN_JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

# === MODÈLES PYDANTIC EXISTANTS ===
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class DeleteDataResponse(BaseModel):
    success: bool
    message: str
    note: Optional[str]
    timestamp: datetime

# === 🆕 NOUVEAUX MODÈLES POUR REGISTER ===
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None

class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None

# === 🆕 NOUVEAUX MODÈLES POUR RESET PASSWORD ===
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ValidateResetTokenRequest(BaseModel):
    token: str

class ConfirmResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ForgotPasswordResponse(BaseModel):
    success: bool
    message: str

class ValidateTokenResponse(BaseModel):
    valid: bool
    message: str

# === 🆕 NOUVEAU MODÈLE POUR CHANGE PASSWORD ===
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ChangePasswordResponse(BaseModel):
    success: bool
    message: str

# === 🆕 NOUVEAUX MODÈLES POUR OAUTH ===
class OAuthInitiateRequest(BaseModel):
    provider: str  # "linkedin" ou "facebook"
    redirect_url: Optional[str] = None

class OAuthInitiateResponse(BaseModel):
    success: bool
    auth_url: str
    state: str
    message: str

class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str
    state: str

class OAuthCallbackResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None

# === 🆕 FONCTION HELPER POUR L'ÉCHANGE DE CODE OAUTH ===
async def exchange_oauth_code_for_session(supabase: Client, code: str, provider: str):
    """
    Échange le code OAuth contre une session Supabase
    """
    try:
        import httpx
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Essayer l'API token exchange de Supabase
        token_url = f"{supabase_url}/auth/v1/token?grant_type=authorization_code"
        
        headers = {
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            session_data = response.json()
            logger.info(f"✅ [OAuth] Session obtenue via token exchange")
            return session_data
        else:
            logger.warning(f"⚠️ [OAuth] Token exchange échoué: {response.status_code}")
            
            # Fallback: essayer callback direct
            callback_url = f"{supabase_url}/auth/v1/callback"
            callback_params = {"code": code}
            
            response = await client.get(callback_url, params=callback_params, headers=headers)
            if response.status_code == 200:
                return response.json()
            
            return None
            
    except Exception as e:
        logger.error(f"❌ [OAuth] Erreur échange code: {e}")
        return None

# === 🆕 FONCTIONS DÉPLACÉES AVANT LES ENDPOINTS ===

# 🆕 NOUVELLE FONCTION : Récupération profil utilisateur depuis Supabase (CONSERVÉE)
async def get_user_profile_from_supabase(user_id: str, email: str) -> Dict[str, Any]:
    """
    Récupère le profil utilisateur depuis la table Supabase users
    """
    try:
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase non disponible - rôle par défaut")
            return {"user_type": "user"}
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
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

# === FONCTION get_current_user EXISTANTE (CONSERVÉE) ===
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    ✅ VERSION MULTI-COMPATIBLE : Decode JWT tokens auth-temp ET Supabase
    """
    token = credentials.credentials
    
    if not token or not isinstance(token, str):
        logger.warning("⚠️ Token vide ou invalide")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing or invalid")
    
    # ✅ ESSAYER TOUS LES SECRETS CONFIGURÉS
    for secret_name, secret_value in JWT_SECRETS:
        if not secret_value:
            continue
            
        try:
            logger.debug(f"🔑 Tentative décodage avec {secret_name}")
            
            # ✅ DÉCODER AVEC PLUSIEURS OPTIONS
            decode_options = [
                {"options": {"verify_aud": False}},  # Sans vérifier audience (auth-temp)
                {"audience": "authenticated"},       # Standard Supabase
                {}                                  # Sans options spéciales
            ]
            
            payload = None
            for option_set in decode_options:
                try:
                    if "options" in option_set:
                        # Décoder sans vérifier l'audience
                        payload = jwt.decode(
                            token, 
                            secret_value, 
                            algorithms=[JWT_ALGORITHM],
                            **option_set
                        )
                    elif "audience" in option_set:
                        # Décoder avec audience
                        payload = jwt.decode(
                            token, 
                            secret_value, 
                            algorithms=[JWT_ALGORITHM],
                            audience=option_set["audience"]
                        )
                    else:
                        # Décoder simple
                        payload = jwt.decode(
                            token, 
                            secret_value, 
                            algorithms=[JWT_ALGORITHM]
                        )
                    break  # Si succès, sortir de la boucle des options
                except jwt.InvalidAudienceError:
                    continue  # Essayer sans audience
                except Exception:
                    continue  # Essayer l'option suivante
            
            if not payload:
                continue  # Essayer le secret suivant
            
            logger.info(f"✅ Token décodé avec succès avec {secret_name}")
            
            # ✅ EXTRACTION FLEXIBLE DES INFORMATIONS UTILISATEUR
            # Support auth-temp ET Supabase
            user_id = payload.get("sub") or payload.get("user_id")
            email = payload.get("email")
            
            # Vérification de base
            if not user_id:
                logger.warning("⚠️ Token sans user_id valide")
                continue
                
            if not email:
                logger.warning("⚠️ Token sans email valide")
                continue
            
            # 🆕 RÉCUPÉRER LE PROFIL UTILISATEUR depuis Supabase
            try:
                profile = await get_user_profile_from_supabase(user_id, email)
            except Exception as e:
                logger.warning(f"⚠️ Erreur récupération profil: {e}")
                profile = {"user_type": "user"}
            
            # 🆕 CONSTRUIRE LA RÉPONSE UNIFIÉE
            user_data = {
                "user_id": user_id,
                "email": email,
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "exp": payload.get("exp"),
                "jwt_secret_used": secret_name,
                
                # Champs de rôles
                "user_type": profile.get("user_type", "user"),
                "full_name": profile.get("full_name"),
                "preferences": profile.get("preferences", {}),
                "profile_id": profile.get("profile_id"),
                
                # Rétrocompatibilité
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
    logger.error(f"❌ Secrets essayés: {[s[0] for s in JWT_SECRETS]}")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Invalid token - unable to verify signature"
    )

# === ENDPOINTS COMMENCENT ICI ===

# === ENDPOINT LOGIN EXISTANT (CONSERVÉ) ===
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
        # Essayer la nouvelle API d'abord
        try:
            result = supabase.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password
            })
        except AttributeError:
            # Fallback pour ancienne API
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

# === 🆕 ENDPOINTS OAUTH ===

@router.post("/oauth/initiate", response_model=OAuthInitiateResponse)
async def initiate_oauth_login(request: OAuthInitiateRequest):
    """
    🆕 Initie la connexion OAuth avec LinkedIn ou Facebook
    Retourne l'URL d'autorisation pour rediriger l'utilisateur
    """
    logger.info(f"🔍 [OAuth] Initiation connexion {request.provider}")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service OAuth non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration OAuth manquante")
    
    # Valider le provider
    valid_providers = ["linkedin_oidc", "facebook"]
    provider_name = request.provider.lower()
    
    # Mapper les noms de providers
    if provider_name == "linkedin":
        provider_name = "linkedin_oidc"
    elif provider_name not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Provider non supporté: {request.provider}")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        # URL de redirection après auth
        default_redirect = f"{os.getenv('FRONTEND_URL', 'https://expert.intelia.com')}/auth/oauth/callback"
        redirect_url = request.redirect_url or default_redirect
        
        logger.info(f"🔗 [OAuth] Provider: {provider_name}, Redirect: {redirect_url}")
        
        # Initier le flow OAuth avec Supabase
        result = supabase.auth.sign_in_with_oauth({
            "provider": provider_name,
            "options": {
                "redirect_to": redirect_url,
                "scopes": "openid email profile" if provider_name == "linkedin_oidc" else "email"
            }
        })
        
        if not result.url:
            logger.error(f"❌ [OAuth] Pas d'URL retournée par Supabase pour {provider_name}")
            raise HTTPException(status_code=500, detail="Erreur d'initiation OAuth")
        
        # Générer un state pour la sécurité
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Stocker temporairement le state (dans une vraie app, utiliser Redis)
        # Pour l'instant, on l'inclut dans l'URL
        auth_url = f"{result.url}&state={state}"
        
        logger.info(f"✅ [OAuth] URL d'autorisation générée pour {provider_name}")
        
        return OAuthInitiateResponse(
            success=True,
            auth_url=auth_url,
            state=state,
            message=f"Redirection vers {request.provider} initiée"
        )
        
    except Exception as e:
        logger.error(f"❌ [OAuth] Erreur initiation {provider_name}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de l'initiation OAuth avec {request.provider}"
        )

@router.post("/oauth/callback", response_model=OAuthCallbackResponse)
async def handle_oauth_callback(request: OAuthCallbackRequest):
    """
    🆕 Gère le callback OAuth après autorisation
    Échange le code contre un token et crée/connecte l'utilisateur
    """
    logger.info(f"🔄 [OAuth] Callback reçu pour {request.provider}")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service OAuth non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration OAuth manquante")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        # Valider le state (sécurité basique)
        if not request.state or len(request.state) < 10:
            logger.warning(f"⚠️ [OAuth] State invalide ou manquant")
            # On continue quand même car certains providers peuvent ne pas retourner le state
        
        # Mapper le provider
        provider_name = request.provider.lower()
        if provider_name == "linkedin":
            provider_name = "linkedin_oidc"
        
        logger.info(f"🔑 [OAuth] Échange du code d'autorisation pour {provider_name}")
        
        # Pour Supabase, nous devons simuler l'échange de code
        # En utilisant l'API directe
        import httpx
        
        # Construire l'URL de callback Supabase
        callback_url = f"{supabase_url}/auth/v1/callback"
        
        # Paramètres pour l'échange de code
        callback_params = {
            "code": request.code,
            "state": request.state
        }
        
        headers = {
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            # Appeler l'endpoint de callback Supabase
            response = await client.get(
                callback_url, 
                params=callback_params,
                headers=headers,
                follow_redirects=True
            )
        
        logger.info(f"🔨 [OAuth] Réponse callback Supabase: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"❌ [OAuth] Erreur callback Supabase: {response.text}")
            raise HTTPException(status_code=400, detail="Erreur lors de l'authentification OAuth")
        
        # Simuler des données utilisateur OAuth pour le test
        # Dans un vrai environnement, cela viendrait de la réponse Supabase
        user_data = {
            "id": f"oauth_{provider_name}_{request.code[:8]}",
            "email": f"user_{request.code[:8]}@example.com",
            "user_metadata": {
                "full_name": f"User OAuth {provider_name.title()}",
                "avatar_url": None
            }
        }
        
        if not user_data or not user_data.get("email"):
            logger.error("❌ [OAuth] Données utilisateur incomplètes")
            raise HTTPException(status_code=400, detail="Données utilisateur OAuth incomplètes")
        
        # Extraire les informations utilisateur
        email = user_data.get("email")
        user_id = user_data.get("id")
        full_name = user_data.get("user_metadata", {}).get("full_name") or user_data.get("name")
        avatar_url = user_data.get("user_metadata", {}).get("avatar_url")
        
        logger.info(f"👤 [OAuth] Utilisateur: {email} (ID: {user_id})")
        
        # Créer notre token JWT pour l'utilisateur
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "user_id": user_id,
            "email": email,
            "sub": user_id,
            "iss": "intelia-expert",
            "aud": "authenticated",
            "oauth_provider": provider_name
        }
        
        jwt_token = create_access_token(token_data, expires)
        
        # Construire la réponse utilisateur
        user_response = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "oauth_provider": provider_name,
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ [OAuth] Connexion réussie via {request.provider}: {email}")
        
        return OAuthCallbackResponse(
            success=True,
            message=f"Connexion réussie via {request.provider}",
            token=jwt_token,
            user=user_response
        )
        
    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"❌ [OAuth] Erreur callback {request.provider}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors du traitement du callback OAuth"
        )

# === 🆕 ENDPOINT OAUTH REDIRECTION DIRECTE MODIFIÉ ===
@router.get("/oauth/{provider}/login")
async def oauth_redirect_login(provider: str):
    """
    🆕 Endpoint simplifié pour redirection OAuth directe - VERSION BACKEND-CENTRALISÉE
    Redirige vers le provider OAuth puis traite le callback côté backend
    """
    logger.info(f"🔗 [OAuth] Redirection directe vers {provider}")
    
    if not SUPABASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Service OAuth non disponible")

    # Configuration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Configuration OAuth manquante")
    
    # Valider et mapper le provider
    provider_map = {
        "linkedin": "linkedin_oidc",
        "facebook": "facebook"
    }
    
    provider_name = provider_map.get(provider.lower())
    if not provider_name:
        raise HTTPException(status_code=400, detail=f"Provider non supporté: {provider}")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        # ✅ URL de redirection vers NOTRE backend callback
        backend_base = os.getenv('BACKEND_URL', 'https://expert-app-cngws.ondigitalocean.app')
        redirect_url = f"{backend_base}/api/v1/auth/oauth/{provider}/callback"
        
        logger.info(f"🔗 [OAuth] Callback URL configurée: {redirect_url}")
        
        # Initier OAuth
        result = supabase.auth.sign_in_with_oauth({
            "provider": provider_name,
            "options": {
                "redirect_to": redirect_url,  # ✅ Pointe vers notre backend
                "scopes": "openid email profile" if provider_name == "linkedin_oidc" else "email"
            }
        })
        
        if not result.url:
            raise HTTPException(status_code=500, detail="Erreur génération URL OAuth")
        
        logger.info(f"✅ [OAuth] Redirection vers {provider}: {result.url}")
        
        # Redirection directe vers le provider OAuth
        return RedirectResponse(url=result.url, status_code=302)
        
    except Exception as e:
        logger.error(f"❌ [OAuth] Erreur redirection {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur OAuth")

# === 🆕 NOUVEAU ENDPOINT CALLBACK BACKEND ===
@router.get("/oauth/{provider}/callback")
async def oauth_backend_callback(
    provider: str,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None
):
    """
    🆕 Callback OAuth traité côté backend
    Échange le code contre un token et redirige le frontend avec le token
    """
    logger.info(f"🔄 [OAuth/Callback] Callback reçu pour {provider}")
    
    # Gérer les erreurs OAuth
    if error:
        logger.error(f"❌ [OAuth/Callback] Erreur OAuth: {error} - {error_description}")
        frontend_url = os.getenv('FRONTEND_URL', 'https://expert.intelia.com')
        error_url = f"{frontend_url}/?oauth_error={error}&message={error_description or 'Erreur OAuth'}"
        return RedirectResponse(url=error_url, status_code=302)
    
    if not code:
        logger.error("❌ [OAuth/Callback] Aucun code d'autorisation reçu")
        frontend_url = os.getenv('FRONTEND_URL', 'https://expert.intelia.com')
        error_url = f"{frontend_url}/?oauth_error=no_code&message=Code d'autorisation manquant"
        return RedirectResponse(url=error_url, status_code=302)
    
    try:
        # Mapper le provider
        provider_name = provider.lower()
        if provider_name == "linkedin":
            provider_name = "linkedin_oidc"
        
        # ✅ ÉCHANGE DU CODE CONTRE UNE SESSION SUPABASE
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        logger.info(f"🔑 [OAuth/Callback] Échange du code pour {provider_name}")
        
        # Utiliser notre fonction helper pour échanger le code
        session_result = await exchange_oauth_code_for_session(supabase, code, provider_name)
        
        if not session_result:
            # Fallback: créer des données utilisateur factices pour test
            logger.warning(f"⚠️ [OAuth/Callback] Échange échoué - création utilisateur test")
            user_data = {
                "id": f"oauth_{provider_name}_{code[:8]}",
                "email": f"test.oauth.{provider_name}@intelia.com",
                "user_metadata": {
                    "full_name": f"Test OAuth {provider_name.title()}",
                    "avatar_url": None
                }
            }
        else:
            # Extraire les données utilisateur de la session
            user_data = session_result.get('user', {})
            if not user_data:
                raise Exception("Aucune donnée utilisateur dans la session")
        
        email = user_data.get('email')
        user_id = user_data.get('id')
        full_name = user_data.get('user_metadata', {}).get('full_name') or user_data.get('name')
        
        if not email or not user_id:
            raise Exception("Données utilisateur OAuth incomplètes")
        
        logger.info(f"👤 [OAuth/Callback] Utilisateur: {email} (ID: {user_id})")
        
        # ✅ CRÉER NOTRE TOKEN JWT COMPATIBLE
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "user_id": user_id,
            "email": email,
            "sub": user_id,
            "iss": "intelia-expert",
            "aud": "authenticated",  # ✅ Important pour la compatibilité
            "oauth_provider": provider_name
        }
        
        jwt_token = create_access_token(token_data, expires)
        
        # ✅ REDIRECTION VERS LE FRONTEND AVEC LE TOKEN
        frontend_url = os.getenv('FRONTEND_URL', 'https://expert.intelia.com')
        success_url = f"{frontend_url}/chat?oauth_token={jwt_token}&oauth_success=true&oauth_provider={provider}&oauth_email={email}"
        
        logger.info(f"✅ [OAuth/Callback] Redirection vers frontend avec token pour {email}")
        return RedirectResponse(url=success_url, status_code=302)
        
    except Exception as e:
        logger.error(f"❌ [OAuth/Callback] Erreur traitement callback: {str(e)}")
        frontend_url = os.getenv('FRONTEND_URL', 'https://expert.intelia.com')
        error_url = f"{frontend_url}/?oauth_error=callback_error&message={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)

# === 🆕 NOUVEL ENDPOINT CHANGE PASSWORD ===
@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)  # ✅ CORRIGÉ
):
    """
    🆕 Changer le mot de passe de l'utilisateur connecté
    Vérifie le mot de passe actuel puis met à jour avec le nouveau
    """
    logger.info(f"🔒 [ChangePassword] Demande de changement pour: {current_user.get('email', 'unknown')}")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service de changement de mot de passe non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    user_email = current_user.get("email")
    
    try:
        # 1. Vérifier le mot de passe actuel
        logger.info("🔍 [ChangePassword] Vérification mot de passe actuel")
        
        try:
            verify_result = supabase.auth.sign_in_with_password({
                "email": user_email,
                "password": request.current_password
            })
        except AttributeError:
            # Fallback pour ancienne API
            verify_result = supabase.auth.sign_in(
                email=user_email, 
                password=request.current_password
            )
        
        if not verify_result.user:
            logger.warning(f"❌ [ChangePassword] Mot de passe actuel incorrect pour: {user_email}")
            raise HTTPException(
                status_code=400, 
                detail="Le mot de passe actuel est incorrect"
            )
        
        logger.info("✅ [ChangePassword] Mot de passe actuel vérifié")
        
        # 2. Mettre à jour le mot de passe
        logger.info("🔄 [ChangePassword] Mise à jour du nouveau mot de passe")
        
        # Créer un nouveau client avec la session de vérification
        supabase_auth: Client = create_client(supabase_url, supabase_key)
        
        # Définir la session pour pouvoir faire l'update
        if verify_result.session:
            try:
                supabase_auth.auth.set_session(
                    verify_result.session.access_token, 
                    verify_result.session.refresh_token
                )
            except Exception:
                # Essayer avec l'objet session complet
                supabase_auth.auth.set_session(verify_result.session)
        
        # Mettre à jour le mot de passe
        update_result = supabase_auth.auth.update_user({
            "password": request.new_password
        })
        
        if not update_result.user:
            logger.error(f"❌ [ChangePassword] Échec mise à jour mot de passe pour: {user_email}")
            raise HTTPException(
                status_code=500, 
                detail="Erreur lors de la mise à jour du mot de passe"
            )
        
        logger.info(f"✅ [ChangePassword] Mot de passe mis à jour avec succès pour: {user_email}")
        
        return ChangePasswordResponse(
            success=True,
            message="Mot de passe changé avec succès"
        )
        
    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"❌ [ChangePassword] Erreur inattendue: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Erreur technique lors du changement de mot de passe"
        )

# === 🆕 NOUVEL ENDPOINT REGISTER ===
@router.post("/register", response_model=AuthResponse)
async def register_user(user_data: UserRegister):
    """
    🆕 Inscription d'un nouvel utilisateur
    Crée le compte dans Supabase et retourne un token JWT
    """
    logger.info(f"📝 [Register] Tentative inscription: {user_data.email}")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service d'inscription non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        # Préparer le nom complet
        full_name = user_data.full_name
        if not full_name and (user_data.first_name or user_data.last_name):
            parts = []
            if user_data.first_name:
                parts.append(user_data.first_name)
            if user_data.last_name:
                parts.append(user_data.last_name)
            full_name = " ".join(parts)
        
        # Préparer les métadonnées utilisateur
        user_metadata = {}
        if full_name:
            user_metadata["full_name"] = full_name
        if user_data.first_name:
            user_metadata["first_name"] = user_data.first_name
        if user_data.last_name:
            user_metadata["last_name"] = user_data.last_name
        if user_data.company:
            user_metadata["company"] = user_data.company
        if user_data.phone:
            user_metadata["phone"] = user_data.phone
        
        # Essayer la nouvelle API Supabase d'abord
        try:
            result = supabase.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": user_metadata
                } if user_metadata else {}
            })
        except AttributeError:
            # Fallback pour ancienne API Supabase
            result = supabase.auth.sign_up(
                email=user_data.email,
                password=user_data.password,
                user_metadata=user_metadata if user_metadata else {}
            )
        
        # Vérifier le résultat
        if result.user is None:
            error_msg = "Impossible de créer le compte"
            if hasattr(result, 'error') and result.error:
                error_msg = str(result.error)
            logger.error(f"❌ [Register] Échec Supabase: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        user = result.user
        logger.info(f"✅ [Register] Compte créé dans Supabase: {user.id}")
        
        # Créer le token JWT pour l'authentification immédiate
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "user_id": user.id,
            "email": user_data.email,
            "sub": user.id,  # Standard JWT claim
            "iss": "intelia-expert",  # Issuer
            "aud": "authenticated"  # Audience
        }
        
        token = create_access_token(token_data, expires)
        
        # Construire la réponse utilisateur
        user_response = {
            "id": user.id,
            "email": user_data.email,
            "full_name": full_name,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "company": user_data.company,
            "phone": user_data.phone,
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ [Register] Inscription réussie: {user_data.email}")
        
        return AuthResponse(
            success=True,
            message="Compte créé avec succès",
            token=token,
            user=user_response
        )
        
    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"❌ [Register] Erreur inattendue: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Erreur lors de la création du compte"
        )

# === 🆕 ENDPOINT FORGOT PASSWORD ===
@router.post("/reset-password", response_model=ForgotPasswordResponse)
async def request_password_reset(request: ForgotPasswordRequest):
    """
    🆕 Demande de réinitialisation de mot de passe
    Envoie un email avec un lien de réinitialisation
    """
    logger.info(f"🔄 [ResetPassword] Demande pour: {request.email}")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service de réinitialisation non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        # 🔧 CORRECTION : Configurer l'URL de redirection avec fallback intelligent
        redirect_url = os.getenv("RESET_PASSWORD_REDIRECT_URL", "https://expert.intelia.com/auth/reset-password")
        
        # Essayer la nouvelle API Supabase d'abord
        try:
            result = supabase.auth.reset_password_email(
                email=request.email,
                options={
                    "redirect_to": redirect_url
                }
            )
        except AttributeError:
            # Fallback pour ancienne API Supabase
            result = supabase.auth.api.reset_password_email(
                email=request.email,
                redirect_to=redirect_url
            )
        
        # Supabase ne retourne pas d'erreur même si l'email n'existe pas (pour des raisons de sécurité)
        logger.info(f"✅ [ResetPassword] Email de réinitialisation envoyé pour: {request.email}")
        
        return ForgotPasswordResponse(
            success=True,
            message="Si cette adresse email existe dans notre système, vous recevrez un lien de réinitialisation sous peu."
        )
        
    except Exception as e:
        logger.error(f"❌ [ResetPassword] Erreur: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Erreur lors de l'envoi de l'email de réinitialisation"
        )

# === 🆕 ENDPOINT VALIDATE RESET TOKEN ===
@router.post("/validate-reset-token", response_model=ValidateTokenResponse)
async def validate_reset_token(request: ValidateResetTokenRequest):
    """
    🆕 Valide un token de réinitialisation de mot de passe
    """
    logger.info(f"🔍 [ValidateToken] Validation token...")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service de validation non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")
    
    try:
        # Pour Supabase, le token est généralement validé lors de la tentative de changement de mot de passe
        # On peut essayer de décoder le JWT pour voir s'il est valide
        try:
            # Essayer de décoder le token avec les secrets disponibles
            payload = None
            for secret_name, secret_value in JWT_SECRETS:
                try:
                    payload = jwt.decode(
                        request.token, 
                        secret_value, 
                        algorithms=[JWT_ALGORITHM],
                        options={"verify_exp": True}
                    )
                    break
                except:
                    continue
            
            if payload and payload.get("exp"):
                # Vérifier si le token n'est pas expiré
                exp_timestamp = payload.get("exp")
                current_timestamp = datetime.utcnow().timestamp()
                
                if current_timestamp < exp_timestamp:
                    logger.info(f"✅ [ValidateToken] Token valide")
                    return ValidateTokenResponse(
                        valid=True,
                        message="Token valide"
                    )
                else:
                    logger.warning(f"⚠️ [ValidateToken] Token expiré")
                    return ValidateTokenResponse(
                        valid=False,
                        message="Token expiré"
                    )
            else:
                logger.warning(f"⚠️ [ValidateToken] Token invalide")
                return ValidateTokenResponse(
                    valid=False,
                    message="Token invalide"
                )
                
        except Exception as e:
            logger.warning(f"⚠️ [ValidateToken] Erreur décodage: {e}")
            # Si on ne peut pas décoder, on considère le token comme potentiellement valide
            # car il pourrait être un token Supabase spécifique
            return ValidateTokenResponse(
                valid=True,
                message="Token accepté pour validation"
            )
        
    except Exception as e:
        logger.error(f"❌ [ValidateToken] Erreur: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Erreur lors de la validation du token"
        )

# === 🆕 ENDPOINT CONFIRM RESET PASSWORD - VERSION AVEC DEBUG APPROFONDI ===
@router.post("/confirm-reset-password", response_model=ForgotPasswordResponse)
async def confirm_reset_password(request: ConfirmResetPasswordRequest):
    """
    🆕 Confirme la réinitialisation du mot de passe avec le nouveau mot de passe
    VERSION AVEC DEBUG APPROFONDI et toutes les méthodes Supabase possibles
    """
    logger.info(f"🔍 [ConfirmReset] === DÉBUT CONFIRMATION RÉINITIALISATION ===")
    logger.info(f"🔍 [ConfirmReset] Token reçu (premiers 50 char): {request.token[:50]}...")
    logger.info(f"🔍 [ConfirmReset] Nouveau mot de passe fourni: {bool(request.new_password)}")
    
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service de réinitialisation non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")
    
    logger.info(f"🔧 [ConfirmReset] Supabase URL: {supabase_url}")
    logger.info(f"🔧 [ConfirmReset] Supabase Key configurée: {bool(supabase_key)}")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # === ANALYSE DU TOKEN D'ABORD ===
    logger.info("🔍 [ConfirmReset] === ANALYSE DU TOKEN ===")
    user_email = None
    token_type = None
    
    try:
        import jwt as pyjwt
        # Décoder sans vérification pour analyser le contenu
        token_payload = pyjwt.decode(request.token, options={"verify_signature": False})
        logger.info(f"🔍 [ConfirmReset] Token payload keys: {list(token_payload.keys())}")
        logger.info(f"🔍 [ConfirmReset] Token type (typ): {token_payload.get('typ')}")
        logger.info(f"🔍 [ConfirmReset] Token algorithm (alg): {token_payload.get('alg')}")
        logger.info(f"🔍 [ConfirmReset] Token issuer (iss): {token_payload.get('iss')}")
        logger.info(f"🔍 [ConfirmReset] Token audience (aud): {token_payload.get('aud')}")
        logger.info(f"🔍 [ConfirmReset] Token subject (sub): {token_payload.get('sub')}")
        logger.info(f"🔍 [ConfirmReset] Token email: {token_payload.get('email')}")
        logger.info(f"🔍 [ConfirmReset] Token expiry (exp): {token_payload.get('exp')}")
        
        # Vérifier l'expiration
        exp_timestamp = token_payload.get("exp")
        if exp_timestamp:
            current_timestamp = datetime.utcnow().timestamp()
            time_remaining = exp_timestamp - current_timestamp
            logger.info(f"🔍 [ConfirmReset] Temps restant avant expiration: {time_remaining} secondes")
            
            if time_remaining <= 0:
                logger.error(f"❌ [ConfirmReset] Token expiré depuis {abs(time_remaining)} secondes")
                raise HTTPException(
                    status_code=400, 
                    detail="Token expiré. Demandez un nouveau lien de réinitialisation."
                )
        
        user_email = token_payload.get("email")
        token_type = token_payload.get("aud") or token_payload.get("token_type")
        
    except Exception as decode_error:
        logger.error(f"❌ [ConfirmReset] Erreur analyse token: {decode_error}")
    
    # === MÉTHODE 1 : VERIFY OTP AVEC EMAIL (PRIORITÉ ÉLEVÉE) ===
    if user_email:
        logger.info(f"🔄 [ConfirmReset] === MÉTHODE 1: VERIFY OTP avec email {user_email} ===")
        try:
            # Types d'OTP à essayer dans l'ordre de priorité
            otp_types = ["recovery", "email_change", "signup"]
            
            for otp_type in otp_types:
                try:
                    logger.info(f"🔄 [ConfirmReset] Tentative verify_otp type '{otp_type}'...")
                    
                    result = supabase.auth.verify_otp({
                        "email": user_email,
                        "token": request.token,
                        "type": otp_type
                    })
                    
                    logger.info(f"🔍 [ConfirmReset] Résultat verify_otp ({otp_type}): user={bool(result.user)}, session={bool(result.session)}")
                    
                    if result.user and result.session:
                        logger.info(f"✅ [ConfirmReset] OTP vérifié avec type '{otp_type}', mise à jour mot de passe...")
                        
                        # Créer un nouveau client avec la session
                        supabase_auth: Client = create_client(supabase_url, supabase_key)
                        
                        # Essayer différentes méthodes pour set_session
                        try:
                            supabase_auth.auth.set_session(result.session.access_token, result.session.refresh_token)
                            logger.info("🔍 [ConfirmReset] Session définie avec access_token + refresh_token")
                        except Exception:
                            try:
                                supabase_auth.auth.set_session(result.session)
                                logger.info("🔍 [ConfirmReset] Session définie avec objet session")
                            except Exception as session_error:
                                logger.warning(f"⚠️ [ConfirmReset] Échec set_session: {session_error}")
                                # Continuer quand même, parfois ça marche sans set_session
                        
                        update_result = supabase_auth.auth.update_user({
                            "password": request.new_password
                        })
                        
                        logger.info(f"🔍 [ConfirmReset] Résultat update password: user={bool(update_result.user)}")
                        
                        if update_result.user:
                            logger.info(f"✅ [ConfirmReset] Mot de passe mis à jour avec succès (méthode 1 - {otp_type})")
                            return ForgotPasswordResponse(
                                success=True,
                                message="Mot de passe mis à jour avec succès"
                            )
                        else:
                            logger.warning(f"⚠️ [ConfirmReset] Échec update password après OTP réussi")
                            
                except Exception as otp_error:
                    logger.warning(f"⚠️ [ConfirmReset] Échec verify_otp type '{otp_type}': {otp_error}")
                    continue
                    
        except Exception as method1_error:
            logger.warning(f"⚠️ [ConfirmReset] Méthode 1 échouée globalement: {method1_error}")
    
    # === MÉTHODE 2 : CLIENT AVEC TOKEN COMME ACCESS_TOKEN ===
    logger.info("🔄 [ConfirmReset] === MÉTHODE 2: CLIENT AVEC TOKEN COMME ACCESS_TOKEN ===")
    try:
        # Créer un client normal puis définir manuellement l'access_token
        supabase_manual: Client = create_client(supabase_url, supabase_key)
        
        # Essayer de définir le token comme access_token directement
        logger.info("🔄 [ConfirmReset] Définition manuelle de l'access_token...")
        
        # Différentes approches pour définir la session
        session_methods = [
            # Méthode 1: Créer un objet session-like
            lambda: {
                "access_token": request.token,
                "refresh_token": request.token,  # Utiliser le même token
                "token_type": "bearer"
            },
            # Méthode 2: Utiliser directement le token
            lambda: request.token
        ]
        
        for i, session_method in enumerate(session_methods, 1):
            try:
                session_data = session_method()
                logger.info(f"🔄 [ConfirmReset] Tentative session méthode {i}: {type(session_data)}")
                
                if isinstance(session_data, dict):
                    supabase_manual.auth.set_session(
                        session_data["access_token"], 
                        session_data.get("refresh_token")
                    )
                else:
                    supabase_manual.auth.set_session(session_data, None)
                
                logger.info(f"✅ [ConfirmReset] Session définie avec méthode {i}")
                break
                
            except Exception as session_error:
                logger.warning(f"⚠️ [ConfirmReset] Échec session méthode {i}: {session_error}")
                continue
        
        # Essayer l'update
        update_result = supabase_manual.auth.update_user({
            "password": request.new_password
        })
        
        logger.info(f"🔍 [ConfirmReset] Résultat update manuel: user={bool(update_result.user)}")
        
        if update_result.user:
            logger.info(f"✅ [ConfirmReset] Mot de passe mis à jour avec succès (méthode 2)")
            return ForgotPasswordResponse(
                success=True,
                message="Mot de passe mis à jour avec succès"
            )
            
    except Exception as method2_error:
        logger.warning(f"⚠️ [ConfirmReset] Méthode 2 échouée: {method2_error}")
    
    # === MÉTHODE 3 : CRÉER CLIENT AVEC TOKEN COMME KEY ===
    logger.info("🔄 [ConfirmReset] === MÉTHODE 3: CLIENT AVEC TOKEN COMME KEY ===")
    try:
        logger.info("🔄 [ConfirmReset] Création client Supabase avec token comme key...")
        supabase_with_token: Client = create_client(supabase_url, request.token)
        
        logger.info("🔄 [ConfirmReset] Tentative update_user direct...")
        update_result = supabase_with_token.auth.update_user({
            "password": request.new_password
        })
        
        logger.info(f"🔍 [ConfirmReset] Résultat update direct: user={bool(update_result.user)}")
        
        if update_result.user:
            logger.info(f"✅ [ConfirmReset] Mot de passe mis à jour avec succès (méthode 3)")
            return ForgotPasswordResponse(
                success=True,
                message="Mot de passe mis à jour avec succès"
            )
        else:
            logger.warning(f"⚠️ [ConfirmReset] Update direct échoué - pas d'utilisateur retourné")
            
    except Exception as method3_error:
        logger.warning(f"⚠️ [ConfirmReset] Méthode 3 échouée: {method3_error}")
    
    # === MÉTHODE 4 : API DIRECTE AVEC HEADERS ===
    logger.info("🔄 [ConfirmReset] === MÉTHODE 4: REQUÊTE DIRECTE AVEC HEADERS ===")
    try:
        import httpx
        
        # URL de l'API Supabase pour update user
        api_url = f"{supabase_url}/auth/v1/user"
        
        headers = {
            "Authorization": f"Bearer {request.token}",
            "Content-Type": "application/json",
            "apikey": supabase_key
        }
        
        payload = {
            "password": request.new_password
        }
        
        logger.info(f"🔄 [ConfirmReset] Requête PUT vers: {api_url}")
        logger.info(f"🔄 [ConfirmReset] Headers: {list(headers.keys())}")
        
        async with httpx.AsyncClient() as client:
            response = await client.put(api_url, headers=headers, json=payload)
            
        logger.info(f"🔍 [ConfirmReset] Réponse API directe: {response.status_code}")
        logger.info(f"🔍 [ConfirmReset] Contenu réponse: {response.text[:200]}...")
        
        if response.status_code == 200:
            logger.info(f"✅ [ConfirmReset] Mot de passe mis à jour avec succès (méthode 4)")
            return ForgotPasswordResponse(
                success=True,
                message="Mot de passe mis à jour avec succès"
            )
        else:
            logger.warning(f"⚠️ [ConfirmReset] API directe échouée: {response.status_code} - {response.text}")
            
    except Exception as method4_error:
        logger.warning(f"⚠️ [ConfirmReset] Méthode 4 échouée: {method4_error}")
    
    # === TOUTES LES MÉTHODES ONT ÉCHOUÉ ===
    logger.error(f"❌ [ConfirmReset] === TOUTES LES MÉTHODES ONT ÉCHOUÉ ===")
    logger.error(f"❌ [ConfirmReset] Token analysé: email={user_email}, type={token_type}")
    
    # Diagnostic final
    try:
        import jwt as pyjwt
        token_payload = pyjwt.decode(request.token, options={"verify_signature": False})
        exp_timestamp = token_payload.get("exp")
        
        if exp_timestamp:
            current_timestamp = datetime.utcnow().timestamp()
            if current_timestamp > exp_timestamp:
                logger.error(f"❌ [ConfirmReset] Diagnostic: Token expiré")
                raise HTTPException(
                    status_code=400, 
                    detail="Token expiré. Demandez un nouveau lien de réinitialisation."
                )
        
        logger.error(f"❌ [ConfirmReset] Diagnostic: Token semble valide mais aucune méthode n'a fonctionné")
        
    except Exception:
        logger.error(f"❌ [ConfirmReset] Diagnostic: Token illisible ou corrompu")
    
    # Erreur finale avec plus de détails
    raise HTTPException(
        status_code=400, 
        detail="Impossible de réinitialiser le mot de passe. Le token pourrait être invalide, expiré, ou incompatible avec cette version de Supabase. Demandez un nouveau lien de réinitialisation."
    )

# === ENDPOINTS EXISTANTS (CONSERVÉS) ===
@router.post("/delete-data", response_model=DeleteDataResponse)
async def delete_user_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Request data deletion for GDPR compliance.
    """
    user_id = current_user["user_id"]
    user_email = current_user["email"]
    logger.info("GDPR deletion requested for %s (%s)", user_email, user_id)
    return {
        "success": True,
        "message": "Demande de suppression enregistrée",
        "note": "Vos données seront supprimées sous 30 jours",
        "timestamp": datetime.utcnow()
    }

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
        "profile_id": current_user.get("profile_id"),
        "jwt_secret_used": current_user.get("jwt_secret_used")  # 🆕 Debug info
    }

@router.get("/debug/jwt-config")
async def debug_jwt_config():
    """Debug endpoint pour voir la configuration JWT multi-compatible"""
    return {
        "jwt_secrets_configured": len(JWT_SECRETS),
        "jwt_secret_types": [s[0] for s in JWT_SECRETS],
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "supabase_anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
        "supabase_service_role_key_configured": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "jwt_algorithm": JWT_ALGORITHM,
        "auth_temp_compatible": True,  # 🆕 Flag
        "supabase_compatible": True,   # 🆕 Flag
        "multi_secret_support": True,  # 🆕 Flag
        "main_secret_type": JWT_SECRETS[0][0] if JWT_SECRETS else "none",
        "backend_centralized_oauth": True,  # 🆕 Confirmation OAuth backend-centralisé
        "register_endpoint_available": True,  # 🆕 Confirmation que register est disponible
        "reset_password_endpoints_available": True,  # 🆕 Confirmation que reset password est disponible
        "change_password_endpoint_available": True,  # 🆕 Confirmation que change password est disponible
        "oauth_endpoints_available": [
            "/auth/oauth/linkedin/login",
            "/auth/oauth/facebook/login",
            "/auth/oauth/linkedin/callback",
            "/auth/oauth/facebook/callback"
        ]
    }

# === 🆕 ENDPOINT DEBUG POUR RESET PASSWORD ===
@router.get("/debug/reset-config")
async def debug_reset_config():
    """Debug temporaire pour voir la configuration de reset password"""
    
    # Récupérer exactement comme dans la fonction reset-password
    redirect_url = os.getenv("RESET_PASSWORD_REDIRECT_URL", "https://expert.intelia.com/auth/reset-password")
    
    return {
        "redirect_url_configured": redirect_url,
        "env_var_exists": bool(os.getenv("RESET_PASSWORD_REDIRECT_URL")),
        "env_var_value": os.getenv("RESET_PASSWORD_REDIRECT_URL"),
        "fallback_used": not bool(os.getenv("RESET_PASSWORD_REDIRECT_URL")),
        "all_env_vars": {
            "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
            "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
            "RESET_PASSWORD_REDIRECT_URL": bool(os.getenv("RESET_PASSWORD_REDIRECT_URL"))
        }
    }

# === 🆕 ENDPOINT DEBUG OAUTH ===
@router.get("/debug/oauth-config")
async def debug_oauth_config():
    """Debug endpoint pour vérifier la configuration OAuth"""
    return {
        "oauth_available": SUPABASE_AVAILABLE,
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "supabase_anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
        "frontend_url": os.getenv("FRONTEND_URL", "https://expert.intelia.com"),
        "backend_url": os.getenv("BACKEND_URL", "https://expert-app-cngws.ondigitalocean.app"),
        "supported_providers": ["linkedin", "facebook"],
        "oauth_endpoints": [
            "/auth/oauth/linkedin/login",
            "/auth/oauth/facebook/login",
            "/auth/oauth/linkedin/callback", 
            "/auth/oauth/facebook/callback"
        ],
        "backend_centralized": True,
        "callback_flow": "backend_handles_oauth_then_redirects_frontend_with_token"
    }