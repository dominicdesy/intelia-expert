# -*- coding: utf-8 -*-
"""
retriever_adaptive.py - Recherche adaptative avec stratégies intelligentes
"""

import logging
import time
from typing import Dict, List
from core.data_models import Document

logger = logging.getLogger(__name__)


class AdaptiveMixin:
    """Mixin contenant les méthodes de recherche adaptative"""

    async def adaptive_search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 15,
        intent_result=None,
        context: Dict = None,
        alpha: float = None,
        where_filter: Dict = None,
        **kwargs,
    ) -> List[Document]:
        """Recherche adaptative qui ajuste automatiquement les paramètres selon le contexte"""
        start_time = time.time()

        # Assurer la détection des dimensions
        await self._ensure_dimension_detected()

        # Analyser le contexte pour adapter la stratégie
        search_strategy = self._analyze_search_context(
            query_text, intent_result, context
        )

        try:
            # Ajuster les paramètres selon la stratégie
            adjusted_params = self._adjust_search_parameters(search_strategy, top_k)

            # Construire le filtre where si des entités sont détectées
            where_filter = None
            if intent_result and hasattr(intent_result, "detected_entities"):
                from utils.utilities import build_where_filter

                where_filter = build_where_filter(intent_result)

            # Exécuter la recherche hybride avec paramètres adaptés
            documents = await self.hybrid_search(
                query_vector=query_vector,
                query_text=query_text,
                top_k=adjusted_params["top_k"],
                where_filter=where_filter,
                alpha=adjusted_params["alpha"],
                intent_result=intent_result,
            )

            # Post-traitement adaptatif
            processed_docs = self._post_process_results(documents, search_strategy)

            # Métriques
            processing_time = time.time() - start_time
            self.last_query_analytics = {
                "strategy_used": search_strategy["name"],
                "results_count": len(processed_docs),
                "processing_time": processing_time,
                "alpha_used": adjusted_params["alpha"],
                "top_k_used": adjusted_params["top_k"],
            }

            logger.info(
                f"Adaptive search completed: {search_strategy['name']} strategy, {len(processed_docs)} results in {processing_time:.3f}s"
            )

            return processed_docs

        except Exception as e:
            logger.error(f"Erreur recherche adaptative: {e}")
            # Fallback vers recherche hybride standard
            return await self.hybrid_search(
                query_vector, query_text, top_k, intent_result=intent_result
            )

    def _analyze_search_context(
        self, query_text: str, intent_result=None, context: Dict = None
    ) -> Dict:
        """Analyse le contexte pour déterminer la stratégie de recherche optimale"""
        query_lower = query_text.lower()

        # Stratégie par défaut
        strategy = {
            "name": "balanced",
            "description": "Recherche équilibrée vectoriel/BM25",
            "alpha_base": 0.7,
            "top_k_multiplier": 1.0,
            "diversity_focus": False,
            "entity_boost": False,
        }

        # Requêtes techniques précises -> BM25 favorisé
        if any(
            term in query_lower
            for term in ["fcr", "poids", "température", "mortalité", "consommation"]
        ):
            strategy.update(
                {
                    "name": "factual",
                    "description": "Recherche factuelle précise",
                    "alpha_base": 0.3,
                    "top_k_multiplier": 0.8,
                    "entity_boost": True,
                }
            )

        # Requêtes de diagnostic -> recherche diversifiée
        elif any(
            term in query_lower
            for term in ["symptôme", "problème", "maladie", "diagnostic"]
        ):
            strategy.update(
                {
                    "name": "diagnostic",
                    "description": "Recherche diagnostique diversifiée",
                    "alpha_base": 0.6,
                    "top_k_multiplier": 1.3,
                    "diversity_focus": True,
                }
            )

        # Requêtes conceptuelles -> vectoriel favorisé
        elif any(
            term in query_lower
            for term in ["comment", "pourquoi", "expliquer", "optimiser"]
        ):
            strategy.update(
                {
                    "name": "conceptual",
                    "description": "Recherche conceptuelle sémantique",
                    "alpha_base": 0.8,
                    "top_k_multiplier": 1.2,
                    "diversity_focus": True,
                }
            )

        # Boost si entités spécifiques détectées
        if intent_result and hasattr(intent_result, "detected_entities"):
            entities = intent_result.detected_entities
            if any(entity in entities for entity in ["line", "species", "age_days"]):
                strategy["entity_boost"] = True
                strategy["alpha_base"] *= 0.9

        return strategy

    def _adjust_search_parameters(self, strategy: Dict, base_top_k: int) -> Dict:
        """Ajuste les paramètres de recherche selon la stratégie"""
        return {
            "alpha": strategy["alpha_base"],
            "top_k": max(5, int(base_top_k * strategy["top_k_multiplier"])),
            "diversity_threshold": 0.8 if strategy["diversity_focus"] else 0.6,
        }

    def _post_process_results(
        self, documents: List[Document], strategy: Dict
    ) -> List[Document]:
        """Post-traitement des résultats selon la stratégie"""
        if not documents:
            return documents

        processed_docs = documents.copy()

        # Diversification si requise
        if strategy.get("diversity_focus", False):
            processed_docs = self._ensure_result_diversity(processed_docs)

        # Boost des documents avec entités si requis
        if strategy.get("entity_boost", False):
            processed_docs = self._boost_entity_documents(processed_docs)

        return processed_docs

    def _ensure_result_diversity(self, documents: List[Document]) -> List[Document]:
        """Assure la diversité des résultats"""
        if len(documents) <= 3:
            return documents

        diverse_docs = [documents[0]]
        diversity_threshold = 0.7

        for doc in documents[1:]:
            is_diverse = True
            doc_content = doc.content.lower()

            for selected_doc in diverse_docs:
                selected_content = selected_doc.content.lower()
                doc_words = set(doc_content.split())
                selected_words = set(selected_content.split())

                if doc_words and selected_words:
                    similarity = len(doc_words & selected_words) / len(
                        doc_words | selected_words
                    )
                    if similarity > diversity_threshold:
                        is_diverse = False
                        break

            if is_diverse:
                diverse_docs.append(doc)

        return diverse_docs

    def _boost_entity_documents(self, documents: List[Document]) -> List[Document]:
        """Boost les documents contenant des entités spécifiques"""
        for doc in documents:
            metadata = doc.metadata or {}
            entity_count = sum(
                1
                for key in ["geneticLine", "species", "phase", "age_band"]
                if metadata.get(key)
            )

            if entity_count > 0:
                doc.score = min(1.0, doc.score * (1.0 + entity_count * 0.1))

        # Re-trier par score
        documents.sort(key=lambda x: x.score, reverse=True)
        return documents
