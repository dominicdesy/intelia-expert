# -*- coding: utf-8 -*-
"""
optimization_engine.py - Moteur d'optimisation multi-critères
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
optimization_engine.py - Moteur d'optimisation multi-critères
Trouve les âges/paramètres optimaux selon contraintes
"""

import logging
from utils.types import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Résultat d'une optimisation"""

    optimal_age: int
    optimal_value: float
    metric_optimized: str
    constraints_met: Dict
    all_candidates: List[Dict]
    confidence: float = 1.0


class OptimizationEngine:
    """Moteur d'optimisation pour trouver paramètres optimaux"""

    def __init__(self, db_pool):
        """
        Args:
            db_pool: Pool de connexions PostgreSQL (asyncpg)
        """
        self.db_pool = db_pool

    async def find_optimal_age(
        self,
        breed: str,
        sex: str,
        objective: str,
        objective_value: float = None,
        constraints: Dict = None,
    ) -> OptimizationResult:
        """
        Trouve l'âge optimal selon un objectif et des contraintes

        Args:
            breed: Nom de la souche
            sex: Sexe
            objective: Métrique à optimiser ("fcr", "weight", "efficiency")
            objective_value: Valeur cible (optionnel)
            constraints: Dict de contraintes (ex: {"min_weight": 2000, "max_fcr": 1.5})

        Returns:
            OptimizationResult
        """
        constraints = constraints or {}

        try:
            async with self.db_pool.acquire() as conn:
                # Construction de la requête selon l'objectif
                if objective == "fcr":
                    return await self._optimize_fcr(
                        conn, breed, sex, objective_value, constraints
                    )
                elif objective == "weight":
                    return await self._optimize_weight(
                        conn, breed, sex, objective_value, constraints
                    )
                elif objective == "efficiency":
                    return await self._optimize_efficiency(
                        conn, breed, sex, constraints
                    )
                else:
                    return OptimizationResult(
                        optimal_age=0,
                        optimal_value=0,
                        metric_optimized=objective,
                        constraints_met={},
                        all_candidates=[],
                        confidence=0.0,
                    )

        except Exception as e:
            logger.error(f"Erreur optimisation: {e}")
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized=objective,
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

    async def _optimize_fcr(
        self, conn, breed: str, sex: str, target_fcr: float, constraints: Dict
    ) -> OptimizationResult:
        """Optimise pour trouver meilleur âge avec IC cible"""

        # Requête pour obtenir tous les candidats
        query = """
        SELECT 
            m.age_min as age,
            m.value_numeric as fcr,
            m2.value_numeric as weight
        FROM metrics m
        JOIN documents d ON m.document_id = d.id
        JOIN strains s ON d.strain_id = s.id
        LEFT JOIN metrics m2 ON m2.document_id = m.document_id
            AND m2.age_min = m.age_min
            AND m2.metric_name LIKE 'body_weight for %'
        WHERE s.strain_name = $1
          AND d.sex = $2
          AND m.metric_name LIKE 'feed_conversion_ratio for %'
          AND m.value_numeric IS NOT NULL
        ORDER BY m.age_min
        """

        rows = await conn.fetch(query, breed, sex)

        if not rows:
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized="fcr",
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

        # Filtrer selon contraintes
        candidates = []
        for row in rows:
            age = row["age"]
            fcr = row["fcr"]
            weight = row["weight"]

            # Vérifier contraintes
            meets_constraints = True
            constraints_status = {}

            if "min_weight" in constraints:
                meets_min_weight = weight >= constraints["min_weight"]
                meets_constraints = meets_constraints and meets_min_weight
                constraints_status["min_weight"] = meets_min_weight

            if "max_fcr" in constraints:
                meets_max_fcr = fcr <= constraints["max_fcr"]
                meets_constraints = meets_constraints and meets_max_fcr
                constraints_status["max_fcr"] = meets_max_fcr

            if "min_age" in constraints:
                meets_min_age = age >= constraints["min_age"]
                meets_constraints = meets_constraints and meets_min_age
                constraints_status["min_age"] = meets_min_age

            if "max_age" in constraints:
                meets_max_age = age <= constraints["max_age"]
                meets_constraints = meets_constraints and meets_max_age
                constraints_status["max_age"] = meets_max_age

            if meets_constraints:
                # Calculer distance à la cible si spécifiée
                if target_fcr:
                    distance = abs(fcr - target_fcr)
                else:
                    distance = fcr  # Minimiser IC

                candidates.append(
                    {
                        "age": age,
                        "fcr": fcr,
                        "weight": weight,
                        "distance": distance,
                        "constraints_met": constraints_status,
                    }
                )

        if not candidates:
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized="fcr",
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

        # Trouver meilleur candidat
        best = min(candidates, key=lambda x: x["distance"])

        return OptimizationResult(
            optimal_age=best["age"],
            optimal_value=best["fcr"],
            metric_optimized="fcr",
            constraints_met=best["constraints_met"],
            all_candidates=candidates[:5],  # Top 5
            confidence=0.9,
        )

    async def _optimize_weight(
        self, conn, breed: str, sex: str, target_weight: float, constraints: Dict
    ) -> OptimizationResult:
        """Optimise pour atteindre un poids cible avec contraintes"""

        query = """
        SELECT 
            m.age_min as age,
            m.value_numeric as weight,
            m2.value_numeric as fcr
        FROM metrics m
        JOIN documents d ON m.document_id = d.id
        JOIN strains s ON d.strain_id = s.id
        LEFT JOIN metrics m2 ON m2.document_id = m.document_id
            AND m2.age_min = m.age_min
            AND m2.metric_name LIKE 'feed_conversion_ratio for %'
        WHERE s.strain_name = $1
          AND d.sex = $2
          AND m.metric_name LIKE 'body_weight for %'
          AND m.value_numeric IS NOT NULL
        ORDER BY m.age_min
        """

        rows = await conn.fetch(query, breed, sex)

        if not rows:
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized="weight",
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

        candidates = []
        for row in rows:
            age = row["age"]
            weight = row["weight"]
            fcr = row["fcr"]

            meets_constraints = True
            constraints_status = {}

            if "max_fcr" in constraints:
                meets_max_fcr = fcr and fcr <= constraints["max_fcr"]
                meets_constraints = meets_constraints and meets_max_fcr
                constraints_status["max_fcr"] = meets_max_fcr

            if "max_age" in constraints:
                meets_max_age = age <= constraints["max_age"]
                meets_constraints = meets_constraints and meets_max_age
                constraints_status["max_age"] = meets_max_age

            if meets_constraints:
                distance = abs(weight - target_weight) if target_weight else -weight

                candidates.append(
                    {
                        "age": age,
                        "weight": weight,
                        "fcr": fcr,
                        "distance": distance,
                        "constraints_met": constraints_status,
                    }
                )

        if not candidates:
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized="weight",
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

        best = min(candidates, key=lambda x: abs(x["distance"]))

        return OptimizationResult(
            optimal_age=best["age"],
            optimal_value=best["weight"],
            metric_optimized="weight",
            constraints_met=best["constraints_met"],
            all_candidates=candidates[:5],
            confidence=0.9,
        )

    async def _optimize_efficiency(
        self, conn, breed: str, sex: str, constraints: Dict
    ) -> OptimizationResult:
        """Optimise pour meilleure efficacité alimentaire"""

        query = """
        SELECT 
            m.age_min as age,
            m.value_numeric as weight,
            m2.value_numeric as intake,
            m3.value_numeric as fcr
        FROM metrics m
        JOIN documents d ON m.document_id = d.id
        JOIN strains s ON d.strain_id = s.id
        LEFT JOIN metrics m2 ON m2.document_id = m.document_id
            AND m2.age_min = m.age_min
            AND m2.metric_name LIKE 'feed_intake for %'
        LEFT JOIN metrics m3 ON m3.document_id = m.document_id
            AND m3.age_min = m.age_min
            AND m3.metric_name LIKE 'feed_conversion_ratio for %'
        WHERE s.strain_name = $1
          AND d.sex = $2
          AND m.metric_name LIKE 'body_weight for %'
          AND m.value_numeric IS NOT NULL
        ORDER BY m.age_min
        """

        rows = await conn.fetch(query, breed, sex)

        if not rows:
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized="efficiency",
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

        candidates = []
        for row in rows:
            if not row["intake"] or row["intake"] == 0:
                continue

            age = row["age"]
            weight = row["weight"]
            intake = row["intake"]
            fcr = row["fcr"]

            # Efficacité = g viande / kg aliment
            efficiency = weight / (intake / 1000)

            meets_constraints = True
            constraints_status = {}

            if "min_weight" in constraints:
                meets_min_weight = weight >= constraints["min_weight"]
                meets_constraints = meets_constraints and meets_min_weight
                constraints_status["min_weight"] = meets_min_weight

            if meets_constraints:
                candidates.append(
                    {
                        "age": age,
                        "weight": weight,
                        "fcr": fcr,
                        "efficiency": efficiency,
                        "constraints_met": constraints_status,
                    }
                )

        if not candidates:
            return OptimizationResult(
                optimal_age=0,
                optimal_value=0,
                metric_optimized="efficiency",
                constraints_met={},
                all_candidates=[],
                confidence=0.0,
            )

        # Maximiser l'efficacité
        best = max(candidates, key=lambda x: x["efficiency"])

        return OptimizationResult(
            optimal_age=best["age"],
            optimal_value=round(best["efficiency"], 1),
            metric_optimized="efficiency",
            constraints_met=best["constraints_met"],
            all_candidates=sorted(candidates, key=lambda x: -x["efficiency"])[:5],
            confidence=0.85,
        )

    async def compare_scenarios(self, scenarios: List[Dict]) -> Dict:
        """
        Compare plusieurs scénarios d'élevage

        Args:
            scenarios: Liste de dicts avec breed, sex, age, etc.

        Returns:
            Dict avec comparaison détaillée
        """
        # TODO: Implémenter comparaison multi-scénarios
        return {"error": "Fonction non implémentée", "scenarios_count": len(scenarios)}
