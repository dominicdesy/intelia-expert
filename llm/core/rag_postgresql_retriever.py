# -*- coding: utf-8 -*-
"""
rag_postgresql_retriever.py - Récupérateur de données PostgreSQL
VERSION CORRIGÉE - Utilise PostgreSQLQueryBuilder pour le mapping des souches
avec gestion améliorée des unités et validation stricte
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

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
        Recherche de métriques avec gestion des unités et correspondance de sexe stricte
        
        Args:
            strict_sex_match: Si True, correspondance exacte du sexe uniquement
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

            # NOUVEAU: Détecter si c'est une demande de sexe explicite
            if not strict_sex_match:
                strict_sex_match = self._detect_explicit_sex_request(query, normalized_entities)

            # Utiliser PostgreSQLQueryBuilder pour construction SQL
            sql_query, params = self.query_builder.build_sex_aware_sql_query(
                query=query,
                entities=normalized_entities,
                top_k=top_k,
                strict_sex_match=strict_sex_match,
            )

            logger.debug(f"SQL Query: {sql_query}")
            logger.debug(f"Parameters: {params}")

            async with self.pool.acquire() as conn:
                try:
                    rows = await conn.fetch(sql_query, *params)
                    logger.info(f"PostgreSQL: {len(rows)} metrics found from {len(rows)} rows")
                    
                    # NOUVEAU: Traitement des résultats avec filtrage unités
                    metrics = []
                    for row in rows:
                        metric = self._row_to_metric_result(dict(row))
                        if metric:
                            metrics.append(metric)
                    
                    # NOUVEAU: Filtrer les conflits d'unités
                    filtered_metrics = self._filter_unit_conflicts(metrics)
                    
                    # NOUVEAU: Validation des résultats
                    validated_metrics = self._validate_metric_results(filtered_metrics, normalized_entities)
                    
                    return validated_metrics

                except Exception as query_error:
                    logger.error(f"Query execution error: {query_error}")
                    logger.error(f"SQL: {sql_query}")
                    logger.error(f"Params: {params}")
                    return []

        except Exception as e:
            logger.error(f"Search metrics error: {e}")
            return []

    def _detect_explicit_sex_request(self, query: str, entities: Dict[str, str]) -> bool:
        """Détecte si l'utilisateur demande explicitement un sexe"""
        # Si sexe spécifié dans entités et pas 'as_hatched'
        if entities.get('sex') and entities['sex'] != 'as_hatched':
            return True
        
        # Recherche dans le texte de la requête
        query_lower = query.lower()
        explicit_markers = ['femelle', 'female', 'mâle', 'male', 'poule', 'coq']
        return any(marker in query_lower for marker in explicit_markers)

    def _filter_unit_conflicts(self, metrics: List[MetricResult]) -> List[MetricResult]:
        """Supprime les doublons métrique/impérial, préfère les données métriques"""
        seen_metrics = {}
        filtered = []
        
        # Premier passage : garder seulement les données métriques
        for metric in metrics:
            key = f"{metric.metric_name}_{metric.age_min}_{metric.sex}"
            sheet_name = getattr(metric, 'sheet_name', '').lower()
            
            if 'imperial' not in sheet_name:
                if key not in seen_metrics:
                    seen_metrics[key] = metric
                    filtered.append(metric)
        
        # Si pas de données métriques trouvées, garder les impériales
        if not filtered:
            logger.warning("Aucune donnée métrique trouvée, utilisation des données impériales")
            for metric in metrics:
                key = f"{metric.metric_name}_{metric.age_min}_{metric.sex}"
                if key not in seen_metrics:
                    seen_metrics[key] = metric
                    filtered.append(metric)
        
        logger.debug(f"Filtrage unités: {len(metrics)} -> {len(filtered)} métriques")
        return filtered

    def _validate_metric_results(self, metrics: List[MetricResult], entities: Dict[str, str]) -> List[MetricResult]:
        """Valide les résultats par rapport aux entités demandées"""
        if not metrics:
            return metrics
        
        validated = []
        target_sex = entities.get('sex', 'as_hatched')
        target_age = entities.get('age_days')
        
        for metric in metrics:
            # Validation du sexe si spécifié
            if target_sex != 'as_hatched':
                if metric.sex.lower() != target_sex.lower():
                    logger.debug(f"Métrique exclue: sexe {metric.sex} != {target_sex}")
                    continue
            
            # Validation de l'âge si spécifié (tolérance ±3 jours)
            if target_age:
                age_target = int(target_age)
                age_metric = metric.age_min or metric.age_max or 0
                if abs(age_metric - age_target) > 3:
                    logger.debug(f"Métrique exclue: âge {age_metric} trop éloigné de {age_target}")
                    continue
            
            # Validation des valeurs aberrantes
            if metric.value_numeric is not None:
                if metric.value_numeric <= 0 or metric.value_numeric > 10000:  # Seuils raisonnables
                    logger.warning(f"Valeur aberrante détectée: {metric.value_numeric}")
                    # Ne pas exclure mais logger
            
            validated.append(metric)
        
        logger.debug(f"Validation: {len(metrics)} -> {len(validated)} métriques validées")
        return validated

    def _row_to_metric_result(self, row: dict) -> Optional[MetricResult]:
        """Convertit une ligne de résultat en MetricResult avec validation"""
        try:
            # Extraire les valeurs avec gestion des erreurs
            value_numeric = row.get('value_numeric')
            if isinstance(value_numeric, str):
                try:
                    value_numeric = float(value_numeric)
                except (ValueError, TypeError):
                    value_numeric = None
            
            return MetricResult(
                company=row.get('company_name', ''),
                breed=row.get('breed_name', ''),
                strain=row.get('strain_name', ''),
                species=row.get('species', ''),
                metric_name=row.get('metric_name', ''),
                value_numeric=value_numeric,
                value_text=row.get('value_text'),
                unit=row.get('unit', ''),
                age_min=row.get('age_min'),
                age_max=row.get('age_max'),
                sheet_name=row.get('sheet_name', ''),
                category=row.get('category_name', ''),
                sex=row.get('sex', 'as_hatched'),
                housing_system=row.get('housing_system', ''),
                data_type=row.get('data_type', ''),
                confidence=self._calculate_relevance(
                    query="", dict_row=row, entities={}
                )
            )
        except Exception as e:
            logger.error(f"Erreur conversion MetricResult: {e}")
            return None

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
        self, query: str, dict_row: Dict, entities: Dict[str, str] = None
    ) -> float:
        """Calcule le score de pertinence"""
        score = 0.5

        # Score basé sur le sexe
        sex_from_entities = entities.get("sex") if entities else None
        row_sex = (dict_row.get("sex") or "as_hatched").lower()

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
        metric_name_lower = (dict_row.get("metric_name") or "").lower()

        for concept in normalized_concepts:
            if concept in metric_name_lower:
                score += 0.3
                break

        # Bonus pour valeurs numériques
        if dict_row.get("value_numeric") is not None:
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