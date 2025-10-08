# -*- coding: utf-8 -*-
"""
rag_postgresql_router.py - Routeur intelligent pour types de requêtes
Version 3.0 - Approche hybride avec ContextManager pour multi-turn
"""

import logging
from utils.types import Optional, Dict, Any
from .models import QueryType

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Routeur intelligent pour déterminer le type de requête

    Architecture hybride v3.0:
    - Layer 0 (preprocessing): ContextManager pour multi-turn resolution
    - Layer 1 (rapide): Matching de mots-clés statiques (< 5ms)
    - Layer 2 (fallback): Classification LLM pour cas incertains (~150ms)

    Couverture estimée:
    - 96-97% des requêtes résolues par Layer 0+1
    - 3-4% des requêtes passent au Layer 2 LLM fallback
    """

    def __init__(self, use_context_manager: bool = True):
        # Configuration
        self.confidence_threshold = 2  # Si max_score < 2 → LLM fallback
        self.llm_router = None  # Lazy initialization
        self.use_context_manager = use_context_manager
        self.context_manager = None  # Lazy initialization

        # LAYER 1: Keywords statiques enrichis (22 → 65 mots-clés)
        self.metric_keywords = {
            # === MÉTRIQUES DIRECTES ===
            "performance",
            "metrics",
            "donnees",
            "chiffres",
            "resultats",
            "weight",
            "poids",
            "egg",
            "oeuf",
            "production",
            "feed",
            "alimentation",
            "mortality",
            "mortalite",
            "growth",
            "croissance",
            "fcr",
            "icg",
            "conversion",
            "gain",
            "consommation",
            "consumption",

            # === BREEDS (PostgreSQL a les données) ===
            "ross",
            "cobb",
            "hubbard",
            "aviagen",
            "lohmann",
            "hy-line",
            "isa",

            # === INDICATEURS DE QUESTION MÉTRIQUE ===
            "quel",
            "quelle",
            "quels",
            "quelles",
            "combien",
            "how much",
            "how many",
            "what is",
            "target",
            "cible",
            "objectif",
            "standard",
            "reference",
            "norme",

            # === TEMPOREL (souvent lié aux métriques) ===
            "jour",
            "jours",
            "day",
            "days",
            "semaine",
            "week",
            "age",
            "âge",
            "stade",
            "phase",

            # === SEXE (métriques différenciées) ===
            "male",
            "mâle",
            "males",
            "mâles",
            "femelle",
            "female",
            "femelles",
            "females",
            "mixte",
            "mixed",

            # === TYPES DE QUESTIONS MÉTRIQUES ===
            "courbe",
            "evolution",
            "graphique",
            "tendance",
            "comparer",
            "comparaison",
            "comparison",
            "vs",
            "versus",
            "différence",
            "difference",
            "ecart",
            "gap",
        }

        self.knowledge_keywords = {
            # === QUESTIONS EXPLICATIVES ===
            "comment",
            "how",
            "pourquoi",
            "why",
            "qu'est-ce",
            "qu est-ce",
            "quest-ce",
            "what is",
            "expliquer",
            "explain",
            "definir",
            "define",
            "c'est quoi",
            "cest quoi",

            # === SANTÉ & PATHOLOGIES ===
            "maladie",
            "disease",
            "traitement",
            "treatment",
            "traiter",  # Augmented score
            "treat",
            "prevention",
            "prévention",  # Augmented score
            "prevenir",
            "prevent",
            "biosecurite",
            "biosecurity",
            "symptome",
            "symptom",
            "diagnostic",
            "vaccination",
            "vaccin",
            "vaccine",
            "protocole",
            "protocol",

            # === MALADIES COMMUNES (ajoutées aussi aux KNOWLEDGE keywords) ===
            "newcastle",
            "coccidiose",
            "coccidiosis",
            "gumboro",
            "marek",
            "bronchite",
            "bronchitis",
            "aviaire",
            "avian",
            "poulet",  # Ajouté pour contexte pathologie
            "chair",   # "poulet de chair" contexte pathologie

            # === PROBLÈMES & CAUSES ===
            "probleme",
            "problem",
            "cause",
            "raison",
            "reason",
        }

    def route_query(
        self, query: str, intent_result: Optional[Dict[str, Any]] = None
    ) -> QueryType:
        """
        Détermine le type de requête avec approche hybride

        Layer 0 (preprocessing): Context resolution pour multi-turn
        Layer 1 (rapide): Keywords matching
        Layer 2 (fallback): LLM classification si confiance faible

        Args:
            query: Question de l'utilisateur
            intent_result: Résultat de classification d'intention (optionnel)

        Returns:
            QueryType: METRICS, KNOWLEDGE ou HYBRID
        """
        # Check for empty query - safe fallback
        if not query or not query.strip():
            logger.warning("Empty query received, returning HYBRID as safe fallback")
            return QueryType.HYBRID

        # IMPORTANT: Detect question/health words in ORIGINAL query BEFORE expansion
        original_query_lower = query.lower()
        question_words = [
            "comment", "qu'est-ce", "qu est-ce", "quest-ce", "c'est quoi", "cest quoi",
            "pourquoi", "why", "how", "what is", "expliquer", "explain"
        ]
        health_keywords = ["traiter", "prévention", "prevenir", "prevent"]
        has_question_word = any(word in original_query_lower for word in question_words)
        has_health_keyword = any(word in original_query_lower for word in health_keywords)

        # LAYER 0: Context resolution (multi-turn)
        if self.use_context_manager:
            if self.context_manager is None:
                try:
                    from processing.context_manager import get_context_manager
                    self.context_manager = get_context_manager()
                    logger.debug("ContextManager initialized")
                except Exception as e:
                    logger.warning(f"Could not init ContextManager: {e}")
                    self.use_context_manager = False

            if self.context_manager:
                # Expand query if coreference detected
                expanded_query = self.context_manager.expand_query(query)
                if expanded_query != query:
                    logger.info(f"Query expanded: '{query}' → '{expanded_query}'")
                    query = expanded_query

                # Update context for next queries
                self.context_manager.update_context(query, intent_result)

        query_lower = query.lower()

        # LAYER 1: Keywords matching
        metric_score = sum(
            1 for keyword in self.metric_keywords if keyword in query_lower
        )
        knowledge_score = sum(
            1 for keyword in self.knowledge_keywords if keyword in query_lower
        )

        # Apply boosts from ORIGINAL query (detected earlier)
        if has_question_word:
            knowledge_score += 3  # Very strong boost for question words
            logger.debug("Question word detected in original query → knowledge_score boosted +3")

        if has_health_keyword:
            knowledge_score += 2  # Boost for health/treatment keywords
            logger.debug("Health keyword detected in original query → knowledge_score boosted +2")

        max_score = max(metric_score, knowledge_score)

        # Logging détaillé pour analyse
        logger.debug(
            f"🔀 ROUTING: '{query[:50]}...' → "
            f"metric={metric_score}, knowledge={knowledge_score}"
        )

        # Décision avec confiance
        if metric_score > knowledge_score + 1:
            logger.info(
                f"✅ METRICS (confident: {metric_score} vs {knowledge_score})"
            )
            return QueryType.METRICS

        elif knowledge_score > metric_score + 1:
            logger.info(
                f"✅ KNOWLEDGE (confident: {knowledge_score} vs {metric_score})"
            )
            return QueryType.KNOWLEDGE

        elif max_score >= self.confidence_threshold:
            # Confiance modérée → HYBRID (recherche dans les 2 sources)
            logger.info(
                f"⚠️ HYBRID (moderate confidence: {metric_score}/{knowledge_score})"
            )
            return QueryType.HYBRID

        else:
            # LAYER 2: Confiance faible → LLM fallback
            logger.warning(
                f"❓ LOW CONFIDENCE ({metric_score}/{knowledge_score}) "
                f"→ LLM Router fallback"
            )
            return self._llm_route_fallback(query, intent_result)

    def _llm_route_fallback(
        self, query: str, intent_result: Optional[Dict[str, Any]] = None
    ) -> QueryType:
        """
        Fallback LLM pour questions ambiguës (rarement appelé ~5%)

        Utilise GPT-4o-mini pour classification sémantique quand
        les keywords ne donnent pas assez de confiance

        Args:
            query: Question de l'utilisateur
            intent_result: Contexte additionnel (optionnel)

        Returns:
            QueryType: METRICS, KNOWLEDGE ou HYBRID (safe fallback)
        """
        # Lazy initialization du LLM router
        if self.llm_router is None:
            try:
                from generation.llm_router import get_llm_router

                self.llm_router = get_llm_router()
                logger.debug("✅ LLM Router initialized for fallback")
            except Exception as e:
                logger.error(f"❌ Failed to init LLM Router: {e}")
                return QueryType.HYBRID  # Safe fallback

        # Classification sémantique via LLM
        prompt = f"""Classify this poultry farming question into ONE category:

