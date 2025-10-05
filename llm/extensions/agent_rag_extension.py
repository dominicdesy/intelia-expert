# -*- coding: utf-8 -*-
"""
agent_rag_extension.py - Extension Agent RAG pour Intelia Expert
Implémente un Agent RAG avec décomposition de requêtes et synthèse multi-documents
Compatible avec votre architecture existante

VERSION CORRIGÉE: Utilise composition au lieu d'héritage pour éviter import circulaire
"""

import asyncio
import time
import logging
from utils.types import Dict, List, Any, Optional
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from core.base import InitializableMixin

# Import conditionnel pour éviter l'import circulaire
if TYPE_CHECKING:
    from core.rag_engine import InteliaRAGEngine

# Imports sûrs (pas de risque d'import circulaire)
from core.data_models import RAGResult, RAGSource
from processing.intent_processor import IntentProcessor, IntentResult, IntentType

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Types de complexité de requête pour l'agent"""

    SIMPLE = "simple"  # Requête directe, un seul concept
    MULTI_METRIC = "multi_metric"  # Plusieurs métriques demandées
    COMPARATIVE = "comparative"  # Comparaison entre lignées/âges
    CONDITIONAL = "conditional"  # "Si... alors..." ou dépendances
    SEQUENTIAL = "sequential"  # Étapes successives à expliquer
    DIAGNOSTIC = "diagnostic"  # Analyse cause-effet complexe


