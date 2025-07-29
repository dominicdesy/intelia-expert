# app/api/v1/invitations.py
"""
Router Invitations pour Intelia Expert
Version intégrée avec main.py v3.5.0
Support UTF-8 complet et templates multilingues
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime
import logging
import os
from app.core.auth import get_current_user
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invitations", tags=["invitations"])

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
            return 'fr'  # Langue par défaut
        return v

class InvitationResponse(BaseModel):
    success: bool
    sent_count: int
    failed_emails: List[str] = []
    message: str

# ==================== SERVICE EMAIL ====================
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
            
            <!-- Features -->
            <div style="background-color: #f9fafb; padding: 25px; border-radius: 8px; margin: 25px 0;">
                <h3 style="color: #1f2937; margin-top: 0; margin-bottom: 20px;">✨ Avec Intelia Expert, vous pouvez :</h3>
                <ul style="color: #4b5563; padding-left: 0; list-style: none;">
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">🎯</span>
                        Poser des questions d'expert en santé animale 24/7
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">📚</span>
                        Accéder à une base de connaissances spécialisée
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">🌍</span>
                        Obtenir des réponses en français, anglais ou espagnol
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">📱</span>
                        Utiliser l'interface sur mobile, tablette et ordinateur
                    </li>
                </ul>
            </div>
            
            <!-- CTA Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{signup_url}" 
                   style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; text-decoration: none; padding: 15px 30px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                    🚀 Créer mon compte gratuitement
                </a>
                <p style="color: #6b7280; font-size: 14px; margin-top: 15px;">
                    Inscription rapide - Aucune carte de crédit requise
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p style="margin: 10px 0;">
                    Cet email vous a été envoyé par <strong>{inviter_name}</strong> via Intelia Expert
                </p>
                <p style="margin: 10px 0;">
                    <a href="https://www.intelia.com" style="color: #3b82f6; text-decoration: none;">www.intelia.com</a> | 
                    <a href="mailto:support@intelia.com" style="color: #3b82f6; text-decoration: none;">support@intelia.com</a>
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
        
        personal_section = ""
        if personal_message.strip():
            personal_section = f"\n\nMessage personnel de {inviter_name} :\n{personal_message}\n"
        
        return f"""
Bonjour !

{inviter_name} vous invite à découvrir Intelia Expert, le premier assistant IA spécialisé en santé et nutrition animale.

{personal_section}

Avec Intelia Expert, vous pouvez :
• Poser des questions d'expert en santé animale 24/7
• Accéder à une base de connaissances spécialisée  
• Obtenir des réponses en français, anglais ou espagnol
• Utiliser l'interface sur mobile, tablette et ordinateur

Créer votre compte gratuitement : {signup_url}

Cet email vous a été envoyé par {inviter_name} via Intelia Expert.
www.intelia.com | support@intelia.com

