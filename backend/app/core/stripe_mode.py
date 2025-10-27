# -*- coding: utf-8 -*-
"""
stripe_mode.py - Gestion des modes de fonctionnement Stripe
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
stripe_mode.py - Gestion des modes de fonctionnement Stripe

Modes disponibles:
- PRODUCTION: Stripe actif, facture réellement les clients, quotas appliqués
- TEST: Stripe en mode test, pas de vraie facturation, quotas appliqués
- DISABLE: Stripe désactivé, aucune limite, développement libre

Configuration via variable d'environnement: STRIPE_MODE=production|test|disable
"""
import os
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class StripeMode(str, Enum):
    """Modes de fonctionnement Stripe"""
    PRODUCTION = "production"
    TEST = "test"
    DISABLE = "disable"


class StripeConfig:
    """Configuration globale Stripe basée sur le mode"""

    def __init__(self):
        self._mode = self._detect_mode()
        self._log_mode_info()

    def _detect_mode(self) -> StripeMode:
        """Détecte le mode depuis les variables d'environnement"""
        mode_str = os.getenv("STRIPE_MODE", "disable").lower()

        if mode_str in ["production", "prod"]:
            return StripeMode.PRODUCTION
        elif mode_str in ["test", "testing"]:
            return StripeMode.TEST
        elif mode_str in ["disable", "disabled", "off"]:
            return StripeMode.DISABLE
        else:
            logger.warning(
                f"Mode Stripe invalide: '{mode_str}'. "
                f"Utilisation du mode DISABLE par défaut."
            )
            return StripeMode.DISABLE

    def _log_mode_info(self):
        """Log les informations sur le mode actuel"""
        mode_info = {
            StripeMode.PRODUCTION: {
                "emoji": "💳",
                "description": "MODE PRODUCTION - Facturation réelle activée",
                "features": [
                    "Stripe en mode live",
                    "Vraie facturation des clients",
                    "Quotas mensuels appliqués (Essential: 50 questions/mois)",
                    "Webhooks Stripe actifs",
                ]
            },
            StripeMode.TEST: {
                "emoji": "🧪",
                "description": "MODE TEST - Environnement de test Stripe",
                "features": [
                    "Stripe en mode test",
                    "Pas de vraie facturation",
                    "Quotas appliqués (pour tester les limites)",
                    "Cartes de test Stripe utilisables",
                ]
            },
            StripeMode.DISABLE: {
                "emoji": "🔓",
                "description": "MODE DISABLE - Stripe désactivé",
                "features": [
                    "Stripe complètement désactivé",
                    "Aucune limite de questions",
                    "Développement et tests locaux",
                    "Pas de vérification de plan",
                ]
            }
        }

        info = mode_info[self._mode]
        logger.info(f"{info['emoji']} {info['description']}")
        for feature in info['features']:
            logger.info(f"  ✓ {feature}")

    @property
    def mode(self) -> StripeMode:
        """Retourne le mode actuel"""
        return self._mode

    @property
    def is_production(self) -> bool:
        """True si en mode production"""
        return self._mode == StripeMode.PRODUCTION

    @property
    def is_test(self) -> bool:
        """True si en mode test"""
        return self._mode == StripeMode.TEST

    @property
    def is_disabled(self) -> bool:
        """True si Stripe est désactivé"""
        return self._mode == StripeMode.DISABLE

    @property
    def quota_enforcement_enabled(self) -> bool:
        """
        True si les quotas doivent être appliqués.

        - PRODUCTION: True (facture les vrais clients)
        - TEST: True (pour tester les limites)
        - DISABLE: False (développement libre)
        """
        return self._mode in [StripeMode.PRODUCTION, StripeMode.TEST]

    @property
    def stripe_enabled(self) -> bool:
        """True si Stripe est actif (production ou test)"""
        return self._mode in [StripeMode.PRODUCTION, StripeMode.TEST]

    @property
    def stripe_api_key(self) -> Optional[str]:
        """
        Retourne la clé API Stripe appropriée selon le mode.

        - PRODUCTION: STRIPE_SECRET_KEY (live key)
        - TEST: STRIPE_TEST_SECRET_KEY
        - DISABLE: None
        """
        if self._mode == StripeMode.PRODUCTION:
            return os.getenv("STRIPE_SECRET_KEY")
        elif self._mode == StripeMode.TEST:
            return os.getenv("STRIPE_TEST_SECRET_KEY")
        else:
            return None

    @property
    def stripe_publishable_key(self) -> Optional[str]:
        """
        Retourne la clé publique Stripe appropriée selon le mode.

        - PRODUCTION: STRIPE_PUBLISHABLE_KEY (live key)
        - TEST: STRIPE_TEST_PUBLISHABLE_KEY
        - DISABLE: None
        """
        if self._mode == StripeMode.PRODUCTION:
            return os.getenv("STRIPE_PUBLISHABLE_KEY")
        elif self._mode == StripeMode.TEST:
            return os.getenv("STRIPE_TEST_PUBLISHABLE_KEY")
        else:
            return None

    @property
    def webhook_secret(self) -> Optional[str]:
        """
        Retourne le secret webhook Stripe selon le mode.

        - PRODUCTION: STRIPE_WEBHOOK_SECRET (live webhook)
        - TEST: STRIPE_TEST_WEBHOOK_SECRET
        - DISABLE: None
        """
        if self._mode == StripeMode.PRODUCTION:
            return os.getenv("STRIPE_WEBHOOK_SECRET")
        elif self._mode == StripeMode.TEST:
            return os.getenv("STRIPE_TEST_WEBHOOK_SECRET")
        else:
            return None

    def get_config_dict(self) -> dict:
        """Retourne la configuration complète sous forme de dictionnaire"""
        return {
            "mode": self._mode.value,
            "is_production": self.is_production,
            "is_test": self.is_test,
            "is_disabled": self.is_disabled,
            "stripe_enabled": self.stripe_enabled,
            "quota_enforcement": self.quota_enforcement_enabled,
            "has_api_key": self.stripe_api_key is not None,
            "has_publishable_key": self.stripe_publishable_key is not None,
            "has_webhook_secret": self.webhook_secret is not None,
        }


# Instance globale singleton
_stripe_config: Optional[StripeConfig] = None


def get_stripe_config() -> StripeConfig:
    """
    Retourne l'instance singleton de la configuration Stripe.
    Initialise la configuration au premier appel.
    """
    global _stripe_config
    if _stripe_config is None:
        _stripe_config = StripeConfig()
    return _stripe_config


def is_quota_enforcement_enabled() -> bool:
    """
    Fonction utilitaire pour vérifier si les quotas doivent être appliqués.

    Utilisée par le service de limitation d'usage.

    Returns:
        - True en mode PRODUCTION ou TEST
        - False en mode DISABLE
    """
    config = get_stripe_config()
    return config.quota_enforcement_enabled


def is_stripe_enabled() -> bool:
    """
    Fonction utilitaire pour vérifier si Stripe est actif.

    Returns:
        - True en mode PRODUCTION ou TEST
        - False en mode DISABLE
    """
    config = get_stripe_config()
    return config.stripe_enabled


def get_current_mode() -> StripeMode:
    """Retourne le mode Stripe actuel"""
    config = get_stripe_config()
    return config.mode