@dataclass
class SubQuery:
    """Sous-requête décomposée"""

    query: str
    intent_type: IntentType
    priority: int = 1  # 1=haute, 2=moyenne, 3=basse
    dependencies: List[str] = field(
        default_factory=list
    )  # IDs de sous-requêtes prérequises
    context_needed: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Résultat de traitement par agent - compatible avec RAGResult"""

    final_answer: str
    confidence: float
    sub_results: List[RAGResult]
    synthesis_method: str
    processing_time: float
    complexity: QueryComplexity
    decomposition_used: bool
    agent_decisions: List[str] = field(default_factory=list)  # Log des décisions


class QueryDecomposer(InitializableMixin):
    """Décompose les requêtes complexes en sous-requêtes"""

    def __init__(self, intent_processor: IntentProcessor):
        super().__init__()
        self.intent_processor = intent_processor

        # Patterns de complexité basés sur votre domaine avicole
        self.complexity_patterns = {
            QueryComplexity.MULTI_METRIC: [
                r"\b(poids|fcr|eau|aliment)\b.*\b(et|and)\b.*\b(poids|fcr|eau|aliment)\b",
                r"\b(performance|résultat)s?\b.*\b(complet|global|détaillé)\b",
            ],
            QueryComplexity.COMPARATIVE: [
                r"\b(ross|cobb|hubbard)\b.*\b(vs|versus|contre|par rapport)\b",
                r"\b(différence|comparer|comparison)\b.*\b(lignée|souche|breed)\b",
                r"\b(meilleur|optimal|plus)\b.*\b(que|than)\b",
            ],
            QueryComplexity.CONDITIONAL: [
                r"\bsi\b.*\b(alors|donc|therefore)\b",
                r"\b(dans le cas|au cas|if)\b.*\b(what|que faire)\b",
                r"\b(dépend|depends)\b.*\b(de|on)\b",
            ],
            QueryComplexity.DIAGNOSTIC: [
                r"\b(problème|symptôme|maladie)\b.*\b(cause|origine|reason)\b",
                r"\b(pourquoi|why)\b.*\b(mortalité|mortality|performance)\b",
            ],
        }

    def analyze_complexity(
        self, query: str, intent_result: IntentResult
    ) -> QueryComplexity:
        """Analyse la complexité d'une requête"""
        import re

        query_lower = query.lower()

        # Vérification par patterns regex
        for complexity, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return complexity

        # Analyse basée sur le nombre d'entités détectées
        entities = intent_result.detected_entities
        if len(entities) >= 4:  # Beaucoup d'entités = complexe
            return QueryComplexity.MULTI_METRIC

        # Analyse par longueur et mots-clés
        words = query.split()
        if len(words) > 20 and any(
            word in query_lower for word in ["et", "and", "aussi", "également"]
        ):
            return QueryComplexity.MULTI_METRIC

        return QueryComplexity.SIMPLE

    async def decompose_query(
        self, query: str, intent_result: IntentResult, complexity: QueryComplexity
    ) -> List[SubQuery]:
        """Décompose une requête selon sa complexité"""

        sub_queries = []
        entities = intent_result.detected_entities

        if complexity == QueryComplexity.MULTI_METRIC:
            sub_queries = await self._decompose_multi_metric(query, entities)

        elif complexity == QueryComplexity.COMPARATIVE:
            sub_queries = await self._decompose_comparative(query, entities)

        elif complexity == QueryComplexity.CONDITIONAL:
            sub_queries = await self._decompose_conditional(query, entities)

        elif complexity == QueryComplexity.DIAGNOSTIC:
            sub_queries = await self._decompose_diagnostic(query, entities)

        else:  # SIMPLE ou autres cas
            # Requête simple -> une seule sous-requête
            sub_queries = [
                SubQuery(query=query, intent_type=intent_result.intent_type, priority=1)
            ]

        return sub_queries

    async def _decompose_multi_metric(
        self, query: str, entities: Dict
    ) -> List[SubQuery]:
        """Décompose les requêtes multi-métriques"""
        sub_queries = []

        # Identifier les métriques mentionnées
        metrics_mentioned = []
        metric_keywords = {
            "poids": ["poids", "weight", "gramme", "kg"],
            "fcr": ["fcr", "conversion", "efficacité"],
            "eau": ["eau", "water", "consommation"],
            "mortalité": ["mortalité", "mortality", "mort"],
        }

        query_lower = query.lower()
        for metric, keywords in metric_keywords.items():
            if any(kw in query_lower for kw in keywords):
                metrics_mentioned.append(metric)

        # Créer une sous-requête par métrique
        base_context = (
            f"lignée {entities.get('line', '')}" if "line" in entities else ""
        )
        age_context = (
            f"âge {entities.get('age_days', entities.get('age_weeks', ''))} jours"
            if "age_days" in entities or "age_weeks" in entities
            else ""
        )

        for i, metric in enumerate(metrics_mentioned):
            sub_query = SubQuery(
                query=f"Quelle est la valeur optimale de {metric} pour {base_context} {age_context}?",
                intent_type=IntentType.METRIC_QUERY,
                priority=1,
                context_needed={"metric": metric, **entities},
            )
            sub_queries.append(sub_query)

        return sub_queries

    async def _decompose_comparative(
        self, query: str, entities: Dict
    ) -> List[SubQuery]:
        """Décompose les requêtes comparatives"""
        sub_queries = []

        # Extraire les lignées à comparer
        lines_to_compare = []
        line_keywords = ["ross", "cobb", "hubbard"]

        for line_kw in line_keywords:
            if line_kw in query.lower():
                lines_to_compare.append(line_kw)

        # Si pas de lignées spécifiques, utiliser celle détectée vs "standards"
        if not lines_to_compare and "line" in entities:
            lines_to_compare = [entities["line"], "standard industrie"]

        # Créer des requêtes pour chaque lignée
        base_question = query.split("vs")[0].strip() if "vs" in query else query

        for line in lines_to_compare:
            sub_query = SubQuery(
                query=f"{base_question} pour {line}",
                intent_type=IntentType.METRIC_QUERY,
                priority=1,
                context_needed={"comparative_line": line, **entities},
            )
            sub_queries.append(sub_query)

        return sub_queries

    async def _decompose_conditional(
        self, query: str, entities: Dict
    ) -> List[SubQuery]:
        """Décompose les requêtes conditionnelles"""
        # Séparer condition et action
        if "si" in query.lower():
            parts = query.lower().split("si")
            if len(parts) > 1:
                condition = parts[1].split("alors")[0].strip()
                action = (
                    parts[1].split("alors")[1].strip()
                    if "alors" in parts[1]
                    else "que faire?"
                )

                return [
                    SubQuery(
                        query=f"Conditions normales pour {condition}",
                        intent_type=IntentType.METRIC_QUERY,
                        priority=1,
                    ),
                    SubQuery(
                        query=f"Actions recommandées: {action}",
                        intent_type=IntentType.PROTOCOL_QUERY,
                        priority=2,
                        dependencies=["condition_check"],
                    ),
                ]

        # Fallback: traiter comme requête simple
        return [
            SubQuery(query=query, intent_type=IntentType.GENERAL_POULTRY, priority=1)
        ]

    async def _decompose_diagnostic(self, query: str, entities: Dict) -> List[SubQuery]:
        """Décompose les requêtes de diagnostic"""
        sub_queries = []

        # 1. Collecte des symptômes/signes
        sub_queries.append(
            SubQuery(
                query=f"Signes cliniques et symptômes observés: {query}",
                intent_type=IntentType.DIAGNOSIS_TRIAGE,
                priority=1,
            )
        )

        # 2. Causes possibles
        sub_queries.append(
            SubQuery(
                query="Causes possibles des symptômes décrits",
                intent_type=IntentType.DIAGNOSIS_TRIAGE,
                priority=2,
                dependencies=["symptom_analysis"],
            )
        )

        # 3. Actions recommandées
        sub_queries.append(
            SubQuery(
                query="Protocole d'action pour ces symptômes",
                intent_type=IntentType.PROTOCOL_QUERY,
                priority=3,
                dependencies=["cause_analysis"],
            )
        )

        return sub_queries


