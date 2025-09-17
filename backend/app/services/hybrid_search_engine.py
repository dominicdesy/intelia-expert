# rag/hybrid_search_engine.py
"""
Moteur de recherche hybride combinant PerfStore et RAG vectoriel
Orchestre les requêtes selon l'intention détectée par le ConceptRouter
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Résultat unifié de recherche hybride"""

    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    performance_data: Optional[pd.DataFrame] = None
    contextual_chunks: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.contextual_chunks is None:
            self.contextual_chunks = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SearchContext:
    """Contexte pour la recherche"""

    user_id: Optional[str] = None
    conversation_history: List[Dict] = None
    preferred_language: str = "fr"
    default_filters: Dict[str, Any] = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.default_filters is None:
            self.default_filters = {}


class HybridSearchEngine:
    """
    Moteur de recherche hybride intelligent
    Combine PerfStore (données quantitatives) + RAG (contexte et conseils)
    """

    def __init__(self, perf_store, rag_retriever, concept_router, llm_client):
        self.perf_store = perf_store
        self.rag_retriever = rag_retriever
        self.concept_router = concept_router
        self.llm_client = llm_client

        # Templates de réponse par type de route
        self.response_templates = {
            "perf_store": self._create_performance_response,
            "rag_vector": self._create_contextual_response,
            "hybrid": self._create_hybrid_response,
            "clarification": self._create_clarification_response,
        }

    async def search(
        self, query: str, context: Optional[SearchContext] = None
    ) -> SearchResult:
        """
        Point d'entrée principal pour la recherche hybride

        Args:
            query: Requête utilisateur
            context: Contexte de recherche (historique, filtres, etc.)

        Returns:
            SearchResult unifié avec réponse synthétisée
        """
        try:
            # Étape 1: Analyse de l'intention
            query_intent = self.concept_router.analyze_query(query, context)

            # Étape 2: Recherche selon la route déterminée
            if query_intent.route.value == "perf_store":
                result = await self._search_performance_focused(
                    query, query_intent, context
                )
            elif query_intent.route.value == "rag_vector":
                result = await self._search_contextual_focused(
                    query, query_intent, context
                )
            elif query_intent.route.value == "hybrid":
                result = await self._search_hybrid_combined(
                    query, query_intent, context
                )
            else:  # clarification
                result = await self._handle_clarification(query, query_intent, context)

            # Étape 3: Enrichissement avec métadonnées
            result.metadata.update(
                {
                    "query_intent": query_intent.route.value,
                    "confidence": query_intent.confidence,
                    "detected_concepts": query_intent.detected_concepts,
                    "filters_applied": query_intent.filters,
                    "reasoning": query_intent.reasoning,
                }
            )

            logger.info(
                f"Recherche complétée: {query_intent.route.value}, confiance: {result.confidence:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            return self._create_error_response(str(e))

    async def _search_performance_focused(
        self, query: str, intent, context: Optional[SearchContext]
    ) -> SearchResult:
        """
        Recherche centrée sur les données de performance quantitatives
        """
        from .perf_store import PerformanceQuery

        # Construction de la requête PerfStore
        perf_query = PerformanceQuery(
            species=intent.filters.get("species"),
            line=intent.filters.get("line"),
            sex=intent.filters.get("sex"),
            age_days=intent.filters.get("age_days"),
            age_range=intent.filters.get("age_range"),
            metrics=intent.filters.get("metrics"),
        )

        # Lookup dans le PerfStore
        perf_result = self.perf_store.query_performance(perf_query)

        # Recherche contextuelle légère pour enrichir la réponse
        rag_context = await self.rag_retriever.retrieve(
            query, filters=intent.filters, limit=3
        )

        # Synthèse de la réponse
        response = await self.response_templates["perf_store"](
            query, perf_result, rag_context, intent
        )

        return SearchResult(
            answer=response["answer"],
            confidence=response["confidence"],
            sources=response["sources"],
            performance_data=perf_result.data,
            contextual_chunks=rag_context,
            metadata={"route": "perf_store", "perf_metadata": perf_result.metadata},
        )

    async def _search_contextual_focused(
        self, query: str, intent, context: Optional[SearchContext]
    ) -> SearchResult:
        """
        Recherche centrée sur le contexte et les conseils (RAG vectoriel)
        """
        # Recherche vectorielle principale
        rag_results = await self.rag_retriever.retrieve(
            query, filters=intent.filters, limit=10
        )

        # Enrichissement optionnel avec données de performance si pertinent
        perf_enrichment = None
        if intent.detected_concepts.get("performance", 0) > 0.3:
            perf_enrichment = await self._get_related_performance_data(intent.filters)

        # Synthèse de la réponse
        response = await self.response_templates["rag_vector"](
            query, rag_results, perf_enrichment, intent
        )

        return SearchResult(
            answer=response["answer"],
            confidence=response["confidence"],
            sources=response["sources"],
            performance_data=perf_enrichment,
            contextual_chunks=rag_results,
            metadata={"route": "rag_vector"},
        )

    async def _search_hybrid_combined(
        self, query: str, intent, context: Optional[SearchContext]
    ) -> SearchResult:
        """
        Recherche hybride combinant PerfStore et RAG vectoriel
        """
        # Recherche simultanée dans les deux systèmes
        perf_task = self._search_performance_focused(query, intent, context)
        rag_task = self._search_contextual_focused(query, intent, context)

        perf_result = await perf_task
        rag_result = await rag_task

        # Fusion intelligente des résultats
        response = await self.response_templates["hybrid"](
            query, perf_result, rag_result, intent
        )

        # Combinaison des sources
        combined_sources = []
        combined_sources.extend(perf_result.sources)
        combined_sources.extend(rag_result.sources)

        return SearchResult(
            answer=response["answer"],
            confidence=response["confidence"],
            sources=combined_sources,
            performance_data=perf_result.performance_data,
            contextual_chunks=rag_result.contextual_chunks,
            metadata={
                "route": "hybrid",
                "fusion_strategy": response.get("fusion_strategy"),
            },
        )

    async def _handle_clarification(
        self, query: str, intent, context: Optional[SearchContext]
    ) -> SearchResult:
        """
        Gestion des demandes de clarification
        """
        response = await self.response_templates["clarification"](
            query, intent, context
        )

        return SearchResult(
            answer=response["answer"],
            confidence=0.9,  # Haute confiance pour les clarifications
            sources=[],
            metadata={
                "route": "clarification",
                "clarification_type": response.get("type"),
            },
        )

    async def _create_performance_response(
        self, query: str, perf_result, rag_context: List[Dict], intent
    ) -> Dict[str, Any]:
        """
        Crée une réponse centrée sur les données de performance
        """
        if perf_result.data.empty:
            return {
                "answer": f"Aucune donnée de performance trouvée pour ces critères: {intent.filters}. "
                f"Vérifiez l'espèce, la lignée ou l'âge spécifiés.",
                "confidence": 0.3,
                "sources": [],
            }

        # Formatage des données de performance
        data_summary = self._format_performance_data(perf_result.data, intent.filters)

        # Enrichissement contextuel si disponible
        context_info = ""
        if rag_context:
            context_info = self._extract_contextual_insights(
                rag_context, intent.filters
            )

        # Construction de la réponse avec prompt structuré
        response_prompt = f"""
Basé sur les données de performance suivantes, répondez à la question: "{query}"

DONNÉES DE PERFORMANCE:
{data_summary}

CONTEXTE ADDITIONNEL:
{context_info}

Fournissez une réponse précise avec:
1. Les données chiffrées pertinentes
2. L'interprétation de ces données
3. Les recommandations si appropriées
4. Les sources des données

Réponse en français, format conversationnel.
"""

        # Génération via LLM
        response_text = await self._call_llm_for_response(response_prompt)

        return {
            "answer": response_text,
            "confidence": min(0.8 + perf_result.confidence * 0.2, 1.0),
            "sources": self._format_sources(perf_result.sources, rag_context),
        }

    async def _create_contextual_response(
        self, query: str, rag_results: List[Dict], perf_enrichment, intent
    ) -> Dict[str, Any]:
        """
        Crée une réponse centrée sur le contexte et les conseils
        """
        if not rag_results:
            return {
                "answer": "Aucune information contextuelle trouvée pour cette question. "
                "Pouvez-vous reformuler ou être plus spécifique ?",
                "confidence": 0.2,
                "sources": [],
            }

        # Extraction du contexte pertinent
        context_chunks = self._select_best_chunks(rag_results, intent)

        # Enrichissement avec données de performance si disponibles
        perf_context = ""
        if perf_enrichment is not None and not perf_enrichment.empty:
            perf_context = f"Données de référence: {self._format_performance_data(perf_enrichment, intent.filters)}"

        # Construction de la réponse
        response_prompt = f"""
Répondez à la question: "{query}"

CONTEXTE PERTINENT:
{self._format_chunks_for_llm(context_chunks)}

{perf_context}

Fournissez une réponse informative et pratique en français.
"""

        response_text = await self._call_llm_for_response(response_prompt)

        return {
            "answer": response_text,
            "confidence": self._calculate_rag_confidence(rag_results, intent),
            "sources": self._extract_sources_from_chunks(context_chunks),
        }

    async def _create_hybrid_response(
        self, query: str, perf_result: SearchResult, rag_result: SearchResult, intent
    ) -> Dict[str, Any]:
        """
        Fusionne les résultats PerfStore et RAG en une réponse cohérente
        """
        # Stratégie de fusion selon le type de question
        if intent.detected_concepts.get("comparison", 0) > 0.5:
            fusion_strategy = "comparison_focused"
            response_text = await self._create_comparison_response(
                query, perf_result, rag_result, intent
            )
        else:
            fusion_strategy = "context_enriched"
            response_text = await self._create_enriched_response(
                query, perf_result, rag_result, intent
            )

        # Confiance combinée (pondérée selon la stratégie)
        combined_confidence = perf_result.confidence * 0.6 + rag_result.confidence * 0.4

        return {
            "answer": response_text,
            "confidence": combined_confidence,
            "sources": perf_result.sources + rag_result.sources,
            "fusion_strategy": fusion_strategy,
        }

    async def _create_clarification_response(
        self, query: str, intent, context: Optional[SearchContext]
    ) -> Dict[str, Any]:
        """
        Crée une réponse de clarification intelligente
        """
        clarification_text = intent.clarification_needed

        # Ajout de suggestions contextuelles
        available_data = self.perf_store.get_available_data_summary()

        suggestions = []
        if available_data["species_available"]:
            suggestions.append(
                f"Espèces disponibles: {', '.join(available_data['species_available'])}"
            )
        if available_data["lines_available"]:
            suggestions.append(
                f"Lignées disponibles: {', '.join(available_data['lines_available'][:5])}"
            )

        full_response = clarification_text
        if suggestions:
            full_response += "\n\nInformations disponibles:\n" + "\n".join(suggestions)

        return {"answer": full_response, "type": "missing_context"}

    async def _get_related_performance_data(
        self, filters: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """
        Récupère des données de performance liées pour enrichir une réponse RAG
        """
        try:
            from .perf_store import PerformanceQuery

            perf_query = PerformanceQuery(
                species=filters.get("species"),
                line=filters.get("line"),
                sex=filters.get("sex"),
            )

            result = self.perf_store.query_performance(perf_query)
            return result.data if not result.data.empty else None

        except Exception as e:
            logger.debug(f"Erreur récupération données performance: {e}")
            return None

    def _format_performance_data(
        self, df: pd.DataFrame, filters: Dict[str, Any]
    ) -> str:
        """
        Formate les données de performance pour inclusion dans les prompts
        """
        if df.empty:
            return "Aucune donnée disponible"

        # Sélection des colonnes les plus pertinentes
        key_columns = ["age_days", "weight_g", "daily_gain_g", "fcr", "mortality"]
        available_columns = [col for col in key_columns if col in df.columns]

        if available_columns:
            formatted_data = df[available_columns].head(10).to_string(index=False)
            return f"Tableau des données:\n{formatted_data}"
        else:
            return (
                f"Données disponibles: {len(df)} entrées, colonnes: {list(df.columns)}"
            )

    def _format_chunks_for_llm(self, chunks: List[Dict]) -> str:
        """
        Formate les chunks RAG pour inclusion dans les prompts
        """
        formatted_chunks = []
        for i, chunk in enumerate(chunks[:5]):  # Limite à 5 chunks
            text = chunk.get("text", "")[:500]  # Limite la taille
            source = chunk.get("metadata", {}).get("source", "Source inconnue")
            formatted_chunks.append(f"Extrait {i+1} ({source}):\n{text}")

        return "\n\n".join(formatted_chunks)

    async def _call_llm_for_response(self, prompt: str) -> str:
        """
        Appel générique au LLM pour la génération de réponse
        """
        try:
            # TODO: Adapter selon votre client LLM
            logger.warning("LLM call not implemented for response generation")
            return "Réponse générée automatiquement (LLM non configuré)"
        except Exception as e:
            logger.error(f"Erreur génération réponse LLM: {e}")
            return "Erreur lors de la génération de la réponse."

    def _create_error_response(self, error_message: str) -> SearchResult:
        """
        Crée une réponse d'erreur standardisée
        """
        return SearchResult(
            answer=f"Une erreur s'est produite lors de la recherche: {error_message}",
            confidence=0.0,
            sources=[],
            metadata={"error": True, "error_message": error_message},
        )


# Factory function
def create_hybrid_search_engine(perf_store, rag_retriever, llm_client):
    """
    Factory pour créer un moteur de recherche hybride configuré
    """
    from .concept_router import create_concept_router

    concept_router = create_concept_router()
    return HybridSearchEngine(perf_store, rag_retriever, concept_router, llm_client)
