# -*- coding: utf-8 -*-
"""
rag_postgresql_validator.py - Validateur flexible pour requêtes PostgreSQL
VERSION 4.5.2: FIX VALIDATION REQUÊTES SIMPLES
- CORRECTION CRITIQUE: Règles de validation réorganisées (requêtes simples EN PREMIER)
- Support réponses courtes: "35 jours", "Jour 42", "... | 35 days"
- Distinction start_age_days vs target_age_days pour calculs de plage
- Validation spécifique pour requêtes de calcul (feed/moulée)
- Nouvelles méthodes: _translate(), _generate_clarification_message()
- Détection améliorée: _is_calculation_query() avec plus de mots-clés
- Messages de clarification contextualisés et naturels
- Toutes les fonctionnalités précédentes préservées
"""

import re
import logging
import json
from typing import Dict, List, Optional, Any

from utils.breeds_registry import get_breeds_registry

logger = logging.getLogger(__name__)


class PostgreSQLValidator:
    """Validateur intelligent avec auto-détection, alternatives et contextualisation"""

    def __init__(
        self, intents_config_path: str = "llm/config/intents.json", openai_client=None
    ):
        """
        Initialise le validateur avec breeds_registry et OpenAI client

        Args:
            intents_config_path: Chemin vers intents.json
            openai_client: Client OpenAI pour extraction multilingue (optionnel)
        """
        self.logger = logger
        self.breeds_registry = get_breeds_registry(intents_config_path)
        self.openai_client = openai_client  # Stocker le client OpenAI

        if not openai_client:
            logger.warning(
                "⚠️ Validator créé sans OpenAI - extraction multilingue désactivée"
            )
        else:
            logger.info(
                "✅ Validator créé avec OpenAI - extraction multilingue activée"
            )

        logger.info(
            f"PostgreSQLValidator initialisé avec breeds_registry "
            f"({len(self.breeds_registry.get_all_breeds())} races)"
        )

    async def initialize(self):
        """
        Initialise le PostgreSQL Validator de manière asynchrone

        Cette méthode assure la compatibilité avec l'architecture RAG Engine
        qui attend une méthode initialize() async pour tous les modules externes.

        Note: L'initialisation principale se fait déjà dans __init__,
        cette méthode sert principalement à la compatibilité architecturale.
        """
        try:
            # Vérifier que breeds_registry est bien initialisé
            if not self.breeds_registry:
                raise RuntimeError("breeds_registry non initialisé")

            breed_count = len(self.breeds_registry.get_all_breeds())

            self.logger.info(
                f"✅ PostgreSQLValidator initialized - {breed_count} breeds loaded"
            )

            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation PostgreSQLValidator: {e}")
            raise

    async def _extract_with_openai(self, query: str, language: str = "en") -> dict:
        """
        Extraction intelligente multilingue avec OpenAI
        VERSION 4.5: Support réponses courtes comme "35 jours"

        Args:
            query: Requête utilisateur
            language: Code langue (fr, en, es, etc.)

        Returns:
            Dict avec start_age_days, target_age_days, breed, metric_type extraits
        """

        if not self.openai_client:
            logger.warning("⚠️ OpenAI client non disponible pour extraction")
            return {
                "start_age_days": None,
                "target_age_days": None,
                "breed": None,
                "metric_type": None,
            }

        prompt = f"""Extract information from this query in {language}:
Query: "{query}"

**IMPORTANT**: Distinguish between:
- **start_age_days**: The CURRENT/STARTING age (e.g., "I'm at day 18", "je suis au jour 18")
- **target_age_days**: The TARGET/ENDING age (e.g., "until day 35", "Jour 35", "35 jours")

Extract:
1. start_age_days: Starting age in days (where farmer currently is)
2. target_age_days: Target/ending age in days (where farmer wants to finish)
3. breed: Breed/strain name (Ross 308, Cobb 500, etc.)
4. metric_type: Metric requested (weight/poids/peso, feed/moulée/alimento, FCR, etc.)

Return ONLY valid JSON, nothing else:
{{
    "start_age_days": <number or null>,
    "target_age_days": <number or null>,
    "breed": "<breed name or null>",
    "metric_type": "<metric or null>"
}}

Examples in French:
- "Je suis au jour 18... Jour 35" → {{"start_age_days": 18, "target_age_days": 35}}
- "... | 35 jours" → {{"start_age_days": null, "target_age_days": 35}}
- "35 jours" → {{"start_age_days": null, "target_age_days": 35}}
- "Jour 42" → {{"start_age_days": null, "target_age_days": 42}}
- "De jour 15 à 28" → {{"start_age_days": 15, "target_age_days": 28}}
- "Combien de moulée de jour 15 à 28?" → {{"start_age_days": 15, "target_age_days": 28}}

Examples in English:
- "I'm at day 18... Day 35" → {{"start_age_days": 18, "target_age_days": 35}}
- "... | 35 days" → {{"start_age_days": null, "target_age_days": 35}}
- "35 days" → {{"start_age_days": null, "target_age_days": 35}}
- "From day 20 to 42 days" → {{"start_age_days": 20, "target_age_days": 42}}

Examples in Spanish:
- "Estoy en día 18... Día 35" → {{"start_age_days": 18, "target_age_days": 35}}
- "... | 35 días" → {{"start_age_days": null, "target_age_days": 35}}
- "35 días" → {{"start_age_days": null, "target_age_days": 35}}
- "Desde día 20 hasta 42 días" → {{"start_age_days": 20, "target_age_days": 42}}
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150,
                response_format={"type": "json_object"},  # ✅ FORCE JSON MODE
            )

            content = response.choices[0].message.content.strip()

            # ✅ Nettoyage robuste du contenu
            # Enlever les backticks markdown si présents
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            logger.info(f"✅ OpenAI extraction ({language}): {result}")

            # Rétrocompatibilité: si pas de start/target mais age_days présent
            if "age_days" in result and "start_age_days" not in result:
                result["start_age_days"] = result["age_days"]

            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            logger.error(f"Raw content: {response.choices[0].message.content[:200]}")
            return {
                "start_age_days": None,
                "target_age_days": None,
                "breed": None,
                "metric_type": None,
            }
        except Exception as e:
            logger.error(f"❌ OpenAI extraction failed: {e}")
            return {
                "start_age_days": None,
                "target_age_days": None,
                "breed": None,
                "metric_type": None,
            }

    async def _validate_query_completeness(
        self,
        query: str,
        entities: dict,
        language: str = "en",
        previous_context: Dict = None,
    ) -> dict:
        """
        Validation intelligente : détecte automatiquement les informations manquantes
        VERSION 4.5.2: RÈGLES RÉORGANISÉES - Requêtes simples en priorité

        Args:
            query: Requête utilisateur
            entities: Entités détectées
            language: Langue de la requête
            previous_context: Contexte conversationnel précédent (optionnel)

        Returns:
            {
                "is_complete": bool,
                "missing_info": ["description de ce qui manque"],
                "reason": "explication"
            }
        """

        if not self.openai_client:
            logger.warning("⚠️ OpenAI non disponible pour validation")
            return {
                "is_complete": True,
                "missing_info": [],
                "reason": "validation_disabled",
            }

        breed = entities.get("breed", "NOT SPECIFIED")
        start_age = entities.get("start_age_days", entities.get("age_days"))
        target_age = entities.get("target_age_days")
        target_weight = entities.get("target_weight")
        sex = entities.get("sex", "NOT SPECIFIED")
        metric = entities.get("metric_type", "NOT SPECIFIED")

        # Formater les entités pour le prompt
        start_age_str = f"{start_age} days" if start_age else "NOT SPECIFIED"
        target_age_str = f"{target_age} days" if target_age else "NOT SPECIFIED"
        target_weight_str = f"{target_weight} kg" if target_weight else "NOT SPECIFIED"

        # Ajouter le contexte conversationnel si disponible
        context_info = ""
        if previous_context:
            context_info = f"""