class MultiDocumentSynthesizer(InitializableMixin):
    """Synthétise les réponses de plusieurs documents"""

    def __init__(self, openai_client):
        super().__init__()
        self.client = openai_client

    async def synthesize_results(
        self,
        original_query: str,
        sub_results: List[RAGResult],
        complexity: QueryComplexity,
    ) -> str:
        """Synthétise plusieurs résultats RAG en une réponse cohérente"""

        if not sub_results:
            return "Aucune information trouvée pour répondre à votre question."

        # Filtrer les résultats valides
        valid_results = [r for r in sub_results if r.answer and r.confidence > 0.3]

        if not valid_results:
            return "Les informations trouvées ne sont pas suffisamment fiables pour répondre à votre question."

        # Stratégie de synthèse selon la complexité
        if complexity == QueryComplexity.MULTI_METRIC:
            return await self._synthesize_multi_metric(original_query, valid_results)
        elif complexity == QueryComplexity.COMPARATIVE:
            return await self._synthesize_comparative(original_query, valid_results)
        elif complexity == QueryComplexity.DIAGNOSTIC:
            return await self._synthesize_diagnostic(original_query, valid_results)
        else:
            return await self._synthesize_general(original_query, valid_results)

    async def _synthesize_multi_metric(
        self, query: str, results: List[RAGResult]
    ) -> str:
        """Synthèse pour requêtes multi-métriques"""

        # Organiser par métrique
        context_by_metric = {}
        for result in results:
            # Extraire la métrique du contexte
            metric = self._extract_metric_from_result(result)
            if metric not in context_by_metric:
                context_by_metric[metric] = []
            context_by_metric[metric].append(result.answer)

        # Construire le prompt de synthèse
        synthesis_prompt = f"""Tu es un expert en aviculture. Synthétise ces informations pour répondre à cette question complexe:

QUESTION: {query}

INFORMATIONS PAR MÉTRIQUE:
"""

        for metric, answers in context_by_metric.items():
            synthesis_prompt += f"\n{metric.upper()}:\n"
            for i, answer in enumerate(answers, 1):
                synthesis_prompt += f"- Source {i}: {answer[:200]}...\n"

        synthesis_prompt += """\nINSTRUCTIONS:
1. Fournis une réponse structurée couvrant toutes les métriques
2. Indique les valeurs cibles et plages normales
3. Mentionne les facteurs d'influence importants
4. Organise par ordre de priorité pratique
5. Maximum 400 mots

RÉPONSE SYNTHÉTISÉE:"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.1,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Erreur synthèse multi-métrique: {e}")
            return self._fallback_concatenation(results)

    async def _synthesize_comparative(
        self, query: str, results: List[RAGResult]
    ) -> str:
        """Synthèse pour requêtes comparatives"""

        synthesis_prompt = f"""Tu es un expert en aviculture. Compare ces informations pour répondre à cette question:

QUESTION: {query}

INFORMATIONS À COMPARER:
"""

        for i, result in enumerate(results, 1):
            synthesis_prompt += (
                f"\nSOURCE {i} (Confiance: {result.confidence:.2f}):\n{result.answer}\n"
            )

        synthesis_prompt += """\nINSTRUCTIONS:
1. Compare point par point les différents éléments
2. Mets en évidence les avantages/inconvénients
3. Fournis une recommandation basée sur les données
4. Structure la réponse en tableau si approprié
5. Maximum 450 mots

