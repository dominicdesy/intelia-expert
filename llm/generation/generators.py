# -*- coding: utf-8 -*-
"""
generators.py - Générateurs de réponses enrichis avec entités et cache externe
Version 3.1 - Instructions de langue renforcées + system_prompts.json centralisés
"""

import logging
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from core.data_models import Document
from config.config import ENTITY_CONTEXTS, MAX_CONVERSATION_CONTEXT
from utils.utilities import METRICS

# Import du gestionnaire de prompts centralisé
try:
    from config.system_prompts import get_prompts_manager

    PROMPTS_AVAILABLE = True
except ImportError as e:
    logging.warning(
        f"SystemPromptsManager non disponible: {e}, utilisation prompts fallback"
    )
    PROMPTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ContextEnrichment:
    """Enrichissement du contexte basé sur les entités détectées"""

    entity_context: str
    metric_focus: str
    temporal_context: str
    species_focus: str
    performance_indicators: List[str]
    confidence_boosters: List[str]


class EntityDescriptionsManager:
    """
    Gestionnaire centralisé des descriptions d'entités pour enrichissement contextuel
    """

    def __init__(self, descriptions_path: Optional[str] = None):
        """
        Charge les descriptions d'entités depuis entity_descriptions.json

        Args:
            descriptions_path: Chemin custom vers entity_descriptions.json
        """
        self.descriptions = {}
        self.performance_metrics = {}

        # Déterminer le chemin du fichier
        if descriptions_path:
            config_path = Path(descriptions_path)
        else:
            # Chemin par défaut: llm/config/entity_descriptions.json
            config_path = (
                Path(__file__).parent.parent / "config" / "entity_descriptions.json"
            )

        # Charger les descriptions
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.descriptions = data.get("entity_contexts", {})
                    self.performance_metrics = data.get("performance_metrics", {})
                logger.info(f"✅ Descriptions d'entités chargées depuis {config_path}")
            else:
                logger.warning(
                    f"⚠️ Fichier {config_path} introuvable, utilisation fallback"
                )
                self._load_fallback_descriptions()
        except Exception as e:
            logger.error(f"❌ Erreur chargement entity_descriptions.json: {e}")
            self._load_fallback_descriptions()

    def _load_fallback_descriptions(self):
        """Descriptions de secours si le fichier JSON n'est pas disponible"""
        self.descriptions = {
            "line": {
                "ross": "lignée à croissance rapide, optimisée pour le rendement carcasse",
                "cobb": "lignée équilibrée performance/robustesse, bonne conversion alimentaire",
                "hubbard": "lignée rustique, adaptée à l'élevage extensif et labels qualité",
                "isa": "lignée ponte, optimisée pour la production d'œufs",
                "lohmann": "lignée ponte, excellence en persistance de ponte",
            },
            "species": {
                "broiler": "poulet de chair, objectifs: poids vif, FCR, rendement carcasse",
                "layer": "poule pondeuse, objectifs: intensité de ponte, qualité œuf, persistance",
                "breeder": "reproducteur, objectifs: fertilité, éclosabilité, viabilité descendance",
            },
            "phase": {
                "starter": "phase démarrage (0-10j), croissance critique, thermorégulation",
                "grower": "phase croissance (11-24j), développement squelettique et musculaire",
                "finisher": "phase finition (25j+), optimisation du poids final et FCR",
                "laying": "phase ponte, maintien de la production et qualité œuf",
                "breeding": "phase reproduction, optimisation fertilité et éclosabilité",
            },
        }

        self.performance_metrics = {
            "weight": [
                "poids vif",
                "gain de poids",
                "homogénéité",
                "courbe de croissance",
            ],
            "fcr": [
                "indice de consommation",
                "efficacité alimentaire",
                "coût alimentaire",
            ],
            "mortality": [
                "mortalité",
                "viabilité",
                "causes de mortalité",
                "prévention",
            ],
            "production": [
                "intensité de ponte",
                "pic de ponte",
                "persistance",
                "qualité œuf",
            ],
            "feed": ["consommation", "appétence", "digestibilité", "conversion"],
        }

    def get_entity_description(
        self, entity_type: str, entity_value: str
    ) -> Optional[str]:
        """
        Récupère la description d'une entité

        Args:
            entity_type: Type d'entité (line, species, phase, etc.)
            entity_value: Valeur de l'entité

        Returns:
            Description ou None si non trouvée
        """
        entity_value_lower = entity_value.lower()
        return self.descriptions.get(entity_type, {}).get(entity_value_lower)

    def get_metric_keywords(self, metric: str) -> List[str]:
        """
        Récupère les mots-clés associés à une métrique

        Args:
            metric: Nom de la métrique

        Returns:
            Liste de mots-clés
        """
        return self.performance_metrics.get(metric, [])

    def get_all_metrics(self) -> Dict[str, List[str]]:
        """Retourne toutes les métriques de performance"""
        return self.performance_metrics.copy()


