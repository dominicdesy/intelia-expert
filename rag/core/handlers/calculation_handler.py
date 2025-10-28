# -*- coding: utf-8 -*-
"""
calculation_handler.py - Handler pour les requêtes de calcul complexes
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
calculation_handler.py - Handler pour les requêtes de calcul complexes
Gère les calculs multi-étapes, projections, et recherches inversées
"""

import logging
from utils.types import Dict, Any
from .base_handler import BaseQueryHandler
from ..calculation_engine import CalculationEngine, CalculationResult
from ..reverse_lookup import ReverseLookup, ReverseLookupResult

logger = logging.getLogger(__name__)


class CalculationQueryHandler(BaseQueryHandler):
    """
    Handler pour les requêtes de calcul nécessitant:
    - Reverse lookup (âge pour poids cible)
    - Cumulative feed (consommation totale entre deux âges)
    - Projections (poids futur)
    - Calculs de troupeau
    """

    def __init__(self, db_pool):
        """
        Args:
            db_pool: Pool de connexions PostgreSQL
        """
        super().__init__()
        self.db_pool = db_pool
        self.calculation_engine = CalculationEngine(db_pool)
        self.reverse_lookup = ReverseLookup(db_pool)
        logger.info(
            "✅ CalculationQueryHandler initialized with calculation_engine + reverse_lookup"
        )

    async def handle(
        self, query: str, entities: Dict[str, Any], language: str = "fr", **kwargs
    ) -> Dict[str, Any]:
        """
        Gère une requête de calcul

        Args:
            query: Question originale
            entities: Entités extraites (breed, age_days, target_weight, calculation_type, etc.)
            language: Langue de réponse

        Returns:
            Dict avec résultats du calcul
        """
        calculation_type = entities.get("calculation_type")

        logger.info(f"🧮 Calculation query detected: type={calculation_type}")

        try:
            # Dispatcher selon le type de calcul
            if calculation_type == "reverse_lookup":
                result = await self._handle_reverse_lookup(query, entities)
            elif calculation_type == "cumulative_feed":
                result = await self._handle_cumulative_feed(query, entities)
            elif calculation_type == "projection":
                result = await self._handle_projection(query, entities)
            elif calculation_type == "flock_calculation":
                result = await self._handle_flock_calculation(query, entities)
            else:
                # Auto-detect si pas spécifié
                result = await self._auto_detect_calculation(query, entities)

            return {
                "success": True,
                "calculation_result": result,
                "query_type": "calculation",
                "calculation_type": calculation_type,
            }

        except Exception as e:
            logger.error(f"❌ Error in calculation handler: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query_type": "calculation",
            }

    async def _handle_reverse_lookup(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gère les recherches inversées (âge pour poids cible)

        Exemple: "À quel âge Ross 308 mâle atteint 2.4 kg?"
        """
        breed = entities.get("breed")
        sex = entities.get("sex", "as_hatched")
        target_weight = entities.get("target_weight")  # en grammes

        if not breed or not target_weight:
            return {
                "error": "Missing breed or target_weight",
                "needs_clarification": True,
            }

        # Normaliser breed name pour PostgreSQL
        breed_normalized = self._normalize_breed_name(breed)

        logger.info(
            f"🔍 Reverse lookup: breed={breed_normalized}, sex={sex}, target={target_weight}g"
        )

        # Trouver l'âge pour le poids cible
        lookup_result: ReverseLookupResult = (
            await self.reverse_lookup.find_age_for_weight(
                breed=breed_normalized, sex=sex, target_weight=target_weight
            )
        )

        return {
            "age_found": lookup_result.age_found,
            "weight_found": lookup_result.value_found,
            "target_weight": lookup_result.target_value,
            "difference": lookup_result.difference,
            "unit": lookup_result.unit,
            "confidence": lookup_result.confidence,
        }

    async def _handle_cumulative_feed(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule la consommation totale d'aliment entre deux âges

        Exemple: "De combien de moulée j'aurai besoin entre jour 18 et poids cible 2.4kg?"

        Cette méthode combine:
        1. Reverse lookup pour trouver âge final (si target_weight fourni)
        2. Calcul consommation cumulée entre age_start et age_end
        """
        # DEBUG: Log exact entities received
        logger.debug(f"🔍 DEBUG _handle_cumulative_feed: entities = {entities}")
        logger.debug(f"🔍 DEBUG: entities.keys() = {list(entities.keys())}")

        breed = entities.get("breed")
        sex = entities.get("sex", "as_hatched")
        age_start = entities.get("age_days")
        target_weight = entities.get("target_weight")

        logger.debug(
            f"🔍 DEBUG: breed={breed}, age_start={age_start}, target_weight={target_weight}"
        )

        if not breed or not age_start:
            return {
                "error": "Missing breed or starting age",
                "needs_clarification": True,
            }

        # Normaliser breed name
        breed_normalized = self._normalize_breed_name(breed)

        # Étape 1: Si target_weight fourni, trouver l'âge correspondant
        if target_weight:
            logger.info(f"🔍 Step 1: Finding age for target weight {target_weight}g")
            lookup_result: ReverseLookupResult = (
                await self.reverse_lookup.find_age_for_weight(
                    breed=breed_normalized, sex=sex, target_weight=target_weight
                )
            )
            age_end = lookup_result.age_found

            if age_end == 0:
                return {
                    "error": f"Could not find age for target weight {target_weight}g",
                    "confidence": 0.0,
                }

            logger.info(f"✅ Target weight {target_weight}g reached at day {age_end}")
        else:
            # Si pas de target_weight, besoin d'un age_end explicite
            age_end = entities.get("age_end")
            logger.debug(
                f"🔍 DEBUG: age_end from entities.get('age_end') = {age_end}, type = {type(age_end)}"
            )
            logger.debug(f"🔍 DEBUG: 'age_end' in entities = {'age_end' in entities}")

            if not age_end:
                logger.error(
                    f"❌ age_end check failed! entities.keys() = {list(entities.keys())}"
                )
                logger.error(f"❌ Full entities dict: {entities}")
                return {
                    "error": "Need either target_weight or age_end",
                    "needs_clarification": True,
                }

        # Étape 2: Calculer consommation totale entre age_start et age_end
        logger.info(
            f"🧮 Step 2: Calculating total feed from day {age_start} to day {age_end}"
        )

        calc_result: CalculationResult = (
            await self.calculation_engine.calculate_total_feed(
                breed=breed_normalized,
                sex=sex,
                age_start=age_start,
                age_end=age_end,
                target_weight=target_weight,  # Pour interpolation proportionnelle
            )
        )

        return {
            "age_start": age_start,
            "age_end": age_end,
            "target_weight": target_weight,
            "total_feed_g": calc_result.value,
            "total_feed_kg": round(calc_result.value / 1000, 2),
            "feed_per_day": calc_result.details.get("feed_per_day"),
            "unit": calc_result.unit,
            "confidence": calc_result.confidence,
            "details": calc_result.details,
        }

    async def _handle_projection(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Projette le poids futur basé sur taux de croissance

        Exemple: "Quel sera le poids à 42j si je suis à 1.2kg à 28j?"
        """
        breed = entities.get("breed")
        sex = entities.get("sex", "as_hatched")
        age_start = entities.get("age_days")
        age_end = entities.get("age_end")

        if not breed or not age_start or not age_end:
            return {
                "error": "Missing breed, age_start, or age_end",
                "needs_clarification": True,
            }

        breed_normalized = self._normalize_breed_name(breed)

        logger.info(
            f"📈 Projection: {breed_normalized} from day {age_start} to {age_end}"
        )

        calc_result: CalculationResult = await self.calculation_engine.project_weight(
            breed=breed_normalized, sex=sex, age_start=age_start, age_end=age_end
        )

        return {
            "projected_weight_g": calc_result.value,
            "projected_weight_kg": round(calc_result.value / 1000, 2),
            "age_start": age_start,
            "age_end": age_end,
            "avg_growth_rate": calc_result.details.get("avg_growth_rate"),
            "unit": calc_result.unit,
            "confidence": calc_result.confidence,
            "details": calc_result.details,
        }

    async def _handle_flock_calculation(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule les totaux pour un troupeau de N oiseaux

        Exemple: "10,000 Ross 308 à 42j, combien de poids total et aliment?"
        """
        breed = entities.get("breed")
        sex = entities.get("sex", "as_hatched")
        age = entities.get("age_days")
        flock_size = entities.get("flock_size", 1000)
        mortality_pct = entities.get("mortality_pct", 0.0)

        if not breed or not age:
            return {"error": "Missing breed or age", "needs_clarification": True}

        breed_normalized = self._normalize_breed_name(breed)

        logger.info(
            f"🐔 Flock calculation: {flock_size} birds, {breed_normalized}, {age}d"
        )

        result = await self.calculation_engine.calculate_flock_totals(
            breed=breed_normalized,
            sex=sex,
            age=age,
            flock_size=flock_size,
            mortality_pct=mortality_pct,
        )

        return result

    async def _auto_detect_calculation(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Auto-détecte le type de calcul si pas spécifié
        """
        query_lower = query.lower()

        # Détection reverse lookup
        if any(
            phrase in query_lower
            for phrase in [
                "à quel âge",
                "at what age",
                "when will",
                "quand",
                "reach",
                "atteindre",
                "atteint",
            ]
        ) and entities.get("target_weight"):
            entities["calculation_type"] = "reverse_lookup"
            return await self._handle_reverse_lookup(query, entities)

        # Détection cumulative feed
        if any(
            phrase in query_lower
            for phrase in [
                "combien de moulée",
                "combien d'aliment",
                "how much feed",
                "total feed",
                "consommation totale",
                "besoin",
            ]
        ) and entities.get("target_weight"):
            entities["calculation_type"] = "cumulative_feed"
            return await self._handle_cumulative_feed(query, entities)

        # Détection projection
        if any(
            phrase in query_lower
            for phrase in ["quel sera", "what will be", "projet", "futur", "future"]
        ):
            entities["calculation_type"] = "projection"
            return await self._handle_projection(query, entities)

        # Défaut: consommation cumulée si target_weight présent
        if entities.get("target_weight"):
            return await self._handle_cumulative_feed(query, entities)

        return {
            "error": "Could not determine calculation type",
            "needs_clarification": True,
        }

    def _normalize_breed_name(self, breed: str) -> str:
        """
        Normalise le nom de souche pour PostgreSQL

        Ross 308 → 308/308 FF
        Cobb 500 → 500
        """
        breed_lower = breed.lower()

        if "ross" in breed_lower and "308" in breed_lower:
            return "308/308 FF"
        elif "cobb" in breed_lower and "500" in breed_lower:
            return "500"
        elif "308" in breed_lower:
            return "308/308 FF"
        elif "500" in breed_lower:
            return "500"

        # Retourner tel quel si pas de match
        return breed
