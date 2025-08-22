# app/api/v1/invitations_supabase.py - VERSION SUPABASE
"""
Router Invitations pour Intelia Expert - VERSION SUPABASE NATIVE
Utilise les invitations intégrées de Supabase Auth
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os
import jwt

# Imports Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invitations", tags=["invitations"])

# ==================== CONFIGURATION SUPABASE ====================
def get_supabase_client() -> Client:
    """Initialise le client Supabase avec Service Role pour les invitations"""
    if not SUPABASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Supabase non disponible")
    
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL manquante")
    
    if not service_key:
        raise HTTPException(
            status_code=500, 
            detail="SUPABASE_SERVICE_ROLE_KEY manquante - nécessaire pour les invitations"
        )
    
    return create_client(url, service_key)

def get_supabase_anon_client() -> Client:
    """Client Supabase avec clé anonyme pour les opérations standard"""
    if not SUPABASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Supabase non disponible")
    
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not anon_key:
        raise HTTPException(status_code=500, detail="Configuration Supabase de base manquante")
    
    return create_client(url, anon_key)

# ==================== AUTH HELPER ====================
def get_current_user_from_token(request: Request):
    """Extraction de l'utilisateur depuis le token JWT Supabase"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token d'authentification manquant")
        
        token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header
        
        # Décoder le JWT sans vérification pour extraire les claims
        payload = jwt.decode(token, options={"verify_signature": False})
        
        user_email = payload.get('email')
        user_id = payload.get('sub') or payload.get('user_id')
        user_name = payload.get('user_metadata', {}).get('name') or payload.get('name')
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Token invalide - email manquant")
        
        return type('User', (), {
            'email': user_email,
            'id': user_id,
            'name': user_name
        })()
        
    except Exception as e:
        logger.error(f"❌ Erreur authentification: {e}")
        raise HTTPException(status_code=401, detail="Erreur d'authentification")

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

class InvitationResponse(BaseModel):
    success: bool
    sent_count: int
    failed_emails: List[str] = []
    message: str
    invitation_details: List[Dict[str, Any]] = []

class InvitationStatus(BaseModel):
    email: str
    status: str  # 'pending', 'accepted', 'expired'
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    invited_by: str

