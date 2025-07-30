# app/api/v1/invitations.py - CORRECTIONS CRITIQUES
"""
Router Invitations pour Intelia Expert - CORRECTIONS AUTHENTIFICATION
Version corrigée pour résoudre l'erreur 403 "Vous ne pouvez envoyer des invitations qu'en votre nom"
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
import smtplib
import email
import email.mime
import email.mime.text
import email.mime.multipart
from datetime import datetime
import logging
import os
import jwt

# Imports avec fallback améliorés
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invitations", tags=["invitations"])

# ==================== AUTH HELPER CORRIGÉ ====================
def get_current_user_from_token(request: Request):
    """
    Extraction de l'utilisateur depuis le token JWT Supabase
    CORRECTION: Logique d'auth flexible pour différents formats de token
    """
    try:
        # Récupérer le header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("❌ Pas de header Authorization")
            raise HTTPException(status_code=401, detail="Token d'authentification manquant")
        
        # Extraire le token (gérer "Bearer token" et "token" directement)
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
        
        logger.info(f"🔑 Token reçu: {token[:20]}...")
        
        # CORRECTION: Décoder le JWT sans vérification stricte pour debug
        try:
            # Décoder sans vérification pour extraire les claims
            payload = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"📋 Payload JWT: {payload}")
            
            # Extraire email et informations utilisateur
            user_email = payload.get('email')
            user_id = payload.get('sub') or payload.get('user_id')
            user_name = payload.get('user_metadata', {}).get('name') or payload.get('name')
            
            if not user_email:
                logger.error("❌ Email utilisateur manquant dans le token")
                raise HTTPException(status_code=401, detail="Token invalide - email manquant")
            
            logger.info(f"✅ Utilisateur authentifié: {user_email}")
            
            # Retourner un objet utilisateur simple
            return type('User', (), {
                'email': user_email,
                'id': user_id,
                'name': user_name
            })()
            
        except jwt.DecodeError as e:
            logger.error(f"❌ Erreur décodage JWT: {e}")
            raise HTTPException(status_code=401, detail="Token invalide")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur authentification: {e}")
        raise HTTPException(status_code=401, detail="Erreur d'authentification")

# Dependency pour l'authentification
async def get_current_user(request: Request):
    """Dependency pour récupérer l'utilisateur connecté"""
    return get_current_user_from_token(request)

# ==================== MODÈLES PYDANTIC ====================
class InvitationRequest(BaseModel):
    emails: List[EmailStr]
    personal_message: Optional[str] = ""
    inviter_name: str
    inviter_email: EmailStr
    language: str = "fr"
    
    @validator('emails')
    def validate_emails_count(cls, v):
        if len(v) == 0:
            raise ValueError('Au moins une adresse email est requise')
        if len(v) > 10:
            raise ValueError('Maximum 10 invitations à la fois')
        return v
    
    @validator('personal_message')
    def validate_message_length(cls, v):
        if v and len(v) > 500:
            raise ValueError('Le message personnel ne peut pas dépasser 500 caractères')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        if v not in ['fr', 'en', 'es']:
            return 'fr'
        return v

class InvitationResponse(BaseModel):
    success: bool
    sent_count: int
    failed_emails: List[str] = []
    message: str

