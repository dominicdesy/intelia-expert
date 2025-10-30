"""
Compass Extension for RAG - Real-time barn data integration
Version: 1.0.0
Date: 2025-10-30
Description: Extension to integrate Compass barn data into RAG responses
"""

import logging
import os
import re
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CompassBarnInfo:
    """Compass barn information for context enrichment"""
    barn_number: str
    barn_name: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    average_weight: Optional[float] = None  # grams
    age_days: Optional[int] = None
    has_data: bool = False
    error: Optional[str] = None

    def to_context_string(self) -> str:
        """Convert barn info to natural language context"""
        if not self.has_data:
            return f"Données non disponibles pour le poulailler {self.barn_number}"

        parts = [f"Poulailler {self.barn_number} ({self.barn_name}):"]

        if self.temperature is not None:
            parts.append(f"- Température: {self.temperature}°C")

        if self.humidity is not None:
            parts.append(f"- Humidité: {self.humidity}%")

        if self.average_weight is not None:
            parts.append(f"- Poids moyen: {self.average_weight:.0f}g")

        if self.age_days is not None:
            parts.append(f"- Âge du troupeau: {self.age_days} jours")

        return "\n".join(parts)


class CompassExtension:
    """
    Compass Extension for RAG system

    Detects queries about barn conditions and enriches context with real-time data
    """

    # Keywords that trigger Compass integration
    BARN_KEYWORDS = [
        "poulailler", "poulaillers", "barn", "barns", "bâtiment", "batiment",
        "étable", "stable"
    ]

    DATA_TYPE_KEYWORDS = {
        "temperature": ["température", "temp", "temperature", "chaleur", "froid"],
        "humidity": ["humidité", "humidity", "humid", "taux d'humidité"],
        "weight": ["poids", "weight", "masse", "grammes", "kg"],
        "age": ["âge", "age", "jours", "days", "troupeau"]
    }

    def __init__(self, backend_url: Optional[str] = None):
        """
        Initialize Compass extension

        Args:
            backend_url: Backend API URL (defaults to localhost or env var)
        """
        self.backend_url = backend_url or os.getenv("BACKEND_URL", "http://localhost:8000")
        self.enabled = os.getenv("COMPASS_ENABLED", "true").lower() == "true"

        if self.enabled:
            logger.info(f"Compass extension initialized (backend: {self.backend_url})")
        else:
            logger.info("Compass extension disabled (COMPASS_ENABLED=false)")

    def is_compass_query(self, query: str) -> bool:
        """
        Check if query is about barn conditions

        Args:
            query: User query

        Returns:
            True if query mentions barns and data types
        """
        if not self.enabled:
            return False

        query_lower = query.lower()

        # Must mention a barn
        has_barn = any(keyword in query_lower for keyword in self.BARN_KEYWORDS)
        if not has_barn:
            return False

        # Must mention a data type or be asking about conditions
        has_data_type = any(
            any(kw in query_lower for kw in keywords)
            for keywords in self.DATA_TYPE_KEYWORDS.values()
        )

        # Or asking about current conditions
        condition_words = ["actuel", "current", "maintenant", "now", "combien", "quelle"]
        has_condition_query = any(word in query_lower for word in condition_words)

        return has_data_type or has_condition_query

    def extract_barn_numbers(self, query: str) -> List[str]:
        """
        Extract barn numbers from query

        Args:
            query: User query

        Returns:
            List of barn numbers (as strings)

        Examples:
            "température poulailler 2" -> ["2"]
            "poulaillers 1 et 3" -> ["1", "3"]
            "mon poulailler" -> [] (will need default/all barns)
        """
        # Match patterns like "poulailler 2", "barn 3", "numéro 1"
        patterns = [
            r'poulailler\s+(\d+)',
            r'barn\s+(\d+)',
            r'bâtiment\s+(\d+)',
            r'batiment\s+(\d+)',
            r'numéro\s+(\d+)',
            r'number\s+(\d+)',
            r'#(\d+)',
        ]

        barn_numbers = []
        query_lower = query.lower()

        for pattern in patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                barn_numbers.append(match.group(1))

        # Remove duplicates while preserving order
        return list(dict.fromkeys(barn_numbers))

    def detect_data_types(self, query: str) -> List[str]:
        """
        Detect which data types are requested

        Args:
            query: User query

        Returns:
            List of data types: ["temperature", "humidity", "weight", "age"]
        """
        query_lower = query.lower()
        requested_types = []

        for data_type, keywords in self.DATA_TYPE_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                requested_types.append(data_type)

        # If no specific type requested, return all
        if not requested_types:
            requested_types = ["temperature", "humidity", "weight", "age"]

        return requested_types

    async def fetch_barn_data(
        self,
        user_token: str,
        barn_number: Optional[str] = None
    ) -> List[CompassBarnInfo]:
        """
        Fetch barn data from backend API

        Args:
            user_token: User's JWT token
            barn_number: Specific barn number (if None, fetch all)

        Returns:
            List of CompassBarnInfo objects
        """
        headers = {"Authorization": f"Bearer {user_token}"}

        try:
            if barn_number:
                # Fetch specific barn
                url = f"{self.backend_url}/api/v1/compass/me/barns/{barn_number}"
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    return [self._parse_barn_data(data)]
                else:
                    logger.warning(f"Failed to fetch barn {barn_number}: {response.status_code}")
                    return [CompassBarnInfo(
                        barn_number=barn_number,
                        barn_name=f"Poulailler {barn_number}",
                        error=f"Données non disponibles (code {response.status_code})"
                    )]

            else:
                # Fetch all barns
                url = f"{self.backend_url}/api/v1/compass/me/barns"
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    barns_data = response.json()
                    return [self._parse_barn_data(barn) for barn in barns_data]
                else:
                    logger.warning(f"Failed to fetch barns: {response.status_code}")
                    return []

        except requests.exceptions.Timeout:
            logger.error("Compass API timeout")
            return [CompassBarnInfo(
                barn_number=barn_number or "?",
                barn_name="Poulailler",
                error="Délai d'attente dépassé"
            )]
        except requests.exceptions.RequestException as e:
            logger.error(f"Compass API error: {e}")
            return [CompassBarnInfo(
                barn_number=barn_number or "?",
                barn_name="Poulailler",
                error=f"Erreur de connexion: {str(e)}"
            )]

    def _parse_barn_data(self, data: Dict[str, Any]) -> CompassBarnInfo:
        """Parse barn data from API response"""
        return CompassBarnInfo(
            barn_number=data.get("client_number", "?"),
            barn_name=data.get("name", "Poulailler"),
            temperature=data.get("temperature"),
            humidity=data.get("humidity"),
            average_weight=data.get("average_weight"),
            age_days=data.get("age_days"),
            has_data=True
        )

    async def enrich_context(
        self,
        query: str,
        user_token: str,
        existing_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich query context with Compass barn data

        Args:
            query: User query
            user_token: User's JWT token
            existing_context: Existing context to append to

        Returns:
            Dictionary with enriched context and metadata
        """
        if not self.is_compass_query(query):
            return {
                "is_compass_query": False,
                "context": existing_context or "",
                "barn_data": []
            }

        # Extract requested barn numbers
        barn_numbers = self.extract_barn_numbers(query)
        data_types = self.detect_data_types(query)

        # Fetch barn data
        if barn_numbers:
            # Fetch specific barns
            all_barn_data = []
            for barn_num in barn_numbers:
                barn_data = await self.fetch_barn_data(user_token, barn_num)
                all_barn_data.extend(barn_data)
        else:
            # Fetch all barns (user didn't specify)
            all_barn_data = await self.fetch_barn_data(user_token)

        # Build enriched context
        context_parts = []

        if existing_context:
            context_parts.append(existing_context)

        if all_barn_data:
            context_parts.append("\n=== DONNÉES TEMPS RÉEL COMPASS ===")
            for barn_info in all_barn_data:
                context_parts.append(barn_info.to_context_string())
            context_parts.append("=== FIN DONNÉES COMPASS ===\n")

        enriched_context = "\n".join(context_parts)

        logger.info(f"Compass context enriched: {len(all_barn_data)} barn(s), "
                   f"data types: {data_types}")

        return {
            "is_compass_query": True,
            "context": enriched_context,
            "barn_data": [
                {
                    "barn_number": barn.barn_number,
                    "barn_name": barn.barn_name,
                    "temperature": barn.temperature,
                    "humidity": barn.humidity,
                    "weight": barn.average_weight,
                    "age": barn.age_days,
                    "has_data": barn.has_data
                }
                for barn in all_barn_data
            ],
            "requested_barns": barn_numbers if barn_numbers else "all",
            "requested_data_types": data_types
        }

    def create_compass_system_prompt(self) -> str:
        """
        Create system prompt addition for Compass queries

        Returns:
            Additional system prompt instructions
        """
        return """
## DONNÉES TEMPS RÉEL COMPASS

Vous avez accès à des données temps réel provenant de Compass (système de gestion de poulaillers).

Lorsque des données Compass sont présentes dans le contexte (section "=== DONNÉES TEMPS RÉEL COMPASS ==="):
1. Utilisez TOUJOURS ces données pour répondre aux questions sur les conditions actuelles
2. Citez les valeurs exactes (température, humidité, poids, âge)
3. Si des données manquent, mentionnez-le clairement
4. Comparez avec les standards si pertinent

Exemple de réponse:
"D'après les données temps réel de votre Poulailler Est (poulailler 2):
- La température actuelle est de 22.5°C
- L'humidité est de 65%
- Le poids moyen du troupeau est de 2450g
- Le troupeau a 35 jours

Cette température est dans la plage normale pour un troupeau de cet âge..."
"""


# Singleton instance
_compass_extension: Optional[CompassExtension] = None


def get_compass_extension() -> CompassExtension:
    """
    Get singleton instance of CompassExtension

    Returns:
        CompassExtension instance
    """
    global _compass_extension

    if _compass_extension is None:
        _compass_extension = CompassExtension()

    return _compass_extension


# Helper function for easy import
async def enrich_with_compass_data(
    query: str,
    user_token: str,
    existing_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to enrich context with Compass data

    Args:
        query: User query
        user_token: User's JWT token
        existing_context: Existing context

    Returns:
        Enriched context dictionary
    """
    extension = get_compass_extension()
    return await extension.enrich_context(query, user_token, existing_context)