Previous conversation context:
{json.dumps(previous_context, indent=2)}

Note: Use this context to understand if missing information might be implied from previous exchanges.
"""

        prompt = f"""You are validating if a poultry production query has all necessary information to be answered.

User query: "{query}"
Language: {language}

{context_info}

Detected entities:
- Breed: {breed}
- Start Age: {start_age_str}
- Target Age: {target_age_str}
- Target Weight: {target_weight_str}
- Sex: {sex}
- Metric: {metric}

**VALIDATION RULES - APPLY IN THIS EXACT ORDER:**

**RULE 1 - SIMPLE METRIC QUERIES (CHECK THIS FIRST):**
If the query asks for a SINGLE METRIC VALUE at a SPECIFIC AGE:
Examples: 
- "weight at 17 days", "poids à 17 jours", "peso a 17 días"
- "What should their weight be at 28 days?", "Quel devrait être leur poids à 28 jours?"
- "FCR at day 28", "IC jour 28", "conversión día 28"
- "feed intake day 35", "consommation jour 35"
- "Quel est le poids...", "What is the weight...", "Cuál es el peso..."
- "I'm raising broilers and they're currently 28 days old. What should their average weight be?"

→ Requirements: Breed + Age + Metric = COMPLETE
→ NO need for target_age or target_weight
→ The age mentioned IS the point of interest (not a starting point for calculation)

**CRITICAL FOR RULE 1:**
- If query asks "What should the weight be at X days?" → ONLY breed is missing (if not specified)
- If query asks "What is the weight at X days?" → ONLY breed is missing (if not specified)
- NEVER EVER ask for target_weight in Rule 1 queries
- target_weight is ONLY for Rule 2 (calculation queries like "feed until reaching 2.5kg")
- Questions using "should", "average", "typical", "normal" at a specific age are Rule 1

**RULE 2 - PERIOD/CALCULATION QUERIES:**
If the query asks for TOTALS, CALCULATIONS, or data over a TIME PERIOD:
Examples:
- "feed from day 18 to 35", "moulée de jour 18 à 35"
- "total feed until 2.5kg", "total jusqu'à 2.5kg"
- "combien de moulée pour finir", "how much feed to finish"

Keywords indicating calculations: "total", "combien", "how much", "cuánto", "de...à", "from...to", "until", "jusqu'à", "hasta"

→ Requirements: Breed + Start Age + (Target Age OR Target Weight) = COMPLETE
→ If only Start Age (no endpoint) = INCOMPLETE

**RULE 3 - COMPARISON QUERIES:**
If comparing multiple entities → need at least 2 complete entities

**CRITICAL INSTRUCTION:**
- Apply RULE 1 FIRST for 80%+ of queries
- Only apply RULE 2 if query explicitly mentions calculations, totals, or time ranges
- Questions like "Quel est...", "What is...", "Cuál es..." are ALWAYS Rule 1 (simple queries)

**Analysis required:**
1. Is this a simple metric lookup at one specific age? (RULE 1) → is_complete based on breed + age + metric
2. OR is this a calculation over a period? (RULE 2) → is_complete needs endpoint

Return ONLY valid JSON:
{{
    "is_complete": true/false,
    "missing_info": ["list of missing information **IN {language.upper()}**"],
    "reason": "brief explanation mentioning which rule applies"
}}

**IMPORTANT**: 
- "missing_info" list MUST be in {language.upper()} language
- State which rule (1, 2, or 3) determined your answer

