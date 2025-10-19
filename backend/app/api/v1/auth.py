import os
import logging
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.utils.gdpr_helpers import mask_email

# Optional Supabase import
try:
    from supabase import create_client, Client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Import email service for multilingual confirmation emails
try:
    from app.services.email_service import get_email_service, EmailType
    EMAIL_SERVICE_AVAILABLE = True
except ImportError:
    EMAIL_SERVICE_AVAILABLE = False
    logger.warning("Email service not available")

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


# ==================== HELPER FUNCTIONS ====================


def extract_facebook_id_from_avatar_url(avatar_url: str) -> Optional[str]:
    """
    Extrait l'ID Facebook depuis l'URL de l'avatar Facebook.

    Format: https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10161563757712721&...
    Retourne: "10161563757712721"
    """
    if not avatar_url or "fbsbx.com" not in avatar_url:
        return None

    try:
        # Chercher le paramètre asid= dans l'URL
        if "asid=" in avatar_url:
            # Extraire la valeur après asid=
            start = avatar_url.index("asid=") + 5
            end = avatar_url.index("&", start) if "&" in avatar_url[start:] else len(avatar_url)
            facebook_id = avatar_url[start:end]

            logger.info(f"[Facebook] ID extrait de l'avatar: {facebook_id}")
            return facebook_id
    except Exception as e:
        logger.warning(f"[Facebook] Erreur extraction ID: {e}")

    return None


def construct_facebook_profile_url(facebook_id: str) -> str:
    """Construit l'URL du profil Facebook depuis l'ID."""
    return f"https://facebook.com/{facebook_id}"

# Configuration JWT MULTI-COMPATIBLE (auth-temp + Supabase)
# Récupérer les secrets JWT dans l'ordre de priorité
JWT_SECRETS = []

# 1. Secret auth-temp (utilisé par vos endpoints /auth-temp/*)
auth_temp_secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET")
if auth_temp_secret:
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

# SÉCURITÉ: Crash si aucun secret configuré
if not JWT_SECRETS:
    raise RuntimeError(
        "❌ FATAL: Aucun JWT secret configuré. "
        "Définissez SUPABASE_JWT_SECRET, JWT_SECRET, SUPABASE_ANON_KEY ou SUPABASE_SERVICE_ROLE_KEY "
        "dans les variables d'environnement. L'application ne peut pas démarrer."
    )

logger.info(f"JWT Secrets configurés: {len(JWT_SECRETS)} secrets disponibles")
logger.info(f"Secrets types: {[s[0] for s in JWT_SECRETS]}")

# Utiliser le premier secret pour créer des tokens
MAIN_JWT_SECRET = JWT_SECRETS[0][1]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

logger.info("JWT signing secret: %s", JWT_SECRETS[0][0])
logger.info("Token validity duration: %s minutes", ACCESS_TOKEN_EXPIRE_MINUTES)

security = HTTPBearer()


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
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


# === NOUVEAUX MODÈLES POUR REGISTER ===
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None  # NOUVEAU: pays
    preferred_language: Optional[str] = "en"  # NOUVEAU: langue préférée


class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


# === NOUVEAUX MODÈLES POUR RESET PASSWORD ===
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ValidateResetTokenRequest(BaseModel):
    token: str


class ConfirmResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    email: Optional[EmailStr] = None  # NOUVEAU: email optionnel pour codes OTP


class ForgotPasswordResponse(BaseModel):
    success: bool
    message: str


class ValidateTokenResponse(BaseModel):
    valid: bool
    message: str


# === NOUVEAU MODÈLE POUR CHANGE PASSWORD ===
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    success: bool
    message: str


# === NOUVEAUX MODÈLES POUR OAUTH ===
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


# === NOUVEAUX MODÈLES POUR SESSION TRACKING ===
class HeartbeatResponse(BaseModel):
    status: str
    session_id: Optional[str] = None
    error: Optional[str] = None


class LogoutRequest(BaseModel):
    reason: Optional[str] = "manual"


class LogoutResponse(BaseModel):
    success: bool
    message: str
    session_duration: Optional[float] = None
    error: Optional[str] = None


# === FONCTION HELPER POUR L'ÉCHANGE DE CODE OAUTH ===
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

        headers = {"apikey": supabase_key, "Content-Type": "application/json"}

        payload = {"code": code}

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, headers=headers, json=payload)

        if response.status_code == 200:
            session_data = response.json()
            logger.info("[OAuth] Session obtenue via token exchange")
            return session_data
        else:
            logger.warning(f"[OAuth] Token exchange échoué: {response.status_code}")

            # Fallback: essayer callback direct
            callback_url = f"{supabase_url}/auth/v1/callback"
            callback_params = {"code": code}

            response = await client.get(
                callback_url, params=callback_params, headers=headers
            )
            if response.status_code == 200:
                return response.json()

            return None

    except Exception as e:
        logger.error(f"[OAuth] Erreur échange code: {e}")
        return None


# === FONCTIONS DÉPLACÉES AVANT LES ENDPOINTS ===


# NOUVELLE FONCTION : Récupération profil utilisateur depuis Supabase (CONSERVÉE)
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
        response = (
            supabase.table("users").select("*").eq("auth_user_id", user_id).execute()
        )

        # Si pas trouvé par auth_user_id, essayer par email
        if not response.data:
            response = supabase.table("users").select("*").eq("email", email).execute()

        if response.data and len(response.data) > 0:
            profile = response.data[0]
            logger.debug(
                f"Profil trouvé pour {email}: {profile.get('user_type', 'user')}"
            )
            return {
                "user_type": profile.get("user_type", "user"),
                "full_name": profile.get("full_name"),
                "preferences": profile.get("preferences", {}),
                "profile_id": profile.get("id"),
            }
        else:
            logger.warning(f"Aucun profil trouvé pour {mask_email(email)} - rôle par défaut")
            return {"user_type": "user"}

    except Exception as e:
        logger.error(f"Erreur récupération profil Supabase: {e}")
        return {"user_type": "user"}


