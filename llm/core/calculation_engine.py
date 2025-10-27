# -*- coding: utf-8 -*-
"""
calculation_engine.py - Calculation and projection engine for metrics
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
calculation_engine.py - Calculation and projection engine for metrics
Handles complex calculations, projections and flock planning
"""

import logging
from utils.types import Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CalculationResult:
    """Calculation result"""

    value: float
    unit: str
    calculation_type: str
    details: Dict
    confidence: float = 1.0


class CalculationEngine:
    """Advanced calculation engine for poultry metrics"""

    def __init__(self, db_pool):
        """
        Args:
            db_pool: PostgreSQL connection pool (asyncpg)
        """
        self.db_pool = db_pool

    async def project_weight(
        self, breed: str, sex: str, age_start: int, age_end: int
    ) -> CalculationResult:
        """
        Projects future weight based on average growth rate

        Args:
            breed: Strain name (e.g. "308/308 FF", "500")
            sex: Sex ("male", "female", "as_hatched")
            age_start: Starting age (days)
            age_end: Target age (days)

        Returns:
            CalculationResult with projected weight
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get weights and gains between age_start and age_end
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
                        details={"error": "No data found"},
                        confidence=0.0,
                    )

                # Calculate average growth rate
                total_gain = sum(row["daily_gain"] for row in rows if row["daily_gain"])
                days_with_data = len([r for r in rows if r["daily_gain"]])

                if days_with_data == 0:
                    avg_growth_rate = 0
                else:
                    avg_growth_rate = total_gain / days_with_data

                # Starting weight
                weight_start = rows[0]["weight"]

                # Linear projection
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
            logger.error(f"Weight projection error: {e}")
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
        Calculates total feed consumption between two ages

        Method: Sum daily_intake day by day

        Note: For each age, there are 2 feed_intake values:
        - MIN = daily intake (e.g. 93g)
        - MAX = cumulative intake (e.g. 878g)
        We use MIN (daily) and sum them.

        Interpolation: If target_weight is provided and reached during the last day,
        the last day's consumption is adjusted proportionally.

        Args:
            breed: Strain name
            sex: Sex
            age_start: Starting age (days)
            age_end: Final age (days)
            target_weight: Target weight in grams (optional, for interpolation)

        Returns:
            CalculationResult with total consumption
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get all daily_intake between age_start and age_end
                # MIN(value_numeric) = daily intake (the smaller of 2 values per day)
                # Filter >= 10 to exclude imperial values
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
                    logger.warning(f"❌ No daily_intake data found between day {age_start} and {age_end}")
                    return CalculationResult(
                        value=0,
                        unit="g",
                        calculation_type="total_feed",
                        details={
                            "error": "No data available",
                            "breed": breed,
                            "sex": sex,
                            "age_start": age_start,
                            "age_end": age_end,
                        },
                        confidence=0.0,
                    )

                actual_age_start = rows[0]["age_min"]
                actual_age_end = rows[-1]["age_min"]

                # Proportional interpolation if target_weight provided
                interpolation_applied = False
                interpolation_ratio = 1.0

                if target_weight and len(rows) >= 2:
                    # Get weight from previous day and last day
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

                        # If target_weight is between the two weights, interpolate
                        if weight_previous < target_weight <= weight_final:
                            interpolation_ratio = (target_weight - weight_previous) / (weight_final - weight_previous)
                            interpolation_applied = True

                            logger.info(
                                f"🎯 Interpolation: target {target_weight}g between day {actual_age_end-1} "
                                f"({weight_previous}g) and day {actual_age_end} ({weight_final}g) "
                                f"→ ratio={interpolation_ratio:.2%}"
                            )

                # Calculate total with last day interpolation if applicable
                if interpolation_applied:
                    # Sum all days except last (convert Decimal to float)
                    total_feed_full_days = sum(float(row["daily_intake"]) for row in rows[:-1])
                    # Add fraction of last day (convert Decimal to float)
                    last_day_intake = float(rows[-1]["daily_intake"])
                    last_day_adjusted = last_day_intake * interpolation_ratio
                    total_feed = total_feed_full_days + last_day_adjusted

                    logger.info(
                        f"📊 Total feed: {len(rows)-1} full days ({total_feed_full_days}g) + "
                        f"{interpolation_ratio:.1%} of day {actual_age_end} ({last_day_adjusted:.1f}g) "
                        f"= {total_feed:.1f}g"
                    )
                else:
                    # No interpolation, sum normally (convert Decimal to float)
                    total_feed = sum(float(row["daily_intake"]) for row in rows)
                    logger.info(
                        f"📊 Feed calculation: {len(rows)} full days from {actual_age_start}→{actual_age_end}, "
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
            logger.error(f"❌ Feed calculation error: {e}", exc_info=True)
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
        Calculates average growth rate between two ages

        Returns:
            CalculationResult with rate in g/day
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
                        unit="g/day",
                        calculation_type="growth_rate",
                        details={"error": "Insufficient data"},
                        confidence=0.0,
                    )

                weight_start = rows[0]["weight"]
                weight_end = rows[1]["weight"]
                days = age_end - age_start

                growth_rate = (weight_end - weight_start) / days

                return CalculationResult(
                    value=round(growth_rate, 2),
                    unit="g/day",
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
            logger.error(f"Growth calculation error: {e}")
            return CalculationResult(
                value=0,
                unit="g/day",
                calculation_type="growth_rate",
                details={"error": str(e)},
                confidence=0.0,
            )

    async def calculate_feed_efficiency(
        self, breed: str, sex: str, age: int
    ) -> CalculationResult:
        """
        Calculates feed efficiency: grams of meat per kg of feed

        Returns:
            CalculationResult with efficiency in g meat / kg feed
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
                        unit="g meat / kg feed",
                        calculation_type="feed_efficiency",
                        details={"error": "Insufficient data"},
                        confidence=0.0,
                    )

                weight = row["weight"]
                intake_kg = row["cumulative_intake"] / 1000

                efficiency = weight / intake_kg

                return CalculationResult(
                    value=round(efficiency, 1),
                    unit="g meat / kg feed",
                    calculation_type="feed_efficiency",
                    details={
                        "weight_g": weight,
                        "intake_kg": round(intake_kg, 2),
                        "fcr": round(row["cumulative_intake"] / weight, 3),
                    },
                    confidence=1.0,
                )

        except Exception as e:
            logger.error(f"Feed efficiency calculation error: {e}")
            return CalculationResult(
                value=0,
                unit="g meat / kg feed",
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
        Calculates totals for a flock of X birds

        Args:
            breed: Strain name
            sex: Sex
            age: Age (days)
            flock_size: Number of birds
            mortality_pct: Mortality rate (%)

        Returns:
            Dict with total weight, total feed, etc.
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
                    return {"error": "Data not available", "confidence": 0.0}

                # Mortality adjustment
                surviving_birds = flock_size * (1 - mortality_pct / 100)

                # Convert Decimal to float for calculations
                weight_per_bird = float(row["weight"]) if row["weight"] else 0
                intake_per_bird = (
                    float(row["cumulative_intake"]) if row["cumulative_intake"] else 0
                )

                total_weight_kg = (weight_per_bird * surviving_birds) / 1000
                total_feed_kg = (intake_per_bird * flock_size) / 1000  # All birds consume

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
            logger.error(f"Flock calculation error: {e}")
            return {"error": str(e), "confidence": 0.0}
