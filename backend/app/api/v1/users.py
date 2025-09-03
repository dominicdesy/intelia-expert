# app/api/v1/users.py - NOUVEAU FICHIER MANQUANT
"""
Endpoints pour la gestion des profils utilisateur
Résout le problème UserInfoModal qui contourne l'API backend
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Import de la fonction d'authentification existante
from .auth import get_current_user

# Import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

# ==================== MODÈLES PYDANTIC ====================

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    country_code: Optional[str] = None
    area_code: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    linkedin_profile: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    linkedin_corporate: Optional[str] = None
    user_type: Optional[str] = None
    language: Optional[str] = None
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError('Le nom doit contenir au moins 2 caractères')
        if v and len(v.strip()) > 50:
            raise ValueError('Le nom ne peut pas dépasser 50 caractères')
        return v.strip() if v else v
    
    @validator('user_type')
    def validate_user_type(cls, v):
        if v and v not in ['producer', 'professional', 'super_admin']:
            raise ValueError('Type d\'utilisateur invalide')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        if v and v not in ['fr', 'en', 'es', 'de', 'it', 'pt', 'nl', 'pl', 'hi', 'th', 'zh']:
            raise ValueError('Langue non supportée')
        return v

class UserProfileResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None

class UserProfileData(BaseModel):
    user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    country_code: Optional[str] = None
    area_code: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    linkedin_profile: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    linkedin_corporate: Optional[str] = None
    user_type: Optional[str] = None
    language: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================

def get_supabase_admin_client():
    """Client Supabase avec service role pour les opérations admin"""
    if not SUPABASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Supabase non disponible")
    
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not service_key:
        raise HTTPException(status_code=500, detail="Configuration Supabase manquante")
    
    return create_client(url, service_key)

# ==================== ENDPOINTS ====================

@router.get("/profile", response_model=UserProfileData)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Récupère le profil complet de l'utilisateur connecté"""
    
    logger.info(f"[get_user_profile] Récupération profil pour {current_user.get('email')}")
    
    try:
        supabase = get_supabase_admin_client()
        
        # Récupérer le profil depuis la table users
        response = supabase.table('users').select('*').eq('auth_user_id', current_user['user_id']).single().execute()
        
        if not response.data:
            # Créer un profil par défaut si inexistant
            default_profile = {
                "auth_user_id": current_user['user_id'],
                "email": current_user['email'],
                "full_name": current_user.get('email', '').split('@')[0],
                "user_type": "producer",
                "language": "fr",
                "created_at": datetime.now().isoformat()
            }
            
            create_response = supabase.table('users').insert(default_profile).execute()
            profile_data = create_response.data[0] if create_response.data else default_profile
            logger.info(f"[get_user_profile] Profil par défaut créé pour {current_user['email']}")
        else:
            profile_data = response.data
            logger.info(f"[get_user_profile] Profil trouvé pour {current_user['email']}")
        
        # Construire la réponse standardisée
        return UserProfileData(
            user_id=current_user['user_id'],
            email=current_user['email'],
            first_name=profile_data.get('first_name'),
            last_name=profile_data.get('last_name'),
            full_name=profile_data.get('full_name'),
            country_code=profile_data.get('country_code'),
            area_code=profile_data.get('area_code'),
            phone_number=profile_data.get('phone_number'),
            country=profile_data.get('country'),
            linkedin_profile=profile_data.get('linkedin_profile'),
            company_name=profile_data.get('company_name'),
            company_website=profile_data.get('company_website'),
            linkedin_corporate=profile_data.get('linkedin_corporate'),
            user_type=profile_data.get('user_type', 'producer'),
            language=profile_data.get('language', 'fr')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_user_profile] Erreur : {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur récupération profil utilisateur")

@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Met à jour le profil de l'utilisateur connecté - ENDPOINT MANQUANT PRINCIPAL"""
    
    logger.info(f"[update_user_profile] Mise à jour profil pour {current_user.get('email')}")
    
    try:
        supabase = get_supabase_admin_client()
        
        # Préparer les données de mise à jour
        update_data = {}
        
        # Traiter chaque champ individuellement
        if profile_update.first_name is not None:
            update_data['first_name'] = profile_update.first_name
        
        if profile_update.last_name is not None:
            update_data['last_name'] = profile_update.last_name
        
        # Construire le full_name si les composants sont fournis
        if profile_update.first_name is not None or profile_update.last_name is not None:
            # Récupérer les valeurs actuelles si partiellement mises à jour
            if profile_update.first_name is not None and profile_update.last_name is not None:
                full_name = f"{profile_update.first_name} {profile_update.last_name}".strip()
            else:
                # Récupérer le profil actuel pour compléter
                current_profile = supabase.table('users').select('first_name,last_name').eq('auth_user_id', current_user['user_id']).single().execute()
                current_first = current_profile.data.get('first_name', '') if current_profile.data else ''
                current_last = current_profile.data.get('last_name', '') if current_profile.data else ''
                
                new_first = profile_update.first_name if profile_update.first_name is not None else current_first
                new_last = profile_update.last_name if profile_update.last_name is not None else current_last
                
                full_name = f"{new_first} {new_last}".strip()
            
            update_data['full_name'] = full_name
        elif profile_update.full_name is not None:
            update_data['full_name'] = profile_update.full_name
        
        # Autres champs
        for field in ['country_code', 'area_code', 'phone_number', 'country', 
                     'linkedin_profile', 'company_name', 'company_website', 
                     'linkedin_corporate', 'user_type', 'language']:
            value = getattr(profile_update, field)
            if value is not None:
                update_data[field] = value
        
        # Ajouter timestamp de mise à jour
        update_data['updated_at'] = datetime.now().isoformat()
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        logger.info(f"[update_user_profile] Champs à mettre à jour : {list(update_data.keys())}")
        
        # Effectuer la mise à jour
        response = supabase.table('users').update(update_data).eq('auth_user_id', current_user['user_id']).execute()
        
        if not response.data:
            # Si pas de données retournées, vérifier si l'utilisateur existe
            check_response = supabase.table('users').select('id').eq('auth_user_id', current_user['user_id']).execute()
            
            if not check_response.data:
                # Créer le profil s'il n'existe pas
                create_data = {
                    "auth_user_id": current_user['user_id'],
                    "email": current_user['email'],
                    **update_data
                }
                
                create_response = supabase.table('users').insert(create_data).execute()
                updated_profile = create_response.data[0] if create_response.data else create_data
                logger.info(f"[update_user_profile] Profil créé pour {current_user['email']}")
            else:
                raise HTTPException(status_code=500, detail="Erreur mise à jour profil")
        else:
            updated_profile = response.data[0]
            logger.info(f"[update_user_profile] Profil mis à jour pour {current_user['email']}")
        
        return UserProfileResponse(
            success=True,
            message="Profil mis à jour avec succès",
            user=updated_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_user_profile] Erreur : {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur mise à jour profil utilisateur")

@router.delete("/profile", response_model=UserProfileResponse)
async def delete_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Supprime le profil utilisateur (RGPD)"""
    
    logger.info(f"[delete_user_profile] Suppression profil pour {current_user.get('email')}")
    
    try:
        supabase = get_supabase_admin_client()
        
        # Supprimer le profil utilisateur
        response = supabase.table('users').delete().eq('auth_user_id', current_user['user_id']).execute()
        
        # Supprimer aussi l'utilisateur auth (optionnel - à débattre)
        try:
            supabase.auth.admin.delete_user(current_user['user_id'])
            logger.info(f"[delete_user_profile] Utilisateur auth supprimé pour {current_user['email']}")
        except Exception as auth_error:
            logger.warning(f"[delete_user_profile] Erreur suppression auth : {auth_error}")
        
        logger.info(f"[delete_user_profile] Profil supprimé pour {current_user['email']}")
        
        return UserProfileResponse(
            success=True,
            message="Profil utilisateur supprimé avec succès"
        )
        
    except Exception as e:
        logger.error(f"[delete_user_profile] Erreur : {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur suppression profil utilisateur")

@router.get("/export", response_model=Dict[str, Any])
async def export_user_data(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Exporte toutes les données utilisateur (RGPD)"""
    
    logger.info(f"[export_user_data] Export données pour {current_user.get('email')}")
    
    try:
        supabase = get_supabase_admin_client()
        
        # Récupérer le profil
        profile_response = supabase.table('users').select('*').eq('auth_user_id', current_user['user_id']).execute()
        
        # Récupérer les invitations envoyées
        invitations_response = supabase.table('invitations').select('*').eq('inviter_email', current_user['email']).execute()
        
        # TODO: Ajouter d'autres données selon vos tables
        # conversations_response = supabase.table('conversations').select('*').eq('user_id', current_user['user_id']).execute()
        
        export_data = {
            "user_profile": profile_response.data[0] if profile_response.data else None,
            "invitations_sent": invitations_response.data or [],
            "export_date": datetime.now().isoformat(),
            "user_id": current_user['user_id'],
            "email": current_user['email']
        }
        
        logger.info(f"[export_user_data] Données exportées pour {current_user['email']}")
        
        return export_data
        
    except Exception as e:
        logger.error(f"[export_user_data] Erreur : {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur export données utilisateur")

@router.get("/debug/profile")
async def debug_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Debug endpoint pour analyser le profil utilisateur"""
    
    try:
        supabase = get_supabase_admin_client()
        
        # Récupérer toutes les infos de debug
        profile_response = supabase.table('users').select('*').eq('auth_user_id', current_user['user_id']).execute()
        
        return {
            "current_user_token_data": current_user,
            "profile_found": bool(profile_response.data),
            "profile_data": profile_response.data[0] if profile_response.data else None,
            "supabase_available": SUPABASE_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[debug_user_profile] Erreur : {str(e)}")
        return {
            "error": str(e),
            "current_user_token_data": current_user,
            "timestamp": datetime.now().isoformat()
        }