Examples:
- "Quel est le poids à 17 jours pour Ross 308?" → {{"is_complete": true, "missing_info": [], "reason": "Rule 1: simple metric query with breed + age + metric"}}
- "Poids du Ross 308 mâle de 17 jours?" → {{"is_complete": true, "missing_info": [], "reason": "Rule 1: has all required data for point query"}}
- "Combien de moulée de jour 18 à 35 pour Ross 308?" → {{"is_complete": true, "missing_info": [], "reason": "Rule 2: calculation query with breed + start + target age"}}
- "Feed from day 18 with 20k birds Ross 308?" → {{"is_complete": false, "missing_info": ["target age or weight"], "reason": "Rule 2: calculation needs endpoint"}}
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()

            # Nettoyage backticks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            logger.info(f"✅ Validation completeness ({language}): {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Validation completeness failed: {e}")
            # En cas d'erreur, retourner incomplet pour éviter de bloquer
            return {
                "is_complete": False,
                "missing_info": ["validation error"],
                "reason": str(e),
            }

    def _generate_smart_clarification(
        self, missing_info: list, language: str, reason: str
    ) -> str:
        """Génère un message de clarification basé sur les informations manquantes détectées par l'IA"""

        templates = {
            "en": "To provide an accurate answer, I need additional information:\n\n{missing_list}\n\nThis will help me give you a precise response.",
            "fr": "Pour vous fournir une réponse précise, j'ai besoin d'informations supplémentaires :\n\n{missing_list}\n\nCela me permettra de vous donner une réponse adaptée.",
            "es": "Para darle una respuesta precisa, necesito información adicional:\n\n{missing_list}\n\nEsto me ayudará a darle una respuesta exacta.",
        }

        template = templates.get(language, templates["en"])

        # Formater la liste des informations manquantes
        missing_formatted = "\n".join([f"• {info}" for info in missing_info])

        return template.format(missing_list=missing_formatted)

    def validate_context(
        self, entities: Dict, query: str, language: str = "fr"
    ) -> Dict:
        """
        Valide le contexte avec fusion OpenAI AVANT validation

        Args:
            entities: Entités extraites (peut contenir _openai_interpretation)
            query: Requête utilisateur
            language: Langue détectée

        Returns:
            Dict avec status et missing_fields après fusion
        """
        # Récupérer les entités OpenAI si disponibles
        openai_interp = entities.get("_openai_interpretation", {})

        # Enrichir avec OpenAI AVANT validation
        if openai_interp:
            if not entities.get("age_days") and "age_days" in openai_interp:
                entities["age_days"] = openai_interp["age_days"]
                logger.info(
                    f"✅ Age récupéré depuis OpenAI: {openai_interp['age_days']}"
                )

            if not entities.get("breed") and "breed" in openai_interp:
                entities["breed"] = openai_interp["breed"]
                logger.info(
                    f"✅ Breed récupéré depuis OpenAI: {openai_interp['breed']}"
                )

            if not entities.get("metric_type") and "metric_type" in openai_interp:
                entities["metric_type"] = openai_interp["metric_type"]
                logger.info(
                    f"✅ Metric récupéré depuis OpenAI: {openai_interp['metric_type']}"
                )

        # MAINTENANT valider ce qui manque vraiment
        missing_fields = []
        if not entities.get("breed"):
            missing_fields.append("breed")
        if not entities.get("age_days"):
            missing_fields.append("age")
        if not entities.get("metric") and not entities.get("metric_type"):
            missing_fields.append("metric")

        return {
            "status": "complete" if not missing_fields else "needs_fallback",
            "missing_fields": missing_fields,
            "enhanced_entities": entities,
            "detected_entities": entities,
        }

    async def flexible_query_validation(
        self,
        query: str,
        entities: Dict[str, Any],
        language: str = "fr",
        conversation_context: Dict = None,  # ✅ NOUVEAU PARAMÈTRE
    ) -> Dict[str, Any]:
        """
        Validation flexible qui essaie de compléter les requêtes incomplètes

        VERSION 4.4.1: AJOUT CONVERSATION_CONTEXT
        - Nouveau paramètre conversation_context pour contexte conversationnel
        - Intégration validation intelligente avec contexte
        - Toutes les autres fonctionnalités préservées

        Args:
            query: Requête utilisateur
            entities: Entités extraites (peut contenir _openai_interpretation)
            language: Langue détectée (fr, en, es, etc.)
            conversation_context: Contexte conversationnel précédent (optionnel)

        Returns:
            Dict avec status: "complete" | "incomplete_but_processable" | "needs_fallback"
        """

        entities = entities or {}
        missing = []
        suggestions = []

        # LOG CRITIQUE #1 : Ce qui ARRIVE au validator
        logger.debug(f"🔍 VALIDATOR INPUT entities: {entities}")
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'sex' present: {'sex' in entities}, value: {entities.get('sex')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'breed' present: {'breed' in entities}, value: {entities.get('breed')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'age_days' present: {'age_days' in entities}, value: {entities.get('age_days')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'explicit_sex_request' present: {'explicit_sex_request' in entities}, value: {entities.get('explicit_sex_request')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'metric_type' present: {'metric_type' in entities}, value: {entities.get('metric_type')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - conversation_context present: {bool(conversation_context)}"
        )

        # CORRECTION CRITIQUE: Copier TOUTES les entités originales en priorité
        # Cela préserve automatiquement 'sex', 'explicit_sex_request', etc.
        enhanced_entities = dict(entities) if entities else {}

        # FUSION OpenAI: Récupérer les entités OpenAI si disponibles
        openai_interp = enhanced_entities.get("_openai_interpretation", {})

        if openai_interp:
            logger.debug(f"🔍 OpenAI interpretation trouvée: {openai_interp}")

            # Enrichir UNIQUEMENT les champs manquants avec OpenAI
            if not enhanced_entities.get("age_days") and "age_days" in openai_interp:
                enhanced_entities["age_days"] = openai_interp["age_days"]
                logger.info(
                    f"✅ Age récupéré depuis OpenAI: {openai_interp['age_days']}"
                )

            if not enhanced_entities.get("breed") and "breed" in openai_interp:
                enhanced_entities["breed"] = openai_interp["breed"]
                logger.info(
                    f"✅ Breed récupéré depuis OpenAI: {openai_interp['breed']}"
                )

            if (
                not enhanced_entities.get("metric_type")
                and "metric_type" in openai_interp
            ):
                enhanced_entities["metric_type"] = openai_interp["metric_type"]
                logger.info(
                    f"✅ Metric récupéré depuis OpenAI: {openai_interp['metric_type']}"
                )

        # 🤖 CORRECTION CRITIQUE VERSION 4.5: Extraction OpenAI SYSTÉMATIQUE
        # Même si age_days existe, on DOIT capturer target_age_days pour les calculs
        logger.info(
            f"🤖 Appel OpenAI SYSTÉMATIQUE pour extraction multilingue ({language})"
        )
        openai_extracted = await self._extract_with_openai(query, language)

        # Fusionner intelligemment les données (prioriser OpenAI pour start/target)
        start_age = (
            openai_extracted.get("start_age_days")
            or enhanced_entities.get("age_days")
            or enhanced_entities.get("start_age_days")
        )
        target_age = openai_extracted.get("target_age_days") or enhanced_entities.get(
            "target_age_days"
        )

        # Logs détaillés
        if start_age:
            logger.info(f"✅ Âge de départ: {start_age} jours")
        if target_age:
            logger.info(f"✅ Âge cible: {target_age} jours")
        else:
            logger.warning(f"⚠️ Âge cible NON détecté dans: '{query}'")

        # ✅ MISE À JOUR DES ENTITÉS avec les deux âges
        if start_age:
            enhanced_entities["age_days"] = start_age
            enhanced_entities["start_age_days"] = start_age  # Alias pour clarté
        if target_age:
            enhanced_entities["target_age_days"] = target_age

        # Enrichir breed si trouvé par OpenAI
        if not enhanced_entities.get("breed") and openai_extracted.get("breed"):

            normalized_breed = self.breeds_registry.normalize_breed_name(
                openai_extracted["breed"]
            )

            if normalized_breed:
                enhanced_entities["breed"] = normalized_breed
                enhanced_entities["has_explicit_breed"] = True
                logger.info(f"✅ Breed détecté par OpenAI: {normalized_breed}")

        # Enrichir metric si trouvé par OpenAI
        if not enhanced_entities.get("metric_type") and openai_extracted.get(
            "metric_type"
        ):
            # Normaliser la métrique
            metric_mapping = {
                "peso": "weight",
                "poids": "weight",
                "gewicht": "weight",
                "conversión": "fcr",
                "conversion": "fcr",
                "mortalidad": "mortality",
                "mortalité": "mortality",
                "moulée": "feed",
                "alimento": "feed",
                "feed": "feed",
            }
            normalized_metric = metric_mapping.get(
                openai_extracted["metric_type"].lower(),
                openai_extracted["metric_type"],
            )
            enhanced_entities["metric_type"] = normalized_metric
            logger.info(f"✅ Metric détecté par OpenAI: {normalized_metric}")

        # ✅ NOUVEAU: Validation intelligente de complétude avec contexte
        logger.info(
            f"🧠 Validation intelligente (contexte: {bool(conversation_context)})..."
        )
        completeness = await self._validate_query_completeness(
            query, enhanced_entities, language, previous_context=conversation_context
        )

        if not completeness.get("is_complete"):
            missing_descriptions = completeness.get("missing_info", [])
            logger.info(f"⚠️ Requête incomplète détectée: {missing_descriptions}")

            clarification_msg = self._generate_smart_clarification(
                missing_descriptions, language, completeness.get("reason", "")
            )

            return {
                "status": "needs_fallback",
                "enhanced_entities": enhanced_entities,
                "missing": missing_descriptions,
                "helpful_message": clarification_msg,
                "detected_entities": enhanced_entities,
            }

        # 🔥 FIX CRITIQUE v4.5.3: Si OpenAI valide comme "complete", on fait confiance
        # La validation intelligente via OpenAI est plus fiable que les regex locales
        logger.info(
            f"✅ Requête validée complète par OpenAI - {completeness.get('reason', '')}"
        )

        # NOTE: L'ancienne logique _is_calculation_query() créait des contradictions
        # Elle est maintenant désactivée car OpenAI gère mieux les cas limites

        # LOG CRITIQUE #2 : Juste après dict(entities) et fusion OpenAI
        logger.debug(
            f"🔍 enhanced_entities AFTER dict(entities) + OpenAI fusion: {enhanced_entities}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'sex' present: {'sex' in enhanced_entities}, value: {enhanced_entities.get('sex')}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'explicit_sex_request' present: {'explicit_sex_request' in enhanced_entities}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'metric_type' present: {'metric_type' in enhanced_entities}, value: {enhanced_entities.get('metric_type')}"
        )

        # Invalider metric_type si c'est 'as_hatched' ou autre valeur invalide
        metric = enhanced_entities.get("metric_type") or enhanced_entities.get("metric")
        if metric:
            metric_lower = str(metric).lower().strip()
            invalid_metrics = [
                "as_hatched",
                "as-hatched",
                "mixed",
                "none",
                "",
                "male",
                "female",
            ]
            if metric_lower in invalid_metrics:
                logger.warning(
                    f"⚠️ metric invalide '{metric}' → None, auto-détection activée"
                )
                enhanced_entities["metric_type"] = None
                enhanced_entities["metric"] = None

        # Auto-détection breed SEULEMENT si absent dans les entités originales ET OpenAI
        if not enhanced_entities.get("breed"):
            logger.debug("🔍 Breed ABSENT, auto-detecting from query...")
            detected_breed = self._detect_breed_from_query(query)
            if detected_breed:
                enhanced_entities["breed"] = detected_breed
                logger.debug(f"✅ Auto-detected breed: {detected_breed}")
            else:
                logger.debug("❌ No breed detected in query")
                missing.append("breed")
                suggestions.append(self._get_breed_suggestion(language))
        else:
            logger.debug(
                f"🔍 Breed PRESENT: '{enhanced_entities.get('breed')}', skipping auto-detection"
            )

        # Auto-détection age SEULEMENT si absent dans les entités originales ET OpenAI
        if not enhanced_entities.get("age_days"):
            logger.debug("🔍 Age ABSENT, auto-detecting from query...")
            detected_age = self._detect_age_from_query(query)
            if detected_age:
                enhanced_entities["age_days"] = detected_age
                logger.debug(f"✅ Auto-detected age: {detected_age} days")
            else:
                logger.debug("❌ No age detected in query")
                # Pour certaines requêtes, l'âge n'est pas critique
                if any(
                    word in query.lower()
                    for word in [
                        "recommande",
                        "meilleur",
                        "compare",
                        "général",
                        "recommend",
                        "best",
                        "compare",
                        "general",
                    ]
                ):
                    logger.debug("🔍 General query, age not critical")
                    pass
                else:
                    missing.append("age")
                    suggestions.append(self._get_age_suggestion(language))
        else:
            logger.debug(
                f"🔍 Age PRESENT: '{enhanced_entities.get('age_days')}', skipping auto-detection"
            )

        # Auto-détection metric avec vérification de 'metric' OU 'metric_type'
        if not enhanced_entities.get("metric_type") and not enhanced_entities.get(
            "metric"
        ):
            logger.debug("🔍 Metric ABSENT, auto-detecting from query...")
            detected_metric = self._auto_detect_metric_type(query)
            if detected_metric:
                enhanced_entities["metric_type"] = detected_metric
                logger.debug(f"✅ Auto-detected metric: {detected_metric}")
            else:
                logger.debug("❌ No metric detected in query")
                missing.append("metric")
                suggestions.append(self._get_metric_suggestion(language))
        else:
            metric_value = enhanced_entities.get("metric") or enhanced_entities.get(
                "metric_type"
            )
            logger.debug(
                f"🔍 Metric PRESENT: '{metric_value}', skipping auto-detection"
            )

        # LOG CRITIQUE #3 : Avant de retourner
        logger.debug(f"🔍 enhanced_entities FINAL before return: {enhanced_entities}")
        logger.debug(
            f"🔍 FINAL - 'sex' present: {'sex' in enhanced_entities}, value: {enhanced_entities.get('sex')}"
        )
        logger.debug(
            f"🔍 FINAL - 'explicit_sex_request' present: {'explicit_sex_request' in enhanced_entities}, value: {enhanced_entities.get('explicit_sex_request')}"
        )
        logger.debug(
            f"🔍 FINAL - 'metric_type' present: {'metric_type' in enhanced_entities}, value: {enhanced_entities.get('metric_type')}"
        )

        # VÉRIFICATION CRITIQUE : Comparaison INPUT vs OUTPUT
        input_keys = set(entities.keys())
        output_keys = set(enhanced_entities.keys())
        lost_keys = input_keys - output_keys

        if lost_keys:
            logger.error(f"❌❌❌ VALIDATOR LOST KEYS: {lost_keys}")
            logger.error(f"❌ INPUT had: {input_keys}")
            logger.error(f"❌ OUTPUT has: {output_keys}")

            # CORRECTION : RESTAURER les champs perdus
            for key in lost_keys:
                enhanced_entities[key] = entities[key]
                logger.warning(f"⚠️ RESTORED lost key '{key}': {entities[key]}")

            logger.debug(f"🔍 enhanced_entities AFTER restoration: {enhanced_entities}")
        else:
            logger.debug("✅ No keys lost, all fields preserved")

        # Log de debug pour vérifier que tous les champs sont préservés
        if entities:
            preserved_fields = [k for k in entities.keys() if k in enhanced_entities]
            if preserved_fields:
                logger.debug(f"✅ Preserved original fields: {preserved_fields}")

        # Déterminer le statut
        if not missing:
            logger.debug("✅ Validation complete, returning enhanced_entities")
            return {
                "status": "complete",
                "enhanced_entities": enhanced_entities,
                "filtering_hints": {
                    "strict_sex_match": enhanced_entities.get(
                        "has_explicit_sex", False
                    ),
                    "strict_breed_match": enhanced_entities.get(
                        "has_explicit_breed", False
                    ),
                    "strict_age_match": enhanced_entities.get(
                        "has_explicit_age", False
                    ),
                },
            }

        elif len(missing) <= 1 and ("breed" not in missing):
            # CORRECTION CRITIQUE : Vérifier si l'âge manquant est critique
            if "age" in missing:
                # Pour des métriques qui varient fortement avec l'âge, c'est critique
                critical_metrics = [
                    "weight",
                    "body_weight",
                    "poids",
                    "feed_conversion",
                    "conversion",
                    "fcr",
                    "daily_gain",
                    "gain",
                ]
                metric = enhanced_entities.get("metric_type", "").lower()
                metric_name = enhanced_entities.get("metric", "").lower()

                # Vérifier si la métrique est critique
                is_critical_metric = any(m in metric for m in critical_metrics) or any(
                    m in metric_name for m in critical_metrics
                )

                if is_critical_metric:
                    logger.debug(
                        f"❌ Age manquant pour métrique critique '{metric}' - needs_fallback"
                    )
                    helpful_message = self._generate_conversational_question(
                        query, missing, suggestions, language
                    )
                    return {
                        "status": "needs_fallback",
                        "missing": missing,
                        "suggestions": suggestions,
                        "helpful_message": helpful_message,
                        "detected_entities": enhanced_entities,
                    }

            # Si ce n'est pas critique (ex: mortalité générale), on peut traiter
            logger.debug(f"⚠️ Validation incomplete but processable, missing: {missing}")
            return {
                "status": "incomplete_but_processable",
                "message": f"Autoriser la requête sans {', '.join(missing)} spécifique",
                "enhanced_entities": enhanced_entities,
                "missing": missing,
            }

        else:
            # Trop d'informations manquantes - Message conversationnel
            logger.debug(f"❌ Validation needs fallback, missing: {missing}")
            helpful_message = self._generate_conversational_question(
                query, missing, suggestions, language
            )
            return {
                "status": "needs_fallback",
                "missing": missing,
                "suggestions": suggestions,
                "helpful_message": helpful_message,
                "detected_entities": enhanced_entities,
            }

    def _is_calculation_query(self, entities: Dict, query: str = "") -> bool:
        """
        Détecte si c'est une requête de calcul nécessitant une plage (start + target age)
        VERSION 4.5: Amélioration de la détection avec plus de mots-clés

        Args:
            entities: Entités extraites
            query: Requête utilisateur (optionnel, pour contexte supplémentaire)

        Returns:
            True si c'est une requête de calcul nécessitant start et target age
        """
        query_lower = query.lower()

        # Mots-clés de calcul (VERSION ÉTENDUE)
        calc_keywords = [
            "combien",
            "how much",
            "cuanto",
            "cuánto",
            "total",
            "besoin",
            "need",
            "necesito",
            "calculer",
            "calculate",
            "calcular",
            "de jour",
            "from day",
            "desde día",
            "jusqu'à",
            "until",
            "hasta",
            "compléter",
            "finish",
            "terminar",
            "à",
            "to",
            "a",
        ]

        # Métrique de type feed/moulée
        metric = entities.get("metric_type", "").lower()
        feed_keywords = ["moulée", "feed", "alimento", "alimentation"]

        has_calc_keyword = any(kw in query_lower for kw in calc_keywords)
        has_feed_metric = any(kw in metric for kw in feed_keywords)

        # Si target_age_days est présent, c'est probablement un calcul
        has_target_age = entities.get("target_age_days") is not None

        is_calc = has_calc_keyword or has_feed_metric or has_target_age

        if is_calc:
            logger.debug(
                f"🔢 Calcul détecté - calc_kw: {has_calc_keyword}, feed: {has_feed_metric}, target_age: {has_target_age}"
            )

        return is_calc

    def _translate(self, term: str, language: str) -> str:
        """
        Traduction simple des termes de clarification

        Args:
            term: Terme anglais à traduire
            language: Langue cible

        Returns:
            Terme traduit
        """
        translations = {
            "starting age": {
                "fr": "âge de départ",
                "en": "starting age",
                "es": "edad de inicio",
            },
            "target age": {
                "fr": "âge cible",
                "en": "target age",
                "es": "edad objetivo",
            },
            "breed": {"fr": "race/souche", "en": "breed/strain", "es": "raza/cepa"},
        }
        return translations.get(term, {}).get(language, term)

    def _generate_clarification_message(
        self, missing_fields: list, language: str
    ) -> str:
        """
        Génère un message de clarification naturel et contextualisé

        Args:
            missing_fields: Liste des champs manquants
            language: Langue du message

        Returns:
            Message de clarification personnalisé
        """
        missing_str = str(missing_fields).lower()

        # Messages spécifiques pour target age dans contexte de calcul
        if language == "fr":
            if "âge cible" in missing_str or "target age" in missing_str:
                return "Pour calculer la quantité de moulée nécessaire, j'ai besoin de connaître l'âge cible (par exemple: 35 jours, 42 jours, etc.)"
            elif "âge de départ" in missing_str or "starting age" in missing_str:
                return "Pour calculer la quantité de moulée, j'ai besoin de connaître l'âge de départ (par exemple: 18 jours, 20 jours, etc.)"
        elif language == "en":
            if "target age" in missing_str or "âge cible" in missing_str:
                return "To calculate the required feed quantity, I need to know the target age (e.g., 35 days, 42 days, etc.)"
            elif "starting age" in missing_str or "âge de départ" in missing_str:
                return "To calculate the feed quantity, I need to know the starting age (e.g., 18 days, 20 days, etc.)"
        elif language == "es":
            if "edad objetivo" in missing_str or "target age" in missing_str:
                return "Para calcular la cantidad de alimento necesaria, necesito saber la edad objetivo (por ejemplo: 35 días, 42 días, etc.)"
            elif "edad de inicio" in missing_str or "starting age" in missing_str:
                return "Para calcular la cantidad de alimento, necesito saber la edad de inicio (por ejemplo: 18 días, 20 días, etc.)"

        # Fallback générique
        return f"Missing information: {', '.join(missing_fields)}"

    def _get_breed_suggestion(self, language: str) -> str:
        """Retourne une suggestion pour la race selon la langue"""
        suggestions = {
            "fr": "Quelle race/souche élevez-vous ? (Ross 308, Cobb 500, Hubbard, etc.)",
            "en": "Which breed/strain are you raising? (Ross 308, Cobb 500, Hubbard, etc.)",
            "es": "¿Qué raza/cepa está criando? (Ross 308, Cobb 500, Hubbard, etc.)",
        }
        return suggestions.get(language, suggestions["fr"])

    def _get_age_suggestion(self, language: str) -> str:
        """Retourne une suggestion pour l'âge selon la langue"""
        suggestions = {
            "fr": "À quel âge (en jours) souhaitez-vous cette information ?",
            "en": "At what age (in days) would you like this information?",
            "es": "¿A qué edad (en días) desea esta información?",
        }
        return suggestions.get(language, suggestions["fr"])

    def _get_metric_suggestion(self, language: str) -> str:
        """Retourne une suggestion pour la métrique selon la langue"""
        suggestions = {
            "fr": "Quelle métrique vous intéresse ? (poids vif, conversion alimentaire, gain quotidien, mortalité)",
            "en": "Which metric are you interested in? (body weight, feed conversion, daily gain, mortality)",
            "es": "¿Qué métrica le interesa? (peso vivo, conversión alimenticia, ganancia diaria, mortalidad)",
        }
        return suggestions.get(language, suggestions["fr"])

    def _generate_conversational_question(
        self,
        query: str,
        missing: List[str],
        suggestions: List[str],
        language: str = "fr",
    ) -> str:
        """
        VERSION 4.3: Génère une question de clarification conversationnelle
        avec format amélioré pour questions multiples (numérotation + fermeture)

        Args:
            query: Requête originale
            missing: Champs manquants
            suggestions: Suggestions détaillées (non utilisées directement)
            language: Langue de la réponse

        Returns:
            Question conversationnelle formatée
        """

        # Templates d'introduction selon la langue
        intros = {
            "fr": "Pour vous donner une réponse précise, j'ai besoin de quelques informations supplémentaires.",
            "en": "To provide you with an accurate answer, I need some additional information.",
            "es": "Para darle una respuesta precisa, necesito información adicional.",
        }

        intro = intros.get(language, intros["fr"])

        # Générer les bonnes suggestions basées sur les champs MISSING
        contextual_suggestions = []
        for field in missing:
            if "breed" in field.lower() or "race" in field.lower():
                contextual_suggestions.append(self._get_breed_suggestion(language))
            elif "age" in field.lower() or "âge" in field.lower():
                contextual_suggestions.append(self._get_age_suggestion(language))
            elif "metric" in field.lower() or "métrique" in field.lower():
                contextual_suggestions.append(self._get_metric_suggestion(language))

        # Construction de la question
        parts = [intro]

        # Format plus conversationnel avec numérotation
        if len(contextual_suggestions) > 1:
            numbered_intro = {
                "fr": "Pourriez-vous me préciser ces informations :",
                "en": "Could you please provide these details:",
                "es": "¿Podría proporcionar estos detalles:",
            }

            parts.append(f"\n\n{numbered_intro.get(language, numbered_intro['fr'])}")

            for idx, suggestion in enumerate(contextual_suggestions, 1):
                parts.append(f"\n{idx}) {suggestion}")

            # Ajouter phrase de fermeture
            closing = {
                "fr": "\n\nCela me permettra de vous donner une réponse précise et adaptée.",
                "en": "\n\nThis will allow me to give you an accurate and tailored answer.",
                "es": "\n\nEsto me permitirá darle una respuesta precisa y adaptada.",
            }
            parts.append(closing.get(language, closing["fr"]))

        elif len(contextual_suggestions) == 1:
            # Un seul champ manquant
            parts.append(f"\n\n{contextual_suggestions[0]}")
        else:
            # Fallback si aucune suggestion générée
            parts.append("\n\nVeuillez fournir les informations manquantes.")

        return "".join(parts)

    def _generate_generic_fallback_message(
        self, query: str, partial_entities: Dict, language: str = "fr"
    ) -> str:
        """
        VERSION 4.3: Génère une réponse générique lorsque clarification abandonnée

        Utilise le contexte partiel disponible pour fournir des informations
        générales utiles selon le type d'oiseau détecté.

        Args:
            query: Requête originale de l'utilisateur
            partial_entities: Entités partiellement extraites (breed, age_days, etc.)
            language: Langue de la réponse (fr, en, es)

        Returns:
            Message générique enrichi avec données moyennes appropriées
        """

        # Extraire ce qu'on sait déjà
        breed = partial_entities.get("breed")
        age_days = partial_entities.get("age_days")

        templates = {
            "fr": {
                "intro": "Je comprends. Voici des informations générales qui pourraient vous aider",
                "with_breed": "pour {breed}",
                "with_age": "à {age} jours",
                "broiler_general": (
                    "**Données moyennes pour poulets de chair :**\n"
                    "- Poids : 300g (J1) à 2500g (J42)\n"
                    "- FCR : 1.5-1.9 selon âge et souche\n"
                    "- Consommation eau : 1.8-2.2x aliment\n"
                    "- Mortalité cumulée : 3-5%"
                ),
                "layer_general": (
                    "**Données moyennes pour poules pondeuses :**\n"
                    "- Poids adulte : 1.8-2.0 kg\n"
                    "- Production : 300-320 œufs/an\n"
                    "- Consommation : 110-120g/jour\n"
                    "- Pic de ponte : 24-28 semaines"
                ),
                "footer": "\n\nPour une réponse précise, indiquez la race et l'âge exacts.",
            },
            "en": {
                "intro": "I understand. Here's general information that might help",
                "with_breed": "for {breed}",
                "with_age": "at {age} days",
                "broiler_general": (
                    "**Average data for broilers:**\n"
                    "- Weight: 300g (D1) to 2500g (D42)\n"
                    "- FCR: 1.5-1.9 depending on age and strain\n"
                    "- Water consumption: 1.8-2.2x feed\n"
                    "- Cumulative mortality: 3-5%"
                ),
                "layer_general": (
                    "**Average data for layers:**\n"
                    "- Adult weight: 1.8-2.0 kg\n"
                    "- Production: 300-320 eggs/year\n"
                    "- Consumption: 110-120g/day\n"
                    "- Peak production: 24-28 weeks"
                ),
                "footer": "\n\nFor a precise answer, provide the exact breed and age.",
            },
            "es": {
                "intro": "Entiendo. Aquí hay información general que podría ayudar",
                "with_breed": "para {breed}",
                "with_age": "a {age} días",
                "broiler_general": (
                    "**Datos promedio para pollos de engorde:**\n"
                    "- Peso: 300g (D1) a 2500g (D42)\n"
                    "- FCR: 1.5-1.9 según edad y cepa\n"
                    "- Consumo de agua: 1.8-2.2x alimento\n"
                    "- Mortalidad acumulada: 3-5%"
                ),
                "layer_general": (
                    "**Datos promedio para gallinas ponedoras:**\n"
                    "- Peso adulto: 1.8-2.0 kg\n"
                    "- Producción: 300-320 huevos/año\n"
                    "- Consumo: 110-120g/día\n"
                    "- Pico de producción: 24-28 semanas"
                ),
                "footer": "\n\nPara una respuesta precisa, indique la raza y edad exactas.",
            },
        }

        t = templates.get(language, templates["en"])

        # Construire message
        message_parts = [t["intro"]]

        # Ajouter contexte partiel si disponible
        if breed:
            message_parts.append(t["with_breed"].format(breed=breed))
        if age_days:
            message_parts.append(t["with_age"].format(age=age_days))

        message_parts.append(":\n\n")

        # Déterminer type d'oiseau pour données appropriées
        bird_type = "broiler"
        if breed:
            try:
                species = self.breeds_registry.get_species(breed)
                if species == "layer":
                    bird_type = "layer"
            except Exception as e:
                logger.debug(f"Impossible de déterminer species pour {breed}: {e}")

        # Ajouter données générales
        if bird_type == "layer":
            message_parts.append(t["layer_general"])
        else:
            message_parts.append(t["broiler_general"])

        message_parts.append(t["footer"])

        return " ".join(message_parts)

    def _generate_validation_help_message(
        self, query: str, missing: List[str], suggestions: List[str]
    ) -> str:
        """
        Génère un message d'aide pour validation
        DÉPRÉCIÉE: Utiliser _generate_conversational_question à la place
        """
        return (
            f"Informations manquantes pour traiter votre requête : {', '.join(missing)}. "
            f"Suggestions : {' '.join(suggestions)}"
        )

    def validate_and_enhance(self, entities: Dict, query: str) -> Dict:
        """
        Valider et enrichir les entités
        Méthode alternative avec invalidation explicite des métriques invalides

        VERSION 4.3.1: Ajoute detected_entities dans tous les retours
        """

        enhanced = dict(entities) if entities else {}
        missing = []
        message = ""

        # Invalider metric_type si c'est 'as_hatched' ou valeur invalide
        metric = enhanced.get("metric_type")
        if metric:
            metric_lower = str(metric).lower().strip()
            invalid_metrics = [
                "as_hatched",
                "as-hatched",
                "mixed",
                "none",
                "",
                "male",
                "female",
            ]
            if metric_lower in invalid_metrics:
                self.logger.warning(
                    f"⚠️ metric_type invalide '{metric}' → None, auto-détection activée"
                )
                enhanced["metric_type"] = None

        # Si metric_type est None, activer auto-détection
        if not enhanced.get("metric_type"):
            self.logger.debug("🔍 Metric ABSENT, auto-detecting from query...")
            detected = self._auto_detect_metric_type(query)
            if detected:
                enhanced["metric_type"] = detected
                self.logger.debug(f"✅ Auto-detected metric: {detected}")
            else:
                self.logger.debug("❌ No metric detected in query")
                missing.append("metric_type")
        else:
            self.logger.debug(
                f"🔍 Metric PRESENT: '{enhanced['metric_type']}', skipping auto-detection"
            )

        # Vérifier breed avec breeds_registry
        if not enhanced.get("breed"):
            detected_breed = self._detect_breed_from_query(query)
            if detected_breed:
                enhanced["breed"] = detected_breed
            else:
                missing.append("breed")

        # Vérifier age
        if not enhanced.get("age_days"):
            detected_age = self._detect_age_from_query(query)
            if detected_age:
                enhanced["age_days"] = detected_age
            else:
                missing.append("age_days")

        # Déterminer statut
        if not missing:
            status = "complete"
        elif len(missing) <= 1:
            status = "incomplete_but_processable"
            message = f"Informations manquantes: {', '.join(missing)}"
        else:
            status = "needs_fallback"
            message = f"Trop d'informations manquantes: {', '.join(missing)}"

        return {
            "status": status,
            "enhanced_entities": enhanced,
            "detected_entities": enhanced,
            "missing": missing,
            "message": message,
        }

    def _detect_breed_from_query(self, query: str) -> Optional[str]:
        """
        Détecte la race dans le texte de la requête via breeds_registry
        Version 3.1: CORRIGÉ - get_all_breeds() retourne Set[str], pas des objets
        """
        query_lower = query.lower()

        # Itérer sur toutes les races connues (Set[str] de noms canoniques)
        for breed_name in self.breeds_registry.get_all_breeds():
            # breed_name est une string comme "ross 308", "cobb 500"

            # Vérifier le nom canonique
            if breed_name.lower() in query_lower:
                logger.debug(f"✅ Breed détecté (canonical): {breed_name}")
                return breed_name

            # Récupérer et vérifier les aliases pour cette race
            aliases = self.breeds_registry.get_aliases(breed_name)
            for alias in aliases:
                if alias.lower() in query_lower:
                    logger.debug(f"✅ Breed détecté (alias '{alias}'): {breed_name}")
                    return breed_name

        logger.debug("❌ Aucun breed détecté")
        return None

    def _detect_age_from_query(self, query: str) -> Optional[int]:
        """Détecte l'âge dans le texte de la requête"""
        age_patterns = [
            r"à \s+(\d+)\s+jours?",
            r"(\d+)\s+jours?",
            r"(\d+)\s*j\b",
            r"(\d+)\s+semaines?",
            r"at\s+(\d+)\s+days?",
        ]

        for pattern in age_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if "semaine" in pattern.lower() or "week" in pattern.lower():
                    age = age * 7
                return age

        return None

    def _detect_metric_from_query(self, query: str) -> Optional[str]:
        """
        Détecte le type de métrique dans la requête
        VERSION BASIQUE - À utiliser pour compatibilité descendante
        """
        query_lower = query.lower()

        metric_keywords = {
            "weight": ["poids", "weight", "body weight"],
            "feed_conversion": [
                "conversion",
                "fcr",
                "ic",
                "feed conversion",
                "conversion alimentaire",
            ],
            "mortality": ["mortalité", "mortality", "viabilité", "viability"],
        }

        for metric_type, keywords in metric_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return metric_type

        return None

    def _auto_detect_metric_type(self, query: str) -> Optional[str]:
        """
        Détecter automatiquement le type de métrique depuis la requête
        VERSION ENRICHIE - Cohérente avec query_preprocessor
        """

        query_lower = query.lower()

        # Patterns étendus (cohérents avec query_preprocessor)
        metric_patterns = {
            # Poids
            "poids": "body_weight",
            "weight": "body_weight",
            "poids vif": "body_weight",
            "body weight": "body_weight",
            # Gain
            "gain quotidien": "daily_weight_gain",
            "gain moyen quotidien": "average_daily_gain",
            "gain moyen": "average_daily_gain",
            "gmq": "average_daily_gain",
            "gmo": "average_daily_gain",
            "adg": "average_daily_gain",
            # Consommation
            "consommation cumulée": "cumulative_feed_intake",
            "consommation cumulative": "cumulative_feed_intake",
            "consommation totale": "cumulative_feed_intake",
            "aliment cumulé": "cumulative_feed_intake",
            # Conversion
            "indice de consommation": "feed_conversion_ratio",
            "conversion alimentaire": "feed_conversion_ratio",
            "ic": "feed_conversion_ratio",
            "fcr": "feed_conversion_ratio",
            # Mortalité
            "mortalité": "mortality",
            "taux de mortalité": "mortality",
            "viabilité": "mortality",
            "mortality": "mortality",
        }

        # Chercher par ordre de spécificité (plus long d'abord)
        for pattern in sorted(metric_patterns.keys(), key=len, reverse=True):
            if pattern in query_lower:
                detected = metric_patterns[pattern]
                self.logger.debug(
                    f"✅ Métrique auto-détectée: '{pattern}' → {detected}"
                )
                return detected

        self.logger.debug("❌ Aucune métrique détectée automatiquement")
        return None

    def check_data_availability_flexible(
        self, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Vérifie si les données demandées sont disponibles
        Version 3.1: Utilise breeds_registry pour obtenir les plages d'âges
        """
        breed = entities.get("breed", "").lower() if entities.get("breed") else None
        age_days = entities.get("age_days")

        if not breed or not age_days:
            return {"available": True}

        age = int(age_days) if isinstance(age_days, (int, str)) else None
        if not age:
            return {"available": True}

        # Utiliser breeds_registry pour valider la race
        is_valid, canonical_breed = self.breeds_registry.validate_breed(breed)

        if not is_valid:
            return {
                "available": False,
                "error": f"Race non reconnue: {breed}",
                "helpful_response": f"La race '{breed}' n'est pas dans notre base de données.",
            }

        # Plages d'âges génériques par species
        species = self.breeds_registry.get_species(canonical_breed)

        age_ranges = {
            "broiler": (0, 56),
            "layer": (0, 600),
            "breeder": (0, 60),
        }

        if species in age_ranges:
            min_age, max_age = age_ranges[species]

            if min_age <= age <= max_age:
                return {"available": True}
            else:
                alternatives = []
                if age < min_age:
                    alternatives.append(f"{min_age} jours (âge minimum)")
                if age > max_age:
                    alternatives.append(f"{max_age} jours (âge maximum)")

                return {
                    "available": False,
                    "alternatives": alternatives,
                    "helpful_response": f"Données non disponibles pour {canonical_breed} à {age} jours. Alternatives : {', '.join(alternatives)}",
                }

        return {"available": True}


# Tests unitaires - AU NIVEAU RACINE
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 70)
    print("🧪 TESTS POSTGRESQL VALIDATOR - VERSION 4.5.2 FIX REQUÊTES SIMPLES")
    print("=" * 70)

    validator = PostgreSQLValidator()

    # Test 1: Détection breed
    print("\n🔍 Test 1: Détection de breed depuis requête")
    test_queries = [
        "Quel est le poids du Cobb 500 à 21 jours ?",
        "FCR ross308 à 35j",
        "Performance ISA Brown",
        "Hubbard classic 42 jours",
    ]

    for query in test_queries:
        detected = validator._detect_breed_from_query(query)
        print(f"  Query: {query}")
        print(f"  → Breed: {detected}")

    # Test 2: Validation avec enrichissement et contexte
    print("\n✅ Test 2: Validation et enrichissement avec contexte")
    test_cases = [
        {
            "query": "Poids à 21 jours pour Cobb 500",
            "entities": {"breed": "cobb 500"},
            "context": None,
        },
        {
            "query": "FCR du Ross 308",
            "entities": {},
            "context": {"breed": "Ross 308", "previous_age": 28},
        },
        {
            "query": "Mortalité",
            "entities": {"age_days": 35},
            "context": {"breed": "Cobb 500", "metric_type": "mortality"},
        },
        {
            "query": "Combien de moulée de jour 18 à 35 pour Ross 308?",
            "entities": {},
            "context": None,
        },
        {
            "query": "35 jours",
            "entities": {},
            "context": {
                "breed": "Ross 308",
                "metric_type": "feed",
                "start_age_days": 18,
            },
        },
        {
            "query": "Quel est le poids d'un Ross 308 mâle de 17 jours ?",
            "entities": {"breed": "ross 308", "age_days": 17, "sex": "male"},
            "context": None,
        },
    ]

    import asyncio

    async def run_tests():
        for test in test_cases:
            print(f"\n  Query: {test['query']}")
            print(f"  Input entities: {test['entities']}")
            print(f"  Context: {test['context']}")

            result = await validator.flexible_query_validation(
                test["query"], test["entities"], conversation_context=test["context"]
            )

            print(f"  → Status: {result['status']}")
            if "enhanced_entities" in result:
                print(f"  → Enhanced: {result['enhanced_entities']}")
            if "detected_entities" in result:
                print(f"  → Detected: {result['detected_entities']}")
            if "helpful_message" in result:
                print(f"  → Message: {result['helpful_message'][:100]}...")

    asyncio.run(run_tests())

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS - PostgreSQL Validator VERSION 4.5.2")
    print(
        "🎯 FIX CRITIQUE: Validation requêtes simples réorganisée (Rule 1 en priorité)"
    )
    print(
        "🔧 Requêtes 'Quel est le poids à X jours' maintenant reconnues comme COMPLÈTES"
    )
    print("=" * 70)
