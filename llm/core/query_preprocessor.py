# -*- coding: utf-8 -*-
"""
query_preprocessor.py - Préprocesseur de requêtes avec OpenAI
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
    """

    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self._is_initialized = False

    async def initialize(self):
        """Initialisation et validation du preprocessor"""
        if not self.client:
            raise ValueError("OpenAI client is required for QueryPreprocessor")

        # Test de connexion optionnel
        try:
            # Vérifier que le client est fonctionnel avec un petit test
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
        # Rien d'autre à nettoyer car le client OpenAI est géré ailleurs

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
                model="gpt-4o-mini",  # Version rapide et économique
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Validation du format de réponse
            if "normalized_query" not in result:
                logger.warning("Preprocessing incomplet, utilisation query originale")
                result["normalized_query"] = query

            return result

        except Exception as e:
            logger.error(f"Erreur preprocessing query: {e}")
            # Fallback : retourner la query originale
            return {
                "normalized_query": query,
                "query_type": "general",
                "entities": {},
                "routing": "weaviate",
                "confidence": 0.5,
                "error": str(e),
            }

    def _get_system_prompt(self, language: str) -> str:
        return f"""Tu es un expert en analyse de requêtes avicoles. Ton rôle est de :

1. **Corriger les fautes** : "conversation alimentaire" → "conversion alimentaire"
2. **Normaliser la terminologie** : 
   - Poids corporel = body_weight = live_weight = peso corporal
   - Conversion alimentaire = feed_conversion = FCR = cum feed conversion = indice de consommation
   - Mortalité = mortality = mortalidad
3. **Extraire les entités** :
   - Race : Cobb 500, Ross 308, Hubbard, ISA Brown, etc.
   - Sexe : male, female, as_hatched (si non spécifié)
   - Âge : en jours (convertir semaines en jours si nécessaire)
   - Type de métrique : body_weight, feed_conversion, mortality, feed_intake, etc.

4. **Déterminer le routage** :
   - **postgresql** : Requêtes sur des métriques chiffrées à un âge précis
     Exemples : "poids à 17 jours", "FCR semaine 3", "mortalité jour 10"
   
   - **weaviate** : Requêtes sur des concepts, recommandations, explications
     Exemples : "comment améliorer la conversion", "recommandations nutritionnelles", "gestion de la température"

5. **Répondre en JSON** avec cette structure exacte :
{{
    "normalized_query": "requête corrigée et normalisée",
    "query_type": "metric|document|general",
    "entities": {{
        "breed": "nom de la race si détecté",
        "sex": "male|female|as_hatched",
        "age_days": nombre de jours,
        "metric_type": "body_weight|feed_conversion|mortality|etc"
    }},
    "routing": "postgresql|weaviate",
    "confidence": 0.0 à 1.0
}}

IMPORTANT : 
- Si tu détectes une faute de frappe évidente, corrige-la dans normalized_query
- Si l'âge est en semaines, convertis en jours (1 semaine = 7 jours)
- Si aucune race n'est mentionnée, n'ajoute pas le champ breed
- La confidence doit refléter ta certitude dans l'analyse

Langue de sortie pour normalized_query : {language}"""

    def _extract_age_from_query(self, query: str) -> int:
        """Fallback : extraction d'âge par regex si OpenAI échoue"""
        patterns = [
            r"(\d+)\s*jour",
            r"(\d+)\s*day",
            r"jour\s*(\d+)",
            r"semaine\s*(\d+)",
            r"week\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                age = int(match.group(1))
                # Convertir semaines en jours si pattern de semaine
                if "semaine" in pattern or "week" in pattern:
                    age *= 7
                return age

        return None
