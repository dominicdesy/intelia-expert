#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_ragas_evaluation.py - Script d'évaluation RAGAS pour Intelia Expert

Évalue le système RAG avec un dataset de questions avicoles.
Génère un rapport détaillé avec scores RAGAS.

Usage:
    python scripts/run_ragas_evaluation.py [--test-cases N] [--output PATH]

Options:
    --test-cases N    Nombre de cas de test (défaut: tous)
    --output PATH     Chemin fichier de sortie (défaut: logs/ragas_evaluation_{timestamp}.json)
    --llm MODEL       Modèle LLM évaluateur (défaut: gpt-4o)
"""

import asyncio
import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports après path setup
from evaluation.ragas_evaluator import RAGASEvaluator
from evaluation.golden_dataset_intelia import get_intelia_test_dataset

# Import du système RAG réel
try:
    from core.rag_engine import InteliaRAGEngine

    RAG_ENGINE_AVAILABLE = True
except ImportError:
    RAG_ENGINE_AVAILABLE = False
    logging.warning("⚠️ InteliaRAGEngine non disponible, mode simulation")

# Configuration logging
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f'logs/ragas_evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        ),
    ],
)
logger = logging.getLogger(__name__)


async def query_rag_system(
    question: str, rag_engine: Optional[object] = None
) -> Dict[str, Any]:
    """
    Interroge le système RAG et retourne réponse + contextes.

    Args:
        question: Question à poser
        rag_engine: Instance de InteliaRAGEngine (optionnel)

    Returns:
        Dictionnaire avec:
            - answer: Réponse générée (str)
            - contexts: Liste de contextes récupérés (List[str])
    """
    if rag_engine and RAG_ENGINE_AVAILABLE:
        try:
            # Appel réel au RAG (méthode correcte: generate_response)
            result = await rag_engine.generate_response(
                query=question,
                language="fr",  # Détection automatique dans le vrai système
                conversation_id=f"ragas_eval_{datetime.now().timestamp()}",
            )

            # Extraire answer (RAGResult.answer)
            answer = result.answer or "[PAS DE RÉPONSE]"

            # Extraire contextes des documents (RAGResult.context_docs: List[Dict])
            contexts = []
            for doc in result.context_docs:
                # doc est un dictionnaire avec 'content' ou 'text'
                content = doc.get("content") or doc.get("text") or doc.get("page_content", "")
                if content:
                    contexts.append(content)

            return {"answer": answer, "contexts": contexts}

        except Exception as e:
            logger.error(f"❌ Erreur query RAG: {e}", exc_info=True)
            return {"answer": f"[ERREUR: {str(e)}]", "contexts": []}
    else:
        # Mode simulation (si RAG non disponible)
        logger.warning(f"⚠️ Simulation réponse pour: {question[:50]}...")
        return {
            "answer": f"[SIMULATION] Réponse pour: {question}",
            "contexts": [
                f"[SIMULATION] Contexte 1 pour {question}",
                f"[SIMULATION] Contexte 2 pour {question}",
            ],
        }


async def run_evaluation(
    num_test_cases: int = None,
    output_path: str = None,
    llm_model: str = "gpt-4o",
    use_real_rag: bool = True,
):
    """
    Exécute l'évaluation RAGAS complète.

    Args:
        num_test_cases: Nombre de cas de test (None = tous)
        output_path: Chemin fichier de sortie
        llm_model: Modèle LLM évaluateur
        use_real_rag: Utiliser vrai RAG (True) ou simulation (False)
    """
    logger.info("=" * 70)
    logger.info("🚀 RAGAS EVALUATION - Intelia Expert LLM")
    logger.info("=" * 70)

    # Générer dataset golden
    logger.info("📊 Chargement dataset golden Intelia...")
    golden_dataset = get_intelia_test_dataset()

    # Limiter nombre de cas si spécifié
    if num_test_cases:
        golden_dataset = golden_dataset[:num_test_cases]
        logger.info(f"   Limité à {num_test_cases} cas de test")

    logger.info(f"   ✅ {len(golden_dataset)} cas de test générés")

    # Initialiser RAG engine si disponible
    rag_engine = None
    if use_real_rag and RAG_ENGINE_AVAILABLE:
        try:
            logger.info("🔧 Initialisation InteliaRAGEngine...")
            rag_engine = InteliaRAGEngine()
            await rag_engine.initialize()
            logger.info("   ✅ RAG Engine initialisé")
        except Exception as e:
            logger.warning(f"   ⚠️ Impossible d'initialiser RAG: {e}")
            logger.info("   → Mode simulation activé")
            rag_engine = None
    else:
        logger.info("🔍 Mode simulation (RAG Engine non disponible)")

    # Interroger le RAG pour chaque cas
    logger.info(f"🔍 Interrogation du système RAG ({len(golden_dataset)} questions)...")

    for i, case in enumerate(golden_dataset, 1):
        logger.info(f"   [{i}/{len(golden_dataset)}] {case['question'][:60]}...")

        # Query RAG
        rag_result = await query_rag_system(
            question=case["question"], rag_engine=rag_engine
        )

        # Mettre à jour cas de test
        case["answer"] = rag_result["answer"]
        case["contexts"] = rag_result["contexts"]

        # Pause pour éviter rate limiting
        await asyncio.sleep(0.5)

    logger.info("   ✅ Toutes les questions traitées")

    # Initialiser évaluateur RAGAS
    logger.info(f"🔧 Initialisation RAGASEvaluator (modèle: {llm_model})...")
    evaluator = RAGASEvaluator(llm_model=llm_model, temperature=0.0)
    logger.info("   ✅ Évaluateur initialisé")

    # Évaluer avec RAGAS
    logger.info("📊 Évaluation RAGAS en cours...")
    results = await evaluator.evaluate_async(golden_dataset)

    # Afficher résumé
    print("\n" + results["summary"])

    # Sauvegarder résultats
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"logs/ragas_evaluation_{timestamp}.json"

    evaluator.save_results(results, output_path)

    logger.info(f"💾 Résultats sauvegardés: {output_path}")

    # Cleanup RAG engine
    if rag_engine:
        try:
            await rag_engine.close()
            logger.info("✅ RAG Engine fermé")
        except Exception as e:
            logger.warning(f"⚠️ Erreur fermeture RAG: {e}")

    logger.info("=" * 70)
    logger.info("✅ ÉVALUATION TERMINÉE")
    logger.info("=" * 70)

    return results


def main():
    """Point d'entrée principal"""

    # Parser arguments
    parser = argparse.ArgumentParser(
        description="Évaluation RAGAS pour Intelia Expert LLM"
    )
    parser.add_argument(
        "--test-cases",
        type=int,
        default=None,
        help="Nombre de cas de test (défaut: tous)",
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Chemin fichier de sortie JSON"
    )
    parser.add_argument(
        "--llm",
        type=str,
        default="gpt-4o",
        help="Modèle LLM évaluateur (défaut: gpt-4o)",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Mode simulation (ne pas utiliser vrai RAG)",
    )

    args = parser.parse_args()

    # Vérifier variable d'environnement OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY non configurée")
        sys.exit(1)

    # Exécuter évaluation
    try:
        asyncio.run(
            run_evaluation(
                num_test_cases=args.test_cases,
                output_path=args.output,
                llm_model=args.llm,
                use_real_rag=not args.simulate,
            )
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Évaluation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Compatibilité Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    main()