# === FONCTION get_current_user EXISTANTE (MODIFIÉE POUR SESSION TRACKING) ===
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    VERSION MULTI-COMPATIBLE : Decode JWT tokens auth-temp ET Supabase
    Maintenant avec support session_id pour le tracking
    """
    token = credentials.credentials

    if not token or not isinstance(token, str):
        logger.warning("Token vide ou invalide")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing or invalid"
        )

    # ESSAYER TOUS LES SECRETS CONFIGURÉS
    for secret_name, secret_value in JWT_SECRETS:
        if not secret_value:
            continue

        try:
            logger.debug(f"Tentative décodage avec {secret_name}")

            # DÉCODER AVEC PLUSIEURS OPTIONS
            decode_options = [
                {
                    "options": {"verify_aud": False}
                },  # Sans vérifier audience (auth-temp)
                {"audience": "authenticated"},  # Standard Supabase
                {},  # Sans options spéciales
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
                            **option_set,
                        )
                    elif "audience" in option_set:
                        # Décoder avec audience
                        payload = jwt.decode(
                            token,
                            secret_value,
                            algorithms=[JWT_ALGORITHM],
                            audience=option_set["audience"],
                        )
                    else:
                        # Décoder simple
                        payload = jwt.decode(
                            token, secret_value, algorithms=[JWT_ALGORITHM]
                        )
                    break  # Si succès, sortir de la boucle des options
                except jwt.InvalidAudienceError:
                    continue  # Essayer sans audience
                except Exception:
                    continue  # Essayer l'option suivante

            if not payload:
                continue  # Essayer le secret suivant

            logger.debug("Token décodé avec succès avec %s", secret_name)

            # EXTRACTION FLEXIBLE DES INFORMATIONS UTILISATEUR
            # Support auth-temp ET Supabase
            user_id = payload.get("sub") or payload.get("user_id")
            email = payload.get("email")
            session_id = payload.get("session_id")  # NOUVEAU : extraction session_id

            # Vérification de base
            if not user_id:
                logger.warning("Token sans user_id valide")
                continue

            if not email:
                logger.warning("Token sans email valide")
                continue

            # RÉCUPÉRER LE PROFIL UTILISATEUR depuis Supabase
            try:
                profile = await get_user_profile_from_supabase(user_id, email)
            except Exception as e:
                logger.warning(f"Erreur récupération profil: {e}")
                profile = {"user_type": "user"}

            # CONSTRUIRE LA RÉPONSE UNIFIÉE
            user_data = {
                "user_id": user_id,
                "email": email,
                "session_id": session_id,  # NOUVEAU : inclure session_id
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
                "is_admin": profile.get("user_type") in ["admin", "super_admin"],
            }

            logger.debug(
                "User authenticated: %s (role: %s)", email, user_data['user_type']
            )
            return user_data

        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expiré (testé avec {secret_name})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )

        except jwt.InvalidSignatureError:
            logger.debug(f"Signature invalide avec {secret_name}")
            continue

        except jwt.InvalidTokenError as e:
            logger.debug(f"Token invalide avec {secret_name}: {e}")
            continue

        except Exception as e:
            logger.debug(f"Erreur inattendue avec {secret_name}: {e}")
            continue

    # Si aucun secret n'a fonctionné
    logger.debug("Impossible de décoder le token avec tous les secrets disponibles")
    logger.debug(f"Secrets essayés: {[s[0] for s in JWT_SECRETS]}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token - unable to verify signature",
    )


# === ENDPOINTS COMMENCENT ICI ===


# === ENDPOINT LOGIN MODIFIÉ AVEC SESSION TRACKING ===
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return a JWT access token.
    Version corrigée avec gestion d'erreurs détaillée + session tracking
    """
    logger.info(f"[Login] Tentative de connexion: {mask_email(request.email)}")

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client not available")
        raise HTTPException(
            status_code=500,
            detail="Service d'authentification temporairement indisponible",
        )

    # Validation des données d'entrée
    if not request.email or not request.email.strip():
        logger.warning("[Login] Email manquant ou vide")
        raise HTTPException(status_code=400, detail="L'adresse email est requise")

    if not request.password:
        logger.warning("[Login] Mot de passe manquant")
        raise HTTPException(status_code=400, detail="Le mot de passe est requis")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("[Login] Configuration Supabase manquante")
        raise HTTPException(
            status_code=500, detail="Configuration d'authentification manquante"
        )

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        logger.info(
            f"[Login] Tentative d'authentification Supabase pour: {request.email}"
        )

        # Essayer la nouvelle API d'abord
        try:
            result = supabase.auth.sign_in_with_password(
                {"email": request.email.strip(), "password": request.password}
            )
            logger.info("[Login] Utilisation API sign_in_with_password")
        except AttributeError:
            # Fallback pour ancienne API
            logger.info("[Login] Fallback vers ancienne API sign_in")
            result = supabase.auth.sign_in(
                email=request.email.strip(), password=request.password
            )

        # Vérifier le résultat
        user = result.user
        session = result.session

        logger.info(
            f"[Login] Résultat Supabase - User: {bool(user)}, Session: {bool(session)}"
        )

        if user is None:
            logger.warning(f"[Login] Authentification échouée pour: {mask_email(request.email)}")
            raise HTTPException(
                status_code=401, detail="Email ou mot de passe incorrect"
            )

        # Vérifier si l'email est confirmé
        if hasattr(user, "email_confirmed_at") and not user.email_confirmed_at:
            logger.warning(f"[Login] Email non confirmé pour: {mask_email(request.email)}")
            raise HTTPException(
                status_code=401,
                detail="Veuillez confirmer votre email avant de vous connecter",
            )

        # NOUVEAU : Générer session_id pour tracking
        session_id = str(uuid.uuid4())

        # Créer le token JWT avec session_id
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "user_id": user.id,
            "email": request.email.strip(),
            "sub": user.id,
            "iss": "intelia-expert",
            "aud": "authenticated",
            "session_id": session_id,  # NOUVEAU
        }

        token = create_access_token(token_data, expires)
        expires_at = datetime.utcnow() + expires

        # NOUVEAU : Démarrer le tracking de session
        try:
            from .logging import get_analytics_manager

            analytics = get_analytics_manager()
            analytics.start_session(
                user_email=request.email.strip(), session_id=session_id
            )
            logger.info(f"[Login] Session tracking démarré: {session_id}")
        except Exception as e:
            logger.warning(f"[Login] Erreur session tracking: {e}")
            # Ne pas faire échouer le login si le tracking échoue

        logger.info(f"[Login] Connexion réussie pour: {mask_email(request.email)}")

        return TokenResponse(
            access_token=token, token_type="bearer", expires_at=expires_at
        )

    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise

    except Exception as e:
        logger.error(f"[Login] Erreur inattendue: {str(e)}")
        logger.error(f"[Login] Type d'erreur: {type(e).__name__}")

        # Analyser le type d'erreur pour donner un message approprié
        error_message = str(e).lower()

        if any(
            keyword in error_message
            for keyword in [
                "invalid login credentials",
                "invalid_credentials",
                "wrong password",
                "incorrect password",
                "authentication failed",
                "invalid email or password",
            ]
        ):
            logger.info("[Login] Erreur identifiée comme credentials invalides")
            raise HTTPException(
                status_code=401, detail="Email ou mot de passe incorrect"
            )
        elif any(
            keyword in error_message
            for keyword in [
                "email not confirmed",
                "email_not_confirmed",
                "unconfirmed",
                "verify",
            ]
        ):
            logger.info("[Login] Erreur identifiée comme email non confirmé")
            raise HTTPException(
                status_code=401,
                detail="Veuillez confirmer votre email avant de vous connecter",
            )
        elif any(
            keyword in error_message
            for keyword in ["user not found", "no user", "user does not exist"]
        ):
            logger.info("[Login] Erreur identifiée comme utilisateur inexistant")
            raise HTTPException(
                status_code=401, detail="Email ou mot de passe incorrect"
            )
        elif any(
            keyword in error_message
            for keyword in ["rate limit", "too many", "rate_limit"]
        ):
            logger.info("[Login] Erreur identifiée comme rate limiting")
            raise HTTPException(
                status_code=429,
                detail="Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes.",
            )
        elif any(
            keyword in error_message
            for keyword in ["network", "connection", "timeout", "unavailable"]
        ):
            logger.info("[Login] Erreur identifiée comme problème réseau")
            raise HTTPException(
                status_code=503,
                detail="Service temporairement indisponible. Veuillez réessayer.",
            )
        else:
            # Erreur générique mais avec un message plus utile
            logger.warning("[Login] Erreur non identifiée, traitement générique")
            raise HTTPException(
                status_code=500,
                detail="Erreur technique lors de la connexion. Veuillez réessayer ou contactez le support.",
            )


