# -*- coding: utf-8 -*-
"""
generators.py - Générateurs de réponses enrichis avec entités et cache externe
Version 3.4 - Simplifié et optimisé
- ✅ Instructions de langue compactes EN TÊTE du prompt
- ✅ Validation simple du conversation_context (pas de troncature)
- ✅ Logs réduits (2 logs essentiels seulement)
- ✅ Intégration de build_specialized_prompt depuis prompt_builder.py
- ✅ Suppression des méthodes verboses inutilisées
"""

import logging
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import json
from core.data_models import Document
from config.config import (
    ENTITY_CONTEXTS,
    SUPPORTED_LANGUAGES,
    FALLBACK_LANGUAGE,
)
from utils.utilities import METRICS

# Import du gestionnaire de messages pour disclaimers vétérinaires
try:
    from config.messages import get_message

    MESSAGES_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ config.messages disponible pour disclaimers vétérinaires")
except ImportError:
    logger = logging.getLogger(__name__)
    MESSAGES_AVAILABLE = False
    logger.warning("⚠️ config.messages non disponible pour disclaimers vétérinaires")

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
    Version 3.3: Support multilingue dynamique sans hardcoding
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

        # ✅ NOUVEAU: Charger les noms de langues dynamiquement
        self.language_display_names = self._load_language_names()

    def _load_language_names(self) -> Dict[str, str]:
        """
        Charge les noms d'affichage des langues depuis languages.json
        Fallback vers noms simples si fichier absent
        """
        try:
            from config.messages import load_messages

            messages_data = load_messages()

            # Extraire les noms de langues depuis metadata
            if (
                "metadata" in messages_data
                and "language_names" in messages_data["metadata"]
            ):
                logger.info("✅ Noms de langues chargés depuis languages.json")
                return messages_data["metadata"]["language_names"]

            logger.warning(
                "language_names absent de languages.json, utilisation fallback"
            )

        except Exception as e:
            logger.warning(
                f"Erreur chargement noms de langues: {e}, utilisation fallback"
            )

        # Fallback: génération automatique depuis SUPPORTED_LANGUAGES
        return self._generate_fallback_language_names()

    def _generate_fallback_language_names(self) -> Dict[str, str]:
        """
        Génère des noms de langues de fallback à partir des codes ISO
        Utilise SUPPORTED_LANGUAGES de config.py
        """
        # Mapping minimal pour les langues supportées
        base_names = {
            "de": "GERMAN / DEUTSCH",
            "en": "ENGLISH",
            "es": "SPANISH / ESPAÑOL",
            "fr": "FRENCH / FRANÇAIS",
            "hi": "HINDI / हिन्दी",
            "id": "INDONESIAN / BAHASA INDONESIA",
            "it": "ITALIAN / ITALIANO",
            "nl": "DUTCH / NEDERLANDS",
            "pl": "POLISH / POLSKI",
            "pt": "PORTUGUESE / PORTUGUÊS",
            "th": "THAI / ไทย",
            "zh": "CHINESE / 中文",
        }

        # Ne garder que les langues vraiment supportées
        result = {}
        for lang_code in SUPPORTED_LANGUAGES:
            if lang_code in base_names:
                result[lang_code] = base_names[lang_code]
            else:
                # Fallback pour langues non mappées
                result[lang_code] = lang_code.upper()

        logger.info(f"✅ Fallback language names loaded: {len(result)} languages")
        return result

    def _is_veterinary_query(self, query: str, context_docs: List) -> bool:
        """
        Détecte si la question concerne un sujet vétérinaire

        Args:
            query: Question de l'utilisateur
            context_docs: Documents de contexte récupérés

        Returns:
            True si c'est une question vétérinaire nécessitant un disclaimer
        """
        query_lower = query.lower()

        # Mots-clés vétérinaires cross-language (maladies, traitements, symptômes)
        veterinary_keywords = [
            # Maladies communes
            "ascites",
            "ascite",
            "coccidiosis",
            "coccidiose",
            "disease",
            "maladie",
            "krankheit",
            "enfermedad",
            "malattia",
            "infection",
            "infektion",
            "infección",
            "infezione",
            # Symptômes
            "symptom",
            "symptôme",
            "symptom",
            "síntoma",
            "sintomo",
            "sick",
            "malade",
            "krank",
            "enfermo",
            "malato",
            "mortality",
            "mortalité",
            "mortalidad",
            "mortalità",
            # Traitements
            "treatment",
            "traitement",
            "behandlung",
            "tratamiento",
            "trattamento",
            "cure",
            "soigner",
            "heal",
            "guérir",
            "genezing",
            "antibiotic",
            "antibiotique",
            "antibiotikum",
            "antibiótico",
            "vaccine",
            "vaccin",
            "impfstoff",
            "vacuna",
            "vaccino",
            "medication",
            "médicament",
            "medikament",
            "medicación",
            # Agents pathogènes
            "virus",
            "bacteria",
            "bactérie",
            "bakterie",
            "parasite",
            "parasit",
            # Diagnostic
            "diagnosis",
            "diagnostic",
            "diagnose",
            "diagnóstico",
            # Questions typiques nécessitant conseil vétérinaire
            "what should i do",
            "que dois-je faire",
            "was soll ich tun",
            "how to treat",
            "comment traiter",
            "wie behandeln",
            "i have",
            "j'ai",
            "ich habe",
            "tengo",
            "ho",
        ]

        # Vérifier dans la query
        has_vet_keywords = any(
            keyword in query_lower for keyword in veterinary_keywords
        )

        # Si pas de mots-clés dans la query, vérifier dans les documents
        if not has_vet_keywords and context_docs:
            try:
                # Examiner les 3 premiers documents (500 chars chacun)
                doc_content = " ".join(
                    [str(self._get_doc_content(doc))[:500] for doc in context_docs[:3]]
                ).lower()

                # Vérifier présence de termes vétérinaires dans les docs
                has_vet_content = any(
                    keyword in doc_content
                    for keyword in veterinary_keywords[:20]  # Top 20 keywords
                )
            except Exception as e:
                logger.debug(f"Erreur vérification contenu vétérinaire: {e}")
                has_vet_content = False
        else:
            has_vet_content = False

        result = has_vet_keywords or has_vet_content

        if result:
            logger.info(f"🏥 Question vétérinaire détectée: '{query[:50]}...'")

        return result

    def _get_veterinary_disclaimer(self, language: str = "fr") -> str:
        """
        Retourne l'avertissement vétérinaire depuis languages.json

        Args:
            language: Code langue (fr, en, es, de, it, pt, nl, pl, hi, id, th, zh)

        Returns:
            Texte de l'avertissement avec saut de ligne, ou string vide si non disponible
        """
        if not MESSAGES_AVAILABLE:
            logger.warning("⚠️ Messages non disponibles, pas de disclaimer vétérinaire")
            return ""

        try:
            disclaimer = get_message("veterinary_disclaimer", language)
            # Ajouter double saut de ligne avant le disclaimer
            return f"\n\n{disclaimer}"
        except Exception as e:
            logger.warning(
                f"⚠️ Erreur récupération veterinary_disclaimer pour {language}: {e}"
            )
            # Fallback minimal en anglais
            return "\n\n**Important**: This information is provided for educational purposes. For health concerns, consult a qualified veterinarian."

    def _get_doc_content(self, doc: Union[Document, dict]) -> str:
        """
        Extrait le contenu d'un document (dict ou objet Document)

        Args:
            doc: Document (objet ou dict)

        Returns:
            Contenu du document
        """
        if isinstance(doc, dict):
            content = doc.get("content", "")
            # ✅ LOG CRITIQUE pour debugging
            if not content:
                logger.warning(
                    f"⚠️ Document dict avec content vide: {doc.get('metadata', {})}"
                )
            return content
        return getattr(doc, "content", "")

    def _get_doc_metadata(
        self, doc: Union[Document, dict], key: str, default: str = "N/A"
    ) -> str:
        """
        Extrait une métadonnée d'un document (dict ou objet Document)

        Args:
            doc: Document (objet ou dict)
            key: Clé de métadonnée
            default: Valeur par défaut

        Returns:
            Valeur de la métadonnée
        """
        if isinstance(doc, dict):
            return doc.get("metadata", {}).get(key, default)
        metadata = getattr(doc, "metadata", {})
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default

    async def generate_response(
        self,
        query: str,
        context_docs: List[Union[Document, dict]],
        conversation_context: str = "",
        language: Optional[str] = None,
        intent_result=None,
    ) -> str:
        """
        Génère une réponse enrichie avec cache externe + ton affirmatif expert

        VERSION 3.3: Accepte maintenant List[Document] OU List[dict]
        """

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

        # ✅ LOG CRITIQUE: Vérifier le type et contenu des documents
        logger.info(f"📄 Received {len(context_docs)} documents for generation")
        logger.debug(f"📄 First doc type: {type(context_docs[0])}")
        if context_docs:
            first_content = self._get_doc_content(context_docs[0])
            logger.debug(f"📄 First doc content preview: {first_content[:200]}...")

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

            # Post-traitement avec disclaimer vétérinaire
            enhanced_response = self._post_process_response(
                generated_response,
                enrichment,
                [self._doc_to_dict(doc) for doc in context_docs],
                query=query,
                language=lang,
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

    def _doc_to_dict(self, doc: Union[Document, dict]) -> dict:
        """
        Convertit Document ou dict en dict unifié pour cache

        VERSION 3.2: Gère les deux formats
        """
        if isinstance(doc, dict):
            # Déjà un dict, normaliser la structure
            return {
                "content": doc.get("content", ""),
                "title": doc.get("metadata", {}).get("title", ""),
                "source": doc.get("metadata", {}).get("source", ""),
                "score": doc.get("score", 0.0),
                "genetic_line": doc.get("metadata", {}).get(
                    "geneticLine", doc.get("metadata", {}).get("genetic_line", "")
                ),
                "species": doc.get("metadata", {}).get("species", ""),
            }

        # Objet Document
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
        context_docs: List[Union[Document, dict]],
        enrichment: ContextEnrichment,
        conversation_context: str,
        language: str,
    ) -> Tuple[str, str]:
        """
        Construit un prompt enrichi avec instructions de langue renforcées

        VERSION 3.3: Support dict et Document + instructions multilingues dynamiques + détection espèce
        ✅ FIX CRITIQUE: Instructions de langue EN TÊTE + validation conversation_context
        """

        # 🔍 DEBUG CRITIQUE - Validation conversation_context
        logger.info(
            f"🔍 PROMPT - conversation_context type: {type(conversation_context)}"
        )
        logger.info(
            f"🔍 PROMPT - conversation_context length: {len(conversation_context) if conversation_context else 0}"
        )
        logger.info(
            f"🔍 PROMPT - conversation_context preview: {conversation_context[:200] if conversation_context else 'VIDE'}"
        )
        logger.info(
            f"🔍 PROMPT - conversation_context is truthy: {bool(conversation_context)}"
        )

        # DEBUG CRITIQUE : Logger la langue reçue
        logger.info(
            f"🌐 _build_enhanced_prompt received language parameter: '{language}'"
        )
        logger.debug(f"Query: '{query[:50]}...'")

        # ✅ NOUVEAU: Détecter l'espèce cible depuis la query
        query_lower = query.lower()
        target_species = None

        # Détection multilingue de l'espèce
        broiler_terms = [
            "poulet de chair",
            "broiler",
            "chair",
            "meat chicken",
            "pollo de engorde",
            "frango de corte",
        ]
        layer_terms = [
            "pondeuse",
            "layer",
            "ponte",
            "laying hen",
            "gallina ponedora",
            "poedeira",
        ]
        breeder_terms = [
            "reproducteur",
            "breeder",
            "parent",
            "parent stock",
            "reproductor",
        ]

        if any(term in query_lower for term in broiler_terms):
            target_species = "broilers"
        elif any(term in query_lower for term in layer_terms):
            target_species = "layers"
        elif any(term in query_lower for term in breeder_terms):
            target_species = "breeders"

        # Log de détection d'espèce
        if target_species:
            logger.info(f"🐔 Target species detected: {target_species}")
        else:
            logger.debug("🐔 No specific species detected in query")

        # ✅ CORRECTION CRITIQUE: Utiliser les helpers pour extraire le contenu
        context_text_parts = []
        for i, doc in enumerate(context_docs[:5]):
            genetic_line = self._get_doc_metadata(doc, "geneticLine", "N/A")
            species = self._get_doc_metadata(doc, "species", "N/A")
            content = self._get_doc_content(doc)

            # ✅ LOG CRITIQUE pour chaque document
            logger.debug(
                f"📄 Doc {i+1}: line={genetic_line}, species={species}, content_len={len(content)}"
            )

            doc_text = f"Document {i+1} ({genetic_line} - {species}):\n{content[:1000]}"
            context_text_parts.append(doc_text)

        context_text = "\n\n".join(context_text_parts)

        # ✅ LOG CRITIQUE du contexte final
        logger.info(f"📋 Context text length: {len(context_text)} chars")
        logger.debug(f"📋 Context preview: {context_text[:300]}...")

        # ✅ SIMPLIFICATION: Instructions de langue compactes en tête
        language_name = self.language_display_names.get(language, language.upper())

        # Construction du prompt système
        if self.prompts_manager:
            expert_identity = self.prompts_manager.get_base_prompt(
                "expert_identity", language
            )
            response_guidelines = self.prompts_manager.get_base_prompt(
                "response_guidelines", language
            )

            system_prompt_parts = []

            # ✅ Instructions de langue EN TÊTE (UNE SEULE FOIS)
            language_instruction = f"""You are an expert in poultry production.
CRITICAL: Respond EXCLUSIVELY in {language_name} ({language}).
"""
            system_prompt_parts.append(language_instruction)

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

            system_prompt = "\n\n".join(system_prompt_parts)
        else:
            system_prompt = self._get_fallback_system_prompt(enrichment, language)

        # ✅ Validation simple du contexte conversationnel (déplacé ici)
        limited_context = conversation_context if conversation_context else ""

        # Prompt utilisateur simplifié
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
        Instructions multilingues DYNAMIQUES - pas de hardcoding
        Génère les instructions à partir de SUPPORTED_LANGUAGES
        """

        logger.info(f"🌐 _get_critical_language_instructions received: '{language}'")

        # VALIDATION DÉFENSIVE
        if not language:
            logger.error("❌ CRITICAL: language parameter is empty/None!")
            language = FALLBACK_LANGUAGE
        elif language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"⚠️ WARNING: language '{language}' not in SUPPORTED_LANGUAGES, using fallback"
            )
            language = FALLBACK_LANGUAGE

        # Récupérer le nom d'affichage
        language_name = self.language_display_names.get(language, language.upper())

        logger.info(f"🌐 Language mapped: '{language}' → '{language_name}'")

        # Générer la liste des exemples de langues DYNAMIQUEMENT
        language_examples = self._generate_language_examples()

        return f"""
