# -*- coding: utf-8 -*-
"""
multi_step_orchestrator.py - Orchestration de requêtes complexes multi-étapes
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
multi_step_orchestrator.py - Orchestration de requêtes complexes multi-étapes
Décompose et exécute des requêtes nécessitant plusieurs étapes
"""

import logging
from utils.types import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QueryStep:
    """Une étape d'une requête multi-étapes"""

    step_number: int
    description: str
    query_type: str
    parameters: Dict
    dependencies: List[int]  # Numéros d'étapes dont celle-ci dépend


@dataclass
class OrchestrationResult:
    """Résultat d'une orchestration multi-étapes"""

    success: bool
    steps_executed: int
    results: List[Dict]
    final_result: Dict
    execution_time: float


class MultiStepOrchestrator:
    """Orchestre l'exécution de requêtes complexes en plusieurs étapes"""

    def __init__(
        self, calculation_engine, reverse_lookup, optimization_engine, db_pool
    ):
        """
        Args:
            calculation_engine: Instance de CalculationEngine
            reverse_lookup: Instance de ReverseLookup
            optimization_engine: Instance de OptimizationEngine
            db_pool: Pool de connexions PostgreSQL
        """
        self.calculation_engine = calculation_engine
        self.reverse_lookup = reverse_lookup
        self.optimization_engine = optimization_engine
        self.db_pool = db_pool

    async def decompose_complex_query(
        self, query: str, entities: Dict[str, str]
    ) -> List[QueryStep]:
        """
        Décompose une requête complexe en étapes simples

        Args:
            query: Requête utilisateur complexe
            entities: Entités extraites

        Returns:
            Liste de QueryStep à exécuter
        """
        query_lower = query.lower()
        steps = []

        # Détection pattern: "X poulets avec Y% mortalité"
        if "mortalité" in query_lower or "mortality" in query_lower:
            steps.extend(self._decompose_mortality_query(query, entities))

        # Détection pattern: "si je change X, quel impact sur Y"
        elif "si je change" in query_lower or "if i change" in query_lower:
            steps.extend(self._decompose_scenario_query(query, entities))

        # Détection pattern: "poids total + aliment total"
        elif "total" in query_lower and ("+" in query or "et" in query_lower):
            steps.extend(self._decompose_aggregation_query(query, entities))

        # Détection pattern: "optimisation multi-objectifs"
        elif "optimis" in query_lower and (
            "multi" in query_lower or "plusieurs" in query_lower
        ):
            steps.extend(self._decompose_optimization_query(query, entities))

        return steps

    def _decompose_mortality_query(
        self, query: str, entities: Dict[str, str]
    ) -> List[QueryStep]:
        """
        Décompose requête avec ajustement mortalité
        Exemple: "10,000 Ross 308 jusqu'à 42j avec 5% mortalité"
        """
        steps = []

        # Étape 1: Obtenir performances de base
        steps.append(
            QueryStep(
                step_number=1,
                description="Récupérer performances de base par oiseau",
                query_type="base_performance",
                parameters={
                    "breed": entities.get("breed", ""),
                    "sex": entities.get("sex", "as_hatched"),
                    "age": entities.get("age_days", "42"),
                },
                dependencies=[],
            )
        )

        # Étape 2: Calculer totaux troupeau avec mortalité
        steps.append(
            QueryStep(
                step_number=2,
                description="Calculer totaux troupeau avec ajustement mortalité",
                query_type="flock_calculation_with_mortality",
                parameters={
                    "flock_size": self._extract_flock_size(query),
                    "mortality_pct": self._extract_mortality_pct(query),
                },
                dependencies=[1],
            )
        )

        return steps

    def _decompose_scenario_query(
        self, query: str, entities: Dict[str, str]
    ) -> List[QueryStep]:
        """
        Décompose requête de scénario "si je change X"
        """
        steps = []

        # Étape 1: Scénario de base
        steps.append(
            QueryStep(
                step_number=1,
                description="Calculer scénario de base",
                query_type="base_scenario",
                parameters=entities.copy(),
                dependencies=[],
            )
        )

        # Étape 2: Scénario modifié
        modified_params = self._extract_scenario_modifications(query, entities)
        steps.append(
            QueryStep(
                step_number=2,
                description="Calculer scénario modifié",
                query_type="modified_scenario",
                parameters=modified_params,
                dependencies=[],
            )
        )

        # Étape 3: Comparaison
        steps.append(
            QueryStep(
                step_number=3,
                description="Comparer les deux scénarios",
                query_type="scenario_comparison",
                parameters={},
                dependencies=[1, 2],
            )
        )

        return steps

    def _decompose_aggregation_query(
        self, query: str, entities: Dict[str, str]
    ) -> List[QueryStep]:
        """
        Décompose requête d'agrégation multiple
        Exemple: "poids total + aliment total pour 5000 poulets"
        """
        steps = []

        metrics_requested = self._extract_multiple_metrics(query)

        for idx, metric in enumerate(metrics_requested, 1):
            steps.append(
                QueryStep(
                    step_number=idx,
                    description=f"Calculer {metric}",
                    query_type="metric_calculation",
                    parameters={"metric": metric, **entities},
                    dependencies=[],
                )
            )

        # Étape finale: agrégation
        steps.append(
            QueryStep(
                step_number=len(metrics_requested) + 1,
                description="Agréger tous les résultats",
                query_type="aggregate_results",
                parameters={},
                dependencies=list(range(1, len(metrics_requested) + 1)),
            )
        )

        return steps

    def _decompose_optimization_query(
        self, query: str, entities: Dict[str, str]
    ) -> List[QueryStep]:
        """
        Décompose requête d'optimisation multi-objectifs
        """
        steps = []

        objectives = self._extract_objectives(query)
        constraints = self._extract_constraints(query)

        # Étape 1: Optimisation pour chaque objectif
        for idx, objective in enumerate(objectives, 1):
            steps.append(
                QueryStep(
                    step_number=idx,
                    description=f"Optimiser pour {objective}",
                    query_type="single_optimization",
                    parameters={
                        "objective": objective,
                        "constraints": constraints,
                        **entities,
                    },
                    dependencies=[],
                )
            )

        # Étape finale: compromis multi-objectifs
        steps.append(
            QueryStep(
                step_number=len(objectives) + 1,
                description="Trouver compromis optimal",
                query_type="multi_objective_compromise",
                parameters={"objectives": objectives},
                dependencies=list(range(1, len(objectives) + 1)),
            )
        )

        return steps

    async def execute_query_sequence(
        self, steps: List[QueryStep]
    ) -> OrchestrationResult:
        """
        Exécute une séquence d'étapes

        Args:
            steps: Liste de QueryStep à exécuter

        Returns:
            OrchestrationResult avec résultats de toutes les étapes
        """
        import time

        start_time = time.time()

        results = {}

        try:
            for step in steps:
                # Vérifier dépendances
                dependencies_met = all(dep in results for dep in step.dependencies)

                if not dependencies_met:
                    logger.error(
                        f"Dépendances non satisfaites pour step {step.step_number}"
                    )
                    continue

                # Injecter résultats des dépendances
                step_params = step.parameters.copy()
                for dep in step.dependencies:
                    step_params[f"step_{dep}_result"] = results[dep]

                # Exécuter l'étape
                result = await self._execute_single_step(step, step_params)
                results[step.step_number] = result

            execution_time = time.time() - start_time

            # Résultat final = dernière étape
            final_result = results.get(max(results.keys()), {}) if results else {}

            return OrchestrationResult(
                success=True,
                steps_executed=len(results),
                results=list(results.values()),
                final_result=final_result,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Erreur orchestration: {e}")
            execution_time = time.time() - start_time

            return OrchestrationResult(
                success=False,
                steps_executed=len(results),
                results=list(results.values()),
                final_result={"error": str(e)},
                execution_time=execution_time,
            )

    async def _execute_single_step(self, step: QueryStep, parameters: Dict) -> Dict:
        """
        Exécute une seule étape

        Args:
            step: QueryStep à exécuter
            parameters: Paramètres incluant résultats dépendances

        Returns:
            Résultat de l'étape
        """
        query_type = step.query_type

        try:
            if query_type == "base_performance":
                return await self._get_base_performance(parameters)

            elif query_type == "flock_calculation_with_mortality":
                return await self.handle_mortality_adjustments(
                    parameters["step_1_result"],
                    parameters.get("flock_size", 1000),
                    parameters.get("mortality_pct", 0),
                )

            elif query_type in ["base_scenario", "modified_scenario"]:
                return await self._calculate_scenario(parameters)

            elif query_type == "scenario_comparison":
                return self._compare_scenarios(
                    parameters["step_1_result"], parameters["step_2_result"]
                )

            elif query_type == "metric_calculation":
                return await self._calculate_metric(parameters)

            elif query_type == "aggregate_results":
                return self.aggregate_results(
                    [parameters[f"step_{i}_result"] for i in step.dependencies]
                )

            elif query_type == "single_optimization":
                return await self._run_optimization(parameters)

            elif query_type == "multi_objective_compromise":
                return self._find_compromise(
                    [parameters[f"step_{i}_result"] for i in step.dependencies]
                )

            else:
                return {"error": f"Type de requête inconnu: {query_type}"}

        except Exception as e:
            logger.error(f"Erreur exécution step {step.step_number}: {e}")
            return {"error": str(e)}

    async def _get_base_performance(self, params: Dict) -> Dict:
        """Récupère performances de base"""
        async with self.db_pool.acquire() as conn:
            query = """
            SELECT 
                m.value_numeric as weight,
                m2.value_numeric as fcr,
                m3.value_numeric as intake
            FROM metrics m
            JOIN documents d ON m.document_id = d.id
            JOIN strains s ON d.strain_id = s.id
            LEFT JOIN metrics m2 ON m2.document_id = m.document_id
                AND m2.age_min = m.age_min
                AND m2.metric_name LIKE 'feed_conversion_ratio for %'
            LEFT JOIN metrics m3 ON m3.document_id = m.document_id
                AND m3.age_min = m.age_min
                AND m3.metric_name LIKE 'feed_intake for %'
            WHERE s.strain_name LIKE $1
              AND d.sex = $2
              AND m.metric_name LIKE 'body_weight for %'
              AND m.age_min = $3
            """

            row = await conn.fetchrow(
                query, f"%{params['breed']}%", params["sex"], int(params["age"])
            )

            if row:
                return {
                    "weight_g": row["weight"],
                    "fcr": row["fcr"],
                    "intake_g": row["intake"],
                }
            return {}

    async def handle_mortality_adjustments(
        self, base_result: Dict, flock_size: int, mortality_pct: float
    ) -> Dict:
        """
        Ajuste les calculs selon la mortalité

        Args:
            base_result: Résultats de base par oiseau
            flock_size: Taille du troupeau
            mortality_pct: Pourcentage de mortalité

        Returns:
            Dict avec totaux ajustés
        """
        surviving_birds = int(flock_size * (1 - mortality_pct / 100))
        dead_birds = flock_size - surviving_birds

        weight_per_bird = base_result.get("weight_g", 0)
        intake_per_bird = base_result.get("intake_g", 0)

        return {
            "flock_size_initial": flock_size,
            "surviving_birds": surviving_birds,
            "dead_birds": dead_birds,
            "mortality_pct": mortality_pct,
            "total_live_weight_kg": (weight_per_bird * surviving_birds) / 1000,
            "total_feed_consumed_kg": (intake_per_bird * flock_size) / 1000,
            "avg_fcr": base_result.get("fcr", 0),
        }

    async def _calculate_scenario(self, params: Dict) -> Dict:
        """Calcule un scénario complet"""
        # Utiliser calculation_engine pour calculs
        result = await self.calculation_engine.calculate_flock_totals(
            breed=params.get("breed", ""),
            sex=params.get("sex", "as_hatched"),
            age=int(params.get("age", 42)),
            flock_size=params.get("flock_size", 1000),
            mortality_pct=params.get("mortality_pct", 0),
        )
        return result

    def _compare_scenarios(self, scenario1: Dict, scenario2: Dict) -> Dict:
        """Compare deux scénarios"""
        return {
            "scenario_1": scenario1,
            "scenario_2": scenario2,
            "differences": {
                "weight_diff_kg": scenario2.get("total_live_weight_kg", 0)
                - scenario1.get("total_live_weight_kg", 0),
                "feed_diff_kg": scenario2.get("total_feed_consumed_kg", 0)
                - scenario1.get("total_feed_consumed_kg", 0),
            },
        }

    async def _calculate_metric(self, params: Dict) -> Dict:
        """Calcule une métrique spécifique"""
        metric = params.get("metric", "")

        if "weight" in metric.lower():
            result = await self.calculation_engine.calculate_flock_totals(
                breed=params.get("breed", ""),
                sex=params.get("sex", "as_hatched"),
                age=int(params.get("age", 42)),
                flock_size=params.get("flock_size", 1),
                mortality_pct=0,
            )
            return {"metric": metric, "value": result.get("total_live_weight_kg", 0)}

        return {"metric": metric, "value": 0}

    def aggregate_results(self, results_list: List[Dict]) -> Dict:
        """Agrège plusieurs résultats"""
        aggregated = {"total_metrics": len(results_list), "metrics": results_list}
        return aggregated

    async def _run_optimization(self, params: Dict) -> Dict:
        """Lance une optimisation"""
        result = await self.optimization_engine.find_optimal_age(
            breed=params.get("breed", ""),
            sex=params.get("sex", "as_hatched"),
            objective=params.get("objective", "fcr"),
            constraints=params.get("constraints", {}),
        )
        return result.__dict__

    def _find_compromise(self, optimization_results: List[Dict]) -> Dict:
        """Trouve compromis entre plusieurs optimisations"""
        # Logique simple: moyenne des âges optimaux
        ages = [
            r.get("optimal_age", 0)
            for r in optimization_results
            if r.get("optimal_age")
        ]

        if ages:
            return {
                "compromise_age": int(sum(ages) / len(ages)),
                "individual_optimals": optimization_results,
            }

        return {"error": "Impossible de trouver compromis"}

    # Fonctions utilitaires d'extraction

    def _extract_flock_size(self, query: str) -> int:
        """Extrait la taille du troupeau de la requête"""
        import re

        numbers = re.findall(r"\b(\d{1,3}(?:[,\s]\d{3})*|\d+)\b", query)

        for num_str in numbers:
            num = int(num_str.replace(",", "").replace(" ", ""))
            if num > 100:  # Probablement taille de troupeau
                return num

        return 1000  # Défaut

    def _extract_mortality_pct(self, query: str) -> float:
        """Extrait le pourcentage de mortalité"""
        import re

        match = re.search(r"(\d+(?:\.\d+)?)\s*%", query)
        if match:
            return float(match.group(1))
        return 0.0

    def _extract_scenario_modifications(self, query: str, base_entities: Dict) -> Dict:
        """Extrait les modifications de scénario demandées dans la requête"""
        import re

        modified = base_entities.copy()
        query_lower = query.lower()

        # Parser les modifications de souche/breed
        breed_patterns = [
            r"(?:avec|pour|utilise[rz]?)\s+(?:la souche|le breed)?\s*([A-Za-z]+\s*\d+)",
            r"(?:chang(?:er|ez)|modifi(?:er|ez)|remplace[rz]?)\s+(?:par|avec|pour)\s+([A-Za-z]+\s*\d+)",
            r"(?:si|avec)\s+([A-Za-z]+\s*\d+)\s+(?:à la place|au lieu)"
        ]
        for pattern in breed_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                modified["breed"] = match.group(1).strip()
                break

        # Parser les modifications de sexe
        if re.search(r"\b(?:mâles?|males?|coqs?)\b", query_lower):
            modified["sex"] = "male"
        elif re.search(r"\b(?:femelles?|poules?|poulettes?)\b", query_lower):
            modified["sex"] = "female"
        elif re.search(r"\b(?:mixt?es?|ensemble)\b", query_lower):
            modified["sex"] = "mixed"

        # Parser les modifications d'âge
        age_patterns = [
            r"à\s+(\d+)\s+jours?",
            r"(\d+)\s+jours?",
            r"J\s*(\d+)",
            r"semaine\s+(\d+)",  # Convertir semaines en jours
        ]
        for i, pattern in enumerate(age_patterns):
            match = re.search(pattern, query)
            if match:
                age = int(match.group(1))
                # Convertir semaines en jours si nécessaire
                if i == 3:
                    age *= 7
                modified["age_days"] = age
                break

        # Parser les modifications de température/conditions
        temp_match = re.search(r"(\d+)\s*[°C]", query)
        if temp_match:
            modified["temperature"] = int(temp_match.group(1))

        # Parser les modifications de densité
        density_patterns = [
            r"(\d+)\s*(?:oiseaux?|poulets?|sujets?)\s*(?:par|/)\s*m[²2]",
            r"densité\s*(?:de)?\s*(\d+)"
        ]
        for pattern in density_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                modified["density"] = int(match.group(1))
                break

        # Parser les modifications de régime alimentaire
        if re.search(r"\b(?:sans|pas de)\s+(?:antibiotique|atb)\b", query_lower):
            modified["antibiotic_free"] = True
        if re.search(r"\bavec\s+(?:antibiotique|atb)\b", query_lower):
            modified["antibiotic_free"] = False

        # Parser les modifications de formulation
        if re.search(r"\b(?:maïs|corn)\b", query_lower):
            modified["feed_base"] = "corn"
        elif re.search(r"\b(?:blé|wheat)\b", query_lower):
            modified["feed_base"] = "wheat"

        return modified

    def _extract_multiple_metrics(self, query: str) -> List[str]:
        """Extrait plusieurs métriques demandées"""
        metrics = []
        if "poids" in query.lower() or "weight" in query.lower():
            metrics.append("weight")
        if "aliment" in query.lower() or "feed" in query.lower():
            metrics.append("feed")
        if "ic" in query.lower() or "fcr" in query.lower():
            metrics.append("fcr")
        return metrics if metrics else ["weight"]

    def _extract_objectives(self, query: str) -> List[str]:
        """Extrait les objectifs d'optimisation"""
        objectives = []
        if "ic" in query.lower() or "conversion" in query.lower():
            objectives.append("fcr")
        if "poids" in query.lower() or "weight" in query.lower():
            objectives.append("weight")
        return objectives if objectives else ["fcr"]

    def _extract_constraints(self, query: str) -> Dict:
        """Extrait les contraintes complexes de la requête"""
        import re

        constraints = {}
        query_lower = query.lower()

        # Contraintes de poids (min/max)
        weight_patterns = [
            (r"poids\s+(?:mini(?:mum|mal)?|min)\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:kg|g)?", "min_weight"),
            (r"poids\s+(?:maxi(?:mum|mal)?|max)\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:kg|g)?", "max_weight"),
            (r"au moins\s+(\d+(?:\.\d+)?)\s*(?:kg|g)", "min_weight"),
            (r"maximum\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:kg|g)", "max_weight"),
        ]
        for pattern, key in weight_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # Convertir kg en g si nécessaire
                if "kg" in match.group(0).lower():
                    value *= 1000
                constraints[key] = value

        # Contraintes de FCR (IC)
        fcr_patterns = [
            (r"ic\s+(?:inférieur|inf|<)\s+(?:à\s+)?(\d+(?:\.\d+)?)", "max_fcr"),
            (r"ic\s+(?:supérieur|sup|>)\s+(?:à\s+)?(\d+(?:\.\d+)?)", "min_fcr"),
            (r"fcr\s+(?:below|under|<)\s+(\d+(?:\.\d+)?)", "max_fcr"),
            (r"fcr\s+(?:above|over|>)\s+(\d+(?:\.\d+)?)", "min_fcr"),
            (r"meilleur que\s+(\d+(?:\.\d+)?)", "max_fcr"),
        ]
        for pattern, key in fcr_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                constraints[key] = float(match.group(1))

        # Contraintes de mortalité
        mortality_patterns = [
            (r"mortalité\s+(?:max|maximum|inférieure?)\s+(?:à|de)?\s+(\d+(?:\.\d+)?)\s*%", "max_mortality"),
            (r"(?:moins|max)\s+(\d+(?:\.\d+)?)\s*%\s+(?:de\s+)?mortalité", "max_mortality"),
        ]
        for pattern, key in mortality_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                constraints[key] = float(match.group(1))

        # Contraintes de gain quotidien
        gain_patterns = [
            (r"gain\s+(?:quotidien|journalier)\s+(?:min|minimum)\s+(?:de\s+)?(\d+(?:\.\d+)?)", "min_daily_gain"),
            (r"gain\s+(?:quotidien|journalier)\s+(?:max|maximum)\s+(?:de\s+)?(\d+(?:\.\d+)?)", "max_daily_gain"),
            (r"(?:au moins|minimum)\s+(\d+(?:\.\d+)?)\s*g?/j(?:our)?", "min_daily_gain"),
        ]
        for pattern, key in gain_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                constraints[key] = float(match.group(1))

        # Contraintes d'âge
        age_patterns = [
            (r"avant\s+(\d+)\s+jours?", "max_age"),
            (r"après\s+(\d+)\s+jours?", "min_age"),
            (r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?", "age_range"),
            (r"(?:moins|max)\s+de\s+(\d+)\s+jours?", "max_age"),
        ]
        for pattern, key in age_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if key == "age_range":
                    constraints["min_age"] = int(match.group(1))
                    constraints["max_age"] = int(match.group(2))
                else:
                    constraints[key] = int(match.group(1))

        # Contraintes budgétaires/économiques
        budget_patterns = [
            (r"budget\s+(?:max|maximum)\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*€", "max_budget"),
            (r"coût\s+(?:max|maximum)\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*€", "max_cost"),
            (r"moins de\s+(\d+(?:\.\d+)?)\s*€", "max_budget"),
        ]
        for pattern, key in budget_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                constraints[key] = float(match.group(1))

        # Contraintes de température
        temp_patterns = [
            (r"température\s+(?:min|minimum)\s+(?:de\s+)?(\d+)\s*°?C?", "min_temperature"),
            (r"température\s+(?:max|maximum)\s+(?:de\s+)?(\d+)\s*°?C?", "max_temperature"),
            (r"entre\s+(\d+)\s+et\s+(\d+)\s*°?C", "temp_range"),
        ]
        for pattern, key in temp_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if key == "temp_range":
                    constraints["min_temperature"] = int(match.group(1))
                    constraints["max_temperature"] = int(match.group(2))
                else:
                    constraints[key] = int(match.group(1))

        # Contraintes de densité
        density_patterns = [
            (r"densité\s+(?:max|maximum)\s+(?:de\s+)?(\d+)", "max_density"),
            (r"(?:maximum|max)\s+(\d+)\s+(?:oiseaux?|poulets?)\s*(?:/|par)\s*m[²2]", "max_density"),
        ]
        for pattern, key in density_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                constraints[key] = int(match.group(1))

        return constraints