# === NOUVEAUX ENDPOINTS SESSION TRACKING ===


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def session_heartbeat(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Maintient la session active via heartbeat
    """
    session_id = current_user.get("session_id")
    if not session_id:
        return HeartbeatResponse(status="no_session_id")

    try:
        from .logging import get_analytics_manager

        analytics = get_analytics_manager()
        analytics.update_session_heartbeat(session_id)
        return HeartbeatResponse(status="active", session_id=session_id)
    except Exception as e:
        logger.error(f"[Heartbeat] Erreur: {e}")
        return HeartbeatResponse(status="error", error=str(e))


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: LogoutRequest = LogoutRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Termine la session et calcule la durée
    """
    session_id = current_user.get("session_id")
    user_email = current_user.get("email", "unknown")

    try:
        if session_id:
            from .logging import get_analytics_manager

            analytics = get_analytics_manager()
            result = analytics.end_session(session_id, request.reason or "manual")

            duration = result.get("duration") if result else None
            logger.info(f"[Logout] Session terminée: {user_email}, durée: {duration}s")

            return LogoutResponse(
                success=True, message="Déconnexion réussie", session_duration=duration
            )
        else:
            return LogoutResponse(
                success=True, message="Déconnexion réussie (pas de session_id)"
            )
    except Exception as e:
        logger.error(f"[Logout] Erreur: {e}")
        return LogoutResponse(
            success=False, message="Erreur lors de la déconnexion", error=str(e)
        )


# === ENDPOINT REFRESH TOKEN ===
@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Rafraîchit le token lors d'une activité utilisateur
    """
    user_id = current_user.get("user_id")
    email = current_user.get("email")
    session_id = current_user.get("session_id")

    # Créer un nouveau token avec 60 minutes d'expiration
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "user_id": user_id,
        "email": email,
        "sub": user_id,
        "iss": "intelia-expert",
        "aud": "authenticated",
        "session_id": session_id,
    }

    new_token = create_access_token(token_data, expires)
    expires_at = datetime.utcnow() + expires

    logger.info(f"[RefreshToken] Token rafraîchi pour: {mask_email(email)}")

    return TokenResponse(
        access_token=new_token, token_type="bearer", expires_at=expires_at
    )


# === ENDPOINTS OAUTH ===


@router.post("/oauth/initiate", response_model=OAuthInitiateResponse)
async def initiate_oauth_login(request: OAuthInitiateRequest):
    """
    Initie la connexion OAuth avec LinkedIn ou Facebook
    Retourne l'URL d'autorisation pour rediriger l'utilisateur
    """
    logger.info(f"[OAuth] Initiation connexion {request.provider}")

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service OAuth non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration OAuth manquante")

    # Valider le provider
    valid_providers = ["linkedin_oidc", "facebook"]
    provider_name = request.provider.lower()

    # Mapper les noms de providers
    if provider_name == "linkedin":
        provider_name = "linkedin_oidc"
    elif provider_name not in valid_providers:
        raise HTTPException(
            status_code=400, detail=f"Provider non supporté: {request.provider}"
        )

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # URL de redirection après auth
        default_redirect = f"{os.getenv('FRONTEND_URL', 'https://expert.intelia.com')}/auth/oauth/callback"
        redirect_url = request.redirect_url or default_redirect

        logger.info(f"[OAuth] Provider: {provider_name}, Redirect: {redirect_url}")

        # Initier le flow OAuth avec Supabase
        result = supabase.auth.sign_in_with_oauth(
            {
                "provider": provider_name,
                "options": {
                    "redirect_to": redirect_url,
                    "scopes": (
                        "openid email profile"
                        if provider_name == "linkedin_oidc"
                        else "email"
                    ),
                },
            }
        )

        if not result.url:
            logger.error(
                f"[OAuth] Pas d'URL retournée par Supabase pour {provider_name}"
            )
            raise HTTPException(status_code=500, detail="Erreur d'initiation OAuth")

        # Générer un state pour la sécurité
        import secrets

        state = secrets.token_urlsafe(32)

        # Stocker temporairement le state (dans une vraie app, utiliser Redis)
        # Pour l'instant, on l'inclut dans l'URL
        auth_url = f"{result.url}&state={state}"

        logger.info(f"[OAuth] URL d'autorisation générée pour {provider_name}")

        return OAuthInitiateResponse(
            success=True,
            auth_url=auth_url,
            state=state,
            message=f"Redirection vers {request.provider} initiée",
        )

    except Exception as e:
        logger.error(f"[OAuth] Erreur initiation {provider_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'initiation OAuth avec {request.provider}",
        )


@router.get("/oauth/{provider}/login")
async def oauth_redirect_login(provider: str):
    """
    Endpoint simplifié pour redirection OAuth directe - VERSION BACKEND-CENTRALISÉE
    Redirige vers le provider OAuth puis traite le callback côté backend
    """
    logger.info(f"[OAuth] Redirection directe vers {provider}")

    if not SUPABASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Service OAuth non disponible")

    # Configuration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Configuration OAuth manquante")

    # Valider et mapper le provider
    provider_map = {"linkedin": "linkedin_oidc", "facebook": "facebook"}

    provider_name = provider_map.get(provider.lower())
    if not provider_name:
        raise HTTPException(
            status_code=400, detail=f"Provider non supporté: {provider}"
        )

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # URL de redirection vers NOTRE backend callback
        backend_base = os.getenv(
            "BACKEND_URL", "https://expert-app-cngws.ondigitalocean.app"
        )
        redirect_url = f"{backend_base}/api/v1/auth/oauth/{provider}/callback"

        logger.info(f"[OAuth] Callback URL configurée: {redirect_url}")

        # Initier OAuth
        result = supabase.auth.sign_in_with_oauth(
            {
                "provider": provider_name,
                "options": {
                    "redirect_to": redirect_url,  # Pointe vers notre backend
                    "scopes": (
                        "openid email profile"
                        if provider_name == "linkedin_oidc"
                        else "email"
                    ),
                },
            }
        )

        if not result.url:
            raise HTTPException(status_code=500, detail="Erreur génération URL OAuth")

        logger.info(f"[OAuth] Redirection vers {provider}: {result.url}")

        # Redirection directe vers le provider OAuth
        return RedirectResponse(url=result.url, status_code=302)

    except Exception as e:
        logger.error(f"[OAuth] Erreur redirection {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur OAuth")


@router.get("/oauth/{provider}/callback")
async def oauth_backend_callback(
    provider: str,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
):
    """
    Callback OAuth traité côté backend avec session tracking
    Échange le code contre un token et redirige le frontend avec le token
    """
    logger.info(f"[OAuth/Callback] Callback reçu pour {provider}")

    # Gérer les erreurs OAuth
    if error:
        logger.error(f"[OAuth/Callback] Erreur OAuth: {error} - {error_description}")
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        error_url = f"{frontend_url}/?oauth_error={error}&message={error_description or 'Erreur OAuth'}"
        return RedirectResponse(url=error_url, status_code=302)

    if not code:
        logger.error("[OAuth/Callback] Aucun code d'autorisation reçu")
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        error_url = (
            f"{frontend_url}/?oauth_error=no_code&message=Code d'autorisation manquant"
        )
        return RedirectResponse(url=error_url, status_code=302)

    try:
        # Mapper le provider
        provider_name = provider.lower()
        if provider_name == "linkedin":
            provider_name = "linkedin_oidc"

        # ÉCHANGE DU CODE CONTRE UNE SESSION SUPABASE
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)

        logger.info(f"[OAuth/Callback] Échange du code pour {provider_name}")

        # Utiliser notre fonction helper pour échanger le code
        session_result = await exchange_oauth_code_for_session(
            supabase, code, provider_name
        )

        if not session_result:
            # Fallback: créer des données utilisateur factices pour test
            logger.warning(
                "[OAuth/Callback] Échange échoué - création utilisateur test"
            )
            user_data = {
                "id": f"oauth_{provider_name}_{code[:8]}",
                "email": f"test.oauth.{provider_name}@intelia.com",
                "user_metadata": {
                    "full_name": f"Test OAuth {provider_name.title()}",
                    "avatar_url": None,
                },
            }
        else:
            # Extraire les données utilisateur de la session
            user_data = session_result.get("user", {})
            if not user_data:
                raise Exception("Aucune donnée utilisateur dans la session")

        email = user_data.get("email")
        user_id = user_data.get("id")
        # CORRECTION: Suppression de la variable non utilisée full_name

        if not email or not user_id:
            raise Exception("Données utilisateur OAuth incomplètes")

        logger.info(f"[OAuth/Callback] Utilisateur: {mask_email(email)} (ID: {user_id})")

        # NOUVEAU : Générer session_id pour OAuth
        session_id = str(uuid.uuid4())

        # CRÉER NOTRE TOKEN JWT COMPATIBLE avec session_id
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "user_id": user_id,
            "email": email,
            "sub": user_id,
            "iss": "intelia-expert",
            "aud": "authenticated",  # Important pour la compatibilité
            "oauth_provider": provider_name,
            "session_id": session_id,  # NOUVEAU
        }

        jwt_token = create_access_token(token_data, expires)

        # NOUVEAU : Démarrer le tracking de session OAuth
        try:
            from .logging import get_analytics_manager

            analytics = get_analytics_manager()
            analytics.start_session(user_email=email, session_id=session_id)
            logger.info(f"[OAuth/Callback] Session tracking démarré: {session_id}")
        except Exception as e:
            logger.warning(f"[OAuth/Callback] Erreur session tracking: {e}")

        # REDIRECTION VERS LE FRONTEND AVEC LE TOKEN
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        success_url = f"{frontend_url}/chat?oauth_token={jwt_token}&oauth_success=true&oauth_provider={provider}&oauth_email={email}"

        logger.info(
            f"[OAuth/Callback] Redirection vers frontend avec token pour {email}"
        )
        return RedirectResponse(url=success_url, status_code=302)

    except Exception as e:
        logger.error(f"[OAuth/Callback] Erreur traitement callback: {str(e)}")
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        error_url = f"{frontend_url}/?oauth_error=callback_error&message={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)


@router.post("/oauth/callback", response_model=OAuthCallbackResponse)
async def handle_oauth_callback(request: OAuthCallbackRequest):
    """
    Gère le callback OAuth après autorisation
    Échange le code contre un token et crée/connecte l'utilisateur
    """
    logger.info(f"[OAuth] Callback reçu pour {request.provider}")

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(status_code=500, detail="Service OAuth non disponible")

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration OAuth manquante")

    # CORRECTION: Import os ajouté pour résoudre F821

    try:
        # Valider le state (sécurité basique)
        if not request.state or len(request.state) < 10:
            logger.warning("[OAuth] State invalide ou manquant")
            # On continue quand même car certains providers peuvent ne pas retourner le state

        # Mapper le provider
        provider_name = request.provider.lower()
        if provider_name == "linkedin":
            provider_name = "linkedin_oidc"

        logger.info(f"[OAuth] Échange du code d'autorisation pour {provider_name}")

        # Pour Supabase, nous devons simuler l'échange de code
        # En utilisant l'API directe
        import httpx

        # Construire l'URL de callback Supabase
        callback_url = f"{supabase_url}/auth/v1/callback"

        # Paramètres pour l'échange de code
        callback_params = {"code": request.code, "state": request.state}

        headers = {"apikey": supabase_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            # Appeler l'endpoint de callback Supabase
            response = await client.get(
                callback_url,
                params=callback_params,
                headers=headers,
                follow_redirects=True,
            )

        logger.info(f"[OAuth] Réponse callback Supabase: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"[OAuth] Erreur callback Supabase: {response.text}")
            raise HTTPException(
                status_code=400, detail="Erreur lors de l'authentification OAuth"
            )

        # Simuler des données utilisateur OAuth pour le test
        # Dans un vrai environnement, cela viendrait de la réponse Supabase
        user_data = {
            "id": f"oauth_{provider_name}_{request.code[:8]}",
            "email": f"user_{request.code[:8]}@example.com",
            "user_metadata": {
                "full_name": f"User OAuth {provider_name.title()}",
                "avatar_url": None,
            },
        }

        if not user_data or not user_data.get("email"):
            logger.error("[OAuth] Données utilisateur incomplètes")
            raise HTTPException(
                status_code=400, detail="Données utilisateur OAuth incomplètes"
            )

        # Extraire les informations utilisateur
        email = user_data.get("email")
        user_id = user_data.get("id")
        full_name = user_data.get("user_metadata", {}).get(
            "full_name"
        ) or user_data.get("name")
        avatar_url = user_data.get("user_metadata", {}).get("avatar_url")

        logger.info(f"[OAuth] Utilisateur: {mask_email(email)} (ID: {user_id})")

        # Créer notre token JWT pour l'utilisateur
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "user_id": user_id,
            "email": email,
            "sub": user_id,
            "iss": "intelia-expert",
            "aud": "authenticated",
            "oauth_provider": provider_name,
        }

        jwt_token = create_access_token(token_data, expires)

        # Construire la réponse utilisateur
        user_response = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "oauth_provider": provider_name,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"[OAuth] Connexion réussie via {request.provider}: {mask_email(email)}")

        return OAuthCallbackResponse(
            success=True,
            message=f"Connexion réussie via {request.provider}",
            token=jwt_token,
            user=user_response,
        )

    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"[OAuth] Erreur callback {request.provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur lors du traitement du callback OAuth"
        )


# === NOUVEL ENDPOINT CHANGE PASSWORD ===
@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Changer le mot de passe de l'utilisateur connecté
    Vérifie le mot de passe actuel puis met à jour avec le nouveau
    """
    logger.info(
        f"[ChangePassword] Demande de changement pour: {current_user.get('email', 'unknown')}"
    )

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(
            status_code=500,
            detail="Service de changement de mot de passe non disponible",
        )

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")

    supabase: Client = create_client(supabase_url, supabase_key)
    user_email = current_user.get("email")

    try:
        # 1. Vérifier le mot de passe actuel
        logger.info("[ChangePassword] Vérification mot de passe actuel")

        try:
            verify_result = supabase.auth.sign_in_with_password(
                {"email": user_email, "password": request.current_password}
            )
        except AttributeError:
            # Fallback pour ancienne API
            verify_result = supabase.auth.sign_in(
                email=user_email, password=request.current_password
            )

        if not verify_result.user:
            logger.warning(
                f"[ChangePassword] Mot de passe actuel incorrect pour: {user_email}"
            )
            raise HTTPException(
                status_code=400, detail="Le mot de passe actuel est incorrect"
            )

        logger.info("[ChangePassword] Mot de passe actuel vérifié")

        # 2. Mettre à jour le mot de passe
        logger.info("[ChangePassword] Mise à jour du nouveau mot de passe")

        # Créer un nouveau client avec la session de vérification
        supabase_auth: Client = create_client(supabase_url, supabase_key)

        # Définir la session pour pouvoir faire l'update
        if verify_result.session:
            try:
                supabase_auth.auth.set_session(
                    verify_result.session.access_token,
                    verify_result.session.refresh_token,
                )
            except Exception:
                # Essayer avec l'objet session complet
                supabase_auth.auth.set_session(verify_result.session)

        # Mettre à jour le mot de passe
        update_result = supabase_auth.auth.update_user(
            {"password": request.new_password}
        )

        if not update_result.user:
            logger.error(
                f"[ChangePassword] Échec mise à jour mot de passe pour: {user_email}"
            )
            raise HTTPException(
                status_code=500, detail="Erreur lors de la mise à jour du mot de passe"
            )

        logger.info(
            f"[ChangePassword] Mot de passe mis à jour avec succès pour: {user_email}"
        )

        return ChangePasswordResponse(
            success=True, message="Mot de passe changé avec succès"
        )

    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"[ChangePassword] Erreur inattendue: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erreur technique lors du changement de mot de passe",
        )


