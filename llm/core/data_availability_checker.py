# -*- coding: utf-8 -*-
"""
data_availability_checker.py - Vérification de disponibilité des données
Détecte si les données demandées existent dans la base
"""

import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AvailabilityResult:
    """Résultat de vérification de disponibilité"""

    available: bool
    issue_type: str
    message: str
    suggestions: List[str]
    confidence: float = 1.0


class DataAvailabilityChecker:
    """Vérifie la disponibilité des données avant exécution de requête"""

    # Plages d'âges valides par souche
    AGE_RANGES = {
        "308/308 FF": {"min": 0, "max": 56},
        "500": {"min": 1, "max": 57},
        "ross 308": {"min": 0, "max": 56},
        "cobb 500": {"min": 1, "max": 57},
    }

    # Souches connues
    KNOWN_BREEDS = ["308/308 FF", "500", "ross 308", "cobb 500"]

    def __init__(self, db_pool=None):
        """
        Args:
            db_pool: Pool de connexions PostgreSQL (optionnel)
        """
        self.db_pool = db_pool

    def check_data_availability(
        self, query: str, entities: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Vérifie la disponibilité des données pour une requête

        MÉTHODE AJOUTÉE: Interface synchrone requise par le système principal

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            Dict avec clés: data_available, reason, data_type
        """
        # CORRECTION: Normaliser les entités age_days → age
        normalized_entities = entities.copy()
        if "age_days" in entities and "age" not in entities:
            normalized_entities["age"] = entities["age_days"]

        # Vérifications par priorité

        # 1. Données économiques
        if self._is_economic_query(query):
            return {
                "data_available": False,
                "reason": "Les données économiques ne sont pas disponibles dans notre système",
                "data_type": "metrics",
            }

        # 2. Nutrition Ross 308
        if self._is_nutrition_ross_query(query, normalized_entities):
            return {
                "data_available": False,
                "reason": "Les tables nutritionnelles Ross 308 ne sont pas disponibles",
                "data_type": "nutrition",
            }

        # 3. Plage d'âge - utiliser entités normalisées
        if "age_days" in entities or "age" in normalized_entities:
            try:
                age = int(entities.get("age_days") or normalized_entities.get("age"))
                age_check = self.check_age_range(
                    normalized_entities.get("breed", ""), age
                )
                if not age_check.available:
                    return {
                        "data_available": False,
                        "reason": age_check.message,
                        "data_type": "metrics",
                    }
            except (ValueError, TypeError):
                return {
                    "data_available": False,
                    "reason": f"Âge invalide: {entities.get('age_days', 'unknown')}",
                    "data_type": "metrics",
                }

        # 4. Souche existe
        if "breed" in normalized_entities:
            breed_check = self.check_breed_exists(normalized_entities["breed"])
            if not breed_check.available:
                return {
                    "data_available": False,
                    "reason": breed_check.message,
                    "data_type": "metrics",
                }

        # Tout est disponible
        return {"data_available": True, "reason": None, "data_type": "metrics"}

    async def check_availability(
        self, query: str, entities: Dict[str, str]
    ) -> AvailabilityResult:
        """
        Vérifie la disponibilité globale des données pour une requête

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            AvailabilityResult
        """
        # Vérifications par priorité

        # 1. Données économiques
        if self._is_economic_query(query):
            return self._handle_economic_data()

        # 2. Nutrition Ross 308
        if self._is_nutrition_ross_query(query, entities):
            return self._handle_nutrition_ross()

        # 3. Plage d'âge
        if "age_days" in entities:
            age_check = self.check_age_range(
                entities.get("breed", ""), int(entities["age_days"])
            )
            if not age_check.available:
                return age_check

        # 4. Souche existe
        if "breed" in entities:
            breed_check = self.check_breed_exists(entities["breed"])
            if not breed_check.available:
                return breed_check

        # 5. Métrique disponible (si DB disponible)
        if self.db_pool and "breed" in entities:
            metric_check = await self.check_metric_available(
                entities.get("breed", ""), self._extract_metric_type(query)
            )
            if not metric_check.available:
                return metric_check

        # Tout est disponible
        return AvailabilityResult(
            available=True,
            issue_type="none",
            message="",
            suggestions=[],
            confidence=1.0,
        )

    def _is_economic_query(self, query: str) -> bool:
        """Détecte si c'est une requête économique"""
        query_lower = query.lower()
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
            "retour sur investissement",
            "économique",
            "economique",
            "economic",
            "€",
            "$",
            "dollar",
            "euro",
        ]
        return any(keyword in query_lower for keyword in economic_keywords)

    def _is_nutrition_ross_query(self, query: str, entities: Dict) -> bool:
        """Détecte si c'est une requête nutrition pour Ross 308"""
        query_lower = query.lower()

        # Mots-clés nutrition
        nutrition_keywords = [
            "nutrition",
            "nutritionnel",
            "aliment",
            "protéine",
            "protein",
            "lysine",
            "méthionine",
            "acide aminé",
            "amino acid",
            "énergie",
            "energy",
            "starter",
            "grower",
            "finisher",
        ]

        has_nutrition = any(keyword in query_lower for keyword in nutrition_keywords)

        # Vérifier si Ross
        breed = entities.get("breed", "").lower()
        is_ross = "ross" in breed or "308" in breed

        return has_nutrition and is_ross

    def _handle_economic_data(self) -> AvailabilityResult:
        """Gère les requêtes économiques"""
        return AvailabilityResult(
            available=False,
            issue_type="economic_data_unavailable",
            message=(
                "Les données économiques (coûts d'aliment, prix de marché) ne sont pas "
                "disponibles dans notre système. Notre expertise se concentre sur les "
                "performances zootechniques et les objectifs de production."
            ),
            suggestions=[
                "Nous pouvons vous fournir les données de performance (poids, IC, gain)",
                "Pour des analyses économiques, utilisez vos données de coûts locales",
                "Nous pouvons calculer l'efficacité alimentaire (g viande / kg aliment)",
            ],
            confidence=1.0,
        )

    def _handle_nutrition_ross(self) -> AvailabilityResult:
        """Gère les requêtes nutrition Ross 308"""
        return AvailabilityResult(
            available=False,
            issue_type="nutrition_ross_unavailable",
            message=(
                "Les tables nutritionnelles détaillées pour Ross 308 ne sont pas disponibles "
                "dans notre base de données. Nous disposons de recommandations générales "
                "dans les guides Aviagen Ross."
            ),
            suggestions=[
                "Consultez les spécifications nutritionnelles officielles Aviagen Ross",
                "Nous avons des données nutritionnelles complètes pour Cobb 500",
                "Je peux vous fournir les performances de croissance Ross 308",
            ],
            confidence=1.0,
        )

    def check_age_range(self, breed: str, age: int) -> AvailabilityResult:
        """
        Vérifie si l'âge est dans la plage valide pour la souche

        Args:
            breed: Nom de la souche
            age: Âge en jours

        Returns:
            AvailabilityResult
        """
        # Normaliser nom de souche
        breed_lower = breed.lower()

        age_range = None
        for known_breed, range_info in self.AGE_RANGES.items():
            if known_breed.lower() in breed_lower or breed_lower in known_breed.lower():
                age_range = range_info
                break

        if not age_range:
            # Souche inconnue, plage par défaut
            age_range = {"min": 0, "max": 60}

        if age < age_range["min"] or age > age_range["max"]:
            return AvailabilityResult(
                available=False,
                issue_type="age_out_of_range",
                message=(
                    f"L'âge demandé ({age} jours) est hors de la plage de données disponibles "
                    f"pour {breed} ({age_range['min']}-{age_range['max']} jours)."
                ),
                suggestions=[
                    f"Les données sont disponibles de {age_range['min']} à {age_range['max']} jours",
                    "Choisissez un âge dans cette plage",
                ],
                confidence=1.0,
            )

        return AvailabilityResult(
            available=True,
            issue_type="none",
            message="",
            suggestions=[],
            confidence=1.0,
        )

    def check_breed_exists(self, breed: str) -> AvailabilityResult:
        """
        Vérifie si la souche existe dans notre base

        Args:
            breed: Nom de la souche

        Returns:
            AvailabilityResult
        """
        breed_lower = breed.lower()

        # Vérifier si souche connue
        is_known = any(
            known.lower() in breed_lower or breed_lower in known.lower()
            for known in self.KNOWN_BREEDS
        )

        if not is_known:
            return AvailabilityResult(
                available=False,
                issue_type="breed_unknown",
                message=(
                    f"La souche '{breed}' n'est pas disponible dans notre base de données."
                ),
                suggestions=[
                    "Souches disponibles: Ross 308, Cobb 500",
                    "Vérifiez l'orthographe du nom de la souche",
                ],
                confidence=0.9,
            )

        return AvailabilityResult(
            available=True,
            issue_type="none",
            message="",
            suggestions=[],
            confidence=1.0,
        )

    async def check_metric_available(
        self, breed: str, metric_type: str
    ) -> AvailabilityResult:
        """
        Vérifie si une métrique est disponible pour une souche

        Args:
            breed: Nom de la souche
            metric_type: Type de métrique

        Returns:
            AvailabilityResult
        """
        if not self.db_pool or not metric_type:
            return AvailabilityResult(
                available=True,
                issue_type="none",
                message="",
                suggestions=[],
                confidence=0.7,
            )

        try:
            async with self.db_pool.acquire() as conn:
                # Vérifier si métrique existe
                query = """
                SELECT COUNT(*) as count
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name LIKE $1
                  AND m.metric_name LIKE $2
                """

                row = await conn.fetchrow(query, f"%{breed}%", f"%{metric_type}%")

                if row["count"] == 0:
                    return AvailabilityResult(
                        available=False,
                        issue_type="metric_unavailable",
                        message=(
                            f"La métrique '{metric_type}' n'est pas disponible pour {breed}."
                        ),
                        suggestions=[
                            "Métriques disponibles: body_weight, feed_conversion_ratio, daily_gain, feed_intake",
                            "Vérifiez le nom de la métrique",
                        ],
                        confidence=0.9,
                    )

                return AvailabilityResult(
                    available=True,
                    issue_type="none",
                    message="",
                    suggestions=[],
                    confidence=1.0,
                )

        except Exception as e:
            logger.error(f"Erreur vérification métrique: {e}")
            return AvailabilityResult(
                available=True,
                issue_type="none",
                message="",
                suggestions=[],
                confidence=0.5,
            )

    def _extract_metric_type(self, query: str) -> str:
        """
        Extrait le type de métrique de la requête

        Args:
            query: Requête utilisateur

        Returns:
            Type de métrique ou chaîne vide
        """
        query_lower = query.lower()

        metric_keywords = {
            "body_weight": ["poids", "weight", "kg", "gramme"],
            "feed_conversion_ratio": ["ic", "fcr", "conversion", "indice"],
            "daily_gain": ["gain", "croissance", "growth"],
            "feed_intake": ["consommation", "intake", "aliment", "feed"],
        }

        for metric_type, keywords in metric_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return metric_type

        return ""

    def generate_unavailable_message(
        self, issue_type: str, details: Dict = None
    ) -> str:
        """
        Génère un message explicatif pour données non disponibles

        Args:
            issue_type: Type de problème
            details: Détails additionnels

        Returns:
            Message formaté
        """
        details = details or {}

        messages = {
            "economic_data_unavailable": (
                "💡 Les données économiques ne sont pas dans notre domaine d'expertise. "
                "Nous nous concentrons sur les performances zootechniques."
            ),
            "nutrition_ross_unavailable": (
                "📊 Les tables nutritionnelles détaillées Ross 308 ne sont pas disponibles. "
                "Consultez les spécifications officielles Aviagen Ross."
            ),
            "age_out_of_range": (
                "⚠️ L'âge demandé est hors de la plage de données disponibles."
            ),
            "breed_unknown": (
                "❌ Cette souche n'est pas disponible dans notre base de données."
            ),
            "metric_unavailable": (
                "⚠️ Cette métrique n'est pas disponible pour cette souche."
            ),
        }

        return messages.get(issue_type, "Données non disponibles.")
