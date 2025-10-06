# -*- coding: utf-8 -*-
"""
llm_ensemble.py - Multi-LLM Ensemble with Intelligent Arbitrage

Queries 3 LLMs in parallel (Anthropic Claude, OpenAI GPT-4, DeepSeek)
and selects/fuses the best response using an intelligent judge.

QUALITY OPTIMIZATION: Best-of-3 consensus for high-stakes queries
- Parallel generation from all 3 providers
- Quality scoring via judge LLM (factuality, completeness, coherence)
- Automatic selection of best response OR fusion of multiple responses

Cost: ~3x single LLM (but only for critical queries where quality matters)
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class EnsembleMode(Enum):
    """Ensemble operating modes"""

    BEST_OF_N = "best_of_n"  # Select single best response
    FUSION = "fusion"  # Merge best parts from all responses
    VOTING = "voting"  # Majority vote on key facts


class ResponseQuality:
    """Quality assessment for a single response"""

    def __init__(
        self,
        provider: str,
        response: str,
        factual_score: float = 0.0,
        completeness_score: float = 0.0,
        coherence_score: float = 0.0,
        specificity_score: float = 0.0,
    ):
        self.provider = provider
        self.response = response
        self.factual_score = factual_score
        self.completeness_score = completeness_score
        self.coherence_score = coherence_score
        self.specificity_score = specificity_score

    @property
    def overall_score(self) -> float:
        """Weighted average of all quality dimensions"""
        return (
            self.factual_score * 0.4
            + self.completeness_score * 0.3
            + self.coherence_score * 0.2
            + self.specificity_score * 0.1
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "factual_score": self.factual_score,
            "completeness_score": self.completeness_score,
            "coherence_score": self.coherence_score,
            "specificity_score": self.specificity_score,
            "overall_score": self.overall_score,
        }


class LLMEnsemble:
    """
    Multi-LLM Ensemble for high-quality response generation

    Usage:
        ensemble = LLMEnsemble(mode=EnsembleMode.BEST_OF_N)

        result = await ensemble.generate_ensemble_response(
            query="Quel poids pour Ross 308 à 35 jours ?",
            context_docs=documents,
            language="fr"
        )

        # result = {
        #     "final_answer": "La meilleure réponse sélectionnée",
        #     "provider": "claude",
        #     "confidence": 0.95,
        #     "all_responses": [...],
        #     "quality_scores": [...]
        # }
    """

    def __init__(
        self,
        mode: EnsembleMode = EnsembleMode.BEST_OF_N,
        judge_model: str = "gpt-4o-mini",
        enable_ensemble: bool = None,
    ):
        """
        Initialize LLM ensemble

        Args:
            mode: Ensemble mode (best_of_n, fusion, voting)
            judge_model: Model to use for quality judging (default: gpt-4o-mini for cost)
            enable_ensemble: Enable/disable ensemble (reads from env if None)
        """
        self.mode = mode
        self.judge_model = judge_model

        # Read configuration from environment
        if enable_ensemble is None:
            enable_ensemble = (
                os.getenv("ENABLE_LLM_ENSEMBLE", "false").lower() == "true"
            )
        self.enabled = enable_ensemble

        # Initialize clients for all 3 providers
        self._init_clients()

        # Cost tracking
        self.usage_stats = {
            "ensemble_queries": 0,
            "total_llm_calls": 0,
            "total_cost": 0.0,
        }

        logger.info(
            f"✅ LLM Ensemble initialized (mode={mode.value}, enabled={self.enabled}, judge={judge_model})"
        )

    def _init_clients(self):
        """Initialize all LLM clients"""

        # OpenAI (GPT-4o)
        openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = (
            AsyncOpenAI(api_key=openai_key) if openai_key else None
        )

        # Anthropic (Claude 3.5 Sonnet)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = (
            AsyncAnthropic(api_key=anthropic_key) if anthropic_key else None
        )

        # DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_client = None
        if deepseek_key:
            self.deepseek_client = AsyncOpenAI(
                api_key=deepseek_key, base_url="https://api.deepseek.com/v1"
            )

        # Count available providers
        available = sum(
            [
                self.openai_client is not None,
                self.claude_client is not None,
                self.deepseek_client is not None,
            ]
        )
        logger.info(f"📊 {available}/3 LLM providers available for ensemble")

        if available < 2:
            logger.warning(
                f"⚠️ Only {available} providers available - ensemble quality may be limited"
            )

    async def generate_ensemble_response(
        self,
        query: str,
        context_docs: List[Dict],
        language: str = "fr",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate response using multi-LLM ensemble

        Args:
            query: User query
            context_docs: Retrieved context documents
            language: Response language
            system_prompt: Optional system prompt override

        Returns:
            {
                "final_answer": str,
                "provider": str,  # Which provider's response was selected
                "confidence": float,
                "all_responses": List[Dict],
                "quality_scores": List[Dict],
                "execution_time_ms": float
            }
        """
        import time

        start_time = time.time()

        # Check if ensemble is enabled
        if not self.enabled:
            logger.debug("🔀 Ensemble disabled, falling back to single LLM")
            return await self._fallback_single_llm(
                query, context_docs, language, system_prompt
            )

        # Step 1: Generate responses from all providers in parallel
        logger.info(f"🔀 Ensemble query started: {query[:50]}...")
        responses = await self._generate_parallel_responses(
            query, context_docs, language, system_prompt
        )

        if len(responses) == 0:
            logger.error("❌ No responses generated from any provider")
            return {
                "final_answer": "Désolé, aucune réponse n'a pu être générée.",
                "provider": "none",
                "confidence": 0.0,
                "all_responses": [],
                "quality_scores": [],
                "execution_time_ms": (time.time() - start_time) * 1000,
            }

        # Step 2: Evaluate quality of each response
        quality_assessments = await self._evaluate_responses(
            query, context_docs, responses, language
        )

        # Step 3: Select or fuse based on mode
        if self.mode == EnsembleMode.BEST_OF_N:
            final_result = self._select_best_response(responses, quality_assessments)
        elif self.mode == EnsembleMode.FUSION:
            final_result = await self._fuse_responses(
                query, responses, quality_assessments, language
            )
        elif self.mode == EnsembleMode.VOTING:
            final_result = await self._vote_on_facts(
                query, responses, quality_assessments, language
            )
        else:
            final_result = self._select_best_response(responses, quality_assessments)

        # Add metadata
        final_result["all_responses"] = [
            {"provider": r["provider"], "text": r["text"]} for r in responses
        ]
        final_result["quality_scores"] = [q.to_dict() for q in quality_assessments]
        final_result["execution_time_ms"] = (time.time() - start_time) * 1000

        # Update stats
        self.usage_stats["ensemble_queries"] += 1
        self.usage_stats["total_llm_calls"] += len(responses) + 1  # +1 for judge

        logger.info(
            f"✅ Ensemble complete: {final_result['provider']} selected "
            f"(confidence={final_result['confidence']:.2f}, "
            f"time={final_result['execution_time_ms']:.0f}ms)"
        )

        return final_result

    async def _generate_parallel_responses(
        self,
        query: str,
        context_docs: List[Dict],
        language: str,
        system_prompt: Optional[str],
    ) -> List[Dict[str, str]]:
        """
        Generate responses from all providers in parallel

        Returns:
            [
                {"provider": "claude", "text": "..."},
                {"provider": "gpt4o", "text": "..."},
                {"provider": "deepseek", "text": "..."}
            ]
        """
        # Build user message
        context_text = self._format_context(context_docs)
        user_message = f"""Contexte:
{context_text}

Question: {query}

Réponds en {language}."""

        # Create tasks for all providers
        tasks = []

        if self.claude_client:
            tasks.append(
                self._generate_claude_response(query, user_message, system_prompt)
            )

        if self.openai_client:
            tasks.append(
                self._generate_openai_response(
                    "gpt4o", "gpt-4o", query, user_message, system_prompt
                )
            )

        if self.deepseek_client:
            tasks.append(
                self._generate_deepseek_response(query, user_message, system_prompt)
            )

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors
        responses = []
        for result in results:
            if isinstance(result, dict) and "provider" in result:
                responses.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"⚠️ Provider failed: {result}")

        logger.info(f"📊 Generated {len(responses)}/{len(tasks)} responses")
        return responses

    async def _generate_claude_response(
        self, query: str, user_message: str, system_prompt: Optional[str]
    ) -> Dict[str, str]:
        """Generate response from Claude 3.5 Sonnet"""
        try:
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=system_prompt
                or "Tu es un expert en production avicole. Réponds de manière factuelle et précise.",
                messages=[{"role": "user", "content": user_message}],
            )
            text = response.content[0].text
            logger.debug(f"✅ Claude response: {len(text)} chars")
            return {"provider": "claude", "text": text}
        except Exception as e:
            logger.error(f"❌ Claude generation failed: {e}")
            raise

    async def _generate_openai_response(
        self,
        provider_name: str,
        model: str,
        query: str,
        user_message: str,
        system_prompt: Optional[str],
    ) -> Dict[str, str]:
        """Generate response from OpenAI (GPT-4o)"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                        or "Tu es un expert en production avicole. Réponds de manière factuelle et précise.",
                    },
                    {"role": "user", "content": user_message},
                ],
            )
            text = response.choices[0].message.content
            logger.debug(f"✅ {provider_name} response: {len(text)} chars")
            return {"provider": provider_name, "text": text}
        except Exception as e:
            logger.error(f"❌ {provider_name} generation failed: {e}")
            raise

    async def _generate_deepseek_response(
        self, query: str, user_message: str, system_prompt: Optional[str]
    ) -> Dict[str, str]:
        """Generate response from DeepSeek"""
        try:
            response = await self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=1024,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                        or "Tu es un expert en production avicole. Réponds de manière factuelle et précise.",
                    },
                    {"role": "user", "content": user_message},
                ],
            )
            text = response.choices[0].message.content
            logger.debug(f"✅ DeepSeek response: {len(text)} chars")
            return {"provider": "deepseek", "text": text}
        except Exception as e:
            logger.error(f"❌ DeepSeek generation failed: {e}")
            raise

    async def _evaluate_responses(
        self,
        query: str,
        context_docs: List[Dict],
        responses: List[Dict[str, str]],
        language: str,
    ) -> List[ResponseQuality]:
        """
        Evaluate quality of all responses using judge LLM

        Returns:
            List of ResponseQuality objects, one per response
        """
        if not self.openai_client:
            logger.warning("⚠️ No judge client available, using dummy scores")
            return [
                ResponseQuality(
                    provider=r["provider"],
                    response=r["text"],
                    factual_score=0.8,
                    completeness_score=0.8,
                    coherence_score=0.8,
                    specificity_score=0.8,
                )
                for r in responses
            ]

        # Build evaluation prompt
        context_text = self._format_context(context_docs)
        responses_text = "\n\n".join(
            [
                f"**Réponse {i+1} ({r['provider']}):**\n{r['text']}"
                for i, r in enumerate(responses)
            ]
        )

        judge_prompt = f"""Tu es un évaluateur expert en production avicole. Évalue la qualité de chaque réponse selon 4 critères.

