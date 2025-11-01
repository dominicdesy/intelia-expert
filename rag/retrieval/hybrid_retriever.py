# -*- coding: utf-8 -*-
"""
hybrid_retriever.py - Retriever hybride optimisé avec RRF Intelligent
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
hybrid_retriever.py - Retriever hybride optimisé avec RRF Intelligent
Combine recherche vectorielle et BM25 avec fusion intelligente
CORRIGÉ: Ajout fonction hybrid_search globale pour import depuis rag_engine.py
"""

import asyncio
import logging
from utils.types import Dict, List, Optional
import anyio

# === NOUVEAU: Import RRF Intelligent ===
try:
    from retrieval.enhanced_rrf_fusion import IntelligentRRFFusion

    # CORRECTION: Suppression de l'import RRF_LEARNING_MODE non utilisé
    from config.config import ENABLE_INTELLIGENT_RRF

    INTELLIGENT_RRF_AVAILABLE = True
except ImportError:
    INTELLIGENT_RRF_AVAILABLE = False

# === NOUVEAU: Import Advanced Boosting ===
try:
    from retrieval.advanced_boosting import AdvancedResultBoosting
    ADVANCED_BOOSTING_AVAILABLE = True
except ImportError:
    ADVANCED_BOOSTING_AVAILABLE = False

logger = logging.getLogger(__name__)


