# -*- coding: utf-8 -*-
"""
rag_postgresql.py - Système PostgreSQL pour métriques avicoles
VERSION AMÉLIORÉE: Normalisation multilingue inspirée du PerfStore
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import asyncpg

    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

from .data_models import RAGResult, RAGSource, Document

logger = logging.getLogger(__name__)

# Configuration PostgreSQL
POSTGRESQL_CONFIG = {
    "user": os.getenv("DB_USER", "doadmin"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 25060)),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "ssl": os.getenv("DB_SSL", "require"),
}


class QueryType(Enum):
    """Types de requêtes pour routage intelligent"""

    KNOWLEDGE = "knowledge"  # Connaissances générales → Weaviate
    METRICS = "metrics"  # Données de performance → PostgreSQL
    HYBRID = "hybrid"  # Combinaison des deux
    UNKNOWN = "unknown"  # Type indéterminé


@dataclass
class MetricResult:
    """Résultat d'une requête de métriques PostgreSQL"""

    company: str
    breed: str
    strain: str
    species: str
    metric_name: str
    value_numeric: Optional[float]
    value_text: Optional[str]
    unit: Optional[str]
    age_min: Optional[int]
    age_max: Optional[int]
    sheet_name: str
    category: str
    confidence: float = 1.0


class SQLQueryNormalizer:
    """
    Normalisateur multilingue inspiré du PerfStore
    Convertit les concepts utilisateur en termes recherchables dans la BD
    """

    CONCEPT_MAPPINGS = {
        "weight": [
            "poids",
            "peso",
            "weight",
            "body_weight",
            "live_weight",
            "body weight",
            "weight_g",
            "weight_lb",
            "masse",
            "masse corporelle",
            "poids corporel",
            "poids vif",
        ],
        "feed": [
            "alimentation",
            "alimento",
            "feed",
            "nutrition",
            "consommation",
            "feed_intake",
            "feed consumption",
            "aliment",
            "nourriture",
            "ration",
            "aliment_consommé",
        ],
        "mortality": [
            "mortalité",
            "mortalidad",
            "mortality",
            "death_rate",
            "viability",
            "survie",
            "taux de mortalité",
            "mort",
            "décès",
            "pertes",
        ],
        "growth": [
            "croissance",
            "crecimiento",
            "growth",
            "gain",
            "développement",
            "daily_gain",
            "gain quotidien",
            "croissance pondérale",
        ],
        "production": [
            "production",
            "producción",
            "ponte",
            "laying",
            "egg_production",
            "lay_rate",
            "taux de ponte",
            "œufs",
            "eggs",
            "rendement",
        ],
        "fcr": [
            "icg",
            "fcr",
            "feed_conversion",
            "conversion",
            "efficacité",
            "efficiency",
            "indice de consommation",
            "conversion alimentaire",
        ],
        "water": [
            "eau",
            "water",
            "água",
            "water_consumption",
            "hydratation",
            "consommation d'eau",
            "abreuvement",
        ],
        "temperature": [
            "température",
            "temperature",
            "temp",
            "chaleur",
            "froid",
            "thermique",
            "climat",
        ],
        "density": [
            "densité",
            "density",
            "peuplement",
            "stocking",
            "occupation",
            "espace",
            "space",
        ],
        "age": [
            "âge",
            "age",
            "semaine",
            "week",
            "jour",
            "day",
            "période",
            "phase",
            "stade",
        ],
    }

    def normalize_query_concepts(self, query: str) -> List[str]:
        """
        Convertit 'quel poids' en ['weight', 'body_weight', 'live_weight']
        Inspiré de la méthode _canon_sex du PerfStore
        """
        query_lower = query.lower()
        normalized_concepts = []

        for concept, terms in self.CONCEPT_MAPPINGS.items():
            if any(term in query_lower for term in terms):
                # Ajouter tous les termes équivalents pour maximiser les résultats
                normalized_concepts.extend(self.CONCEPT_MAPPINGS[concept])

        # Déduplication tout en préservant l'ordre
        seen = set()
        unique_concepts = []
        for concept in normalized_concepts:
            if concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        return unique_concepts

    def get_search_terms(self, query: str) -> Tuple[List[str], List[str]]:
        """
        Retourne (concepts_normalisés, mots_bruts) pour recherche SQL
        """
        normalized = self.normalize_query_concepts(query)
        raw_words = [word for word in query.lower().split() if len(word) > 3]

        return normalized, raw_words


