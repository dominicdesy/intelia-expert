# -*- coding: utf-8 -*-
"""
query_preprocessor.py - Préprocesseur de requêtes avec OpenAI
Version ENRICHIE avec détection patterns calculatoires, temporels, économiques
"""

import logging
import re
from openai import AsyncOpenAI
import json
from typing import Dict, Any, List, Optional

from .comparative_detector import ComparativeQueryDetector

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """
    Préprocesse les requêtes utilisateur avec :
    - Correction des fautes de frappe
    - Normalisation de la terminologie
    - Extraction des métadonnées structurées
    - Détection des requêtes comparatives
    - Détection patterns calculatoires, temporels, optimisation, économiques
    """

    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self._is_initialized = False
        self.comparative_detector = ComparativeQueryDetector()

    async def initialize(self):
        """Initialisation et validation du preprocessor"""
        if not self.client:
            raise ValueError("OpenAI client is required for QueryPreprocessor")

        try:
            logger.info(
                "Initialisation du Query Preprocessor avec détection enrichie..."
            )
            self._is_initialized = True
            logger.info("Query Preprocessor initialisé avec succès")
            return self
        except Exception as e:
            logger.error(f"Erreur initialisation QueryPreprocessor: {e}")
            raise

    async def close(self):
        """Fermeture propre du preprocessor"""
        self._is_initialized = False
        logger.debug("Query Preprocessor fermé")

    async def preprocess_query(
        self, query: str, language: str = "fr"
    ) -> Dict[str, Any]:
        """
        Analyse et normalise une requête utilisateur avec détections enrichies

        Returns:
            {
                "normalized_query": str,
                "query_type": str,
                "entities": Dict,
                "routing": str,
                "confidence": float,
                "is_comparative": bool,
                "comparative_info": Dict,
                "requires_calculation": bool,
                "comparison_entities": List[Dict],
                "query_patterns": Dict  # NOUVEAU
            }
        """

        # 1. Détection comparative AVANT OpenAI
        comparative_info = self.comparative_detector.detect(query)
        logger.debug(f"Détection comparative: {comparative_info}")

        # 2. NOUVEAU: Détection des patterns spéciaux
        query_patterns = self._detect_query_patterns(query)
        logger.debug(f"Patterns détectés: {query_patterns}")

        # 3. Appel OpenAI pour normalisation et extraction d'entités
        system_prompt = self._get_system_prompt(
            language, comparative_info["is_comparative"]
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Validation
            if "normalized_query" not in result:
                logger.warning("Preprocessing incomplet, utilisation query originale")
                result["normalized_query"] = query

            if "entities" not in result:
                result["entities"] = {}

            # NOUVEAU: Validation et correction des entités OpenAI défaillantes
            result["entities"] = self._validate_and_fix_entities(result["entities"])
            logger.debug(f"Entités après validation: {result['entities']}")

            # 4. Enrichir avec les informations comparatives
            result["is_comparative"] = comparative_info["is_comparative"]
            result["comparative_info"] = comparative_info
            result["requires_calculation"] = comparative_info["is_comparative"]

            # 5. NOUVEAU: Ajouter les patterns détectés
            result["query_patterns"] = query_patterns

            # 6. Si comparaison détectée, créer les entités multiples
            if comparative_info["is_comparative"]:
                result["comparison_entities"] = self._build_comparison_entities(
                    result["entities"], comparative_info["entities"]
                )
                logger.info(
                    f"Requête comparative détectée: {comparative_info['type']}, "
                    f"{len(result['comparison_entities'])} jeux d'entités à rechercher"
                )

            logger.info(
                f"Query preprocessed: '{query}' -> '{result['normalized_query']}'"
            )
            logger.debug(f"Routing suggestion: {result.get('routing')}")
            logger.debug(f"Entities detected: {result['entities']}")
            logger.debug(f"Patterns: {query_patterns}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON OpenAI: {e}")
            return self._fallback_preprocessing(query, comparative_info, query_patterns)

        except Exception as e:
            logger.error(f"Erreur preprocessing OpenAI: {e}")
            return self._fallback_preprocessing(query, comparative_info, query_patterns)

    # ========================================================================
    # NOUVELLE MÉTHODE: Validation des entités OpenAI
    # ========================================================================

    def _validate_and_fix_entities(self, entities: Dict) -> Dict:
        """
        Nettoie les entités OpenAI défaillantes

        OpenAI peut générer des incohérences comme :
        - age_days: "as_hatched" (devrait être un nombre ou None)
        - breed: "as_hatched" (devrait être une souche ou None)
        - sex manquant ou invalide

        Args:
            entities: Dictionnaire d'entités brutes d'OpenAI

        Returns:
            Dictionnaire d'entités nettoyées et validées
        """
        cleaned_entities = entities.copy()

        # Correction age_days
        if cleaned_entities.get("age_days") == "as_hatched":
            cleaned_entities["age_days"] = None  # Plus clair que "as_hatched"
            logger.debug("Correction: age_days 'as_hatched' → None")

        # Validation age_days est un nombre valide
        if "age_days" in cleaned_entities and cleaned_entities["age_days"] is not None:
            try:
                age = cleaned_entities["age_days"]
                if isinstance(age, str):
                    # Tenter conversion string → int
                    if age.isdigit():
                        cleaned_entities["age_days"] = int(age)
                    else:
                        cleaned_entities["age_days"] = None
                        logger.warning(f"age_days invalide '{age}' → None")
                elif isinstance(age, (int, float)):
                    # Validation range
                    if not (0 <= age <= 150):
                        cleaned_entities["age_days"] = None
                        logger.warning(f"age_days hors range {age} → None")
                    else:
                        cleaned_entities["age_days"] = int(age)
            except (ValueError, TypeError):
                cleaned_entities["age_days"] = None
                logger.warning("age_days non convertible → None")

        # Correction breed
        if cleaned_entities.get("breed") == "as_hatched":
            cleaned_entities["breed"] = None
            logger.debug("Correction: breed 'as_hatched' → None")

        # Validation breed
        if "breed" in cleaned_entities and cleaned_entities["breed"]:
            breed = str(cleaned_entities["breed"]).strip()
            if not breed or breed.lower() in ["none", "null", ""]:
                cleaned_entities["breed"] = None

        # Assurer que sex a une valeur valide
        valid_sexes = ["male", "female", "as_hatched"]
        current_sex = cleaned_entities.get("sex")

        if not current_sex or current_sex not in valid_sexes:
            cleaned_entities["sex"] = "as_hatched"
            logger.debug(f"Correction: sex '{current_sex}' → 'as_hatched'")

        # Validation metric_type
        if "metric_type" in cleaned_entities and cleaned_entities["metric_type"]:
            metric = str(cleaned_entities["metric_type"]).strip()
            if not metric or metric.lower() in ["none", "null", ""]:
                cleaned_entities["metric_type"] = None

        # Log des corrections effectuées
        if cleaned_entities != entities:
            logger.info(f"Entités corrigées: {entities} → {cleaned_entities}")

        return cleaned_entities

    # ========================================================================
    # MÉTHODES CORRIGÉES: Détection de patterns spéciaux
    # ========================================================================

    def _detect_query_patterns(self, query: str) -> Dict[str, Any]:
        """
        Version corrigée avec patterns d'âge robustes

        Détecte les patterns spéciaux dans la requête

        Returns:
            {
                "is_calculation": bool,
                "is_temporal_reverse": bool,
                "is_optimization": bool,
                "is_economic": bool,
                "is_planning": bool,
                "extracted_age": int,
                "calculation_type": str,
                "flock_size": int,
                "target_value": float
            }
        """

        # NOUVEAUX patterns d'âge plus robustes
        age_patterns = [
            r"à\s+(\d+)\s+jours?",  # "à 42 jours"
            r"(\d+)\s+jours?",  # "42 jours"
            r"de\s+(\d+)\s+jours?",  # "de 42 jours"
            r"(\d+)\s*j\b",  # "42j"
            r"day\s+(\d+)",  # "day 42"
            r"(\d+)\s+days?",  # "42 days"
            r"(\d+)-?jours?",  # "42-jours"
            r"(\d+)\s+semaines?",  # "6 semaines" → *7
        ]

        query_lower = query.lower()
        extracted_age = None

        for pattern in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    # Conversion semaines → jours si nécessaire
                    if "semaine" in pattern:
                        age = age * 7
                    if 0 <= age <= 150:  # Validation range
                        extracted_age = age
                        logger.debug(
                            f"Age détecté: {age} jours via pattern '{pattern}'"
                        )
                        break
                except ValueError:
                    continue

        patterns = {
            "is_calculation": self._is_calculation_query(query_lower),
            "is_temporal_reverse": self._is_temporal_reverse_query(query_lower),
            "is_optimization": self._is_optimization_query(query_lower),
            "is_economic": self._is_economic_query(query_lower),
            "is_planning": self._is_planning_query(query_lower),
            "extracted_age": extracted_age,
        }

        # Extraire informations additionnelles
        if patterns["is_calculation"]:
            patterns["calculation_type"] = self._identify_calculation_type(query_lower)

        if patterns["is_planning"]:
            patterns["flock_size"] = self._extract_flock_size(query)

        if patterns["is_temporal_reverse"]:
            patterns["target_value"] = self._extract_target_value(query)

        return patterns

    def _is_calculation_query(self, query_lower: str) -> bool:
        """Détecte requêtes nécessitant des calculs"""
        calculation_keywords = [
            "projette",
            "projection",
            "calcul",
            "calculer",
            "total",
            "totaux",
            "somme",
            "entre",
            "de X à Y",
            "from X to Y",
            "combien",
            "how much",
            "how many",
        ]
        return any(keyword in query_lower for keyword in calculation_keywords)

    def _is_temporal_reverse_query(self, query_lower: str) -> bool:
        """Détecte requêtes de recherche inversée (valeur → âge)"""
        reverse_patterns = [
            "quel âge",
            "à quel âge",
            "combien de jours",
            "quand atteint",
            "when reach",
            "at what age",
            "pour atteindre",
            "to reach",
        ]
        return any(pattern in query_lower for pattern in reverse_patterns)

    def _is_optimization_query(self, query_lower: str) -> bool:
        """Détecte requêtes d'optimisation"""
        optimization_keywords = [
            "optimal",
            "optimis",
            "meilleur",
            "best",
            "maximis",
            "minimis",
            "maximize",
            "minimize",
            "idéal",
            "ideal",
        ]
        return any(keyword in query_lower for keyword in optimization_keywords)

    def _is_economic_query(self, query_lower: str) -> bool:
        """Détecte requêtes économiques"""
        economic_keywords = [
            "coût",
            "cout",
            "cost",
            "prix",
            "price",
            "rentabilité",
            "rentabilite",
            "profitability",
            "marge",
            "margin",
            "roi",
            "€",
            "$",
            "dollar",
            "euro",
        ]
        return any(keyword in query_lower for keyword in economic_keywords)

    def _is_planning_query(self, query_lower: str) -> bool:
        """Détecte requêtes de planification de troupeau"""
        planning_patterns = [
            r"\d+[\s,]?\d{3}.*poulet",
            r"\d+[\s,]?\d{3}.*bird",
            r"pour \d+.*oiseaux",
            r"for \d+.*chickens",
        ]
        return any(re.search(pattern, query_lower) for pattern in planning_patterns)

    def _identify_calculation_type(self, query_lower: str) -> str:
        """Identifie le type de calcul demandé"""
        if "projection" in query_lower or "projette" in query_lower:
            return "projection"
        elif "total" in query_lower or "somme" in query_lower:
            return "total"
        elif "entre" in query_lower or "from" in query_lower:
            return "range_calculation"
        elif "taux" in query_lower or "rate" in query_lower:
            return "rate_calculation"
        else:
            return "general_calculation"

    def _extract_flock_size(self, query: str) -> Optional[int]:
        """Extrait la taille du troupeau"""
        numbers = re.findall(r"\b(\d{1,3}(?:[,\s]\d{3})*|\d+)\b", query)
        for num_str in numbers:
            num = int(num_str.replace(",", "").replace(" ", ""))
            if num > 100:  # Probablement taille de troupeau
                return num
        return None

    def _extract_target_value(self, query: str) -> Optional[float]:
        """Extrait valeur cible pour recherche inversée"""
        # Chercher patterns comme "2000g", "3kg", "1.5"
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:kg|g|grammes?|kilos?)",
            r"(\d+(?:\.\d+)?)\s*(?=\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    # ========================================================================
    # MÉTHODE CORRIGÉE: Construction des entités de comparaison
    # ========================================================================

    def _build_comparison_entities(
        self, base_entities: Dict[str, Any], comparative_entities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Construire des entités multiples pour comparaisons

        Construit les différents jeux d'entités pour chaque comparaison

        Exemple:
        Si base_entities = {'breed': 'Cobb 500', 'age_days': 17}
        Et comparative_entities = [{'dimension': 'sex', 'values': ['male', 'female']}]

        Returns:
        [
            {'breed': 'Cobb 500', 'sex': 'male', 'age_days': 17, '_comparison_label': 'male'},
            {'breed': 'Cobb 500', 'sex': 'female', 'age_days': 17, '_comparison_label': 'female'}
        ]
        """

        if not comparative_entities:
            return [base_entities]

        comparison_sets = []

        # Cas 1: Comparaison de sexes (mâle vs femelle)
        if any(entity.get("dimension") == "sex" for entity in comparative_entities):
            for sex in ["male", "female"]:
                entity_set = base_entities.copy()
                entity_set["sex"] = sex
                entity_set["_comparison_label"] = sex
                entity_set["_comparison_dimension"] = "sex"
                comparison_sets.append(entity_set)

        # Cas 2: Comparaison de souches (Ross vs Cobb)
        elif any(entity.get("dimension") == "breed" for entity in comparative_entities):
            breeds = []
            for entity in comparative_entities:
                if entity.get("dimension") == "breed":
                    breeds.extend(entity.get("values", []))

            for breed in breeds:
                entity_set = base_entities.copy()
                entity_set["breed"] = breed
                entity_set["_comparison_label"] = breed
                entity_set["_comparison_dimension"] = "breed"
                comparison_sets.append(entity_set)

        # Cas 3: Comparaison d'âges
        elif any(entity.get("dimension") == "age" for entity in comparative_entities):
            ages = []
            for entity in comparative_entities:
                if entity.get("dimension") == "age":
                    ages.extend(entity.get("values", []))

            for age in ages:
                entity_set = base_entities.copy()
                entity_set["age_days"] = age
                entity_set["_comparison_label"] = str(age)
                entity_set["_comparison_dimension"] = "age"
                comparison_sets.append(entity_set)

        # Cas 4: Gestion des entités dans base_entities (format "value1, value2")
        else:
            # Vérifier si les entités de base contiennent des comparaisons
            for key, value in base_entities.items():
                if isinstance(value, str) and "," in value:
                    values = [v.strip() for v in value.split(",")]
                    if len(values) > 1:
                        for val in values:
                            entity_set = base_entities.copy()
                            entity_set[key] = val
                            entity_set["_comparison_label"] = val
                            entity_set["_comparison_dimension"] = key
                            comparison_sets.append(entity_set)
                        break

        logger.debug(f"Entités de comparaison construites: {len(comparison_sets)} sets")
        return comparison_sets if comparison_sets else [base_entities]

    # ========================================================================
    # MÉTHODE CORRIGÉE: Prompts système améliorés
    # ========================================================================

    def _get_system_prompt(self, language: str, is_comparative: bool) -> str:
        """Prompts spécialisés selon le type de requête"""

        comparative_instructions = ""
        if is_comparative:
            comparative_instructions = """
ATTENTION: Cette requête demande une COMPARAISON ou un CALCUL.
- Extrais TOUTES les valeurs à comparer (ex: mâle ET femelle, Ross ET Cobb)
- Identifie les dimensions de comparaison (sexe, âge, souche)
- Pour "Ross 308 vs Cobb 500" → breed: "Ross 308, Cobb 500"
- Pour "mâle vs femelle" → sex: "male, female"  
- Pour "21 jours vs 42 jours" → age_days: "21, 42"
- Ne privilégie pas une valeur par rapport à l'autre
"""

        if language == "fr":
            return f"""Tu es un assistant expert en aviculture qui normalise les requêtes utilisateur.

{comparative_instructions}

Tâches:
1. Corriger les fautes de frappe et orthographe
2. Normaliser la terminologie avicole (ex: "conversion aliment" → "conversion alimentaire")
3. Extraire les entités structurées:
   - breed: race/souche (ex: "Cobb 500", "Ross 308", "Cobb 500, Ross 308" pour comparaisons)
   - sex: sexe ("male", "female", "male, female" pour comparaisons, ou "as_hatched" si non spécifié)
   - age_days: âge en jours (nombre entier ou "21, 42" pour comparaisons)
   - metric_type: type de métrique (ex: "feed_conversion", "body_weight", "mortality")
4. Suggérer le routage optimal:
   - "postgresql" pour métriques chiffrées
   - "weaviate" pour documents/guides
5. Déterminer le type de requête:
   - "metric" pour données chiffrées
   - "document" pour guides/docs
   - "general" pour questions générales

IMPORTANT: 
- Si le sexe n'est PAS explicitement mentionné, utiliser "as_hatched"
- Pour les comparaisons, extraire TOUTES les entités mentionnées
- Pour "à 42 jours", extraire age_days: 42
- Pour "Ross vs Cobb", extraire breed: "Ross 308, Cobb 500"

Réponds en JSON:
{{
    "normalized_query": "requête corrigée",
    "query_type": "metric|document|general",
    "entities": {{
        "breed": "...",
        "sex": "male|female|as_hatched|male, female",
        "age_days": 17,
        "metric_type": "..."
    }},
    "routing": "postgresql|weaviate",
    "confidence": 0.95
}}"""

        else:  # English
            return f"""You are a poultry expert assistant that normalizes user queries.

{comparative_instructions}

Tasks:
1. Fix typos and spelling errors
2. Normalize poultry terminology
3. Extract structured entities:
   - breed: breed/strain name (ex: "Cobb 500, Ross 308" for comparisons)
   - sex: "male", "female", "male, female" for comparisons, or "as_hatched" if not specified
   - age_days: age in days (integer or "21, 42" for comparisons)
   - metric_type: metric type
4. Suggest optimal routing:
   - "postgresql" for numeric metrics
   - "weaviate" for documents/guides
5. Determine query type

IMPORTANT:
- If sex is NOT explicitly mentioned, use "as_hatched"
- For comparisons, extract ALL mentioned entities
- For "at 42 days", extract age_days: 42
- For "Ross vs Cobb", extract breed: "Ross 308, Cobb 500"

Respond in JSON:
{{
    "normalized_query": "corrected query",
    "query_type": "metric|document|general",
    "entities": {{...}},
    "routing": "postgresql|weaviate",
    "confidence": 0.95
}}"""

    def _fallback_preprocessing(
        self, query: str, comparative_info: Dict, query_patterns: Dict
    ) -> Dict[str, Any]:
        """Preprocessing de secours en cas d'erreur OpenAI"""
        logger.warning("Utilisation du preprocessing de secours")

        return {
            "normalized_query": query,
            "query_type": "general",
            "entities": self._validate_and_fix_entities({"sex": "as_hatched"}),
            "routing": "weaviate",
            "confidence": 0.3,
            "is_comparative": comparative_info["is_comparative"],
            "comparative_info": comparative_info,
            "requires_calculation": comparative_info["is_comparative"],
            "comparison_entities": [],
            "query_patterns": query_patterns,
            "preprocessing_fallback": True,
        }

    def get_status(self) -> Dict[str, Any]:
        """Status du preprocessor"""
        return {
            "initialized": self._is_initialized,
            "comparative_detection": True,
            "pattern_detection": True,
            "supported_comparisons": list(
                self.comparative_detector.COMPARATIVE_PATTERNS.keys()
            ),
            "supported_patterns": [
                "calculation",
                "temporal_reverse",
                "optimization",
                "economic",
                "planning",
            ],
            "client_available": self.client is not None,
        }