**Contexte de référence:**
{context_text}

**Question:**
{query}

**Réponses à évaluer:**
{responses_text}

**Critères d'évaluation (score 0.0 à 1.0):**
1. **Factualité** (0.0-1.0): La réponse est-elle exacte selon le contexte ?
2. **Complétude** (0.0-1.0): Tous les aspects de la question sont-ils couverts ?
3. **Cohérence** (0.0-1.0): La réponse est-elle logique et bien structurée ?
4. **Spécificité** (0.0-1.0): La réponse est-elle précise avec des valeurs concrètes ?

**Format de sortie (JSON strict):**
```json
[
  {{
    "response_id": 1,
    "provider": "claude",
    "factual_score": 0.95,
    "completeness_score": 0.90,
    "coherence_score": 0.85,
    "specificity_score": 0.90,
    "reasoning": "Brève justification"
  }},
  ...
]
```

Réponds UNIQUEMENT avec le JSON, sans texte additionnel."""

        try:
            # Call judge LLM
            response = await self.openai_client.chat.completions.create(
                model=self.judge_model,
                max_tokens=1024,
                temperature=0.0,  # Deterministic evaluation
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un évaluateur objectif. Réponds uniquement en JSON valide.",
                    },
                    {"role": "user", "content": judge_prompt},
                ],
            )

            # Parse judge response
            judge_text = response.choices[0].message.content
            import json
            import re

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", judge_text, re.DOTALL)
            if json_match:
                judge_text = json_match.group(1)

            evaluations = json.loads(judge_text)

            # Convert to ResponseQuality objects
            quality_assessments = []
            for eval_data, response in zip(evaluations, responses):
                quality_assessments.append(
                    ResponseQuality(
                        provider=response["provider"],
                        response=response["text"],
                        factual_score=eval_data.get("factual_score", 0.5),
                        completeness_score=eval_data.get("completeness_score", 0.5),
                        coherence_score=eval_data.get("coherence_score", 0.5),
                        specificity_score=eval_data.get("specificity_score", 0.5),
                    )
                )

            logger.info(
                "📊 Quality scores: "
                + ", ".join(
                    [f"{q.provider}={q.overall_score:.2f}" for q in quality_assessments]
                )
            )
            return quality_assessments

        except Exception as e:
            logger.error(f"❌ Judge evaluation failed: {e}")
            # Fallback: equal scores
            return [
                ResponseQuality(
                    provider=r["provider"],
                    response=r["text"],
                    factual_score=0.7,
                    completeness_score=0.7,
                    coherence_score=0.7,
                    specificity_score=0.7,
                )
                for r in responses
            ]

    def _select_best_response(
        self, responses: List[Dict[str, str]], quality_assessments: List[ResponseQuality]
    ) -> Dict[str, Any]:
        """
        Select single best response based on quality scores

        Returns:
            {
                "final_answer": str,
                "provider": str,
                "confidence": float
            }
        """
        # Find highest scoring response
        best_quality = max(quality_assessments, key=lambda q: q.overall_score)

        return {
            "final_answer": best_quality.response,
            "provider": best_quality.provider,
            "confidence": best_quality.overall_score,
        }

    async def _fuse_responses(
        self,
        query: str,
        responses: List[Dict[str, str]],
        quality_assessments: List[ResponseQuality],
        language: str,
    ) -> Dict[str, Any]:
        """
        Fuse multiple responses into single optimal answer

        Uses a synthesis LLM to merge best parts from all responses
        """
        if not self.openai_client:
            logger.warning("⚠️ No synthesis client, falling back to best-of-N")
            return self._select_best_response(responses, quality_assessments)

        # Build fusion prompt
        responses_with_scores = []
        for resp, quality in zip(responses, quality_assessments):
            responses_with_scores.append(
                f"**{resp['provider']} (score: {quality.overall_score:.2f}):**\n{resp['text']}"
            )

        fusion_prompt = f"""Tu es un expert en synthèse d'informations. Tu as reçu plusieurs réponses à la même question, chacune avec un score de qualité.