COMPARAISON:"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.1,
                max_tokens=650,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Erreur synthèse comparative: {e}")
            return self._fallback_concatenation(results)

    async def _synthesize_diagnostic(self, query: str, results: List[RAGResult]) -> str:
        """Synthèse pour requêtes de diagnostic"""

        synthesis_prompt = f"""Tu es un vétérinaire spécialisé en aviculture. Analyse ces informations pour répondre à cette question diagnostique:

QUESTION: {query}

INFORMATIONS DIAGNOSTIQUES:
"""

        for i, result in enumerate(results, 1):
            synthesis_prompt += f"\nÉLÉMENT {i}:\n{result.answer}\n"

        synthesis_prompt += """\nINSTRUCTIONS:
1. Analyse différentielle structurée
2. Hiérarchise les causes par probabilité
3. Propose un plan d'investigation
4. Recommande des actions immédiates si nécessaire
5. Format: Diagnostic différentiel > Examens complémentaires > Plan d'action

ANALYSE DIAGNOSTIQUE:"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.1,
                max_tokens=700,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Erreur synthèse diagnostic: {e}")
            return self._fallback_concatenation(results)

    async def _synthesize_general(self, query: str, results: List[RAGResult]) -> str:
        """Synthèse générale"""

        # Sélectionner les meilleurs résultats
        sorted_results = sorted(results, key=lambda r: r.confidence, reverse=True)[:3]

        synthesis_prompt = f"""Synthétise ces informations avicoles pour répondre précisément à cette question:

QUESTION: {query}

INFORMATIONS DISPONIBLES:
"""

        for i, result in enumerate(sorted_results, 1):
            synthesis_prompt += (
                f"\nSource {i} (Confiance: {result.confidence:.2f}):\n{result.answer}\n"
            )

        synthesis_prompt += """\nFournis une réponse synthétique, précise et pratique en maximum 300 mots.

RÉPONSE:"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.2,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Erreur synthèse générale: {e}")
            return self._fallback_concatenation(results)

    def _extract_metric_from_result(self, result: RAGResult) -> str:
        """Extrait la métrique principale d'un résultat"""
        answer_lower = result.answer.lower()

        metric_indicators = {
            "poids": ["poids", "weight", "gramme", "kg"],
            "fcr": ["fcr", "conversion", "efficacité"],
            "eau": ["eau", "water", "consommation"],
            "température": ["température", "temp", "°c"],
            "mortalité": ["mortalité", "mortality"],
        }

        for metric, indicators in metric_indicators.items():
            if any(ind in answer_lower for ind in indicators):
                return metric

        return "général"

    def _fallback_concatenation(self, results: List[RAGResult]) -> str:
        """Fallback: concaténation simple des résultats"""
        sorted_results = sorted(results, key=lambda r: r.confidence, reverse=True)

        response_parts = []
        for i, result in enumerate(sorted_results[:3], 1):
            response_parts.append(f"**Point {i}:** {result.answer}")

        return "\n\n".join(response_parts)


