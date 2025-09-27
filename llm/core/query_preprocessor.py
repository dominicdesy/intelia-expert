# -*- coding: utf-8 -*-
"""
query_preprocessor.py - Préprocesseur de requêtes avec OpenAI
Version modulaire utilisant ComparativeQueryDetector
"""

import logging
from openai import AsyncOpenAI
import json
from typing import Dict, Any, List

# Import du détecteur comparatif
from .comparative_detector import ComparativeQueryDetector

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """
    Préprocesse les requêtes utilisateur avec :
    - Correction des fautes de frappe
    - Normalisation de la terminologie
    - Extraction des métadonnées structurées
    - Détection des requêtes comparatives (via ComparativeQueryDetector)
    - Gestion correcte du sexe (as_hatched par défaut si non spécifié)
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
                "Initialisation du Query Preprocessor avec support comparatif..."
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
        Analyse et normalise une requête utilisateur avec détection comparative

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
                "comparison_entities": List[Dict]  # Si comparatif
            }
        """

        # 1. Détection comparative AVANT OpenAI (économie de tokens)
        comparative_info = self.comparative_detector.detect(query)
        logger.debug(f"Détection comparative: {comparative_info}")

        # 2. Appel OpenAI pour normalisation et extraction d'entités
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

            # Garantir as_hatched par défaut si sexe non spécifié
            if "sex" not in result["entities"] or not result["entities"]["sex"]:
                result["entities"]["sex"] = "as_hatched"
                logger.debug("Sexe non spécifié → as_hatched par défaut")

            # 3. Enrichir avec les informations comparatives
            result["is_comparative"] = comparative_info["is_comparative"]
            result["comparative_info"] = comparative_info
            result["requires_calculation"] = comparative_info["is_comparative"]

            # 4. Si comparaison détectée, créer les entités multiples
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

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON OpenAI: {e}")
            return self._fallback_preprocessing(query, comparative_info)

        except Exception as e:
            logger.error(f"Erreur preprocessing OpenAI: {e}")
            return self._fallback_preprocessing(query, comparative_info)

    def _build_comparison_entities(
        self, base_entities: Dict[str, Any], comparative_entities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
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

        entity_sets = []

        # Pour l'instant, on gère une seule dimension de comparaison
        # TODO: Support multi-dimensionnel (ex: mâle vs femelle ET 17j vs 21j)
        comparison_dimension = comparative_entities[0]
        dimension_name = comparison_dimension["dimension"]

        for value in comparison_dimension["values"]:
            entity_set = base_entities.copy()
            entity_set[dimension_name] = value
            entity_set["_comparison_label"] = str(value)
            entity_set["_comparison_dimension"] = dimension_name
            entity_sets.append(entity_set)

        logger.debug(f"Construit {len(entity_sets)} jeux d'entités pour comparaison")
        return entity_sets

    def _get_system_prompt(self, language: str, is_comparative: bool) -> str:
        """Génère le prompt système avec support comparatif"""

        comparative_instructions = ""
        if is_comparative:
            comparative_instructions = """
ATTENTION: Cette requête demande une COMPARAISON ou un CALCUL.
- Extrais TOUTES les valeurs à comparer (ex: mâle ET femelle)
- Identifie les dimensions de comparaison (sexe, âge, souche)
- Ne privilégie pas une valeur par rapport à l'autre
"""

        if language == "fr":
            return f"""Tu es un assistant expert en aviculture qui normalise les requêtes utilisateur.

{comparative_instructions}

Tâches:
1. Corriger les fautes de frappe et orthographe
2. Normaliser la terminologie avicole (ex: "conversion aliment" → "conversion alimentaire")
3. Extraire les entités structurées:
   - breed: race/souche (ex: "Cobb 500", "Ross 308")
   - sex: sexe ("male", "female", ou "as_hatched" si non spécifié)
   - age_days: âge en jours (nombre entier)
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

Réponds en JSON:
{{
    "normalized_query": "requête corrigée",
    "query_type": "metric|document|general",
    "entities": {{
        "breed": "...",
        "sex": "male|female|as_hatched",
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
   - breed: breed/strain name
   - sex: "male", "female", or "as_hatched" if not specified
   - age_days: age in days (integer)
   - metric_type: metric type
4. Suggest optimal routing:
   - "postgresql" for numeric metrics
   - "weaviate" for documents/guides
5. Determine query type

IMPORTANT:
- If sex is NOT explicitly mentioned, use "as_hatched"
- For comparisons, extract ALL mentioned entities

Respond in JSON:
{{
    "normalized_query": "corrected query",
    "query_type": "metric|document|general",
    "entities": {{...}},
    "routing": "postgresql|weaviate",
    "confidence": 0.95
}}"""

    def _fallback_preprocessing(
        self, query: str, comparative_info: Dict
    ) -> Dict[str, Any]:
        """Preprocessing de secours en cas d'erreur OpenAI"""
        logger.warning("Utilisation du preprocessing de secours")

        return {
            "normalized_query": query,
            "query_type": "general",
            "entities": {"sex": "as_hatched"},
            "routing": "weaviate",
            "confidence": 0.3,
            "is_comparative": comparative_info["is_comparative"],
            "comparative_info": comparative_info,
            "requires_calculation": comparative_info["is_comparative"],
            "comparison_entities": [],
            "preprocessing_fallback": True,
        }

    def get_status(self) -> Dict[str, Any]:
        """Status du preprocessor"""
        return {
            "initialized": self._is_initialized,
            "comparative_detection": True,
            "supported_comparisons": list(
                self.comparative_detector.COMPARATIVE_PATTERNS.keys()
            ),
            "client_available": self.client is not None,
        }


# Fonction utilitaire pour tests
async def test_comparative_detection():
    """Test de la détection comparative sans OpenAI"""
    detector = ComparativeQueryDetector()

    test_queries = [
        "Quelle est la différence de FCR entre un Cobb 500 mâle et femelle de 17 jours ?",
        "Compare le poids vif mâle vs femelle à 21 jours",
        "FCR du Cobb 500 mâle à 17 jours",  # Non comparatif
    ]

    for query in test_queries:
        result = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Comparative: {result['is_comparative']}")
        if result["is_comparative"]:
            print(f"Type: {result['type']}")
            print(f"Entities: {result['entities']}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_comparative_detection())