**Question originale:**
{query}

**Réponses disponibles:**
{chr(10).join(responses_with_scores)}

**Tâche:**
Synthétise une réponse optimale en:
1. Prenant les faits les plus précis de chaque réponse
2. Conservant les valeurs numériques les plus fiables
3. Éliminant les contradictions (privilégier les réponses à score élevé)
4. Produisant une réponse cohérente et complète

Réponds directement en {language}, sans préambule."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                temperature=0.3,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un synthétiseur expert. Fusionne les réponses en une réponse optimale.",
                    },
                    {"role": "user", "content": fusion_prompt},
                ],
            )

            fused_text = response.choices[0].message.content
            avg_confidence = sum(q.overall_score for q in quality_assessments) / len(
                quality_assessments
            )

            logger.info(f"✅ Fused response created (confidence={avg_confidence:.2f})")

            return {
                "final_answer": fused_text,
                "provider": "fusion",
                "confidence": avg_confidence,
            }

        except Exception as e:
            logger.error(f"❌ Fusion failed: {e}, falling back to best-of-N")
            return self._select_best_response(responses, quality_assessments)

    async def _vote_on_facts(
        self,
        query: str,
        responses: List[Dict[str, str]],
        quality_assessments: List[ResponseQuality],
        language: str,
    ) -> Dict[str, Any]:
        """
        Use voting to determine consensus on key facts

        Extracts numeric values/key facts from each response and uses majority vote
        """
        # For now, fallback to fusion (voting requires fact extraction)
        logger.info("ℹ️ Voting mode not yet implemented, using fusion")
        return await self._fuse_responses(
            query, responses, quality_assessments, language
        )

    async def _fallback_single_llm(
        self,
        query: str,
        context_docs: List[Dict],
        language: str,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        """Fallback to single LLM when ensemble is disabled"""

        context_text = self._format_context(context_docs)
        user_message = f"""Contexte:
{context_text}

Question: {query}

Réponds en {language}."""

        # Use Claude if available, else GPT-4o
        if self.claude_client:
            result = await self._generate_claude_response(
                query, user_message, system_prompt
            )
            provider = "claude"
        elif self.openai_client:
            result = await self._generate_openai_response(
                "gpt4o", "gpt-4o", query, user_message, system_prompt
            )
            provider = "gpt4o"
        else:
            return {
                "final_answer": "Aucun LLM disponible.",
                "provider": "none",
                "confidence": 0.0,
            }

        return {
            "final_answer": result["text"],
            "provider": provider,
            "confidence": 0.8,  # Default confidence for single LLM
            "all_responses": [result],
            "quality_scores": [],
        }

    def _format_context(self, context_docs: List[Dict]) -> str:
        """Format context documents for prompts"""
        if not context_docs:
            return "Aucun contexte disponible."

        formatted = []
        for i, doc in enumerate(context_docs[:5], 1):  # Limit to top 5
            content = doc.get("page_content", doc.get("content", ""))
            source = doc.get("metadata", {}).get("source", "unknown")
            formatted.append(f"[Doc {i} - {source}]\n{content}")

        return "\n\n".join(formatted)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get ensemble usage statistics"""
        return self.usage_stats.copy()


# Singleton instance
_ensemble_instance = None


def get_llm_ensemble(
    mode: EnsembleMode = EnsembleMode.BEST_OF_N, force_new: bool = False
) -> LLMEnsemble:
    """
    Get or create LLM Ensemble singleton

    Args:
        mode: Ensemble mode to use
        force_new: Force creation of new instance

    Returns:
        LLMEnsemble instance
    """
    global _ensemble_instance

    if _ensemble_instance is None or force_new:
        _ensemble_instance = LLMEnsemble(mode=mode)

    return _ensemble_instance
