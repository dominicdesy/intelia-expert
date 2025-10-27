# -*- coding: utf-8 -*-
"""
ragas_evaluator.py - RAGAS-based evaluation for Intelia Expert LLM
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
ragas_evaluator.py - RAGAS-based evaluation for Intelia Expert LLM

Implements comprehensive RAG evaluation using the RAGAS framework.
Metrics: Context Precision, Context Recall, Faithfulness, Answer Relevancy

Documentation: https://docs.ragas.io/en/stable/
"""

import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import numpy as np

# RAGAS imports
try:
    from ragas import evaluate
    from ragas.metrics import (
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    )
    from datasets import Dataset, Features, Value, Sequence

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logging.warning("⚠️ RAGAS not installed. Run: pip install ragas datasets")

# LangChain imports for LLM configuration
try:
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning(
        "⚠️ LangChain OpenAI not installed. Run: pip install langchain-openai"
    )

logger = logging.getLogger(__name__)


def convert_numpy_to_python(obj):
    """
    Convertit les types numpy en types Python natifs pour JSON serialization.

    Args:
        obj: Objet à convertir (peut être dict, list, ndarray, etc.)

    Returns:
        Objet converti en types Python natifs
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    else:
        return obj


class RAGASEvaluator:
    """
    Évaluateur RAGAS pour système RAG Intelia Expert.

    Mesure 4 métriques principales:
    - Context Precision: Pertinence des documents récupérés
    - Context Recall: Couverture du contexte par rapport à la ground truth
    - Faithfulness: Fidélité de la réponse au contexte fourni
    - Answer Relevancy: Pertinence de la réponse à la question
    """

    def __init__(
        self,
        llm_model: str = "gpt-4o",
        temperature: float = 0.0,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialise l'évaluateur RAGAS.

        Args:
            llm_model: Modèle LLM pour évaluation (défaut: gpt-4o)
            temperature: Température pour génération (défaut: 0.0 pour déterminisme)
            openai_api_key: Clé API OpenAI (optionnel, prend OPENAI_API_KEY si None)
        """
        if not RAGAS_AVAILABLE:
            raise ImportError(
                "RAGAS non installé. Exécutez: pip install ragas datasets"
            )

        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain OpenAI non installé. Exécutez: pip install langchain-openai"
            )

        self.llm_model = llm_model
        self.temperature = temperature
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY non configurée")

        # Initialiser LLM pour évaluation
        self.evaluator_llm = ChatOpenAI(
            model=llm_model, temperature=temperature, api_key=self.openai_api_key
        )

        # Métriques RAGAS
        self.metrics = [
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ]

        logger.info(f"✅ RAGASEvaluator initialisé avec {llm_model}")

    def prepare_evaluation_dataset(self, test_cases: List[Dict[str, Any]]) -> Dataset:
        """
        Prépare un dataset RAGAS à partir de cas de test.

        Args:
            test_cases: Liste de dictionnaires avec:
                - question: Question posée (str)
                - answer: Réponse générée par le RAG (str)
                - contexts: Liste de contextes récupérés (List[str])
                - ground_truth: Réponse attendue (str, optionnel)

        Returns:
            Dataset RAGAS formaté

        Example:
            >>> test_cases = [{
            ...     "question": "Quel est le poids cible Ross 308 à 35j?",
            ...     "answer": "Le poids cible est de 2350g pour mâles...",
            ...     "contexts": ["Ross 308: poids 35j mâles 2350g...", ...],
            ...     "ground_truth": "2350g pour mâles, 2100g pour femelles"
            ... }]
            >>> dataset = evaluator.prepare_evaluation_dataset(test_cases)
        """
        # Valider structure
        required_keys = {"question", "answer", "contexts"}
        for i, case in enumerate(test_cases):
            missing = required_keys - set(case.keys())
            if missing:
                raise ValueError(f"Cas de test {i} manque clés: {missing}")

            # Vérifier types
            if not isinstance(case["question"], str):
                raise TypeError(f"Cas {i}: 'question' doit être str")
            if not isinstance(case["answer"], str):
                raise TypeError(f"Cas {i}: 'answer' doit être str")
            if not isinstance(case["contexts"], list):
                raise TypeError(f"Cas {i}: 'contexts' doit être List[str]")
            if case.get("ground_truth") and not isinstance(case["ground_truth"], str):
                raise TypeError(f"Cas {i}: 'ground_truth' doit être str")

        # Convertir en format RAGAS
        ragas_data = {
            "question": [case["question"] for case in test_cases],
            "answer": [case["answer"] for case in test_cases],
            "contexts": [case["contexts"] for case in test_cases],
        }

        # Ajouter ground_truth si disponible
        if any("ground_truth" in case for case in test_cases):
            ragas_data["ground_truth"] = [
                case.get("ground_truth", "") for case in test_cases
            ]

        # Définir features explicitement pour RAGAS 0.1.1
        features = Features({
            "question": Value("string"),
            "answer": Value("string"),
            "contexts": Sequence(Value("string")),
        })

        if "ground_truth" in ragas_data:
            features["ground_truth"] = Value("string")

        dataset = Dataset.from_dict(ragas_data, features=features)

        logger.info(f"📊 Dataset RAGAS créé: {len(test_cases)} cas de test")

        return dataset

    async def evaluate_async(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Évalue le système RAG de manière asynchrone.

        Args:
            test_cases: Liste de cas de test (voir prepare_evaluation_dataset)

        Returns:
            Dictionnaire avec:
                - scores: Scores par métrique (moyenne)
                - detailed_scores: Scores par cas de test
                - summary: Résumé textuel
                - timestamp: Date d'évaluation

        Example:
            >>> results = await evaluator.evaluate_async(test_cases)
            >>> print(f"Faithfulness: {results['scores']['faithfulness']:.2%}")
        """
        # Préparer dataset
        dataset = self.prepare_evaluation_dataset(test_cases)

        logger.info(f"🔍 Début évaluation RAGAS ({len(test_cases)} cas)...")
        start_time = datetime.now()

        try:
            # Évaluer avec RAGAS (sync, wrapper async)
            result = await asyncio.to_thread(
                evaluate, dataset=dataset, metrics=self.metrics, llm=self.evaluator_llm
            )

            # Extraire scores et convertir numpy en Python natif
            # result est un EvaluationResult object, convertir en dict via to_pandas()
            result_df = result.to_pandas()
            scores = {
                "context_precision": float(result_df["context_precision"].mean()),
                "context_recall": float(result_df["context_recall"].mean()),
                "faithfulness": float(result_df["faithfulness"].mean()),
                "answer_relevancy": float(result_df["answer_relevancy"].mean()),
            }

            # Score global (moyenne)
            overall_score = sum(scores.values()) / len(scores)
            scores["overall"] = float(overall_score)

            # Détails par cas de test (convertir numpy arrays)
            detailed_scores = []
            if hasattr(result, "to_pandas"):
                detailed_scores_raw = result.to_pandas().to_dict("records")
                detailed_scores = convert_numpy_to_python(detailed_scores_raw)

            # Résumé
            duration = (datetime.now() - start_time).total_seconds()
            summary = self._generate_summary(scores, len(test_cases), duration)

            evaluation_result = {
                "scores": scores,
                "detailed_scores": detailed_scores,
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
                "llm_model": self.llm_model,
                "num_test_cases": len(test_cases),
                "duration_seconds": float(duration),
            }

            logger.info(f"✅ Évaluation terminée: Overall={overall_score:.2%}")

            return evaluation_result

        except Exception as e:
            logger.error(f"❌ Erreur évaluation RAGAS: {e}")
            raise

    def evaluate(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Évalue le système RAG de manière synchrone (wrapper).

        Args:
            test_cases: Liste de cas de test

        Returns:
            Résultats d'évaluation (voir evaluate_async)
        """
        return asyncio.run(self.evaluate_async(test_cases))

    def _generate_summary(
        self, scores: Dict[str, float], num_cases: int, duration: float
    ) -> str:
        """
        Génère un résumé textuel de l'évaluation.

        Args:
            scores: Scores par métrique
            num_cases: Nombre de cas de test
            duration: Durée en secondes

        Returns:
            Résumé formaté
        """
        summary = f"""
=================================================================
📊 RAGAS EVALUATION REPORT - Intelia Expert LLM
=================================================================

Test Cases:        {num_cases}
LLM Model:         {self.llm_model}
Duration:          {duration:.1f}s ({duration/60:.1f} min)
Timestamp:         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-----------------------------------------------------------------
SCORES
-----------------------------------------------------------------
Overall Score:          {scores['overall']:.2%}

Context Precision:      {scores['context_precision']:.2%}
  → Pertinence des documents récupérés

Context Recall:         {scores['context_recall']:.2%}
  → Couverture du contexte par rapport à ground truth

Faithfulness:           {scores['faithfulness']:.2%}
  → Fidélité de la réponse au contexte

Answer Relevancy:       {scores['answer_relevancy']:.2%}
  → Pertinence de la réponse à la question

-----------------------------------------------------------------
INTERPRETATION
-----------------------------------------------------------------
"""

        # Interprétation globale
        overall = scores["overall"]
        if overall >= 0.90:
            summary += "🏆 Excellent: Système RAG performant (>90%)\n"
        elif overall >= 0.80:
            summary += "✅ Très Bon: Qualité élevée (80-90%)\n"
        elif overall >= 0.70:
            summary += "⚠️ Bon: Améliorations possibles (70-80%)\n"
        else:
            summary += "❌ Insuffisant: Optimisation requise (<70%)\n"

        # Recommandations par métrique
        if scores["context_precision"] < 0.80:
            summary += "\n💡 Améliorer Context Precision:\n"
            summary += "   - Affiner le reranking (Cohere)\n"
            summary += "   - Optimiser les seuils de similarité\n"
            summary += "   - Améliorer la recherche hybride (RRF)\n"

        if scores["context_recall"] < 0.80:
            summary += "\n💡 Améliorer Context Recall:\n"
            summary += "   - Augmenter top_k retrieval\n"
            summary += "   - Enrichir la base de connaissances\n"
            summary += "   - Améliorer les embeddings (fine-tuning)\n"

        if scores["faithfulness"] < 0.80:
            summary += "\n💡 Améliorer Faithfulness:\n"
            summary += "   - Renforcer les guardrails (hallucination detection)\n"
            summary += "   - Ajuster les prompts système\n"
            summary += "   - Réduire la température du LLM\n"

        if scores["answer_relevancy"] < 0.80:
            summary += "\n💡 Améliorer Answer Relevancy:\n"
            summary += "   - Optimiser la génération de réponse\n"
            summary += "   - Affiner les prompts contextuels\n"
            summary += "   - Améliorer la compréhension d'intention\n"

        summary += (
            "\n=================================================================\n"
        )

        return summary

    def save_results(self, results: Dict[str, Any], output_path: str):
        """
        Sauvegarde les résultats d'évaluation.

        Args:
            results: Résultats d'évaluation (de evaluate_async)
            output_path: Chemin du fichier de sortie (.json)
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Résultats sauvegardés: {output_path}")

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde résultats: {e}")
            raise


# ============================================================================
# UTILITY: Generate Golden Dataset for Intelia Expert
# ============================================================================


def generate_poultry_golden_dataset() -> List[Dict[str, Any]]:
    """
    Génère un dataset golden de cas de test pour l'évaluation.

    Contient des questions avicoles réelles avec réponses attendues.

    Returns:
        Liste de cas de test formatés pour RAGAS

    Note:
        Ce dataset doit être maintenu et enrichi au fil du temps.
        Les ground_truth doivent être validées par des experts avicoles.
    """
    return [
        # Performance Standards - Ross 308
        {
            "question": "Quel est le poids cible pour des mâles Ross 308 à 35 jours?",
            "ground_truth": "Le poids cible pour des mâles Ross 308 à 35 jours est de 2350g selon les standards de performance 2024.",
            "contexts": [],  # À remplir dynamiquement lors de l'évaluation
            "answer": "",  # À remplir par le RAG
        },
        {
            "question": "Quel FCR est attendu pour des Ross 308 mixte à 42 jours?",
            "ground_truth": "Le FCR (Feed Conversion Ratio) attendu pour Ross 308 mixte à 42 jours est de 1.65-1.70.",
            "contexts": [],
            "answer": "",
        },
        # Performance Standards - Cobb 500
        {
            "question": "Quel est le gain de poids journalier pour des mâles Cobb 500 à 28 jours?",
            "ground_truth": "Le gain de poids journalier pour des mâles Cobb 500 à 28 jours est d'environ 60-65g/jour.",
            "contexts": [],
            "answer": "",
        },
        # Nutrition
        {
            "question": "Quel taux de protéine est requis dans l'aliment starter pour Ross 308 de 0-10 jours?",
            "ground_truth": "Le taux de protéine requis dans l'aliment starter pour Ross 308 de 0-10 jours est de 22-23%.",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Quelle densité énergétique est recommandée pour aliment grower Cobb 500?",
            "ground_truth": "La densité énergétique recommandée pour l'aliment grower Cobb 500 est de 3100-3200 kcal/kg.",
            "contexts": [],
            "answer": "",
        },
        # Environment
        {
            "question": "Quelle température ambiante optimale pour poussins Ross 308 jour 1?",
            "ground_truth": "La température ambiante optimale pour les poussins Ross 308 au jour 1 est de 32-34°C.",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Quel taux d'humidité optimal dans bâtiment broiler semaine 4?",
            "ground_truth": "Le taux d'humidité optimal dans un bâtiment broiler en semaine 4 est de 50-70%.",
            "contexts": [],
            "answer": "",
        },
        # Laying Hens - ISA Brown
        {
            "question": "Combien d'œufs par jour pour 1000 poules ISA Brown à 28 semaines?",
            "ground_truth": "1000 poules ISA Brown à 28 semaines produisent environ 950-960 œufs par jour (95-96% de ponte).",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Quel poids corporel cible pour poulette ISA Brown à 16 semaines?",
            "ground_truth": "Le poids corporel cible pour une poulette ISA Brown à 16 semaines est de 1350-1450g.",
            "contexts": [],
            "answer": "",
        },
        # Health & Veterinary
        {
            "question": "Quel est le protocole de vaccination Newcastle pour pondeuses?",
            "ground_truth": "Le protocole de vaccination Newcastle pour pondeuses inclut généralement une primo-vaccination à 10-14 jours (vaccin vivant atténué), un rappel à 4-6 semaines, puis des rappels réguliers tous les 2-3 mois selon le niveau de pression sanitaire.",
            "contexts": [],
            "answer": "",
        },
        # Comparative Questions
        {
            "question": "Quelle différence de FCR entre Ross 308 et Cobb 500 à 42 jours?",
            "ground_truth": "À 42 jours, Ross 308 et Cobb 500 ont des FCR très similaires (1.65-1.70). La différence est minime (<0.05) avec un léger avantage potentiel pour Ross 308 dans certaines conditions.",
            "contexts": [],
            "answer": "",
        },
        # Mathematical Operations
        {
            "question": "Combien de kg d'aliment pour élever 1000 Ross 308 de 0 à 35 jours?",
            "ground_truth": "Pour élever 1000 Ross 308 de 0 à 35 jours, il faut environ 3500-3700 kg d'aliment (FCR ~1.50 × poids moyen 2.3kg × 1000 poulets).",
            "contexts": [],
            "answer": "",
        },
    ]


# ============================================================================
# MAIN: Example Usage
# ============================================================================


async def main_example():
    """Exemple d'utilisation de RAGASEvaluator"""

    # Initialiser évaluateur
    evaluator = RAGASEvaluator(llm_model="gpt-4o", temperature=0.0)

    # Générer dataset golden
    golden_dataset = generate_poultry_golden_dataset()

    # Simuler réponses du RAG (dans la pratique, interroger le vrai système)
    for case in golden_dataset[:3]:  # Test avec 3 cas
        # Simuler appel au RAG
        case["answer"] = f"Réponse simulée pour: {case['question']}"
        case["contexts"] = [
            "Contexte 1: Information pertinente...",
            "Contexte 2: Données additionnelles...",
        ]

    # Évaluer
    results = await evaluator.evaluate_async(golden_dataset[:3])

    # Afficher résumé
    print(results["summary"])

    # Sauvegarder résultats
    evaluator.save_results(results, "evaluation_results.json")


if __name__ == "__main__":
    # Exemple exécution
    asyncio.run(main_example())