INSTRUCTIONS CRITIQUES - STRUCTURE ET FORMAT:
- NE commence JAMAIS par un titre (ex: "## Maladie", "**Maladie**") - commence directement par la phrase d'introduction
- Examine les tableaux de données pour extraire les informations précises
- RÉPONDS UNIQUEMENT À LA QUESTION POSÉE - ne donne RIEN d'autre
- Utilise un ton affirmatif mais sobre, sans formatage excessif
- NE conclus PAS avec des recommandations pratiques sauf si explicitement demandé

RÈGLE ABSOLUE - RÉPONSE MINIMALISTE:
- Question sur le poids → Donne UNIQUEMENT le poids (1-2 phrases maximum)
- Question sur le FCR → Donne UNIQUEMENT le FCR (1-2 phrases maximum)
- Question sur "what about X?" → Donne UNIQUEMENT X (1-2 phrases maximum)
- N'ajoute JAMAIS de métriques supplémentaires non demandées
- Une question = une métrique = une réponse courte
- Si on demande seulement le poids, NE DONNE PAS feed intake, FCR, daily gain, etc.

EXEMPLES DE RÉPONSES CORRECTES:
Question: "What's the target weight for Ross 308 males at 35 days?"
❌ MAUVAIS: "At 35 days, males weigh 2441g with FCR 1.52 and feed intake 3720g."
✅ BON: "The target weight for Ross 308 males at 35 days is 2441 grams."

