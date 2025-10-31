# -*- coding: utf-8 -*-
"""
Batch Extraction AND Ingestion - All 54 PDFs
Extracts with FREE pdfplumber + ingests into Weaviate InteliaKnowledge

Features:
- FREE PDF extraction (0$ cost)
- Quality scoring (5 metrics)
- Entity extraction (breeds, diseases, medications)
- Direct ingestion to InteliaKnowledge collection
- Progress tracking
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import weaviate
from weaviate.classes.data import DataObject

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

# Import pipeline
from multi_format_pipeline import MultiFormatPipeline

# Weaviate connection
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY]):
    print("ERROR: Missing required environment variables")
    print(f"  WEAVIATE_URL: {'OK' if WEAVIATE_URL else 'MISSING'}")
    print(f"  WEAVIATE_API_KEY: {'OK' if WEAVIATE_API_KEY else 'MISSING'}")
    print(f"  OPENAI_API_KEY: {'OK' if OPENAI_API_KEY else 'MISSING'}")
    sys.exit(1)


def connect_to_weaviate():
    """Connect to Weaviate"""
    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY),
            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY}
        )
        if client.is_ready():
            return client
        else:
            print("ERROR: Weaviate client not ready")
            return None
    except Exception as e:
        print(f"ERROR connecting to Weaviate: {e}")
        return None


def ingest_chunks_to_weaviate(client, chunks_with_metadata: List[Dict[str, Any]]) -> int:
    """
    Ingest chunks into Weaviate InteliaKnowledge collection

    Args:
        client: Weaviate client
        chunks_with_metadata: List of chunk dictionaries with all metadata

    Returns:
        Number of chunks successfully ingested
    """
    try:
        collection = client.collections.get("InteliaKnowledge")

        # Batch insert
        ingested_count = 0
        with collection.batch.dynamic() as batch:
            for chunk_data in chunks_with_metadata:
                try:
                    # Weaviate will automatically vectorize the content field
                    batch.add_object(properties=chunk_data)
                    ingested_count += 1
                except Exception as e:
                    print(f"    Warning: Failed to add chunk {chunk_data.get('chunk_index', '?')}: {e}")
                    continue

        return ingested_count

    except Exception as e:
        print(f"    ERROR during ingestion: {e}")
        return 0


def main():
    """Main execution"""
    print("="*80)
    print("BATCH EXTRACTION + INGESTION - All PDFs")
    print("FREE pdfplumber + Quality Scoring + Entity Extraction + Weaviate")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize pipeline
    print("Initializing extraction pipeline...")
    pipeline = MultiFormatPipeline()
    print()

    # Connect to Weaviate
    print("Connecting to Weaviate InteliaKnowledge...")
    weaviate_client = connect_to_weaviate()
    if not weaviate_client:
        print("FAILED: Could not connect to Weaviate")
        sys.exit(1)
    print("Connected successfully!")
    print()

    # Find all PDFs
    base_path = Path("C:/Software_Development/intelia-cognito/knowledge-ingesters")
    sources_path = base_path / "Sources/intelia/public"

    if not sources_path.exists():
        print(f"ERROR: Sources directory not found: {sources_path}")
        sys.exit(1)

    pdf_files = list(sources_path.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files to process")
    print()

    # Statistics
    total_files = len(pdf_files)
    success_count = 0
    error_count = 0
    total_chunks_created = 0
    total_chunks_ingested = 0
    start_time = datetime.now()

    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        pdf_name = pdf_path.name
        relative_path = pdf_path.relative_to(base_path)

        print(f"\n[{i}/{total_files}] {pdf_name}")
        print("-" * 80)

        try:
            # Step 1: Extract with pipeline (includes quality scoring + entities)
            result = pipeline.process_file(str(pdf_path))

            if not result.success:
                print(f"  ERROR: Extraction failed - {result.error}")
                error_count += 1
                continue

            print(f"  Extraction: SUCCESS ({result.chunks_created} chunks created)")
            total_chunks_created += result.chunks_created

            # Step 2: Ingest to Weaviate
            if result.chunks_with_metadata:
                print(f"  Ingesting {len(result.chunks_with_metadata)} chunks to Weaviate...")

                ingested = ingest_chunks_to_weaviate(
                    weaviate_client,
                    result.chunks_with_metadata
                )

                if ingested > 0:
                    print(f"  Ingestion: SUCCESS ({ingested} chunks ingested)")
                    total_chunks_ingested += ingested
                    success_count += 1
                else:
                    print(f"  Ingestion: FAILED (0 chunks ingested)")
                    error_count += 1
            else:
                print(f"  Ingestion: SKIP (no chunks to ingest)")
                error_count += 1

        except Exception as e:
            print(f"  EXCEPTION: {str(e)[:200]}")
            error_count += 1

    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*80)
    print("BATCH PROCESSING COMPLETE")
    print("="*80)
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print()
    print(f"Files processed: {total_files}")
    print(f"Success: {success_count}/{total_files} ({success_count/total_files*100:.1f}%)")
    print(f"Errors: {error_count}/{total_files}")
    print()
    print(f"Total chunks created: {total_chunks_created}")
    print(f"Total chunks ingested: {total_chunks_ingested}")
    print()
    print(f"Collection: InteliaKnowledge")
    print(f"Weaviate URL: {WEAVIATE_URL}")
    print(f"Cost: 0$ (FREE pdfplumber)")
    print("="*80)

    # Close Weaviate connection
    weaviate_client.close()


if __name__ == "__main__":
    main()
