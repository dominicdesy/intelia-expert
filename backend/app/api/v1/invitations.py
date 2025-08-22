# app/api/v1/invitations.py - VERSION SUPABASE COMPLÈTE MISE À JOUR
"""
Router Invitations pour Intelia Expert - VERSION SUPABASE NATIVE
Utilise les invitations intégrées de Supabase Auth avec détection d'utilisateurs existants
MISE À JOUR : Support pour l'authentification d'invitations via backend
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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
    force_send: bool = False  # Nouveau : forcer l'envoi même si utilisateur existe
    
    @validator('emails')
    def validate_emails_count(cls, v):
        if len(v) == 0:
            raise ValueError('Au moins une adresse email est requise')
        if len(v) > 10:
            raise ValueError('Maximum 10 invitations à la fois')
        return v

class InvitationResult(BaseModel):
    email: str
    success: bool
    status: str  # 'sent', 'resent', 'skipped', 'failed'
    reason: Optional[str] = None
    message: str
    details: Dict[str, Any] = {}

class InvitationResponse(BaseModel):
    success: bool
    sent_count: int
    resent_count: int
    skipped_count: int
    failed_count: int
    message: str
    results: List[InvitationResult] = []

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
        # Délai minimum entre deux invitations (en heures)
        self.min_resend_delay_hours = int(os.getenv("MIN_RESEND_DELAY_HOURS", "24"))
    
    async def check_user_exists(self, email: str) -> Dict[str, Any]:
        """Vérifie si un utilisateur existe déjà dans Supabase Auth"""
        try:
            # Utiliser l'API admin pour vérifier l'existence de l'utilisateur
            response = self.admin_client.auth.admin.list_users(
                page=1,
                per_page=1000  # Augmentez si vous avez plus de 1000 utilisateurs
            )
            
            # Chercher l'email dans la liste des utilisateurs
            existing_users = response.data if hasattr(response, 'data') else []
            
            for user in existing_users:
                if user.email and user.email.lower() == email.lower():
                    return {
                        "exists": True,
                        "user_id": user.id,
                        "email": user.email,
                        "created_at": user.created_at,
                        "last_sign_in": user.last_sign_in_at,
                        "email_confirmed": user.email_confirmed_at is not None
                    }
            
            return {"exists": False}
            
        except Exception as e:
            logger.error(f"❌ Erreur vérification utilisateur {email}: {str(e)}")
            # En cas d'erreur, on assume que l'utilisateur n'existe pas pour ne pas bloquer
            return {"exists": False, "error": str(e)}
    
    async def check_invitation_status(self, email: str, inviter_email: str) -> Dict[str, Any]:
        """Vérifie le statut des invitations pour cet email"""
        try:
            # Chercher toutes les invitations pour cet email
            result = self.anon_client.table("invitations").select("*").eq("email", email).order("invited_at", desc=True).execute()
            
            if not result.data:
                return {
                    "has_invitations": False,
                    "can_invite": True,
                    "reason": "no_previous_invitation"
                }
            
            # Vérifier s'il y a une invitation acceptée
            accepted_invitations = [inv for inv in result.data if inv.get("status") == "accepted"]
            if accepted_invitations:
                return {
                    "has_invitations": True,
                    "can_invite": False,
                    "reason": "invitation_already_accepted",
                    "accepted_at": accepted_invitations[0]["accepted_at"],
                    "accepted_invitation": accepted_invitations[0]
                }
            
            # Chercher les invitations en cours (pending)
            pending_invitations = [inv for inv in result.data if inv.get("status") == "pending"]
            
            if not pending_invitations:
                return {
                    "has_invitations": True,
                    "can_invite": True,
                    "reason": "no_pending_invitation"
                }
            
            # Il y a des invitations pending - vérifier si on peut renvoyer
            latest_invitation = pending_invitations[0]  # La plus récente
            invited_at = datetime.fromisoformat(latest_invitation["invited_at"].replace('Z', '+00:00'))
            now = datetime.now(invited_at.tzinfo)
            time_since_last = now - invited_at
            
            # Vérifier si le délai minimum est respecté
            min_delay = timedelta(hours=self.min_resend_delay_hours)
            can_resend = time_since_last >= min_delay
            
            # Vérifier si c'est le même inviteur
            is_same_inviter = latest_invitation["inviter_email"].lower() == inviter_email.lower()
            
            if not can_resend:
                remaining_hours = int((min_delay - time_since_last).total_seconds() / 3600)
                return {
                    "has_invitations": True,
                    "can_invite": False,
                    "reason": "too_recent",
                    "message": f"Dernière invitation envoyée il y a {int(time_since_last.total_seconds() / 3600)}h. Attendez encore {remaining_hours}h.",
                    "latest_invitation": latest_invitation,
                    "hours_remaining": remaining_hours
                }
            
            # Peut renvoyer l'invitation
            return {
                "has_invitations": True,
                "can_invite": True,
                "can_resend": True,
                "reason": "can_resend_invitation",
                "latest_invitation": latest_invitation,
                "is_same_inviter": is_same_inviter,
                "hours_since_last": int(time_since_last.total_seconds() / 3600)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur vérification statut invitation {email}: {str(e)}")
            return {"has_invitations": False, "can_invite": True, "error": str(e)}
    
    async def validate_email_before_invitation(self, email: str, inviter_email: str) -> Dict[str, Any]:
        """Validation complète avant d'envoyer une invitation"""
        
        # 1. Vérifier si l'utilisateur existe déjà 
        user_check = await self.check_user_exists(email)
        
        if user_check["exists"]:
            return {
                "can_invite": False,
                "reason": "user_exists",
                "message": f"L'utilisateur {email} possède déjà un compte Intelia Expert",
                "details": {
                    "registered_since": user_check.get("created_at"),
                    "last_login": user_check.get("last_sign_in"),
                    "email_confirmed": user_check.get("email_confirmed", False)
                }
            }
        
        # 2. Vérifier le statut des invitations
        invitation_status = await self.check_invitation_status(email, inviter_email)
        
        if not invitation_status["can_invite"]:
            return {
                "can_invite": False,
                "reason": invitation_status["reason"],
                "message": invitation_status.get("message", f"Impossible d'inviter {email}"),
                "details": invitation_status
            }
        
        # 3. Cas spécial : peut renvoyer une invitation
        if invitation_status.get("can_resend"):
            return {
                "can_invite": True,
                "reason": "can_resend",
                "is_resend": True,
                "message": f"Renvoi d'invitation possible pour {email}",
                "details": invitation_status
            }
        
        # 4. Validation OK pour nouvelle invitation
        return {
            "can_invite": True,
            "reason": "valid",
            "is_resend": False,
            "message": f"Invitation possible pour {email}"
        }
    
    def get_invitation_template_data(self, language: str, inviter_name: str, personal_message: str = "", is_resend: bool = False) -> Dict[str, str]:
        """Prépare les données pour le template d'email"""
        
        templates = {
            'fr': {
                'subject': f"{inviter_name} vous invite à découvrir Intelia Expert" + (" (Rappel)" if is_resend else ""),
                'title': "🚀 Invitation Intelia Expert" + (" - Rappel" if is_resend else ""),
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
                'subject': f"{inviter_name} invites you to discover Intelia Expert" + (" (Reminder)" if is_resend else ""),
                'title': "🚀 Intelia Expert Invitation" + (" - Reminder" if is_resend else ""),
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
                'subject': f"{inviter_name} te invita a descubrir Intelia Expert" + (" (Recordatorio)" if is_resend else ""),
                'title': "🚀 Invitación Intelia Expert" + (" - Recordatorio" if is_resend else ""),
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
        
        # Ajouter un message de rappel si c'est un renvoi
        if is_resend:
            template_data['resend_note'] = {
                'fr': "Il s'agit d'un rappel de votre invitation précédente.",
                'en': "This is a reminder of your previous invitation.",
                'es': "Este es un recordatorio de tu invitación anterior."
            }.get(language, "Il s'agit d'un rappel de votre invitation précédente.")
        
        return template_data
    
    async def send_invitation(self, email: str, inviter_name: str, inviter_email: str, 
                            personal_message: str = "", language: str = "fr", is_resend: bool = False) -> Dict[str, Any]:
        """Envoie une invitation via Supabase Auth"""
        try:
            # Préparer les données du template
            template_data = self.get_invitation_template_data(language, inviter_name, personal_message, is_resend)
            
            # URL de redirection après inscription
            redirect_to = f"{self.frontend_url}/auth/invitation"
            
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
                        "invitation_date": datetime.now().isoformat(),
                        "is_resend": is_resend
                    }
                }
            )
            
            action_type = "renvoyée" if is_resend else "envoyée"
            logger.info(f"✅ Invitation Supabase {action_type} à {email} de la part de {inviter_name}")
            
            # Enregistrer l'invitation dans une table personnalisée pour le tracking
            await self.log_invitation(email, inviter_email, inviter_name, personal_message, language, is_resend)
            
            return {
                "success": True,
                "email": email,
                "invitation_id": response.user.id if response.user else None,
                "status": "resent" if is_resend else "sent",
                "message": f"Invitation {action_type} avec succès"
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi invitation Supabase à {email}: {str(e)}")
            return {
                "success": False,
                "email": email,
                "error": str(e),
                "status": "failed",
                "message": f"Échec de l'envoi: {str(e)}"
            }
    
    async def send_invitation_with_validation(self, email: str, inviter_name: str, inviter_email: str, 
                                            personal_message: str = "", language: str = "fr", 
                                            force: bool = False) -> Dict[str, Any]:
        """Envoie une invitation avec validation préalable"""
        
        # Validation préalable (sauf si force=True)
        if not force:
            validation = await self.validate_email_before_invitation(email, inviter_email)
            
            if not validation["can_invite"]:
                return {
                    "success": False,
                    "email": email,
                    "status": "skipped",
                    "reason": validation["reason"],
                    "message": validation["message"],
                    "details": validation.get("details", {})
                }
            
            # Déterminer si c'est un renvoi
            is_resend = validation.get("is_resend", False)
        else:
            is_resend = False
        
        # Si validation OK ou force=True, envoyer l'invitation
        return await self.send_invitation(email, inviter_name, inviter_email, personal_message, language, is_resend)
    
    async def log_invitation(self, email: str, inviter_email: str, inviter_name: str, 
                           personal_message: str, language: str, is_resend: bool = False):
        """Enregistre l'invitation dans une table de tracking"""
        try:
            # Si c'est un renvoi, marquer l'ancienne invitation comme superseded
            if is_resend:
                await self.mark_previous_invitations_superseded(email, inviter_email)
            
            # Données à insérer
            invitation_data = {
                "email": email,
                "inviter_email": inviter_email,
                "inviter_name": inviter_name,
                "personal_message": personal_message or "",
                "language": language,
                "status": "pending",
                "invited_at": datetime.now().isoformat(),
                "is_resend": is_resend
            }
            
            # Insertion avec gestion d'erreur détaillée
            result = self.anon_client.table("invitations").insert(invitation_data).execute()
            
            action_type = "renvoi" if is_resend else "nouvelle invitation"
            logger.info(f"✅ {action_type.capitalize()} loggée avec succès: {email}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            # Log détaillé de l'erreur
            logger.error(f"❌ Erreur détaillée enregistrement invitation:")
            logger.error(f"   - Email: {email}")
            logger.error(f"   - Inviter: {inviter_email}")
            logger.error(f"   - Est un renvoi: {is_resend}")
            logger.error(f"   - Erreur: {str(e)}")
            logger.error(f"   - Type erreur: {type(e).__name__}")
            
            # Si c'est une erreur de table inexistante, donner des instructions
            if "404" in str(e) or "not found" in str(e).lower():
                logger.error("⚠️  Table 'invitations' n'existe pas. Créez-la avec le script SQL fourni.")
            
            # Ne pas faire échouer l'invitation à cause du logging
            return None
    
    async def mark_previous_invitations_superseded(self, email: str, inviter_email: str):
        """Marque les invitations précédentes comme superseded"""
        try:
            result = self.anon_client.table("invitations").update({
                "status": "superseded",
                "superseded_at": datetime.now().isoformat()
            }).eq("email", email).eq("inviter_email", inviter_email).eq("status", "pending").execute()
            
            if result.data:
                logger.info(f"📝 {len(result.data)} invitation(s) précédente(s) marquée(s) comme superseded pour {email}")
        
        except Exception as e:
            logger.error(f"❌ Erreur marquage invitations superseded pour {email}: {str(e)}")
    
    async def mark_invitation_accepted(self, email: str, user_id: str = None):
        """Marque une invitation comme acceptée quand l'utilisateur s'inscrit"""
        try:
            # Trouver la dernière invitation pending pour cet email
            pending_invitations = self.anon_client.table("invitations").select("*").eq("email", email).eq("status", "pending").order("invited_at", desc=True).execute()
            
            if pending_invitations.data:
                latest_invitation = pending_invitations.data[0]
                
                # Marquer comme acceptée
                update_data = {
                    "status": "accepted",
                    "accepted_at": datetime.now().isoformat()
                }
                
                if user_id:
                    update_data["accepted_user_id"] = user_id
                
                result = self.anon_client.table("invitations").update(update_data).eq("id", latest_invitation["id"]).execute()
                
                logger.info(f"✅ Invitation marquée comme acceptée pour {email} (ID: {latest_invitation['id']})")
                return result.data[0] if result.data else None
            else:
                logger.warning(f"⚠️ Aucune invitation pending trouvée pour {email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur marquage invitation acceptée pour {email}: {str(e)}")
            return None
    
    # 🆕 NOUVELLE MÉTHODE : Récupérer utilisateur par ID
    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """Récupère un utilisateur Supabase par son ID (pour auth invitations)"""
        try:
            response = self.admin_client.auth.admin.get_user_by_id(user_id)
            
            if response.user:
                return {
                    "success": True,
                    "user": response.user
                }
            else:
                return {
                    "success": False,
                    "error": "Utilisateur non trouvé"
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur récupération utilisateur {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # 🆕 NOUVELLE MÉTHODE : Mettre à jour utilisateur par ID
    def update_user_by_id(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour un utilisateur Supabase par son ID (pour auth invitations)"""
        try:
            response = self.admin_client.auth.admin.update_user_by_id(user_id, update_data)
            
            if response.user:
                return {
                    "success": True,
                    "user": response.user
                }
            else:
                return {
                    "success": False,
                    "error": "Échec mise à jour utilisateur"
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour utilisateur {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_invitation_stats(self, user_email: str) -> Dict[str, Any]:
        """Récupère les statistiques d'invitations d'un utilisateur"""
        try:
            # Invitations envoyées par cet utilisateur
            sent_invitations = self.anon_client.table("invitations").select("*").eq("inviter_email", user_email).execute()
            
            total_sent = len(sent_invitations.data)
            
            # Statistiques par statut
            accepted_invitations = [inv for inv in sent_invitations.data if inv.get("status") == "accepted"]
            pending_invitations = [inv for inv in sent_invitations.data if inv.get("status") == "pending"]
            superseded_invitations = [inv for inv in sent_invitations.data if inv.get("status") == "superseded"]
            
            accepted_count = len(accepted_invitations)
            pending_count = len(pending_invitations)
            superseded_count = len(superseded_invitations)
            
            # Calcul du taux d'acceptation (en excluant les superseded pour éviter de compter les doublons)
            effective_invitations = total_sent - superseded_count
            acceptance_rate = (accepted_count / effective_invitations * 100) if effective_invitations > 0 else 0
            
            # Renvois
            resent_count = len([inv for inv in sent_invitations.data if inv.get("is_resend", False)])
            
            # Invitations ce mois-ci
            current_month = datetime.now().strftime("%Y-%m")
            this_month_sent = len([inv for inv in sent_invitations.data 
                                 if inv["invited_at"].startswith(current_month)])
            this_month_accepted = len([inv for inv in accepted_invitations 
                                     if inv.get("accepted_at", "").startswith(current_month)])
            
            # Invitations cette semaine
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            this_week_sent = len([inv for inv in sent_invitations.data 
                                if inv["invited_at"] >= week_ago])
            this_week_accepted = len([inv for inv in accepted_invitations 
                                    if inv.get("accepted_at", "") >= week_ago])
            
            # Dernière invitation envoyée et acceptée
            last_sent = None
            last_accepted = None
            
            if sent_invitations.data:
                last_sent = max(sent_invitations.data, key=lambda x: x["invited_at"])["invited_at"]
            
            if accepted_invitations:
                last_accepted = max(accepted_invitations, key=lambda x: x.get("accepted_at", ""))["accepted_at"]
            
            # Top 5 des invitations récentes avec leur statut
            recent_invitations = sorted(sent_invitations.data, key=lambda x: x["invited_at"], reverse=True)[:10]
            
            # Statistiques par email unique (dédoublonnage)
            unique_emails = {}
            for inv in sent_invitations.data:
                email = inv["email"]
                if email not in unique_emails or inv["invited_at"] > unique_emails[email]["invited_at"]:
                    unique_emails[email] = inv
            
            unique_sent = len(unique_emails)
            unique_accepted = len([inv for inv in unique_emails.values() if inv.get("status") == "accepted"])
            unique_pending = len([inv for inv in unique_emails.values() if inv.get("status") == "pending"])
            
            return {
                # Statistiques globales
                "total_sent": total_sent,
                "total_accepted": accepted_count,
                "total_pending": pending_count,
                "total_superseded": superseded_count,
                "acceptance_rate": round(acceptance_rate, 1),
                
                # Statistiques uniques (par email)
                "unique_emails_invited": unique_sent,
                "unique_emails_accepted": unique_accepted,
                "unique_emails_pending": unique_pending,
                "unique_acceptance_rate": round((unique_accepted / unique_sent * 100) if unique_sent > 0 else 0, 1),
                
                # Renvois
                "resent_count": resent_count,
                
                # Périodes
                "this_month_sent": this_month_sent,
                "this_month_accepted": this_month_accepted,
                "this_week_sent": this_week_sent,
                "this_week_accepted": this_week_accepted,
                
                # Dates importantes
                "last_sent": last_sent,
                "last_accepted": last_accepted,
                
                # Détails
                "recent_invitations": recent_invitations,
                "accepted_invitations": accepted_invitations[-5:] if accepted_invitations else [],
                "min_resend_delay_hours": self.min_resend_delay_hours
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération stats: {e}")
            return {
                "total_sent": 0,
                "total_accepted": 0,
                "total_pending": 0,
                "total_superseded": 0,
                "acceptance_rate": 0,
                "unique_emails_invited": 0,
                "unique_emails_accepted": 0,
                "unique_emails_pending": 0,
                "unique_acceptance_rate": 0,
                "resent_count": 0,
                "this_month_sent": 0,
                "this_month_accepted": 0,
                "this_week_sent": 0,
                "this_week_accepted": 0,
                "last_sent": None,
                "last_accepted": None,
                "recent_invitations": [],
                "accepted_invitations": [],
                "min_resend_delay_hours": self.min_resend_delay_hours
            }

# ==================== ENDPOINTS ====================
@router.post("/send", response_model=InvitationResponse)
async def send_invitations(
    request: InvitationRequest,
    current_user = Depends(get_current_user)
):
    """Envoie des invitations avec vérification d'utilisateurs existants et possibilité de renvoi"""
    
    logger.info(f"📧 [send_invitations] Demande d'invitation de {request.inviter_email} pour {len(request.emails)} destinataires")
    
    # Vérification et ajustement automatique de l'email inviteur
    if current_user.email.lower() != request.inviter_email.lower():
        request.inviter_email = current_user.email
        if not request.inviter_name or request.inviter_name == request.inviter_email:
            request.inviter_name = current_user.name or current_user.email.split('@')[0]
    
    # Initialiser le service Supabase
    invitation_service = SupabaseInvitationService()
    
    # Compteurs et résultats détaillés
    sent_count = 0
    resent_count = 0
    skipped_count = 0
    failed_count = 0
    results = []
    
    # Traiter chaque email individuellement
    for email in request.emails:
        try:
            logger.info(f"🔍 [send_invitations] Traitement de {email}")
            
            # Envoyer l'invitation avec validation
            result = await invitation_service.send_invitation_with_validation(
                email=email,
                inviter_name=request.inviter_name,
                inviter_email=request.inviter_email,
                personal_message=request.personal_message,
                language=request.language,
                force=request.force_send
            )
            
            # Convertir le résultat en format standardisé
            invitation_result = InvitationResult(
                email=email,
                success=result["success"],
                status=result.get("status", "failed"),
                reason=result.get("reason"),
                message=result.get("message", ""),
                details=result.get("details", {})
            )
            
            results.append(invitation_result)
            
            # Mettre à jour les compteurs
            if result["success"]:
                if result.get("status") == "resent":
                    resent_count += 1
                    logger.info(f"🔄 [send_invitations] Invitation renvoyée: {email}")
                else:
                    sent_count += 1
                    logger.info(f"✅ [send_invitations] Invitation envoyée: {email}")
            elif result.get("status") == "skipped":
                skipped_count += 1
                logger.info(f"⭐️ [send_invitations] Invitation ignorée: {email} - {result.get('reason')}")
            else:
                failed_count += 1
                logger.error(f"❌ [send_invitations] Échec invitation: {email}")
                
        except Exception as e:
            # Gestion d'erreur pour cet email spécifique
            logger.error(f"❌ [send_invitations] Erreur inattendue pour {email}: {str(e)}")
            
            results.append(InvitationResult(
                email=email,
                success=False,
                status="failed",
                reason="unexpected_error",
                message=f"Erreur inattendue: {str(e)}",
                details={}
            ))
            failed_count += 1
    
    # Construire le message de résumé
    total_processed = len(request.emails)
    messages = []
    
    if sent_count > 0:
        messages.append(f"✅ {sent_count} invitation{'s' if sent_count > 1 else ''} envoyée{'s' if sent_count > 1 else ''}")
    
    if resent_count > 0:
        messages.append(f"🔄 {resent_count} renvoyée{'s' if resent_count > 1 else ''}")
    
    if skipped_count > 0:
        messages.append(f"⭐️ {skipped_count} ignorée{'s' if skipped_count > 1 else ''}")
    
    if failed_count > 0:
        messages.append(f"❌ {failed_count} échec{'s' if failed_count > 1 else ''}")
    
    summary_message = " • ".join(messages) if messages else "Aucune invitation traitée"
    
    # Déterminer le succès global
    overall_success = (sent_count + resent_count) > 0 or (sent_count == 0 and resent_count == 0 and skipped_count > 0 and failed_count == 0)
    
    logger.info(f"📊 [send_invitations] Résultat final: {sent_count} envoyées, {resent_count} renvoyées, {skipped_count} ignorées, {failed_count} échecs")
    
    return InvitationResponse(
        success=overall_success,
        sent_count=sent_count,
        resent_count=resent_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        message=summary_message,
        results=results
    )

@router.post("/mark-accepted")
async def mark_invitation_accepted(
    email: EmailStr,
    user_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Marque une invitation comme acceptée (appelé lors de l'inscription d'un utilisateur)"""
    
    logger.info(f"✅ [mark_invitation_accepted] Marquage acceptation pour {email}")
    
    invitation_service = SupabaseInvitationService()
    result = await invitation_service.mark_invitation_accepted(email, user_id)
    
    if result:
        return {
            "success": True,
            "message": f"Invitation marquée comme acceptée pour {email}",
            "invitation": result
        }
    else:
        return {
            "success": False,
            "message": f"Aucune invitation pending trouvée pour {email}"
        }

@router.get("/stats/detailed")
async def get_detailed_stats(
    current_user = Depends(get_current_user)
):
    """Obtient des statistiques détaillées incluant les acceptations"""
    logger.info(f"📊 [get_detailed_stats] Demande stats détaillées pour {current_user.email}")
    
    invitation_service = SupabaseInvitationService()
    stats = await invitation_service.get_invitation_stats(current_user.email)
    
    return {
        "user_email": current_user.email,
        "user_name": current_user.name,
        "supabase_enabled": True,
        "max_per_batch": 10,
        **stats
    }

@router.get("/stats/summary")
async def get_stats_summary(
    current_user = Depends(get_current_user)
):
    """Obtient un résumé des statistiques d'invitations"""
    logger.info(f"📊 [get_stats_summary] Demande résumé stats pour {current_user.email}")
    
    invitation_service = SupabaseInvitationService()
    stats = await invitation_service.get_invitation_stats(current_user.email)
    
    return {
        "user_email": current_user.email,
        "total_invitations_sent": stats["total_sent"],
        "total_invitations_accepted": stats["total_accepted"],
        "unique_emails_invited": stats["unique_emails_invited"],
        "unique_emails_accepted": stats["unique_emails_accepted"],
        "acceptance_rate": stats["acceptance_rate"],
        "unique_acceptance_rate": stats["unique_acceptance_rate"],
        "this_month_sent": stats["this_month_sent"],
        "this_month_accepted": stats["this_month_accepted"],
        "this_week_sent": stats["this_week_sent"],
        "this_week_accepted": stats["this_week_accepted"]
    }

@router.get("/stats/global")
async def get_global_stats(
    current_user = Depends(get_current_user)
):
    """Obtient les statistiques globales de la plateforme (admin seulement)"""
    
    # Note: Ajoutez ici une vérification des permissions admin si nécessaire
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Accès admin requis")
    
    try:
        client = get_supabase_anon_client()
        
        # Toutes les invitations
        all_invitations = client.table("invitations").select("*").execute()
        
        if not all_invitations.data:
            return {
                "total_invitations": 0,
                "total_accepted": 0,
                "total_pending": 0,
                "global_acceptance_rate": 0,
                "active_inviters": 0,
                "top_inviters": []
            }
        
        total_invitations = len(all_invitations.data)
        accepted_count = len([inv for inv in all_invitations.data if inv.get("status") == "accepted"])
        pending_count = len([inv for inv in all_invitations.data if inv.get("status") == "pending"])
        
        # Calcul du taux d'acceptation global
        global_acceptance_rate = (accepted_count / total_invitations * 100) if total_invitations > 0 else 0
        
        # Top des inviteurs
        from collections import defaultdict
        inviter_stats = defaultdict(lambda: {"sent": 0, "accepted": 0})
        
        for inv in all_invitations.data:
            inviter_email = inv["inviter_email"]
            inviter_stats[inviter_email]["sent"] += 1
            if inv.get("status") == "accepted":
                inviter_stats[inviter_email]["accepted"] += 1
        
        # Tri par nombre d'acceptations
        top_inviters = sorted(
            [
                {
                    "inviter_email": email,
                    "invitations_sent": stats["sent"],
                    "invitations_accepted": stats["accepted"],
                    "acceptance_rate": round((stats["accepted"] / stats["sent"] * 100) if stats["sent"] > 0 else 0, 1)
                }
                for email, stats in inviter_stats.items()
            ],
            key=lambda x: x["invitations_accepted"],
            reverse=True
        )[:10]
        
        active_inviters = len(inviter_stats)
        
        return {
            "total_invitations": total_invitations,
            "total_accepted": accepted_count,
            "total_pending": pending_count,
            "global_acceptance_rate": round(global_acceptance_rate, 1),
            "active_inviters": active_inviters,
            "top_inviters": top_inviters
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération stats globales: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération statistiques globales")

@router.post("/validate")
async def validate_invitations(
    emails: List[EmailStr],
    current_user = Depends(get_current_user)
):
    """Valide une liste d'emails avant envoi d'invitations"""
    
    logger.info(f"🔍 [validate_invitations] Validation de {len(emails)} emails par {current_user.email}")
    
    invitation_service = SupabaseInvitationService()
    validations = []
    
    for email in emails:
        validation = await invitation_service.validate_email_before_invitation(email, current_user.email)
        validations.append({
            "email": email,
            "can_invite": validation["can_invite"],
            "reason": validation["reason"],
            "message": validation["message"],
            "is_resend": validation.get("is_resend", False),
            "details": validation.get("details", {})
        })
    
    # Statistiques
    can_invite_count = sum(1 for v in validations if v["can_invite"])
    cannot_invite_count = len(validations) - can_invite_count
    can_resend_count = sum(1 for v in validations if v.get("is_resend", False))
    
    return {
        "total_emails": len(emails),
        "can_invite": can_invite_count,
        "cannot_invite": cannot_invite_count,
        "can_resend": can_resend_count,
        "min_resend_delay_hours": invitation_service.min_resend_delay_hours,
        "validations": validations
    }

@router.get("/stats")
async def get_invitation_stats(
    current_user = Depends(get_current_user)
):
    """Obtient les statistiques d'invitations de l'utilisateur (endpoint de compatibilité)"""
    return await get_stats_summary(current_user)

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
        "min_resend_delay_hours": int(os.getenv("MIN_RESEND_DELAY_HOURS", "24")),
        "timestamp": datetime.now().isoformat()
    }
 
# 🆕 NOUVEAUX ENDPOINTS - À ajouter à la fin du fichier invitations.py (après le dernier endpoint existant)

@router.get("/stats/global-enhanced")
async def get_enhanced_global_stats(
    current_user = Depends(get_current_user)
):
    """Obtient les statistiques globales enrichies avec top inviters par acceptations"""
    
    # Note: Ajoutez ici une vérification des permissions admin si nécessaire
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Accès admin requis")
    
    try:
        client = get_supabase_anon_client()
        
        # Toutes les invitations
        all_invitations = client.table("invitations").select("*").execute()
        
        if not all_invitations.data:
            return {
                "total_invitations": 0,
                "total_accepted": 0,
                "total_pending": 0,
                "global_acceptance_rate": 0,
                "active_inviters": 0,
                "unique_inviters": 0,
                "top_inviters_by_sent": [],
                "top_inviters_by_accepted": []
            }
        
        total_invitations = len(all_invitations.data)
        accepted_count = len([inv for inv in all_invitations.data if inv.get("status") == "accepted"])
        pending_count = len([inv for inv in all_invitations.data if inv.get("status") == "pending"])
        
        # Calcul du taux d'acceptation global
        global_acceptance_rate = (accepted_count / total_invitations * 100) if total_invitations > 0 else 0
        
        # Statistiques par inviteur
        from collections import defaultdict
        inviter_stats = defaultdict(lambda: {
            "sent": 0, 
            "accepted": 0, 
            "pending": 0,
            "inviter_name": "",
            "latest_invitation": None
        })
        
        for inv in all_invitations.data:
            inviter_email = inv["inviter_email"]
            inviter_stats[inviter_email]["sent"] += 1
            inviter_stats[inviter_email]["inviter_name"] = inv.get("inviter_name", inviter_email.split('@')[0])
            
            if inv.get("status") == "accepted":
                inviter_stats[inviter_email]["accepted"] += 1
            elif inv.get("status") == "pending":
                inviter_stats[inviter_email]["pending"] += 1
            
            # Garder la dernière invitation pour des infos supplémentaires
            if not inviter_stats[inviter_email]["latest_invitation"] or inv["invited_at"] > inviter_stats[inviter_email]["latest_invitation"]["invited_at"]:
                inviter_stats[inviter_email]["latest_invitation"] = inv
        
        # Top inviters par nombre d'invitations envoyées
        top_inviters_by_sent = sorted(
            [
                {
                    "inviter_email": email,
                    "inviter_name": stats["inviter_name"],
                    "invitations_sent": stats["sent"],
                    "invitations_accepted": stats["accepted"],
                    "invitations_pending": stats["pending"],
                    "acceptance_rate": round((stats["accepted"] / stats["sent"] * 100) if stats["sent"] > 0 else 0, 1)
                }
                for email, stats in inviter_stats.items()
            ],
            key=lambda x: x["invitations_sent"],
            reverse=True
        )[:10]  # Top 10 pour avoir de la marge
        
        # Top inviters par nombre d'invitations acceptées
        top_inviters_by_accepted = sorted(
            [
                {
                    "inviter_email": email,
                    "inviter_name": stats["inviter_name"],
                    "invitations_sent": stats["sent"],
                    "invitations_accepted": stats["accepted"],
                    "invitations_pending": stats["pending"],
                    "acceptance_rate": round((stats["accepted"] / stats["sent"] * 100) if stats["sent"] > 0 else 0, 1)
                }
                for email, stats in inviter_stats.items()
                if stats["accepted"] > 0  # Seulement ceux qui ont au moins une acceptation
            ],
            key=lambda x: x["invitations_accepted"],
            reverse=True
        )[:10]  # Top 10 pour avoir de la marge
        
        active_inviters = len(inviter_stats)
        unique_inviters = len(set(inv["inviter_email"] for inv in all_invitations.data))
        
        # Statistiques temporelles (bonus)
        from datetime import datetime, timedelta
        now = datetime.now()
        week_ago = (now - timedelta(days=7)).isoformat()
        month_ago = (now - timedelta(days=30)).isoformat()
        
        invitations_this_week = len([inv for inv in all_invitations.data if inv["invited_at"] >= week_ago])
        invitations_this_month = len([inv for inv in all_invitations.data if inv["invited_at"] >= month_ago])
        accepted_this_week = len([inv for inv in all_invitations.data if inv.get("status") == "accepted" and inv.get("accepted_at", "") >= week_ago])
        accepted_this_month = len([inv for inv in all_invitations.data if inv.get("status") == "accepted" and inv.get("accepted_at", "") >= month_ago])
        
        logger.info(f"📊 Statistiques globales enrichies calculées: {total_invitations} invitations, {accepted_count} acceptées, {active_inviters} inviteurs")
        
        return {
            # Statistiques globales
            "total_invitations": total_invitations,
            "total_accepted": accepted_count,
            "total_pending": pending_count,
            "global_acceptance_rate": round(global_acceptance_rate, 1),
            "active_inviters": active_inviters,
            "unique_inviters": unique_inviters,
            
            # Top inviters
            "top_inviters_by_sent": top_inviters_by_sent,
            "top_inviters_by_accepted": top_inviters_by_accepted,
            
            # Statistiques temporelles
            "this_week": {
                "invitations_sent": invitations_this_week,
                "invitations_accepted": accepted_this_week,
                "acceptance_rate": round((accepted_this_week / invitations_this_week * 100) if invitations_this_week > 0 else 0, 1)
            },
            "this_month": {
                "invitations_sent": invitations_this_month,
                "invitations_accepted": accepted_this_month,
                "acceptance_rate": round((accepted_this_month / invitations_this_month * 100) if invitations_this_month > 0 else 0, 1)
            },
            
            # Métadonnées
            "generated_at": datetime.now().isoformat(),
            "data_source": "supabase",
            "calculation_method": "real_time"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération stats globales enrichies: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération statistiques globales enrichies")

@router.get("/stats/summary-all")
async def get_all_invitation_summary():
    """Résumé rapide des invitations (endpoint public pour les stats générales)"""
    try:
        client = get_supabase_anon_client()
        
        # Requête optimisée - seulement les champs nécessaires
        invitations = client.table("invitations").select("status,invited_at,accepted_at").execute()
        
        if not invitations.data:
            return {
                "total": 0,
                "accepted": 0,
                "pending": 0,
                "acceptance_rate": 0
            }
        
        total = len(invitations.data)
        accepted = len([inv for inv in invitations.data if inv.get("status") == "accepted"])
        pending = len([inv for inv in invitations.data if inv.get("status") == "pending"])
        
        return {
            "total": total,
            "accepted": accepted,
            "pending": pending,
            "acceptance_rate": round((accepted / total * 100) if total > 0 else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur résumé invitations: {e}")
        return {
            "total": 0,
            "accepted": 0,
            "pending": 0,
            "acceptance_rate": 0
        }

@router.get("/stats/leaderboard")
async def get_invitation_leaderboard(
    limit: int = 10,
    sort_by: str = "sent",  # "sent" ou "accepted"
    current_user = Depends(get_current_user)
):
    """Obtient le leaderboard des inviteurs"""
    
    if sort_by not in ["sent", "accepted"]:
        raise HTTPException(status_code=400, detail="sort_by doit être 'sent' ou 'accepted'")
    
    try:
        client = get_supabase_anon_client()
        
        # Toutes les invitations avec les champs nécessaires
        invitations = client.table("invitations").select("inviter_email,inviter_name,status").execute()
        
        if not invitations.data:
            return {"leaderboard": [], "total_inviters": 0}
        
        # Grouper par inviteur
        from collections import defaultdict
        inviter_stats = defaultdict(lambda: {"sent": 0, "accepted": 0, "name": ""})
        
        for inv in invitations.data:
            email = inv["inviter_email"]
            inviter_stats[email]["sent"] += 1
            inviter_stats[email]["name"] = inv.get("inviter_name", email.split('@')[0])
            if inv.get("status") == "accepted":
                inviter_stats[email]["accepted"] += 1
        
        # Trier selon le critère demandé
        sort_key = "sent" if sort_by == "sent" else "accepted"
        leaderboard = sorted(
            [
                {
                    "inviter_email": email,
                    "inviter_name": stats["name"],
                    "invitations_sent": stats["sent"],
                    "invitations_accepted": stats["accepted"],
                    "acceptance_rate": round((stats["accepted"] / stats["sent"] * 100) if stats["sent"] > 0 else 0, 1)
                }
                for email, stats in inviter_stats.items()
            ],
            key=lambda x: x[f"invitations_{sort_key}"],
            reverse=True
        )[:limit]
        
        return {
            "leaderboard": leaderboard,
            "total_inviters": len(inviter_stats),
            "sorted_by": sort_by,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur leaderboard invitations: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération leaderboard")
        
    
 