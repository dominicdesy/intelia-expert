# -*- coding: utf-8 -*-
"""
compliance.py - Compliance and Biosecurity Wrapper
Version: 1.0.0
Last modified: 2025-10-28

CRITICAL: This module ensures legal defensibility by adapting disclaimers
and tone based on user role (veterinarian vs producer vs management).
"""

import logging
from typing import Dict, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User role categories for compliance"""

    VETERINARY = "health_veterinary"
    NUTRITION = "feed_nutrition"
    BREEDING = "breeding_hatchery"
    PRODUCTION = "farm_operations"
    MANAGEMENT = "management_oversight"
    EQUIPMENT = "equipment_technology"
    PROCESSING = "processing"
    UNKNOWN = "unknown"


class ComplianceLevel(Enum):
    """Compliance levels for different query types"""

    MINIMAL = "minimal"  # General information
    STANDARD = "standard"  # Normal queries
    REINFORCED = "reinforced"  # Health/disease queries
    CRITICAL = "critical"  # Biosecurity/regulatory queries


class ComplianceWrapper:
    """
    Wrapper for legal compliance and biosecurity

    Adapts disclaimers and tone based on:
    1. User role (veterinarian, producer, management)
    2. Query sensitivity (general, health, biosecurity)
    3. Language

    Legal protection:
    - Veterinarians: Minimal disclaimers (they're qualified)
    - Producers: Reinforced disclaimers (recommend vet consultation)
    - Management: Strategic disclaimers (validate with experts)

    Biosecurity compliance:
    - Critical queries get biosecurity warnings
    - Regulatory queries include compliance notes
    """

    def __init__(self) -> None:
        """Initialize compliance wrapper"""
        # Biosecurity keywords that trigger reinforced disclaimers
        self.biosecurity_keywords = {
            "en": [
                "quarantine",
                "outbreak",
                "contamination",
                "disinfection",
                "biosecurity",
                "epidemic",
                "pandemic",
                "infection control",
                "isolation",
                "decontamination",
            ],
            "fr": [
                "quarantaine",
                "épidémie",
                "contamination",
                "désinfection",
                "biosécurité",
                "pandémie",
                "contrôle infection",
                "isolement",
                "décontamination",
            ],
            "es": [
                "cuarentena",
                "brote",
                "contaminación",
                "desinfección",
                "bioseguridad",
                "epidemia",
                "pandemia",
                "control de infección",
                "aislamiento",
            ],
        }

        # Regulatory keywords
        self.regulatory_keywords = {
            "en": [
                "regulation",
                "compliance",
                "legal",
                "law",
                "authorized",
                "approved",
                "certification",
                "standard",
                "requirement",
                "mandate",
            ],
            "fr": [
                "réglementation",
                "conformité",
                "légal",
                "loi",
                "autorisé",
                "approuvé",
                "certification",
                "norme",
                "exigence",
                "mandat",
            ],
            "es": [
                "regulación",
                "cumplimiento",
                "legal",
                "ley",
                "autorizado",
                "aprobado",
                "certificación",
                "estándar",
                "requisito",
                "mandato",
            ],
        }

        logger.info("[OK] ComplianceWrapper initialized")

    def get_compliance_level(
        self, query: str, is_veterinary_query: bool, language: str = "en"
    ) -> ComplianceLevel:
        """
        Determine compliance level for query

        Args:
            query: User query
            is_veterinary_query: Whether query is health-related
            language: Query language

        Returns:
            ComplianceLevel enum
        """
        query_lower = query.lower()

        # 🚫 EXCLUDE Intelia product questions (nano, compass, unity, farmhub, cognito)
        # These are technical product questions, NOT biosecurity/veterinary questions
        intelia_products = ["nano", "compass", "unity", "farmhub", "cognito"]
        if any(product in query_lower for product in intelia_products):
            logger.debug(f"📦 Intelia product detected in query - using MINIMAL compliance level")
            return ComplianceLevel.MINIMAL

        # CRITICAL: Biosecurity or regulatory queries
        biosec_kw = self.biosecurity_keywords.get(
            language, self.biosecurity_keywords["en"]
        )
        reg_kw = self.regulatory_keywords.get(language, self.regulatory_keywords["en"])

        if any(kw in query_lower for kw in biosec_kw + reg_kw):
            return ComplianceLevel.CRITICAL

        # REINFORCED: Veterinary/health queries
        if is_veterinary_query:
            return ComplianceLevel.REINFORCED

        # STANDARD: Normal queries
        return ComplianceLevel.STANDARD

    def get_role_based_disclaimer(
        self,
        user_category: Optional[str],
        compliance_level: ComplianceLevel,
        language: str = "en",
    ) -> str:
        """
        Get disclaimer adapted to user role and compliance level

        Args:
            user_category: User category (health_veterinary, farm_operations, etc.)
            compliance_level: Query compliance level
            language: Response language

        Returns:
            Disclaimer text (empty string if minimal)
        """
        # Determine user role
        try:
            role = UserRole(user_category) if user_category else UserRole.UNKNOWN
        except ValueError:
            role = UserRole.UNKNOWN

        # Get appropriate disclaimer template
        disclaimer_key = self._get_disclaimer_key(role, compliance_level)

        # Get localized disclaimer
        disclaimers = self._get_disclaimers(language)
        disclaimer = disclaimers.get(disclaimer_key, "")

        if disclaimer:
            logger.debug(
                f"Compliance disclaimer: role={role.value}, level={compliance_level.value}, "
                f"key={disclaimer_key}"
            )

        return disclaimer

    def _get_disclaimer_key(self, role: UserRole, level: ComplianceLevel) -> str:
        """
        Get disclaimer key based on role and compliance level

        Returns:
            Disclaimer key (e.g., "vet_standard", "producer_critical")
        """
        # VETERINARIANS: Minimal disclaimers (they're qualified)
        if role in [UserRole.VETERINARY, UserRole.NUTRITION, UserRole.BREEDING]:
            if level == ComplianceLevel.CRITICAL:
                return "vet_critical"
            elif level == ComplianceLevel.REINFORCED:
                return "vet_reinforced"
            else:
                return "vet_minimal"  # Very light or none

        # PRODUCERS: Reinforced disclaimers (recommend vet consultation)
        elif role == UserRole.PRODUCTION:
            if level == ComplianceLevel.CRITICAL:
                return "producer_critical"
            elif level == ComplianceLevel.REINFORCED:
                return "producer_reinforced"
            else:
                return "producer_standard"

        # MANAGEMENT: Strategic disclaimers (validate with experts)
        elif role in [UserRole.MANAGEMENT, UserRole.EQUIPMENT, UserRole.PROCESSING]:
            if level == ComplianceLevel.CRITICAL:
                return "management_critical"
            elif level == ComplianceLevel.REINFORCED:
                return "management_reinforced"
            else:
                return "management_standard"

        # UNKNOWN: Default to safe (producer-level)
        else:
            if level == ComplianceLevel.CRITICAL:
                return "producer_critical"
            elif level == ComplianceLevel.REINFORCED:
                return "producer_reinforced"
            else:
                return "producer_standard"

    def _get_disclaimers(self, language: str) -> Dict[str, str]:
        """
        Get all disclaimer templates for a language

        Returns:
            Dict of disclaimer_key -> disclaimer_text
        """
        disclaimers = {
            "en": {
                # VETERINARY DISCLAIMERS (minimal - they're professionals)
                "vet_minimal": "",  # No disclaimer for general queries to vets
                "vet_reinforced": "\n\n⚕️ **Professional Note**: This information is provided for reference. Always validate with current research and clinical guidelines.",
                "vet_critical": "\n\n⚠️ **Biosecurity/Regulatory Alert**: Ensure compliance with local regulations and biosecurity protocols. Consult official guidelines and regulatory authorities.",
                # PRODUCER DISCLAIMERS (reinforced - need vet guidance)
                "producer_standard": "\n\n📋 **Note**: This information is for educational purposes. For specific issues on your farm, consult a veterinarian or poultry specialist.",
                "producer_reinforced": "\n\n⚕️ **Important**: This information does not replace veterinary consultation. For health issues, disease diagnosis, or treatment decisions, always consult a licensed veterinarian.",
                "producer_critical": "\n\n⚠️ **CRITICAL**: Biosecurity and regulatory compliance are essential. This information is general guidance only. For disease outbreaks, biosecurity protocols, or regulatory compliance, immediately consult:\n• Your veterinarian\n• Local animal health authorities\n• Biosecurity officials\n\nNon-compliance may result in serious economic and legal consequences.",
                # MANAGEMENT DISCLAIMERS (strategic - need expert validation)
                "management_standard": "\n\n📊 **Management Note**: This analysis is for strategic planning. Validate recommendations with your technical team (veterinarian, nutritionist, production manager) before implementation.",
                "management_reinforced": "\n\n⚕️ **Strategic Recommendation**: Health and production decisions should be validated by qualified professionals (veterinarians, nutritionists, specialists) before implementation.",
                "management_critical": "\n\n⚠️ **CRITICAL DECISION**: Biosecurity, regulatory, and compliance decisions require expert validation. Consult:\n• Veterinary advisors\n• Biosecurity specialists\n• Legal/regulatory compliance team\n\nStrategic decisions in these areas carry significant financial and legal risks.",
            },
            "fr": {
                # VÉTÉRINAIRES (minimal)
                "vet_minimal": "",
                "vet_reinforced": "\n\n⚕️ **Note professionnelle**: Cette information est fournie à titre de référence. Toujours valider avec la recherche actuelle et les directives cliniques.",
                "vet_critical": "\n\n⚠️ **Alerte biosécurité/réglementation**: Assurez la conformité avec les réglementations locales et protocoles de biosécurité. Consultez les directives officielles et autorités réglementaires.",
                # PRODUCTEURS (renforcé)
                "producer_standard": "\n\n📋 **Note**: Cette information est à titre éducatif. Pour des problèmes spécifiques sur votre ferme, consultez un vétérinaire ou spécialiste avicole.",
                "producer_reinforced": "\n\n⚕️ **Important**: Cette information ne remplace pas une consultation vétérinaire. Pour les problèmes de santé, diagnostics ou décisions de traitement, consultez toujours un vétérinaire agréé.",
                "producer_critical": "\n\n⚠️ **CRITIQUE**: La biosécurité et conformité réglementaire sont essentielles. Cette information est un guide général. Pour les épidémies, protocoles de biosécurité ou conformité réglementaire, consultez immédiatement:\n• Votre vétérinaire\n• Autorités de santé animale locales\n• Responsables de biosécurité\n\nLa non-conformité peut entraîner de graves conséquences économiques et légales.",
                # MANAGEMENT (stratégique)
                "management_standard": "\n\n📊 **Note de gestion**: Cette analyse est pour la planification stratégique. Validez les recommandations avec votre équipe technique (vétérinaire, nutritionniste, directeur de production) avant mise en œuvre.",
                "management_reinforced": "\n\n⚕️ **Recommandation stratégique**: Les décisions de santé et production doivent être validées par des professionnels qualifiés (vétérinaires, nutritionnistes, spécialistes) avant mise en œuvre.",
                "management_critical": "\n\n⚠️ **DÉCISION CRITIQUE**: Les décisions de biosécurité, réglementaires et de conformité nécessitent une validation d'experts. Consultez:\n• Conseillers vétérinaires\n• Spécialistes en biosécurité\n• Équipe juridique/conformité réglementaire\n\nLes décisions stratégiques dans ces domaines comportent des risques financiers et légaux importants.",
            },
            "es": {
                # VETERINARIOS (mínimo)
                "vet_minimal": "",
                "vet_reinforced": "\n\n⚕️ **Nota profesional**: Esta información se proporciona como referencia. Siempre valide con investigación actual y directrices clínicas.",
                "vet_critical": "\n\n⚠️ **Alerta bioseguridad/regulatoria**: Asegure cumplimiento con regulaciones locales y protocolos de bioseguridad. Consulte directrices oficiales y autoridades regulatorias.",
                # PRODUCTORES (reforzado)
                "producer_standard": "\n\n📋 **Nota**: Esta información es para fines educativos. Para problemas específicos en su granja, consulte a un veterinario o especialista avícola.",
                "producer_reinforced": "\n\n⚕️ **Importante**: Esta información no reemplaza consulta veterinaria. Para problemas de salud, diagnósticos o decisiones de tratamiento, siempre consulte a un veterinario licenciado.",
                "producer_critical": "\n\n⚠️ **CRÍTICO**: Bioseguridad y cumplimiento regulatorio son esenciales. Esta información es orientación general. Para brotes, protocolos de bioseguridad o cumplimiento regulatorio, consulte inmediatamente:\n• Su veterinario\n• Autoridades locales de salud animal\n• Oficiales de bioseguridad\n\nEl incumplimiento puede resultar en graves consecuencias económicas y legales.",
                # GESTIÓN (estratégico)
                "management_standard": "\n\n📊 **Nota de gestión**: Este análisis es para planificación estratégica. Valide recomendaciones con su equipo técnico (veterinario, nutricionista, director de producción) antes de implementación.",
                "management_reinforced": "\n\n⚕️ **Recomendación estratégica**: Decisiones de salud y producción deben ser validadas por profesionales calificados (veterinarios, nutricionistas, especialistas) antes de implementación.",
                "management_critical": "\n\n⚠️ **DECISIÓN CRÍTICA**: Decisiones de bioseguridad, regulatorias y cumplimiento requieren validación de expertos. Consulte:\n• Asesores veterinarios\n• Especialistas en bioseguridad\n• Equipo legal/cumplimiento regulatorio\n\nDecisiones estratégicas en estas áreas conllevan riesgos financieros y legales significativos.",
            },
        }

        return disclaimers.get(language, disclaimers["en"])

    def wrap_response(
        self,
        response: str,
        query: str,
        user_category: Optional[str],
        is_veterinary_query: bool,
        language: str = "en",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Wrap response with compliance disclaimers

        Args:
            response: Generated response
            query: Original query
            user_category: User category (health_veterinary, farm_operations, etc.)
            is_veterinary_query: Whether query is health-related
            language: Response language

        Returns:
            Tuple of (wrapped_response, metadata)
        """
        # Determine compliance level
        compliance_level = self.get_compliance_level(
            query, is_veterinary_query, language
        )

        # Get role-based disclaimer
        disclaimer = self.get_role_based_disclaimer(
            user_category, compliance_level, language
        )

        # Add disclaimer if not empty
        if disclaimer:
            wrapped = response + disclaimer
        else:
            wrapped = response

        # Metadata for logging/monitoring
        metadata = {
            "compliance_level": compliance_level.value,
            "user_category": user_category or "unknown",
            "disclaimer_added": bool(disclaimer),
            "disclaimer_length": len(disclaimer) if disclaimer else 0,
        }

        return wrapped, metadata


# Singleton instance
_compliance_instance = None


def get_compliance_wrapper() -> ComplianceWrapper:
    """Get or create ComplianceWrapper singleton"""
    global _compliance_instance

    if _compliance_instance is None:
        _compliance_instance = ComplianceWrapper()

    return _compliance_instance
