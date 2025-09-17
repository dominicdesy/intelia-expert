# -*- coding: utf-8 -*-
"""
prompt_builder.py - Constructeur de prompts spécialisés
"""

from typing import Dict, Optional, Any
from processing.intent_types import IntentType, IntentResult


class PromptBuilder:
    """Constructeur de prompts spécialisés pour les différents types d'intentions"""

    def __init__(self, intents_config: dict):
        self.intents_config = intents_config

    def build_specialized_prompt(self, intent_result: IntentResult) -> Optional[str]:
        """Génère un prompt spécialisé - Version améliorée avec intégration cache/guardrails"""
        intent_type = intent_result.intent_type
        entities = intent_result.detected_entities

        prompts = {
            IntentType.METRIC_QUERY: self._build_metric_prompt(entities, intent_result),
            IntentType.ENVIRONMENT_SETTING: self._build_environment_prompt(
                entities, intent_result
            ),
            IntentType.DIAGNOSIS_TRIAGE: self._build_diagnosis_prompt(
                entities, intent_result
            ),
            IntentType.ECONOMICS_COST: self._build_economics_prompt(
                entities, intent_result
            ),
            IntentType.PROTOCOL_QUERY: self._build_protocol_prompt(
                entities, intent_result
            ),
            IntentType.GENERAL_POULTRY: self._build_general_prompt(
                entities, intent_result
            ),
        }

        base_prompt = prompts.get(intent_type)

        # Enrichissement contextuel avec entités et métriques
        if base_prompt and entities:
            entity_context = self._build_entity_context(entities)
            expansion_context = self._build_expansion_context(
                intent_result.expansion_quality
            )
            cache_context = self._build_cache_context(intent_result)

            if entity_context:
                base_prompt += f"\n\nContexte détecté: {entity_context}"
            if expansion_context:
                base_prompt += f"\nExpansion appliquée: {expansion_context}"
            if cache_context:
                base_prompt += f"\nCache: {cache_context}"

        return base_prompt

    def _build_cache_context(self, intent_result: IntentResult) -> str:
        """Construit le contexte cache pour le prompt"""
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

    def _build_entity_context(self, entities: Dict[str, str]) -> str:
        """Construit un contexte enrichi à partir des entités"""
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
        """Construit le contexte d'expansion pour le prompt"""
        if expansion_quality.get("terms_added", 0) > 0:
            ratio = expansion_quality.get("expansion_ratio", 1.0)
            normalization = (
                " (norm)"
                if expansion_quality.get("normalization_applied", False)
                else ""
            )
            return f"{expansion_quality['terms_added']} termes ajoutés (ratio: {ratio:.1f}){normalization}"
        return ""

    def _build_metric_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt spécialisé pour les métriques avec contexte cache"""
        base_prompt = """Tu es un expert en performances avicoles. 
Fournis des données précises avec références aux standards de l'industrie.
Inclus les valeurs cibles, les plages normales et les facteurs d'influence."""

        if "metrics" in entities:
            metrics_list = [
                m.strip() for m in entities["metrics"].split(",") if m.strip()
            ]
            base_prompt += (
                f"\nMétriques spécifiques à traiter: {', '.join(metrics_list)}"
            )

        # Ajout contexte haute confiance si détecté
        adaptive_factors = intent_result.vocabulary_coverage.get("adaptive_factors", {})
        if adaptive_factors.get("high_confidence", False):
            base_prompt += "\nContexte haute confiance détecté - données techniques précises attendues."

        return base_prompt

    def _build_environment_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour l'environnement d'élevage"""
        return """Tu es un expert en ambiance et climat d'élevage avicole.
Fournis des paramètres techniques précis, des courbes de température,
et des recommandations de réglage selon l'âge et la saison.
Inclus les plages optimales et les ajustements selon les conditions."""

    def _build_diagnosis_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour le diagnostic"""
        return """Tu es un vétérinaire spécialisé en aviculture.
Utilise une approche méthodique de diagnostic différentiel,
considère l'épidémiologie et propose des examens complémentaires.
Fournis des diagnostics différentiels et des plans d'action."""

    def _build_economics_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour l'économie"""
        return """Tu es un expert en économie de l'élevage avicole.
Fournis des analyses de coûts détaillées, des calculs de rentabilité
et des comparaisons avec les standards du marché.
Inclus les facteurs de variation et les optimisations possibles."""

    def _build_protocol_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour les protocoles"""
        return """Tu es un expert en protocoles vétérinaires et biosécurité avicole.
Fournis des protocoles détaillés, des calendriers de vaccination
et des mesures de prévention spécifiques.
Inclus les adaptations selon l'âge et le type d'élevage."""

    def _build_general_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        return """Tu es un expert avicole polyvalent.
Réponds de manière factuelle et concise, puis propose des pistes de suivi (mesures, documents de référence, contacts).
Si nécessaire, demande 1-2 précisions pour personnaliser la réponse."""