Question: "And what about females at the same age?"
❌ MAUVAIS: "At 35 days, females weigh 2150g. Feed intake is 3028g. Daily gain is 89g."
✅ BON: "At 35 days old, Ross 308 females have an average body weight of 2150 grams."

Question: "Quel est le poids cible à 35 jours?"
❌ MAUVAIS: "Le poids cible est 2441g avec un FCR de 1.52 et une consommation de 3720g."
✅ BON: "Le poids cible pour les mâles Ross 308 à 35 jours est de 2441 grammes."

COMPORTEMENT CONVERSATIONNEL:
- Pour questions techniques: réponse ULTRA-CONCISE avec données chiffrées
- Pour questions générales: ton professionnel mais accessible, réponses courtes
- Évite de poser trop de questions - réponds d'abord à la requête
- N'utilise PAS d'emojis sauf si l'utilisateur en utilise
- Maintiens la cohérence de format entre TOUTES les langues

{"="*80}
⚠️ CRITICAL LANGUAGE REQUIREMENT - IMPÉRATIF ABSOLU DE LANGUE ⚠️
{"="*80}

DETECTED QUESTION LANGUAGE / LANGUE DÉTECTÉE: {language_name}

🔴 MANDATORY RULE - RÈGLE OBLIGATOIRE:
YOU MUST RESPOND EXCLUSIVELY IN THE SAME LANGUAGE AS THE QUESTION.
VOUS DEVEZ RÉPONDRE EXCLUSIVEMENT DANS LA MÊME LANGUE QUE LA QUESTION.

