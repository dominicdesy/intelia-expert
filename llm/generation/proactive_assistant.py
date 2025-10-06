# -*- coding: utf-8 -*-
"""
proactive_assistant.py - Proactive Follow-up Questions Generator

Transforms the system from a passive data provider to an active assistant
that offers help and guidance after answering queries.

Features:
- Context-aware follow-up questions based on query intent
- Domain-specific assistance offers (production, health, nutrition, etc.)
- Multilingual support (English, French, Spanish)
- Configurable tone (helpful, professional, friendly)
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AssistanceContext(Enum):
    """Types of assistance contexts for follow-up questions"""

    PERFORMANCE_ISSUE = "performance_issue"  # Low weight, high FCR, etc.
    HEALTH_CONCERN = "health_concern"  # Mortality, disease symptoms
    OPTIMIZATION = "optimization"  # How to improve metrics
    COMPARISON = "comparison"  # Comparing breeds/strategies
    PLANNING = "planning"  # Future planning questions
    GENERAL_INFO = "general_info"  # Simple data lookup


class ProactiveAssistant:
    """
    Generates contextual follow-up questions to help users

    The assistant analyzes the query and response to offer relevant help,
    transforming a simple Q&A into an interactive conversation.

    Example:
        User: "Quel poids pour Ross 308 à 35 jours ?"
        System: "Le poids cible est 2.2-2.4 kg."
        Assistant: "Avez-vous un problème avec le poids de vos oiseaux ? Comment puis-je vous aider ?"
    """

    def __init__(self, default_language: str = "fr"):
        """
        Initialize proactive assistant

        Args:
            default_language: Default language for follow-up questions (fr/en/es)
        """
        self.default_language = default_language
        self.follow_up_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Load follow-up question templates by context and language

        Returns:
            {
                "performance_issue": {
                    "fr": ["Question en français", ...],
                    "en": ["Question in English", ...],
                    "es": ["Pregunta en español", ...]
                },
                ...
            }
        """
        return {
            AssistanceContext.PERFORMANCE_ISSUE.value: {
                "fr": [
                    "Avez-vous un problème avec le {metric} de vos oiseaux ? Comment puis-je vous aider ?",
                    "Vos oiseaux ne performent pas comme prévu ? Je peux vous aider à identifier les causes possibles.",
                    "Rencontrez-vous des difficultés avec le {metric} ? Je peux vous proposer des solutions.",
                ],
                "en": [
                    "Do you have an issue with your bird {metric}? How can I help you?",
                    "Are your birds not performing as expected? I can help identify possible causes.",
                    "Are you experiencing difficulties with {metric}? I can suggest solutions.",
                ],
                "es": [
                    "¿Tiene algún problema con el {metric} de sus aves? ¿Cómo puedo ayudarlo?",
                    "¿Sus aves no están rindiendo como esperaba? Puedo ayudarlo a identificar posibles causas.",
                    "¿Está experimentando dificultades con el {metric}? Puedo sugerir soluciones.",
                ],
            },
            AssistanceContext.HEALTH_CONCERN.value: {
                "fr": [
                    "Observez-vous des symptômes de {disease} dans votre élevage ? Je peux vous aider avec le diagnostic.",
                    "Avez-vous besoin de conseils sur la prévention ou le traitement ? Je suis là pour vous aider.",
                    "Voulez-vous en savoir plus sur les protocoles de vaccination et biosécurité ?",
                ],
                "en": [
                    "Are you observing {disease} symptoms in your flock? I can help with diagnosis.",
                    "Do you need advice on prevention or treatment? I'm here to help.",
                    "Would you like to know more about vaccination protocols and biosecurity?",
                ],
                "es": [
                    "¿Observa síntomas de {disease} en su lote? Puedo ayudarlo con el diagnóstico.",
                    "¿Necesita consejos sobre prevención o tratamiento? Estoy aquí para ayudar.",
                    "¿Le gustaría saber más sobre protocolos de vacunación y bioseguridad?",
                ],
            },
            AssistanceContext.OPTIMIZATION.value: {
                "fr": [
                    "Voulez-vous optimiser le {metric} de vos oiseaux ? Je peux vous suggérer des stratégies.",
                    "Souhaitez-vous des recommandations pour améliorer les performances de votre élevage ?",
                    "Puis-je vous aider à identifier les facteurs clés pour améliorer vos résultats ?",
                ],
                "en": [
                    "Would you like to optimize your bird {metric}? I can suggest strategies.",
                    "Would you like recommendations to improve your flock performance?",
                    "Can I help you identify key factors to improve your results?",
                ],
                "es": [
                    "¿Le gustaría optimizar el {metric} de sus aves? Puedo sugerir estrategias.",
                    "¿Quisiera recomendaciones para mejorar el rendimiento de su lote?",
                    "¿Puedo ayudarlo a identificar factores clave para mejorar sus resultados?",
                ],
            },
            AssistanceContext.COMPARISON.value: {
                "fr": [
                    "Voulez-vous comparer ces résultats avec une autre race ou période ?",
                    "Souhaitez-vous analyser les différences en détail ? Je peux vous aider.",
                    "Puis-je vous recommander la meilleure option pour votre situation ?",
                ],
                "en": [
                    "Would you like to compare these results with another breed or period?",
                    "Would you like to analyze the differences in detail? I can help.",
                    "Can I recommend the best option for your situation?",
                ],
                "es": [
                    "¿Le gustaría comparar estos resultados con otra raza o período?",
                    "¿Quisiera analizar las diferencias en detalle? Puedo ayudar.",
                    "¿Puedo recomendar la mejor opción para su situación?",
                ],
            },
            AssistanceContext.PLANNING.value: {
                "fr": [
                    "Avez-vous besoin d'aide pour planifier votre prochaine bande ?",
                    "Voulez-vous des prévisions de performance pour votre élevage ?",
                    "Puis-je vous aider à établir un calendrier de gestion optimal ?",
                ],
                "en": [
                    "Do you need help planning your next flock?",
                    "Would you like performance forecasts for your farm?",
                    "Can I help you establish an optimal management schedule?",
                ],
                "es": [
                    "¿Necesita ayuda para planificar su próximo lote?",
                    "¿Quisiera pronósticos de rendimiento para su granja?",
                    "¿Puedo ayudarlo a establecer un calendario de gestión óptimo?",
                ],
            },
            AssistanceContext.GENERAL_INFO.value: {
                "fr": [
                    "Avez-vous d'autres questions sur cette race ou ces données ?",
                    "Puis-je vous aider avec d'autres informations ?",
                    "Voulez-vous en savoir plus sur un aspect spécifique ?",
                ],
                "en": [
                    "Do you have other questions about this breed or data?",
                    "Can I help you with additional information?",
                    "Would you like to know more about a specific aspect?",
                ],
                "es": [
                    "¿Tiene otras preguntas sobre esta raza o estos datos?",
                    "¿Puedo ayudarlo con información adicional?",
                    "¿Le gustaría saber más sobre un aspecto específico?",
                ],
            },
        }

    def generate_follow_up(
        self,
        query: str,
        response: str,
        intent_result: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        Generate contextual follow-up question based on query and response

        Args:
            query: Original user query
            response: Generated response
            intent_result: Intent classification result (query_type, domain, etc.)
            entities: Extracted entities (breed, age, metric_type, etc.)
            language: Target language (fr/en/es)

        Returns:
            Follow-up question string, or empty string if no follow-up needed

        Example:
            >>> assistant = ProactiveAssistant()
            >>> follow_up = assistant.generate_follow_up(
            ...     query="Quel poids pour Ross 308 à 35 jours ?",
            ...     response="Le poids cible est 2.2-2.4 kg.",
            ...     entities={"metric_type": "body_weight"},
            ...     language="fr"
            ... )
            >>> print(follow_up)
            "Avez-vous un problème avec le poids de vos oiseaux ? Comment puis-je vous aider ?"
        """
        lang = language or self.default_language

        # Validate language
        if lang not in ["fr", "en", "es"]:
            lang = "fr"

        # Determine assistance context
        context = self._identify_context(query, response, intent_result, entities)

        # Get appropriate template
        templates = self.follow_up_templates.get(context.value, {}).get(lang, [])

        if not templates:
            logger.debug(f"No follow-up template for context={context}, lang={lang}")
            return ""

        # Select first template (could be randomized later)
        template = templates[0]

        # Fill template with context variables
        follow_up = self._fill_template(template, entities, lang)

        logger.info(f"Generated follow-up (context={context.value}): {follow_up}")
        return follow_up

    def _identify_context(
        self,
        query: str,
        response: str,
        intent_result: Optional[Dict[str, Any]],
        entities: Optional[Dict[str, Any]],
    ) -> AssistanceContext:
        """
        Identify the appropriate assistance context from query analysis

        Args:
            query: User query
            response: Generated response
            intent_result: Intent classification
            entities: Extracted entities

        Returns:
            AssistanceContext enum value
        """
        query_lower = query.lower()
        entities = entities or {}

        # Health-related queries
        if intent_result and intent_result.get("domain") == "health":
            return AssistanceContext.HEALTH_CONCERN

        health_keywords = [
            "mortalité",
            "mortality",
            "mortalidad",
            "maladie",
            "disease",
            "enfermedad",
            "symptôme",
            "symptom",
            "síntoma",
            "traitement",
            "treatment",
            "tratamiento",
        ]
        if any(keyword in query_lower for keyword in health_keywords):
            return AssistanceContext.HEALTH_CONCERN

        # Comparison queries
        if intent_result and intent_result.get("query_type") in [
            "comparative",
            "comparison",
        ]:
            return AssistanceContext.COMPARISON

        comparison_keywords = ["compare", "comparer", "comparar", "vs", "versus"]
        if any(keyword in query_lower for keyword in comparison_keywords):
            return AssistanceContext.COMPARISON

        # Optimization/improvement queries
        optimization_keywords = [
            "optimiser",
            "optimize",
            "optimizar",
            "améliorer",
            "improve",
            "mejorar",
            "augmenter",
            "increase",
            "aumentar",
            "comment",
            "how",
            "cómo",
        ]
        if any(keyword in query_lower for keyword in optimization_keywords):
            return AssistanceContext.OPTIMIZATION

        # Planning queries
        planning_keywords = [
            "planifier",
            "planning",
            "planificar",
            "prochaine",
            "next",
            "próximo",
            "prévision",
            "forecast",
            "pronóstico",
        ]
        if any(keyword in query_lower for keyword in planning_keywords):
            return AssistanceContext.PLANNING

        # Performance metrics = likely performance issue
        metric_keywords = ["poids", "weight", "peso", "fcr", "gain", "conversion"]
        if any(keyword in query_lower for keyword in metric_keywords):
            return AssistanceContext.PERFORMANCE_ISSUE

        # Default: general info
        return AssistanceContext.GENERAL_INFO

    def _fill_template(
        self, template: str, entities: Optional[Dict[str, Any]], language: str
    ) -> str:
        """
        Fill template placeholders with actual values

        Args:
            template: Template string with {placeholders}
            entities: Extracted entities
            language: Target language

        Returns:
            Filled template string
        """
        entities = entities or {}

        # Metric name mapping by language
        metric_names = {
            "fr": {
                "body_weight": "poids",
                "feed_conversion_ratio": "FCR",
                "daily_gain": "gain quotidien",
                "mortality": "mortalité",
                "livability": "viabilité",
            },
            "en": {
                "body_weight": "weight",
                "feed_conversion_ratio": "FCR",
                "daily_gain": "daily gain",
                "mortality": "mortality",
                "livability": "livability",
            },
            "es": {
                "body_weight": "peso",
                "feed_conversion_ratio": "FCR",
                "daily_gain": "ganancia diaria",
                "mortality": "mortalidad",
                "livability": "viabilidad",
            },
        }

        # Get metric name in target language
        metric_type = entities.get("metric_type", "")
        metric_name = metric_names.get(language, {}).get(metric_type, metric_type)

        # Replace placeholders
        filled = template.replace("{metric}", metric_name)
        filled = filled.replace("{disease}", entities.get("disease_name", ""))

        return filled


def get_proactive_assistant(language: str = "fr") -> ProactiveAssistant:
    """
    Get or create singleton ProactiveAssistant instance

    Args:
        language: Default language

    Returns:
        ProactiveAssistant instance
    """
    return ProactiveAssistant(default_language=language)


__all__ = ["ProactiveAssistant", "AssistanceContext", "get_proactive_assistant"]
