# -*- coding: utf-8 -*-
"""
reverse_lookup.py - Recherches inversées (valeur → âge)
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
reverse_lookup.py - Recherches inversées (valeur → âge)
Trouve l'âge correspondant à une valeur cible de métrique
"""

import logging
from utils.types import Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReverseLookupResult:
    """Résultat d'une recherche inversée"""

    age_found: int
    value_found: float
    target_value: float
    difference: float
    unit: str
    metric_type: str
    confidence: float = 1.0


class ReverseLookup:
    """Moteur de recherches inversées pour trouver l'âge correspondant à une valeur"""

    def __init__(self, db_pool):
        """
        Args:
            db_pool: Pool de connexions PostgreSQL (asyncpg)
        """
        self.db_pool = db_pool

    async def find_age_for_weight(
        self, breed: str, sex: str, target_weight: float
    ) -> ReverseLookupResult:
        """
        Trouve l'âge auquel un poulet atteint un poids cible

        Args:
            breed: Nom de la souche (ex: "308/308 FF", "500")
            sex: Sexe ("male", "female", "as_hatched")
            target_weight: Poids cible en grammes

        Returns:
            ReverseLookupResult avec l'âge trouvé
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Recherche de l'âge le plus proche du poids cible
                query = """
                SELECT 
                    m.age_min,
                    m.value_numeric as weight,
                    ABS(m.value_numeric - $1) as difference
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name = $2
                  AND d.sex = $3
                  AND m.metric_name LIKE 'body_weight for %'
                  AND m.value_numeric IS NOT NULL
                ORDER BY difference ASC
                LIMIT 1
                """

                row = await conn.fetchrow(query, target_weight, breed, sex)

                if not row:
                    return ReverseLookupResult(
                        age_found=0,
                        value_found=0,
                        target_value=target_weight,
                        difference=0,
                        unit="g",
                        metric_type="body_weight",
                        confidence=0.0,
                    )

                # Calculer confiance basée sur la proximité
                confidence = 1.0 if row["difference"] < 50 else 0.8

                return ReverseLookupResult(
                    age_found=row["age_min"],
                    value_found=row["weight"],
                    target_value=target_weight,
                    difference=round(row["difference"], 1),
                    unit="g",
                    metric_type="body_weight",
                    confidence=confidence,
                )

        except Exception as e:
            logger.error(f"Erreur recherche âge pour poids: {e}")
            return ReverseLookupResult(
                age_found=0,
                value_found=0,
                target_value=target_weight,
                difference=0,
                unit="g",
                metric_type="body_weight",
                confidence=0.0,
            )

    async def find_age_for_fcr(
        self, breed: str, sex: str, target_fcr: float
    ) -> ReverseLookupResult:
        """
        Trouve l'âge auquel l'IC atteint une valeur cible

        Args:
            breed: Nom de la souche
            sex: Sexe
            target_fcr: IC cible

        Returns:
            ReverseLookupResult avec l'âge trouvé
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                SELECT 
                    m.age_min,
                    m.value_numeric as fcr,
                    ABS(m.value_numeric - $1) as difference
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name = $2
                  AND d.sex = $3
                  AND m.metric_name LIKE 'feed_conversion_ratio for %'
                  AND m.value_numeric IS NOT NULL
                ORDER BY difference ASC
                LIMIT 1
                """

                row = await conn.fetchrow(query, target_fcr, breed, sex)

                if not row:
                    return ReverseLookupResult(
                        age_found=0,
                        value_found=0,
                        target_value=target_fcr,
                        difference=0,
                        unit="",
                        metric_type="feed_conversion_ratio",
                        confidence=0.0,
                    )

                confidence = 1.0 if row["difference"] < 0.05 else 0.8

                return ReverseLookupResult(
                    age_found=row["age_min"],
                    value_found=row["fcr"],
                    target_value=target_fcr,
                    difference=round(row["difference"], 3),
                    unit="",
                    metric_type="feed_conversion_ratio",
                    confidence=confidence,
                )

        except Exception as e:
            logger.error(f"Erreur recherche âge pour IC: {e}")
            return ReverseLookupResult(
                age_found=0,
                value_found=0,
                target_value=target_fcr,
                difference=0,
                unit="",
                metric_type="feed_conversion_ratio",
                confidence=0.0,
            )

    async def find_closest_match(
        self, breed: str, sex: str, metric_type: str, target_value: float
    ) -> ReverseLookupResult:
        """
        Recherche générique pour n'importe quelle métrique

        Args:
            breed: Nom de la souche
            sex: Sexe
            metric_type: Type de métrique (ex: "daily_gain", "feed_intake")
            target_value: Valeur cible

        Returns:
            ReverseLookupResult avec l'âge trouvé
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                SELECT 
                    m.age_min,
                    m.value_numeric as value,
                    m.unit,
                    ABS(m.value_numeric - $1) as difference
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name = $2
                  AND d.sex = $3
                  AND m.metric_name LIKE $4 || ' for %'
                  AND m.value_numeric IS NOT NULL
                ORDER BY difference ASC
                LIMIT 1
                """

                row = await conn.fetchrow(query, target_value, breed, sex, metric_type)

                if not row:
                    return ReverseLookupResult(
                        age_found=0,
                        value_found=0,
                        target_value=target_value,
                        difference=0,
                        unit="",
                        metric_type=metric_type,
                        confidence=0.0,
                    )

                # Confiance basée sur différence relative
                relative_diff = (
                    abs(row["difference"] / target_value) if target_value != 0 else 1.0
                )
                confidence = (
                    1.0 if relative_diff < 0.05 else 0.8 if relative_diff < 0.1 else 0.6
                )

                return ReverseLookupResult(
                    age_found=row["age_min"],
                    value_found=row["value"],
                    target_value=target_value,
                    difference=round(row["difference"], 2),
                    unit=row["unit"] or "",
                    metric_type=metric_type,
                    confidence=confidence,
                )

        except Exception as e:
            logger.error(f"Erreur recherche générique: {e}")
            return ReverseLookupResult(
                age_found=0,
                value_found=0,
                target_value=target_value,
                difference=0,
                unit="",
                metric_type=metric_type,
                confidence=0.0,
            )

    async def find_age_range_for_weight_range(
        self, breed: str, sex: str, min_weight: float, max_weight: float
    ) -> Dict:
        """
        Trouve la plage d'âges correspondant à une plage de poids

        Args:
            breed: Nom de la souche
            sex: Sexe
            min_weight: Poids minimum (g)
            max_weight: Poids maximum (g)

        Returns:
            Dict avec age_min, age_max
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                SELECT 
                    MIN(m.age_min) as age_min,
                    MAX(m.age_min) as age_max
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name = $1
                  AND d.sex = $2
                  AND m.metric_name LIKE 'body_weight for %'
                  AND m.value_numeric >= $3
                  AND m.value_numeric <= $4
                """

                row = await conn.fetchrow(query, breed, sex, min_weight, max_weight)

                if not row or row["age_min"] is None:
                    return {
                        "age_min": None,
                        "age_max": None,
                        "error": "Aucune donnée dans cette plage de poids",
                        "confidence": 0.0,
                    }

                return {
                    "age_min": row["age_min"],
                    "age_max": row["age_max"],
                    "weight_min": min_weight,
                    "weight_max": max_weight,
                    "duration_days": row["age_max"] - row["age_min"],
                    "confidence": 1.0,
                }

        except Exception as e:
            logger.error(f"Erreur recherche plage d'âges: {e}")
            return {
                "age_min": None,
                "age_max": None,
                "error": str(e),
                "confidence": 0.0,
            }