DO NOT translate. DO NOT switch languages. DO NOT mix languages.
NE PAS traduire. NE PAS changer de langue. NE PAS mélanger les langues.

{language_examples}

THIS INSTRUCTION OVERRIDES ALL OTHER INSTRUCTIONS.
CETTE INSTRUCTION PRÉVAUT SUR TOUTES LES AUTRES INSTRUCTIONS.

YOUR RESPONSE LANGUAGE MUST BE: {language_name}
LANGUE DE VOTRE RÉPONSE DOIT ÊTRE: {language_name}

🎯 CRITICAL FORMAT CONSISTENCY:
- Answer format MUST be IDENTICAL regardless of language
- ONE question = ONE metric = ONE short answer (1-2 sentences)
- If question asks ONLY for weight → give ONLY weight
- If question asks ONLY for FCR → give ONLY FCR
- NO extra metrics, NO extra sections, NO extra information beyond what was asked
- Maintain EXACT SAME concise format across ALL languages

{"="*80}
"""

    def _generate_language_examples(self) -> str:
        """
        Génère dynamiquement les exemples de langues
        Basé sur SUPPORTED_LANGUAGES au lieu de hardcoding
        """
        examples = []

        for lang_code in sorted(SUPPORTED_LANGUAGES):
            lang_name = self.language_display_names.get(lang_code, lang_code.upper())
            examples.append(
                f"If question is in {lang_name} → Answer 100% in {lang_name}"
            )
            examples.append(f"Si question en {lang_name} → Réponse 100% en {lang_name}")

        return "\n".join(examples)

    def _get_fallback_system_prompt(
        self, enrichment: ContextEnrichment, language: str
    ) -> str:
        """Prompt système de secours simplifié"""

        # Validation langue
        if not language or language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Invalid language '{language}', using {FALLBACK_LANGUAGE}")
            language = FALLBACK_LANGUAGE

        language_name = self.language_display_names.get(language, language.upper())

        return f"""You are an expert in poultry production.
