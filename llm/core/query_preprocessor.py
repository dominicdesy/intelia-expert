from openai import AsyncOpenAI
import json
from typing import Dict, Any
import re


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

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # Version de base, rapide et économique
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return result

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

5. **Format de réponse** (JSON strict) :
{{
  "normalized_query": "Quelle est la conversion alimentaire d'un Cobb 500 mâle à 17 jours ?",
  "query_type": "metric",
  "entities": {{
    "breed": "Cobb 500",
    "sex": "male",
    "age_days": 17,
    "metric_type": "feed_conversion"
  }},
  "routing": "postgresql",
  "confidence": 0.95,
  "corrections_applied": ["conversation → conversion"]
}}

**IMPORTANT** :
- Si l'âge n'est pas spécifié, ne pas inventer de valeur
- Si le sexe n'est pas mentionné, utiliser "as_hatched"
- Toujours corriger les fautes courantes
- Répondre UNIQUEMENT en JSON valide
- Langue de réponse : {language}"""

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