class InteliaAgentRAG(InitializableMixin):
    """
    Agent RAG intelligent pour Intelia Expert

    ARCHITECTURE: Utilise composition au lieu d'héritage pour éviter import circulaire
    """

    def __init__(self, rag_engine: Optional["InteliaRAGEngine"] = None):
        """
        Initialise l'agent avec un RAG Engine existant

        Args:
            rag_engine: Instance de InteliaRAGEngine (composition, pas héritage)
        """
        super().__init__()
        self.rag_engine = rag_engine
        self.decomposer = None
        self.synthesizer = None

        # Statistiques agent
        self.agent_stats = {
            "total_agent_queries": 0,
            "complex_queries": 0,
            "simple_queries": 0,
            "avg_sub_queries": 0.0,
            "synthesis_success_rate": 0.0,
        }

    async def initialize(self, rag_engine: Optional["InteliaRAGEngine"] = None):
        """
        Initialisation de l'agent RAG

        Args:
            rag_engine: Instance de InteliaRAGEngine si non fournie au __init__
        """
        if rag_engine:
            self.rag_engine = rag_engine

        if not self.rag_engine:
            raise ValueError("RAG Engine requis pour initialiser l'agent")

        # Vérifier que le RAG engine est initialisé
        if not self.rag_engine.is_initialized:
            await self.rag_engine.initialize()

        # Initialiser les composants agent
        # Accéder à intent_processor via le RAG engine
        if hasattr(self.rag_engine, "weaviate_core") and self.rag_engine.weaviate_core:
            intent_processor = self.rag_engine.weaviate_core.intent_processor
        else:
            raise ValueError("Intent processor non disponible dans RAG engine")

        self.decomposer = QueryDecomposer(intent_processor)

        # Accéder au client OpenAI via le RAG engine
        openai_client = (
            self.rag_engine.core.openai_client
            if hasattr(self.rag_engine, "core")
            else None
        )
        if not openai_client:
            raise ValueError("Client OpenAI non disponible dans RAG engine")

        self.synthesizer = MultiDocumentSynthesizer(openai_client)

        logger.info("Agent RAG Intelia initialisé avec décomposition et synthèse")

        await super().initialize()

    async def process_query_agent(
        self, query: str, language: str = "fr", tenant_id: str = ""
    ) -> AgentResult:
        """Interface agent principale - point d'entrée pour le traitement intelligent"""

        start_time = time.time()
        self.agent_stats["total_agent_queries"] += 1

        try:
            # Vérifier que le RAG engine est disponible
            if not self.rag_engine:
                raise ValueError("RAG Engine non initialisé")

            # 1. Analyse d'intention via le RAG engine
            if (
                hasattr(self.rag_engine, "weaviate_core")
                and self.rag_engine.weaviate_core
            ):
                intent_processor = self.rag_engine.weaviate_core.intent_processor
                intent_result = intent_processor.process_query(query)
            else:
                raise ValueError("Intent processor non disponible")

            # 2. Analyse de complexité
            complexity = self.decomposer.analyze_complexity(query, intent_result)
            agent_decisions = [f"Complexité détectée: {complexity.value}"]

            # 3. Décision: décomposer ou traiter directement
            if complexity == QueryComplexity.SIMPLE:
                self.agent_stats["simple_queries"] += 1
                agent_decisions.append("Traitement direct (requête simple)")

                # Utiliser le RAG engine via generate_response
                rag_result = await self.rag_engine.generate_response(
                    query=query, tenant_id=tenant_id, language=language
                )

                return AgentResult(
                    final_answer=rag_result.answer or "Aucune réponse trouvée",
                    confidence=rag_result.confidence,
                    sub_results=[rag_result],
                    synthesis_method="direct",
                    processing_time=time.time() - start_time,
                    complexity=complexity,
                    decomposition_used=False,
                    agent_decisions=agent_decisions,
                )

            else:
                # Traitement complexe avec décomposition
                self.agent_stats["complex_queries"] += 1
                agent_decisions.append("Décomposition requise")

                # 4. Décomposition en sous-requêtes
                sub_queries = await self.decomposer.decompose_query(
                    query, intent_result, complexity
                )
                agent_decisions.append(f"Décomposé en {len(sub_queries)} sous-requêtes")
                self.agent_stats["avg_sub_queries"] = self._update_avg_sub_queries(
                    len(sub_queries)
                )

                # 5. Traitement parallèle des sous-requêtes
                agent_decisions.append("Traitement parallèle démarré")
                sub_results = await asyncio.gather(
                    *[
                        self._process_sub_query(sub_q, language, tenant_id)
                        for sub_q in sub_queries
                    ],
                    return_exceptions=True,
                )

                # Filtrer les exceptions
                valid_sub_results = [r for r in sub_results if isinstance(r, RAGResult)]
                agent_decisions.append(
                    f"{len(valid_sub_results)}/{len(sub_queries)} sous-requêtes réussies"
                )

                # 6. Synthèse multi-documents
                if valid_sub_results:
                    agent_decisions.append("Synthèse multi-documents")
                    final_answer = await self.synthesizer.synthesize_results(
                        query, valid_sub_results, complexity
                    )

                    # Calcul de confiance globale
                    avg_confidence = sum(r.confidence for r in valid_sub_results) / len(
                        valid_sub_results
                    )
                    synthesis_bonus = 0.1 if len(valid_sub_results) > 1 else 0
                    final_confidence = min(0.95, avg_confidence + synthesis_bonus)

                    self.agent_stats["synthesis_success_rate"] = (
                        self._update_success_rate(True)
                    )

                else:
                    agent_decisions.append("Synthèse échouée - fallback")
                    final_answer = "Je n'ai pas pu trouver suffisamment d'informations fiables pour répondre à cette question complexe."
                    final_confidence = 0.2
                    self.agent_stats["synthesis_success_rate"] = (
                        self._update_success_rate(False)
                    )

                return AgentResult(
                    final_answer=final_answer,
                    confidence=final_confidence,
                    sub_results=valid_sub_results,
                    synthesis_method=f"multi_document_{complexity.value}",
                    processing_time=time.time() - start_time,
                    complexity=complexity,
                    decomposition_used=True,
                    agent_decisions=agent_decisions,
                )

        except Exception as e:
            logger.error(f"Erreur agent RAG: {e}")

            # Fallback gracieux vers RAG standard
            try:
                rag_result = await self.rag_engine.generate_response(
                    query=query, tenant_id=tenant_id, language=language
                )
                return AgentResult(
                    final_answer=rag_result.answer
                    or f"Erreur agent, fallback utilisé: {str(e)}",
                    confidence=max(0.3, rag_result.confidence - 0.2),
                    sub_results=[rag_result],
                    synthesis_method="fallback",
                    processing_time=time.time() - start_time,
                    complexity=QueryComplexity.SIMPLE,
                    decomposition_used=False,
                    agent_decisions=[
                        f"Erreur agent: {str(e)}",
                        "Fallback vers RAG standard",
                    ],
                )
            except Exception as e2:
                logger.error(f"Erreur fallback RAG: {e2}")
                return AgentResult(
                    final_answer=f"Une erreur système est survenue. Erreur principale: {str(e)}",
                    confidence=0.1,
                    sub_results=[],
                    synthesis_method="error",
                    processing_time=time.time() - start_time,
                    complexity=QueryComplexity.SIMPLE,
                    decomposition_used=False,
                    agent_decisions=[f"Erreur système: {str(e)}"],
                )

    async def _process_sub_query(
        self, sub_query: SubQuery, language: str, tenant_id: str
    ) -> RAGResult:
        """Traite une sous-requête individuelle"""
        try:
            # Utiliser le RAG engine pour chaque sous-requête
            result = await self.rag_engine.generate_response(
                query=sub_query.query, tenant_id=tenant_id, language=language
            )

            # Enrichir avec le contexte de la sous-requête
            if result.metadata is None:
                result.metadata = {}
            result.metadata.update(
                {
                    "sub_query_priority": sub_query.priority,
                    "sub_query_context": sub_query.context_needed,
                    "agent_processed": True,
                }
            )

            return result

        except Exception as e:
            logger.error(f"Erreur traitement sous-requête '{sub_query.query}': {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer=f"Erreur traitement: {str(e)}",
                confidence=0.1,
                processing_time=0.0,
                metadata={"sub_query_error": str(e)},
            )

    def _update_avg_sub_queries(self, new_count: int) -> float:
        """Met à jour la moyenne du nombre de sous-requêtes"""
        total_complex = self.agent_stats["complex_queries"]
        if total_complex <= 1:
            return float(new_count)

        current_avg = self.agent_stats["avg_sub_queries"]
        return ((current_avg * (total_complex - 1)) + new_count) / total_complex

    def _update_success_rate(self, success: bool) -> float:
        """Met à jour le taux de succès de synthèse"""
        total_complex = self.agent_stats["complex_queries"]
        if total_complex <= 1:
            return 1.0 if success else 0.0

        current_rate = self.agent_stats["synthesis_success_rate"]
        current_successes = current_rate * (total_complex - 1)
        new_successes = current_successes + (1 if success else 0)

        return new_successes / total_complex

    def get_agent_status(self) -> Dict:
        """Status détaillé de l'agent"""
        base_status = self.rag_engine.get_status() if self.rag_engine else {}

        agent_status = {
            **base_status,
            "agent_enabled": True,
            "decomposer_loaded": self.decomposer is not None,
            "synthesizer_loaded": self.synthesizer is not None,
            "agent_stats": self.agent_stats,
            "agent_features": [
                "query_decomposition",
                "parallel_processing",
                "multi_document_synthesis",
                "complexity_analysis",
                "graceful_fallback",
                "decision_logging",
            ],
            "architecture": "composition_based",  # Pas d'héritage
        }

        return agent_status


# Fonctions utilitaires pour l'intégration avec votre système
async def create_agent_rag_engine(rag_engine: "InteliaRAGEngine") -> InteliaAgentRAG:
    """
    Factory pour créer l'agent RAG

    Args:
        rag_engine: Instance existante de InteliaRAGEngine
    """
    agent = InteliaAgentRAG(rag_engine)
    await agent.initialize()
    return agent


async def process_query_with_agent(
    agent_engine: InteliaAgentRAG, query: str, language: str = "fr", tenant_id: str = ""
) -> AgentResult:
    """Interface compatible pour traitement avec agent"""
    return await agent_engine.process_query_agent(query, language, tenant_id)