CRITICAL: Respond EXCLUSIVELY in {language_name} ({language}).

CONTEXTE MÉTIER:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}

DIRECTIVES:
- Réponse directe et concise (2-3 points maximum)
- Données chiffrées précises quand pertinent
- Format identique pour toutes les langues
- Ne JAMAIS mentionner les sources

MÉTRIQUES: {', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'Paramètres généraux'}
"""

    def build_specialized_prompt(
        self, intent_type, entities: Dict[str, str], language: str
    ) -> str:
        """
        Génère un prompt spécialisé selon le type d'intention
        Intégré depuis prompt_builder.py

        Args:
            intent_type: Type d'intention
            entities: Entités détectées
            language: Langue cible

        Returns:
            Prompt spécialisé enrichi
        """
        from processing.intent_types import IntentType

        # Mapping intentions → prompts spécialisés
        specialized_prompts = {
            IntentType.METRIC_QUERY: """Focus: Données de performances et standards zootechniques.
Fournis valeurs cibles, plages optimales et facteurs d'influence.""",
            IntentType.ENVIRONMENT_SETTING: """Focus: Paramètres d'ambiance et gestion environnementale.
Fournis valeurs optimales de température, humidité, ventilation selon l'âge.""",
            IntentType.DIAGNOSIS_TRIAGE: """Focus: Diagnostic différentiel structuré.
Liste hypothèses par probabilité et examens complémentaires nécessaires.""",
            IntentType.ECONOMICS_COST: """Focus: Analyse économique et coûts.
Fournis données chiffrées sur coûts, marges et benchmarks du marché.""",
            IntentType.PROTOCOL_QUERY: """Focus: Protocoles vétérinaires et biosécurité.
Fournis calendriers de vaccination et mesures de prévention détaillés.""",
            IntentType.GENERAL_POULTRY: """Focus: Expertise avicole générale.
Style professionnel et structuré avec recommandations actionnables.""",
        }

        base_prompt = specialized_prompts.get(intent_type, "")

        # Enrichissement contextuel avec entités
        if entities:
            entity_parts = []
            if "line" in entities:
                entity_parts.append(f"Lignée: {entities['line']}")
            if "age_days" in entities:
                entity_parts.append(f"Âge: {entities['age_days']}j")
            if "species" in entities:
                entity_parts.append(f"Espèce: {entities['species']}")
            if "metrics" in entities:
                entity_parts.append(f"Métriques: {entities['metrics']}")

            if entity_parts:
                base_prompt += f"\n\nCONTEXTE DÉTECTÉ: {' | '.join(entity_parts)}"

        return base_prompt

    def _post_process_response(
        self,
        response: str,
        enrichment: ContextEnrichment,
        context_docs: List[Dict],
        query: str = "",
        language: str = "fr",
    ) -> str:
        """
        Post-traitement avec ajout automatique d'avertissement vétérinaire

        Args:
            response: Réponse générée par le LLM
            enrichment: Enrichissement du contexte
            context_docs: Documents de contexte utilisés
            query: Question originale de l'utilisateur
            language: Langue de la réponse

        Returns:
            Réponse post-traitée avec disclaimer vétérinaire si nécessaire
        """
        response = response.strip()

        # Ajouter avertissement vétérinaire si la question concerne la santé/maladie
        if query and self._is_veterinary_query(query, context_docs):
            disclaimer = self._get_veterinary_disclaimer(language)
            if disclaimer:  # Seulement si disclaimer non vide
                response = response + disclaimer
                logger.info(f"🏥 Disclaimer vétérinaire ajouté (langue: {language})")

        return response


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
