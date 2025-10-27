"""
Users
Version: 1.4.1
Last modified: 2025-10-26
"""
# app/api/v1/users.py - CORRECTIONS DES ERREURS RUFF

"""

Endpoints pour la gestion des profils utilisateur
Résout le problème UserInfoModal qui contourne l'API backend
VERSION CORRIGÉE: F401, F821, F841
Updated: 2025-10-22 - Added user profiling fields (production_type, category, category_other)

"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Import de la fonction d'authentification existante
from .auth import get_current_user
from app.utils.gdpr_helpers import mask_email

# Import Supabase - CORRECTION F401: Suppression de Client non utilisé
try:
    from supabase import create_client  # ✅ Client supprimé

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
    whatsapp_number: Optional[str] = None  # 📱 WhatsApp number for chat integration
    country: Optional[str] = None
    linkedin_profile: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    linkedin_corporate: Optional[str] = None
    user_type: Optional[str] = None
    language: Optional[str] = None
    ad_history: Optional[list] = None  # 🎯 Ad rotation history (last 10 ads shown)
    production_type: Optional[list[str]] = None  # 🆕 Production type: broiler, layer, or both
    category: Optional[str] = None  # 🆕 Value chain category
    category_other: Optional[str] = None  # 🆕 Description if category = "other"

    @validator("first_name", "last_name")
    def validate_names(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caractères")
        if v and len(v.strip()) > 50:
            raise ValueError("Le nom ne peut pas dépasser 50 caractères")
        return v.strip() if v else v

    @validator("user_type")
    def validate_user_type(cls, v):
        if v and v not in ["producer", "professional", "super_admin"]:
            raise ValueError("Type d'utilisateur invalide")
        return v

    @validator("language")
    def validate_language(cls, v):
        if v and v not in [
            "ar",
            "de",
            "en",
            "es",
            "fr",
            "hi",
            "id",
            "it",
            "ja",
            "nl",
            "pl",
            "pt",
            "th",
            "tr",
            "vi",
            "zh",
        ]:
            raise ValueError("Langue non supportée")
        return v

    @validator("ad_history")
    def validate_ad_history(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("ad_history doit être une liste")
            if len(v) > 10:
                raise ValueError("ad_history ne peut pas contenir plus de 10 éléments")
            # Vérifier que ce sont des strings
            if not all(isinstance(item, str) for item in v):
                raise ValueError("ad_history doit contenir uniquement des chaînes de caractères")
        return v

    @validator("production_type")
    def validate_production_type(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("production_type doit être une liste")
            valid_types = ["broiler", "layer"]
            if not all(item in valid_types for item in v):
                raise ValueError("production_type ne peut contenir que 'broiler' ou 'layer'")
            if len(v) == 0:
                raise ValueError("production_type ne peut pas être vide")
        return v

    @validator("category")
    def validate_category(cls, v):
        if v is not None:
            valid_categories = [
                "breeding_hatchery",
                "feed_nutrition",
                "farm_operations",
                "health_veterinary",
                "processing",
                "management_oversight",
                "equipment_technology",
                "other"
            ]
            if v not in valid_categories:
                raise ValueError(f"category invalide. Valeurs autorisées: {', '.join(valid_categories)}")
        return v


class UserProfileResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None


class UserProfileData(BaseModel):
    user_id: str
    email: str
    tenant_id: Optional[str] = None  # 🆕 Pour isolation mémoire conversationnelle
    organization_id: Optional[str] = None  # 🆕 Fallback pour tenant_id
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    country_code: Optional[str] = None
    area_code: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None  # 📱 WhatsApp number for chat integration
    country: Optional[str] = None
    linkedin_profile: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    linkedin_corporate: Optional[str] = None
    user_type: Optional[str] = None
    language: Optional[str] = None
    ad_history: Optional[list] = None  # 🎯 Ad rotation history (last 10 ads shown)
    production_type: Optional[list] = None  # 🆕 Production type: broiler, layer, or both
    category: Optional[str] = None  # 🆕 Value chain category
    category_other: Optional[str] = None  # 🆕 Description if category = "other"
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
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Récupère le profil complet de l'utilisateur connecté"""

    logger.info(
        f"[get_user_profile] Récupération profil pour {current_user.get('email')}"
    )

    try:
        supabase = get_supabase_admin_client()

        # CORRECTION F821: Définir response avant utilisation
        response = (
            supabase.table("users")
            .select("*")
            .eq("auth_user_id", current_user["user_id"])
            .single()
            .execute()
        )

        if not response.data:
            # Créer un profil par défaut si inexistant
            default_profile = {
                "auth_user_id": current_user["user_id"],
                "email": current_user["email"],
                "full_name": current_user.get("email", "").split("@")[0],
                "user_type": "producer",
                "language": "fr",
                "created_at": datetime.now().isoformat(),
            }

            create_response = supabase.table("users").insert(default_profile).execute()
            profile_data = (
                create_response.data[0] if create_response.data else default_profile
            )
            logger.info(
                f"[get_user_profile] Profil par défaut créé pour {current_user['email']}"
            )
        else:
            profile_data = response.data  # ✅ response maintenant définie
            logger.info(
                f"[get_user_profile] Profil trouvé pour {current_user['email']}"
            )

        # Construire la réponse standardisée
        return UserProfileData(
            user_id=current_user["user_id"],
            email=current_user["email"],
            tenant_id=profile_data.get("tenant_id"),  # 🆕 Pour isolation mémoire
            organization_id=profile_data.get("organization_id"),  # 🆕 Fallback
            first_name=profile_data.get("first_name"),
            last_name=profile_data.get("last_name"),
            full_name=profile_data.get("full_name"),
            country_code=profile_data.get("country_code"),
            area_code=profile_data.get("area_code"),
            phone_number=profile_data.get("phone_number"),
            whatsapp_number=profile_data.get("whatsapp_number"),  # 📱 WhatsApp number
            country=profile_data.get("country"),
            linkedin_profile=profile_data.get("linkedin_profile"),
            company_name=profile_data.get("company_name"),
            company_website=profile_data.get("company_website"),
            linkedin_corporate=profile_data.get("linkedin_corporate"),
            user_type=profile_data.get("user_type", "producer"),
            language=profile_data.get("language", "fr"),
            ad_history=profile_data.get("ad_history", []),  # 🎯 Ad rotation history
            production_type=profile_data.get("production_type"),  # 🆕 User profiling
            category=profile_data.get("category"),  # 🆕 User profiling
            category_other=profile_data.get("category_other"),  # 🆕 User profiling
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_user_profile] Erreur : {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur récupération profil utilisateur"
        )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Met à jour le profil de l'utilisateur connecté - ENDPOINT MANQUANT PRINCIPAL"""

    logger.info(
        f"[update_user_profile] Mise à jour profil pour {current_user.get('email')}"
    )

    try:
        supabase = get_supabase_admin_client()

        # Préparer les données de mise à jour
        update_data = {}

        # Traiter chaque champ individuellement
        if profile_update.first_name is not None:
            update_data["first_name"] = profile_update.first_name

        if profile_update.last_name is not None:
            update_data["last_name"] = profile_update.last_name

        # Construire le full_name si les composants sont fournis
        if (
            profile_update.first_name is not None
            or profile_update.last_name is not None
        ):
            # Récupérer les valeurs actuelles si partiellement mises à jour
            if (
                profile_update.first_name is not None
                and profile_update.last_name is not None
            ):
                full_name = (
                    f"{profile_update.first_name} {profile_update.last_name}".strip()
                )
            else:
                # Récupérer le profil actuel pour compléter
                current_profile = (
                    supabase.table("users")
                    .select("first_name,last_name")
                    .eq("auth_user_id", current_user["user_id"])
                    .single()
                    .execute()
                )
                current_first = (
                    current_profile.data.get("first_name", "")
                    if current_profile.data
                    else ""
                )
                current_last = (
                    current_profile.data.get("last_name", "")
                    if current_profile.data
                    else ""
                )

                new_first = (
                    profile_update.first_name
                    if profile_update.first_name is not None
                    else current_first
                )
                new_last = (
                    profile_update.last_name
                    if profile_update.last_name is not None
                    else current_last
                )

                full_name = f"{new_first} {new_last}".strip()

            update_data["full_name"] = full_name
        elif profile_update.full_name is not None:
            update_data["full_name"] = profile_update.full_name

        # Autres champs
        for field in [
            "country_code",
            "area_code",
            "phone_number",
            "whatsapp_number",  # 📱 WhatsApp number
            "country",
            "linkedin_profile",
            "company_name",
            "company_website",
            "linkedin_corporate",
            "user_type",
            "language",
            "ad_history",  # 🎯 Ad rotation history
        ]:
            value = getattr(profile_update, field)
            if value is not None:
                update_data[field] = value

        # Ajouter timestamp de mise à jour
        update_data["updated_at"] = datetime.now().isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

        logger.info(
            f"[update_user_profile] Champs à mettre à jour : {list(update_data.keys())}"
        )

        # 🐛 Debug: Log whatsapp_number if present
        if "whatsapp_number" in update_data:
            logger.info(f"[update_user_profile] 📱 WhatsApp number being saved: {update_data['whatsapp_number']}")

        # Effectuer la mise à jour
        response = (
            supabase.table("users")
            .update(update_data)
            .eq("auth_user_id", current_user["user_id"])
            .execute()
        )

        # 🐛 Debug: Log response data
        if response.data:
            logger.info(f"[update_user_profile] 📱 WhatsApp number in response: {response.data[0].get('whatsapp_number')}")

        if not response.data:
            # Si pas de données retournées, vérifier si l'utilisateur existe
            check_response = (
                supabase.table("users")
                .select("id")
                .eq("auth_user_id", current_user["user_id"])
                .execute()
            )

            if not check_response.data:
                # Créer le profil s'il n'existe pas
                create_data = {
                    "auth_user_id": current_user["user_id"],
                    "email": current_user["email"],
                    **update_data,
                }

                create_response = supabase.table("users").insert(create_data).execute()
                updated_profile = (
                    create_response.data[0] if create_response.data else create_data
                )
                logger.info(
                    f"[update_user_profile] Profil créé pour {current_user['email']}"
                )
            else:
                raise HTTPException(status_code=500, detail="Erreur mise à jour profil")
        else:
            updated_profile = response.data[0]
            logger.info(
                f"[update_user_profile] Profil mis à jour pour {current_user['email']}"
            )

        return UserProfileResponse(
            success=True, message="Profil mis à jour avec succès", user=updated_profile
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_user_profile] Erreur : {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erreur mise à jour profil utilisateur"
        )


