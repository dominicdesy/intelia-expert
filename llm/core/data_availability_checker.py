# -*- coding: utf-8 -*-
"""
data_availability_checker.py - Vérification de disponibilité des données
Détecte si les données demandées existent dans la base
VERSION ASSOUPLIE: Propose des alternatives au lieu de rejeter
"""

import logging
from typing import Dict, List, Tuple, Any
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
    # NOUVEAU: Champs pour alternatives
    available_range: Tuple[int, int] = None
    closest_age: int = None
    allow_extrapolation: bool = False


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
    ) -> Dict[str, Any]:
        """
        Vérification assouplie de la disponibilité des données

        MODIFICATION MAJEURE: Au lieu de rejeter, propose des alternatives

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            Dict avec clés: data_available, reason, data_type, suggestions, alternatives
        """
        # CORRECTION: Normaliser les entités age_days → age
        normalized_entities = entities.copy()
        if "age_days" in entities and "age" not in entities:
            normalized_entities["age"] = entities["age_days"]

        # Vérifications par priorité

        # 1. Données économiques - ASSOUPLI
        if self._is_economic_query(query):
            return {
                "data_available": False,
                "reason": "Les données économiques ne sont pas disponibles dans notre système",
                "data_type": "metrics",
                "suggestions": [
                    "Nous pouvons calculer l'efficacité alimentaire (g viande / kg aliment)",
                    "Les données de performance peuvent aider à estimer la rentabilité",
                    "Utilisez vos coûts locaux avec nos données de performance",
                ],
                "allow_partial": True,  # NOUVEAU: Permettre analyse partielle
            }

        # 2. Nutrition Ross 308 - ASSOUPLI
        if self._is_nutrition_ross_query(query, normalized_entities):
            return {
                "data_available": False,
                "reason": "Les tables nutritionnelles Ross 308 ne sont pas disponibles",
                "data_type": "nutrition",
                "suggestions": [
                    "Nous avons des données nutritionnelles complètes pour Cobb 500",
                    "Je peux vous fournir les performances de croissance Ross 308",
                    "Consultez les spécifications officielles Aviagen Ross",
                ],
                "alternative_breed": "cobb 500",  # NOUVEAU: Souche alternative
                "allow_performance_data": True,  # NOUVEAU: Données de performance disponibles
            }

        # 3. Plage d'âge - ASSOUPLI AVEC ALTERNATIVES
        if "age_days" in entities or "age" in normalized_entities:
            try:
                age = int(entities.get("age_days") or normalized_entities.get("age"))
                breed = normalized_entities.get("breed", "")

                age_check = self.check_age_range_flexible(breed, age)
                if not age_check["available"]:
                    return {
                        "data_available": False,
                        "reason": age_check["message"],
                        "data_type": "metrics",
                        "available_range": age_check.get("available_range"),
                        "closest_age": age_check.get("closest_age"),
                        "allow_extrapolation": age_check.get(
                            "allow_extrapolation", False
                        ),
                        "suggestions": age_check.get("suggestions", []),
                    }
            except (ValueError, TypeError):
                return {
                    "data_available": False,
                    "reason": f"Âge invalide: {entities.get('age_days', 'unknown')}",
                    "data_type": "metrics",
                    "suggestions": ["Veuillez spécifier un âge valide en jours"],
                }

        # 4. Souche existe - ASSOUPLI
        if "breed" in normalized_entities:
            breed_check = self.check_breed_exists_flexible(normalized_entities["breed"])
            if not breed_check["available"]:
                return {
                    "data_available": False,
                    "reason": breed_check["message"],
                    "data_type": "metrics",
                    "suggested_breeds": breed_check.get("suggested_breeds", []),
                    "similarity_score": breed_check.get("similarity_score", 0),
                    "suggestions": breed_check.get("suggestions", []),
                }

        # Tout est disponible
        return {"data_available": True, "reason": None, "data_type": "metrics"}

    def check_age_range_flexible(self, breed: str, age: int) -> Dict[str, Any]:
        """
        NOUVELLE MÉTHODE: Vérification assouplie de l'âge avec alternatives

        Args:
            breed: Nom de la souche
            age: Âge en jours

        Returns:
            Dict avec disponibilité et alternatives
        """
        available_range = self.get_available_age_range(breed)

        if age < available_range[0] or age > available_range[1]:
            closest_age = self._find_closest_available_age(breed, age)

            # Déterminer si extrapolation est raisonnable
            allow_extrapolation = self._can_extrapolate(breed, age, available_range)

            return {
                "available": False,
                "message": f"Âge {age} jours non disponible pour {breed}",
                "available_range": available_range,
                "closest_age": closest_age,
                "allow_extrapolation": allow_extrapolation,
                "suggestions": [
                    f"Essayez avec {closest_age} jours",
                    f"Données disponibles de {available_range[0]} à {available_range[1]} jours",
                    (
                        "L'extrapolation est possible avec une précision réduite"
                        if allow_extrapolation
                        else "Extrapolation non recommandée"
                    ),
                ],
            }

        return {"available": True}

    def check_breed_exists_flexible(self, breed: str) -> Dict[str, Any]:
        """
        NOUVELLE MÉTHODE: Vérification assouplie de la souche avec suggestions

        Args:
            breed: Nom de la souche

        Returns:
            Dict avec disponibilité et suggestions
        """
        breed_lower = breed.lower()

        # Vérifier si souche connue
        is_known = any(
            known.lower() in breed_lower or breed_lower in known.lower()
            for known in self.KNOWN_BREEDS
        )

        if not is_known:
            # Chercher souches similaires
            suggested_breeds = self._find_similar_breeds(breed)
            similarity_score = self._calculate_breed_similarity(breed, suggested_breeds)

            return {
                "available": False,
                "message": f"La souche '{breed}' n'est pas disponible dans notre base de données",
                "suggested_breeds": suggested_breeds,
                "similarity_score": similarity_score,
                "suggestions": [
                    f"Souches similaires disponibles: {', '.join(suggested_breeds)}",
                    "Vérifiez l'orthographe du nom de la souche",
                    "Souches complètes: Ross 308, Cobb 500",
                ],
            }

        return {"available": True}

    def get_available_age_range(self, breed: str) -> Tuple[int, int]:
        """
        NOUVELLE MÉTHODE: Récupère la plage d'âge disponible pour une souche

        Args:
            breed: Nom de la souche

        Returns:
            Tuple (âge_min, âge_max)
        """
        breed_lower = breed.lower()

        for known_breed, range_info in self.AGE_RANGES.items():
            if known_breed.lower() in breed_lower or breed_lower in known_breed.lower():
                return (range_info["min"], range_info["max"])

        # Plage par défaut pour souche inconnue
        return (0, 60)

    def _find_closest_available_age(self, breed: str, requested_age: int) -> int:
        """
        NOUVELLE MÉTHODE: Trouve l'âge disponible le plus proche

        Args:
            breed: Nom de la souche
            requested_age: Âge demandé

        Returns:
            Âge le plus proche disponible
        """
        min_age, max_age = self.get_available_age_range(breed)

        if requested_age < min_age:
            return min_age
        elif requested_age > max_age:
            return max_age
        else:
            return requested_age

    def _can_extrapolate(
        self, breed: str, age: int, available_range: Tuple[int, int]
    ) -> bool:
        """
        NOUVELLE MÉTHODE: Détermine si l'extrapolation est raisonnable

        Args:
            breed: Nom de la souche
            age: Âge demandé
            available_range: Plage disponible

        Returns:
            True si extrapolation possible
        """
        min_age, max_age = available_range

        # Extrapolation acceptable si dans les 20% de la plage
        range_size = max_age - min_age
        tolerance = range_size * 0.2

        if age < min_age:
            return (min_age - age) <= tolerance
        elif age > max_age:
            return (age - max_age) <= tolerance

        return True

    def _find_similar_breeds(self, breed: str) -> List[str]:
        """
        NOUVELLE MÉTHODE: Trouve des souches similaires

        Args:
            breed: Nom de la souche recherchée

        Returns:
            Liste des souches similaires
        """
        breed_lower = breed.lower()
        similar_breeds = []

        # Recherche par mots-clés
        if "ross" in breed_lower or "308" in breed_lower:
            similar_breeds.append("ross 308")
        if "cobb" in breed_lower or "500" in breed_lower:
            similar_breeds.append("cobb 500")

        # Si aucune correspondance, proposer toutes les souches
        if not similar_breeds:
            similar_breeds = ["ross 308", "cobb 500"]

        return similar_breeds

    def _calculate_breed_similarity(
        self, breed: str, suggested_breeds: List[str]
    ) -> float:
        """
        NOUVELLE MÉTHODE: Calcule un score de similarité

        Args:
            breed: Souche recherchée
            suggested_breeds: Souches suggérées

        Returns:
            Score de similarité (0-1)
        """
        if not suggested_breeds:
            return 0.0

        breed_lower = breed.lower()
        max_similarity = 0.0

        for suggested in suggested_breeds:
            suggested_lower = suggested.lower()

            # Similarité basée sur les mots communs
            breed_words = set(breed_lower.split())
            suggested_words = set(suggested_lower.split())

            if breed_words and suggested_words:
                common_words = breed_words.intersection(suggested_words)
                similarity = len(common_words) / len(breed_words.union(suggested_words))
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    async def check_availability(
        self, query: str, entities: Dict[str, str]
    ) -> AvailabilityResult:
        """
        Vérification assouplie globale des données pour une requête
        MODIFICATION: Intègre les nouvelles méthodes flexibles

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            AvailabilityResult
        """
        # Vérifications par priorité

        # 1. Données économiques - ASSOUPLI
        if self._is_economic_query(query):
            return AvailabilityResult(
                available=False,
                issue_type="economic_data_unavailable",
                message=(
                    "Les données économiques ne sont pas disponibles, mais nous pouvons "
                    "vous aider avec l'efficacité alimentaire et les performances."
                ),
                suggestions=[
                    "Calcul de l'efficacité alimentaire (g viande / kg aliment)",
                    "Données de performance pour estimation de rentabilité",
                    "Utilisez vos coûts locaux avec nos données de performance",
                ],
                confidence=0.8,  # Réduit car alternatives disponibles
                allow_extrapolation=True,
            )

        # 2. Nutrition Ross 308 - ASSOUPLI
        if self._is_nutrition_ross_query(query, entities):
            return AvailabilityResult(
                available=False,
                issue_type="nutrition_ross_unavailable",
                message=(
                    "Tables nutritionnelles Ross 308 non disponibles, mais données "
                    "de performance disponibles. Données nutritionnelles Cobb 500 complètes."
                ),
                suggestions=[
                    "Données nutritionnelles complètes pour Cobb 500",
                    "Performances de croissance Ross 308 disponibles",
                    "Consultez spécifications officielles Aviagen Ross",
                ],
                confidence=0.7,  # Alternative disponible
                allow_extrapolation=True,
            )

        # 3. Plage d'âge - UTILISE NOUVELLE MÉTHODE FLEXIBLE
        if "age_days" in entities:
            breed = entities.get("breed", "")
            age = int(entities["age_days"])

            age_check = self.check_age_range_flexible(breed, age)
            if not age_check["available"]:
                return AvailabilityResult(
                    available=False,
                    issue_type="age_out_of_range",
                    message=age_check["message"],
                    suggestions=age_check["suggestions"],
                    confidence=0.6 if age_check.get("allow_extrapolation") else 0.3,
                    available_range=age_check.get("available_range"),
                    closest_age=age_check.get("closest_age"),
                    allow_extrapolation=age_check.get("allow_extrapolation", False),
                )

        # 4. Souche existe - UTILISE NOUVELLE MÉTHODE FLEXIBLE
        if "breed" in entities:
            breed_check = self.check_breed_exists_flexible(entities["breed"])
            if not breed_check["available"]:
                return AvailabilityResult(
                    available=False,
                    issue_type="breed_unknown",
                    message=breed_check["message"],
                    suggestions=breed_check["suggestions"],
                    confidence=breed_check.get("similarity_score", 0.5),
                    allow_extrapolation=True,  # Souches similaires disponibles
                )

        # 5. Métrique disponible (si DB disponible) - ASSOUPLI
        if self.db_pool and "breed" in entities:
            metric_check = await self.check_metric_available(
                entities.get("breed", ""), self._extract_metric_type(query)
            )
            if not metric_check.available:
                # Assoupli: propose métriques alternatives
                metric_check.suggestions.extend(
                    [
                        "Métriques similaires peuvent être disponibles",
                        "Vérifiez les métriques de base: poids, IC, gain, consommation",
                    ]
                )
                metric_check.confidence = max(0.5, metric_check.confidence)
                metric_check.allow_extrapolation = True

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

    async def check_metric_available(
        self, breed: str, metric_type: str
    ) -> AvailabilityResult:
        """
        Vérification assouplie des métriques disponibles
        MODIFICATION: Plus tolérant, propose alternatives

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
                    # ASSOUPLI: Chercher métriques similaires
                    similar_metrics = await self._find_similar_metrics(
                        conn, breed, metric_type
                    )

                    return AvailabilityResult(
                        available=False,
                        issue_type="metric_unavailable",
                        message=(
                            f"Métrique '{metric_type}' non disponible pour {breed}, "
                            f"mais {len(similar_metrics)} métriques similaires trouvées."
                        ),
                        suggestions=[
                            f"Métriques similaires: {', '.join(similar_metrics[:3])}",
                            "Métriques de base: body_weight, feed_conversion_ratio, daily_gain",
                            "Vérifiez le nom de la métrique",
                        ],
                        confidence=0.6 if similar_metrics else 0.3,
                        allow_extrapolation=bool(similar_metrics),
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
                available=True,  # Assoupli: assume disponible en cas d'erreur
                issue_type="none",
                message="",
                suggestions=["Vérification automatique indisponible"],
                confidence=0.5,
            )

    async def _find_similar_metrics(
        self, conn, breed: str, metric_type: str
    ) -> List[str]:
        """
        NOUVELLE MÉTHODE: Trouve des métriques similaires

        Args:
            conn: Connexion DB
            breed: Souche
            metric_type: Type de métrique recherché

        Returns:
            Liste des métriques similaires
        """
        try:
            query = """
            SELECT DISTINCT m.metric_name
            FROM metrics m
            JOIN documents d ON m.document_id = d.id
            JOIN strains s ON d.strain_id = s.id
            WHERE s.strain_name LIKE $1
            ORDER BY m.metric_name
            """

            rows = await conn.fetch(query, f"%{breed}%")
            available_metrics = [row["metric_name"] for row in rows]

            # Recherche par similarité de mots
            metric_lower = metric_type.lower()
            similar_metrics = []

            for metric in available_metrics:
                metric_words = set(metric.lower().split("_"))
                search_words = set(metric_lower.split("_"))

                if metric_words.intersection(search_words):
                    similar_metrics.append(metric)

            return similar_metrics[:5]  # Limite à 5 suggestions

        except Exception as e:
            logger.error(f"Erreur recherche métriques similaires: {e}")
            return []

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
        MODIFICATION: Messages plus positifs avec alternatives

        Args:
            issue_type: Type de problème
            details: Détails additionnels

        Returns:
            Message formaté
        """
        details = details or {}

        messages = {
            "economic_data_unavailable": (
                "💡 Données économiques non disponibles, mais nous pouvons calculer "
                "l'efficacité alimentaire et vous aider avec les performances zootechniques."
            ),
            "nutrition_ross_unavailable": (
                "📊 Tables nutritionnelles Ross 308 non disponibles. "
                "Données Cobb 500 complètes disponibles et performances Ross 308 accessibles."
            ),
            "age_out_of_range": (
                "⚠️ Âge hors plage disponible, mais extrapolation possible. "
                f"Âge le plus proche: {details.get('closest_age', 'N/A')} jours."
            ),
            "breed_unknown": (
                "❌ Souche non disponible. "
                f"Souches similaires: {', '.join(details.get('suggested_breeds', []))}"
            ),
            "metric_unavailable": (
                "⚠️ Métrique non disponible. "
                f"Alternatives disponibles: {', '.join(details.get('similar_metrics', []))}"
            ),
        }

        return messages.get(
            issue_type, "Données partiellement disponibles avec alternatives."
        )
