# -*- coding: utf-8 -*-
"""
query_enricher.py - Enrichissement conversationnel des requêtes
Version 1.0 - Reformule les questions de suivi avec le contexte précédent
"""

import logging
import re
from utils.types import Dict, Set

logger = logging.getLogger(__name__)


class ConversationalQueryEnricher:
    """Enrichit les questions de suivi avec le contexte conversationnel"""

    def __init__(self):
        # Patterns de questions de suivi
        self.followup_patterns = {
            "fr": [
                r"^(quel|quelle|quels|quelles)\s+\w+\s*\??$",
                r"^et\s+(pour|chez|avec|à)",
                r"^(comment|pourquoi|où|quand)\s+\w+\s*\??$",
            ],
            "en": [
                r"^(what|which)\s+\w+\s*\??$",
                r"^(and|what\s+about)\s+",
                r"^(how|why|where|when)\s+\w+\s*\??$",
            ],
        }

        # Entités importantes
        self.entity_keywords = {
            "diseases": [
                "ascite",
                "ascites",
                "coccidiosis",
                "coccidiose",  # 🔧 FIX: Ajout coccidiose FR
                "newcastle",
                "gumboro",
                "bronchite",
                "colibacillose",
                "salmonellose",
                "salmonella",
                "mycoplasma",
                "mycoplasmose",
                "marek",
                "aviaire",
                "influenza",
                "grippe",
                "enterite",
                "dermatite",
            ],
            "breeds": ["ross", "cobb", "hubbard", "ross 308", "cobb 500"],
            "species": ["poulet", "broiler", "layer", "chair", "pondeuse"],
            "metrics": ["poids", "weight", "fcr", "mortalité", "ponte"],
            "treatments": ["traitement", "treatment", "vaccin", "antibiotique"],
        }

    def enrich(self, query: str, contextual_history: str, language: str = "fr") -> str:
        """Enrichit une query avec le contexte conversationnel"""

        if not query or not contextual_history:
            return query

        # 🆕 STEP 0: Check if this is a confirmation to a specific follow-up question
        # If user says "Yes" to "Can I help you optimize weight?", reformulate as optimization request
        enriched_from_followup = self._handle_followup_confirmation(query, contextual_history, language)
        if enriched_from_followup:
            logger.info(f"Follow-up confirmation enriched: '{query}' → '{enriched_from_followup}'")
            return enriched_from_followup

        # 1. Détecter question de suivi
        if not self._is_followup_question(query, language):
            return query

        logger.info(f"Question de suivi détectée: '{query}'")

        # 2. Extraire entités du contexte
        entities = self._extract_entities_from_history(contextual_history)

        if not entities:
            return query

        # 3. Reformuler
        enriched = self._rewrite_query(query, entities, language)

        if enriched != query:
            logger.info(f"Query enrichie: '{query}' → '{enriched}'")

        return enriched

    def _handle_followup_confirmation(self, query: str, contextual_history: str, language: str) -> str:
        """
        Handle user confirmation to a proactive follow-up question

        If user says "Yes" to "Can I help you optimize weight?", reformulate as
        "How to optimize weight for Ross 308 at 16 days?"

        Returns enriched query if confirmation detected, None otherwise
        """
        query_lower = query.lower().strip()

        # Check if query is a short confirmation (yes/oui/ok)
        confirmation_words = {
            'fr': ['oui', 'ouais', 'd\'accord', 'ok', 'okay', 'bien sûr', 'volontiers', 'oui,'],
            'en': ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'please', 'yup', 'yes,'],
            'es': ['sí', 'si', 'vale', 'ok', 'okay', 'claro', 'por supuesto'],
            'de': ['ja', 'okay', 'ok', 'gerne', 'klar'],
        }

        is_confirmation = any(
            query_lower == word or query_lower.startswith(word + ' ')
            for word in confirmation_words.get(language, confirmation_words['fr'])
        )

        if not is_confirmation:
            return None

        # Check if history contains a proactive follow-up with optimization/improvement
        history_lower = contextual_history.lower()

        # Extract the follow-up question from history
        # Format: [Follow-up: Question here...]
        followup_match = re.search(r'\[follow-up:\s*(.+?)\]', history_lower, re.IGNORECASE)
        if not followup_match:
            return None

        followup_text = followup_match.group(1).strip()

        # Check if follow-up is about optimization/improvement
        optimization_keywords = {
            'fr': ['optimiser', 'améliorer', 'augmenter', 'conseils', 'stratégies'],
            'en': ['optimize', 'improve', 'increase', 'advice', 'strategies'],
            'es': ['optimizar', 'mejorar', 'aumentar', 'consejos', 'estrategias'],
            'de': ['optimieren', 'verbessern', 'erhöhen', 'ratschläge', 'strategien'],
        }

        is_optimization_followup = any(
            keyword in followup_text
            for keyword in optimization_keywords.get(language, optimization_keywords['fr'])
        )

        if not is_optimization_followup:
            return None

        # Extract entities from history (breed, age, metric)
        entities = self.extract_entities_from_context(contextual_history, language)

        # Build optimization question
        metric = entities.get('metric_type', 'performance')
        breed = entities.get('breed', '')
        age = entities.get('age_days', '')
        sex = entities.get('sex', '')

        # Translate metric to readable form
        metric_translations = {
            'fr': {
                'weight': 'poids',
                'fcr': 'FCR',
                'feed_consumption': 'consommation d\'aliment',
                'mortality': 'mortalité',
                'performance': 'performances',
            },
            'en': {
                'weight': 'weight',
                'fcr': 'FCR',
                'feed_consumption': 'feed consumption',
                'mortality': 'mortality',
                'performance': 'performance',
            },
            'es': {
                'weight': 'peso',
                'fcr': 'FCR',
                'feed_consumption': 'consumo de alimento',
                'mortality': 'mortalidad',
                'performance': 'rendimiento',
            },
            'de': {
                'weight': 'Gewicht',
                'fcr': 'Futterverwertung',
                'feed_consumption': 'Futterverbrauch',
                'mortality': 'Mortalität',
                'performance': 'Leistung',
            },
        }

        metric_display = metric_translations.get(language, {}).get(metric, metric)

        # Build enriched query based on language
        if language == 'fr':
            enriched = f"Comment améliorer le {metric_display}"
            if breed:
                enriched += f" pour {breed}"
            if age:
                enriched += f" à {age} jours"
            if sex and sex != 'mixed':
                sex_fr = {'male': 'mâle', 'female': 'femelle'}.get(sex, sex)
                enriched += f" ({sex_fr})"
            enriched += " ?"
        elif language == 'en':
            enriched = f"How to improve {metric_display}"
            if breed:
                enriched += f" for {breed}"
            if age:
                enriched += f" at {age} days"
            if sex and sex != 'mixed':
                enriched += f" ({sex})"
            enriched += "?"
        elif language == 'es':
            enriched = f"Cómo mejorar el {metric_display}"
            if breed:
                enriched += f" para {breed}"
            if age:
                enriched += f" a los {age} días"
            if sex and sex != 'mixed':
                sex_es = {'male': 'macho', 'female': 'hembra'}.get(sex, sex)
                enriched += f" ({sex_es})"
            enriched += "?"
        elif language == 'de':
            enriched = f"Wie kann man das {metric_display} verbessern"
            if breed:
                enriched += f" für {breed}"
            if age:
                enriched += f" am Tag {age}"
            if sex and sex != 'mixed':
                sex_de = {'male': 'männlich', 'female': 'weiblich'}.get(sex, sex)
                enriched += f" ({sex_de})"
            enriched += "?"
        else:
            enriched = f"How to improve {metric_display}"
            if breed:
                enriched += f" for {breed}"
            enriched += "?"

        return enriched

    def _is_followup_question(self, query: str, language: str) -> bool:
        """Détecte si c'est une question de suivi"""

        query_lower = query.lower().strip()

        # 🔧 FIX: Critère spécial pour questions de traitement/protocole sans contexte
        # Ces questions sont souvent des follow-ups même si elles sont complètes
        treatment_patterns = [
            "quel traitement",
            "quelle traitement",
            "what treatment",
            "which treatment",
            "quel protocole",
            "what protocol",
            "quel vaccin",
            "what vaccine",
        ]

        for pattern in treatment_patterns:
            if query_lower.startswith(pattern):
                logger.debug(f"Treatment question detected as follow-up: {query}")
                return True

        # Critère 1: Très courte (< 6 mots)
        word_count = len(query_lower.split())
        if word_count > 6:
            return False

        # Critère 2: Match patterns de suivi
        patterns = self.followup_patterns.get(language, self.followup_patterns["fr"])

        for pattern in patterns:
            if re.search(pattern, query_lower):
                return True

        # Critère 3: Pronoms sans antécédent clair
        pronouns = ["il", "elle", "le", "la", "les", "celui", "celle", "ceux"]
        if any(pronoun in query_lower.split()[:3] for pronoun in pronouns):
            return True

        return False

    def _extract_entities_from_history(self, history: str) -> Dict[str, Set[str]]:
        """Extrait les entités du dernier échange"""

        entities = {
            "diseases": set(),
            "breeds": set(),
            "species": set(),
            "metrics": set(),
            "treatments": set(),
        }

        history_lower = history.lower()

        # Extraire chaque type d'entité
        for entity_type, keywords in self.entity_keywords.items():
            for keyword in keywords:
                if keyword in history_lower:
                    entities[entity_type].add(keyword)

        return entities

    def _rewrite_query(
        self, query: str, entities: Dict[str, Set[str]], language: str
    ) -> str:
        """Reformule la query en ajoutant le contexte"""

        query_lower = query.lower()
        additions = []

        # 🔧 FIX: Détection améliorée pour questions de traitement/protocole
        is_treatment_question = any(
            keyword in query_lower
            for keyword in [
                "traitement",
                "treatment",
                "protocole",
                "protocol",
                "vaccin",
                "vaccine",
                "antibiotique",
                "antibiotic",
                "médicament",
                "medication",
                "utilise",
                "utilisé",
                "used",
                "recommandé",
                "recommended",
            ]
        )

        # Cas 1: "Quel traitement ?" + maladie connue
        if is_treatment_question:
            # Ajouter maladie du contexte si disponible
            if entities["diseases"]:
                disease = list(entities["diseases"])[0]
                # Ne pas ajouter si déjà dans la query
                if disease.lower() not in query_lower:
                    # Format FR: "pour la coccidiose"
                    if language == "fr":
                        additions.append(f"pour la {disease}")
                    else:
                        additions.append(f"for {disease}")

            # Ajouter espèce si disponible
            if entities["species"]:
                species = list(entities["species"])[0]
                if species not in query_lower:
                    if language == "fr":
                        additions.append(f"chez les {species}s")
                    else:
                        additions.append(f"in {species}s")

        # Cas 2: "Et pour X ?" → ajouter race/métrique du contexte
        elif query_lower.startswith("et ") or query_lower.startswith("and "):
            if entities["breeds"]:
                breed = list(entities["breeds"])[0]
                if breed not in query_lower:
                    additions.insert(0, breed)
            if entities["metrics"]:
                metric = list(entities["metrics"])[0]
                if metric not in query_lower:
                    additions.append(metric)

        # Cas 3: Question vague → ajouter espèce si disponible
        elif len(query.split()) < 4 and entities["species"]:
            species = list(entities["species"])[0]
            if species not in query_lower:
                additions.append(f"chez {species}")

        # Construire query enrichie
        if additions:
            enriched = query.rstrip("?") + " " + " ".join(additions)
            return enriched.strip() + ("?" if query.endswith("?") else "")

        return query

    def extract_entities_from_context(
        self, contextual_history: str, language: str = "fr", current_query: str = ""
    ) -> Dict[str, any]:
        """
        Extract structured entities from conversation history for router

        IMPORTANT: Only extract missing entities to avoid contaminating standalone queries
        If current query already contains breed + metric, do NOT extract age from context

        Args:
            contextual_history: Formatted conversation history
            language: Query language
            current_query: Current user query (to detect if it's standalone vs follow-up)

        Returns:
            Dict with extracted entities (breed, age_days, sex, etc.)
        """
        if not contextual_history:
            return {}

        entities = {}
        history_lower = contextual_history.lower()

        # 🔍 Detect if current query is a standalone complete question
        current_query_lower = current_query.lower() if current_query else ""

        # Check if current query contains breed + metric (indicates standalone question)
        has_breed_in_query = any(
            breed in current_query_lower
            for breed in ["ross", "cobb", "hubbard", "aviagen", "isa", "lohmann"]
        )
        has_metric_in_query = any(
            metric in current_query_lower
            for metric in ["poids", "weight", "fcr", "mortalité", "mortality", "ponte", "consommation", "gain"]
        )

        is_standalone_query = has_breed_in_query and has_metric_in_query

        # 🔧 FIX: Extract age from CURRENT QUERY first (BEFORE standalone check)
        # Important pour merged queries comme "What is weight of Cobb 500 male? 17"
        age_from_current_query = None
        if current_query:
            current_query_stripped = current_query.strip()

            # Check if current query is a simple number (clarification response)
            if current_query_stripped.isdigit():
                age_from_current_query = int(current_query_stripped)
                logger.info(f"✅ Age extracted from current query: {age_from_current_query} days (number only)")
            else:
                # Try patterns in current query
                age_patterns_current = [
                    r"(\d+)\s*(?:jour|day)s?",  # "21 days", "21 jours"
                    r"(\d+)\s*j\b",             # "21j"
                    r"\?\s*(\d+)\s*$",          # "...male? 17" (nombre après ?)
                    r"\s(\d+)\s*$",             # "...male 17" (nombre à la fin)
                ]

                for pattern in age_patterns_current:
                    match = re.search(pattern, current_query.lower())
                    if match:
                        age_from_current_query = int(match.group(1))
                        logger.info(f"✅ Age extracted from current query: {age_from_current_query} days (pattern match)")
                        break

        if is_standalone_query:
            logger.info(
                "🚫 Standalone query detected (breed + metric present) - "
                "will NOT extract age from context to avoid contamination"
            )
        else:
            logger.debug(
                "✅ Follow-up query detected - will extract all entities from context"
            )

        # Extract breed
        breed_patterns = [
            (r"ross\s*308", "Ross 308"),
            (r"cobb\s*500", "Cobb 500"),
            (r"hubbard\s*(classic|flex)", "Hubbard"),
            (r"\bross\b", "Ross"),
            (r"\bcobb\b", "Cobb"),
        ]

        for pattern, breed_name in breed_patterns:
            if re.search(pattern, history_lower):
                entities["breed"] = breed_name
                logger.debug(f"Breed extracted from context: {breed_name}")
                break

        # Extract age in days
        # 🔧 PRIORITÉ #1: Use age already extracted from current query (above)
        # 🔧 PRIORITÉ #2: Extract from context if follow-up query and no age in current query
        if age_from_current_query is not None:
            # Age already extracted from current query
            entities["age_days"] = age_from_current_query
        elif not is_standalone_query:
            # Follow-up query: try to extract from context
            age_days = None

            # Extract from cleaned context
            if contextual_history:
                # Remove examples from history to avoid extracting from them
                # 🔧 FIX: Also remove "e.g." patterns
                history_cleaned = re.sub(
                    r'(?:ex:|exemple:|example:|e\.g\.|eg\.).*?(?:\)|$)',  # Remove text after examples until ) or end
                    '',
                    history_lower,
                    flags=re.IGNORECASE | re.DOTALL
                )

                age_patterns = [
                    r"(\d+)\s*(?:jour|day)s?",
                    r"(\d+)\s*j\b",
                    r"day\s*(\d+)",
                    r"à\s*(\d+)",
                ]

                for pattern in age_patterns:
                    match = re.search(pattern, history_cleaned)
                    if match:
                        age_days = int(match.group(1))
                        logger.debug(f"Age extracted from context: {age_days} days")
                        break

            # Store extracted age
            if age_days is not None:
                entities["age_days"] = age_days
        else:
            logger.info(
                "🔒 Skipping age extraction from context (standalone query with breed + metric)"
            )

        # Extract sex
        sex_keywords = {
            "mâle": "male",
            "male": "male",
            "femelle": "female",
            "female": "female",
            "mixte": "mixed",
            "mixed": "mixed",
        }

        for keyword, sex_value in sex_keywords.items():
            if keyword in history_lower:
                entities["sex"] = sex_value
                logger.debug(f"Sex extracted from context: {sex_value}")
                break

        # Extract metric type
        metric_keywords = {
            "poids": "weight",
            "weight": "weight",
            "fcr": "fcr",
            "conversion": "fcr",
            "mortalité": "mortality",
            "mortality": "mortality",
            "consommation": "feed_consumption",
        }

        for keyword, metric_value in metric_keywords.items():
            if keyword in history_lower:
                entities["metric_type"] = metric_value
                logger.debug(f"Metric extracted from context: {metric_value}")
                break

        # 🔧 FIX: Extract disease from context (important for treatment follow-up questions)
        for disease in self.entity_keywords["diseases"]:
            if disease in history_lower:
                entities["disease"] = disease
                logger.debug(f"Disease extracted from context: {disease}")
                break

        if entities:
            logger.info(
                f"📦 Extracted {len(entities)} entities from context: {list(entities.keys())}"
            )

        return entities


# Factory function
def create_query_enricher() -> ConversationalQueryEnricher:
    """Crée une instance de l'enrichisseur"""
    return ConversationalQueryEnricher()
