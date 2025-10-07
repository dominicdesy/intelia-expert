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
from utils.types import List, Tuple, Dict, Optional, Union
import re
from core.data_models import Document
from config.config import (
    SUPPORTED_LANGUAGES,
    FALLBACK_LANGUAGE,
)
from utils.utilities import METRICS
from .entity_manager import EntityEnrichmentBuilder
from .models import ContextEnrichment
from utils.llm_translator import LLMTranslator

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

        # Charger le gestionnaire d'enrichissement d'entités
        self.entity_enrichment_builder = EntityEnrichmentBuilder(descriptions_path)

        # ✅ NOUVEAU: Charger les noms de langues dynamiquement
        self.language_display_names = self._load_language_names()

        # 🌍 Initialiser traducteur pour réponses multilingues
        self.translator = LLMTranslator(cache_enabled=True)
        logger.info("✅ LLMTranslator initialized for response translation")

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
        detected_domain: str = None,
    ) -> str:
        """
        Génère une réponse enrichie avec cache externe + ton affirmatif expert

        VERSION 3.4: Support détection de domaine pour sélection de prompt spécialisé
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
                self.entity_enrichment_builder.build_enrichment(intent_result)
                if intent_result
                else ContextEnrichment("", "", "", "", [], [])
            )

            # Générer le prompt enrichi avec domaine détecté
            system_prompt, user_prompt = self._build_enhanced_prompt(
                query,
                context_docs,
                enrichment,
                conversation_context,
                lang,
                detected_domain,
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

            # 🌍 Translate response to target language if not English
            # The LLM generates in English (based on English-translated query and English documents)
            # We need to translate back to user's language
            final_response = enhanced_response
            if lang and lang != "en":
                try:
                    final_response = self.translator.translate(
                        enhanced_response,
                        target_language=lang,
                        source_language="en"
                    )
                    logger.info(
                        f"🌍 Response translated en→{lang}: {len(enhanced_response)} → {len(final_response)} chars"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Response translation failed (en→{lang}), using English: {e}"
                    )
                    # Fallback: keep English response
                    final_response = enhanced_response

            # Mettre en cache
            if self.cache_manager and self.cache_manager.enabled:
                await self.cache_manager.set_response(
                    query, context_hash, final_response, lang
                )

            return final_response

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

    def _build_enhanced_prompt(
        self,
        query: str,
        context_docs: List[Union[Document, dict]],
        enrichment: ContextEnrichment,
        conversation_context: str,
        language: str,
        detected_domain: str = None,
    ) -> Tuple[str, str]:
        """
        Construit un prompt enrichi avec instructions de langue renforcées

        VERSION 3.4: Support détection domaine pour prompts spécialisés
        ✅ NEW: Utilise detected_domain pour sélectionner nutrition_query, health_diagnosis, etc.
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
            f"🌍 _build_enhanced_prompt received language parameter: '{language}'"
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
            logger.info(f"🔍 Target species detected: {target_species}")
        else:
            logger.debug("🔍 No specific species detected in query")

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
        # language_name unused - removed to fix F841

        # Construction du prompt système avec domaine spécialisé
        if self.prompts_manager:
            system_prompt_parts = []

            # ✅ Instructions de langue EN TÊTE (UNE SEULE FOIS)
            # 🌍 ALWAYS generate in English - translation to target language happens post-generation
            language_instruction = """You are an expert in poultry production.
CRITICAL: Respond EXCLUSIVELY in ENGLISH.

FORMATTING RULES - CLEAN & MODERN:
- NO bold headers with asterisks (**Header:**)
- Use simple paragraph structure with clear topic sentences
- Separate ideas with line breaks, not headers
- Use bullet points (- ) ONLY for lists, NEVER numbered lists (1., 2., 3.)
- Keep responses clean, concise and professional
- NO excessive formatting or visual artifacts
"""
            system_prompt_parts.append(language_instruction)

            # ✅ NOUVEAU: Utiliser le prompt spécialisé si domaine détecté
            if detected_domain and detected_domain != "general_poultry":
                specialized_prompt = self.prompts_manager.get_specialized_prompt(
                    detected_domain, language
                )
                if specialized_prompt:
                    logger.info(f"✅ Utilisation prompt spécialisé: {detected_domain}")
                    system_prompt_parts.append(specialized_prompt)
                else:
                    logger.warning(
                        f"Prompt spécialisé '{detected_domain}' non trouvé, fallback general"
                    )
                    expert_identity = self.prompts_manager.get_base_prompt(
                        "expert_identity", language
                    )
                    if expert_identity:
                        system_prompt_parts.append(expert_identity)
            else:
                # Fallback: prompt général
                expert_identity = self.prompts_manager.get_base_prompt(
                    "expert_identity", language
                )
                if expert_identity:
                    system_prompt_parts.append(expert_identity)

            # Contexte métier (toujours inclus)
            context_section = f"""
CONTEXTE MÉTIER DÉTECTÉ:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}
"""
            system_prompt_parts.append(context_section)

            # Guidelines générales
            response_guidelines = self.prompts_manager.get_base_prompt(
                "response_guidelines", language
            )
            if response_guidelines:
                system_prompt_parts.append(response_guidelines)

            # Métriques prioritaires
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

        logger.info(f"🌍 _get_critical_language_instructions received: '{language}'")

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

        logger.info(f"🌍 Language mapped: '{language}' → '{language_name}'")

        # Language examples generation removed (unused variable F841)

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
⚠️ CRITICAL LANGUAGE REQUIREMENT ⚠️
{"="*80}

🔴 MANDATORY RULE:
YOU MUST RESPOND EXCLUSIVELY IN ENGLISH.

All responses will be automatically translated to the user's language ({language_name}) after generation.

THIS INSTRUCTION OVERRIDES ALL OTHER INSTRUCTIONS.

YOUR RESPONSE LANGUAGE MUST BE: ENGLISH

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

        # 🌍 ALWAYS generate in English - translation to target language happens post-generation
        return f"""You are an expert in poultry production.
CRITICAL: Respond EXCLUSIVELY in ENGLISH.

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

        # ✅ NETTOYAGE AMÉLIORÉ DU FORMATAGE

        # 1. Supprimer les numéros de liste (1., 2., etc.)
        response = re.sub(r"^\d+\.\s+", "", response, flags=re.MULTILINE)

        # 2. Nettoyer les astérisques orphelins (lignes avec juste ** ou **)
        response = re.sub(r"^\*\*\s*$", "", response, flags=re.MULTILINE)

        # 3. SUPPRIMER COMPLÈTEMENT les headers en gras (**Titre:** ou **Titre**)
        # Cette règle remplace les anciennes règles 3-5 qui essayaient de "corriger" les headers
        response = re.sub(r"\*\*([^*]+?):\*\*\s*", "", response)
        response = re.sub(r"\*\*([^*]+?)\*\*\s*:", "", response)

        # 4. Nettoyer les deux-points orphelins sur des lignes isolées
        response = re.sub(r"^\s*:\s*$", "", response, flags=re.MULTILINE)

        # 5. Nettoyer les lignes vides multiples (3+ → 2)
        response = re.sub(r"\n{3,}", "\n\n", response)

        # 6. Supprimer les espaces en fin de ligne
        response = re.sub(r" +$", "", response, flags=re.MULTILINE)

        # 7. S'assurer qu'il y a un espace après les bullet points
        response = re.sub(r"^-([^ ])", r"- \1", response, flags=re.MULTILINE)

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