class OptimizedHybridRetriever:
    """Retriever hybride avec fusion optimisée des scores"""

    def __init__(self, client, collection_name: str = "InteliaKnowledge", enable_advanced_boosting: bool = True):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = hasattr(client, "collections")

        # Configuration de fusion hybride
        self.fusion_config = {
            "vector_weight": 0.7,  # Poids recherche vectorielle
            "bm25_weight": 0.3,  # Poids recherche BM25
            "rrf_k": 60,  # Paramètre Reciprocal Rank Fusion
            "min_score_threshold": 0.1,  # Score minimum pour inclusion
            "diversity_threshold": 0.8,  # Seuil de similarité pour diversité
        }

        # === NOUVEAU: RRF Intelligent ===
        self.intelligent_rrf = None
        if INTELLIGENT_RRF_AVAILABLE and ENABLE_INTELLIGENT_RRF:
            logger.info("🧠 RRF Intelligent disponible pour HybridRetriever")

        # === NOUVEAU: Advanced Boosting ===
        self.advanced_booster = None
        self.enable_advanced_boosting = enable_advanced_boosting
        if ADVANCED_BOOSTING_AVAILABLE and enable_advanced_boosting:
            self.advanced_booster = AdvancedResultBoosting(
                quality_boost_weight=0.2,  # +20% max for quality
                breed_boost_multiplier=1.3,  # +30% for breed match
                disease_boost_multiplier=1.2,  # +20% for disease match
                medication_boost_multiplier=1.15  # +15% for medication match
            )
            logger.info("✨ Advanced Boosting activé pour HybridRetriever")

    def set_intelligent_rrf(self, intelligent_rrf: "IntelligentRRFFusion"):
        """Configure le RRF intelligent (appelé depuis RAG Engine)"""
        self.intelligent_rrf = intelligent_rrf
        logger.info("✅ RRF Intelligent configuré pour HybridRetriever")

    async def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 15,
        where_filter: Optional[Dict] = None,
        alpha: float = 0.7,
        query_context: Optional[Dict] = None,
        intent_result=None,
    ) -> List[Dict]:
        """
        Recherche hybride optimisée combinant vector et BM25
        avec RRF intelligent optionnel
        """
        try:
            # === NOUVEAU: Utilisation RRF Intelligent si disponible ===
            if (
                self.intelligent_rrf
                and self.intelligent_rrf.enabled
                and ENABLE_INTELLIGENT_RRF
                and query_context
            ):

                return await self._hybrid_search_with_intelligent_rrf(
                    query_vector,
                    query_text,
                    top_k,
                    where_filter,
                    alpha,
                    query_context,
                    intent_result,
                )

            # Sinon, utilisation fusion classique
            if self.is_v4:
                return await self._hybrid_search_v4(
                    query_vector, query_text, top_k, where_filter, alpha
                )
            else:
                return await self._hybrid_search_v3(
                    query_vector, query_text, top_k, where_filter, alpha
                )

        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            # Fallback vers recherche vectorielle seule
            return await self._vector_search_fallback(query_vector, top_k, where_filter)

    # === NOUVEAU: MÉTHODE RRF INTELLIGENT ===

    async def _hybrid_search_with_intelligent_rrf(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int,
        where_filter: Dict,
        alpha: float,
        query_context: Dict,
        intent_result,
    ) -> List[Dict]:
        """Recherche hybride utilisant le RRF intelligent"""

        try:
            # 1. Recherche vectorielle étendue
            vector_results = await self._vector_search_v4(
                query_vector, top_k * 2, where_filter
            )

            # 2. Recherche BM25 étendue (via hybrid avec alpha=0)
            bm25_results = await self._bm25_search_v4(
                query_text, top_k * 2, where_filter
            )

            # 3. Fusion via RRF intelligent
            enhanced_results = await self.intelligent_rrf.enhanced_fusion(
                vector_results, bm25_results, alpha, top_k, query_context, intent_result
            )

            logger.debug(
                f"RRF Intelligent: {len(vector_results)} vector + "
                f"{len(bm25_results)} BM25 → {len(enhanced_results)} fusionnés"
            )

            return enhanced_results

        except Exception as e:
            logger.error(f"Erreur RRF intelligent: {e}")
            # Fallback vers fusion classique
            return await self._hybrid_search_v4(
                query_vector, query_text, top_k, where_filter, alpha
            )

    # === MÉTHODES RECHERCHE SÉPARÉES POUR RRF ===

    async def _vector_search_v4(
        self, query_vector: List[float], top_k: int, where_filter: Dict
    ) -> List[Dict]:
        """Recherche vectorielle pure pour RRF intelligent"""

        def _sync_vector_search():
            import weaviate.classes as wvc

            collection = self.client.collections.get(self.collection_name)

            search_params = {
                "vector": query_vector,
                "limit": top_k,
                "return_metadata": wvc.query.MetadataQuery(score=True),
            }

            if where_filter:
                v4_filter = self._convert_to_v4_filter(where_filter)
                if v4_filter:
                    search_params["where"] = v4_filter

            return collection.query.near_vector(**search_params)

        try:
            response = await anyio.to_thread.run_sync(_sync_vector_search)

            documents = []
            for obj in response.objects:
                doc = {
                    "content": obj.properties.get("content", ""),
                    "metadata": {
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "source_file": obj.properties.get("source_file", ""),  # For image retrieval
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "search_type": "vector_only",
                    },
                    "score": float(getattr(obj.metadata, "score", 0.0)),
                    "search_type": "vector",
                }
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v4: {e}")
            return []

    async def _bm25_search_v4(
        self, query_text: str, top_k: int, where_filter: Dict
    ) -> List[Dict]:
        """Recherche BM25 pure pour RRF intelligent"""

        def _sync_bm25_search():
            import weaviate.classes as wvc

            collection = self.client.collections.get(self.collection_name)

            # Recherche BM25 via hybrid avec alpha=0 (BM25 pur)
            search_params = {
                "query": query_text,
                "alpha": 0.0,  # 100% BM25
                "limit": top_k,
                "return_metadata": wvc.query.MetadataQuery(score=True),
            }

            if where_filter:
                v4_filter = self._convert_to_v4_filter(where_filter)
                if v4_filter:
                    search_params["where"] = v4_filter

            return collection.query.hybrid(**search_params)

        try:
            response = await anyio.to_thread.run_sync(_sync_bm25_search)

            documents = []
            for obj in response.objects:
                doc = {
                    "content": obj.properties.get("content", ""),
                    "metadata": {
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "source_file": obj.properties.get("source_file", ""),  # For image retrieval
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "search_type": "bm25_only",
                    },
                    "score": float(getattr(obj.metadata, "score", 0.0)),
                    "search_type": "bm25",
                }
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Erreur recherche BM25 v4: {e}")
            return []

    # === MÉTHODES HYBRIDES CLASSIQUES (EXISTANTES) ===

    async def _hybrid_search_v4(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int,
        where_filter: Dict,
        alpha: float,
    ) -> List[Dict]:
        """Recherche hybride native Weaviate v4 (méthode existante)"""
        try:

            def _sync_hybrid_search():
                import weaviate.classes as wvc

                collection = self.client.collections.get(self.collection_name)

                # Paramètres de recherche hybride
                search_params = {
                    "query": query_text,
                    "vector": query_vector,
                    "alpha": alpha,  # Fusion automatique par Weaviate
                    "limit": top_k,
                    "return_metadata": wvc.query.MetadataQuery(
                        score=True, explain_score=True
                    ),
                }

                # Ajouter les filtres si présents
                if where_filter:
                    v4_filter = self._convert_to_v4_filter(where_filter)
                    if v4_filter:
                        search_params["where"] = v4_filter

                return collection.query.hybrid(**search_params)

            response = await anyio.to_thread.run_sync(_sync_hybrid_search)

            documents = []
            for obj in response.objects:
                # Score hybride fourni par Weaviate
                hybrid_score = float(getattr(obj.metadata, "score", 0.0))

                # Explication du score si disponible
                explain_score = getattr(obj.metadata, "explain_score", None)

                doc = {
                    "content": obj.properties.get("content", ""),
                    "metadata": {
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "source_file": obj.properties.get("source_file", ""),  # For image retrieval
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "hybrid_used": True,
                        "alpha": alpha,
                        "explain_score": explain_score,
                        "search_type": "hybrid_native_v4",
                    },
                    "score": hybrid_score,
                    "search_type": "hybrid_native_v4",
                    # Add quality and entity fields for boosting
                    "quality_score": obj.properties.get("quality_score"),
                    "breeds": obj.properties.get("breeds", []),
                    "diseases": obj.properties.get("diseases", []),
                    "medications": obj.properties.get("medications", []),
                }
                documents.append(doc)

            logger.debug(
                f"Recherche hybride v4: {len(documents)} documents (alpha={alpha})"
            )

            # === NOUVEAU: Apply Advanced Boosting ===
            if self.advanced_booster and documents:
                documents = self.advanced_booster.boost_results(
                    results=documents,
                    query_text=query_text
                )
                logger.debug(f"Advanced boosting applied to {len(documents)} results")

            return documents

        except Exception as e:
            logger.error(f"Erreur recherche hybride v4: {e}")
            raise

    async def _hybrid_search_v3(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int,
        where_filter: Dict,
        alpha: float,
    ) -> List[Dict]:
        """Recherche hybride manuelle pour Weaviate v3"""
        try:
            # Lancer recherche vectorielle et BM25 en parallèle
            vector_task = self._vector_search_v3(query_vector, top_k * 2, where_filter)
            bm25_task = self._bm25_search_v3(query_text, top_k * 2, where_filter)

            vector_results, bm25_results = await asyncio.gather(
                vector_task, bm25_task, return_exceptions=True
            )

            # Gérer les erreurs
            if isinstance(vector_results, Exception):
                logger.warning(f"Erreur recherche vectorielle: {vector_results}")
                vector_results = []
            if isinstance(bm25_results, Exception):
                logger.warning(f"Erreur recherche BM25: {bm25_results}")
                bm25_results = []

            # === MODIFICATION: Utiliser RRF intelligent si disponible ===
            if (
                self.intelligent_rrf
                and self.intelligent_rrf.enabled
                and ENABLE_INTELLIGENT_RRF
            ):

                query_context = {"query": query_text, "alpha": alpha, "top_k": top_k}

                fused_results = await self.intelligent_rrf.enhanced_fusion(
                    vector_results, bm25_results, alpha, top_k, query_context, None
                )
            else:
                # Fusion RRF classique
                fused_results = self._fuse_results(
                    vector_results, bm25_results, alpha, top_k
                )

            logger.debug(
                "hybrid_retriever: alpha=%.2f bm25=%d vector=%d fused=%d",
                alpha,
                len(bm25_results),
                len(vector_results),
                len(fused_results),
            )

            # Diversité: remove quasi-duplicates
            deduped = self._apply_diversity_filter(fused_results)

            return deduped[:top_k]

        except Exception as e:
            logger.error(f"Erreur recherche hybride v3: {e}")
            raise

    def _fuse_results(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        alpha: float,
        top_k: int,
    ) -> List[Dict]:
        """Fusion avancée des résultats avec RRF et normalisation (méthode existante)"""
        try:
            # Indexer par contenu pour déduplication
            all_docs = {}

            # Traiter les résultats vectoriels
            for i, doc in enumerate(vector_results):
                content_key = doc.get("content", "")[
                    :100
                ]  # Clé basée sur début du contenu

                if content_key not in all_docs:
                    all_docs[content_key] = {
                        "doc": doc,
                        "vector_rank": i + 1,
                        "vector_score": doc.get("score", 0.0),
                        "bm25_rank": None,
                        "bm25_score": 0.0,
                    }

            # Traiter les résultats BM25
            for i, doc in enumerate(bm25_results):
                content_key = doc.get("content", "")[:100]

                if content_key in all_docs:
                    all_docs[content_key]["bm25_rank"] = i + 1
                    all_docs[content_key]["bm25_score"] = doc.get("score", 0.0)
                else:
                    # Document trouvé uniquement par BM25
                    all_docs[content_key] = {
                        "doc": doc,
                        "vector_rank": None,
                        "vector_score": 0.0,
                        "bm25_rank": i + 1,
                        "bm25_score": doc.get("score", 0.0),
                    }

            # Calcul du score hybride avec RRF (Reciprocal Rank Fusion)
            fused_docs = []
            for content_key, data in all_docs.items():
                doc = data["doc"]

                # Score RRF
                rrf_score = 0.0
                if data["vector_rank"]:
                    rrf_score += alpha / (
                        self.fusion_config["rrf_k"] + data["vector_rank"]
                    )
                if data["bm25_rank"]:
                    rrf_score += (1 - alpha) / (
                        self.fusion_config["rrf_k"] + data["bm25_rank"]
                    )

                # Score normalisé pondéré (alternative)
                normalized_score = (
                    alpha * data["vector_score"] + (1 - alpha) * data["bm25_score"]
                )

                # Utiliser le maximum des deux méthodes pour robustesse
                final_score = max(
                    rrf_score * 10, normalized_score
                )  # *10 pour calibrer RRF

                if final_score >= self.fusion_config["min_score_threshold"]:
                    # Enrichir les métadonnées
                    if "metadata" not in doc:
                        doc["metadata"] = {}

                    doc["metadata"].update(
                        {
                            "hybrid_used": True,
                            "fusion_method": "rrf_weighted",
                            "alpha": alpha,
                            "vector_rank": data["vector_rank"],
                            "bm25_rank": data["bm25_rank"],
                            "vector_score": data["vector_score"],
                            "bm25_score": data["bm25_score"],
                            "rrf_score": rrf_score,
                            "normalized_score": normalized_score,
                        }
                    )

                    doc["final_score"] = final_score
                    fused_docs.append(doc)

            # Tri par score final
            return sorted(
                fused_docs, key=lambda x: x.get("final_score", 0), reverse=True
            )

        except Exception as e:
            logger.error(f"Erreur fusion RRF: {e}")
            return vector_results[:top_k]  # Fallback

    def _apply_diversity_filter(self, results: List[Dict]) -> List[Dict]:
        """Applique un filtre de diversité"""
        if len(results) <= 3:
            return results

        diverse_results = [results[0]]  # Garde toujours le premier

        for candidate in results[1:]:
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

                    if similarity > self.fusion_config["diversity_threshold"]:
                        is_diverse = False
                        break

            if is_diverse:
                diverse_results.append(candidate)

        return diverse_results

    # === MÉTHODES UTILITAIRES ===

    def _convert_to_v4_filter(self, where_dict):
        """Convertit dict where v3 vers Filter v4"""
        if not where_dict:
            return None

        try:
            import weaviate.classes as wvc

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

            return None

        except Exception as e:
            logger.warning(f"Erreur conversion filter v4: {e}")
            return None

    async def _vector_search_fallback(
        self, query_vector: List[float], top_k: int, where_filter: Dict
    ) -> List[Dict]:
        """Recherche vectorielle de fallback"""
        try:
            return await self._vector_search_v4(query_vector, top_k, where_filter)
        except Exception as e:
            logger.error(f"Erreur fallback vectoriel: {e}")
            return []

    def get_fusion_stats(self) -> Dict:
        """Retourne les statistiques de configuration de fusion"""
        stats = {
            "fusion_config": self.fusion_config,
            "weaviate_version": "v4" if self.is_v4 else "v3",
            "native_hybrid_support": self.is_v4,
            "intelligent_rrf": {
                "available": INTELLIGENT_RRF_AVAILABLE,
                "enabled": ENABLE_INTELLIGENT_RRF,
                "configured": bool(self.intelligent_rrf),
            },
            "fusion_methods": [
                "reciprocal_rank_fusion",
                "weighted_score_normalization",
                "diversity_filtering",
                "adaptive_alpha_selection",
            ],
        }

        if self.intelligent_rrf:
            stats["intelligent_rrf"][
                "performance"
            ] = self.intelligent_rrf.get_performance_stats()

        return stats

    # === MÉTHODES V3 LEGACY ===

    async def _vector_search_v3(
        self, query_vector: List[float], top_k: int, where_filter: Dict
    ) -> List[Dict]:
        """Recherche vectorielle Weaviate v3"""
        # Implémentation legacy pour v3 (simplifiée)
        return []

    async def _bm25_search_v3(
        self, query_text: str, top_k: int, where_filter: Dict
    ) -> List[Dict]:
        """Recherche BM25 Weaviate v3"""
        # Implémentation legacy pour v3 (simplifiée)
        return []


