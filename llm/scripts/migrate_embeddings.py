#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_embeddings.py - Migration vers text-embedding-3-large

Re-vectorise tous les documents existants avec le nouveau modèle d'embedding.
Supporte les dimensions réduites (1536) et complètes (3072).

Usage:
    python scripts/migrate_embeddings.py [--dry-run] [--batch-size 100] [--collection COLLECTION]

Options:
    --dry-run         Simulation sans modification (compte uniquement)
    --batch-size N    Nombre de documents par batch (défaut: 100)
    --collection C    Nom de la collection Weaviate (défaut: Documents)
    --dimensions D    Dimensions vecteurs (1536 ou 3072, défaut: 1536)
    --skip-cache      Ne pas utiliser le cache Redis
"""

import asyncio
import os
import sys
import logging
import argparse
import time
from pathlib import Path

# Ajouter le répertoire parent au path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports après path setup
from utils.imports_and_dependencies import AsyncOpenAI
from retrieval.embedder import OpenAIEmbedder
from utils.types import List, Dict, Any

# Créer logs directory AVANT logging config
os.makedirs("logs", exist_ok=True)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/migration_embeddings.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


class EmbeddingMigrator:
    """Gestionnaire de migration des embeddings"""

    def __init__(
        self,
        collection_name: str = "Documents",
        batch_size: int = 100,
        dimensions: int = 1536,
        dry_run: bool = False,
        skip_cache: bool = False,
    ):
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.dimensions = dimensions
        self.dry_run = dry_run
        self.skip_cache = skip_cache

        # Clients
        self.openai_client = None
        self.weaviate_client = None
        self.embedder = None

        # Stats
        self.stats = {
            "total_documents": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
        }

    async def initialize(self):
        """Initialise les clients"""
        logger.info("🔧 Initialisation des clients...")

        # OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY non configurée")

        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        logger.info("✅ Client OpenAI initialisé")

        # Embedder (sans cache si --skip-cache)
        cache_manager = None
        if not self.skip_cache:
            try:
                from cache.cache_manager import CacheManager

                cache_manager = CacheManager()
                await cache_manager.initialize()
                logger.info("✅ Cache manager activé")
            except Exception as e:
                logger.warning(f"⚠️ Cache non disponible: {e}")

        # Vérifier modèle configuré
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
        logger.info(f"📊 Modèle d'embedding: {embedding_model}")
        logger.info(f"📊 Dimensions cibles: {self.dimensions}")

        self.embedder = OpenAIEmbedder(
            client=self.openai_client,
            cache_manager=cache_manager,
            model=embedding_model,
        )
        logger.info(f"✅ Embedder initialisé avec {embedding_model}")

        # Weaviate
        await self._connect_weaviate()

    async def _connect_weaviate(self):
        """Connexion Weaviate"""
        try:
            import weaviate
            import weaviate.classes as wvc_classes

            weaviate_url = os.getenv(
                "WEAVIATE_URL",
                "https://xmlc4jvtu6hfw9zrrmnw.c0.us-east1.gcp.weaviate.cloud",
            )
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY", "")
            openai_api_key = os.getenv("OPENAI_API_KEY", "")

            logger.info(f"🔌 Connexion Weaviate: {weaviate_url}")

            # Définir OPENAI_APIKEY pour Weaviate
            if openai_api_key and "OPENAI_APIKEY" not in os.environ:
                os.environ["OPENAI_APIKEY"] = openai_api_key

            # Connexion cloud
            if "weaviate.cloud" in weaviate_url:
                headers = {}
                if openai_api_key:
                    headers["X-OpenAI-Api-Key"] = openai_api_key

                self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=weaviate_url,
                    auth_credentials=wvc_classes.init.Auth.api_key(weaviate_api_key),
                    headers=headers,
                )
            else:
                # Connexion locale
                host = weaviate_url.replace("http://", "").replace("https://", "")
                self.weaviate_client = weaviate.connect_to_local(host=host)

            # Test connexion
            if self.weaviate_client and self.weaviate_client.is_ready():
                logger.info(f"✅ Weaviate connecté: {weaviate_url}")
            else:
                raise Exception("Weaviate non prêt")

        except Exception as e:
            logger.error(f"❌ Erreur connexion Weaviate: {e}")
            raise

    async def count_documents(self) -> int:
        """Compte le nombre total de documents"""
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)

            # Compter avec aggregate
            result = collection.aggregate.over_all(total_count=True)
            count = result.total_count

            logger.info(f"📊 Documents trouvés: {count}")
            return count

        except Exception as e:
            logger.error(f"❌ Erreur comptage documents: {e}")
            return 0

    async def fetch_documents_batch(
        self, offset: int, limit: int
    ) -> List[Dict[str, Any]]:
        """Récupère un batch de documents"""
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)

            # Fetch avec pagination
            results = collection.query.fetch_objects(
                limit=limit,
                offset=offset,
                include_vector=False,  # On ne récupère pas les vecteurs existants
            )

            documents = []
            for obj in results.objects:
                # Extraire propriétés
                doc = {
                    "id": str(obj.uuid),
                    "content": obj.properties.get("content", ""),
                    "metadata": {
                        k: v for k, v in obj.properties.items() if k != "content"
                    },
                }
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"❌ Erreur fetch batch (offset={offset}): {e}")
            return []

    async def update_document_vector(
        self, doc_id: str, new_vector: List[float]
    ) -> bool:
        """Met à jour le vecteur d'un document"""
        try:
            if self.dry_run:
                return True  # Simulation

            collection = self.weaviate_client.collections.get(self.collection_name)

            # Update uniquement le vecteur
            collection.data.update(uuid=doc_id, vector=new_vector)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur update vecteur {doc_id}: {e}")
            return False

    async def migrate_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Migre un batch de documents"""
        stats = {"success": 0, "failed": 0}

        try:
            # Extraire textes
            texts = [doc.get("content", "") for doc in documents]

            # Filtrer textes vides
            valid_docs = [
                (i, doc) for i, doc in enumerate(documents) if texts[i].strip()
            ]
            if not valid_docs:
                logger.warning("⚠️ Batch vide (tous textes vides)")
                stats["failed"] = len(documents)
                return stats

            valid_texts = [texts[i] for i, _ in valid_docs]

            # Générer nouveaux embeddings (batch)
            logger.debug(
                f"   Génération embeddings pour {len(valid_texts)} documents..."
            )

            try:
                # Appel direct API OpenAI avec dimensions
                response = await self.openai_client.embeddings.create(
                    model=self.embedder.model,
                    input=valid_texts,
                    encoding_format="float",
                    dimensions=self.dimensions,  # Force dimensions
                )

                if not response or not response.data:
                    logger.error("❌ Réponse embeddings vide")
                    stats["failed"] = len(documents)
                    return stats

                new_embeddings = [item.embedding for item in response.data]

            except Exception as emb_error:
                logger.error(f"❌ Erreur génération embeddings: {emb_error}")
                stats["failed"] = len(documents)
                return stats

            # Mettre à jour les documents
            for (i, doc), new_vector in zip(valid_docs, new_embeddings):
                doc_id = doc["id"]

                # Vérifier dimensions
                if len(new_vector) != self.dimensions:
                    logger.warning(
                        f"⚠️ Dimension mismatch {doc_id}: "
                        f"attendu {self.dimensions}, reçu {len(new_vector)}"
                    )
                    stats["failed"] += 1
                    continue

                # Update vecteur
                success = await self.update_document_vector(doc_id, new_vector)

                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

        except Exception as e:
            logger.error(f"❌ Erreur migration batch: {e}")
            stats["failed"] = len(documents)

        return stats

    async def migrate_all(self):
        """Migration complète de tous les documents"""
        self.stats["start_time"] = time.time()

        try:
            # Compter documents
            total = await self.count_documents()
            self.stats["total_documents"] = total

            if total == 0:
                logger.warning("⚠️ Aucun document à migrer")
                return

            if self.dry_run:
                logger.info(f"🔍 DRY RUN: {total} documents seraient migrés")
                return

            logger.info(f"🚀 Début migration de {total} documents...")
            logger.info(f"   Batch size: {self.batch_size}")
            logger.info(f"   Dimensions: {self.dimensions}")
            logger.info(f"   Modèle: {self.embedder.model}")

            # Migration par batches
            offset = 0
            batch_num = 0

            while offset < total:
                batch_num += 1
                batch_size = min(self.batch_size, total - offset)

                logger.info(
                    f"📦 Batch {batch_num} (documents {offset+1}-{offset+batch_size}/{total})..."
                )

                # Fetch batch
                documents = await self.fetch_documents_batch(offset, batch_size)

                if not documents:
                    logger.warning(f"⚠️ Batch {batch_num} vide, skip")
                    offset += batch_size
                    continue

                # Migrer batch
                batch_stats = await self.migrate_batch(documents)

                # Stats
                self.stats["processed"] += batch_stats["success"]
                self.stats["failed"] += batch_stats["failed"]

                # Progress
                progress = (offset + batch_size) / total * 100
                elapsed = time.time() - self.stats["start_time"]
                rate = (offset + batch_size) / elapsed if elapsed > 0 else 0
                eta = (total - (offset + batch_size)) / rate if rate > 0 else 0

                logger.info(
                    f"   ✅ Success: {batch_stats['success']}, "
                    f"❌ Failed: {batch_stats['failed']}"
                )
                logger.info(
                    f"   📊 Progress: {progress:.1f}% "
                    f"({offset+batch_size}/{total}) - "
                    f"Rate: {rate:.1f} docs/s - "
                    f"ETA: {eta/60:.1f} min"
                )

                offset += batch_size

                # Pause pour éviter rate limiting
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Erreur migration: {e}")
            raise

        finally:
            self.stats["end_time"] = time.time()
            await self._print_summary()

    async def _print_summary(self):
        """Affiche le résumé de migration"""
        duration = (
            self.stats["end_time"] - self.stats["start_time"]
            if self.stats["end_time"] and self.stats["start_time"]
            else 0
        )

        logger.info("\n" + "=" * 70)
        logger.info("📊 RÉSUMÉ MIGRATION")
        logger.info("=" * 70)
        logger.info(f"Collection:       {self.collection_name}")
        logger.info(f"Modèle:           {self.embedder.model}")
        logger.info(f"Dimensions:       {self.dimensions}")
        logger.info(f"Mode:             {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info("")
        logger.info(f"Documents total:  {self.stats['total_documents']}")
        logger.info(f"✅ Traités:        {self.stats['processed']}")
        logger.info(f"❌ Échecs:         {self.stats['failed']}")
        logger.info(f"⏭️ Skipped:         {self.stats['skipped']}")
        logger.info("")
        logger.info(f"Durée:            {duration:.1f}s ({duration/60:.1f} min)")
        logger.info(
            f"Rate:             {self.stats['processed']/duration if duration > 0 else 0:.1f} docs/s"
        )
        logger.info("=" * 70)

        if self.stats["failed"] > 0:
            logger.warning(f"⚠️ {self.stats['failed']} documents ont échoué")
        else:
            logger.info("🎉 Migration terminée avec succès!")

    async def close(self):
        """Fermeture propre"""
        if self.weaviate_client:
            try:
                self.weaviate_client.close()
                logger.info("✅ Weaviate fermé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur fermeture Weaviate: {e}")

        if self.openai_client:
            try:
                await self.openai_client.close()
                logger.info("✅ OpenAI fermé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur fermeture OpenAI: {e}")


async def main():
    """Point d'entrée principal"""
    # Parser arguments
    parser = argparse.ArgumentParser(
        description="Migrer les embeddings vers text-embedding-3-large"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulation sans modification"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Nombre de documents par batch (défaut: 100)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="Documents",
        help="Nom de la collection Weaviate (défaut: Documents)",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=1536,
        choices=[1536, 3072],
        help="Dimensions vecteurs (1536 ou 3072, défaut: 1536)",
    )
    parser.add_argument(
        "--skip-cache", action="store_true", help="Ne pas utiliser le cache Redis"
    )

    args = parser.parse_args()

    # Créer logs directory
    os.makedirs("logs", exist_ok=True)

    # Vérifier variables d'environnement critiques
    required_vars = ["OPENAI_API_KEY", "WEAVIATE_URL", "WEAVIATE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"❌ Variables d'environnement manquantes: {', '.join(missing_vars)}"
        )
        sys.exit(1)

    # Vérifier modèle configuré
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
    if embedding_model == "text-embedding-ada-002":
        logger.warning(
            "⚠️ OPENAI_EMBEDDING_MODEL est toujours text-embedding-ada-002\n"
            "   Voulez-vous vraiment migrer vers le même modèle?\n"
            "   Pour utiliser text-embedding-3-large, configurez:\n"
            "   export OPENAI_EMBEDDING_MODEL=text-embedding-3-large"
        )
        response = input("   Continuer quand même? (y/N): ")
        if response.lower() != "y":
            logger.info("Migration annulée")
            sys.exit(0)

    # Créer migrator
    migrator = EmbeddingMigrator(
        collection_name=args.collection,
        batch_size=args.batch_size,
        dimensions=args.dimensions,
        dry_run=args.dry_run,
        skip_cache=args.skip_cache,
    )

    try:
        # Initialiser
        await migrator.initialize()

        # Migrer
        await migrator.migrate_all()

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Migration interrompue par l'utilisateur")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        await migrator.close()


if __name__ == "__main__":
    # Compatibilité Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
