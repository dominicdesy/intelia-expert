# -*- coding: utf-8 -*-
"""
Script to recreate Weaviate collection with new schema v2 (quality scores + entities)

This script will:
1. Connect to Weaviate
2. List all existing collections
3. Delete old collection(s)
4. Create new KnowledgeChunks collection with schema v2
5. Provide report on changes

Usage:
    python recreate_weaviate_collection.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import weaviate
from weaviate.classes.config import Configure, Property, DataType

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Weaviate connection
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY]):
    print("ERROR: Missing required environment variables:")
    print(f"  WEAVIATE_URL: {'OK' if WEAVIATE_URL else 'MISSING'}")
    print(f"  WEAVIATE_API_KEY: {'OK' if WEAVIATE_API_KEY else 'MISSING'}")
    print(f"  OPENAI_API_KEY: {'OK' if OPENAI_API_KEY else 'MISSING'}")
    sys.exit(1)


def connect_to_weaviate():
    """Connect to Weaviate instance"""
    print("="*80)
    print("WEAVIATE CONNECTION")
    print("="*80)
    print(f"URL: {WEAVIATE_URL}")

    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY),
            headers={
                "X-OpenAI-Api-Key": OPENAI_API_KEY
            }
        )

        if client.is_ready():
            print("Status: CONNECTED")
            return client
        else:
            print("Status: FAILED - Client not ready")
            return None

    except Exception as e:
        print(f"Status: ERROR - {e}")
        return None


def list_collections(client):
    """List all existing collections"""
    print("\n" + "="*80)
    print("EXISTING COLLECTIONS")
    print("="*80)

    try:
        collections = client.collections.list_all()

        if not collections:
            print("No collections found")
            return []

        collection_names = []
        for name, collection in collections.items():
            print(f"\nCollection: {name}")

            # Get collection object count
            try:
                coll = client.collections.get(name)
                response = coll.aggregate.over_all(total_count=True)
                count = response.total_count if response.total_count else 0
                print(f"  Objects: {count}")
            except Exception as e:
                print(f"  Objects: Unable to count ({e})")

            collection_names.append(name)

        return collection_names

    except Exception as e:
        print(f"ERROR listing collections: {e}")
        return []


def delete_collection(client, collection_name):
    """Delete a collection"""
    print(f"\nDeleting collection: {collection_name}")

    try:
        client.collections.delete(collection_name)
        print(f"  Status: DELETED")
        return True
    except Exception as e:
        print(f"  Status: ERROR - {e}")
        return False


def create_knowledge_chunks_schema(client):
    """
    Create KnowledgeChunks collection with schema v2
    Includes: 60+ fields with quality scores and entity extraction
    """
    print("\n" + "="*80)
    print("CREATING NEW COLLECTION: KnowledgeChunks")
    print("="*80)

    properties = [
        # ============================================================
        # CONTENT (Vectorized)
        # ============================================================
        Property(
            name="content",
            data_type=DataType.TEXT,
            description="Main text content of the chunk (vectorized for semantic search)"
        ),

        # ============================================================
        # QUALITY SCORE FIELDS (NEW in v2.0)
        # ============================================================
        Property(
            name="quality_score",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Overall chunk quality score (0.0-1.0) - weighted average of 5 metrics"
        ),
        Property(
            name="info_density",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Information density score (0.0-1.0) - entity and number presence"
        ),
        Property(
            name="completeness",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Completeness score (0.0-1.0) - intro/conclusion detection"
        ),
        Property(
            name="semantic_coherence",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Semantic coherence score (0.0-1.0) - sentence variance and transitions"
        ),
        Property(
            name="structure_score",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Structure score (0.0-1.0) - lists, tables, headers presence"
        ),

        # ============================================================
        # ENTITY EXTRACTION FIELDS (NEW in v2.0)
        # ============================================================
        Property(
            name="breeds",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Extracted breed names (Ross 308, Cobb 500, Hy-Line Brown, etc.)"
        ),
        Property(
            name="diseases",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Extracted disease names (Newcastle, Gumboro, Coccidiosis, etc.)"
        ),
        Property(
            name="medications",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Extracted medication names (Amprolium, vaccines, antibiotics)"
        ),
        Property(
            name="has_performance_data",
            data_type=DataType.BOOL,
            skip_vectorization=True,
            description="Boolean: chunk contains performance metrics (FCR, weight, etc.)"
        ),
        Property(
            name="has_health_info",
            data_type=DataType.BOOL,
            skip_vectorization=True,
            description="Boolean: chunk contains health/disease information"
        ),
        Property(
            name="has_nutrition_info",
            data_type=DataType.BOOL,
            skip_vectorization=True,
            description="Boolean: chunk contains nutrition/feed information"
        ),
        Property(
            name="metrics",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="JSON string of extracted metrics with values (FCR, weight, mortality, etc.)"
        ),
        Property(
            name="age_ranges",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="JSON string of age ranges normalized to days"
        ),

        # ============================================================
        # PATH-BASED METADATA (70% - from directory structure)
        # ============================================================
        Property(
            name="owner_org_id",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Organization ID (intelia, client_abc, etc.) - PRIMARY FILTER"
        ),
        Property(
            name="visibility_level",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Visibility level: public_global, intelia_internal, org_internal, org_customer_facing"
        ),
        Property(
            name="site_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Site type: broiler_farms, layer_farms, breeding_farms, hatcheries, etc."
        ),
        Property(
            name="breed",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Breed/genetic line from path: ross_308, cobb_500, hy_line_brown, etc."
        ),
        Property(
            name="category",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document category: biosecurity, breed, housing, management, etc."
        ),
        Property(
            name="subcategory",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Subcategory: common, by_breed, by_climate, etc."
        ),
        Property(
            name="climate_zone",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Climate zone: tropical, temperate, cold"
        ),

        # ============================================================
        # VISION-BASED METADATA (25% - from document analysis)
        # ============================================================
        Property(
            name="species",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Poultry species: chicken, turkey, duck"
        ),
        Property(
            name="genetic_line",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Genetic line/brand: Ross, Cobb, Hy-Line, Lohmann, Hubbard"
        ),
        Property(
            name="company",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Company/breeder: Aviagen, Cobb-Vantress, Hy-Line, Lohmann"
        ),
        Property(
            name="document_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document type: technical_guide, performance_goals, management_handbook, etc."
        ),
        Property(
            name="production_stage",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Production stage: brooding, growing, laying, reproduction"
        ),
        Property(
            name="topics",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Main topics covered: vaccination, biosecurity, feeding, etc."
        ),

        # ============================================================
        # SMART DEFAULTS (5%)
        # ============================================================
        Property(
            name="language",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document language ISO code: en, fr, es, etc."
        ),
        Property(
            name="unit_system",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Unit system: metric, imperial, mixed"
        ),

        # ============================================================
        # DOCUMENT METADATA
        # ============================================================
        Property(
            name="title",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document title"
        ),
        Property(
            name="source",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Full source file path"
        ),
        Property(
            name="filename",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Source filename"
        ),
        Property(
            name="extraction_method",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Extraction method used: pdf_text (pdfplumber), docx, web_scrape, etc."
        ),
        Property(
            name="extraction_date",
            data_type=DataType.DATE,
            skip_vectorization=True,
            description="Date when document was extracted and ingested"
        ),
        Property(
            name="document_version",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document version if available"
        ),

        # ============================================================
        # CHUNK METADATA
        # ============================================================
        Property(
            name="chunk_index",
            data_type=DataType.INT,
            skip_vectorization=True,
            description="Chunk index in document (0-based)"
        ),
        Property(
            name="word_count",
            data_type=DataType.INT,
            skip_vectorization=True,
            description="Word count in chunk"
        ),
        Property(
            name="char_count",
            data_type=DataType.INT,
            skip_vectorization=True,
            description="Character count in chunk"
        ),
    ]

    try:
        # Create collection with OpenAI text-embedding-3-large
        client.collections.create(
            name="KnowledgeChunks",
            properties=properties,
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-large",
                dimensions=3072  # text-embedding-3-large uses 3072 dimensions
            ),
            description="Knowledge chunks with quality scoring and entity extraction (v2.0)"
        )

        print("Status: CREATED")
        print(f"Total properties: {len(properties)}")
        print("\nKey features:")
        print("  - Quality scoring (5 metrics)")
        print("  - Entity extraction (breeds, diseases, medications)")
        print("  - Path-based metadata (organization, site type, breed)")
        print("  - Vision-based metadata (species, genetic line, topics)")
        print("  - 60+ metadata fields for advanced filtering")
        print("\nVectorizer: text-embedding-3-large (3072 dimensions)")

        return True

    except Exception as e:
        print(f"Status: ERROR - {e}")
        return False


def main():
    """Main execution"""
    print("="*80)
    print("WEAVIATE COLLECTION RECREATION SCRIPT")
    print("v2.0.0 - Quality Scoring + Entity Extraction")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: Connect to Weaviate
    client = connect_to_weaviate()
    if not client:
        print("\nFAILED: Could not connect to Weaviate")
        sys.exit(1)

    # Step 2: List existing collections
    existing_collections = list_collections(client)

    # Step 3: Delete old collection(s)
    if existing_collections:
        print("\n" + "="*80)
        print("DELETING OLD COLLECTIONS")
        print("="*80)

        collections_to_delete = []
        for coll_name in existing_collections:
            if "knowledge" in coll_name.lower() or "intelia" in coll_name.lower():
                collections_to_delete.append(coll_name)

        if collections_to_delete:
            print(f"\nFound {len(collections_to_delete)} collection(s) to delete:")
            for coll_name in collections_to_delete:
                print(f"  - {coll_name}")

            print("\nProceed with deletion? (yes/no): ", end="")
            confirm = input().strip().lower()

            if confirm == "yes":
                for coll_name in collections_to_delete:
                    delete_collection(client, coll_name)
            else:
                print("Deletion cancelled")
                client.close()
                sys.exit(0)
        else:
            print("\nNo knowledge-related collections found to delete")

    # Step 4: Create new collection
    success = create_knowledge_chunks_schema(client)

    # Step 5: Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if success:
        print("Status: SUCCESS")
        print("\nNew collection 'KnowledgeChunks' created with:")
        print("  - 60+ metadata fields")
        print("  - Quality scoring system (5 metrics)")
        print("  - Entity extraction (breeds, diseases, medications)")
        print("  - text-embedding-3-large vectorizer (3072 dimensions)")
        print("\nNext steps:")
        print("  1. Update RAG code to use 'KnowledgeChunks' collection")
        print("  2. Update embedding dimension to 3072 in retriever_core.py")
        print("  3. Run ingestion script to load 457 chunks")
    else:
        print("Status: FAILED")
        print("Collection creation failed. Check error messages above.")

    # Close connection
    client.close()
    print("\nWeaviate connection closed")
    print("="*80)


if __name__ == "__main__":
    main()
