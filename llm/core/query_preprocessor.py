# -*- coding: utf-8 -*-
"""
query_preprocessor.py - Préprocesseur de requêtes avec OpenAI
Version améliorée avec gestion correcte du sexe (as_hatched par défaut)
"""

import logging
from openai import AsyncOpenAI
import json
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """
    Préprocesse les requêtes utilisateur avec OpenAI pour :
    - Corriger les fautes de frappe
    - Normaliser la terminologie
    - Extraire les métadonnées structurées
    - Déterminer le type de requête
    - Gérer correctement le sexe (as_hatched par défaut si non spécifié)
    """

    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self._is_initialized = False

    async def initialize(self):
        """Initialisation et validation du preprocessor"""
        if not self.client:
            raise ValueError("OpenAI client is required for QueryPreprocessor")

        try:
            logger.info("Initialisation du Query Preprocessor...")
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
        Analyse et normalise une requête utilisateur

        Returns:
            {
                "normalized_query": str,  # Requête corrigée
                "query_type": str,        # "metric" | "document" | "general"
                "entities": {
                    "breed": str,         # Ex: "Cobb 500"
                    "sex": str,           # "male" | "female" | "as_hatched"
                    "age_days": int,      # Ex: 17
                    "metric_type": str    # Ex: "feed_conversion", "body_weight"
                },
                "routing": str,           # "postgresql" | "weaviate"
                "confidence": float       # 0-1
            }
        """

        system_prompt = self._get_system_prompt(language)

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

            # Validation et nettoyage du format de réponse
            if "normalized_query" not in result:
                logger.warning("Preprocessing incomplet, utilisation query originale")
                result["normalized_query"] = query

            # CRITIQUE: Assurer que 'sex' est toujours présent dans entities
            if "entities" not in result:
                result["entities"] = {}

            if "sex" not in result["entities"]:
                logger.debug(
                    "Aucun sexe détecté par OpenAI, utilisation as_hatched par défaut"
                )
                result["entities"]["sex"] = "as_hatched"

            # Validation que le sexe est valide
            valid_sexes = ["male", "female", "as_hatched"]
            if result["entities"]["sex"] not in valid_sexes:
                logger.warning(
                    f"Sexe invalide '{result['entities']['sex']}', correction vers as_hatched"
                )
                result["entities"]["sex"] = "as_hatched"

            logger.debug(
                f"Preprocessing terminé - Sex: {result['entities'].get('sex', 'as_hatched')}"
            )

            return result

        except Exception as e:
            logger.error(f"Erreur preprocessing query: {e}")
            # Fallback : retourner la query originale avec as_hatched par défaut
            return {
                "normalized_query": query,
                "query_type": "general",
                "entities": {"sex": "as_hatched"},  # Valeur par défaut explicite
                "routing": "weaviate",
                "confidence": 0.5,
                "error": str(e),
            }

    def _get_system_prompt(self, language: str) -> str:
        return f"""Tu es un expert en analyse de requêtes avicoles. Ton rôle est de :

1. **Corriger les fautes** : "conversation alimentaire" → "conversion alimentaire"
   Autres exemples courants :
   - "poid" → "poids"
   - "mortaliter" → "mortalité"
   - "consomation" → "consommation"
   - "Ros 308" → "Ross 308"

2. **Normaliser la terminologie** : 
   - Poids corporel = body_weight = live_weight = peso corporal
   - Conversion alimentaire = feed_conversion = FCR = cum feed conversion = indice de consommation = IC
   - Mortalité = mortality = mortalidad
   - Consommation alimentaire = feed intake = feed consumption = consommation d'aliment

3. **Extraire les entités** :
   - Race : Cobb 500, Ross 308, Ross 708, Hubbard, ISA Brown, Lohmann, etc.
   - Sexe : RÈGLES CRITIQUES
     * Si la requête mentionne explicitement : "mâle", "male", "masculin", "coq" → "male"
     * Si la requête mentionne explicitement : "femelle", "female", "féminin", "poule" → "female"
     * Si AUCUNE mention explicite du sexe → "as_hatched" (VALEUR PAR DÉFAUT - le cas le plus fréquent)
     * Le champ "sex" est OBLIGATOIRE dans toutes les réponses
   - Âge : en jours (convertir semaines en jours si nécessaire : 1 semaine = 7 jours)
   - Type de métrique : body_weight, feed_conversion, mortality, feed_intake, fcr, etc.