class QueryRouter:
    """Routeur intelligent pour diriger les requêtes vers la bonne source"""

    def __init__(self):
        # Mots-clés pour PostgreSQL (métriques/performance)
        self.metric_keywords = {
            "performance",
            "metrics",
            "données",
            "chiffres",
            "résultats",
            "weight",
            "poids",
            "egg",
            "oeuf",
            "production",
            "feed",
            "alimentation",
            "mortality",
            "mortalité",
            "growth",
            "croissance",
            "nutrition",
            "age",
            "semaine",
            "week",
            "day",
            "jour",
            "phase",
            "temperature",
            "température",
            "humidity",
            "humidité",
            "housing",
            "logement",
            "density",
            "densité",
            "fcr",
            "icg",
            "conversion",
            "efficacité",
        }

        # Mots-clés pour Weaviate (connaissances)
        self.knowledge_keywords = {
            "comment",
            "pourquoi",
            "qu'est-ce",
            "expliquer",
            "définir",
            "maladie",
            "disease",
            "traitement",
            "treatment",
            "symptom",
            "symptôme",
            "prévention",
            "prevention",
            "biosécurité",
            "biosecurity",
            "management",
            "gestion",
            "guide",
            "protocol",
            "protocole",
            "conseil",
            "advice",
            "recommendation",
            "recommandation",
        }

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Détermine le type de requête et la source appropriée"""
        query_lower = query.lower()

        # Compteurs de mots-clés
        metric_score = sum(
            1 for keyword in self.metric_keywords if keyword in query_lower
        )
        knowledge_score = sum(
            1 for keyword in self.knowledge_keywords if keyword in query_lower
        )

        # Analyse des entités si intent_result disponible
        if intent_result:
            if hasattr(intent_result, "genetic_line") and intent_result.genetic_line:
                metric_score += 2
            if hasattr(intent_result, "age") and intent_result.age:
                metric_score += 1

        # Détection de comparaisons (souvent hybride)
        comparison_indicators = [
            "vs",
            "versus",
            "compare",
            "comparaison",
            "différence",
            "mieux",
        ]
        has_comparison = any(
            indicator in query_lower for indicator in comparison_indicators
        )

        # Règles de décision
        if metric_score > knowledge_score + 1:
            return QueryType.METRICS
        elif knowledge_score > metric_score + 1:
            return QueryType.KNOWLEDGE
        elif has_comparison or (metric_score > 0 and knowledge_score > 0):
            return QueryType.HYBRID
        else:
            return QueryType.UNKNOWN


class PostgreSQLRetriever:
    """Récupérateur de données PostgreSQL pour métriques avicoles"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self.query_normalizer = SQLQueryNormalizer()  # NOUVEAU

    async def initialize(self):
        """Initialise la connexion PostgreSQL"""
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg requis pour PostgreSQL")

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
            )
            logger.info("✅ PostgreSQL Retriever initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur PostgreSQL Retriever: {e}")
            raise

    async def search_metrics(
        self, query: str, intent_result=None, top_k: int = 10
    ) -> List[MetricResult]:
        """Recherche de métriques dans PostgreSQL avec normalisation multilingue"""

        if not self.pool:
            await self.initialize()

        try:
            # Construction de la requête SQL avec normalisation
            sql_query, params = self._build_sql_query_with_normalization(
                query, intent_result, top_k
            )

            logger.debug(f"SQL Query: {sql_query}")
            logger.debug(f"Parameters: {params}")

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)

            # Conversion en MetricResult
            results = []
            for row in rows:
                result = MetricResult(
                    company=row["company_name"],
                    breed=row["breed_name"],
                    strain=row["strain_name"],
                    species=row["species"],
                    metric_name=row["metric_name"],
                    value_numeric=row["value_numeric"],
                    value_text=row["value_text"],
                    unit=row["unit"],
                    age_min=row["age_min"],
                    age_max=row["age_max"],
                    sheet_name=row["sheet_name"],
                    category=row["category_name"],
                    confidence=self._calculate_relevance_score(query, row),
                )
                results.append(result)

            logger.info(f"PostgreSQL: {len(results)} métriques trouvées")
            return results

        except Exception as e:
            logger.error(f"Erreur recherche PostgreSQL: {e}")
            raise Exception("NO_RESULTS")

    def _build_sql_query_with_normalization(
        self, query: str, intent_result=None, top_k: int = 10
    ) -> Tuple[str, List]:
        """
        Construction dynamique de la requête SQL avec normalisation multilingue
        VERSION AMÉLIORÉE: Résout le problème "quel poids" → "weight"
        """

        base_query = """
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
            m.metadata
        FROM companies c
        JOIN breeds b ON c.id = b.company_id
        JOIN strains s ON b.id = s.breed_id  
        JOIN documents d ON s.id = d.strain_id
        JOIN metrics m ON d.id = m.document_id
        JOIN data_categories dc ON m.category_id = dc.id
        WHERE 1=1
        """

        params = []
        conditions = []
        param_count = 0

        # NOUVEAU: Normalisation des concepts
        normalized_concepts, raw_words = self.query_normalizer.get_search_terms(query)

        logger.debug(f"Concepts normalisés: {normalized_concepts}")
        logger.debug(f"Mots bruts: {raw_words}")

        # Filtres selon intent_result
        if intent_result:
            if hasattr(intent_result, "genetic_line") and intent_result.genetic_line:
                param_count += 1
                conditions.append(f"LOWER(s.strain_name) ILIKE ${param_count}")
                params.append(f"%{intent_result.genetic_line.lower()}%")

            if hasattr(intent_result, "age") and intent_result.age:
                param_count += 1
                param_count_age2 = param_count + 1
                conditions.append(
                    f"(m.age_min <= ${param_count} AND m.age_max >= ${param_count_age2}) OR (m.age_min IS NULL AND m.age_max IS NULL)"
                )
                params.append(intent_result.age)
                params.append(intent_result.age)
                param_count += 1

        # CORRECTION PRINCIPALE: Recherche avec concepts normalisés
        metric_search_conditions = []

        # 1. Recherche sur concepts normalisés (priorité haute)
        if normalized_concepts:
            for concept in normalized_concepts[
                :10
            ]:  # Limite pour éviter requêtes trop lourdes
                param_count += 1
                metric_search_conditions.append(
                    f"LOWER(m.metric_name) ILIKE ${param_count}"
                )
                params.append(f"%{concept}%")

        # 2. Recherche sur mots bruts (fallback)
        for word in raw_words[:3]:  # Limite à 3 mots
            param_count += 1
            param_count_word2 = param_count + 1
            metric_search_conditions.append(
                f"(LOWER(m.metric_name) ILIKE ${param_count} OR LOWER(m.value_text) ILIKE ${param_count_word2})"
            )
            params.append(f"%{word}%")
            params.append(f"%{word}%")
            param_count += 1

        # Ajouter les conditions de recherche métrique
        if metric_search_conditions:
            conditions.append(f"({' OR '.join(metric_search_conditions)})")

        # Ajout des conditions à la requête
        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        # Tri par pertinence et limite
        base_query += f" ORDER BY m.value_numeric DESC NULLS LAST LIMIT {top_k}"

        return base_query, params

    def _calculate_relevance_score(self, query: str, row: Dict) -> float:
        """
        Calcule un score de pertinence pour un résultat
        AMÉLIORÉ: Prend en compte la normalisation multilingue
        """
        score = 0.5  # Score de base
        query_lower = query.lower()

        # Normaliser la requête pour comparaison
        normalized_concepts, _ = self.query_normalizer.get_search_terms(query)

        # Boost si métrique correspond aux concepts normalisés
        metric_name_lower = (row["metric_name"] or "").lower()
        for concept in normalized_concepts:
            if concept in metric_name_lower:
                score += 0.4  # Boost élevé pour correspondance conceptuelle
                break

        # Boost si correspondance directe avec la requête originale
        if query_lower in metric_name_lower:
            score += 0.3

        # Boost si valeur numérique disponible
        if row["value_numeric"] is not None:
            score += 0.1

        # Boost si âge spécifique
        if row["age_min"] is not None and row["age_max"] is not None:
            score += 0.1

        return min(1.0, score)

    async def close(self):
        """Ferme la connexion PostgreSQL"""
        if self.pool:
            await self.pool.close()


