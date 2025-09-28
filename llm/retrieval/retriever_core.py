# -*- coding: utf-8 -*-
"""
retriever_core.py - Classe principale HybridWeaviateRetriever avec héritage modulaire
"""

import logging
import re
from typing import Dict, List, Any
from utils.utilities import METRICS
from utils.imports_and_dependencies import (
    WEAVIATE_V4,
    wvc,
)
from config.config import ENABLE_API_DIAGNOSTICS
from .retriever_search import SearchMixin
from .retriever_adaptive import AdaptiveMixin
from .retriever_rrf import RRFMixin

logger = logging.getLogger(__name__)


class HybridWeaviateRetriever(SearchMixin, AdaptiveMixin, RRFMixin):
    """Retriever hybride avec dimension vectorielle correcte dès le départ"""

    def __init__(self, client, collection_name: str = "InteliaExpertKnowledge"):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = hasattr(client, "collections")

        # Configuration dynamique des capacités API
        self.api_capabilities = {
            "hybrid_with_vector": True,
            "hybrid_with_where": True,
            "explain_score_available": False,
            "near_vector_format": "positional",
            "api_stability": "stable",
            "runtime_corrections": 0,
        }

        # Configuration fusion hybride enrichie
        self.fusion_config = {
            "vector_weight": 0.7,
            "bm25_weight": 0.3,
            "rrf_k": 60,
            "min_score_threshold": 0.1,
            "diversity_threshold": 0.8,
            "intent_boost_factors": {
                "search": 1.2,
                "diagnosis": 1.1,
                "protocol": 1.0,
                "economic": 0.9,
            },
        }

        # Cache des métriques pour optimisation
        self.retrieval_cache = {}
        self.last_query_analytics = {}

        # CORRECTION CRITIQUE: Dimension vectorielle correcte dès l'initialisation
        # text-embedding-3-small utilise 1536 dimensions (pas 384)
        self.working_vector_dimension = (
            1536  # CORRIGÉ: OpenAI text-embedding-3-small = 1536
        )
        self.dimension_detection_attempted = False
        self.dimension_detection_success = False

        # RRF Intelligent (sera configuré par RAG Engine)
        self.intelligent_rrf = None

        # Note: La détection sera faite lors du premier appel async pour confirmer

    async def _ensure_dimension_detected(self):
        """S'assure que la dimension est détectée et confirmée avant utilisation"""
        if not self.dimension_detection_attempted:
            await self._detect_vector_dimension()

    async def _detect_vector_dimension(self):
        """Détection et confirmation de la dimension vectorielle avec syntaxe v4"""
        if self.dimension_detection_attempted:
            return self.working_vector_dimension

        self.dimension_detection_attempted = True

        try:
            collection = self.client.collections.get(self.collection_name)

            # Test avec différentes dimensions courantes dans l'ordre de probabilité
            test_vectors = {
                1536: [0.1] * 1536,  # text-embedding-3-small (plus probable)
                3072: [0.1] * 3072,  # text-embedding-3-large
                384: [0.1] * 384,  # anciens modèles
            }

            for size, vector in test_vectors.items():
                try:
                    # Test direct
                    collection.query.near_vector(
                        vector,
                        limit=1,
                    )

                    # Si aucune exception, cette dimension fonctionne
                    self.working_vector_dimension = size
                    self.dimension_detection_success = True

                    if size == 1536:
                        logger.info(
                            f"Dimension vectorielle confirmée: {size} (text-embedding-3-small)"
                        )
                    else:
                        logger.info(f"Dimension vectorielle détectée: {size}")

                    return size

                except Exception as e:
                    error_str = str(e).lower()
                    if any(
                        keyword in error_str
                        for keyword in [
                            "vector lengths don't match",
                            "dimension",
                            "length mismatch",
                            "size mismatch",
                        ]
                    ):
                        logger.debug(f"Dimension {size} incorrecte: {e}")
                        continue
                    else:
                        logger.warning(f"Erreur API Weaviate (dimension {size}): {e}")
                        break

            # Aucune dimension détectée avec succès - garder 1536 par défaut
            logger.warning("Aucune dimension détectée par test, conservation de 1536")
            self.working_vector_dimension = 1536
            return 1536

        except Exception as e:
            logger.error(f"Erreur détection dimension: {e}")
            self.working_vector_dimension = 1536  # CORRIGÉ: Fallback sur 1536
            self.api_capabilities["api_stability"] = "degraded"
            return 1536

    async def diagnose_weaviate_api(self):
        """Diagnostic des capacités API Weaviate"""
        if ENABLE_API_DIAGNOSTICS:
            await self._ensure_dimension_detected()
            await self._test_api_features()

    async def _test_api_features(self):
        """Test des fonctionnalités API avec syntaxe v4"""
        if not self.working_vector_dimension:
            return

        try:
            collection = self.client.collections.get(self.collection_name)
            test_vector = [0.1] * self.working_vector_dimension

            # Test 1: Hybrid query basique
            try:
                collection.query.hybrid(query="test capacity", limit=1)
                logger.info("Hybrid query basique fonctionne")
            except Exception as e:
                logger.warning(f"Hybrid query limité: {e}")
                self.api_capabilities["api_stability"] = "limited"

            # Test 2: Hybrid avec vector
            try:
                collection.query.hybrid(
                    query="test",
                    vector=test_vector,
                    limit=1,
                )
                self.api_capabilities["hybrid_with_vector"] = True
                logger.info("Hybrid avec vector supporté")
            except Exception as e:
                self.api_capabilities["hybrid_with_vector"] = False
                logger.warning(f"Hybrid sans vector: {e}")
                if hasattr(METRICS, "api_correction_applied"):
                    METRICS.api_correction_applied("hybrid_no_vector")

            # Test 3: Explain score
            try:
                if (
                    wvc
                    and hasattr(wvc, "query")
                    and hasattr(wvc.query, "MetadataQuery")
                ):
                    collection.query.near_vector(
                        test_vector,
                        limit=1,
                        return_metadata=wvc.query.MetadataQuery(
                            score=True, explain_score=True
                        ),
                    )
                    self.api_capabilities["explain_score_available"] = True
                    logger.info("Explain score disponible")
            except Exception as e:
                self.api_capabilities["explain_score_available"] = False
                logger.warning(f"Explain score indisponible: {e}")

            # Test 4: Filtres
            try:
                if wvc and hasattr(wvc, "query") and hasattr(wvc.query, "Filter"):
                    test_filter = wvc.query.Filter.by_property("species").equal("test")
                    collection.query.hybrid(query="test", where=test_filter, limit=1)
                    self.api_capabilities["hybrid_with_where"] = True
                    logger.info("Filtres supportés")
            except Exception as e:
                self.api_capabilities["hybrid_with_where"] = False
                logger.warning(f"Filtres non supportés: {e}")

        except Exception as e:
            logger.error(f"Erreur test fonctionnalités API: {e}")
            self.api_capabilities["api_stability"] = "degraded"

    def _adjust_vector_dimension(self, vector: List[float]) -> List[float]:
        """Ajuste automatiquement les dimensions vectorielles"""
        if not self.working_vector_dimension:
            return vector

        expected_dim = self.working_vector_dimension
        current_dim = len(vector)

        if current_dim == expected_dim:
            return vector

        adjusted_vector = vector.copy()

        if current_dim > expected_dim:
            # Tronquer
            adjusted_vector = adjusted_vector[:expected_dim]
            logger.debug(f"Vector tronqué: {current_dim} → {expected_dim}")
        else:
            # Compléter avec des zéros
            adjusted_vector.extend([0.0] * (expected_dim - current_dim))
            logger.debug(f"Vector complété: {current_dim} → {expected_dim}")

        return adjusted_vector

    def _to_v4_filter(self, where_dict):
        """Convertit dict where v3 vers Filter v4"""
        if not where_dict or not WEAVIATE_V4 or not wvc:
            return None

        try:
            if "path" in where_dict:
                property_name = (
                    where_dict["path"][-1]
                    if isinstance(where_dict["path"], list)
                    else where_dict["path"]
                )
                operator = where_dict.get("operator", "Equal")
                value = where_dict.get("valueText", where_dict.get("valueString", ""))

                if operator == "Like":
                    return wvc.query.Filter.by_property(property_name).like(value)
                elif operator == "Equal":
                    return wvc.query.Filter.by_property(property_name).equal(value)
                else:
                    return wvc.query.Filter.by_property(property_name).equal(value)

            operator = where_dict.get("operator", "And").lower()
            operands = [self._to_v4_filter(o) for o in where_dict.get("operands", [])]
            operands = [op for op in operands if op is not None]

            if not operands:
                return None

            if operator == "and" and len(operands) >= 2:
                result = operands[0]
                for op in operands[1:]:
                    result = result & op
                return result
            elif operator == "or" and len(operands) >= 2:
                result = operands[0]
                for op in operands[1:]:
                    result = result | op
                return result
            else:
                return operands[0] if operands else None

        except Exception as e:
            logger.warning(f"Erreur conversion filter v4: {e}")
            return None

    def _calculate_dynamic_alpha(self, query: str, intent_result=None) -> float:
        """Calcule alpha dynamiquement avec gestion robuste des types intent_result"""
        query_lower = query.lower()

        # Boost basé sur l'intention détectée
        intent_boost = 1.0
        intent_value = "general_poultry"

        if intent_result:
            try:
                # CAS 1: Objet IntentResult standard avec attributs
                if hasattr(intent_result, "intent_type"):
                    intent_type_attr = intent_result.intent_type
                    if hasattr(intent_type_attr, "value"):
                        intent_value = intent_type_attr.value
                    else:
                        intent_value = str(intent_type_attr)

                # CAS 2: Dictionnaire
                elif isinstance(intent_result, dict):
                    intent_type = intent_result.get("intent_type")
                    if intent_type:
                        if hasattr(intent_type, "value"):
                            intent_value = intent_type.value
                        elif isinstance(intent_type, str):
                            intent_value = intent_type
                        else:
                            intent_value = str(intent_type)

                # CAS 3: String directement
                elif isinstance(intent_result, str):
                    intent_value = intent_result

            except Exception as e:
                logger.error(
                    f"Erreur traitement intent_result dans alpha calculation: {e}"
                )
                intent_value = "general_poultry"

        # Application du boost selon l'intention
        intent_boost = self.fusion_config.get("intent_boost_factors", {}).get(
            intent_value, 1.0
        )

        # Requêtes factuelles -> favoriser BM25
        if any(
            keyword in query_lower
            for keyword in [
                "combien",
                "quel",
                "quelle",
                "nombre",
                "prix",
                "cout",
                "temperature",
                "duree",
                "age",
                "poids",
                "taille",
            ]
        ):
            base_alpha = 0.3

        # Requêtes temporelles -> BM25
        elif re.search(
            r"\b(jour|semaine|mois|an|annee|h|heure|min|minute)\b", query_lower
        ):
            base_alpha = 0.4

        # Requêtes conceptuelles -> vectoriel
        elif any(
            concept in query_lower
            for concept in [
                "comment",
                "pourquoi",
                "expliquer",
                "difference",
                "ameliorer",
                "optimiser",
                "probleme",
                "solution",
                "recommandation",
                "conseil",
            ]
        ):
            base_alpha = 0.8

        # Requêtes de diagnostic -> équilibré
        elif any(
            diag in query_lower
            for diag in [
                "symptome",
                "maladie",
                "diagnostic",
                "traitement",
                "infection",
                "virus",
                "bacterie",
                "parasite",
            ]
        ):
            base_alpha = 0.6

        # Default équilibré
        else:
            base_alpha = 0.7

        # Application du boost d'intention
        final_alpha = min(0.95, max(0.05, base_alpha * intent_boost))

        logger.debug(
            f"Dynamic alpha: {final_alpha} (base={base_alpha}, boost={intent_boost})"
        )
        return final_alpha

    def _safe_extract_intent_type(self, intent_result) -> str:
        """Extraction sécurisée du type d'intention pour métriques"""
        if not intent_result:
            return None

        try:
            # CAS 1: Objet IntentResult standard
            if hasattr(intent_result, "intent_type"):
                intent_type_attr = intent_result.intent_type
                if hasattr(intent_type_attr, "value"):
                    return intent_type_attr.value
                else:
                    return str(intent_type_attr)

            # CAS 2: Dictionnaire
            elif isinstance(intent_result, dict):
                intent_type = intent_result.get("intent_type")
                if intent_type:
                    if hasattr(intent_type, "value"):
                        return intent_type.value
                    elif isinstance(intent_type, str):
                        return intent_type
                    else:
                        return str(intent_type)

            # CAS 3: String directement
            elif isinstance(intent_result, str):
                return intent_result

        except Exception as e:
            logger.debug(f"Erreur extraction intent_type pour métriques: {e}")

        return "unknown"

    def get_retrieval_analytics(self) -> Dict[str, Any]:
        """Analytics de récupération pour monitoring"""
        return {
            "api_capabilities": self.api_capabilities,
            "last_query_analytics": self.last_query_analytics,
            "fusion_config": self.fusion_config,
            "working_vector_dimension": self.working_vector_dimension,
            "runtime_corrections": self.api_capabilities.get("runtime_corrections", 0),
            "dimension_detection_attempted": self.dimension_detection_attempted,
            "dimension_detection_success": self.dimension_detection_success,
            "intelligent_rrf_configured": bool(self.intelligent_rrf),
        }
