# -*- coding: utf-8 -*-
"""
rag_postgresql_temporal.py - Processeur de requêtes temporelles optimisées
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
rag_postgresql_temporal.py - Processeur de requêtes temporelles optimisées
"""

import re
import time
import logging
from utils.types import Dict, List, Optional, Any, Tuple

from core.data_models import RAGResult, RAGSource
from .models import MetricResult
from .config import OPENAI_MODEL

logger = logging.getLogger(__name__)


class TemporalQueryProcessor:
    """Processeur spécialisé pour les requêtes temporelles"""

    def __init__(self, postgres_retriever):
        self.postgres_retriever = postgres_retriever

    def detect_temporal_range(
        self, query: str, entities: Dict[str, Any]
    ) -> Optional[Dict[str, int]]:
        """
        Détecte si la requête demande une plage temporelle

        Returns:
            Dict avec age_min, age_max si détecté, None sinon
        """
        query_lower = query.lower()

        # Patterns pour plages temporelles
        range_patterns = [
            r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?",
            r"de\s+(\d+)\s+à\s+(\d+)\s+jours?",
            r"(\d+)\s*-\s*(\d+)\s+jours?",
            r"(\d+)\s+à\s+(\d+)\s+j\b",
            r"from\s+(\d+)\s+to\s+(\d+)\s+days?",
        ]

        for pattern in range_patterns:
            match = re.search(pattern, query_lower)
            if match:
                age_min = int(match.group(1))
                age_max = int(match.group(2))

                # Validation de la plage
                if 0 <= age_min <= age_max <= 150 and (age_max - age_min) >= 1:
                    logger.debug(f"Temporal range detected: {age_min}-{age_max} days")
                    return {"age_min": age_min, "age_max": age_max}

        # Vérifier aussi dans les entités pour fallback
        if entities and "age_min" in entities and "age_max" in entities:
            try:
                age_min = int(entities["age_min"])
                age_max = int(entities["age_max"])
                if 0 <= age_min <= age_max <= 150:
                    return {"age_min": age_min, "age_max": age_max}
            except (ValueError, TypeError):
                pass

        return None

    async def search_metrics_range(
        self,
        query: str,
        entities: Dict[str, str],
        age_min: int,
        age_max: int,
        top_k: int = 12,
        strict_sex_match: bool = False,
    ) -> RAGResult:
        """
        Recherche optimisée pour plages temporelles avec UNE SEULE requête SQL

        Args:
            age_min: Âge minimum en jours
            age_max: Âge maximum en jours

        Returns:
            RAGResult avec données groupées par âge
        """

        if not self.postgres_retriever or not self.postgres_retriever.is_initialized:
            return RAGResult(
                source=RAGSource.ERROR, answer="Système de métriques non disponible."
            )

        start_time = time.time()

        try:
            logger.info(
                f"🔧 Optimisation: Requête plage temporelle {age_min}-{age_max} jours (UNE requête SQL)"
            )

            # Construction SQL avec BETWEEN optimisé
            sql_query, params = await self._build_range_query(
                entities=entities,
                age_min=age_min,
                age_max=age_max,
                limit=top_k,
                strict_sex_match=strict_sex_match,
            )

            # UNE SEULE exécution SQL
            results = await self._execute_single_range_query(sql_query, params)

            if not results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    answer=f"Aucune donnée trouvée pour la plage d'âge {age_min}-{age_max} jours.",
                    metadata={
                        "processing_time": time.time() - start_time,
                        "age_range": f"{age_min}-{age_max}",
                        "sql_optimized": True,
                    },
                )

            # Traitement des résultats groupés par âge
            processed_result = await self._process_temporal_results(
                results, age_min, age_max, query, entities
            )

            # Ajouter métadonnées d'optimisation
            processed_result.metadata.update(
                {
                    "processing_time": time.time() - start_time,
                    "age_range": f"{age_min}-{age_max}",
                    "sql_optimized": True,
                    "single_query_used": True,
                    "results_count": len(results),
                }
            )

            logger.info(
                f"✅ Plage temporelle optimisée: {len(results)} résultats en {time.time() - start_time:.2f}s"
            )
            return processed_result

        except Exception as e:
            logger.error(f"Range query error: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors de la recherche par plage temporelle.",
                metadata={"error": str(e), "processing_time": time.time() - start_time},
            )

    async def _build_range_query(
        self,
        entities: Dict[str, str],
        age_min: int,
        age_max: int,
        limit: int,
        strict_sex_match: bool = False,
    ) -> Tuple[str, List[Any]]:
        """
        Construit une requête SQL optimisée avec BETWEEN pour plages temporelles
        """

        conditions = []
        params = []
        param_count = 0

        # Condition BETWEEN pour l'âge (optimisé)
        param_count += 2
        conditions.append(
            f"""
            (m.age_min <= ${param_count} AND m.age_max >= ${param_count-1})
            OR (m.age_min BETWEEN ${param_count-1} AND ${param_count})
            OR (m.age_max BETWEEN ${param_count-1} AND ${param_count})
        """
        )
        params.extend([age_min, age_max])

        # Filtres pour breed/strain
        if entities.get("breed"):
            param_count += 1
            conditions.append(f"LOWER(s.strain_name) LIKE LOWER(${param_count})")
            params.append(f"%{entities['breed']}%")

        # Filtres pour sex si nécessaire
        if entities.get("sex") and entities["sex"] != "as_hatched":
            if strict_sex_match:
                param_count += 1
                conditions.append(f"LOWER(d.sex) = ${param_count}")
                params.append(entities["sex"].lower())
            else:
                param_count += 1
                conditions.append(
                    f"""
                    (LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_count} 
                     OR LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed'))
                """
                )
                params.append(entities["sex"].lower())

        # Construction de la requête finale
        sql_conditions = " AND ".join(conditions)
        sql_query = f"""
            SELECT 
                c.company_name,
                b.breed_name,
                s.strain_name,
                s.species,
                m.metric_name,
                m.value_numeric,
                m.value_text,
                m.unit,
                m.age_min,
                m.age_max,
                m.sheet_name,
                dc.category_name,
                d.sex,
                d.housing_system,
                d.data_type,
                m.metadata
            FROM companies c
            JOIN breeds b ON c.id = b.company_id
            JOIN strains s ON b.id = s.breed_id  
            JOIN documents d ON s.id = d.strain_id
            JOIN metrics m ON d.id = m.document_id
            JOIN data_categories dc ON m.category_id = dc.id
            WHERE {sql_conditions}
            ORDER BY 
                m.age_min ASC,
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed') THEN 1
                    ELSE 2
                END,
                m.value_numeric DESC NULLS LAST
            LIMIT {limit * 3}
        """

        return sql_query, params

    async def _execute_single_range_query(
        self, sql_query: str, params: List[Any]
    ) -> List[Dict]:
        """
        Exécute UNE SEULE requête SQL pour la plage temporelle
        """

        if not self.postgres_retriever.pool:
            raise Exception("PostgreSQL pool not available")

        try:
            async with self.postgres_retriever.pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)

            # Conversion en liste de dicts
            results = []
            for row in rows:
                results.append(
                    {
                        "company_name": row.get("company_name"),
                        "breed_name": row.get("breed_name"),
                        "strain_name": row.get("strain_name"),
                        "species": row.get("species"),
                        "metric_name": row.get("metric_name"),
                        "value_numeric": row.get("value_numeric"),
                        "value_text": row.get("value_text"),
                        "unit": row.get("unit"),
                        "age_min": row.get("age_min"),
                        "age_max": row.get("age_max"),
                        "sheet_name": row.get("sheet_name"),
                        "category_name": row.get("category_name"),
                        "sex": row.get("sex"),
                        "housing_system": row.get("housing_system"),
                        "data_type": row.get("data_type"),
                    }
                )

            logger.debug(f"Single range query executed: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Range query execution error: {e}")
            raise

    async def _process_temporal_results(
        self,
        results: List[Dict],
        age_min: int,
        age_max: int,
        query: str,
        entities: Dict[str, Any],
    ) -> RAGResult:
        """
        Traite les résultats temporels groupés par âge
        """

        if not results:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                answer=f"Aucune donnée trouvée pour la plage {age_min}-{age_max} jours.",
            )

        # Grouper par âge pour analyse temporelle
        age_groups = {}
        for result in results:
            age_key = result.get("age_min", 0)
            if age_key not in age_groups:
                age_groups[age_key] = []
            age_groups[age_key].append(result)

        # Convertir en MetricResult pour compatibilité
        metric_results = []
        for result in results[:12]:  # Limite pour éviter surcharge
            try:
                metric_result = MetricResult(
                    company=result.get("company_name", "Unknown"),
                    breed=result.get("breed_name", "Unknown"),
                    strain=result.get("strain_name", "Unknown"),
                    species=result.get("species", "Unknown"),
                    metric_name=result.get("metric_name", "Unknown"),
                    value_numeric=result.get("value_numeric"),
                    value_text=result.get("value_text"),
                    unit=result.get("unit"),
                    age_min=result.get("age_min"),
                    age_max=result.get("age_max"),
                    sheet_name=result.get("sheet_name", ""),
                    category=result.get("category_name", ""),
                    sex=result.get("sex"),
                    housing_system=result.get("housing_system"),
                    data_type=result.get("data_type"),
                    confidence=0.9,  # Haute confiance pour plage optimisée
                )
                metric_results.append(metric_result)
            except Exception as e:
                logger.error(f"Metric conversion error: {e}")
                continue

        # Génération de réponse temporelle spécialisée
        documents = self._convert_metrics_to_documents(metric_results)
        answer_text = await self._generate_temporal_response(
            metric_results, age_min, age_max, age_groups
        )

        avg_confidence = (
            sum(m.confidence for m in metric_results) / len(metric_results)
            if metric_results
            else 0.5
        )

        return RAGResult(
            source=RAGSource.RAG_SUCCESS,
            answer=answer_text,
            context_docs=[doc.to_dict() for doc in documents],
            confidence=avg_confidence,
            metadata={
                "source_type": "temporal_metrics",
                "data_source": "postgresql_optimized",
                "age_range": f"{age_min}-{age_max}",
                "metric_count": len(metric_results),
                "age_groups_count": len(age_groups),
                "openai_model": OPENAI_MODEL,
            },
        )

    def _convert_metrics_to_documents(self, metric_results: List[MetricResult]) -> List:
        """Convertit les métriques en documents"""
        from core.data_models import Document

        documents = []
        for metric in metric_results:
            try:
                content = f"**{metric.metric_name}**\nStrain: {metric.strain}"
                if metric.sex:
                    content += f"\nSex: {metric.sex}"
                if metric.value_numeric is not None:
                    content += f"\nValue: {metric.value_numeric} {metric.unit or ''}"
                if metric.age_min is not None:
                    if metric.age_min == metric.age_max:
                        content += f"\nAge: {metric.age_min} days"
                    else:
                        content += f"\nAge: {metric.age_min}-{metric.age_max} days"

                doc = Document(
                    content=content,
                    metadata={
                        "strain": metric.strain,
                        "metric_name": metric.metric_name,
                        "sex": metric.sex,
                        "source_type": "temporal_metrics",
                    },
                    score=metric.confidence,
                    source_type="temporal_metrics",
                    retrieval_method="postgresql_temporal",
                )
                documents.append(doc)
            except Exception as e:
                logger.error(f"Document creation error: {e}")
                continue
        return documents

    async def _generate_temporal_response(
        self,
        metric_results: List[MetricResult],
        age_min: int,
        age_max: int,
        age_groups: Dict[int, List[Dict]],
    ) -> str:
        """
        Génère une réponse spécialisée pour les données temporelles
        """

        if not metric_results:
            return f"Aucune donnée trouvée pour la plage {age_min}-{age_max} jours."

        # Identifier la souche principale
        strain = metric_results[0].strain

        # Créer un résumé temporel
        temporal_summary = []
        ages_available = sorted(age_groups.keys())

        for age in ages_available:
            age_data = age_groups[age]
            if age_data and age_data[0].get("value_numeric"):
                value = age_data[0]["value_numeric"]
                unit = age_data[0].get("unit", "")
                temporal_summary.append(f"• {age}j: {value} {unit}")

        if temporal_summary:
            summary_text = "\n".join(temporal_summary[:5])  # Limite à 5 points
            return f"""**Évolution {strain} ({age_min}-{age_max} jours) :**

{summary_text}

Données trouvées sur {len(ages_available)} âges différents dans la plage demandée."""
        else:
            return f"Données trouvées pour {strain} entre {age_min} et {age_max} jours, mais valeurs numériques limitées."
