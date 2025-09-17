# -*- coding: utf-8 -*-
"""
enhanced_rrf_fusion.py - RRF Intelligent avec apprentissage contextuel pour l'aviculture
Optimisé pour Digital Ocean App Platform avec Redis externe
"""

import os
import json
import time
import logging
import hashlib
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types de requêtes pour optimisation RRF"""

    METRIC_EXACT = "metric_exact"  # "FCR Ross 308 35j"
    CONCEPTUAL = "conceptual"  # "Comment améliorer"
    DIAGNOSTIC = "diagnostic"  # "Problème respiratoire"
    COMPARISON = "comparison"  # "Ross vs Cobb"
    GENERAL = "general"  # Requête générale


@dataclass
class RRFPerformanceMetric:
    """Métrique de performance RRF"""

    query_hash: str
    context_type: str
    genetic_line: str
    rrf_method: str
    relevance_score: float
    user_feedback: Optional[float]
    timestamp: float
    processing_time: float


@dataclass
class AdaptiveRRFParams:
    """Paramètres RRF adaptatifs"""

    rrf_k: int = 60
    vector_weight: float = 0.7
    bm25_weight: float = 0.3
    genetic_boost: float = 1.0
    age_precision_boost: float = 1.0
    score_multiplier: float = 10.0
    diversity_threshold: float = 0.8


class IntelligentRRFFusion:
    """RRF de nouvelle génération avec apprentissage contextuel aviculture"""

    def __init__(self, redis_client=None, intent_processor=None):
        self.redis = redis_client
        self.intent_processor = intent_processor

        # Configuration aviculture spécialisée
        self.genetic_line_profiles = {
            "ross_308": {
                "vector_preference": 0.35,  # Favorise BM25 pour termes exacts
                "bm25_preference": 0.65,
                "optimal_rrf_k": 45,
                "specialization_boost": 1.3,
            },
            "cobb_500": {
                "vector_preference": 0.30,
                "bm25_preference": 0.70,
                "optimal_rrf_k": 50,
                "specialization_boost": 1.25,
            },
            "hubbard": {
                "vector_preference": 0.40,
                "bm25_preference": 0.60,
                "optimal_rrf_k": 40,
                "specialization_boost": 1.2,
            },
            "isa_brown": {
                "vector_preference": 0.45,
                "bm25_preference": 0.55,
                "optimal_rrf_k": 55,
                "specialization_boost": 1.15,
            },
        }

        self.query_type_optimization = {
            QueryType.METRIC_EXACT: {
                "rrf_k": 30,
                "bm25_boost": 1.4,
                "vector_boost": 0.8,
                "diversity_weight": 0.9,
            },
            QueryType.CONCEPTUAL: {
                "rrf_k": 80,
                "bm25_boost": 0.7,
                "vector_boost": 1.3,
                "diversity_weight": 1.2,
            },
            QueryType.DIAGNOSTIC: {
                "rrf_k": 50,
                "bm25_boost": 1.1,
                "vector_boost": 1.1,
                "diversity_weight": 1.0,
            },
            QueryType.COMPARISON: {
                "rrf_k": 65,
                "bm25_boost": 1.2,
                "vector_boost": 1.0,
                "diversity_weight": 1.3,
            },
        }

        # Historique performance (limitée pour mémoire)
        self.performance_history = deque(maxlen=1000)
        self.adaptation_cache = {}

        # Statistiques temps réel
        self.stats = {
            "total_fusions": 0,
            "genetic_boosts_applied": 0,
            "adaptive_optimizations": 0,
            "cache_hits": 0,
            "learning_updates": 0,
        }

        # Configuration depuis variables d'environnement
        self.enabled = os.getenv("ENABLE_INTELLIGENT_RRF", "false").lower() == "true"
        self.learning_mode = os.getenv("RRF_LEARNING_MODE", "true").lower() == "true"
        self.genetic_boost_enabled = (
            os.getenv("RRF_GENETIC_BOOST", "true").lower() == "true"
        )
        self.debug_mode = os.getenv("RRF_DEBUG_MODE", "false").lower() == "true"

        logger.info(
            f"IntelligentRRF initialisé - Enabled: {self.enabled}, Learning: {self.learning_mode}"
        )

    async def enhanced_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        alpha: float,
        top_k: int,
        query_context: Dict,
        intent_result=None,
    ) -> List[Dict]:
        """Point d'entrée principal pour la fusion RRF intelligente"""

        if not self.enabled:
            return await self._classic_rrf_fallback(
                vector_results, bm25_results, alpha, top_k
            )

        start_time = time.time()
        self.stats["total_fusions"] += 1

        try:
            # 1. Analyse contextuelle avancée
            context = await self._analyze_query_context(query_context, intent_result)

            # 2. Optimisation des paramètres RRF
            rrf_params = await self._get_adaptive_parameters(context)

            # 3. Fusion multi-méthodes
            fusion_candidates = await self._multi_method_fusion(
                vector_results, bm25_results, rrf_params, context
            )

            # 4. Post-processing spécialisé aviculture
            final_results = await self._poultry_specialized_ranking(
                fusion_candidates, context, top_k
            )

            # 5. Enregistrement performance pour apprentissage
            if self.learning_mode:
                await self._record_fusion_performance(
                    context, final_results, time.time() - start_time
                )

            if self.debug_mode:
                logger.debug(
                    f"RRF intelligent: {len(final_results)} docs, "
                    f"context: {context.get('query_type')}, "
                    f"genetic: {context.get('genetic_line', 'none')}, "
                    f"time: {(time.time() - start_time)*1000:.1f}ms"
                )

            return final_results

        except Exception as e:
            logger.error(f"Erreur RRF intelligent: {e}")
            return await self._classic_rrf_fallback(
                vector_results, bm25_results, alpha, top_k
            )

    async def _analyze_query_context(self, query_context: Dict, intent_result) -> Dict:
        """Analyse contextuelle approfondie de la requête"""

        query = query_context.get("query", "")
        query_lower = query.lower()

        # Extraction entités depuis intent_result
        entities = {}
        if intent_result and hasattr(intent_result, "detected_entities"):
            entities = intent_result.detected_entities

        # Détection lignée génétique
        genetic_line = entities.get("line", "") or self._detect_genetic_line(
            query_lower
        )

        # Détection âge
        age_days = entities.get("age_days")
        age_weeks = entities.get("age_weeks")

        # Détection métriques performance
        performance_metrics = self._extract_performance_metrics(query_lower)

        # Classification type de requête
        query_type = self._classify_query_type(query_lower, entities)

        # Détection urgence/diagnostic
        urgency_level = self._assess_urgency(query_lower)

        context = {
            "query": query,
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
            "genetic_line": genetic_line.lower() if genetic_line else "",
            "age_days": age_days,
            "age_weeks": age_weeks,
            "performance_metrics": performance_metrics,
            "query_type": query_type,
            "urgency_level": urgency_level,
            "intent_confidence": getattr(intent_result, "confidence", 0.0),
            "has_age_metric": bool(age_days or age_weeks),
            "has_performance_metric": bool(performance_metrics),
            "is_comparative": any(
                word in query_lower
                for word in ["vs", "versus", "contre", "par rapport"]
            ),
            "seasonal_context": self._detect_seasonal_context(query_lower),
            "timestamp": time.time(),
        }

        return context

    async def _get_adaptive_parameters(self, context: Dict) -> AdaptiveRRFParams:
        """Calcule les paramètres RRF optimaux selon le contexte"""

        # Paramètres de base
        params = AdaptiveRRFParams()

        # Cache adaptatif
        cache_key = f"rrf_params:{context['query_hash'][:4]}:{context.get('genetic_line', 'none')}"

        if cache_key in self.adaptation_cache:
            cached_params = self.adaptation_cache[cache_key]
            self.stats["cache_hits"] += 1
            return cached_params

        # Adaptation par lignée génétique
        genetic_line = context.get("genetic_line", "")
        if genetic_line in self.genetic_line_profiles:
            profile = self.genetic_line_profiles[genetic_line]
            params.vector_weight = profile["vector_preference"]
            params.bm25_weight = profile["bm25_preference"]
            params.rrf_k = profile["optimal_rrf_k"]
            params.genetic_boost = profile["specialization_boost"]

            if self.genetic_boost_enabled:
                self.stats["genetic_boosts_applied"] += 1

        # Adaptation par type de requête
        query_type = context.get("query_type", QueryType.GENERAL)
        if query_type in self.query_type_optimization:
            type_config = self.query_type_optimization[query_type]
            params.rrf_k = min(params.rrf_k, type_config["rrf_k"])
            params.vector_weight *= type_config["vector_boost"]
            params.bm25_weight *= type_config["bm25_boost"]
            params.diversity_threshold = type_config["diversity_weight"]

        # Boost précision âge
        if context.get("has_age_metric") and context.get("has_performance_metric"):
            params.rrf_k = max(25, params.rrf_k - 15)  # Plus précis
            params.age_precision_boost = 1.4

        # Normalisation des poids
        total_weight = params.vector_weight + params.bm25_weight
        params.vector_weight /= total_weight
        params.bm25_weight /= total_weight

        # Cache pour futures requêtes similaires
        self.adaptation_cache[cache_key] = params
        self.stats["adaptive_optimizations"] += 1

        return params

    async def _multi_method_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        params: AdaptiveRRFParams,
        context: Dict,
    ) -> List[Dict]:
        """Fusion avec méthodes multiples et sélection optimale"""

        # Méthodes de fusion disponibles
        fusion_methods = {
            "weighted_rrf": self._weighted_rrf_fusion,
            "score_interpolation": self._score_interpolation_fusion,
            "rank_biased_precision": self._rbp_fusion,
        }

        # Sélection méthode selon contexte
        optimal_method = self._select_fusion_method(context)
        fusion_func = fusion_methods.get(optimal_method, self._weighted_rrf_fusion)

        return await fusion_func(vector_results, bm25_results, params, context)

    async def _weighted_rrf_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        params: AdaptiveRRFParams,
        context: Dict,
    ) -> List[Dict]:
        """Fusion RRF pondérée avec boost spécialisé aviculture"""

        all_docs = {}

        # Traitement résultats vectoriels
        for i, doc in enumerate(vector_results):
            content_key = self._generate_content_key(doc)
            specialization_boost = self._calculate_poultry_boost(doc, context)

            all_docs[content_key] = {
                "doc": doc,
                "vector_rank": i + 1,
                "vector_score": doc.get("score", 0.0),
                "bm25_rank": None,
                "bm25_score": 0.0,
                "specialization_boost": specialization_boost,
            }

        # Traitement résultats BM25
        for i, doc in enumerate(bm25_results):
            content_key = self._generate_content_key(doc)

            if content_key in all_docs:
                all_docs[content_key]["bm25_rank"] = i + 1
                all_docs[content_key]["bm25_score"] = doc.get("score", 0.0)
            else:
                specialization_boost = self._calculate_poultry_boost(doc, context)
                all_docs[content_key] = {
                    "doc": doc,
                    "vector_rank": None,
                    "vector_score": 0.0,
                    "bm25_rank": i + 1,
                    "bm25_score": doc.get("score", 0.0),
                    "specialization_boost": specialization_boost,
                }

        # Calcul scores RRF pondérés
        final_docs = []
        for content_key, data in all_docs.items():

            rrf_score = 0.0

            # Composante vectorielle
            if data["vector_rank"]:
                vector_contribution = (
                    params.vector_weight * data["specialization_boost"]
                ) / (params.rrf_k + data["vector_rank"])
                rrf_score += vector_contribution

            # Composante BM25
            if data["bm25_rank"]:
                bm25_contribution = params.bm25_weight / (
                    params.rrf_k + data["bm25_rank"]
                )
                rrf_score += bm25_contribution

            # Score final avec multiplicateur
            final_score = rrf_score * params.score_multiplier * params.genetic_boost

            # Enrichissement métadonnées
            doc = data["doc"].copy()
            if "metadata" not in doc:
                doc["metadata"] = {}

            doc["metadata"].update(
                {
                    "rrf_method": "weighted_intelligent",
                    "genetic_boost": data["specialization_boost"],
                    "final_rrf_score": final_score,
                    "vector_rank": data["vector_rank"],
                    "bm25_rank": data["bm25_rank"],
                    "context_type": context.get("query_type", "unknown"),
                    "genetic_line_detected": context.get("genetic_line", "none"),
                }
            )

            doc["final_score"] = final_score
            final_docs.append(doc)

        return sorted(final_docs, key=lambda x: x["final_score"], reverse=True)

    async def _poultry_specialized_ranking(
        self, candidates: List[Dict], context: Dict, top_k: int
    ) -> List[Dict]:
        """Post-processing avec optimisations spécialisées aviculture"""

        # Filtrage diversité
        diverse_results = self._apply_diversity_filter(candidates, context)

        # Boost urgence médicale
        if context.get("urgency_level", 0) > 0.7:
            diverse_results = self._boost_medical_urgency(diverse_results)

        # Boost cohérence lignée-métrique
        if context.get("genetic_line") and context.get("has_performance_metric"):
            diverse_results = self._boost_genetic_metric_coherence(
                diverse_results, context
            )

        return diverse_results[:top_k]

    def _calculate_poultry_boost(self, doc: Dict, context: Dict) -> float:
        """Calcule le boost spécialisé aviculture pour un document"""

        content = doc.get("content", "").lower()
        boost = 1.0

        # Boost lignée génétique exacte
        genetic_line = context.get("genetic_line", "")
        if genetic_line and genetic_line in content:
            boost *= 1.3

        # Boost âge précis
        age_days = context.get("age_days")
        if age_days:
            age_patterns = [f"{age_days}j", f"{age_days} j", f"{age_days} jour"]
            if any(pattern in content for pattern in age_patterns):
                boost *= 1.4

        # Boost métrique + lignée (combo parfait)
        if (
            context.get("genetic_line")
            and context.get("has_performance_metric")
            and genetic_line in content
            and any(
                metric in content for metric in context.get("performance_metrics", [])
            )
        ):
            boost *= 1.5

        # Boost source technique
        source_type = doc.get("metadata", {}).get("source", "")
        if any(
            keyword in source_type.lower()
            for keyword in ["guide", "référence", "technique", "standard"]
        ):
            boost *= 1.2

        return min(2.0, boost)  # Limite le boost maximum

    def _classify_query_type(self, query_lower: str, entities: Dict) -> QueryType:
        """Classifie le type de requête pour optimisation"""

        # Requête métrique exacte
        if any(
            metric in query_lower for metric in ["fcr", "poids", "mortalité", "ponte"]
        ) and any(
            genetic in query_lower for genetic in ["ross", "cobb", "hubbard", "isa"]
        ):
            return QueryType.METRIC_EXACT

        # Requête comparative
        if any(
            comp in query_lower
            for comp in [
                "vs",
                "versus",
                "contre",
                "par rapport",
                "différence",
                "compare",
            ]
        ):
            return QueryType.COMPARISON

        # Requête conceptuelle
        if any(
            concept in query_lower
            for concept in [
                "comment",
                "pourquoi",
                "expliquer",
                "améliorer",
                "optimiser",
            ]
        ):
            return QueryType.CONCEPTUAL

        # Requête diagnostic
        if any(
            diag in query_lower
            for diag in ["problème", "symptôme", "maladie", "diagnostic", "traitement"]
        ):
            return QueryType.DIAGNOSTIC

        return QueryType.GENERAL

    # === MÉTHODES UTILITAIRES ===

    def _detect_genetic_line(self, query_lower: str) -> str:
        """Détecte la lignée génétique dans la requête"""
        genetic_patterns = {
            "ross_308": ["ross 308", "ross308", "r308", "r-308"],
            "cobb_500": ["cobb 500", "cobb500", "c500", "c-500"],
            "hubbard": ["hubbard", "hub", "hubbard flex"],
            "isa_brown": ["isa brown", "isa-brown", "isabrown"],
        }

        for genetic_line, patterns in genetic_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return genetic_line

        return ""

    def _extract_performance_metrics(self, query_lower: str) -> List[str]:
        """Extrait les métriques de performance de la requête"""
        metrics = []
        metric_patterns = {
            "fcr": ["fcr", "conversion", "feed conversion"],
            "poids": ["poids", "weight", "masse"],
            "mortalité": ["mortalité", "mortality", "mort"],
            "ponte": ["ponte", "production", "laying"],
            "gain": ["gain", "croissance", "growth"],
        }

        for metric, patterns in metric_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                metrics.append(metric)

        return metrics

    def _assess_urgency(self, query_lower: str) -> float:
        """Évalue le niveau d'urgence de la requête"""
        urgency_keywords = {
            "critique": 1.0,
            "urgent": 0.9,
            "problème": 0.7,
            "symptôme": 0.8,
            "maladie": 0.8,
            "mortalité élevée": 1.0,
            "que faire": 0.6,
        }

        max_urgency = 0.0
        for keyword, score in urgency_keywords.items():
            if keyword in query_lower:
                max_urgency = max(max_urgency, score)

        return max_urgency

    def _generate_content_key(self, doc: Dict) -> str:
        """Génère une clé unique pour le document"""
        content = doc.get("content", "")
        title = doc.get("metadata", {}).get("title", "")
        return hashlib.md5(f"{title}:{content[:100]}".encode()).hexdigest()[:16]

    def _select_fusion_method(self, context: Dict) -> str:
        """Sélectionne la méthode de fusion optimale"""
        query_type = context.get("query_type", QueryType.GENERAL)

        if query_type == QueryType.METRIC_EXACT:
            return "weighted_rrf"
        elif query_type == QueryType.COMPARISON:
            return "rank_biased_precision"
        else:
            return "weighted_rrf"

    async def _classic_rrf_fallback(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        alpha: float,
        top_k: int,
    ) -> List[Dict]:
        """Fallback vers RRF classique en cas d'erreur"""
        logger.warning("Fallback vers RRF classique")

        # Implémentation RRF simple comme fallback
        all_docs = {}
        rrf_k = 60

        for i, doc in enumerate(vector_results):
            content_key = self._generate_content_key(doc)
            all_docs[content_key] = {
                "doc": doc,
                "vector_rank": i + 1,
                "bm25_rank": None,
            }

        for i, doc in enumerate(bm25_results):
            content_key = self._generate_content_key(doc)
            if content_key in all_docs:
                all_docs[content_key]["bm25_rank"] = i + 1
            else:
                all_docs[content_key] = {
                    "doc": doc,
                    "vector_rank": None,
                    "bm25_rank": i + 1,
                }

        final_docs = []
        for content_key, data in all_docs.items():
            rrf_score = 0.0
            if data["vector_rank"]:
                rrf_score += alpha / (rrf_k + data["vector_rank"])
            if data["bm25_rank"]:
                rrf_score += (1 - alpha) / (rrf_k + data["bm25_rank"])

            doc = data["doc"].copy()
            doc["final_score"] = rrf_score * 10
            final_docs.append(doc)

        return sorted(final_docs, key=lambda x: x["final_score"], reverse=True)[:top_k]

    # === MÉTHODES D'APPRENTISSAGE ===

    async def _record_fusion_performance(
        self, context: Dict, results: List[Dict], processing_time: float
    ):
        """Enregistre les performances pour apprentissage futur"""
        if not self.learning_mode or not self.redis:
            return

        try:
            metric = RRFPerformanceMetric(
                query_hash=context["query_hash"],
                context_type=context.get("query_type", "unknown"),
                genetic_line=context.get("genetic_line", "none"),
                rrf_method="intelligent_weighted",
                relevance_score=self._calculate_relevance_score(results),
                user_feedback=None,  # À implémenter plus tard
                timestamp=time.time(),
                processing_time=processing_time,
            )

            # Stockage Redis pour analytics
            redis_key = f"rrf_performance:{metric.query_hash}:{int(metric.timestamp)}"
            await self.redis.setex(
                redis_key, 86400, json.dumps(asdict(metric))
            )  # 24h TTL

            self.performance_history.append(metric)
            self.stats["learning_updates"] += 1

        except Exception as e:
            logger.warning(f"Erreur enregistrement performance RRF: {e}")

    def _calculate_relevance_score(self, results: List[Dict]) -> float:
        """Calcule un score de pertinence approximatif"""
        if not results:
            return 0.0

        # Score basé sur la distribution des scores finaux
        scores = [doc.get("final_score", 0.0) for doc in results[:5]]
        if not scores:
            return 0.0

        avg_score = sum(scores) / len(scores)
        return min(1.0, avg_score / 10.0)  # Normalisation

    def get_performance_stats(self) -> Dict:
        """Retourne les statistiques de performance"""
        return {
            **self.stats,
            "enabled": self.enabled,
            "learning_mode": self.learning_mode,
            "genetic_boost_enabled": self.genetic_boost_enabled,
            "cache_size": len(self.adaptation_cache),
            "history_size": len(self.performance_history),
        }

    # === MÉTHODES POST-PROCESSING ===

    def _apply_diversity_filter(
        self, candidates: List[Dict], context: Dict
    ) -> List[Dict]:
        """Applique un filtre de diversité"""
        if len(candidates) <= 3:
            return candidates

        diverse_results = [candidates[0]]  # Garde toujours le premier

        for candidate in candidates[1:]:
            is_diverse = True
            candidate_content = candidate.get("content", "").lower()

            for existing in diverse_results:
                existing_content = existing.get("content", "").lower()

                # Similarité simple par mots communs
                candidate_words = set(candidate_content.split())
                existing_words = set(existing_content.split())

                if candidate_words and existing_words:
                    overlap = len(candidate_words.intersection(existing_words))
                    similarity = overlap / min(
                        len(candidate_words), len(existing_words)
                    )

                    if similarity > context.get("diversity_threshold", 0.8):
                        is_diverse = False
                        break

            if is_diverse:
                diverse_results.append(candidate)

        return diverse_results

    def _boost_medical_urgency(self, results: List[Dict]) -> List[Dict]:
        """Boost les documents d'urgence médicale"""
        medical_keywords = [
            "traitement",
            "diagnostic",
            "symptôme",
            "maladie",
            "vétérinaire",
        ]

        for doc in results:
            content = doc.get("content", "").lower()
            if any(keyword in content for keyword in medical_keywords):
                doc["final_score"] *= 1.2

        return sorted(results, key=lambda x: x["final_score"], reverse=True)

    def _boost_genetic_metric_coherence(
        self, results: List[Dict], context: Dict
    ) -> List[Dict]:
        """Boost la cohérence lignée-métrique"""
        genetic_line = context.get("genetic_line", "")
        performance_metrics = context.get("performance_metrics", [])

        if not genetic_line or not performance_metrics:
            return results

        for doc in results:
            content = doc.get("content", "").lower()

            has_genetic = genetic_line in content
            has_metric = any(metric in content for metric in performance_metrics)

            if has_genetic and has_metric:
                doc["final_score"] *= 1.3  # Boost cohérence

        return sorted(results, key=lambda x: x["final_score"], reverse=True)

    def _detect_seasonal_context(self, query_lower: str) -> str:
        """Détecte le contexte saisonnier"""
        seasonal_keywords = {
            "hiver": "winter",
            "été": "summer",
            "printemps": "spring",
            "automne": "autumn",
            "froid": "winter",
            "chaud": "summer",
        }

        for keyword, season in seasonal_keywords.items():
            if keyword in query_lower:
                return season

        return "none"

    # === MÉTHODES DE FUSION ALTERNATIVES ===

    async def _score_interpolation_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        params: AdaptiveRRFParams,
        context: Dict,
    ) -> List[Dict]:
        """Fusion par interpolation de scores"""
        # Implémentation alternative simple
        return await self._weighted_rrf_fusion(
            vector_results, bm25_results, params, context
        )

    async def _rbp_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        params: AdaptiveRRFParams,
        context: Dict,
    ) -> List[Dict]:
        """Fusion Rank-Biased Precision"""
        # Implémentation alternative simple
        return await self._weighted_rrf_fusion(
            vector_results, bm25_results, params, context
        )