Question: "{query}"

Categories:
- METRICS: Questions about numbers, performance data, targets (weight, FCR, gain, production, mortality, age, breed comparisons with numbers)
- KNOWLEDGE: Questions about concepts, diseases, treatments, procedures, explanations, "how-to", "why", "what is"
- HYBRID: Questions mixing both aspects

Answer with ONLY ONE WORD: METRICS or KNOWLEDGE or HYBRID"""

        try:
            response = self.llm_router.generate(
                provider="gpt-4o-mini",  # Rapide et économique
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )

            result = response.strip().upper()
            logger.info(f"🤖 LLM Router fallback → {result}")

            if "METRICS" in result:
                return QueryType.METRICS
            elif "KNOWLEDGE" in result:
                return QueryType.KNOWLEDGE
            else:
                return QueryType.HYBRID

        except Exception as e:
            logger.error(f"❌ LLM Router fallback failed: {e}")
            return QueryType.HYBRID  # Safe fallback

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le routing (pour monitoring)

        Returns:
            Dict avec nombre de mots-clés et configuration
        """
        return {
            "metric_keywords_count": len(self.metric_keywords),
            "knowledge_keywords_count": len(self.knowledge_keywords),
            "confidence_threshold": self.confidence_threshold,
            "llm_fallback_enabled": self.llm_router is not None,
            "version": "2.0 (hybrid)",
        }
