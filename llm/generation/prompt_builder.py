# -*- coding: utf-8 -*-
"""
prompt_builder.py - Constructeur de prompts spécialisés
Version 2.0 - Utilise system_prompts.json centralisé
"""

import logging
from typing import Dict, Optional, Any

from processing.intent_types import IntentType, IntentResult

# Import du gestionnaire de prompts centralisé
try:
    # ✅ CORRECTION: Import relatif au lieu d'import absolu
    from ..config.system_prompts import get_prompts_manager

    PROMPTS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("SystemPromptsManager chargé avec succès")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"SystemPromptsManager import error: {e}")
    PROMPTS_AVAILABLE = False
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"SystemPromptsManager error: {e}")
    PROMPTS_AVAILABLE = False


class PromptBuilder:
    """
    Constructeur de prompts spécialisés pour les différents types d'intentions
    Version 2.0: Charge les prompts depuis system_prompts.json
    """

    def __init__(
        self,
        intents_config: dict,
        language: str = "fr",
        prompts_path: Optional[str] = None,
    ):
        """
        Initialise le constructeur de prompts

        Args:
            intents_config: Configuration des intentions (héritage)
            language: Langue par défaut ("fr" ou "en")
            prompts_path: Chemin custom vers system_prompts.json (optionnel)
        """
        self.intents_config = intents_config
        self.language = language

        # Charger le gestionnaire de prompts centralisé
        if PROMPTS_AVAILABLE:
            try:
                if prompts_path:
                    self.prompts_manager = get_prompts_manager(prompts_path)
                else:
                    self.prompts_manager = get_prompts_manager()
                logger.info("PromptBuilder initialisé avec system_prompts.json")
            except Exception as e:
                logger.error(f"Erreur chargement prompts: {e}")
                self.prompts_manager = None
        else:
            self.prompts_manager = None
            logger.warning("PromptBuilder en mode fallback (prompts hardcodés)")

    def build_specialized_prompt(
        self, intent_result: IntentResult, language: Optional[str] = None
    ) -> Optional[str]:
        """
        Génère un prompt spécialisé selon le type d'intention

        Args:
            intent_result: Résultat de la classification d'intention
            language: Langue (override du défaut)

        Returns:
            Prompt spécialisé ou None
        """
        intent_type = intent_result.intent_type
        entities = intent_result.detected_entities
        lang = language or self.language

        # Mapping IntentType → clé prompt
        intent_to_prompt_key = {
            IntentType.METRIC_QUERY: "metric_query",
            IntentType.ENVIRONMENT_SETTING: "environment_setting",
            IntentType.DIAGNOSIS_TRIAGE: "diagnosis_triage",
            IntentType.ECONOMICS_COST: "economics_cost",
            IntentType.PROTOCOL_QUERY: "protocol_query",
            IntentType.GENERAL_POULTRY: "general_poultry",
        }

        prompt_key = intent_to_prompt_key.get(intent_type)

        if not prompt_key:
            logger.warning(f"Type d'intention non supporté: {intent_type}")
            return None

        # Récupérer le prompt depuis le gestionnaire centralisé
        if self.prompts_manager:
            base_prompt = self.prompts_manager.get_specialized_prompt(prompt_key, lang)

            if not base_prompt:
                logger.warning(
                    f"Prompt non trouvé pour {prompt_key}/{lang}, "
                    f"utilisation fallback"
                )
                base_prompt = self._get_fallback_prompt(prompt_key)
        else:
            # Fallback si gestionnaire non disponible
            base_prompt = self._get_fallback_prompt(prompt_key)

        if not base_prompt:
            logger.error(f"Impossible de générer prompt pour {prompt_key}")
            return None

        # Enrichissement contextuel avec entités et métriques
        if entities:
            entity_context = self._build_entity_context(entities)
            expansion_context = self._build_expansion_context(
                intent_result.expansion_quality
            )
            cache_context = self._build_cache_context(intent_result)

            # Ajouter contexte si présent
            enrichments = []
            if entity_context:
                enrichments.append(f"Contexte détecté: {entity_context}")
            if expansion_context:
                enrichments.append(f"Expansion appliquée: {expansion_context}")
            if cache_context:
                enrichments.append(f"Cache: {cache_context}")

            if enrichments:
                base_prompt += "\n\n" + "\n".join(enrichments)

        # Ajouter contexte métrique spécifique si nécessaire
        if prompt_key == "metric_query" and "metrics" in entities:
            metrics_list = [
                m.strip() for m in entities["metrics"].split(",") if m.strip()
            ]
            base_prompt += f"\n\nMÉTRIQUES À TRAITER: {', '.join(metrics_list)}"

        # Ajouter contexte haute confiance
        adaptive_factors = intent_result.vocabulary_coverage.get("adaptive_factors", {})
        if adaptive_factors.get("high_confidence", False):
            base_prompt += (
                "\n\nCONTEXTE: Question technique précise - "
                "données détaillées attendues"
            )

        return base_prompt

    def _build_entity_context(self, entities: Dict[str, str]) -> str:
        """
        Construit un contexte enrichi à partir des entités détectées

        Args:
            entities: Dictionnaire des entités extraites

        Returns:
            String de contexte formaté
        """
        context_parts = []

        if "line" in entities:
            context_parts.append(f"Lignée: {entities['line']}")
        if "line_normalized" in entities:
            context_parts.append(f"(norm: {entities['line_normalized']})")
        if "age_days" in entities:
            context_parts.append(f"Âge: {entities['age_days']} jours")
        if "site_type" in entities:
            context_parts.append(f"Type d'élevage: {entities['site_type']}")
        if "bird_type" in entities:
            context_parts.append(f"Type d'oiseau: {entities['bird_type']}")
        if "weight_value" in entities:
            unit = entities.get("weight_unit", "g")
            context_parts.append(f"Poids: {entities['weight_value']}{unit}")
        if "temperature_value" in entities:
            context_parts.append(f"Température: {entities['temperature_value']}°C")
        if "flock_size" in entities:
            context_parts.append(f"Taille troupeau: {entities['flock_size']}")
        if "environment" in entities:
            context_parts.append(f"Environnement: {entities['environment']}")

        return " | ".join(context_parts)

    def _build_expansion_context(self, expansion_quality: Dict[str, Any]) -> str:
        """
        Construit le contexte d'expansion de requête

        Args:
            expansion_quality: Métadonnées sur l'expansion

        Returns:
            String décrivant l'expansion appliquée
        """
        if expansion_quality.get("terms_added", 0) > 0:
            ratio = expansion_quality.get("expansion_ratio", 1.0)
            normalization = (
                " (norm)"
                if expansion_quality.get("normalization_applied", False)
                else ""
            )
            return (
                f"{expansion_quality['terms_added']} termes ajoutés "
                f"(ratio: {ratio:.1f}){normalization}"
            )
        return ""

    def _build_cache_context(self, intent_result: IntentResult) -> str:
        """
        Construit le contexte cache pour debug/monitoring

        Args:
            intent_result: Résultat de l'analyse d'intention

        Returns:
            String avec infos cache
        """
        context_parts = []

        if intent_result.cache_key_normalized:
            context_parts.append(f"clé={intent_result.cache_key_normalized}")

        if intent_result.semantic_fallback_candidates:
            fallback_count = len(intent_result.semantic_fallback_candidates)
            context_parts.append(f"fallback={fallback_count}")

        explain_score = intent_result.metadata.get("explain_score_used")
        if explain_score is not None:
            context_parts.append(f"evidence={explain_score:.2f}")

        return " | ".join(context_parts)

    def _get_fallback_prompt(self, prompt_key: str) -> Optional[str]:
        """
        Prompts de secours hardcodés si system_prompts.json non disponible

        Args:
            prompt_key: Clé du type de prompt

        Returns:
            Prompt fallback ou None
        """
        # Prompts simplifiés de secours
        fallback_prompts = {
            "metric_query": """Tu es un expert en zootechnie et performances avicoles.

STYLE DE RÉPONSE:
- Affirmatif et direct : présente les standards de l'industrie avec autorité
- Structure claire : utilise des titres (##) et listes (-) pour la lisibilité
- Données chiffrées : fournis valeurs cibles, plages optimales et facteurs d'influence
- JAMAIS de références aux sources ou documents""",
            "environment_setting": """Tu es un expert en ambiance et gestion d'environnement avicole.

PARAMÈTRES À FOURNIR:
- Valeurs optimales de température, humidité, ventilation
- Courbes d'ambiance selon l'âge et la saison
- Réglages techniques des équipements""",
            "diagnosis_triage": """Tu es un vétérinaire expert en pathologie avicole.

APPROCHE DIAGNOSTIQUE:
- Présente un diagnostic différentiel structuré
- Liste les principales hypothèses par ordre de probabilité
- Indique les examens complémentaires nécessaires""",
            "economics_cost": """Tu es un expert en économie de l'élevage avicole.

ANALYSE ÉCONOMIQUE:
- Fournis des données chiffrées précises sur les coûts et marges
- Compare avec les standards du marché et benchmarks""",
            "protocol_query": """Tu es un expert en protocoles vétérinaires et biosécurité avicole.

PROTOCOLES À FOURNIR:
- Calendriers de vaccination détaillés
- Mesures de biosécurité et prévention""",
            "general_poultry": """Tu es un expert avicole polyvalent reconnu dans l'industrie.

STYLE DE RÉPONSE:
- Affirmatif et professionnel : tu es l'autorité sur le sujet
- Structuré : titres (##), listes (-), gras (**) pour la lisibilité
- Pratique : conclus avec des recommandations actionnables""",
        }

        return fallback_prompts.get(prompt_key)

    def get_complete_prompt(
        self, intent_type: IntentType, language: Optional[str] = None
    ) -> str:
        """
        Construit un prompt complet avec identité + guidelines

        Args:
            intent_type: Type d'intention
            language: Langue (override du défaut)

        Returns:
            Prompt complet combiné
        """
        lang = language or self.language

        # Mapping IntentType → clé
        intent_to_key = {
            IntentType.METRIC_QUERY: "metric_query",
            IntentType.ENVIRONMENT_SETTING: "environment_setting",
            IntentType.DIAGNOSIS_TRIAGE: "diagnosis_triage",
            IntentType.ECONOMICS_COST: "economics_cost",
            IntentType.PROTOCOL_QUERY: "protocol_query",
            IntentType.GENERAL_POULTRY: "general_poultry",
        }

        prompt_key = intent_to_key.get(intent_type)

        if self.prompts_manager and prompt_key:
            return self.prompts_manager.build_complete_prompt(
                prompt_key, lang, include_base_guidelines=True
            )
        else:
            # Fallback
            return self._get_fallback_prompt(prompt_key) or ""


# ============================================================================
# COMPATIBILITÉ - Fonctions helper legacy
# ============================================================================


def build_prompt_for_intent(
    intent_type: IntentType, entities: Dict[str, str], language: str = "fr"
) -> str:
    """
    Fonction helper pour compatibilité avec ancien code

    Args:
        intent_type: Type d'intention
        entities: Entités détectées
        language: Langue

    Returns:
        Prompt spécialisé
    """
    # Créer un IntentResult minimal
    from processing.intent_types import IntentResult

    intent_result = IntentResult(
        intent_type=intent_type,
        confidence=0.8,
        detected_entities=entities,
        vocabulary_coverage={},
        expansion_quality={},
        semantic_fallback_candidates=[],
        cache_key_normalized=None,
        metadata={},
    )

    builder = PromptBuilder({}, language=language)
    return builder.build_specialized_prompt(intent_result, language) or ""