# ==================== SERVICE SUPABASE INVITATIONS ====================
class SupabaseInvitationService:
    def __init__(self):
        self.admin_client = get_supabase_client()  # Service role pour invitations
        self.anon_client = get_supabase_anon_client()  # Clé anon pour autres opérations
        self.frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
    
    def get_invitation_template_data(self, language: str, inviter_name: str, personal_message: str = "") -> Dict[str, str]:
        """Prépare les données pour le template d'email"""
        
        templates = {
            'fr': {
                'subject': f"{inviter_name} vous invite à découvrir Intelia Expert",
                'title': "🚀 Invitation Intelia Expert",
                'greeting': f"Bonjour ! {inviter_name} vous invite à découvrir Intelia Expert",
                'description': "Le premier assistant IA spécialisé en santé et nutrition animale",
                'cta_text': "Créer mon compte gratuitement",
                'features_title': "✨ Avec Intelia Expert, vous pouvez :",
                'features': [
                    "🎯 Poser des questions d'expert en santé animale 24/7",
                    "📚 Accéder à une base de connaissances spécialisée",
                    "🌍 Obtenir des réponses en français, anglais ou espagnol",
                    "📱 Utiliser l'interface sur mobile, tablette et ordinateur"
                ]
            },
            'en': {
                'subject': f"{inviter_name} invites you to discover Intelia Expert",
                'title': "🚀 Intelia Expert Invitation",
                'greeting': f"Hello! {inviter_name} invites you to discover Intelia Expert",
                'description': "The first AI assistant specialized in animal health and nutrition",
                'cta_text': "Create my free account",
                'features_title': "✨ With Intelia Expert, you can:",
                'features': [
                    "🎯 Ask expert questions about animal health 24/7",
                    "📚 Access a specialized knowledge base",
                    "🌍 Get answers in French, English, or Spanish",
                    "📱 Use on mobile, tablet, and computer"
                ]
            },
            'es': {
                'subject': f"{inviter_name} te invita a descubrir Intelia Expert",
                'title': "🚀 Invitación Intelia Expert",
                'greeting': f"¡Hola! {inviter_name} te invita a descubrir Intelia Expert",
                'description': "El primer asistente IA especializado en salud y nutrición animal",
                'cta_text': "Crear mi cuenta gratuita",
                'features_title': "✨ Con Intelia Expert, puedes:",
                'features': [
                    "🎯 Hacer preguntas expertas sobre salud animal 24/7",
                    "📚 Acceder a una base de conocimiento especializada",
                    "🌍 Obtener respuestas en francés, inglés o español",
                    "📱 Usar en móvil, tableta y computadora"
                ]
            }
        }
        
        template_data = templates.get(language, templates['fr'])
        
        # Ajouter le message personnel si présent
        if personal_message.strip():
            template_data['personal_message'] = personal_message
            template_data['personal_message_title'] = {
                'fr': f"Message personnel de {inviter_name} :",
                'en': f"Personal message from {inviter_name}:",
                'es': f"Mensaje personal de {inviter_name}:"
            }.get(language, f"Message personnel de {inviter_name} :")
        
        return template_data
    
    async def send_invitation(self, email: str, inviter_name: str, inviter_email: str, 
                            personal_message: str = "", language: str = "fr") -> Dict[str, Any]:
        """Envoie une invitation via Supabase Auth"""
        try:
            # Préparer les données du template
            template_data = self.get_invitation_template_data(language, inviter_name, personal_message)
            
            # URL de redirection après inscription
            redirect_to = f"{self.frontend_url}/welcome?invited_by={inviter_email}"
            
            # Envoyer l'invitation via Supabase Auth (nécessite service role)
            response = self.admin_client.auth.admin.invite_user_by_email(
                email=email,
                options={
                    "redirect_to": redirect_to,
                    "data": {
                        "invited_by": inviter_email,
                        "inviter_name": inviter_name,
                        "personal_message": personal_message,
                        "language": language,
                        "invitation_date": datetime.now().isoformat()
                    }
                }
            )
            
            logger.info(f"✅ Invitation Supabase envoyée à {email} de la part de {inviter_name}")
            
            # Enregistrer l'invitation dans une table personnalisée pour le tracking
            await self.log_invitation(email, inviter_email, inviter_name, personal_message, language)
            
            return {
                "success": True,
                "email": email,
                "invitation_id": response.user.id if response.user else None,
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi invitation Supabase à {email}: {str(e)}")
            return {
                "success": False,
                "email": email,
                "error": str(e),
                "status": "failed"
            }
    
    async def log_invitation(self, email: str, inviter_email: str, inviter_name: str, 
                           personal_message: str, language: str):
        """Enregistre l'invitation dans une table de tracking"""
        try:
            self.anon_client.table("invitations").insert({
                "email": email,
                "inviter_email": inviter_email,
                "inviter_name": inviter_name,
                "personal_message": personal_message,
                "language": language,
                "status": "pending",
                "invited_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"⚠️ Erreur enregistrement invitation: {e}")
    
    async def get_invitation_stats(self, user_email: str) -> Dict[str, Any]:
        """Récupère les statistiques d'invitations d'un utilisateur"""
        try:
            # Invitations envoyées par cet utilisateur
            sent_invitations = self.anon_client.table("invitations").select("*").eq("inviter_email", user_email).execute()
            
            total_sent = len(sent_invitations.data)
            
            # Invitations ce mois-ci
            current_month = datetime.now().strftime("%Y-%m")
            this_month = len([inv for inv in sent_invitations.data 
                            if inv["invited_at"].startswith(current_month)])
            
            # Dernière invitation
            last_sent = None
            if sent_invitations.data:
                last_sent = max(sent_invitations.data, key=lambda x: x["invited_at"])["invited_at"]
            
            return {
                "total_sent": total_sent,
                "this_month": this_month,
                "last_sent": last_sent,
                "recent_invitations": sent_invitations.data[-5:] if sent_invitations.data else []
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération stats: {e}")
            return {"total_sent": 0, "this_month": 0, "last_sent": None, "recent_invitations": []}

# ==================== ENDPOINTS ====================
@router.post("/send", response_model=InvitationResponse)
async def send_invitations(
    request: InvitationRequest,
    current_user = Depends(get_current_user)
):
    """Envoie des invitations via Supabase Auth"""
    
    logger.info(f"📧 [send_invitations] Demande d'invitation Supabase de {request.inviter_email} pour {len(request.emails)} destinataires")
    
    # Vérification et ajustement automatique de l'email inviteur
    if current_user.email.lower() != request.inviter_email.lower():
        request.inviter_email = current_user.email
        if not request.inviter_name or request.inviter_name == request.inviter_email:
            request.inviter_name = current_user.name or current_user.email.split('@')[0]
    
    # Initialiser le service Supabase
    invitation_service = SupabaseInvitationService()
    
    # Compteurs et résultats détaillés
    sent_count = 0
    failed_emails = []
    invitation_details = []
    
    # Envoyer les invitations une par une
    for email in request.emails:
        result = await invitation_service.send_invitation(
            email=email,
            inviter_name=request.inviter_name,
            inviter_email=request.inviter_email,
            personal_message=request.personal_message,
            language=request.language
        )
        
        invitation_details.append(result)
        
        if result["success"]:
            sent_count += 1
        else:
            failed_emails.append(email)
    
    # Construire la réponse
    success = sent_count > 0
    message = f"✅ {sent_count} invitation{'s' if sent_count > 1 else ''} envoyée{'s' if sent_count > 1 else ''} avec succès"
    
    if failed_emails:
        message += f" - {len(failed_emails)} échec{'s' if len(failed_emails) > 1 else ''}"
    
    logger.info(f"📊 [send_invitations] Résultat Supabase: {sent_count} envoyées, {len(failed_emails)} échecs")
    
    return InvitationResponse(
        success=success,
        sent_count=sent_count,
        failed_emails=failed_emails,
        message=message,
        invitation_details=invitation_details
    )

@router.get("/stats")
async def get_invitation_stats(
    current_user = Depends(get_current_user)
):
    """Obtient les statistiques d'invitations de l'utilisateur"""
    logger.info(f"📊 [get_invitation_stats] Demande stats Supabase pour {current_user.email}")
    
    invitation_service = SupabaseInvitationService()
    stats = await invitation_service.get_invitation_stats(current_user.email)
    
    return {
        "user_email": current_user.email,
        "user_name": current_user.name,
        "supabase_enabled": True,
        "max_per_batch": 10,
        **stats
    }

@router.get("/status")
async def get_invitations_status(
    current_user = Depends(get_current_user)
):
    """Récupère le statut des invitations envoyées"""
    try:
        client = get_supabase_anon_client()
        
        # Récupérer les invitations de l'utilisateur
        invitations = client.table("invitations").select("*").eq("inviter_email", current_user.email).order("invited_at", desc=True).limit(20).execute()
        
        return {
            "invitations": invitations.data,
            "total_count": len(invitations.data)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération statut invitations: {e}")
        return {"invitations": [], "total_count": 0}

@router.get("/debug/auth")
async def debug_auth(
    current_user = Depends(get_current_user)
):
    """Debug endpoint pour vérifier l'authentification et Supabase"""
    return {
        "authenticated": True,
        "user_email": current_user.email,
        "user_name": current_user.name,
        "user_id": current_user.id,
        "supabase_available": SUPABASE_AVAILABLE,
        "supabase_url": os.getenv("SUPABASE_URL"),
        "service_role_configured": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "frontend_url": os.getenv("FRONTEND_URL"),
        "timestamp": datetime.now().isoformat()
    }