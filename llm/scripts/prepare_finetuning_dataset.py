#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_finetuning_dataset.py - Génération dataset fine-tuning embeddings avicoles

Extrait documents de Weaviate/PostgreSQL et génère des paires (query, positive)
pour fine-tuner text-embedding-3-large sur vocabulaire avicole.

Usage:
    python scripts/prepare_finetuning_dataset.py [--target N] [--output PATH]

Options:
    --target N        Nombre de paires cibles (défaut: 1000)
    --output PATH     Chemin fichier sortie (défaut: data/finetuning_dataset_raw.json)
    --queries-per-doc N  Questions générées par document (défaut: 3)
"""

import asyncio
import os
import sys
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Ajouter répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports après path setup
from utils.imports_and_dependencies import AsyncOpenAI

# Imports conditionnels
try:
    from core.rag_weaviate_core import WeaviateCore

    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    logging.warning("⚠️ WeaviateCore non disponible")

try:
    from core.rag_postgresql_retriever import PostgreSQLRetriever

    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    logging.warning("⚠️ PostgreSQLRetriever non disponible")

# Configuration logging
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f'logs/finetuning_prep_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        ),
    ],
)
logger = logging.getLogger(__name__)


class FineTuningDatasetGenerator:
    """
    Générateur de dataset de fine-tuning pour embeddings avicoles.

    Workflow:
    1. Extraire documents de Weaviate + PostgreSQL
    2. Pour chaque document, générer 3-5 questions représentatives (LLM)
    3. Sauvegarder paires (query, positive)
    """

    def __init__(
        self,
        target_pairs: int = 1000,
        queries_per_doc: int = 3,
        openai_api_key: str = None,
    ):
        self.target_pairs = target_pairs
        self.queries_per_doc = queries_per_doc
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY non configurée")

        # Clients
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        self.weaviate_core = None
        self.postgresql_retriever = None

        # Dataset
        self.pairs = []

        # Stats
        self.stats = {
            "total_documents": 0,
            "queries_generated": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
        }

    async def initialize(self):
        """Initialise les clients Weaviate et PostgreSQL"""
        logger.info("🔧 Initialisation des clients...")

        # Weaviate
        if WEAVIATE_AVAILABLE:
            try:
                self.weaviate_core = WeaviateCore()
                await self.weaviate_core.initialize()
                logger.info("   ✅ WeaviateCore initialisé")
            except Exception as e:
                logger.warning(f"   ⚠️ Weaviate indisponible: {e}")
        else:
            logger.warning("   ⚠️ Weaviate non disponible")

        # PostgreSQL
        if POSTGRESQL_AVAILABLE:
            try:
                self.postgresql_retriever = PostgreSQLRetriever()
                await self.postgresql_retriever.initialize()
                logger.info("   ✅ PostgreSQL initialisé")
            except Exception as e:
                logger.warning(f"   ⚠️ PostgreSQL indisponible: {e}")
        else:
            logger.warning("   ⚠️ PostgreSQL non disponible")

        if not self.weaviate_core and not self.postgresql_retriever:
            raise RuntimeError("Aucune source de données disponible")

    async def fetch_documents(self) -> List[Dict[str, Any]]:
        """
        Récupère documents de Weaviate et PostgreSQL.

        Returns:
            Liste de documents avec:
                - content: Texte du document
                - source: "weaviate" ou "postgresql"
                - metadata: Métadonnées additionnelles
        """
        documents = []

        # Weaviate
        if self.weaviate_core:
            try:
                logger.info("📊 Extraction documents Weaviate...")

                # Fetch all documents (simplified, adapt to your WeaviateCore API)
                # Assuming a method like fetch_all_documents exists or using search
                weaviate_docs = await self._fetch_weaviate_documents()

                for doc in weaviate_docs:
                    content = doc.get("content", "")
                    if content.strip():
                        documents.append(
                            {
                                "content": content,
                                "source": "weaviate",
                                "metadata": doc.get("metadata", {}),
                            }
                        )

                logger.info(f"   ✅ {len(weaviate_docs)} documents Weaviate")

            except Exception as e:
                logger.error(f"   ❌ Erreur extraction Weaviate: {e}")

        # PostgreSQL
        if self.postgresql_retriever:
            try:
                logger.info("📊 Extraction données PostgreSQL...")

                # Fetch performance standards
                postgresql_docs = await self._fetch_postgresql_documents()

                for doc in postgresql_docs:
                    content = doc.get("content", "")
                    if content.strip():
                        documents.append(
                            {
                                "content": content,
                                "source": "postgresql",
                                "metadata": doc.get("metadata", {}),
                            }
                        )

                logger.info(f"   ✅ {len(postgresql_docs)} documents PostgreSQL")

            except Exception as e:
                logger.error(f"   ❌ Erreur extraction PostgreSQL: {e}")

        logger.info(f"📊 Total documents: {len(documents)}")
        self.stats["total_documents"] = len(documents)

        return documents

    async def _fetch_weaviate_documents(self) -> List[Dict[str, Any]]:
        """
        Fetch documents from Weaviate.

        Returns:
            List of documents
        """
        # Simplified implementation - adapt based on WeaviateCore API
        try:
            # Example: Use search with broad query or iterate over collection
            # This is a placeholder - replace with actual implementation

            # Option 1: Use search with generic query
            results = await self.weaviate_core.hybrid_search(
                query="poultry chicken broiler layer nutrition performance",
                top_k=500,  # Fetch large batch
            )

            return results

        except Exception as e:
            logger.error(f"Erreur fetch Weaviate: {e}")
            return []

    async def _fetch_postgresql_documents(self) -> List[Dict[str, Any]]:
        """
        Fetch documents from PostgreSQL.

        Returns:
            List of documents (formatted as text)
        """
        try:
            # Fetch all performance standards as documents
            # This is a placeholder - adapt based on PostgreSQLRetriever API

            # Example: Get all breeds and their performance data
            documents = []

            # Placeholder - replace with actual query
            # breeds = await self.postgresql_retriever.get_all_breeds()
            # for breed in breeds:
            #     for age in range(1, 50):
            #         data = await self.postgresql_retriever.get_performance_data(breed, age)
            #         if data:
            #             content = self._format_postgresql_data(breed, age, data)
            #             documents.append({
            #                 "content": content,
            #                 "metadata": {"breed": breed, "age": age, "source": "postgresql"}
            #             })

            # Temporary mock for demonstration
            logger.warning(
                "⚠️ _fetch_postgresql_documents is placeholder - implement actual logic"
            )

            return documents

        except Exception as e:
            logger.error(f"Erreur fetch PostgreSQL: {e}")
            return []

    def _format_postgresql_data(self, breed: str, age: int, data: Dict) -> str:
        """
        Formate données PostgreSQL en texte pour embeddings.

        Args:
            breed: Nom de la génétique (ex: Ross 308)
            age: Âge en jours
            data: Données de performance

        Returns:
            Texte formaté
        """
        return f"""
{breed} Performance Standards at {age} days:
- Body Weight (males): {data.get('body_weight_male', 'N/A')}g
- Body Weight (females): {data.get('body_weight_female', 'N/A')}g
- FCR: {data.get('fcr', 'N/A')}
- Daily Gain: {data.get('daily_gain', 'N/A')}g/day
- Cumulative Feed Intake: {data.get('feed_intake', 'N/A')}g
- Mortality: {data.get('mortality', 'N/A')}%
""".strip()

    async def generate_queries_for_document(
        self, document_content: str, num_queries: int = 3
    ) -> List[str]:
        """
        Génère questions représentatives pour un document (via LLM).

        Args:
            document_content: Contenu du document
            num_queries: Nombre de questions à générer

        Returns:
            Liste de questions
        """
        # Prompt pour générer questions
        system_prompt = """You are an expert in poultry farming and aviculture.
