"""
Service d'analyse de qualité Q&A avec OpenAI
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Service d'analyse de qualité Q&A avec OpenAI
Détecte automatiquement les réponses problématiques
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL = "gpt-3.5-turbo"  # Économique pour l'analyse
ANALYSIS_PROMPT_VERSION = "v1.0"

# OpenAI client (lazy initialization)
_client = None


def get_openai_client():
    """Lazy initialization of OpenAI client"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(api_key=api_key)
    return _client

# Seuils de détection
QUALITY_THRESHOLD = 5.0  # Score < 5 = problématique
CONFIDENCE_THRESHOLD = 0.7  # Confiance minimale pour marquer comme problématique


class QAQualityAnalyzer:
    """Analyseur de qualité Q&A utilisant OpenAI"""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.prompt_version = ANALYSIS_PROMPT_VERSION

    def build_analysis_prompt(
        self,
        question: str,
        response: str,
        response_source: Optional[str] = None,
        response_confidence: Optional[float] = None,
        context_docs: Optional[List[str]] = None
    ) -> str:
        """Construit le prompt d'analyse pour OpenAI"""

        prompt = f"""Tu es un expert en aviculture chargé d'évaluer la qualité des réponses fournies par un système d'IA.

**QUESTION DE L'UTILISATEUR:**
{question}

**RÉPONSE FOURNIE:**
{response}

**MÉTADONNÉES:**
- Source de la réponse: {response_source or 'inconnue'}
- Confiance du système: {response_confidence or 'non spécifiée'}
"""

        if context_docs:
            prompt += f"\n**DOCUMENTS DE CONTEXTE UTILISÉS:**\n"
            for i, doc in enumerate(context_docs[:3], 1):
                prompt += f"{i}. {doc[:200]}...\n"

        prompt += """

**TÂCHE D'ÉVALUATION:**

Analyse cette réponse selon les critères suivants:

1. **Exactitude technique** (0-10): La réponse est-elle techniquement correcte en aviculture?
2. **Pertinence** (0-10): La réponse répond-elle directement à la question posée?
3. **Complétude** (0-10): La réponse est-elle suffisamment détaillée et complète?
4. **Cohérence** (0-10): La réponse est-elle cohérente et sans contradictions?

**DÉTECTION DE PROBLÈMES:**

Identifie si la réponse présente l'un de ces problèmes graves:

- ❌ **Informations incorrectes**: Erreurs factuelles, données obsolètes, conseils dangereux
- ❌ **Hors sujet**: Réponse qui ne correspond pas à la question
- ❌ **Réponse générique**: Réponse vague sans détails spécifiques à l'aviculture
- ❌ **Informations manquantes**: Omet des éléments critiques pour la sécurité/santé
- ❌ **Contradictions**: Contient des affirmations contradictoires
- ❌ **Hallucination**: Invente des faits, statistiques ou recommandations non vérifiables

**FORMAT DE RÉPONSE (JSON strict):**

{
  "scores": {
    "accuracy": 0-10,
    "relevance": 0-10,
    "completeness": 0-10,
    "coherence": 0-10
  },
  "overall_quality_score": 0-10,
  "is_problematic": true/false,
  "problem_category": "incorrect|incomplete|off_topic|generic|contradictory|hallucination|none",
  "problems": ["liste des problèmes spécifiques détectés"],
  "recommendation": "recommandation pour améliorer la réponse ou action à prendre",
  "confidence": 0.0-1.0,
  "reasoning": "explication brève de l'évaluation"
}

**CRITÈRES POUR is_problematic=true:**
- overall_quality_score < 5
- OU présence d'informations incorrectes/dangereuses
- OU réponse complètement hors sujet
- OU hallucination détectée

Réponds UNIQUEMENT avec le JSON, sans texte additionnel.
"""

        return prompt

    async def analyze_qa(
        self,
        question: str,
        response: str,
        response_source: Optional[str] = None,
        response_confidence: Optional[float] = None,
        context_docs: Optional[List[str]] = None,
        trigger: str = "manual"
    ) -> Dict[str, Any]:
        """
        Analyse une paire Q&A et retourne les résultats

        Args:
            question: Question de l'utilisateur
            response: Réponse fournie par le système
            response_source: Source de la réponse (rag, openai_fallback, etc.)
            response_confidence: Score de confiance du système (0-1)
            context_docs: Documents de contexte utilisés (optionnel)
            trigger: Comment l'analyse a été déclenchée (manual, batch, realtime, etc.)

        Returns:
            Dict contenant les résultats d'analyse
        """
        try:
            prompt = self.build_analysis_prompt(
                question=question,
                response=response,
                response_source=response_source,
                response_confidence=response_confidence,
                context_docs=context_docs
            )

            logger.info(f"🔍 [QA_QUALITY] Analysing Q&A with {self.model}")

            # Appel à OpenAI
            client = get_openai_client()
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en aviculture et en évaluation de la qualité des réponses. Tu réponds toujours en JSON strict."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Peu de créativité pour l'analyse
                max_tokens=800,
                response_format={"type": "json_object"}  # Force JSON
            )

            # Parser la réponse
            analysis_text = completion.choices[0].message.content
            analysis = json.loads(analysis_text)

            # Valider et enrichir les résultats
            overall_score = analysis.get("overall_quality_score", 0)
            is_problematic = analysis.get("is_problematic", False)
            confidence = analysis.get("confidence", 0.5)

            # Application des seuils
            if overall_score < QUALITY_THRESHOLD:
                is_problematic = True

            # Si confiance basse de l'analyseur, être prudent
            if confidence < CONFIDENCE_THRESHOLD and is_problematic:
                logger.warning(f"⚠️ [QA_QUALITY] Low analysis confidence: {confidence}")

            result = {
                "quality_score": round(overall_score, 1),
                "is_problematic": is_problematic,
                "problem_category": analysis.get("problem_category", "none"),
                "problems": analysis.get("problems", []),
                "recommendation": analysis.get("recommendation", ""),
                "analysis_confidence": round(confidence, 2),
                "scores_detail": analysis.get("scores", {}),
                "reasoning": analysis.get("reasoning", ""),
                "analysis_trigger": trigger,
                "analysis_model": self.model,
                "analysis_prompt_version": self.prompt_version,
                "analyzed_at": datetime.now().isoformat(),
                "tokens_used": completion.usage.total_tokens,
                "cost_estimate": self._estimate_cost(completion.usage.total_tokens)
            }

            logger.info(
                f"✅ [QA_QUALITY] Analysis complete: "
                f"score={overall_score}, problematic={is_problematic}, "
                f"category={result['problem_category']}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ [QA_QUALITY] JSON parsing error: {e}")
            return self._create_error_result("json_parse_error", str(e))

        except Exception as e:
            logger.error(f"❌ [QA_QUALITY] Analysis error: {e}", exc_info=True)
            return self._create_error_result("analysis_error", str(e))

    def _estimate_cost(self, tokens: int) -> float:
        """Estime le coût de l'analyse en USD"""
        # Prix GPT-3.5-turbo: $0.0005/1K input + $0.0015/1K output
        # Approximation: ~$0.001 per 1K tokens
        return round((tokens / 1000) * 0.001, 4)

    def _create_error_result(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """Crée un résultat d'erreur standardisé"""
        return {
            "quality_score": None,
            "is_problematic": False,
            "problem_category": "analysis_error",
            "problems": [f"{error_type}: {error_message}"],
            "recommendation": "Analyse manuelle requise",
            "analysis_confidence": 0.0,
            "scores_detail": {},
            "reasoning": f"Erreur lors de l'analyse: {error_message}",
            "analysis_trigger": "error",
            "analysis_model": self.model,
            "analysis_prompt_version": self.prompt_version,
            "analyzed_at": datetime.now().isoformat(),
            "tokens_used": 0,
            "cost_estimate": 0.0,
            "error": True
        }

    def should_analyze_realtime(
        self,
        response_source: Optional[str] = None,
        response_confidence: Optional[float] = None,
        feedback: Optional[int] = None
    ) -> bool:
        """
        Détermine si une Q&A doit être analysée en temps réel (Approche C - Hybride)

        Critères pour analyse temps réel:
        - Feedback négatif de l'utilisateur
        - Confidence très basse (< 0.3)
        - Source openai_fallback avec confidence < 0.5
        - Source inconnue

        Returns:
            True si analyse temps réel recommandée
        """
        # Feedback négatif = analyse immédiate
        if feedback is not None and feedback < 0:
            logger.info("🚨 [QA_QUALITY] Realtime analysis triggered: negative feedback")
            return True

        # Confidence très basse
        if response_confidence is not None and response_confidence < 0.3:
            logger.info("🚨 [QA_QUALITY] Realtime analysis triggered: low confidence")
            return True

        # Fallback OpenAI avec confidence moyenne-basse
        if response_source == "openai_fallback" and (response_confidence or 0) < 0.5:
            logger.info("🚨 [QA_QUALITY] Realtime analysis triggered: fallback with low confidence")
            return True

        # Source inconnue ou manquante
        if not response_source or response_source == "unknown":
            logger.info("🚨 [QA_QUALITY] Realtime analysis triggered: unknown source")
            return True

        return False


# Instance globale
qa_analyzer = QAQualityAnalyzer()