4. **Déterminer le routage** :
   - **postgresql** : Requêtes sur des métriques chiffrées à un âge précis
     Exemples : "poids à 17 jours", "FCR semaine 3", "mortalité jour 10", "conversion alimentaire jour 27"
   
   - **weaviate** : Requêtes sur des concepts, recommandations, explications
     Exemples : "comment améliorer la conversion", "recommandations nutritionnelles", "gestion de la température"

5. **Répondre en JSON** avec cette structure exacte :
{{
    "normalized_query": "requête corrigée et normalisée",
    "query_type": "metric|document|general",
    "entities": {{
        "breed": "nom de la race si détecté (optionnel)",
        "sex": "male|female|as_hatched",  // OBLIGATOIRE - toujours inclure
        "age_days": nombre de jours (optionnel),
        "metric_type": "body_weight|feed_conversion|mortality|etc (optionnel)"
    }},
    "routing": "postgresql|weaviate",
    "confidence": 0.0 à 1.0
}}

RÈGLES CRITIQUES :
- Le champ "sex" dans entities est OBLIGATOIRE dans chaque réponse
- Par défaut, si aucun sexe n'est mentionné explicitement → "as_hatched"
- Ne devine JAMAIS le sexe s'il n'est pas explicitement mentionné
- Exemples où le sexe N'est PAS mentionné :
  * "Quelle est la conversion d'un poulet Cobb 500 ?" → sex: "as_hatched"
  * "Poids Ross 308 à 17 jours" → sex: "as_hatched"
  * "FCR du broiler au jour 27" → sex: "as_hatched"
- Exemples où le sexe EST mentionné :
  * "Quelle est la conversion d'un poulet mâle Cobb 500 ?" → sex: "male"
  * "Poids femelle Ross 308 à 17 jours" → sex: "female"

IMPORTANT : 
- Si tu détectes une faute de frappe évidente, corrige-la dans normalized_query
- Si l'âge est en semaines, convertis en jours (1 semaine = 7 jours)
- Si aucune race n'est mentionnée, n'ajoute pas le champ breed aux entities
- La confidence doit refléter ta certitude dans l'analyse (0.0 à 1.0)
- Sois conservateur sur le sexe : en cas de doute, utilise "as_hatched"

Langue de sortie pour normalized_query : {language}"""

    def _extract_age_from_query(self, query: str) -> int:
        """Fallback : extraction d'âge par regex si OpenAI échoue"""
        patterns = [
            (r"(\d+)\s*jour", 1),  # "27 jours" ou "jour 27"
            (r"jour\s*(\d+)", 1),
            (r"(\d+)\s*day", 1),  # "27 days" ou "day 27"
            (r"day\s*(\d+)", 1),
            (r"semaine\s*(\d+)", 7),  # "semaine 4" → 28 jours
            (r"(\d+)\s*semaine", 7),
            (r"week\s*(\d+)", 7),  # "week 4" → 28 jours
            (r"(\d+)\s*week", 7),
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, query.lower())
            if match:
                age = int(match.group(1)) * multiplier
                logger.debug(f"Âge extrait par regex: {age} jours (pattern: {pattern})")
                return age

        return None

    def _extract_sex_fallback(self, query: str) -> str:
        """
        Fallback : extraction du sexe par regex si OpenAI échoue
        Retourne toujours "as_hatched" sauf si mention explicite
        """
        query_lower = query.lower()

        # Patterns explicites pour male
        male_patterns = [
            r"\bmâle\b",
            r"\bmale\b",
            r"\bmasculin\b",
            r"\bcoq\b",
            r"\bmâles\b",
            r"\bmales\b",
        ]
        if any(re.search(pattern, query_lower) for pattern in male_patterns):
            logger.debug("Sexe détecté par regex fallback: male")
            return "male"

        # Patterns explicites pour female
        female_patterns = [
            r"\bfemelle\b",
            r"\bfemale\b",
            r"\bféminin\b",
            r"\bpoule\b",
            r"\bfemelles\b",
            r"\bfemales\b",
        ]
        if any(re.search(pattern, query_lower) for pattern in female_patterns):
            logger.debug("Sexe détecté par regex fallback: female")
            return "female"

        # Aucun sexe explicite détecté
        logger.debug("Aucun sexe explicite détecté par regex, retour as_hatched")
        return "as_hatched"
