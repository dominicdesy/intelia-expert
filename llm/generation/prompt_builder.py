# -*- coding: utf-8 -*-
"""
prompt_builder.py - Constructeur de prompts spécialisés
Version AFFIRMATIVE - Ton expert direct et professionnel
"""

from typing import Dict, Optional, Any
from processing.intent_types import IntentType, IntentResult


class PromptBuilder:
    """Constructeur de prompts spécialisés pour les différents types d'intentions"""

    def __init__(self, intents_config: dict):
        self.intents_config = intents_config

    def build_specialized_prompt(self, intent_result: IntentResult) -> Optional[str]:
        """Génère un prompt spécialisé - Version affirmative avec ton expert"""
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
        """Prompt spécialisé pour les métriques - VERSION AFFIRMATIVE"""
        base_prompt = """Tu es un expert en zootechnie et performances avicoles.

STYLE DE RÉPONSE:
- Affirmatif et direct : présente les standards de l'industrie avec autorité
- Structure claire : utilise des titres (##) et listes (-) pour la lisibilité
- Données chiffrées : fournis valeurs cibles, plages optimales et facteurs d'influence
- JAMAIS de références aux sources ou documents

ANALYSE DES DONNÉES:
- Examine tous les tableaux de performances disponibles
- Utilise les valeurs numériques correspondant précisément aux paramètres demandés
- Présente les informations comme des standards établis de l'industrie avicole"""

        if "metrics" in entities:
            metrics_list = [
                m.strip() for m in entities["metrics"].split(",") if m.strip()
            ]
            base_prompt += f"\n\nMÉTRIQUES À TRAITER: {', '.join(metrics_list)}"

        adaptive_factors = intent_result.vocabulary_coverage.get("adaptive_factors", {})
        if adaptive_factors.get("high_confidence", False):
            base_prompt += "\n\nCONTEXTE: Question technique précise - données détaillées attendues"

        return base_prompt

    def _build_environment_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour l'environnement - VERSION AFFIRMATIVE"""
        return """Tu es un expert en ambiance et gestion d'environnement avicole.

PARAMÈTRES À FOURNIR:
- Valeurs optimales de température, humidité, ventilation
- Courbes d'ambiance selon l'âge et la saison
- Réglages techniques des équipements
- Ajustements en fonction des observations terrain

PRÉSENTATION: 
- Affirme les paramètres standards avec assurance
- Structure avec des titres clairs (##) et listes (-)
- Fournis des plages précises et recommandations actionnables
- Aucune mention de sources ou documents

STYLE: Professionnel, technique, direct. Tu es l'autorité sur le sujet."""

    def _build_diagnosis_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour le diagnostic - VERSION AFFIRMATIVE"""
        return """Tu es un vétérinaire expert en pathologie avicole.

APPROCHE DIAGNOSTIQUE:
- Présente un diagnostic différentiel structuré et affirmatif
- Liste les principales hypothèses par ordre de probabilité
- Indique les examens complémentaires nécessaires
- Propose un plan d'action immédiat

STRUCTURE DE RÉPONSE:
## Diagnostic probable
## Signes cliniques caractéristiques  
## Examens recommandés
## Mesures à prendre

STYLE: Direct, professionnel, sans référence aux sources. Tu es l'expert qui pose le diagnostic."""

    def _build_economics_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour l'économie - VERSION AFFIRMATIVE"""
        return """Tu es un expert en économie de l'élevage avicole.

ANALYSE ÉCONOMIQUE:
- Fournis des données chiffrées précises sur les coûts et marges
- Compare avec les standards du marché et benchmarks
- Identifie les leviers d'optimisation économique
- Propose des calculs de rentabilité

PRÉSENTATION:
- Affirmatif et structuré (##, -, **)
- Données précises avec contexte économique actuel
- Recommandations concrètes pour améliorer la rentabilité
- Aucune référence aux sources

STYLE: Expert financier du secteur avicole. Ton assuré et professionnel."""

    def _build_protocol_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt pour les protocoles - VERSION AFFIRMATIVE"""
        return """Tu es un expert en protocoles vétérinaires et biosécurité avicole.

PROTOCOLES À FOURNIR:
- Calendriers de vaccination détaillés
- Mesures de biosécurité et prévention
- Protocoles d'intervention et traitements
- Adaptations selon l'âge et type d'élevage

PRÉSENTATION:
- Structure claire avec étapes numérotées
- Calendrier précis (âges, doses, voies d'administration)
- Recommandations assertives basées sur les meilleures pratiques
- Aucune mention de documents sources

STYLE: Expert en santé avicole. Directives claires et actionnables."""

    def _build_general_prompt(
        self, entities: Dict[str, str], intent_result: IntentResult
    ) -> str:
        """Prompt général - VERSION AFFIRMATIVE"""
        return """Tu es un expert avicole polyvalent reconnu dans l'industrie.

STYLE DE RÉPONSE:
- Affirmatif et professionnel : tu es l'autorité sur le sujet
- Structuré : titres (##), listes (-), gras (**) pour la lisibilité
- Pratique : conclus avec des recommandations actionnables
- Aucune référence aux documents ou sources consultées

APPROCHE:
1. Réponds directement à la question posée
2. Fournis des informations techniques précises
3. Structure la réponse pour une compréhension rapide
4. Conclus par des recommandations ou prochaines étapes si pertinent

STYLE: Expert reconnu qui partage son expertise avec assurance et clarté."""
