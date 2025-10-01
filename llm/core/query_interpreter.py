# -*- coding: utf-8 -*-
"""
query_interpreter.py - Interprétation intelligente des requêtes via OpenAI
"""

import logging
from typing import Dict, Optional
from openai import AsyncOpenAI
import os

logger = logging.getLogger(__name__)


class QueryInterpreter:
    """Interprète les requêtes utilisateur avec OpenAI pour extraction précise"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def interpret_query(self, query: str) -> Dict[str, any]:
        """
        Utilise OpenAI pour interpréter précisément la requête
        
        Returns:
            {
                "metric": "feed_conversion_ratio" | "cumulative_feed_intake" | ...,
                "breed": "Ross 308",
                "age_days": 31,
                "sex": "male",
                "confidence": 0.95
            }
        """
        
        system_prompt = """Tu es un expert en aviculture qui extrait les informations précises des requêtes.

MÉTRIQUES POSSIBLES (IMPORTANT - ne confonds JAMAIS) :
- feed_conversion_ratio (FCR, indice de conversion, conversion alimentaire)
- cumulative_feed_intake (consommation cumulée, total feed intake)
- body_weight (poids vif, body weight)
- daily_gain (gain quotidien)
- mortality (mortalité)

RÈGLES CRITIQUES :
1. "feed conversion ratio", "FCR", "indice de conversion" → feed_conversion_ratio
2. "feed intake", "consommation", "total feed" → cumulative_feed_intake
3. Si la requête mentionne "conversion" ou "ratio" → TOUJOURS feed_conversion_ratio
4. Si la requête mentionne uniquement "intake" ou "consommation" → cumulative_feed_intake

Réponds en JSON :
{
  "metric": "nom_métrique",
  "breed": "nom_race",
  "age_days": nombre,
  "sex": "male|female|as_hatched",
  "confidence": 0.0-1.0
}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,  # Très bas pour cohérence
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ OpenAI interprétation: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur interprétation OpenAI: {e}")
            return {}