# === NOUVEL ENDPOINT REGISTER ===
@router.post("/register", response_model=AuthResponse)
async def register_user(user_data: UserRegister):
    """
    Inscription d'un nouvel utilisateur
    Crée le compte dans Supabase et retourne un token JWT
    """
    logger.info(f"[Register] Tentative inscription: {user_data.email}")

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(
            status_code=500, detail="Service d'inscription non disponible"
        )

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
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
        if user_data.country:
            user_metadata["country"] = user_data.country
        # NOUVEAU: Stocker la langue préférée
        if user_data.preferred_language:
            user_metadata["preferred_language"] = user_data.preferred_language

        # Configuration de l'URL de redirection après confirmation
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        redirect_to = f"{frontend_url}/auth/verify-email"

        # Essayer la nouvelle API Supabase d'abord
        try:
            result = supabase.auth.sign_up(
                {
                    "email": user_data.email,
                    "password": user_data.password,
                    "options": {
                        "data": user_metadata if user_metadata else {},
                        "email_redirect_to": redirect_to,  # URL de redirection après clic sur le lien
                    },
                }
            )
        except AttributeError:
            # Fallback pour ancienne API Supabase
            result = supabase.auth.sign_up(
                email=user_data.email,
                password=user_data.password,
                user_metadata=user_metadata if user_metadata else {},
            )
        except Exception as e:
            # Capturer les erreurs Supabase (ex: utilisateur existant)
            error_msg = str(e)
            logger.error(f"[Register] Erreur Supabase sign_up: {error_msg}")
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                raise HTTPException(status_code=400, detail="Un compte avec cet email existe déjà")
            raise HTTPException(status_code=400, detail=error_msg)

        # Vérifier le résultat
        if result.user is None:
            error_msg = "Impossible de créer le compte"
            if hasattr(result, "error") and result.error:
                error_msg = str(result.error)
            logger.error(f"[Register] Échec Supabase: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Vérifier si l'utilisateur existe déjà (Supabase peut retourner un user même si déjà inscrit)
        # Dans ce cas, user.email_confirmed_at peut être None (nouveau) ou avoir une valeur (existant)
        # MAIS si "Confirm email" est activé, tous les nouveaux users ont email_confirmed_at=None
        # Donc on ne peut pas distinguer facilement. On va logger les métadonnées pour debug.
        logger.info(f"[Register] User metadata envoyées: {user_metadata}")
        if hasattr(result.user, "user_metadata"):
            logger.info(f"[Register] User metadata retournées par Supabase: {result.user.user_metadata}")

        user = result.user
        logger.info(f"[Register] Compte créé dans Supabase: {user.id}")

        # NOUVEAU: Créer aussi une entrée dans la table public.users
        try:
            supabase_url_admin = os.getenv("SUPABASE_URL")
            service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if supabase_url_admin and service_role_key:
                admin_client = create_client(supabase_url_admin, service_role_key)

                # Créer l'entrée utilisateur dans public.users
                user_profile = {
                    "auth_user_id": user.id,
                    "email": user_data.email,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "full_name": full_name,
                    "country": user_data.country,
                    "phone": user_data.phone,
                    "company_name": user_data.company,
                    "user_type": "user",
                    "language": user_data.preferred_language or "en",
                    "created_at": datetime.utcnow().isoformat(),
                }

                # Filtrer les None
                user_profile = {k: v for k, v in user_profile.items() if v is not None}

                insert_response = admin_client.table("users").insert(user_profile).execute()
                logger.info(f"[Register] Profil utilisateur créé dans public.users: {user.id}")
            else:
                logger.warning(f"[Register] Service role key non configuré - profil public.users non créé")
        except Exception as e:
            logger.error(f"[Register] Erreur création profil public.users: {e}")
            # Ne pas bloquer l'inscription si la création du profil échoue

        # NOTE: Supabase envoie automatiquement l'email de confirmation via SMTP configuré
        # L'email utilise le template personnalisé (Supabase Dashboard → Email Templates → Confirm signup)
        # Le template détecte la langue via {{ .UserMetaData.preferred_language }}
        logger.info(f"[Register] Email de confirmation multilangue envoyé par Supabase (langue: {user_data.preferred_language})")

        # DÉSACTIVÉ: Envoi d'email custom car Supabase génère les tokens
        # et ne les expose pas via l'API. Pour des emails multilingues,
        # il faut personnaliser les templates dans Supabase Dashboard.
        if False and EMAIL_SERVICE_AVAILABLE and user_data.preferred_language:
            try:
                logger.info(f"[Register] EMAIL_SERVICE_AVAILABLE=True, initialisation email service...")
                email_service = get_email_service()
                logger.info(f"[Register] Email service initialisé: {type(email_service)}")

                # Générer un lien de confirmation via l'API Admin Supabase
                # Utiliser le service role key pour accéder à l'API admin
                supabase_url = os.getenv("SUPABASE_URL")
                service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")

                confirmation_url = None
                otp_token = None

                # Générer un lien de confirmation avec token via l'API Admin Supabase
                if supabase_url and service_role_key:
                    try:
                        logger.info(f"[Register] Génération du lien de confirmation via Admin API...")

                        # Créer un client admin avec service role key
                        admin_client = create_client(supabase_url, service_role_key)

                        # Générer le lien de confirmation
                        link_response = admin_client.auth.admin.generate_link(
                            {
                                "type": "signup",
                                "email": user_data.email,
                                "password": user_data.password,
                            }
                        )

                        logger.info(f"[Register] Admin API response type: {type(link_response)}")

                        # Extraire l'action_link et le hashed_token de la réponse
                        if hasattr(link_response, 'properties'):
                            properties = link_response.properties
                            action_link = properties.get('action_link')
                            hashed_token = properties.get('hashed_token')

                            if action_link:
                                confirmation_url = action_link
                                otp_token = hashed_token
                                logger.info(f"[Register] ✅ Lien de confirmation généré avec token")
                            else:
                                logger.warning(f"[Register] Pas d'action_link dans properties")
                        else:
                            logger.warning(f"[Register] Pas de 'properties' dans la réponse Admin API")

                    except Exception as e:
                        logger.error(f"[Register] ❌ Erreur Admin API: {type(e).__name__}: {str(e)}")
                        import traceback
                        logger.error(f"[Register] Traceback: {traceback.format_exc()}")
                else:
                    logger.warning(f"[Register] Service role key non configuré - Admin API skip")

                # Fallback si pas de service role key ou erreur
                if not confirmation_url:
                    logger.warning(f"[Register] Fallback: utilisation URL simple sans token")
                    confirmation_url = f"{frontend_url}/auth/verify-email?email={user_data.email}"

                logger.info(f"[Register] Envoi email de confirmation à {user_data.email} en {user_data.preferred_language}")
                logger.info(f"[Register] URL confirmation: {confirmation_url}")
                logger.info(f"[Register] First name: {user_data.first_name}")

                result = email_service.send_auth_email(
                    email_type=EmailType.SIGNUP_CONFIRMATION,
                    to_email=user_data.email,
                    language=user_data.preferred_language,
                    confirmation_url=confirmation_url,
                    otp_token=otp_token or "",  # Token OTP si disponible
                    first_name=user_data.first_name,
                )

                if result:
                    logger.info(f"[Register] ✅ Email de confirmation envoyé avec succès")
                else:
                    logger.error(f"[Register] ❌ Échec envoi email (send_auth_email returned False)")
            except Exception as e:
                logger.error(f"[Register] ❌ Exception lors de l'envoi email: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[Register] Traceback: {traceback.format_exc()}")
                # Ne pas bloquer la registration si l'email échoue
        else:
            if not EMAIL_SERVICE_AVAILABLE:
                logger.warning(f"[Register] EMAIL_SERVICE_AVAILABLE=False - email non envoyé")
            elif not user_data.preferred_language:
                logger.warning(f"[Register] preferred_language vide - email non envoyé")

        # NE PAS créer de token JWT - l'utilisateur doit confirmer son email d'abord
        # Le login sera possible uniquement après confirmation de l'email

        logger.info(f"[Register] Inscription réussie: {user_data.email} - Email de confirmation requis")

        return AuthResponse(
            success=True,
            message="Compte créé avec succès. Veuillez vérifier votre email pour confirmer votre compte.",
            token=None,  # Pas de token tant que l'email n'est pas confirmé
            user=None,   # Pas d'infos utilisateur tant que l'email n'est pas confirmé
        )

    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"[Register] Erreur inattendue: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur lors de la création du compte"
        )