class EnhancedResponseGenerator:
    """
    Générateur avec enrichissement d'entités et cache externe + ton affirmatif expert
    Version 3.1: Instructions de langue renforcées
    """

    def __init__(
        self,
        client,
        cache_manager=None,
        language: str = "fr",
        prompts_path: Optional[str] = None,
        descriptions_path: Optional[str] = None,
    ):
        """
        Initialise le générateur de réponses

        Args:
            client: Client OpenAI
            cache_manager: Gestionnaire de cache (optionnel)
            language: Langue par défaut
            prompts_path: Chemin custom vers system_prompts.json
            descriptions_path: Chemin custom vers entity_descriptions.json
        """
        self.client = client
        self.cache_manager = cache_manager
        self.language = language

        # Charger le gestionnaire de prompts centralisé
        if PROMPTS_AVAILABLE:
            try:
                if prompts_path:
                    self.prompts_manager = get_prompts_manager(prompts_path)
                else:
                    self.prompts_manager = get_prompts_manager()
                logger.info(
                    "✅ EnhancedResponseGenerator initialisé avec system_prompts.json"
                )
            except Exception as e:
                logger.error(f"❌ Erreur chargement prompts: {e}")
                self.prompts_manager = None
        else:
            self.prompts_manager = None
            logger.warning("⚠️ EnhancedResponseGenerator en mode fallback")

        # Charger le gestionnaire de descriptions d'entités
        self.entity_descriptions = EntityDescriptionsManager(descriptions_path)

        # Garder compatibilité avec ENTITY_CONTEXTS de config
        if ENTITY_CONTEXTS:
            for entity_type, contexts in ENTITY_CONTEXTS.items():
                if entity_type not in self.entity_descriptions.descriptions:
                    self.entity_descriptions.descriptions[entity_type] = {}
                self.entity_descriptions.descriptions[entity_type].update(contexts)

    async def generate_response(
        self,
        query: str,
        context_docs: List[Document],
        conversation_context: str = "",
        language: Optional[str] = None,
        intent_result=None,
    ) -> str:
        """Génère une réponse enrichie avec cache externe + ton affirmatif expert"""

        lang = language or self.language

        # Protection contre les documents vides
        if not context_docs or len(context_docs) == 0:
            logger.warning("⚠️ Générateur appelé avec 0 documents - protection activée")

            if self.prompts_manager:
                error_msg = self.prompts_manager.get_error_message(
                    "insufficient_data", lang
                )
                if error_msg:
                    return error_msg

            return "Je n'ai pas trouvé d'informations pertinentes dans ma base de connaissances pour répondre à votre question. Pouvez-vous reformuler ou être plus spécifique ?"

        try:
            # Vérifier le cache externe
            if self.cache_manager and self.cache_manager.enabled:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                cached_response = await self.cache_manager.get_response(
                    query, context_hash, lang
                )
                if cached_response:
                    METRICS.cache_hit("response")
                    if hasattr(self.cache_manager, "get_last_cache_details"):
                        try:
                            cache_hit_details = (
                                await self.cache_manager.get_last_cache_details()
                            )
                            if cache_hit_details.get("semantic_fallback_used"):
                                METRICS.semantic_fallback_used()
                            else:
                                METRICS.semantic_cache_hit("exact")
                        except Exception:
                            pass
                    return cached_response
                METRICS.cache_miss("response")

            # Construire enrichissement avancé
            enrichment = (
                self._build_entity_enrichment(intent_result)
                if intent_result
                else ContextEnrichment("", "", "", "", [], [])
            )

            # Générer le prompt enrichi
            system_prompt, user_prompt = self._build_enhanced_prompt(
                query, context_docs, enrichment, conversation_context, lang
            )

            # Génération
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=900,
            )

            generated_response = response.choices[0].message.content.strip()

            # Post-traitement
            enhanced_response = self._post_process_response(
                generated_response,
                enrichment,
                [self._doc_to_dict(doc) for doc in context_docs],
            )

            # Mettre en cache
            if self.cache_manager and self.cache_manager.enabled:
                await self.cache_manager.set_response(
                    query, context_hash, enhanced_response, lang
                )

            return enhanced_response

        except Exception as e:
            logger.error(f"Erreur génération réponse enrichie: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."

    def _doc_to_dict(self, doc: Document) -> dict:
        """Convertit Document en dict pour cache"""
        result = {
            "content": doc.content,
            "title": doc.metadata.get("title", ""),
            "source": doc.metadata.get("source", ""),
            "score": doc.score,
            "genetic_line": doc.metadata.get(
                "geneticLine", doc.metadata.get("genetic_line", "")
            ),
            "species": doc.metadata.get("species", ""),
        }
        if doc.explain_score:
            result["explain_score"] = doc.explain_score
        return result

    def _build_entity_enrichment(self, intent_result) -> ContextEnrichment:
        """Construit l'enrichissement basé sur les entités détectées"""
        try:
            entities = getattr(intent_result, "detected_entities", {})

            # Contexte des entités via EntityDescriptionsManager
            entity_contexts = []

            if "line" in entities:
                description = self.entity_descriptions.get_entity_description(
                    "line", entities["line"]
                )
                if description:
                    entity_contexts.append(f"Lignée {entities['line']}: {description}")

            if "species" in entities:
                description = self.entity_descriptions.get_entity_description(
                    "species", entities["species"]
                )
                if description:
                    entity_contexts.append(f"Type {entities['species']}: {description}")

            if "phase" in entities:
                description = self.entity_descriptions.get_entity_description(
                    "phase", entities["phase"]
                )
                if description:
                    entity_contexts.append(f"Phase {entities['phase']}: {description}")

            # Focus métrique
            metric_focus = ""
            detected_metrics = []
            expanded_query = getattr(intent_result, "expanded_query", "")

            all_metrics = self.entity_descriptions.get_all_metrics()
            for metric, keywords in all_metrics.items():
                metric_in_entities = metric in entities
                metric_in_query = (
                    any(kw in expanded_query.lower() for kw in keywords)
                    if expanded_query
                    else False
                )

                if metric_in_entities or metric_in_query:
                    detected_metrics.extend(keywords)

            if detected_metrics:
                metric_focus = f"Focus métriques: {', '.join(detected_metrics[:3])}"

            # Contexte temporel
            temporal_context = ""
            if "age_days" in entities:
                age = entities["age_days"]
                if isinstance(age, (int, float)):
                    if age <= 7:
                        temporal_context = "Période critique première semaine - Focus thermorégulation et démarrage"
                    elif age <= 21:
                        temporal_context = "Phase de croissance rapide - Développement osseux et musculaire"
                    elif age <= 35:
                        temporal_context = (
                            "Phase d'optimisation - Maximisation du gain de poids"
                        )
                    else:
                        temporal_context = (
                            "Phase de finition - Optimisation FCR et qualité carcasse"
                        )

            # Focus espèce
            species_focus = ""
            if "species" in entities:
                species = entities["species"].lower()
                if "broiler" in species or "chair" in species:
                    species_focus = (
                        "Objectifs chair: poids vif, FCR, rendement, qualité carcasse"
                    )
                elif "layer" in species or "ponte" in species:
                    species_focus = "Objectifs ponte: intensité, persistance, qualité œuf, viabilité"

            # Indicateurs de performance
            performance_indicators = []
            if "weight" in entities or (
                "poids" in expanded_query.lower() if expanded_query else False
            ):
                performance_indicators.extend(
                    ["poids vif", "gain quotidien", "homogénéité du lot"]
                )
            if "fcr" in entities or any(
                term in expanded_query.lower() if expanded_query else False
                for term in ["conversion", "indice"]
            ):
                performance_indicators.extend(
                    ["FCR", "consommation", "efficacité alimentaire"]
                )

            # Éléments de confiance
            confidence_boosters = []
            if entity_contexts:
                confidence_boosters.append("Contexte lignée/espèce identifié")
            if temporal_context:
                confidence_boosters.append("Phase d'élevage précisée")
            if metric_focus:
                confidence_boosters.append("Métriques cibles identifiées")

            return ContextEnrichment(
                entity_context="; ".join(entity_contexts),
                metric_focus=metric_focus,
                temporal_context=temporal_context,
                species_focus=species_focus,
                performance_indicators=performance_indicators,
                confidence_boosters=confidence_boosters,
            )

        except Exception as e:
            logger.warning(f"Erreur construction enrichissement: {e}")
            return ContextEnrichment("", "", "", "", [], [])

    def _build_enhanced_prompt(
        self,
        query: str,
        context_docs: List[Document],
        enrichment: ContextEnrichment,
        conversation_context: str,
        language: str,
    ) -> Tuple[str, str]:
        """Construit un prompt enrichi avec instructions de langue renforcées"""

        # Contexte documentaire
        context_text = "\n\n".join(
            [
                f"Document {i+1} ({doc.metadata.get('geneticLine', 'N/A')} - {doc.metadata.get('species', 'N/A')}):\n{doc.content[:1000]}"
                for i, doc in enumerate(context_docs[:5])
            ]
        )

        # Construction du prompt système avec instructions de langue RENFORCÉES
        if self.prompts_manager:
            expert_identity = self.prompts_manager.get_base_prompt(
                "expert_identity", language
            )
            response_guidelines = self.prompts_manager.get_base_prompt(
                "response_guidelines", language
            )

            system_prompt_parts = []

            if expert_identity:
                system_prompt_parts.append(expert_identity)

            context_section = f"""
CONTEXTE MÉTIER DÉTECTÉ:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}
"""
            system_prompt_parts.append(context_section)

            if response_guidelines:
                system_prompt_parts.append(response_guidelines)

            metrics_section = f"""
MÉTRIQUES PRIORITAIRES:
{', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'Paramètres généraux de production'}
"""
            system_prompt_parts.append(metrics_section)

            # ✅ INSTRUCTIONS DE LANGUE RENFORCÉES
            critical_instructions = self._get_critical_language_instructions(language)
            system_prompt_parts.append(critical_instructions)

            system_prompt = "\n\n".join(system_prompt_parts)

        else:
            system_prompt = self._get_fallback_system_prompt(enrichment, language)

        # Prompt utilisateur
        limited_context = (
            conversation_context[:MAX_CONVERSATION_CONTEXT]
            if conversation_context
            else ""
        )

        user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{limited_context}

INFORMATIONS TECHNIQUES DISPONIBLES:
{context_text}

ENRICHISSEMENT DÉTECTÉ:
- Entités métier: {enrichment.entity_context or 'Non spécifiées'}
- Focus performance: {', '.join(enrichment.performance_indicators) if enrichment.performance_indicators else 'Général'}
- Contexte temporel: {enrichment.temporal_context or 'Non spécifié'}

QUESTION:
{query}

RÉPONSE EXPERTE (affirmative, structurée, sans mention de sources):"""

        return system_prompt, user_prompt

    def _get_critical_language_instructions(self, language: str) -> str:
        """
        ✅ NOUVEAU: Instructions de langue ULTRA-RENFORCÉES + Comportement conversationnel
        Garantit que le LLM répond dans la langue de la question avec ton approprié
        """
        # Mapping des noms de langue
        language_names = {
            "en": "ENGLISH",
            "fr": "FRENCH / FRANÇAIS",
            "es": "SPANISH / ESPAÑOL",
            "de": "GERMAN / DEUTSCH",
            "it": "ITALIAN / ITALIANO",
            "pt": "PORTUGUESE / PORTUGUÊS",
            "nl": "DUTCH / NEDERLANDS",
            "pl": "POLISH / POLSKI",
            "zh": "CHINESE / 中文",
            "hi": "HINDI / हिन्दी",
            "th": "THAI / ไทย",
            "id": "INDONESIAN / BAHASA INDONESIA",
        }

        language_name = language_names.get(language, language.upper())

        return f"""
INSTRUCTIONS CRITIQUES - STRUCTURE ET FORMAT:
- NE commence JAMAIS par un titre (ex: "## Maladie", "**Maladie**") - commence directement par la phrase d'introduction
- Examine les tableaux de données pour extraire les informations précises
- Présente 2-3 éléments principaux, pas plus
- Utilise un ton affirmatif mais sobre, sans formatage excessif
- NE conclus PAS avec des recommandations pratiques sauf si explicitement demandé

COMPORTEMENT CONVERSATIONNEL:
- Pour questions techniques: réponse structurée et détaillée avec données chiffrées
- Pour questions générales ou clarifications: ton professionnel mais accessible, réponses plus courtes acceptables
- Évite de poser trop de questions - réponds d'abord à la requête, même si ambiguë, puis demande clarification si nécessaire
- Si question vague: fournis la meilleure réponse possible puis propose de préciser
- N'utilise PAS d'emojis sauf si l'utilisateur en utilise dans sa question
- Si l'utilisateur semble insatisfait: maintiens le professionnalisme et rappelle qu'il peut utiliser le feedback pour améliorer les réponses

{"="*80}
⚠️ CRITICAL LANGUAGE REQUIREMENT - IMPÉRATIF ABSOLU DE LANGUE ⚠️
{"="*80}

DETECTED QUESTION LANGUAGE / LANGUE DÉTECTÉE: {language_name}

🔴 MANDATORY RULE - RÈGLE OBLIGATOIRE:
YOU MUST RESPOND EXCLUSIVELY IN THE SAME LANGUAGE AS THE QUESTION.
VOUS DEVEZ RÉPONDRE EXCLUSIVEMENT DANS LA MÊME LANGUE QUE LA QUESTION.

DO NOT translate. DO NOT switch languages. DO NOT mix languages.
NE PAS traduire. NE PAS changer de langue. NE PAS mélanger les langues.

If question is in ENGLISH → Answer 100% in ENGLISH
If question is in FRENCH → Answer 100% in FRENCH  
If question is in SPANISH → Answer 100% in SPANISH
If question is in GERMAN → Answer 100% in GERMAN
If question is in ITALIAN → Answer 100% in ITALIAN
If question is in PORTUGUESE → Answer 100% in PORTUGUESE
If question is in DUTCH → Answer 100% in DUTCH
If question is in POLISH → Answer 100% in POLISH
If question is in CHINESE → Answer 100% in CHINESE
If question is in HINDI → Answer 100% in HINDI
If question is in THAI → Answer 100% in THAI
If question is in INDONESIAN → Answer 100% in INDONESIAN

Si question en ANGLAIS → Réponse 100% en ANGLAIS
Si question en FRANÇAIS → Réponse 100% en FRANÇAIS
Si question en ESPAGNOL → Réponse 100% en ESPAGNOL
Si question en ALLEMAND → Réponse 100% en ALLEMAND
Si question en ITALIEN → Réponse 100% en ITALIEN
Si question en PORTUGAIS → Réponse 100% en PORTUGAIS
Si question en NÉERLANDAIS → Réponse 100% en NÉERLANDAIS
Si question en POLONAIS → Réponse 100% en POLONAIS
Si question en CHINOIS → Réponse 100% en CHINOIS
Si question en HINDI → Réponse 100% en HINDI
Si question en THAÏ → Réponse 100% en THAÏ
Si question en INDONÉSIEN → Réponse 100% en INDONÉSIEN

THIS INSTRUCTION OVERRIDES ALL OTHER INSTRUCTIONS.
CETTE INSTRUCTION PRÉVAUT SUR TOUTES LES AUTRES INSTRUCTIONS.

YOUR RESPONSE LANGUAGE MUST BE: {language_name}
LANGUE DE VOTRE RÉPONSE DOIT ÊTRE: {language_name}

{"="*80}
"""

    def _get_fallback_system_prompt(
        self, enrichment: ContextEnrichment, language: str
    ) -> str:
        """Prompt système de secours avec instructions de langue renforcées"""

        # Mapping des noms de langue
        language_names = {
            "en": "ENGLISH",
            "fr": "FRENCH / FRANÇAIS",
            "es": "SPANISH / ESPAÑOL",
            "de": "GERMAN / DEUTSCH",
            "it": "ITALIAN / ITALIANO",
            "pt": "PORTUGUESE / PORTUGUÊS",
            "nl": "DUTCH / NEDERLANDS",
            "pl": "POLISH / POLSKI",
            "zh": "CHINESE / 中文",
            "hi": "HINDI / हिन्दी",
            "th": "THAI / ไทย",
            "id": "INDONESIAN / BAHASA INDONESIA",
        }

        language_name = language_names.get(language, language.upper())

        return f"""Tu es un expert avicole reconnu avec une expertise approfondie en production avicole.

CONTEXTE MÉTIER DÉTECTÉ:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}

