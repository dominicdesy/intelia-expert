"""
Zoho Campaigns Integration Service
Version: 1.0.0
Last modified: 2025-10-31

Service pour synchroniser les nouveaux utilisateurs avec Zoho Campaigns
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ZohoCampaignsService:
    """Service pour intégrer Zoho Campaigns"""

    def __init__(self):
        self.client_id = os.getenv("ZOHO_CLIENT_ID")
        self.client_secret = os.getenv("ZOHO_CLIENT_SECRET")
        self.refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        self.region = os.getenv("ZOHO_REGION", "com")  # com, eu, in, etc.
        self.list_key = os.getenv("ZOHO_CAMPAIGNS_LIST_KEY")  # List key where contacts will be added

        # Construire l'URL de base selon la région
        self.api_base_url = f"https://campaigns.zoho.{self.region}/api/v1.1"
        self.accounts_url = f"https://accounts.zoho.{self.region}/oauth/v2/token"

        self.access_token = None
        self.token_expires_at = None

    def is_configured(self) -> bool:
        """Vérifie si le service Zoho est configuré"""
        return all([
            self.client_id,
            self.client_secret,
            self.refresh_token,
            self.list_key
        ])

    async def get_access_token(self) -> Optional[str]:
        """
        Obtient un access token valide via le refresh token
        Cache le token jusqu'à expiration
        """
        # Si token existe et n'est pas expiré, le réutiliser
        if self.access_token and self.token_expires_at:
            if datetime.now().timestamp() < self.token_expires_at:
                return self.access_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.accounts_url,
                    params={
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "refresh_token"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    # Les tokens Zoho expirent après 1 heure
                    expires_in = data.get("expires_in", 3600)
                    self.token_expires_at = datetime.now().timestamp() + expires_in - 60  # 1 min de marge

                    logger.info("[Zoho] Access token obtenu avec succès")
                    return self.access_token
                else:
                    logger.error(f"[Zoho] Erreur obtention token: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"[Zoho] Exception lors de l'obtention du token: {str(e)}")
            return None

    async def add_contact(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        country: Optional[str] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        Ajoute ou met à jour un contact dans Zoho Campaigns

        Args:
            email: Email du contact (requis)
            first_name: Prénom du contact
            last_name: Nom du contact
            country: Pays du contact
            **extra_fields: Champs supplémentaires (company, phone, etc.)

        Returns:
            Dict avec success: bool et message/error
        """
        if not self.is_configured():
            logger.warning("[Zoho] Service non configuré - contact non synchronisé")
            return {
                "success": False,
                "error": "Zoho Campaigns non configuré",
                "skipped": True
            }

        try:
            # Obtenir un access token valide
            access_token = await self.get_access_token()
            if not access_token:
                return {
                    "success": False,
                    "error": "Impossible d'obtenir un access token"
                }

            # Construire les données du contact
            contact_data = {
                "contact_email": email,
                "contact_info": {}
            }

            # Ajouter les champs standards
            if first_name:
                contact_data["contact_info"]["First Name"] = first_name
            if last_name:
                contact_data["contact_info"]["Last Name"] = last_name
            if country:
                contact_data["contact_info"]["Country"] = country

            # Ajouter les champs supplémentaires
            for key, value in extra_fields.items():
                if value:
                    # Convertir snake_case en Title Case pour Zoho
                    field_name = key.replace("_", " ").title()
                    contact_data["contact_info"][field_name] = value

            # Appeler l'API Zoho Campaigns pour ajouter le contact
            url = f"{self.api_base_url}/json/listsubscribe"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params={
                        "resfmt": "JSON",
                        "listkey": self.list_key
                    },
                    headers={
                        "Authorization": f"Zoho-oauthtoken {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=contact_data,
                    timeout=10.0
                )

                response_data = response.json()

                if response.status_code == 200:
                    # Vérifier le code de statut Zoho
                    zoho_code = response_data.get("code")

                    if zoho_code == "0":
                        # Succès
                        logger.info(f"[Zoho] Contact ajouté avec succès: {email}")
                        return {
                            "success": True,
                            "message": "Contact ajouté à Zoho Campaigns",
                            "data": response_data
                        }
                    elif zoho_code == "1006":
                        # Contact déjà existant
                        logger.info(f"[Zoho] Contact déjà existant: {email}")
                        return {
                            "success": True,
                            "message": "Contact déjà présent dans Zoho Campaigns",
                            "data": response_data,
                            "already_exists": True
                        }
                    else:
                        # Autre erreur Zoho
                        error_msg = response_data.get("message", "Erreur inconnue")
                        logger.error(f"[Zoho] Erreur API (code {zoho_code}): {error_msg}")
                        return {
                            "success": False,
                            "error": f"Erreur Zoho: {error_msg}",
                            "zoho_code": zoho_code
                        }
                else:
                    logger.error(f"[Zoho] Erreur HTTP {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": f"Erreur HTTP {response.status_code}"
                    }

        except httpx.TimeoutException:
            logger.error(f"[Zoho] Timeout lors de l'ajout du contact: {email}")
            return {
                "success": False,
                "error": "Timeout lors de la connexion à Zoho"
            }
        except Exception as e:
            logger.error(f"[Zoho] Exception lors de l'ajout du contact {email}: {str(e)}")
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }

    async def sync_new_user(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        country: Optional[str] = None,
        company_name: Optional[str] = None,
        phone: Optional[str] = None,
        language: Optional[str] = None,
        production_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronise un nouvel utilisateur avec Zoho Campaigns
        Méthode spécifique pour l'inscription utilisateur

        Args:
            email: Email de l'utilisateur
            first_name: Prénom
            last_name: Nom
            country: Pays
            company_name: Nom de l'entreprise
            phone: Téléphone
            language: Langue préférée
            production_type: Type de production (broiler, layer, etc.)
            category: Catégorie utilisateur

        Returns:
            Dict avec success: bool et détails
        """
        logger.info(f"[Zoho] Synchronisation nouvel utilisateur: {email}")

        result = await self.add_contact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            country=country,
            company=company_name,
            phone=phone,
            language=language,
            production_type=production_type,
            category=category
        )

        if result.get("success"):
            logger.info(f"[Zoho] ✅ Utilisateur synchronisé: {email}")
        elif result.get("skipped"):
            logger.debug(f"[Zoho] ⊘ Synchronisation ignorée (service non configuré): {email}")
        else:
            logger.warning(f"[Zoho] ⚠️ Échec synchronisation: {email} - {result.get('error')}")

        return result


# Instance globale du service
zoho_campaigns_service = ZohoCampaignsService()