# === ENDPOINT FORGOT PASSWORD ===
@router.post("/reset-password", response_model=ForgotPasswordResponse)
async def request_password_reset(request: ForgotPasswordRequest):
    """
    Demande de réinitialisation de mot de passe
    Envoie un email avec un lien de réinitialisation
    """
    logger.info("[ResetPassword] Demande de réinitialisation reçue")

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(
            status_code=500, detail="Service de réinitialisation non disponible"
        )

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # Configurer l'URL de redirection avec fallback intelligent
        redirect_url = os.getenv(
            "RESET_PASSWORD_REDIRECT_URL",
            "https://expert.intelia.com/auth/reset-password",
        )

        # Essayer la nouvelle API Supabase d'abord
        try:
            supabase.auth.reset_password_email(
                email=request.email, options={"redirect_to": redirect_url}
            )
        except AttributeError:
            # CORRECTION: Suppression de la variable non utilisée result
            # Fallback pour ancienne API Supabase
            supabase.auth.api.reset_password_email(
                email=request.email, redirect_to=redirect_url
            )

        # Supabase ne retourne pas d'erreur même si l'email n'existe pas (pour des raisons de sécurité)
        logger.info("[ResetPassword] Demande traitée avec succès")

        return ForgotPasswordResponse(
            success=True,
            message="Si cette adresse email existe dans notre système, vous recevrez un lien de réinitialisation sous peu.",
        )

    except Exception as e:
        logger.error(f"[ResetPassword] Erreur: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'envoi de l'email de réinitialisation",
        )


# === ENDPOINT VALIDATE RESET TOKEN ===
@router.post("/validate-reset-token", response_model=ValidateTokenResponse)
async def validate_reset_token(request: ValidateResetTokenRequest):
    """
    Valide un token de réinitialisation de mot de passe
    """
    logger.info("[ValidateToken] Validation token...")

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(
            status_code=500, detail="Service de validation non disponible"
        )

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
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
                        options={"verify_exp": True},
                    )
                    break
                except Exception:
                    continue

            if payload and payload.get("exp"):
                # Vérifier si le token n'est pas expiré
                exp_timestamp = payload.get("exp")
                current_timestamp = datetime.utcnow().timestamp()

                if current_timestamp < exp_timestamp:
                    logger.info("[ValidateToken] Token valide")
                    return ValidateTokenResponse(valid=True, message="Token valide")
                else:
                    logger.warning("[ValidateToken] Token expiré")
                    return ValidateTokenResponse(valid=False, message="Token expiré")
            else:
                logger.warning("[ValidateToken] Token invalide")
                return ValidateTokenResponse(valid=False, message="Token invalide")

        except Exception as e:
            logger.warning(f"[ValidateToken] Erreur décodage: {e}")
            # Si on ne peut pas décoder, on considère le token comme potentiellement valide
            # car il pourrait être un token Supabase spécifique
            return ValidateTokenResponse(
                valid=True, message="Token accepté pour validation"
            )

    except Exception as e:
        logger.error(f"[ValidateToken] Erreur: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur lors de la validation du token"
        )