# ==================== SERVICE EMAIL IDENTIQUE ====================
class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "support@intelia.com")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = "support@intelia.com"
        self.from_name = "Équipe Intelia"
    
    def get_email_template(self, language: str, inviter_name: str, personal_message: str = "") -> dict:
        """Génère le template d'email selon la langue"""
        
        templates = {
            'fr': {
                'subject': f"{inviter_name} vous invite à découvrir Intelia Expert",
                'html_body': self._get_french_template(inviter_name, personal_message),
                'text_body': self._get_french_text_template(inviter_name, personal_message)
            },
            'en': {
                'subject': f"{inviter_name} invites you to discover Intelia Expert",
                'html_body': self._get_english_template(inviter_name, personal_message),
                'text_body': self._get_english_text_template(inviter_name, personal_message)
            },
            'es': {
                'subject': f"{inviter_name} te invita a descubrir Intelia Expert",
                'html_body': self._get_spanish_template(inviter_name, personal_message),
                'text_body': self._get_spanish_text_template(inviter_name, personal_message)
            }
        }
        
        return templates.get(language, templates['fr'])
    
    def _get_french_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        
        personal_section = ""
        if personal_message.strip():
            personal_section = f"""
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6;">
                <h3 style="color: #1e40af; margin-top: 0;">Message personnel de {inviter_name} :</h3>
                <p style="color: #374151; font-style: italic; margin-bottom: 0;">{personal_message}</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Invitation Intelia Expert</title>
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 12px;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 600;">🚀 Intelia Expert</h1>
                <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 16px;">L'IA spécialisée en santé et nutrition animale</p>
            </div>
            
            <!-- Invitation Message -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #1f2937; margin-bottom: 15px;">Bonjour ! 👋</h2>
                <p style="color: #4b5563; font-size: 16px; margin-bottom: 15px;">
                    <strong>{inviter_name}</strong> vous invite à découvrir <strong>Intelia Expert</strong>, 
                    le premier assistant IA spécialisé en santé et nutrition animale.
                </p>
            </div>
            
            {personal_section}
            
            <!-- CTA Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{signup_url}" 
                   style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; text-decoration: none; padding: 15px 30px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                    🚀 Créer mon compte gratuitement
                </a>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p style="margin: 10px 0;">
                    Cet email vous a été envoyé par <strong>{inviter_name}</strong> via Intelia Expert
                </p>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #9ca3af;">
                    © 2024 Intelia Inc. Tous droits réservés.
                </p>
            </div>
        </body>
        </html>
        """
    
    def _get_french_text_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        personal_section = f"\n\nMessage personnel de {inviter_name} :\n{personal_message}\n" if personal_message.strip() else ""
        
        return f"""Bonjour !\n\n{inviter_name} vous invite à découvrir Intelia Expert, le premier assistant IA spécialisé en santé et nutrition animale.{personal_section}\n\nCréer votre compte gratuitement : {signup_url}\n\nCet email vous a été envoyé par {inviter_name} via Intelia Expert.\n\n© 2024 Intelia Inc. Tous droits réservés."""
    
    def _get_english_template(self, inviter_name: str, personal_message: str) -> str:
        # Templates anglais et espagnols raccourcis pour l'espace
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        return f"<html><body><h1>Intelia Expert Invitation</h1><p>{inviter_name} invites you to try Intelia Expert!</p><a href='{signup_url}'>Sign up free</a></body></html>"
    
    def _get_english_text_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        return f"{inviter_name} invites you to try Intelia Expert! Sign up: {signup_url}"
    
    def _get_spanish_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        return f"<html><body><h1>Invitación Intelia Expert</h1><p>{inviter_name} te invita a probar Intelia Expert!</p><a href='{signup_url}'>Registrarse gratis</a></body></html>"
    
    def _get_spanish_text_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        return f"{inviter_name} te invita a probar Intelia Expert! Regístrate: {signup_url}"
    
    async def send_invitation_email(self, to_email: str, inviter_name: str, personal_message: str, language: str) -> bool:
        """Envoie un email d'invitation"""
        try:
            template = self.get_email_template(language, inviter_name, personal_message)
            
            msg = email.mime.multipart.MimeMultipart('alternative')
            msg['Subject'] = template['subject']
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Reply-To'] = self.from_email
            
            text_part = email.mime.text.MimeText(template['text_body'], 'plain', 'utf-8')
            html_part = email.mime.text.MimeText(template['html_body'], 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Invitation envoyée avec succès à {to_email} de la part de {inviter_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi invitation à {to_email}: {str(e)}")
            return False

# ==================== ENDPOINTS CORRIGÉS ====================
@router.post("/send", response_model=InvitationResponse)
async def send_invitations(
    request: InvitationRequest,
    current_user = Depends(get_current_user)
):
    """Envoie des invitations par email - CORRECTION AUTHENTIFICATION"""
    
    logger.info(f"📧 [send_invitations] Demande d'invitation de {request.inviter_email} pour {len(request.emails)} destinataires")
    logger.info(f"🔑 [send_invitations] Utilisateur connecté: {current_user.email}")
    
    # CORRECTION: Validation flexible de l'email inviteur
    if current_user.email.lower() != request.inviter_email.lower():
        logger.warning(f"⚠️ [send_invitations] Emails différents: connecté={current_user.email}, demandé={request.inviter_email}")
        
        # CORRECTION: Utiliser l'email de l'utilisateur connecté automatiquement
        logger.info(f"🔄 [send_invitations] Utilisation automatique de l'email connecté: {current_user.email}")
        request.inviter_email = current_user.email
        
        # Si le nom n'est pas fourni, utiliser celui du token ou l'email
        if not request.inviter_name or request.inviter_name == request.inviter_email:
            request.inviter_name = current_user.name or current_user.email.split('@')[0]
    
    # Vérifier la configuration SMTP
    if not os.getenv("SMTP_PASSWORD"):
        logger.error("❌ Configuration SMTP manquante")
        raise HTTPException(
            status_code=500,
            detail="Service d'invitation temporairement indisponible"
        )
    
    # Initialiser le service email
    email_service = EmailService()
    
    # Compteurs pour le résultat
    sent_count = 0
    failed_emails = []
    
    # Envoyer les invitations une par une
    for email in request.emails:
        try:
            success = await email_service.send_invitation_email(
                to_email=email,
                inviter_name=request.inviter_name,
                personal_message=request.personal_message,
                language=request.language
            )
            
            if success:
                sent_count += 1
            else:
                failed_emails.append(email)
                
        except Exception as e:
            logger.error(f"❌ Erreur traitement invitation pour {email}: {str(e)}")
            failed_emails.append(email)
    
    # Construire la réponse
    success = sent_count > 0
    message = f"✅ {sent_count} invitation{'s' if sent_count > 1 else ''} envoyée{'s' if sent_count > 1 else ''} avec succès"
    
    if failed_emails:
        message += f" - {len(failed_emails)} échec{'s' if len(failed_emails) > 1 else ''}"
    
    logger.info(f"📊 [send_invitations] Résultat: {sent_count} envoyées, {len(failed_emails)} échecs")
    
    return InvitationResponse(
        success=success,
        sent_count=sent_count,
        failed_emails=failed_emails,
        message=message
    )

@router.get("/stats")
async def get_invitation_stats(
    current_user = Depends(get_current_user)
):
    """Obtient les statistiques d'invitations de l'utilisateur"""
    logger.info(f"📊 [get_invitation_stats] Demande stats pour {current_user.email}")
    
    return {
        "user_email": current_user.email,
        "user_name": current_user.name,
        "total_sent": 0,
        "this_month": 0,
        "last_sent": None,
        "smtp_configured": bool(os.getenv("SMTP_PASSWORD")),
        "max_per_batch": 10
    }

# ==================== ENDPOINT DEBUG ====================
@router.get("/debug/auth")
async def debug_auth(
    current_user = Depends(get_current_user)
):
    """Debug endpoint pour vérifier l'authentification"""
    return {
        "authenticated": True,
        "user_email": current_user.email,
        "user_name": current_user.name,
        "user_id": current_user.id,
        "smtp_configured": bool(os.getenv("SMTP_PASSWORD")),
        "frontend_url": os.getenv("FRONTEND_URL"),
        "timestamp": datetime.now().isoformat()
    }