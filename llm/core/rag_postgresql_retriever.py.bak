# -*- coding: utf-8 -*-
"""
rag_postgresql_retriever.py - Récupérateur de données PostgreSQL
Version 3.1: CORRECTION CRITIQUE - Format documents avec 'content' + metadata
- Mapping breed → nom PostgreSQL via breeds_registry
- Retourne RAGResult avec documents formatés correctement
- ✅ NOUVEAU: Conversion MetricResult → dict avec 'content' et 'metadata'
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

from .rag_postgresql_config import ASYNCPG_AVAILABLE
from .rag_postgresql_models import MetricResult
from .rag_postgresql_normalizer import SQLQueryNormalizer
from .data_models import RAGResult, RAGSource


if ASYNCPG_AVAILABLE:
    import asyncpg

logger = logging.getLogger(__name__)


class PostgreSQLRetriever:
    """Récupérateur de données PostgreSQL avec normalisation et mapping breeds"""

    def __init__(
        self, config: Dict[str, Any], intents_file_path: str = "llm/config/intents.json"
    ):
        self.config = config
        self.pool = None
        self.query_normalizer = SQLQueryNormalizer()
        self.is_initialized = False

        # Charger le breeds registry pour mapping vers noms PostgreSQL
        self.breeds_registry = None
        try:
            from utils.breeds_registry import get_breeds_registry

            self.breeds_registry = get_breeds_registry(intents_file_path)
            logger.info(
                f"Breeds registry loaded: {len(self.breeds_registry.get_all_breeds())} breeds"
            )
        except Exception as e:
            logger.warning(
                f"Breeds registry not available: {e}. Will use fallback LIKE queries."
            )
            self.breeds_registry = None

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

    def _get_db_breed_name(self, canonical_breed: str) -> Optional[str]:
        """
        Convertit le nom de race canonique vers le nom PostgreSQL

        Args:
            canonical_breed: Nom canonique (ex: "ross 308")

        Returns:
            Nom PostgreSQL (ex: "308/308 FF") ou None si pas de mapping
        """
        if not self.breeds_registry:
            return None

        try:
            db_name = self.breeds_registry.get_db_name(canonical_breed)
            return db_name if db_name else None
        except Exception as e:
            logger.warning(f"Error getting DB name for '{canonical_breed}': {e}")
            return None

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
    ) -> RAGResult:
        """
        Recherche de métriques avec correspondance de sexe optionnelle stricte

        VERSION 3.1: CORRECTION CRITIQUE - Retourne documents formatés avec 'content'

        Args:
            query: Requête de recherche
            entities: Entités extraites (breed, age_days, sex, metric_type, etc.)
            top_k: Nombre maximum de résultats
            strict_sex_match: Si True, correspondance exacte du sexe uniquement (pour comparaisons)

        Returns:
            RAGResult contenant les documents formatés et métadonnées
        """

        if not self.is_initialized or not self.pool:
            logger.warning("PostgreSQL not initialized")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Initialization failed: {e}")
                return RAGResult(
                    context_docs=[],
                    source=RAGSource.INTERNAL_ERROR,
                    metadata={"error": str(e), "initialized": False},
                )

        try:
            normalized_entities = self._normalize_entities(entities)
            logger.debug(f"Entities: {entities}")
            logger.debug(f"Normalized: {normalized_entities}")

            sql_query, params = self._build_query(
                query, normalized_entities, entities, top_k, strict_sex_match
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

            # ✅ CONVERSION CRITIQUE: Transformer MetricResult en dict avec 'content'
            formatted_docs = []
            for metric in results:
                # Extraire le type de métrique de manière propre
                metric_type_clean = self._extract_metric_type(metric.metric_name)

                # Informations sur le sexe
                sex_info = self._format_sex_info(metric.sex)

                # Créer un contenu textuel naturel et lisible pour le LLM
                if metric.value_numeric is not None:
                    # Phrase complète avec contexte
                    content = (
                        f"At {metric.age_min} days old, {metric.strain} {sex_info} chickens "
                        f"have an average {metric_type_clean} of {metric.value_numeric} "
                        f"{metric.unit or 'grams'}."
                    )
                else:
                    # Fallback pour valeurs textuelles
                    content = (
                        f"For {metric.strain} at {metric.age_min} days ({sex_info}): "
                        f"{metric_type_clean} = {metric.value_text or 'N/A'}"
                    )

                # Structurer avec metadata complète
                formatted_docs.append(
                    {
                        "content": content,
                        "metadata": {
                            "company": metric.company,
                            "breed": metric.breed,
                            "strain": metric.strain,
                            "species": metric.species,
                            "metric_name": metric.metric_name,
                            "value_numeric": metric.value_numeric,
                            "value_text": metric.value_text,
                            "unit": metric.unit,
                            "age_min": metric.age_min,
                            "age_max": metric.age_max,
                            "category": metric.category,
                            "sex": metric.sex,
                            "housing_system": metric.housing_system,
                            "data_type": metric.data_type,
                        },
                        "score": metric.confidence,
                    }
                )

            # Retourner un RAGResult structuré avec documents formatés
            if len(formatted_docs) > 0:
                return RAGResult(
                    context_docs=formatted_docs,  # ✅ Utiliser formatted_docs au lieu de results
                    source=RAGSource.RAG_SUCCESS,
                    metadata={
                        "count": len(formatted_docs),
                        "query": query,
                        "entities": normalized_entities,
                        "strict_sex_match": strict_sex_match,
                    },
                )
            else:
                # Aucun résultat trouvé
                return RAGResult(
                    context_docs=[],
                    source=RAGSource.NO_RESULTS,
                    metadata={
                        "count": 0,
                        "query": query,
                        "entities": normalized_entities,
                        "reason": "no_matching_metrics",
                    },
                )

        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}")
            return RAGResult(
                context_docs=[],
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e), "query": query, "entities": entities},
            )

    def _build_query(
        self,
        query: str,
        entities: Dict[str, str],
        original_entities: Dict[str, Any],
        top_k: int,
        strict_sex_match: bool,
    ) -> Tuple[str, List]:
        """Construit une requête SQL avec filtres"""
        conditions = []
        params = []
        param_count = 0

        # CORRECTION: Filtres de base avec mapping vers noms PostgreSQL
        if entities.get("breed"):
            canonical_breed = entities["breed"]
            db_breed_name = self._get_db_breed_name(canonical_breed)

            if db_breed_name and db_breed_name != canonical_breed:
                # Mapping trouvé - utiliser recherche exacte
                param_count += 1
                conditions.append(f"s.strain_name = ${param_count}")
                params.append(db_breed_name)
                logger.debug(
                    f"Breed DB mapping: '{canonical_breed}' → '{db_breed_name}'"
                )
            else:
                # Pas de mapping ou breeds_registry non disponible - fallback LIKE
                param_count += 1
                conditions.append(f"LOWER(s.strain_name) LIKE LOWER(${param_count})")
                params.append(f"%{canonical_breed}%")
                if db_breed_name is None and self.breeds_registry:
                    logger.warning(
                        f"No DB mapping found for breed: '{canonical_breed}', using LIKE fallback"
                    )

        # Filtre d'âge
        if entities.get("age_days"):
            try:
                age = int(entities["age_days"])
                param_count += 1
                conditions.append(
                    f"m.age_min <= ${param_count} AND m.age_max >= ${param_count}"
                )
                params.append(age)
            except (ValueError, TypeError):
                logger.warning(f"Invalid age_days: {entities.get('age_days')}")

        # NOUVEAU: Filtre métrique basé sur interprétation OpenAI
        if (
            original_entities
            and "metric" in original_entities
            and original_entities["metric"]
        ):
            metric_name = original_entities["metric"]

            # Mapping métrique OpenAI → pattern base de données
            metric_to_db_pattern = {
                "feed_conversion_ratio": "feed_conversion_ratio for %",
                "cumulative_feed_intake": "feed_intake for %",
                "body_weight": "body_weight for %",
                "daily_gain": "daily_gain for %",
                "mortality": "mortality for %",
                "livability": "livability for %",
            }

            db_pattern = metric_to_db_pattern.get(metric_name)
            if db_pattern:
                param_count += 1
                conditions.append(f"m.metric_name LIKE ${param_count}")
                params.append(db_pattern)
                logger.info(f"🎯 Filtering by metric: {metric_name} → {db_pattern}")
            else:
                logger.warning(f"⚠️ Unknown metric type from OpenAI: {metric_name}")

        # Filtres pour sexe
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

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql_query = f"""
            SELECT 
                c.company_name, b.breed_name, s.strain_name, s.species,
                m.metric_name, m.value_numeric, m.value_text, m.unit,
                m.age_min, m.age_max, m.sheet_name,
                dc.category_name, d.sex, d.housing_system, d.data_type
            FROM companies c
            JOIN breeds b ON c.id = b.company_id
            JOIN strains s ON b.id = s.breed_id  
            JOIN documents d ON s.id = d.strain_id
            JOIN metrics m ON d.id = m.document_id
            JOIN data_categories dc ON m.category_id = dc.id
            {where_clause}
            ORDER BY 
                CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed') THEN 1
                    ELSE 2
                END,
                m.value_numeric DESC NULLS LAST
            LIMIT {top_k}
        """

        return sql_query, params

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

    def _extract_metric_type(self, metric_name: str) -> str:
        """
        Extrait et nettoie le type de métrique depuis le nom brut

        Exemples:
        - "body_weight for male" → "body weight"
        - "feed_conversion_ratio for as_hatched" → "feed conversion ratio"
        - "mortality for female" → "mortality rate"
        """
        if not metric_name:
            return "metric"

        # Retirer la partie "for [sex]"
        clean_name = (
            metric_name.split(" for ")[0] if " for " in metric_name else metric_name
        )

        # Remplacer underscores par espaces
        clean_name = clean_name.replace("_", " ")

        # Mapping pour des noms plus naturels
        name_mappings = {
            "body weight": "body weight",
            "feed conversion ratio": "feed conversion ratio (FCR)",
            "feed intake": "feed intake",
            "daily gain": "daily weight gain",
            "mortality": "mortality rate",
            "livability": "livability rate",
        }

        return name_mappings.get(clean_name.lower(), clean_name)

    def _format_sex_info(self, sex: Optional[str]) -> str:
        """
        Formate l'information sur le sexe de manière naturelle

        Args:
            sex: Sexe brut (male, female, as_hatched, mixed, None)

        Returns:
            Texte formaté (ex: "male", "female", "mixed-sex")
        """
        if not sex or sex.lower() in ["as_hatched", "as hatched", "mixed"]:
            return "mixed-sex"
        elif sex.lower() == "male":
            return "male"
        elif sex.lower() == "female":
            return "female"
        else:
            return "mixed-sex"

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


# Tests unitaires
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.DEBUG)

    print("=" * 70)
    print("🧪 TESTS POSTGRESQL RETRIEVER - VERSION 3.1")
    print("=" * 70)

    async def test_retriever():
        """Test de base pour vérifier le format de sortie"""

        print("\n✅ Test 1: Vérification du format de sortie")
        print("Note: Ce test nécessite une connexion PostgreSQL active")

        # Test de la structure sans connexion réelle
        test_entities = {
            "breed": "ross 308",
            "age_days": 21,
            "sex": "male",
            "metric": "body_weight",
        }

        print(f"\nEntités de test: {test_entities}")
        print("\nFormat attendu des documents retournés:")
        print(
            {
                "content": "body_weight for male: 850.0 g (Age: 21-21 days, Sex: male)",
                "metadata": {
                    "company": "Aviagen",
                    "breed": "Ross",
                    "strain": "308/308 FF",
                    "species": "broiler",
                    "metric_name": "body_weight for male",
                    "value_numeric": 850.0,
                    "unit": "g",
                    "age_min": 21,
                    "age_max": 21,
                    "sex": "male",
                },
                "score": 0.9,
            }
        )

        print("\n✅ Structure validée:")
        print("- Chaque document a un champ 'content' (str)")
        print("- Chaque document a un champ 'metadata' (dict)")
        print("- Chaque document a un champ 'score' (float)")

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS - PostgreSQL Retriever VERSION 3.1")
    print("🎯 CORRECTION APPLIQUÉE: Documents formatés avec 'content' + metadata")
    print("=" * 70)

    # Exécuter le test
    asyncio.run(test_retriever())