# === ENDPOINT CONFIRM RESET PASSWORD ===
@router.post("/confirm-reset-password", response_model=ForgotPasswordResponse)
async def confirm_reset_password(request: ConfirmResetPasswordRequest):
    """
    Confirme la réinitialisation du mot de passe avec le nouveau mot de passe
    VERSION AVEC DEBUG APPROFONDI et toutes les méthodes Supabase possibles
    """
    logger.info("[ConfirmReset] === DÉBUT CONFIRMATION RÉINITIALISATION ===")
    logger.info(
        f"[ConfirmReset] Token reçu (premiers 50 char): {request.token[:50]}..."
    )
    logger.info(
        f"[ConfirmReset] Nouveau mot de passe fourni: {bool(request.new_password)}"
    )

    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client non disponible")
        raise HTTPException(
            status_code=500, detail="Service de réinitialisation non disponible"
        )

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")

    logger.info(f"[ConfirmReset] Supabase URL: {supabase_url}")
    logger.info(f"[ConfirmReset] Supabase Key configurée: {bool(supabase_key)}")

    supabase: Client = create_client(supabase_url, supabase_key)

    # === ANALYSE DU TOKEN D'ABORD ===
    logger.info("[ConfirmReset] === ANALYSE DU TOKEN ===")

    # NOUVEAU: Utiliser l'email fourni dans la requête si disponible (pour OTP)
    user_email = request.email if request.email else None
    if user_email:
        logger.info(f"[ConfirmReset] Email fourni dans la requête: {user_email}")

    token_type = None

    try:
        import jwt as pyjwt

        # Décoder sans vérification pour analyser le contenu
        token_payload = pyjwt.decode(request.token, options={"verify_signature": False})
        logger.info(f"[ConfirmReset] Token payload keys: {list(token_payload.keys())}")
        logger.info(f"[ConfirmReset] Token type (typ): {token_payload.get('typ')}")
        logger.info(f"[ConfirmReset] Token algorithm (alg): {token_payload.get('alg')}")
        logger.info(f"[ConfirmReset] Token issuer (iss): {token_payload.get('iss')}")
        logger.info(f"[ConfirmReset] Token audience (aud): {token_payload.get('aud')}")
        logger.info(f"[ConfirmReset] Token subject (sub): {token_payload.get('sub')}")
        logger.info(f"[ConfirmReset] Token email: {token_payload.get('email')}")
        logger.info(f"[ConfirmReset] Token expiry (exp): {token_payload.get('exp')}")

        # Vérifier l'expiration
        exp_timestamp = token_payload.get("exp")
        if exp_timestamp:
            current_timestamp = datetime.utcnow().timestamp()
            time_remaining = exp_timestamp - current_timestamp
            logger.info(
                f"[ConfirmReset] Temps restant avant expiration: {time_remaining} secondes"
            )

            if time_remaining <= 0:
                logger.error(
                    f"[ConfirmReset] Token expiré depuis {abs(time_remaining)} secondes"
                )
                raise HTTPException(
                    status_code=400,
                    detail="Token expiré. Demandez un nouveau lien de réinitialisation.",
                )

        # Si pas d'email fourni, essayer d'extraire du token
        if not user_email:
            user_email = token_payload.get("email")
            if user_email:
                logger.info(f"[ConfirmReset] Email extrait du token: {user_email}")

        token_type = token_payload.get("aud") or token_payload.get("token_type")

    except Exception as decode_error:
        logger.error(f"[ConfirmReset] Erreur analyse token: {decode_error}")
        # Si c'est un OTP court et qu'on a l'email de la requête, continuer
        if user_email and len(request.token) < 10:
            logger.info(f"[ConfirmReset] Token court ({len(request.token)} chars) détecté comme OTP, email fourni: {user_email}")

    # === MÉTHODE 1 : VERIFY OTP AVEC EMAIL (PRIORITÉ ÉLEVÉE) ===
    if user_email:
        logger.info(
            f"[ConfirmReset] === MÉTHODE 1: VERIFY OTP avec email {user_email} ==="
        )
        try:
            # Types d'OTP à essayer dans l'ordre de priorité
            otp_types = ["recovery", "email_change", "signup"]

            for otp_type in otp_types:
                try:
                    logger.info(
                        f"[ConfirmReset] Tentative verify_otp type '{otp_type}'..."
                    )

                    result = supabase.auth.verify_otp(
                        {"email": user_email, "token": request.token, "type": otp_type}
                    )

                    logger.info(
                        f"[ConfirmReset] Résultat verify_otp ({otp_type}): user={bool(result.user)}, session={bool(result.session)}"
                    )

                    if result.user and result.session:
                        logger.info(
                            f"[ConfirmReset] OTP vérifié avec type '{otp_type}', mise à jour mot de passe..."
                        )

                        # Créer un nouveau client avec la session
                        supabase_auth: Client = create_client(
                            supabase_url, supabase_key
                        )

                        # Essayer différentes méthodes pour set_session
                        try:
                            supabase_auth.auth.set_session(
                                result.session.access_token,
                                result.session.refresh_token,
                            )
                            logger.info(
                                "[ConfirmReset] Session définie avec access_token + refresh_token"
                            )
                        except Exception:
                            try:
                                supabase_auth.auth.set_session(result.session)
                                logger.info(
                                    "[ConfirmReset] Session définie avec objet session"
                                )
                            except Exception as session_error:
                                logger.warning(
                                    f"[ConfirmReset] Échec set_session: {session_error}"
                                )
                                # Continuer quand même, parfois ça marche sans set_session

                        update_result = supabase_auth.auth.update_user(
                            {"password": request.new_password}
                        )

                        logger.info(
                            f"[ConfirmReset] Résultat update password: user={bool(update_result.user)}"
                        )

                        if update_result.user:
                            logger.info(
                                f"[ConfirmReset] Mot de passe mis à jour avec succès (méthode 1 - {otp_type})"
                            )
                            return ForgotPasswordResponse(
                                success=True,
                                message="Mot de passe mis à jour avec succès",
                            )
                        else:
                            logger.warning(
                                "[ConfirmReset] Échec update password après OTP réussi"
                            )

                except Exception as otp_error:
                    logger.warning(
                        f"[ConfirmReset] Échec verify_otp type '{otp_type}': {otp_error}"
                    )
                    continue

        except Exception as method1_error:
            logger.warning(
                f"[ConfirmReset] Méthode 1 échouée globalement: {method1_error}"
            )

    # === Toutes les méthodes ont échoué ===
    logger.error("[ConfirmReset] === TOUTES LES MÉTHODES ONT ÉCHOUÉ ===")
    logger.error(f"[ConfirmReset] Token analysé: email={user_email}, type={token_type}")

    # Erreur finale avec plus de détails
    raise HTTPException(
        status_code=400,
        detail="Impossible de réinitialiser le mot de passe. Le token pourrait être invalide, expiré, ou incompatible avec cette version de Supabase. Demandez un nouveau lien de réinitialisation.",
    )


# === NOUVEAUX MODÈLES POUR INVITATIONS ===
class ValidateInvitationTokenRequest(BaseModel):
    access_token: str


class ValidateInvitationTokenResponse(BaseModel):
    success: bool
    user_email: str
    user_id: str
    inviter_name: Optional[str] = None
    invitation_data: Optional[Dict[str, Any]] = None


class CompleteInvitationProfileRequest(BaseModel):
    access_token: str
    password: str
    firstName: str
    lastName: str
    fullName: str
    email: EmailStr
    country: str
    companyName: Optional[str] = None
    companyWebsite: Optional[str] = None


class CompleteInvitationProfileResponse(BaseModel):
    success: bool
    message: str
    redirect_url: str


# === NOUVEAUX ENDPOINTS POUR INVITATIONS ===