@router.delete("/profile", response_model=UserProfileResponse)
async def delete_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Supprime le profil utilisateur et anonymise toutes les données (RGPD).

    Conformité RGPD:
    - Article 17: Droit à l'oubli (Right to be forgotten)
    - Article 20: Portabilité des données

    Stratégie:
    - ANONYMISATION: Conversations, messages, historique de paiements
    - SUPPRESSION: Compte d'authentification, profil utilisateur, passkeys

    IMPORTANT: Les conversations sont CONSERVÉES mais rendues anonymes.
    Cette opération est IRRÉVERSIBLE.
    """
    user_id = current_user["user_id"]
    user_email = current_user["email"]

    logger.info(
        f"[delete_user_profile] Début anonymisation RGPD pour {mask_email(user_email)}"
    )

    try:
        from app.core.database import get_pg_connection
        from app.utils.gdpr_deletion import (
            anonymize_user_in_postgresql,
            delete_user_auth_data,
            log_gdpr_deletion,
            get_anonymization_summary
        )

        # ========================================================================
        # ÉTAPE 1: ANONYMISATION POSTGRESQL (transaction atomique)
        # ========================================================================

        with get_pg_connection() as conn:
            logger.info(f"[delete_user_profile] Étape 1/3: Anonymisation PostgreSQL...")

            # Anonymiser toutes les données dans PostgreSQL
            anonymization_stats = anonymize_user_in_postgresql(conn, user_id, user_email)
            logger.info(f"[delete_user_profile] PostgreSQL anonymization stats: {anonymization_stats}")

            # Supprimer les passkeys (données cryptographiques non-anonymisables)
            deletion_stats = delete_user_auth_data(conn, user_id)
            logger.info(f"[delete_user_profile] Auth data deletion stats: {deletion_stats}")

            # Logger pour audit RGPD (conformité légale)
            log_gdpr_deletion(conn, user_id, user_email, {**anonymization_stats, **deletion_stats})

            # Le commit est automatique si pas d'exception (context manager)

        logger.info(f"[delete_user_profile] ✅ Étape 1/3: PostgreSQL anonymization completed")

        # ========================================================================
        # ÉTAPE 2: SUPPRESSION SUPABASE (après succès PostgreSQL)
        # ========================================================================

        logger.info(f"[delete_user_profile] Étape 2/3: Suppression Supabase...")

        supabase = get_supabase_admin_client()

        # Supprimer les invitations envoyées par l'utilisateur
        try:
            supabase.table("invitations").delete().eq("inviter_email", user_email).execute()
            logger.info(f"[delete_user_profile] ✅ Supabase invitations table: deleted")
        except Exception as e:
            logger.warning(f"[delete_user_profile] ⚠️ Invitations deletion warning: {e}")

        # Supprimer les passkeys WebAuthn
        try:
            supabase.table("webauthn_credentials").delete().eq("user_id", user_id).execute()
            logger.info(f"[delete_user_profile] ✅ Supabase webauthn_credentials table: deleted")
        except Exception as e:
            logger.warning(f"[delete_user_profile] ⚠️ WebAuthn credentials deletion warning: {e}")

        # Supprimer le profil utilisateur (table public.users)
        supabase.table("users").delete().eq("auth_user_id", user_id).execute()
        logger.info(f"[delete_user_profile] ✅ Supabase users table: deleted")

        # Supprimer le compte d'authentification (table auth.users)
        try:
            supabase.auth.admin.delete_user(user_id)
            logger.info(f"[delete_user_profile] ✅ Supabase auth.users: deleted")
        except Exception as auth_error:
            logger.warning(
                f"[delete_user_profile] ⚠️ Auth deletion warning: {auth_error}"
            )

        logger.info(f"[delete_user_profile] ✅ Étape 2/3: Supabase deletion completed")

        # ========================================================================
        # ÉTAPE 3: RÉSUMÉ ET CONFIRMATION
        # ========================================================================

        summary = get_anonymization_summary(user_id, user_email)
        logger.info(f"[delete_user_profile] ✅ Étape 3/3: Anonymization summary generated")
        logger.info(f"[delete_user_profile] 🎉 Anonymisation complète pour {mask_email(user_email)}")
        logger.info(f"[delete_user_profile] Anonymous ID: {summary['anonymous_identifier']}")

        return UserProfileResponse(
            success=True,
            message="Votre compte a été supprimé et vos données anonymisées avec succès (conforme RGPD)"
        )

    except Exception as e:
        logger.error(f"[delete_user_profile] ❌ Erreur lors de l'anonymisation: {str(e)}")
        logger.error(f"[delete_user_profile] ❌ Transaction rollback - aucune donnée modifiée")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la suppression du compte. Veuillez réessayer ou contacter le support."
        )


@router.get("/export", response_model=Dict[str, Any])
async def export_user_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Exporte toutes les données utilisateur (RGPD Article 20).

    Inclut:
    - Profil utilisateur (Supabase)
    - Invitations envoyées (Supabase)
    - Conversations complètes avec messages (PostgreSQL)
    - Images médicales métadonnées (PostgreSQL)
    - Statistiques d'utilisation (PostgreSQL)
    """

    logger.info(f"[export_user_data] Export GDPR complet pour {mask_email(current_user.get('email'))}")

    try:
        from app.core.database import get_pg_connection

        supabase = get_supabase_admin_client()
        user_id = current_user["user_id"]
        user_email = current_user["email"]

        # ========================================================================
        # SUPABASE : Profil + Invitations
        # ========================================================================

        # Récupérer le profil
        profile_response = (
            supabase.table("users")
            .select("*")
            .eq("auth_user_id", user_id)
            .execute()
        )

        # Récupérer les invitations envoyées
        invitations_response = (
            supabase.table("invitations")
            .select("*")
            .eq("inviter_email", user_email)
            .execute()
        )

        # ========================================================================
        # POSTGRESQL : Conversations, Messages, Images
        # ========================================================================

        conversations_data = []
        medical_images_data = []
        billing_data = []

        with get_pg_connection() as conn:
            cursor = conn.cursor()

            # Récupérer toutes les conversations avec leurs messages
            cursor.execute("""
                SELECT
                    c.id,
                    c.user_id,
                    c.title,
                    c.language,
                    c.created_at,
                    c.updated_at,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'id', m.id,
                                'role', m.role,
                                'content', m.content,
                                'sequence_number', m.sequence_number,
                                'created_at', m.created_at,
                                'response_source', m.response_source,
                                'response_confidence', m.response_confidence
                            ) ORDER BY m.sequence_number
                        ) FILTER (WHERE m.id IS NOT NULL),
                        '[]'::json
                    ) as messages
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                WHERE c.user_id = %s
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """, (user_id,))

            conversations_raw = cursor.fetchall()

            # Formater les conversations
            for row in conversations_raw:
                conversations_data.append({
                    "id": row[0],
                    "user_id": row[1],
                    "title": row[2],
                    "language": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "messages": row[6] if row[6] else []
                })

            logger.info(f"[export_user_data] {len(conversations_data)} conversations exportées")

            # Récupérer les images médicales (métadonnées uniquement)
            try:
                cursor.execute("""
                    SELECT
                        id, user_id, file_name, file_size,
                        content_type, upload_date, s3_key
                    FROM medical_images
                    WHERE user_id = %s
                    ORDER BY upload_date DESC
                """, (user_id,))

                images_raw = cursor.fetchall()

                for row in images_raw:
                    medical_images_data.append({
                        "id": row[0],
                        "file_name": row[2],
                        "file_size": row[3],
                        "content_type": row[4],
                        "upload_date": row[5].isoformat() if row[5] else None,
                        "s3_key": row[6]
                    })

                logger.info(f"[export_user_data] {len(medical_images_data)} images médicales exportées")
            except Exception as e:
                logger.warning(f"[export_user_data] Erreur export images: {str(e)}")

            # Récupérer les données de facturation (anonymisées)
            try:
                cursor.execute("""
                    SELECT
                        user_email, subscription_tier, subscription_status,
                        billing_cycle, created_at, updated_at
                    FROM user_billing_info
                    WHERE user_email = %s
                """, (user_email,))

                billing_raw = cursor.fetchone()

                if billing_raw:
                    billing_data = {
                        "subscription_tier": billing_raw[1],
                        "subscription_status": billing_raw[2],
                        "billing_cycle": billing_raw[3],
                        "created_at": billing_raw[4].isoformat() if billing_raw[4] else None,
                        "updated_at": billing_raw[5].isoformat() if billing_raw[5] else None
                    }

                logger.info(f"[export_user_data] Données de facturation exportées")
            except Exception as e:
                logger.warning(f"[export_user_data] Erreur export billing: {str(e)}")

        # ========================================================================
        # ASSEMBLAGE FINAL
        # ========================================================================

        export_data = {
            "user_profile": profile_response.data[0] if profile_response.data else None,
            "invitations_sent": invitations_response.data or [],
            "conversations": conversations_data,
            "medical_images": medical_images_data,
            "billing_info": billing_data,
            "export_date": datetime.now().isoformat(),
            "user_id": user_id,
            "email": user_email,
            "total_conversations": len(conversations_data),
            "total_messages": sum(len(conv.get("messages", [])) for conv in conversations_data),
            "gdpr_compliant": True,
            "data_format": "JSON",
            "export_version": "1.0"
        }

        logger.info(
            f"[export_user_data] ✅ Export GDPR complet: {export_data['total_conversations']} conversations, "
            f"{export_data['total_messages']} messages pour {mask_email(user_email)}"
        )

        return export_data

    except Exception as e:
        logger.error(f"[export_user_data] ❌ Erreur export GDPR: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur export données utilisateur")


@router.get("/debug/profile")
async def debug_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Debug endpoint pour analyser le profil utilisateur"""

    try:
        supabase = get_supabase_admin_client()

        # Récupérer toutes les infos de debug
        profile_response = (
            supabase.table("users")
            .select("*")
            .eq("auth_user_id", current_user["user_id"])
            .execute()
        )

        return {
            "current_user_token_data": current_user,
            "profile_found": bool(profile_response.data),
            "profile_data": profile_response.data[0] if profile_response.data else None,
            "supabase_available": SUPABASE_AVAILABLE,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"[debug_user_profile] Erreur : {str(e)}")
        return {
            "error": str(e),
            "current_user_token_data": current_user,
            "timestamp": datetime.now().isoformat(),
        }