class PostgreSQLSystem:
    """Système PostgreSQL principal"""

    def __init__(self):
        self.query_router = None
        self.postgres_retriever = None

    async def initialize(self):
        """Initialise le système PostgreSQL"""
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg requis pour PostgreSQL")

        try:
            # Router de requêtes
            self.query_router = QueryRouter()

            # PostgreSQL Retriever avec normalisation
            self.postgres_retriever = PostgreSQLRetriever(POSTGRESQL_CONFIG)
            await self.postgres_retriever.initialize()

            logger.info(
                "✅ Système PostgreSQL initialisé avec normalisation multilingue"
            )

        except Exception as e:
            logger.error(f"❌ Erreur initialisation PostgreSQL: {e}")
            raise

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Route une requête vers la source appropriée"""
        if not self.query_router:
            return QueryType.KNOWLEDGE
        return self.query_router.route_query(query, intent_result)

    async def search_metrics(
        self, query: str, intent_result=None, top_k: int = 10
    ) -> RAGResult:
        """Recherche dans PostgreSQL pour les métriques avec confidence scoring"""

        if not self.postgres_retriever:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                metadata={"error": "PostgreSQL non disponible"},
            )

        try:
            # Recherche des métriques
            metric_results = await self.postgres_retriever.search_metrics(
                query, intent_result, top_k
            )

            if not metric_results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={"source_type": "metrics", "data_source": "postgresql"},
                )

            # Conversion en Documents pour compatibilité
            documents = []
            for metric in metric_results:
                doc_content = self._format_metric_content(metric)

                doc = Document(
                    content=doc_content,
                    metadata={
                        "company": metric.company,
                        "breed": metric.breed,
                        "strain": metric.strain,
                        "species": metric.species,
                        "metric_name": metric.metric_name,
                        "category": metric.category,
                        "sheet_name": metric.sheet_name,
                        "source_type": "metrics",
                        "data_source": "postgresql",
                        "normalized_search": True,  # NOUVEAU: Indicateur de recherche normalisée
                    },
                    score=metric.confidence,
                )
                documents.append(doc)

            # Calcul confiance globale avec boost pour normalisation
            avg_confidence = sum(m.confidence for m in metric_results) / len(
                metric_results
            )

            # Bonus de confiance si recherche normalisée a trouvé des résultats
            normalized_concepts, _ = (
                self.postgres_retriever.query_normalizer.get_search_terms(query)
            )
            if normalized_concepts:
                avg_confidence = min(1.0, avg_confidence + 0.1)

            return RAGResult(
                documents=documents,
                source=RAGSource.RETRIEVAL_SUCCESS,
                confidence=avg_confidence,
                metadata={
                    "source_type": "metrics",
                    "data_source": "postgresql",
                    "metric_count": len(metric_results),
                    "avg_confidence": avg_confidence,
                    "multilingual_normalization": True,
                    "normalized_concepts": normalized_concepts[
                        :5
                    ],  # Premiers concepts pour debug
                },
            )

        except Exception as e:
            logger.error(f"Erreur recherche métriques PostgreSQL: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "metrics"},
            )

    def _format_metric_content(self, metric: MetricResult) -> str:
        """Formate une métrique en contenu texte pour le LLM"""
        content_parts = [
            f"**{metric.metric_name}**",
            f"Entreprise: {metric.company}",
            f"Race: {metric.breed}",
            f"Lignée: {metric.strain}",
            f"Espèce: {metric.species}",
            f"Catégorie: {metric.category}",
        ]

        # Valeur
        if metric.value_numeric is not None:
            value_str = f"{metric.value_numeric}"
            if metric.unit:
                value_str += f" {metric.unit}"
            content_parts.append(f"Valeur: {value_str}")
        elif metric.value_text:
            content_parts.append(f"Valeur: {metric.value_text}")

        # Age si disponible
        if metric.age_min is not None and metric.age_max is not None:
            if metric.age_min == metric.age_max:
                content_parts.append(f"Age: {metric.age_min} semaines")
            else:
                content_parts.append(f"Age: {metric.age_min}-{metric.age_max} semaines")

        content_parts.append(f"Source: {metric.sheet_name}")
        return "\n".join(content_parts)

    async def close(self):
        """Ferme le système PostgreSQL"""
        if self.postgres_retriever:
            await self.postgres_retriever.close()

    def get_normalization_status(self) -> Dict[str, Any]:
        """Retourne le statut du système de normalisation"""
        if not self.postgres_retriever:
            return {"available": False}

        return {
            "available": True,
            "concept_mappings_count": len(
                self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS
            ),
            "supported_concepts": list(
                self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS.keys()
            ),
            "total_terms": sum(
                len(terms)
                for terms in self.postgres_retriever.query_normalizer.CONCEPT_MAPPINGS.values()
            ),
        }