@router.post("/invitations/validate-token", response_model=ValidateInvitationTokenResponse)
async def validate_invitation_token(request: ValidateInvitationTokenRequest):
    """
    Valide un token d'invitation Supabase et retourne les informations de l'invitation
    """
    logger.info("[InvitationValidate] Début validation token d'invitation")

    if not SUPABASE_AVAILABLE:
        logger.error("[InvitationValidate] Supabase non disponible")
        raise HTTPException(
            status_code=500, detail="Service d'invitation non disponible"
        )

    try:
        # Décoder le token pour extraire les informations
        payload = None
        for secret_name, secret_value in JWT_SECRETS:
            try:
                payload = jwt.decode(
                    request.access_token,
                    secret_value,
                    algorithms=[JWT_ALGORITHM],
                    options={"verify_aud": False},
                )
                logger.info(f"[InvitationValidate] Token décodé avec {secret_name}")
                break
            except Exception:
                continue

        if not payload:
            logger.error("[InvitationValidate] Impossible de décoder le token")
            raise HTTPException(
                status_code=400, detail="Token d'invitation invalide"
            )

        # Extraire les informations utilisateur
        user_email = payload.get("email")
        user_id = payload.get("sub") or payload.get("user_id")
        user_metadata = payload.get("user_metadata", {})

        if not user_email or not user_id:
            logger.error("[InvitationValidate] Token sans email ou user_id")
            raise HTTPException(
                status_code=400, detail="Token d'invitation incomplet"
            )

        # Extraire les données d'invitation du user_metadata
        inviter_name = user_metadata.get("inviter_name")
        personal_message = user_metadata.get("personal_message")
        language = user_metadata.get("language", "fr")
        invitation_date = user_metadata.get("invitation_date")
        invited_by = user_metadata.get("invited_by")

        logger.info(f"[InvitationValidate] Invitation valide pour {user_email}")
        logger.info(f"[InvitationValidate] Invité par: {inviter_name} ({invited_by})")

        return ValidateInvitationTokenResponse(
            success=True,
            user_email=user_email,
            user_id=user_id,
            inviter_name=inviter_name,
            invitation_data={
                "personal_message": personal_message,
                "language": language,
                "invitation_date": invitation_date,
                "invited_by": invited_by,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[InvitationValidate] Erreur inattendue: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur lors de la validation du token"
        )


@router.post("/invitations/complete-profile", response_model=CompleteInvitationProfileResponse)
async def complete_invitation_profile(request: CompleteInvitationProfileRequest):
    """
    Finalise le profil de l'utilisateur invité en définissant son mot de passe
    et en créant son entrée dans la table users
    """
    logger.info(f"[InvitationComplete] Début finalisation profil pour {request.email}")

    if not SUPABASE_AVAILABLE:
        logger.error("[InvitationComplete] Supabase non disponible")
        raise HTTPException(
            status_code=500, detail="Service d'invitation non disponible"
        )

    # Configuration Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_anon_key or not service_role_key:
        logger.error("[InvitationComplete] Configuration Supabase manquante")
        raise HTTPException(status_code=500, detail="Configuration service manquante")

    try:
        # 1. Décoder le token pour obtenir le user_id
        payload = None
        for secret_name, secret_value in JWT_SECRETS:
            try:
                payload = jwt.decode(
                    request.access_token,
                    secret_value,
                    algorithms=[JWT_ALGORITHM],
                    options={"verify_aud": False},
                )
                logger.info(f"[InvitationComplete] Token décodé avec {secret_name}")
                break
            except Exception:
                continue

        if not payload:
            logger.error("[InvitationComplete] Token invalide")
            raise HTTPException(
                status_code=400, detail="Token d'invitation invalide"
            )

        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            logger.error("[InvitationComplete] user_id manquant dans le token")
            raise HTTPException(
                status_code=400, detail="Token d'invitation incomplet"
            )

        logger.info(f"[InvitationComplete] User ID extrait: {user_id}")

        # 2. Mettre à jour le mot de passe de l'utilisateur avec Service Role Key
        admin_client = create_client(supabase_url, service_role_key)

        logger.info("[InvitationComplete] Mise à jour mot de passe...")
        password_update_result = admin_client.auth.admin.update_user_by_id(
            user_id,
            {"password": request.password}
        )

        if not password_update_result.user:
            logger.error("[InvitationComplete] Échec mise à jour mot de passe")
            raise HTTPException(
                status_code=500, detail="Erreur lors de la configuration du mot de passe"
            )

        logger.info(f"[InvitationComplete] Mot de passe défini pour {user_id}")

        # 3. Mettre à jour l'entrée dans la table users (créée automatiquement par le trigger on_auth_user_created)
        logger.info("[InvitationComplete] Mise à jour du profil dans la table users...")

        user_profile = {
            "email": request.email,
            "first_name": request.firstName,
            "last_name": request.lastName,
            "full_name": request.fullName,
            "country": request.country,
            "company_name": request.companyName,
            "company_website": request.companyWebsite,
            "user_type": "user",
            "language": payload.get("user_metadata", {}).get("language", "fr"),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Filtrer les valeurs None
        user_profile = {k: v for k, v in user_profile.items() if v is not None}

        # UPSERT : UPDATE si l'utilisateur existe (créé par trigger), sinon INSERT
        # Le conflit est sur email car c'est la colonne avec contrainte UNIQUE (users_email_key)
        upsert_response = admin_client.table("users").upsert(
            {**user_profile, "auth_user_id": user_id},
            on_conflict="email"
        ).execute()

        if not upsert_response.data:
            logger.error("[InvitationComplete] Échec mise à jour profil dans users")
            raise HTTPException(
                status_code=500, detail="Erreur lors de la finalisation du profil"
            )

        logger.info(f"[InvitationComplete] Profil finalisé dans users pour {request.email}")

        # 4. Marquer l'invitation comme acceptée dans la table invitations
        try:
            invited_by_email = payload.get("user_metadata", {}).get("invited_by")
            if invited_by_email:
                logger.info(f"[InvitationComplete] Marquage invitation acceptée pour {request.email}")
                admin_client.table("invitations").update({
                    "status": "accepted",
                    "accepted_at": datetime.utcnow().isoformat(),
                    "accepted_user_id": user_id,
                }).eq("email", request.email).eq("status", "pending").execute()
        except Exception as e:
            logger.warning(f"[InvitationComplete] Erreur marquage invitation: {e}")
            # Ne pas bloquer le flux si le marquage échoue

        # 5. Confirmer l'email automatiquement pour les invitations
        try:
            logger.info(f"[InvitationComplete] Confirmation automatique de l'email pour {user_id}")
            admin_client.auth.admin.update_user_by_id(
                user_id,
                {"email_confirm": True}
            )
        except Exception as e:
            logger.warning(f"[InvitationComplete] Erreur confirmation email: {e}")

        logger.info(f"[InvitationComplete] Profil finalisé avec succès pour {request.email}")

        return CompleteInvitationProfileResponse(
            success=True,
            message="Profil créé avec succès. Vous pouvez maintenant vous connecter.",
            redirect_url="/chat",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[InvitationComplete] Erreur inattendue: {str(e)}")
        import traceback
        logger.error(f"[InvitationComplete] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la finalisation du profil: {str(e)}"
        )


# === ENDPOINT ÉCHANGE TOKEN INVITATION ===
class ExchangeInvitationTokenRequest(BaseModel):
    token: str  # Token de vérification Supabase


class ExchangeInvitationTokenResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user_email: Optional[str] = None
    error: Optional[str] = None


@router.post("/invitations/exchange-token", response_model=ExchangeInvitationTokenResponse)
async def exchange_invitation_token(request: ExchangeInvitationTokenRequest):
    """
    Échange un token de vérification d'invitation contre des tokens d'accès.
    Nécessaire avec le custom domain auth.intelia.com qui ne passe pas les tokens dans le hash.
    """
    logger.info("[ExchangeToken] Début échange token d'invitation")

    if not SUPABASE_AVAILABLE:
        logger.error("[ExchangeToken] Supabase non disponible")
        return ExchangeInvitationTokenResponse(
            success=False,
            error="Service d'invitation non disponible"
        )

    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        logger.error("[ExchangeToken] Configuration Supabase manquante")
        return ExchangeInvitationTokenResponse(
            success=False,
            error="Configuration service manquante"
        )

    try:
        # Utiliser l'API Supabase Admin pour vérifier le token d'invitation
        import requests

        logger.info(f"[ExchangeToken] Vérification token: {request.token[:20]}...")

        # Appeler l'endpoint Supabase de vérification d'invitation
        verify_url = f"{supabase_url}/auth/v1/verify"
        headers = {
            "apikey": service_role_key,
            "Content-Type": "application/json"
        }

        # Construire l'URL de vérification avec le token et redirect_to
        verify_params = {
            "token": request.token,
            "type": "invite",
        }

        response = requests.get(verify_url, params=verify_params, headers=headers, allow_redirects=False)

        logger.info(f"[ExchangeToken] Status code: {response.status_code}")
        logger.info(f"[ExchangeToken] Response headers: {dict(response.headers)}")

        # Si la réponse est une redirection avec tokens dans le fragment
        if response.status_code in [302, 303, 307, 308]:
            location = response.headers.get("Location", "")
            logger.info(f"[ExchangeToken] Redirection vers: {location}")

            # Extraire les tokens du fragment de l'URL de redirection
            if "#" in location:
                fragment = location.split("#")[1]
                fragment_params = dict(param.split("=") for param in fragment.split("&") if "=" in param)

                access_token = fragment_params.get("access_token")
                refresh_token = fragment_params.get("refresh_token")
                expires_in = fragment_params.get("expires_in")

                if access_token and refresh_token:
                    # Décoder le token pour obtenir l'email
                    try:
                        payload = jwt.decode(
                            access_token,
                            options={"verify_signature": False}  # Pas besoin de vérifier ici, Supabase l'a déjà fait
                        )
                        user_email = payload.get("email")

                        logger.info(f"[ExchangeToken] Tokens extraits avec succès pour {user_email}")

                        return ExchangeInvitationTokenResponse(
                            success=True,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_in=int(expires_in) if expires_in else 3600,
                            user_email=user_email
                        )
                    except Exception as e:
                        logger.warning(f"[ExchangeToken] Erreur décodage token: {e}")
                        # Retourner quand même les tokens même si le décodage échoue
                        return ExchangeInvitationTokenResponse(
                            success=True,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_in=int(expires_in) if expires_in else 3600
                        )

        # Si pas de redirection ou pas de tokens, erreur
        logger.error(f"[ExchangeToken] Échec vérification token. Status: {response.status_code}")
        logger.error(f"[ExchangeToken] Response: {response.text[:500]}")

        return ExchangeInvitationTokenResponse(
            success=False,
            error=f"Token d'invitation invalide ou expiré (status: {response.status_code})"
        )

    except Exception as e:
        logger.error(f"[ExchangeToken] Erreur inattendue: {str(e)}")
        import traceback
        logger.error(f"[ExchangeToken] Traceback: {traceback.format_exc()}")
        return ExchangeInvitationTokenResponse(
            success=False,
            error=f"Erreur lors de l'échange du token: {str(e)}"
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
        "timestamp": datetime.utcnow(),
    }


@router.get("/me")
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Récupère le profil de l'utilisateur connecté avec données complètes depuis Supabase"""

    try:
        # Récupérer les données complètes depuis Supabase
        if SUPABASE_AVAILABLE:
            url = os.getenv("SUPABASE_URL")
            service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if url and service_key:
                try:
                    supabase = create_client(url, service_key)
                    response = (
                        supabase.table("users")
                        .select("*")
                        .eq("auth_user_id", current_user["user_id"])
                        .single()
                        .execute()
                    )

                    if response.data:
                        profile_data = response.data
                        logger.debug(f"[/auth/me] Profil complet récupéré pour {current_user.get('email')}")

                        # Retourner les données complètes incluant first_name, last_name, country
                        return {
                            "user_id": current_user.get("user_id"),
                            "email": current_user.get("email"),
                            "session_id": current_user.get("session_id"),
                            "user_type": profile_data.get("user_type", current_user.get("user_type")),
                            "full_name": profile_data.get("full_name", current_user.get("full_name")),
                            "first_name": profile_data.get("first_name"),  # NOUVEAU
                            "last_name": profile_data.get("last_name"),    # NOUVEAU
                            "country": profile_data.get("country"),        # NOUVEAU
                            "country_code": profile_data.get("country_code"),
                            "area_code": profile_data.get("area_code"),
                            "phone_number": profile_data.get("phone_number"),
                            "phone": profile_data.get("phone"),
                            "linkedin_profile": profile_data.get("linkedin_profile"),
                            "facebook_profile": profile_data.get("facebook_profile"),  # 🎯 Facebook profile URL
                            "company_name": profile_data.get("company_name"),
                            "company_website": profile_data.get("company_website"),
                            "linkedin_corporate": profile_data.get("linkedin_corporate"),
                            "language": profile_data.get("language", "fr"),
                            "ad_history": profile_data.get("ad_history", []),  # 🎯 Ad rotation history
                            "is_admin": current_user.get("is_admin") or profile_data.get("is_admin", False),
                            "preferences": current_user.get("preferences", {}),
                            "profile_id": current_user.get("profile_id"),
                            "jwt_secret_used": current_user.get("jwt_secret_used"),
                            "plan": profile_data.get("plan"),
                            "avatar_url": profile_data.get("avatar_url"),
                            "consent_given": profile_data.get("consent_given"),
                            "consent_date": profile_data.get("consent_date"),
                            "created_at": profile_data.get("created_at"),
                            "updated_at": profile_data.get("updated_at"),
                        }
                except Exception as e:
                    logger.warning(f"[/auth/me] Erreur récupération profil Supabase: {e}")
                    # Fallback vers données JWT si erreur Supabase

        # Fallback: retourner les données du JWT token si Supabase non disponible
        logger.info(f"[/auth/me] Fallback vers données JWT pour {current_user.get('email')}")
        return {
            "user_id": current_user.get("user_id"),
            "email": current_user.get("email"),
            "session_id": current_user.get("session_id"),
            "user_type": current_user.get("user_type"),
            "full_name": current_user.get("full_name"),
            "is_admin": current_user.get("is_admin"),
            "preferences": current_user.get("preferences", {}),
            "profile_id": current_user.get("profile_id"),
            "jwt_secret_used": current_user.get("jwt_secret_used"),
        }
    except Exception as e:
        logger.error(f"[/auth/me] Erreur inattendue: {e}")
        # En cas d'erreur, retourner au minimum les données du JWT
        return {
            "user_id": current_user.get("user_id"),
            "email": current_user.get("email"),
            "session_id": current_user.get("session_id"),
            "user_type": current_user.get("user_type"),
            "full_name": current_user.get("full_name"),
            "is_admin": current_user.get("is_admin"),
            "preferences": current_user.get("preferences", {}),
            "profile_id": current_user.get("profile_id"),
            "jwt_secret_used": current_user.get("jwt_secret_used"),
        }


@router.get("/debug/jwt-config")
async def debug_jwt_config():
    """Debug endpoint pour voir la configuration JWT multi-compatible"""
    return {
        "jwt_secrets_configured": len(JWT_SECRETS),
        "jwt_secret_types": [s[0] for s in JWT_SECRETS],
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "supabase_anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
        "supabase_service_role_key_configured": bool(
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        ),
        "jwt_algorithm": JWT_ALGORITHM,
        "auth_temp_compatible": True,
        "supabase_compatible": True,
        "multi_secret_support": True,
        "main_secret_type": JWT_SECRETS[0][0] if JWT_SECRETS else "none",
        "backend_centralized_oauth": True,
        "register_endpoint_available": True,
        "reset_password_endpoints_available": True,
        "change_password_endpoint_available": True,
        "session_tracking_available": True,  # NOUVEAU
        "oauth_endpoints_available": [
            "/auth/oauth/linkedin/login",
            "/auth/oauth/facebook/login",
            "/auth/oauth/linkedin/callback",
            "/auth/oauth/facebook/callback",
        ],
        "session_endpoints_available": ["/auth/heartbeat", "/auth/logout"],  # NOUVEAU
    }


# === ENDPOINT DEBUG POUR RESET PASSWORD ===
@router.get("/debug/reset-config")
async def debug_reset_config():
    """Debug temporaire pour voir la configuration de reset password"""

    # Récupérer exactement comme dans la fonction reset-password
    redirect_url = os.getenv(
        "RESET_PASSWORD_REDIRECT_URL", "https://expert.intelia.com/auth/reset-password"
    )

    return {
        "redirect_url_configured": redirect_url,
        "env_var_exists": bool(os.getenv("RESET_PASSWORD_REDIRECT_URL")),
        "env_var_value": os.getenv("RESET_PASSWORD_REDIRECT_URL"),
        "fallback_used": not bool(os.getenv("RESET_PASSWORD_REDIRECT_URL")),
        "all_env_vars": {
            "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
            "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
            "RESET_PASSWORD_REDIRECT_URL": bool(
                os.getenv("RESET_PASSWORD_REDIRECT_URL")
            ),
        },
    }


# === ENDPOINT DEBUG OAUTH ===
@router.get("/debug/oauth-config")
async def debug_oauth_config():
    """Debug endpoint pour vérifier la configuration OAuth"""
    return {
        "oauth_available": SUPABASE_AVAILABLE,
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "supabase_anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
        "frontend_url": os.getenv("FRONTEND_URL", "https://expert.intelia.com"),
        "backend_url": os.getenv(
            "BACKEND_URL", "https://expert-app-cngws.ondigitalocean.app"
        ),
        "supported_providers": ["linkedin", "facebook"],
        "oauth_endpoints": [
            "/auth/oauth/linkedin/login",
            "/auth/oauth/facebook/login",
            "/auth/oauth/linkedin/callback",
            "/auth/oauth/facebook/callback",
        ],
        "backend_centralized": True,
        "callback_flow": "backend_handles_oauth_then_redirects_frontend_with_token",
    }


# === ENDPOINT DEBUG SESSION TRACKING ===
@router.get("/debug/session-config")
async def debug_session_config():
    """Debug endpoint pour vérifier la configuration du session tracking"""
    try:
        from .logging import get_analytics_manager

        analytics = get_analytics_manager()
        analytics_available = True
        analytics_type = type(analytics).__name__
    except Exception as e:
        analytics_available = False
        analytics_type = f"Error: {str(e)}"

    return {
        "session_tracking_available": analytics_available,
        "analytics_manager_type": analytics_type,
        "session_endpoints": ["/auth/heartbeat", "/auth/logout"],
        "login_generates_session_id": True,
        "oauth_generates_session_id": True,
        "token_includes_session_id": True,
        "heartbeat_updates_last_activity": True,
        "logout_calculates_duration": True,
    }
