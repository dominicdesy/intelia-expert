# -*- coding: utf-8 -*-
"""
calculation_engine.py - Moteur de calculs et projections sur les métriques
Gère les calculs complexes, projections et planification de troupeaux
"""

import logging
from utils.types import Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CalculationResult:
    """Résultat d'un calcul"""

    value: float
    unit: str
    calculation_type: str
    details: Dict
    confidence: float = 1.0


class CalculationEngine:
    """Moteur de calculs avancés sur les métriques avicoles"""

    def __init__(self, db_pool):
        """
        Args:
            db_pool: Pool de connexions PostgreSQL (asyncpg)
        """
        self.db_pool = db_pool

    async def project_weight(
        self, breed: str, sex: str, age_start: int, age_end: int
    ) -> CalculationResult:
        """
        Projette le poids futur basé sur le taux de croissance moyen

        Args:
            breed: Nom de la souche (ex: "308/308 FF", "500")
            sex: Sexe ("male", "female", "as_hatched")
            age_start: Âge de départ (jours)
            age_end: Âge cible (jours)

        Returns:
            CalculationResult avec poids projeté
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Récupérer poids et gains entre age_start et age_end
                query = """
                SELECT 
                    m.age_min,
                    m.value_numeric as weight,
                    m2.value_numeric as daily_gain
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                LEFT JOIN metrics m2 ON m2.document_id = m.document_id 
                    AND m2.age_min = m.age_min
                    AND m2.metric_name LIKE 'daily_gain for %'
                WHERE s.strain_name = $1
                  AND d.sex = $2
                  AND m.metric_name LIKE 'body_weight for %'
                  AND m.age_min >= $3
                  AND m.age_min <= $4
                ORDER BY m.age_min
                """

                rows = await conn.fetch(query, breed, sex, age_start, age_end)

                if not rows:
                    return CalculationResult(
                        value=0,
                        unit="g",
                        calculation_type="projection_weight",
                        details={"error": "Aucune données trouvées"},
                        confidence=0.0,
                    )

                # Calculer taux de croissance moyen
                total_gain = sum(row["daily_gain"] for row in rows if row["daily_gain"])
                days_with_data = len([r for r in rows if r["daily_gain"]])

                if days_with_data == 0:
                    avg_growth_rate = 0
                else:
                    avg_growth_rate = total_gain / days_with_data

                # Poids au départ
                weight_start = rows[0]["weight"]

                # Projection linéaire
                days_to_project = age_end - age_start
                projected_weight = weight_start + (avg_growth_rate * days_to_project)

                return CalculationResult(
                    value=round(projected_weight, 1),
                    unit="g",
                    calculation_type="projection_weight",
                    details={
                        "weight_start": weight_start,
                        "age_start": age_start,
                        "age_end": age_end,
                        "avg_growth_rate": round(avg_growth_rate, 2),
                        "days_projected": days_to_project,
                    },
                    confidence=0.85,
                )

        except Exception as e:
            logger.error(f"Erreur projection poids: {e}")
            return CalculationResult(
                value=0,
                unit="g",
                calculation_type="projection_weight",
                details={"error": str(e)},
                confidence=0.0,
            )

    async def calculate_total_feed(
        self, breed: str, sex: str, age_start: int, age_end: int, target_weight: float = None
    ) -> CalculationResult:
        """
        Calcule la consommation totale d'aliment entre deux âges

        Méthode: Additionner les daily_intake jour par jour

        Note: Pour chaque âge, il y a 2 valeurs feed_intake:
        - MIN = daily intake (consommation quotidienne, ex: 93g)
        - MAX = cumulative intake (consommation cumulée, ex: 878g)
        On utilise MIN (daily) et on additionne.

        Interpolation: Si target_weight est fourni et atteint pendant le dernier jour,
        la consommation du dernier jour est ajustée proportionnellement.

        Args:
            breed: Nom de la souche
            sex: Sexe
            age_start: Âge de départ (jours)
            age_end: Âge final (jours)
            target_weight: Poids cible en grammes (optionnel, pour interpolation)

        Returns:
            CalculationResult avec consommation totale
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Récupérer tous les daily_intake entre age_start et age_end
                # MIN(value_numeric) = daily intake (la plus petite des 2 valeurs par jour)
                # Filtre >= 10 pour exclure valeurs impériales
                query = """
                SELECT
                    m.age_min,
                    MIN(m.value_numeric) as daily_intake
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name = $1
                  AND d.sex = $2
                  AND m.metric_name LIKE 'feed_intake for %'
                  AND m.value_numeric IS NOT NULL
                  AND m.value_numeric >= 10
                  AND m.age_min >= $3
                  AND m.age_min <= $4
                GROUP BY m.age_min
                ORDER BY m.age_min
                """

                rows = await conn.fetch(query, breed, sex, age_start, age_end)

                if not rows or len(rows) == 0:
                    logger.warning(f"❌ Aucune donnée daily_intake trouvée entre jour {age_start} et {age_end}")
                    return CalculationResult(
                        value=0,
                        unit="g",
                        calculation_type="total_feed",
                        details={
                            "error": "Aucune donnée disponible",
                            "breed": breed,
                            "sex": sex,
                            "age_start": age_start,
                            "age_end": age_end,
                        },
                        confidence=0.0,
                    )

                actual_age_start = rows[0]["age_min"]
                actual_age_end = rows[-1]["age_min"]

                # Interpolation proportionnelle si target_weight fourni
                interpolation_applied = False
                interpolation_ratio = 1.0

                if target_weight and len(rows) >= 2:
                    # Récupérer poids du jour précédent et du dernier jour
                    query_weights = """
                    SELECT
                        m.age_min,
                        MAX(m.value_numeric) as body_weight
                    FROM metrics m
                    JOIN documents d ON m.document_id = d.id
                    JOIN strains s ON d.strain_id = s.id
                    WHERE s.strain_name = $1
                      AND d.sex = $2
                      AND m.metric_name LIKE 'body_weight for %'
                      AND m.value_numeric IS NOT NULL
                      AND m.age_min IN ($3, $4)
                    GROUP BY m.age_min
                    ORDER BY m.age_min
                    """

                    weight_rows = await conn.fetch(
                        query_weights, breed, sex, actual_age_end - 1, actual_age_end
                    )

                    if len(weight_rows) == 2:
                        weight_previous = weight_rows[0]["body_weight"]
                        weight_final = weight_rows[1]["body_weight"]

                        # Si target_weight est entre les deux poids, interpoler
                        if weight_previous < target_weight <= weight_final:
                            interpolation_ratio = (target_weight - weight_previous) / (weight_final - weight_previous)
                            interpolation_applied = True

                            logger.info(
                                f"🎯 Interpolation: target {target_weight}g entre jour {actual_age_end-1} "
                                f"({weight_previous}g) et jour {actual_age_end} ({weight_final}g) "
                                f"→ ratio={interpolation_ratio:.2%}"
                            )

                # Calculer total avec interpolation du dernier jour si applicable
                if interpolation_applied:
                    # Sommer tous les jours sauf le dernier (convert Decimal to float)
                    total_feed_full_days = sum(float(row["daily_intake"]) for row in rows[:-1])
                    # Ajouter fraction du dernier jour (convert Decimal to float)
                    last_day_intake = float(rows[-1]["daily_intake"])
                    last_day_adjusted = last_day_intake * interpolation_ratio
                    total_feed = total_feed_full_days + last_day_adjusted

                    logger.info(
                        f"📊 Feed total: {len(rows)-1} jours complets ({total_feed_full_days}g) + "
                        f"{interpolation_ratio:.1%} du jour {actual_age_end} ({last_day_adjusted:.1f}g) "
                        f"= {total_feed:.1f}g"
                    )
                else:
                    # Pas d'interpolation, sommer normalement (convert Decimal to float)
                    total_feed = sum(float(row["daily_intake"]) for row in rows)
                    logger.info(
                        f"📊 Feed calculation: {len(rows)} jours complets de {actual_age_start}→{actual_age_end}, "
                        f"total={total_feed}g ({round(total_feed/1000, 2)}kg)"
                    )

                days_count = len(rows)
                avg_daily = total_feed / days_count if days_count > 0 else 0

                return CalculationResult(
                    value=round(total_feed, 1),
                    unit="g",
                    calculation_type="total_feed",
                    details={
                        "age_start_requested": age_start,
                        "age_end_requested": age_end,
                        "age_start_actual": actual_age_start,
                        "age_end_actual": actual_age_end,
                        "days_count": days_count,
                        "avg_daily_intake": round(avg_daily, 2),
                        "total_kg": round(total_feed / 1000, 2),
                        "interpolation_applied": interpolation_applied,
                        "interpolation_ratio": round(interpolation_ratio, 3) if interpolation_applied else None,
                    },
                    confidence=1.0,
                )

        except Exception as e:
            logger.error(f"❌ Erreur calcul consommation: {e}", exc_info=True)
            return CalculationResult(
                value=0,
                unit="g",
                calculation_type="total_feed",
                details={"error": str(e)},
                confidence=0.0,
            )

    async def calculate_growth_rate(
        self, breed: str, sex: str, age_start: int, age_end: int
    ) -> CalculationResult:
        """
        Calcule le taux de croissance moyen entre deux âges

        Returns:
            CalculationResult avec taux en g/jour
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                SELECT 
                    m.age_min,
                    m.value_numeric as weight
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                WHERE s.strain_name = $1
                  AND d.sex = $2
                  AND m.metric_name LIKE 'body_weight for %'
                  AND m.age_min IN ($3, $4)
                ORDER BY m.age_min
                """

                rows = await conn.fetch(query, breed, sex, age_start, age_end)

                if len(rows) < 2:
                    return CalculationResult(
                        value=0,
                        unit="g/jour",
                        calculation_type="growth_rate",
                        details={"error": "Données insuffisantes"},
                        confidence=0.0,
                    )

                weight_start = rows[0]["weight"]
                weight_end = rows[1]["weight"]
                days = age_end - age_start

                growth_rate = (weight_end - weight_start) / days

                return CalculationResult(
                    value=round(growth_rate, 2),
                    unit="g/jour",
                    calculation_type="growth_rate",
                    details={
                        "weight_start": weight_start,
                        "weight_end": weight_end,
                        "total_gain": weight_end - weight_start,
                        "days": days,
                    },
                    confidence=1.0,
                )

        except Exception as e:
            logger.error(f"Erreur calcul croissance: {e}")
            return CalculationResult(
                value=0,
                unit="g/jour",
                calculation_type="growth_rate",
                details={"error": str(e)},
                confidence=0.0,
            )

    async def calculate_feed_efficiency(
        self, breed: str, sex: str, age: int
    ) -> CalculationResult:
        """
        Calcule l'efficacité alimentaire: grammes de viande par kg d'aliment

        Returns:
            CalculationResult avec efficacité en g viande / kg aliment
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                SELECT 
                    m.value_numeric as weight,
                    m2.value_numeric as cumulative_intake
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                LEFT JOIN metrics m2 ON m2.document_id = m.document_id
                    AND m2.age_min = m.age_min
                    AND m2.metric_name LIKE 'feed_intake for %'
                WHERE s.strain_name = $1
                  AND d.sex = $2
                  AND m.metric_name LIKE 'body_weight for %'
                  AND m.age_min = $3
                """

                row = await conn.fetchrow(query, breed, sex, age)

                if not row or not row["cumulative_intake"]:
                    return CalculationResult(
                        value=0,
                        unit="g viande / kg aliment",
                        calculation_type="feed_efficiency",
                        details={"error": "Données insuffisantes"},
                        confidence=0.0,
                    )

                weight = row["weight"]
                intake_kg = row["cumulative_intake"] / 1000

                efficiency = weight / intake_kg

                return CalculationResult(
                    value=round(efficiency, 1),
                    unit="g viande / kg aliment",
                    calculation_type="feed_efficiency",
                    details={
                        "weight_g": weight,
                        "intake_kg": round(intake_kg, 2),
                        "fcr": round(row["cumulative_intake"] / weight, 3),
                    },
                    confidence=1.0,
                )

        except Exception as e:
            logger.error(f"Erreur calcul efficacité: {e}")
            return CalculationResult(
                value=0,
                unit="g viande / kg aliment",
                calculation_type="feed_efficiency",
                details={"error": str(e)},
                confidence=0.0,
            )

    async def calculate_flock_totals(
        self,
        breed: str,
        sex: str,
        age: int,
        flock_size: int,
        mortality_pct: float = 0.0,
    ) -> Dict:
        """
        Calcule les totaux pour un troupeau de X oiseaux

        Args:
            breed: Nom de la souche
            sex: Sexe
            age: Âge (jours)
            flock_size: Nombre d'oiseaux
            mortality_pct: Taux de mortalité (%)

        Returns:
            Dict avec poids total, aliment total, etc.
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                SELECT 
                    m.value_numeric as weight,
                    m2.value_numeric as cumulative_intake
                FROM metrics m
                JOIN documents d ON m.document_id = d.id
                JOIN strains s ON d.strain_id = s.id
                LEFT JOIN metrics m2 ON m2.document_id = m.document_id
                    AND m2.age_min = m.age_min
                    AND m2.metric_name LIKE 'feed_intake for %'
                WHERE s.strain_name = $1
                  AND d.sex = $2
                  AND m.metric_name LIKE 'body_weight for %'
                  AND m.age_min = $3
                """

                row = await conn.fetchrow(query, breed, sex, age)

                if not row:
                    return {"error": "Données non disponibles", "confidence": 0.0}

                # Ajustement mortalité
                surviving_birds = flock_size * (1 - mortality_pct / 100)

                # Convert Decimal to float for calculations
                weight_per_bird = float(row["weight"]) if row["weight"] else 0
                intake_per_bird = (
                    float(row["cumulative_intake"]) if row["cumulative_intake"] else 0
                )

                total_weight_kg = (weight_per_bird * surviving_birds) / 1000
                total_feed_kg = (intake_per_bird * flock_size) / 1000  # Tous consomment

                return {
                    "flock_size": flock_size,
                    "surviving_birds": int(surviving_birds),
                    "mortality_pct": mortality_pct,
                    "age_days": age,
                    "weight_per_bird_g": weight_per_bird,
                    "total_live_weight_kg": round(total_weight_kg, 1),
                    "feed_per_bird_kg": round(intake_per_bird / 1000, 2),
                    "total_feed_consumed_kg": round(total_feed_kg, 1),
                    "avg_fcr": (
                        round(intake_per_bird / weight_per_bird, 3)
                        if weight_per_bird > 0
                        else None
                    ),
                    "confidence": 1.0,
                }

        except Exception as e:
            logger.error(f"Erreur calcul troupeau: {e}")
            return {"error": str(e), "confidence": 0.0}
