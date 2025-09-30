# -*- coding: utf-8 -*-
"""
generators.py - Générateurs de réponses enrichis avec entités et cache externe
Version 2.0 - Utilise system_prompts.json centralisé
"""

import logging
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from core.data_models import Document
from config.config import ENTITY_CONTEXTS, MAX_CONVERSATION_CONTEXT
from utils.utilities import METRICS

# Import du gestionnaire de prompts centralisé
try:
    from llm.config.system_prompts import get_prompts_manager

    PROMPTS_AVAILABLE = True
except ImportError:
    logging.warning("SystemPromptsManager non disponible, utilisation prompts fallback")
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


class EnhancedResponseGenerator:
    """
    Générateur avec enrichissement d'entités et cache externe + ton affirmatif expert
    Version 2.0: Charge les prompts depuis system_prompts.json
    """

    def __init__(
        self,
        client,
        cache_manager=None,
        language: str = "fr",
        prompts_path: Optional[str] = None,
    ):
        """
        Initialise le générateur de réponses

        Args:
            client: Client OpenAI
            cache_manager: Gestionnaire de cache (optionnel)
            language: Langue par défaut
            prompts_path: Chemin custom vers system_prompts.json
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

        # Import des contextes depuis config + mapping métier détaillé hardcodé
        self.entity_contexts = (
            ENTITY_CONTEXTS
            if ENTITY_CONTEXTS
            else {
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
        )

        # Métriques clés par contexte
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

            # Message d'erreur depuis system_prompts.json
            if self.prompts_manager:
                error_msg = self.prompts_manager.get_error_message(
                    "insufficient_data", lang
                )
                if error_msg:
                    return error_msg

            # Fallback
            return "Je n'ai pas trouvé d'informations pertinentes dans ma base de connaissances pour répondre à votre question. Pouvez-vous reformuler ou être plus spécifique ?"

        try:
            # Vérifier le cache externe
            cache_hit_details = {"semantic_reasoning": "", "cache_type": ""}
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

            # Post-traitement pour intégrer les éléments manqués
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

            # Contexte des entités
            entity_contexts = []

            if "line" in entities:
                line = entities["line"].lower()
                if line in self.entity_contexts["line"]:
                    entity_contexts.append(
                        f"Lignée {entities['line']}: {self.entity_contexts['line'][line]}"
                    )

            if "species" in entities:
                species = entities["species"].lower()
                if species in self.entity_contexts["species"]:
                    entity_contexts.append(
                        f"Type {entities['species']}: {self.entity_contexts['species'][species]}"
                    )

            if "phase" in entities:
                phase = entities["phase"].lower()
                if phase in self.entity_contexts["phase"]:
                    entity_contexts.append(
                        f"Phase {entities['phase']}: {self.entity_contexts['phase'][phase]}"
                    )

            # Focus métrique
            metric_focus = ""
            detected_metrics = []
            expanded_query = getattr(intent_result, "expanded_query", "")

            for metric, keywords in self.performance_metrics.items():
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

            # Indicateurs de performance attendus
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
        """
        Construit un prompt enrichi avec ton affirmatif expert
        Version 2.0: Utilise system_prompts.json si disponible
        """

        # Contexte documentaire
        context_text = "\n\n".join(
            [
                f"Document {i+1} ({doc.metadata.get('geneticLine', 'N/A')} - {doc.metadata.get('species', 'N/A')}):\n{doc.content[:1000]}"
                for i, doc in enumerate(context_docs[:5])
            ]
        )

        # Construction du prompt système depuis system_prompts.json
        if self.prompts_manager:
            # Récupérer le prompt de base expert
            expert_identity = self.prompts_manager.get_base_prompt(
                "expert_identity", language
            )

            response_guidelines = self.prompts_manager.get_base_prompt(
                "response_guidelines", language
            )

            # Construire le prompt système complet
            system_prompt_parts = []

            if expert_identity:
                system_prompt_parts.append(expert_identity)

            # Ajouter contexte métier détecté
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

            # Métriques prioritaires
            metrics_section = f"""
MÉTRIQUES PRIORITAIRES:
{', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'Paramètres généraux de production'}
"""
            system_prompt_parts.append(metrics_section)

            # Instructions critiques
            critical_instructions = f"""
INSTRUCTIONS CRITIQUES:
- NE commence JAMAIS par un titre (ex: "## Maladie", "**Maladie**") - commence directement par la phrase d'introduction
- Examine les tableaux de données pour extraire les informations précises
- Présente 2-3 éléments principaux, pas plus
- Utilise un ton affirmatif mais sobre, sans formatage excessif
- NE conclus PAS avec des recommandations pratiques sauf si explicitement demandé

LANGUE: Réponds STRICTEMENT en {language}
"""
            system_prompt_parts.append(critical_instructions)

            system_prompt = "\n\n".join(system_prompt_parts)

        else:
            # Fallback si prompts manager non disponible
            system_prompt = self._get_fallback_system_prompt(enrichment, language)

        # Prompt utilisateur enrichi
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

    def _get_fallback_system_prompt(
        self, enrichment: ContextEnrichment, language: str
    ) -> str:
        """
        Prompt système de secours si system_prompts.json non disponible
        """
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

LANGUE: Réponds STRICTEMENT en {language}"""

    def _post_process_response(
        self, response: str, enrichment: ContextEnrichment, context_docs: List[Dict]
    ) -> str:
        """Post-traitement pour enrichir la réponse - Version minimaliste"""
        try:
            # Vérification simple sans ajout de notes de confiance
            # Le but est de garder une réponse claire et professionnelle
            return response.strip()

        except Exception as e:
            logger.warning(f"Erreur post-traitement: {e}")
            return response


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_enhanced_generator(
    openai_client,
    cache_manager=None,
    language: str = "fr",
    prompts_path: Optional[str] = None,
):
    """
    Factory pour créer le générateur enrichi

    Args:
        openai_client: Client OpenAI
        cache_manager: Gestionnaire de cache (optionnel)
        language: Langue par défaut
        prompts_path: Chemin custom vers system_prompts.json

    Returns:
        Instance EnhancedResponseGenerator
    """
    return EnhancedResponseGenerator(
        openai_client, cache_manager, language, prompts_path
    )


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    print("=" * 70)
    print("🧪 TESTS ENHANCED RESPONSE GENERATOR")
    print("=" * 70)

    # Test 1: Initialisation
    print("\n📥 Test 1: Initialisation")
    try:
        # Mock client
        class MockClient:
            pass

        generator = EnhancedResponseGenerator(MockClient(), language="fr")
        print("  ✅ Générateur créé")
        print(f"  📊 Prompts manager: {generator.prompts_manager is not None}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")

    # Test 2: Enrichissement
    print("\n🎯 Test 2: Construction enrichissement")

    class MockIntentResult:
        detected_entities = {"line": "Ross 308", "species": "broiler", "age_days": 35}
        expanded_query = "poids vif conversion alimentaire"

    enrichment = generator._build_entity_enrichment(MockIntentResult())
    print("  ✅ Enrichissement créé")
    print(f"  📊 Entity context: {enrichment.entity_context[:50]}...")
    print(f"  📊 Métriques: {enrichment.performance_indicators}")

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