# ============================================================================
# FONCTIONS GLOBALES POUR COMPATIBILITÉ - CORRECTION CRITIQUE
# ============================================================================


async def hybrid_search(
    query_vector: List[float],
    query_text: str,
    client,
    collection_name: str = "InteliaKnowledge",
    top_k: int = 15,
    where_filter: Optional[Dict] = None,
    alpha: float = 0.7,
    query_context: Optional[Dict] = None,
    intent_result=None,
) -> List[Dict]:
    """
    FONCTION GLOBALE HYBRID_SEARCH - CORRECTION POUR RAG_ENGINE.PY

    Cette fonction wrapper permet l'import depuis rag_engine.py:
    from hybrid_retriever import hybrid_search
    """
    if not client:
        raise ValueError("Client Weaviate requis pour hybrid_search")

    # Créer une instance du retriever
    retriever = OptimizedHybridRetriever(client, collection_name)

    # Appeler la méthode de la classe
    return await retriever.hybrid_search(
        query_vector=query_vector,
        query_text=query_text,
        top_k=top_k,
        where_filter=where_filter,
        alpha=alpha,
        query_context=query_context,
        intent_result=intent_result,
    )


def create_hybrid_retriever(
    client, collection_name: str = "InteliaKnowledge"
) -> OptimizedHybridRetriever:
    """Factory pour créer un retriever hybride configuré"""
    return OptimizedHybridRetriever(client, collection_name)


# ============================================================================
# EXPORTS POUR COMPATIBILITÉ
# ============================================================================

__all__ = [
    "OptimizedHybridRetriever",
    "hybrid_search",  # ← EXPORT CRITIQUE AJOUTÉ
    "create_hybrid_retriever",
    "INTELLIGENT_RRF_AVAILABLE",
]
