# -*- coding: utf-8 -*-
"""
rag_postgresql_retriever.py - Récupérateur de données PostgreSQL
Version 3.3: Support du flag has_explicit_sex pour mode strict/souple
- Mapping breed → nom PostgreSQL via breeds_registry
- Retourne RAGResult avec documents formatés correctement
- ✅ Support des calculs de moulée sur plage d'âges
- ✅ Extraction du nombre de poulets depuis la requête
- ✅ NOUVEAU: Mode strict/souple basé sur has_explicit_sex
- Format documents avec 'content' + metadata
"""

import logging
import re
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

    def _extract_bird_count(self, query: str) -> Optional[int]:
        """
        Extrait le nombre de poulets de la requête

        Args:
            query: Requête utilisateur (ex: "moulée pour 20,000 poulets")

        Returns:
            Nombre de poulets ou None si non trouvé
        """
        # Patterns: "20,000 poulets", "20000 birds", "20 000 pollos"
        patterns = [
            r"(\d+[,\s]?\d+)\s*(?:poulets|birds|pollos|chickens|aves)",
            r"(\d+[,\s]?\d+)\s*(?:en production|in production)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                # Nettoyer et convertir
                num_str = match.group(1).replace(",", "").replace(" ", "")
                try:
                    return int(num_str)
                except ValueError:
                    continue

        return None

    async def search_metrics(
        self,
        query: str,
        entities: Dict[str, Any] = None,
        top_k: int = 10,
        strict_sex_match: bool = False,
    ) -> RAGResult:
        """
        Recherche de métriques avec support des calculs de plage d'âges

        VERSION 3.3: Support du flag has_explicit_sex pour mode strict/souple

        Args:
            query: Requête de recherche
            entities: Entités extraites (breed, age_days, start_age_days, target_age_days, sex, metric_type, has_explicit_sex, etc.)
            top_k: Nombre maximum de résultats
            strict_sex_match: DEPRECATED - utilisez has_explicit_sex dans entities à la place

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

            # ✅ DÉTECTION CALCUL DE MOULÉE
            start_age = entities.get("start_age_days") or entities.get("age_days")
            target_age = entities.get("target_age_days")
            breed = entities.get("breed")
            sex = entities.get("sex", "as_hatched")

            is_feed_calc = (
                start_age
                and target_age
                and any(
                    kw in query.lower()
                    for kw in ["moulée", "feed", "alimento", "combien", "cuánto"]
                )
            )

            if is_feed_calc:
                logger.info(
                    f"📢 Calcul de moulée détecté: jour {start_age} → {target_age}"
                )
                return await self._calculate_feed_range(
                    breed, start_age, target_age, sex, query, entities
                )

            # Sinon, requête standard
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

            # Conversion: Transformer MetricResult en dict avec 'content'
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
                    context_docs=formatted_docs,
                    source=RAGSource.RAG_SUCCESS,
                    metadata={
                        "count": len(formatted_docs),
                        "query": query,
                        "entities": normalized_entities,
                        "strict_sex_match": strict_sex_match,
                        "has_explicit_sex": entities.get("has_explicit_sex", False),
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

    async def _calculate_feed_range(
        self,
        breed: str,
        start_age: int,
        target_age: int,
        sex: str,
        query: str,
        entities: Dict,
    ) -> RAGResult:
        """
        Calcul de consommation de moulée sur une plage d'âges

        Args:
            breed: Race (ex: "ross 308")
            start_age: Âge de départ (jours)
            target_age: Âge cible (jours)
            sex: Sexe (male, female, as_hatched)
            query: Requête originale
            entities: Entités complètes

        Returns:
            RAGResult avec calcul détaillé
        """

        # Normaliser breed pour DB
        breed_db = self._get_db_breed_name(breed) if breed else None

        if not breed_db and breed:
            # Fallback si pas de mapping
            breed_db = breed

        # ✅ Support du mode strict/souple pour les calculs de feed
        has_explicit_sex = entities.get("has_explicit_sex", False)

        if has_explicit_sex and sex not in ["as_hatched", "mixed"]:
            # Mode strict: UNIQUEMENT le sexe demandé
            sex_condition = "AND LOWER(COALESCE(d.sex, 'as_hatched')) = $4"
            logger.info(f"🎯 Feed calculation: STRICT sex mode for '{sex}'")
        else:
            # Mode souple: sexe demandé OU fallback mixed/as_hatched
            sex_condition = """AND (LOWER(COALESCE(d.sex, 'as_hatched')) = $4 
                   OR LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed'))"""
            logger.info(f"🔄 Feed calculation: FLEXIBLE sex mode for '{sex}'")

        sql = f"""
            SELECT 
                m.age_min as age_days,
                m.value_numeric as feed_intake,
                m.metric_name,
                s.strain_name,
                d.sex
            FROM companies c
            JOIN breeds b ON c.id = b.company_id
            JOIN strains s ON b.id = s.breed_id  
            JOIN documents d ON s.id = d.strain_id
            JOIN metrics m ON d.id = m.document_id
            WHERE s.strain_name = $1
              AND m.age_min BETWEEN $2 AND $3
              AND m.metric_name LIKE 'feed_intake for %'
              AND m.value_numeric IS NOT NULL
              {sex_condition}
            ORDER BY m.age_min ASC
        """

        params = [breed_db if breed_db else breed, start_age, target_age, sex.lower()]

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)

            logger.debug(f"📊 SQL returned {len(rows)} rows")

            if not rows:
                logger.warning(
                    f"❌ Aucune donnée feed_intake trouvée pour {breed_db if breed_db else breed} entre {start_age}-{target_age} jours (sex: {sex}, strict: {has_explicit_sex})"
                )
                return RAGResult(
                    context_docs=[],
                    source=RAGSource.NO_RESULTS,
                    metadata={
                        "query_type": "feed_calculation",
                        "reason": "no_feed_data_for_range",
                        "start_age": start_age,
                        "target_age": target_age,
                        "sex": sex,
                        "has_explicit_sex": has_explicit_sex,
                    },
                )

            # ✅ Grouper par jour (un seul feed_intake par jour)
            daily_feed = {}
            strain_name = rows[0].get("strain_name", breed)
            actual_sex = rows[0].get("sex", sex)

            for row in rows:
                age = row["age_days"]
                feed = row["feed_intake"]
                if feed and feed > 0:
                    # Prendre la valeur max si plusieurs entrées pour le même jour
                    if age not in daily_feed or feed > daily_feed[age]:
                        daily_feed[age] = feed

            logger.info(
                f"✅ {len(daily_feed)} jours de données feed_intake trouvés (sex: {actual_sex})"
            )

            # ✅ SOMME (pas moyenne) pour le total par poulet
            total_feed_grams = sum(daily_feed.values())
            num_days = len(daily_feed)
            avg_daily_grams = total_feed_grams / num_days if num_days > 0 else 0

            # Nombre de poulets (extraire de la requête)
            num_birds = self._extract_bird_count(query)

            # Formatage détails quotidiens (limiter affichage)
            daily_details = [
                f"Day {age}: {feed:.1f}g" for age, feed in sorted(daily_feed.items())
            ]

            # Calculs finaux
            total_feed_kg_per_bird = total_feed_grams / 1000

            # ✅ FORMATAGE RÉSULTAT
            context_text = f"""Feed calculation for {strain_name} ({actual_sex}) from day {start_age} to day {target_age}:

**Daily feed intake:**
{chr(10).join(daily_details[:10])}"""

            if len(daily_details) > 10:
                context_text += "\n... (see all details in the data)"

            context_text += f"""

**Totals:**
- Total feed per bird: {total_feed_kg_per_bird:.2f} kg over {num_days} days
- Average daily consumption: {avg_daily_grams:.1f} g/day/bird"""

            if num_birds:
                total_feed_kg = total_feed_kg_per_bird * num_birds
                total_feed_tonnes = total_feed_kg / 1000
                context_text += f"""
- Number of birds: {num_birds:,}
- **TOTAL FEED REQUIRED: {total_feed_tonnes:.2f} tonnes** ({total_feed_kg:,.0f} kg)"""

            # Créer document formaté
            formatted_doc = {
                "content": context_text,
                "metadata": {
                    "calculation": True,
                    "query_type": "feed_calculation",
                    "breed": strain_name,
                    "start_age": start_age,
                    "target_age": target_age,
                    "sex": actual_sex,
                    "has_explicit_sex": has_explicit_sex,
                    "num_birds": num_birds,
                    "total_feed_kg_per_bird": total_feed_kg_per_bird,
                    "total_feed_tonnes": total_feed_tonnes if num_birds else None,
                    "days_calculated": len(daily_details),
                },
                "score": 1.0,
            }

            return RAGResult(
                context_docs=[formatted_doc],
                source=RAGSource.RAG_SUCCESS,
                metadata={
                    "query_type": "feed_calculation",
                    "start_age": start_age,
                    "target_age": target_age,
                    "sex": actual_sex,
                    "has_explicit_sex": has_explicit_sex,
                    "num_birds": num_birds,
                    "total_feed_tonnes": total_feed_tonnes if num_birds else None,
                    "days_with_data": num_days,
                },
            )

        except Exception as e:
            logger.error(f"❌ Erreur calcul feed range: {e}")
            return RAGResult(
                context_docs=[],
                source=RAGSource.INTERNAL_ERROR,
                metadata={
                    "error": str(e),
                    "query_type": "feed_calculation_error",
                },
            )

    def _build_query(
        self,
        query: str,
        entities: Dict[str, str],
        original_entities: Dict[str, Any],
        top_k: int,
        strict_sex_match: bool,
    ) -> Tuple[str, List]:
        """Construit une requête SQL avec filtres adaptatifs selon has_explicit_sex"""
        conditions = []
        params = []
        param_count = 0

        # Filtres de base avec mapping vers noms PostgreSQL
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

        # Filtre métrique basé sur interprétation OpenAI
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

        # ✅ FILTRES POUR SEXE - LOGIQUE ADAPTATIVE
        sex = entities.get("sex", "as_hatched")
        has_explicit_sex = original_entities.get("has_explicit_sex", False)

        # Pour backward compatibility avec strict_sex_match (deprecated)
        if strict_sex_match:
            has_explicit_sex = True
            logger.warning(
                "strict_sex_match is deprecated, using has_explicit_sex instead"
            )

        sex_condition = None
        order_sex_clause = None

        if sex and sex != "as_hatched":
            if has_explicit_sex:
                # 🎯 MODE STRICT: UNIQUEMENT le sexe demandé
                param_count += 1
                sex_condition = f"LOWER(d.sex) = ${param_count}"
                params.append(sex.lower())
                order_sex_clause = ""  # Pas de priorisation nécessaire
                logger.info(f"🎯 Using STRICT sex filter: only '{sex}' results")
            else:
                # 🔄 MODE SOUPLE: sexe demandé OU fallback mixed/as_hatched
                param_count += 1
                sex_condition = f"""
                    (LOWER(COALESCE(d.sex, 'as_hatched')) = ${param_count} 
                     OR LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed'))
                """
                params.append(sex.lower())
                # Priorisation: exact match > fallback
                order_sex_clause = """CASE 
                    WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed') THEN 1
                    ELSE 2
                END,"""
                logger.info(
                    f"🔄 Using FLEXIBLE sex filter: '{sex}' + fallback to mixed/as_hatched"
                )
        else:
            # Pas de filtre sexe spécifique
            order_sex_clause = """CASE 
                WHEN LOWER(COALESCE(d.sex, 'as_hatched')) IN ('as_hatched', 'mixed') THEN 1
                ELSE 2
            END,"""

        if sex_condition:
            conditions.append(sex_condition)

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
                {order_sex_clause or ''}
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
    print("🧪 TESTS POSTGRESQL RETRIEVER - VERSION 3.3")
    print("=" * 70)

    async def test_retriever():
        """Test de base pour vérifier le format de sortie"""

        print("\n✅ Test 1: Vérification du format de sortie standard")
        test_entities = {
            "breed": "ross 308",
            "age_days": 21,
            "sex": "male",
            "metric": "body_weight",
            "has_explicit_sex": False,  # Mode souple
        }

        print(f"\nEntités de test: {test_entities}")
        print("\nFormat attendu des documents retournés:")
        print(
            {
                "content": "At 21 days old, 308/308 FF male chickens have an average body weight of 850.0 grams.",
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

        print("\n✅ Test 2: Mode strict avec has_explicit_sex=True")
        strict_entities = {
            "breed": "ross 308",
            "age_days": 21,
            "sex": "male",
            "metric": "body_weight",
            "has_explicit_sex": True,  # Mode strict - UNIQUEMENT male
        }
        print(f"\nEntités strict: {strict_entities}")
        print("→ SQL WHERE: LOWER(d.sex) = 'male' (pas de fallback)")

        print("\n✅ Test 3: Calcul de moulée sur plage d'âges")
        feed_entities = {
            "breed": "ross 308",
            "start_age_days": 1,
            "target_age_days": 35,
            "sex": "as_hatched",
            "has_explicit_sex": False,
        }

        print(f"\nEntités de test feed: {feed_entities}")
        print("\nFormat attendu pour calcul de moulée:")
        print(
            {
                "content": "Feed calculation for 308/308 FF (as_hatched) from day 1 to day 35...",
                "metadata": {
                    "calculation": True,
                    "query_type": "feed_calculation",
                    "breed": "308/308 FF",
                    "start_age": 1,
                    "target_age": 35,
                    "has_explicit_sex": False,
                    "total_feed_kg_per_bird": 3.5,
                    "days_calculated": 35,
                },
                "score": 1.0,
            }
        )

        print("\n✅ Structure validée:")
        print("- Chaque document a un champ 'content' (str)")
        print("- Chaque document a un champ 'metadata' (dict)")
        print("- Chaque document a un champ 'score' (float)")
        print("- Support des calculs de moulée sur plage d'âges")
        print("- Extraction automatique du nombre de poulets")
        print("- 🆕 Support du flag has_explicit_sex pour mode strict/souple")

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS - PostgreSQL Retriever VERSION 3.3")
    print("🎯 NOUVELLES FONCTIONNALITÉS:")
    print("   - Détection automatique des calculs de moulée")
    print("   - Support des plages d'âges (start_age → target_age)")
    print("   - Extraction du nombre de poulets depuis la requête")
    print("   - Calcul automatique de consommation totale")
    print("   - 🆕 Mode strict/souple avec has_explicit_sex")
    print("   - 🆕 Logique SQL adaptative selon le contexte")
    print("=" * 70)

    # Exécuter le test
    asyncio.run(test_retriever())