© 2024 Intelia Inc. Tous droits réservés.
        """
    
    def _get_english_template(self, inviter_name: str, personal_message: str) -> str:
        # Template similaire en anglais
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        
        personal_section = ""
        if personal_message.strip():
            personal_section = f"""
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6;">
                <h3 style="color: #1e40af; margin-top: 0;">Personal message from {inviter_name}:</h3>
                <p style="color: #374151; font-style: italic; margin-bottom: 0;">{personal_message}</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 12px;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 600;">🚀 Intelia Expert</h1>
                <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 16px;">AI specialized in animal health and nutrition</p>
            </div>
            
            <div style="margin-bottom: 30px;">
                <h2 style="color: #1f2937; margin-bottom: 15px;">Hello! 👋</h2>
                <p style="color: #4b5563; font-size: 16px; margin-bottom: 15px;">
                    <strong>{inviter_name}</strong> invites you to discover <strong>Intelia Expert</strong>, 
                    the first AI assistant specialized in animal health and nutrition.
                </p>
            </div>
            
            {personal_section}
            
            <div style="background-color: #f9fafb; padding: 25px; border-radius: 8px; margin: 25px 0;">
                <h3 style="color: #1f2937; margin-top: 0; margin-bottom: 20px;">✨ With Intelia Expert, you can:</h3>
                <ul style="color: #4b5563; padding-left: 0; list-style: none;">
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">🎯</span>
                        Ask expert questions about animal health 24/7
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">📚</span>
                        Access a specialized knowledge base
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">🌍</span>
                        Get answers in French, English, or Spanish
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">📱</span>
                        Use the interface on mobile, tablet, and computer
                    </li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{signup_url}" 
                   style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; text-decoration: none; padding: 15px 30px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                    🚀 Create my free account
                </a>
                <p style="color: #6b7280; font-size: 14px; margin-top: 15px;">
                    Quick registration - No credit card required
                </p>
            </div>
            
            <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p style="margin: 10px 0;">
                    This email was sent by <strong>{inviter_name}</strong> via Intelia Expert
                </p>
                <p style="margin: 10px 0;">
                    <a href="https://www.intelia.com" style="color: #3b82f6; text-decoration: none;">www.intelia.com</a> | 
                    <a href="mailto:support@intelia.com" style="color: #3b82f6; text-decoration: none;">support@intelia.com</a>
                </p>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #9ca3af;">
                    © 2024 Intelia Inc. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
    
    def _get_english_text_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        
        personal_section = ""
        if personal_message.strip():
            personal_section = f"\n\nPersonal message from {inviter_name}:\n{personal_message}\n"
        
        return f"""
Hello!

{inviter_name} invites you to discover Intelia Expert, the first AI assistant specialized in animal health and nutrition.

{personal_section}

With Intelia Expert, you can:
• Ask expert questions about animal health 24/7
• Access a specialized knowledge base
• Get answers in French, English, or Spanish
• Use the interface on mobile, tablet, and computer

Create your free account: {signup_url}

This email was sent by {inviter_name} via Intelia Expert.
www.intelia.com | support@intelia.com

© 2024 Intelia Inc. All rights reserved.
        """
    
    def _get_spanish_template(self, inviter_name: str, personal_message: str) -> str:
        # Template similaire en espagnol
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        
        personal_section = ""
        if personal_message.strip():
            personal_section = f"""
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6;">
                <h3 style="color: #1e40af; margin-top: 0;">Mensaje personal de {inviter_name}:</h3>
                <p style="color: #374151; font-style: italic; margin-bottom: 0;">{personal_message}</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 12px;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 600;">🚀 Intelia Expert</h1>
                <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 16px;">IA especializada en salud y nutrición animal</p>
            </div>
            
            <div style="margin-bottom: 30px;">
                <h2 style="color: #1f2937; margin-bottom: 15px;">¡Hola! 👋</h2>
                <p style="color: #4b5563; font-size: 16px; margin-bottom: 15px;">
                    <strong>{inviter_name}</strong> te invita a descubrir <strong>Intelia Expert</strong>, 
                    el primer asistente IA especializado en salud y nutrición animal.
                </p>
            </div>
            
            {personal_section}
            
            <div style="background-color: #f9fafb; padding: 25px; border-radius: 8px; margin: 25px 0;">
                <h3 style="color: #1f2937; margin-top: 0; margin-bottom: 20px;">✨ Con Intelia Expert, puedes:</h3>
                <ul style="color: #4b5563; padding-left: 0; list-style: none;">
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">🎯</span>
                        Hacer preguntas expertas sobre salud animal 24/7
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">📚</span>
                        Acceder a una base de conocimiento especializada
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">🌍</span>
                        Obtener respuestas en francés, inglés o español
                    </li>
                    <li style="margin: 12px 0; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: #10b981;">📱</span>
                        Usar la interfaz en móvil, tableta y computadora
                    </li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{signup_url}" 
                   style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; text-decoration: none; padding: 15px 30px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                    🚀 Crear mi cuenta gratuita
                </a>
                <p style="color: #6b7280; font-size: 14px; margin-top: 15px;">
                    Registro rápido - No se requiere tarjeta de crédito
                </p>
            </div>
            
            <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p style="margin: 10px 0;">
                    Este email fue enviado por <strong>{inviter_name}</strong> vía Intelia Expert
                </p>
                <p style="margin: 10px 0;">
                    <a href="https://www.intelia.com" style="color: #3b82f6; text-decoration: none;">www.intelia.com</a> | 
                    <a href="mailto:support@intelia.com" style="color: #3b82f6; text-decoration: none;">support@intelia.com</a>
                </p>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #9ca3af;">
                    © 2024 Intelia Inc. Todos los derechos reservados.
                </p>
            </div>
        </body>
        </html>
        """
    
    def _get_spanish_text_template(self, inviter_name: str, personal_message: str) -> str:
        signup_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com") + "/register"
        
        personal_section = ""
        if personal_message.strip():
            personal_section = f"\n\nMensaje personal de {inviter_name}:\n{personal_message}\n"
        
        return f"""
¡Hola!

{inviter_name} te invita a descubrir Intelia Expert, el primer asistente IA especializado en salud y nutrición animal.

{personal_section}

Con Intelia Expert, puedes:
• Hacer preguntas expertas sobre salud animal 24/7
• Acceder a una base de conocimiento especializada
• Obtener respuestas en francés, inglés o español
• Usar la interfaz en móvil, tableta y computadora

Crear tu cuenta gratuita: {signup_url}

Este email fue enviado por {inviter_name} vía Intelia Expert.
www.intelia.com | support@intelia.com

© 2024 Intelia Inc. Todos los derechos reservados.
        """
    
    async def send_invitation_email(self, to_email: str, inviter_name: str, personal_message: str, language: str) -> bool:
        """Envoie un email d'invitation"""
        try:
            # Obtenir le template selon la langue
            template = self.get_email_template(language, inviter_name, personal_message)
            
            # Créer le message email
            msg = MimeMultipart('alternative')
            msg['Subject'] = template['subject']
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Reply-To'] = self.from_email
            
            # Ajouter les parties texte et HTML
            text_part = MimeText(template['text_body'], 'plain', 'utf-8')
            html_part = MimeText(template['html_body'], 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Envoyer l'email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Invitation envoyée avec succès à {to_email} de la part de {inviter_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi invitation à {to_email}: {str(e)}")
            return False

# ==================== ENDPOINT ====================
@router.post("/send", response_model=InvitationResponse)
async def send_invitations(
    request: InvitationRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Envoie des invitations par email
    
    - **emails**: Liste d'adresses email (max 10)
    - **personal_message**: Message personnel optionnel (max 500 caractères)
    - **inviter_name**: Nom de la personne qui invite
    - **inviter_email**: Email de la personne qui invite
    - **language**: Langue de l'invitation (fr, en, es)
    """
    
    logger.info(f"📧 [send_invitations] Demande d'invitation de {request.inviter_email} pour {len(request.emails)} destinataires")
    
    # Vérifier que l'utilisateur connecté correspond à l'inviteur
    if current_user.email != request.inviter_email:
        logger.warning(f"⚠️ Tentative d'usurpation: {current_user.email} tente d'envoyer pour {request.inviter_email}")
        raise HTTPException(
            status_code=403, 
            detail="Vous ne pouvez envoyer des invitations qu'en votre nom"
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
                
                # Log dans la base de données (optionnel)
                try:
                    # Ici, vous pouvez enregistrer l'invitation dans la DB
                    # invitation_record = {
                    #     'inviter_id': current_user.id,
                    #     'inviter_email': request.inviter_email,
                    #     'invited_email': email,
                    #     'sent_at': datetime.utcnow(),
                    #     'language': request.language,
                    #     'has_personal_message': bool(request.personal_message.strip())
                    # }
                    # db.add(InvitationModel(**invitation_record))
                    # db.commit()
                    pass
                except Exception as db_error:
                    logger.warning(f"⚠️ Erreur sauvegarde DB pour {email}: {db_error}")
                    # Ne pas faire échouer l'envoi si la DB échoue
                    
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

# ==================== ENDPOINT STATISTIQUES (OPTIONNEL) ====================
@router.get("/stats")
async def get_invitation_stats(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Obtient les statistiques d'invitations de l'utilisateur"""
    
    # Ici vous pouvez implémenter les statistiques depuis la DB
    # total_sent = db.query(InvitationModel).filter(
    #     InvitationModel.inviter_id == current_user.id
    # ).count()
    
    return {
        "total_sent": 0,  # total_sent
        "this_month": 0,
        "last_sent": None
    }