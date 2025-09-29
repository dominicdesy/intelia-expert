# -*- coding: utf-8 -*-
"""
rag_postgresql_retriever.py - Récupérateur de données PostgreSQL
VERSION CORRIGÉE - Utilise PostgreSQLQueryBuilder pour le mapping des souches
"""

import logging
from typing import Dict, List, Any, Tuple

from .rag_postgresql_config import ASYNCPG_AVAILABLE
from .rag_postgresql_models import MetricResult
from .rag_postgresql_normalizer import SQLQueryNormalizer
from .postgresql_query_builder import PostgreSQLQueryBuilder

if ASYNCPG_AVAILABLE:
    import asyncpg

logger = logging.getLogger(__name__)


class PostgreSQLRetriever:
    """Récupérateur de données PostgreSQL avec normalisation et mapping des souches"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self.query_normalizer = SQLQueryNormalizer()
        # NOUVEAU: Utiliser PostgreSQLQueryBuilder pour le mapping correct
        self.query_builder = PostgreSQLQueryBuilder(self.query_normalizer)
        self.is_initialized = False

    async def initialize(self):
        """Initialise la connexion PostgreSQL"""
        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not available")
            raise ImportError("asyncpg required")

        if self.is_initialized:
            return

        try:
            self.pool = await asyncpg.create_pool(
                user=self.config["user"],
                password=self.config["password"],
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                ssl=self.config["ssl"],
                min_size=2,
                max_size=10,
                command_timeout=30,
            )

            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            self.is_initialized = True
            logger.info("PostgreSQL Retriever initialized")

        except Exception as e:
            logger.error(f"PostgreSQL initialization error: {e}")
            self.pool = None
            self.is_initialized = False
            raise

    def _normalize_entities(self, entities: Dict[str, Any] = None) -> Dict[str, str]:
        """Normalise les entités en dict string simple"""
        if not entities:
            return {}

        normalized = {}
        for key, value in entities.items():
            if value is None:
                continue

            if isinstance(value, str):
                normalized[key] = value
            elif isinstance(value, bool):
                normalized[key] = "true" if value else "false"
            elif isinstance(value, (int, float)):
                normalized[key] = str(value)
            elif hasattr(value, "value"):
                normalized[key] = str(value.value)
            else:
                normalized[key] = str(value)

        return normalized

    async def search_metrics(
        self,
        query: str,
        entities: Dict[str, Any] = None,
        top_k: int = 10,
        strict_sex_match: bool = False,
    ) -> List[MetricResult]:
        """
        Recherche de métriques avec correspondance de sexe optionnelle stricte

        Args:
            strict_sex_match: Si True, correspondance exacte du sexe uniquement (pour comparaisons)
        """

        if not self.is_initialized or not self.pool:
            logger.warning("PostgreSQL not initialized")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Initialization failed: {e}")
                return []

        try:
            normalized_entities = self._normalize_entities(entities)
            logger.debug(f"Entities: {entities}")
            logger.debug(f"Normalized: {normalized_entities}")

            # CORRECTION: Utiliser PostgreSQLQueryBuilder au lieu de _build_query
            sql_query, params = self.query_builder.build_sex_aware_sql_query(
                query=query,
                entities=normalized_entities,
                top_k=top_k,
                strict_sex_match=strict_sex_match,
            )

            logger.debug(f"SQL Query: {sql_query}")
            logger.debug(f"Parameters: {params}")

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)

            results = []
            for i, row in enumerate(rows):
                try:
                    result = MetricResult(
                        company=row.get("company_name", "Unknown"),
                        breed=row.get("breed_name", "Unknown"),
                        strain=row.get("strain_name", "Unknown"),
                        species=row.get("species", "Unknown"),
                        metric_name=row.get("metric_name", "Unknown"),
                        value_numeric=row.get("value_numeric"),
                        value_text=row.get("value_text"),
                        unit=row.get("unit"),
                        age_min=row.get("age_min"),
                        age_max=row.get("age_max"),
                        sheet_name=row.get("sheet_name", ""),
                        category=row.get("category_name", ""),
                        sex=row.get("sex"),
                        housing_system=row.get("housing_system"),
                        data_type=row.get("data_type"),
                        confidence=self._calculate_relevance(
                            query, dict(row), normalized_entities
                        ),
                    )
                    results.append(result)
                except Exception as row_error:
                    logger.error(f"Row conversion error {i}: {row_error}")
                    continue

            logger.info(
                f"PostgreSQL: {len(results)} metrics found from {len(rows)} rows"
            )
            return results

        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}")
            return []

    def _build_query(
        self, query: str, entities: Dict[str, str], top_k: int, strict_sex_match: bool
    ) -> Tuple[str, List]:
        """
        DEPRECATED: Cette méthode est remplacée par PostgreSQLQueryBuilder
        Conservée pour compatibilité mais redirige vers le builder
        """
        logger.warning(
            "_build_query is deprecated, using PostgreSQLQueryBuilder instead"
        )

        return self.query_builder.build_sex_aware_sql_query(
            query=query,
            entities=entities,
            top_k=top_k,
            strict_sex_match=strict_sex_match,
        )

    def _calculate_relevance(
        self, query: str, row: Dict, entities: Dict[str, str] = None
    ) -> float:
        """Calcule le score de pertinence"""
        score = 0.5

        # Score basé sur le sexe
        sex_from_entities = entities.get("sex") if entities else None
        row_sex = (row.get("sex") or "as_hatched").lower()

        if sex_from_entities and sex_from_entities != "as_hatched":
            if row_sex == sex_from_entities.lower():
                score += 0.3
            elif row_sex in ["as_hatched", "mixed"]:
                score += 0.1
        else:
            if row_sex in ["as_hatched", "mixed"]:
                score += 0.2

        # Score basé sur les concepts normalisés
        normalized_concepts, _ = self.query_normalizer.get_search_terms(query)
        metric_name_lower = (row.get("metric_name") or "").lower()

        for concept in normalized_concepts:
            if concept in metric_name_lower:
                score += 0.3
                break

        # Bonus pour valeurs numériques
        if row.get("value_numeric") is not None:
            score += 0.1

        return min(1.0, score)

    async def close(self):
        """Ferme la connexion PostgreSQL"""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("PostgreSQL connection closed")
            except Exception as e:
                logger.error(f"PostgreSQL close error: {e}")
            finally:
                self.pool = None
                self.is_initialized = False


# Tests unitaires pour vérifier la correction
if __name__ == "__main__":
    import asyncio

    async def test_mapping_correction():
        """Test pour vérifier que le mapping fonctionne"""

        # Mock config
        mock_config = {
            "user": "test",
            "password": "test",
            "host": "localhost",
            "port": 5432,
            "database": "test",
            "ssl": False,
        }

        # Créer retriever
        retriever = PostgreSQLRetriever(mock_config)

        # Vérifier que query_builder est initialisé
        assert hasattr(
            retriever, "query_builder"
        ), "PostgreSQLQueryBuilder non initialisé"

        # Test du mapping via query_builder
        test_breeds = ["Ross 308", "Cobb 500", "ross 308", "cobb 500"]

        print("Test du mapping des souches:")
        for breed in test_breeds:
            mapped = retriever.query_builder._normalize_breed_for_db(breed)
            print(f"  {breed:15s} -> {mapped}")

        # Vérifier mappings corrects
        assert (
            retriever.query_builder._normalize_breed_for_db("Ross 308") == "308/308 FF"
        )
        assert retriever.query_builder._normalize_breed_for_db("Cobb 500") == "500"
        assert (
            retriever.query_builder._normalize_breed_for_db("ross 308") == "308/308 FF"
        )
        assert retriever.query_builder._normalize_breed_for_db("cobb 500") == "500"

        print("\n✅ CORRECTION VALIDÉE: Le mapping fonctionne correctement!")
        print(
            "Les requêtes utiliseront maintenant '308/308 FF' et '500' au lieu de 'Ross 308' et 'Cobb 500'"
        )

    # Exécuter le test
    asyncio.run(test_mapping_correction())
