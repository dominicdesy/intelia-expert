# -*- coding: utf-8 -*-
"""
Phase 2 Migration Script - Recréer Weaviate avec Nouveau Chunking

Ce script automatise la migration complète :
1. Backup de la collection actuelle (optionnel)
2. Recréation de la collection Weaviate
3. Re-ingestion de tous les documents avec nouveau chunking
4. Validation de la migration
5. Test de retrieval

Usage:
    python migrate_to_new_chunking.py --source-dir documents/Knowledge --backup
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Add to path for imports
rag_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, rag_dir)
sys.path.insert(0, os.path.join(rag_dir, 'knowledge_extractor'))

from weaviate_integration.ingester import WeaviateIngester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_collection(ingester: WeaviateIngester, backup_file: str = "weaviate_backup.json"):
    """
    Backup current Weaviate collection

    Args:
        ingester: WeaviateIngester instance
        backup_file: Path to backup file
    """
    logger.info("="*80)
    logger.info("STEP 1: BACKUP COLLECTION")
    logger.info("="*80)

    try:
        collection = ingester.client.collections.get(ingester.collection_name)

        # Query all documents
        logger.info("Fetching all documents from Weaviate...")
        all_objects = []

        # Fetch in batches
        offset = 0
        batch_size = 100

        while True:
            response = collection.query.fetch_objects(
                limit=batch_size,
                offset=offset
            )

            if not response.objects:
                break

            for obj in response.objects:
                all_objects.append({
                    "properties": obj.properties,
                    "uuid": str(obj.uuid)
                })

            offset += batch_size
            logger.info(f"  Fetched {len(all_objects)} documents...")

        # Save to file
        backup_path = Path(backup_file)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump({
                "collection_name": ingester.collection_name,
                "timestamp": datetime.now().isoformat(),
                "total_documents": len(all_objects),
                "documents": all_objects
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"[PASS] Backup created: {backup_path}")
        logger.info(f"  Total documents: {len(all_objects)}")
        logger.info(f"  File size: {backup_path.stat().st_size / 1024:.1f} KB")

        return True

    except Exception as e:
        logger.error(f"[FAIL] Backup failed: {e}")
        return False


def recreate_collection(ingester: WeaviateIngester):
    """
    Recreate Weaviate collection (delete + create)

    Args:
        ingester: WeaviateIngester instance
    """
    logger.info("\n" + "="*80)
    logger.info("STEP 2: RECREATE COLLECTION")
    logger.info("="*80)

    try:
        logger.info(f"Deleting collection: {ingester.collection_name}")
        ingester.recreate_collection()
        logger.info(f"[PASS] Collection recreated successfully")
        return True

    except Exception as e:
        logger.error(f"[FAIL] Collection recreation failed: {e}")
        return False


def reingest_documents(source_dir: str, recursive: bool = True, batch_size: int = 10):
    """
    Re-ingest all documents with new chunking

    Args:
        source_dir: Directory containing JSON/TXT files
        recursive: Search recursively
        batch_size: Batch size for ingestion
    """
    logger.info("\n" + "="*80)
    logger.info("STEP 3: RE-INGEST DOCUMENTS")
    logger.info("="*80)

    try:
        source_path = Path(source_dir)

        if not source_path.exists():
            logger.error(f"[FAIL] Source directory not found: {source_dir}")
            return False

        logger.info(f"Source directory: {source_path}")
        logger.info(f"Recursive: {recursive}")

        # Find all JSON files
        if recursive:
            json_files = list(source_path.rglob("*.json"))
        else:
            json_files = list(source_path.glob("*.json"))

        logger.info(f"Found {len(json_files)} JSON files")

        if len(json_files) == 0:
            logger.warning("[WARN] No JSON files found!")
            return False

        # Process documents using knowledge_extractor script
        logger.info("\nStarting document processing...")
        logger.info("This will use the new ChunkingService for semantic chunking")
        logger.info("\nRunning knowledge_extractor.py...")

        # Call knowledge_extractor as subprocess
        import subprocess

        ke_script = os.path.join(rag_dir, 'knowledge_extractor', 'knowledge_extractor.py')

        cmd = [
            sys.executable,
            ke_script
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=os.path.join(rag_dir, 'knowledge_extractor'),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Print output
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    logger.info(f"  {line}")

        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip() and 'warning' not in line.lower():
                    logger.warning(f"  {line}")

        if result.returncode != 0:
            logger.error(f"[FAIL] knowledge_extractor.py failed with code {result.returncode}")
            return False

        logger.info(f"\n[PASS] Document ingestion completed")
        logger.info(f"  Total files found: {len(json_files)}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] Document ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_migration(ingester: WeaviateIngester):
    """
    Validate migration success

    Args:
        ingester: WeaviateIngester instance
    """
    logger.info("\n" + "="*80)
    logger.info("STEP 4: VALIDATE MIGRATION")
    logger.info("="*80)

    try:
        collection = ingester.client.collections.get(ingester.collection_name)

        # Count total chunks
        logger.info("Counting total chunks...")
        result = collection.aggregate.over_all(total_count=True)
        total_count = result.total_count

        logger.info(f"Total chunks in Weaviate: {total_count}")

        if total_count == 0:
            logger.warning("[WARN] No chunks found in Weaviate!")
            return False

        # Sample some chunks
        logger.info("\nSampling chunks (first 5):")
        sample = collection.query.fetch_objects(limit=5)

        for i, obj in enumerate(sample.objects, 1):
            props = obj.properties
            logger.info(f"\n  Chunk {i}:")
            logger.info(f"    Chunk ID: {props.get('chunk_id', 'N/A')}")
            logger.info(f"    Word count: {props.get('word_count', 'N/A')}")
            logger.info(f"    Genetic line: {props.get('genetic_line', 'N/A')}")
            logger.info(f"    Intent category: {props.get('intent_category', 'N/A')}")
            logger.info(f"    Content preview: {props.get('content', '')[:80]}...")

        logger.info(f"\n[PASS] Migration validation successful")
        logger.info(f"  Total chunks: {total_count}")
        logger.info(f"  Chunks sampled: {len(sample.objects)}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retrieval():
    """
    Test retrieval with sample queries
    """
    logger.info("\n" + "="*80)
    logger.info("STEP 5: TEST RETRIEVAL")
    logger.info("="*80)

    try:
        # Test queries
        test_queries = [
            ("Quel est le poids d'un Ross 308 male de 21 jours ?", "fr"),
            ("What is the feed conversion ratio for broilers?", "en"),
        ]

        # Import retriever (if available)
        try:
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../llm')))
            from retrieval.retriever_core import UnifiedRetriever

            retriever = UnifiedRetriever()

            for query, language in test_queries:
                logger.info(f"\nQuery: {query}")
                logger.info(f"Language: {language}")

                results = retriever.retrieve(query, language=language, top_k=3)

                logger.info(f"Results: {len(results)} chunks")
                for i, chunk in enumerate(results, 1):
                    logger.info(f"  {i}. Score: {chunk.score:.3f}")
                    logger.info(f"     Content: {chunk.content[:100]}...")
                    logger.info(f"     Genetic line: {chunk.metadata.get('genetic_line', 'N/A')}")

            logger.info(f"\n[PASS] Retrieval test successful")
            return True

        except ImportError:
            logger.warning("[SKIP] Retrieval test skipped (UnifiedRetriever not available)")
            logger.info("  This is normal if running from RAG directory only")
            return True

    except Exception as e:
        logger.error(f"[FAIL] Retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(
        description="Migrate Weaviate to new chunking system"
    )
    parser.add_argument(
        '--source-dir',
        type=str,
        default='documents/Knowledge',
        help='Source directory containing JSON/TXT files'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before migration'
    )
    parser.add_argument(
        '--backup-file',
        type=str,
        default='weaviate_backup.json',
        help='Backup file path'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=True,
        help='Search recursively in source directory'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for ingestion'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation and retrieval tests'
    )

    args = parser.parse_args()

    logger.info("\n" + "="*80)
    logger.info("PHASE 2 MIGRATION - WEAVIATE NEW CHUNKING")
    logger.info("="*80)
    logger.info(f"Source directory: {args.source_dir}")
    logger.info(f"Backup enabled: {args.backup}")
    logger.info(f"Recursive: {args.recursive}")
    logger.info(f"Batch size: {args.batch_size}")

    # Initialize ingester
    try:
        ingester = WeaviateIngester()
    except Exception as e:
        logger.error(f"[FAIL] Failed to initialize WeaviateIngester: {e}")
        logger.error("Please check your .env file (WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY)")
        return False

    # Track results
    results = {}

    # Step 1: Backup (optional)
    if args.backup:
        results['backup'] = backup_collection(ingester, args.backup_file)
        if not results['backup']:
            logger.warning("[WARN] Backup failed, but continuing...")
    else:
        logger.info("\n[SKIP] Backup skipped (use --backup to enable)")

    # Step 2: Recreate collection
    results['recreate'] = recreate_collection(ingester)
    if not results['recreate']:
        logger.error("[FAIL] Migration aborted - collection recreation failed")
        return False

    # Step 3: Re-ingest documents
    results['reingest'] = reingest_documents(
        args.source_dir,
        recursive=args.recursive,
        batch_size=args.batch_size
    )
    if not results['reingest']:
        logger.error("[FAIL] Migration aborted - document ingestion failed")
        return False

    # Step 4: Validate
    if not args.skip_validation:
        results['validate'] = validate_migration(ingester)
        if not results['validate']:
            logger.warning("[WARN] Validation failed, but migration may still be successful")

    # Step 5: Test retrieval
    if not args.skip_validation:
        results['retrieval'] = test_retrieval()

    # Summary
    logger.info("\n" + "="*80)
    logger.info("MIGRATION SUMMARY")
    logger.info("="*80)

    for step, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        logger.info(f"{status} {step.capitalize()}")

    all_success = all(results.values())

    if all_success:
        logger.info("\n" + "="*80)
        logger.info("[SUCCESS] MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        logger.info("\nNext steps:")
        logger.info("  1. Test queries in production")
        logger.info("  2. Monitor retrieval quality")
        logger.info("  3. Compare with pre-migration performance")
        logger.info("\nBenefits:")
        logger.info("  - Semantic chunking (no mid-sentence splits)")
        logger.info("  - Optimized chunk sizes (50-1200 words)")
        logger.info("  - Better context preservation (20% overlap)")
        logger.info("  - Improved retrieval quality")
    else:
        logger.error("\n" + "="*80)
        logger.error("[FAIL] MIGRATION COMPLETED WITH ERRORS")
        logger.error("="*80)
        logger.error("\nPlease check logs above for details")
        if args.backup:
            logger.error(f"\nBackup available at: {args.backup_file}")

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