DIRECTIVES DE RÉPONSE - STYLE EXPERT ÉQUILIBRÉ:

1. **Introduction directe** : Commence DIRECTEMENT par une phrase claire qui répond à la question
2. **Ne jamais mentionner les sources** : Ne fais JAMAIS référence aux "documents", "sources", "selon les données fournies"
3. **Structure sobre** : Utilise des titres en gras (**Titre**) uniquement pour les sous-sections
4. **Concision** : Présente 2-3 points principaux maximum
5. **Données précises** : Fournis des valeurs chiffrées quand pertinent

MÉTRIQUES PRIORITAIRES:
{', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'Paramètres généraux de production'}

{"="*80}
⚠️ CRITICAL LANGUAGE INSTRUCTION - IMPÉRATIF ABSOLU ⚠️
{"="*80}

YOU MUST RESPOND EXCLUSIVELY IN: {language_name}
VOUS DEVEZ RÉPONDRE EXCLUSIVEMENT EN: {language_name}

DO NOT translate or switch languages under ANY circumstances.
NE traduisez PAS ou ne changez PAS de langue sous AUCUNE circonstance.

THIS IS THE MOST IMPORTANT INSTRUCTION.
CECI EST L'INSTRUCTION LA PLUS IMPORTANTE.

{"="*80}
"""

    def _post_process_response(
        self, response: str, enrichment: ContextEnrichment, context_docs: List[Dict]
    ) -> str:
        """Post-traitement minimaliste"""
        return response.strip()


# Factory function
def create_enhanced_generator(
    openai_client,
    cache_manager=None,
    language: str = "fr",
    prompts_path: Optional[str] = None,
    descriptions_path: Optional[str] = None,
):
    """
    Factory pour créer le générateur enrichi

    Args:
        openai_client: Client OpenAI
        cache_manager: Gestionnaire de cache (optionnel)
        language: Langue par défaut
        prompts_path: Chemin custom vers system_prompts.json
        descriptions_path: Chemin custom vers entity_descriptions.json

    Returns:
        Instance EnhancedResponseGenerator
    """
    return EnhancedResponseGenerator(
        openai_client, cache_manager, language, prompts_path, descriptions_path
    )