Generate specific, technical questions that this document would answer.

Requirements:
- Questions MUST be in French
- Questions should be specific and technical
- Questions should match real user queries
- Include breed names, ages, metrics (FCR, weight, etc.)
- Vary question types: factual, comparative, quantitative

Example good questions:
- "Quel est le poids cible pour des mâles Ross 308 à 35 jours?"
- "Quel FCR est attendu pour Cobb 500 à 42 jours?"
- "Quelle température optimale pour poussins jour 1?"

Return ONLY the questions, one per line, numbered 1., 2., 3., etc."""

        user_prompt = f"""Document:
{document_content[:1000]}  # Limit to 1000 chars to avoid token limits

Generate {num_queries} technical questions in French that this document would answer."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper model for generation
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            )

            # Parse questions
            content = response.choices[0].message.content
            questions = []

            for line in content.split("\n"):
                line = line.strip()
                # Remove numbering (1., 2., etc.)
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove prefix
                    question = line.lstrip("0123456789.-) ").strip()
                    if question and question.endswith("?"):
                        questions.append(question)

            # Validate
            if len(questions) < num_queries:
                logger.warning(
                    f"⚠️ Seulement {len(questions)} questions générées "
                    f"(attendu {num_queries})"
                )

            return questions[:num_queries]

        except Exception as e:
            logger.error(f"❌ Erreur génération questions: {e}")
            return []

    async def generate_dataset(self) -> List[Dict[str, Any]]:
        """
        Génère le dataset complet de paires (query, positive).

        Returns:
            Liste de paires
        """
        self.stats["start_time"] = datetime.now()

        # Fetch documents
        documents = await self.fetch_documents()

        if not documents:
            logger.error("❌ Aucun document disponible")
            return []

        # Calculer nombre de documents requis
        docs_needed = self.target_pairs // self.queries_per_doc + 1

        logger.info(
            f"🎯 Objectif: {self.target_pairs} paires "
            f"({docs_needed} documents × {self.queries_per_doc} questions)"
        )

        # Limiter documents si trop nombreux
        if len(documents) > docs_needed:
            logger.info(f"   Limitation à {docs_needed} premiers documents")
            documents = documents[:docs_needed]

        # Générer questions pour chaque document
        for i, doc in enumerate(documents, 1):
            logger.info(f"📝 [{i}/{len(documents)}] Génération questions...")

            # Générer questions
            queries = await self.generate_queries_for_document(
                document_content=doc["content"], num_queries=self.queries_per_doc
            )

            if not queries:
                self.stats["failed"] += 1
                continue

            # Créer paires (query, positive)
            for query in queries:
                self.pairs.append(
                    {
                        "query": query,
                        "positive": doc["content"],
                        "source": doc["source"],
                        "metadata": doc.get("metadata", {}),
                    }
                )

                self.stats["queries_generated"] += 1

            # Stop si objectif atteint
            if len(self.pairs) >= self.target_pairs:
                logger.info(f"   ✅ Objectif atteint: {len(self.pairs)} paires")
                break

            # Pause pour éviter rate limiting
            await asyncio.sleep(0.5)

        self.stats["end_time"] = datetime.now()

        logger.info(f"✅ {len(self.pairs)} paires générées")

        return self.pairs

    def save_dataset(self, output_path: str):
        """
        Sauvegarde le dataset au format JSON.

        Args:
            output_path: Chemin fichier de sortie
        """
        try:
            output_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_pairs": len(self.pairs),
                    "queries_per_doc": self.queries_per_doc,
                    "stats": self.stats,
                },
                "pairs": self.pairs,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Dataset sauvegardé: {output_path}")

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {e}")
            raise

    def print_summary(self):
        """Affiche résumé de génération"""
        duration = (
            (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            if self.stats["end_time"] and self.stats["start_time"]
            else 0
        )

        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ GÉNÉRATION DATASET")
        print("=" * 70)
        print(f"Documents traités:    {self.stats['total_documents']}")
        print(f"Questions générées:   {self.stats['queries_generated']}")
        print(f"Paires créées:        {len(self.pairs)}")
        print(f"Échecs:               {self.stats['failed']}")
        print(f"Durée:                {duration:.1f}s ({duration/60:.1f} min)")
        print("=" * 70)

    async def close(self):
        """Fermeture propre des clients"""
        if self.weaviate_core:
            try:
                await self.weaviate_core.close()
            except Exception as e:
                logger.warning(f"⚠️ Erreur fermeture Weaviate: {e}")

        if self.postgresql_retriever:
            try:
                await self.postgresql_retriever.close()
            except Exception as e:
                logger.warning(f"⚠️ Erreur fermeture PostgreSQL: {e}")

        if self.openai_client:
            try:
                await self.openai_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Erreur fermeture OpenAI: {e}")


async def main():
    """Point d'entrée principal"""

    # Parser arguments
    parser = argparse.ArgumentParser(
        description="Générer dataset fine-tuning embeddings avicoles"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Nombre de paires cibles (défaut: 1000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/finetuning_dataset_raw.json",
        help="Chemin fichier sortie",
    )
    parser.add_argument(
        "--queries-per-doc",
        type=int,
        default=3,
        help="Questions générées par document (défaut: 3)",
    )

    args = parser.parse_args()

    # Vérifier OPENAI_API_KEY
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY non configurée")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🚀 GÉNÉRATION DATASET FINE-TUNING")
    logger.info("=" * 70)

    # Créer générateur
    generator = FineTuningDatasetGenerator(
        target_pairs=args.target, queries_per_doc=args.queries_per_doc
    )

    try:
        # Initialiser
        await generator.initialize()

        # Générer dataset
        pairs = await generator.generate_dataset()

        if not pairs:
            logger.error("❌ Aucune paire générée")
            sys.exit(1)

        # Sauvegarder
        generator.save_dataset(args.output)

        # Résumé
        generator.print_summary()

        logger.info("✅ Génération terminée avec succès")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Génération interrompue par l'utilisateur")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        await generator.close()


if __name__ == "__main__":
    # Compatibilité Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
