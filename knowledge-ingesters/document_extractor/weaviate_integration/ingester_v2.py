"""
Weaviate Ingester V2 - Multi-Format Knowledge Extraction
Ingests enriched chunks into Weaviate Cloud with new schema
Collection: InteliaKnowledgeBase
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Also try parent directories
if not os.getenv("WEAVIATE_URL"):
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


class WeaviateIngesterV2:
    """
    Weaviate ingester for multi-format knowledge extraction.

    Features:
    - Creates InteliaKnowledgeBase collection with rich metadata schema
    - Batch ingestion with progress tracking
    - Error handling and retry logic
    - Collection cleanup and recreation
    """

    def __init__(self, collection_name: str = "InteliaKnowledgeBase"):
        """
        Initialize Weaviate ingester.

        Args:
            collection_name: Name of collection (default: InteliaKnowledgeBase)
        """
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.collection = None

        self._setup_weaviate_client()

    def _setup_weaviate_client(self):
        """Setup Weaviate v4 client connection"""
        try:
            weaviate_url = os.getenv("WEAVIATE_URL")
            api_key = os.getenv("WEAVIATE_API_KEY")
            openai_key = os.getenv("OPENAI_API_KEY")

            if not weaviate_url or not api_key:
                raise ValueError("WEAVIATE_URL and WEAVIATE_API_KEY required in .env")

            if not openai_key:
                self.logger.warning("OPENAI_API_KEY not found - vectorization may fail")

            # Connect to Weaviate Cloud
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(api_key),
                headers={"X-OpenAI-Api-Key": openai_key} if openai_key else {}
            )

            self.logger.info(f"Connected to Weaviate: {weaviate_url}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Weaviate: {e}")
            raise

    def delete_collection(self) -> bool:
        """
        Delete existing collection if it exists.

        Returns:
            True if deleted or didn't exist, False on error
        """
        try:
            if self.client.collections.exists(self.collection_name):
                self.client.collections.delete(self.collection_name)
                self.logger.info(f"Deleted existing collection: {self.collection_name}")
                return True
            else:
                self.logger.info(f"Collection does not exist: {self.collection_name}")
                return True
        except Exception as e:
            self.logger.error(f"Error deleting collection: {e}")
            return False

    def create_collection(self) -> bool:
        """
        Create InteliaKnowledgeBase collection with full schema.

        Returns:
            True if created successfully, False on error
        """
        try:
            self.logger.info(f"Creating collection: {self.collection_name}")

            self.client.collections.create(
                name=self.collection_name,
                description="Multi-format knowledge base with rich metadata for Intelia",

                # Vectorizer configuration
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-large"
                ),

                # Properties (metadata fields)
                properties=[
                    # ============================================================
                    # CONTENT (Vectorized)
                    # ============================================================
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="Main text content of the chunk (vectorized)"
                    ),

                    # ============================================================
                    # PATH-BASED METADATA (70%)
                    # ============================================================
                    Property(
                        name="owner_org_id",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Organization ID (intelia, client_abc, etc.)"
                    ),
                    Property(
                        name="visibility_level",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Visibility: public_global, intelia_internal, org_internal, org_customer_facing"
                    ),
                    Property(
                        name="site_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Site type: broiler_farms, layer_farms, breeding_farms, etc."
                    ),
                    Property(
                        name="breed",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Breed: ross_308, cobb_500, hy_line_brown, etc."
                    ),
                    Property(
                        name="category",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Category: biosecurity, breed, housing, management"
                    ),
                    Property(
                        name="subcategory",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Subcategory: common, by_breed, by_climate"
                    ),
                    Property(
                        name="climate_zone",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Climate: tropical, temperate, cold"
                    ),

                    # ============================================================
                    # VISION-BASED METADATA (25%)
                    # ============================================================
                    Property(
                        name="species",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Species: chicken, turkey, duck"
                    ),
                    Property(
                        name="genetic_line",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Genetic line: Ross, Cobb, Hy-Line, Lohmann, Hubbard"
                    ),
                    Property(
                        name="company",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Company: Aviagen, Cobb-Vantress, Hy-Line, Lohmann"
                    ),
                    Property(
                        name="document_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type: handbook, guide, technical_note, research, standard"
                    ),
                    Property(
                        name="target_audience",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Audience: farmer, veterinarian, manager, technician"
                    ),
                    Property(
                        name="technical_level",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Level: basic, intermediate, advanced"
                    ),
                    Property(
                        name="topics",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Topics: nutrition, housing, health, biosecurity, etc."
                    ),

                    # ============================================================
                    # DOCUMENT-LEVEL METADATA
                    # ============================================================
                    Property(
                        name="language",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Language: en, es, fr, etc."
                    ),
                    Property(
                        name="unit_system",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Units: metric, imperial, mixed"
                    ),

                    # ============================================================
                    # CONFIDENCE SCORES
                    # ============================================================
                    Property(
                        name="path_confidence",
                        data_type=DataType.NUMBER,
                        skip_vectorization=True,
                        description="Path classification confidence (0.0-1.0)"
                    ),
                    Property(
                        name="vision_confidence",
                        data_type=DataType.NUMBER,
                        skip_vectorization=True,
                        description="Vision enrichment confidence (0.0-1.0)"
                    ),
                    Property(
                        name="overall_confidence",
                        data_type=DataType.NUMBER,
                        skip_vectorization=True,
                        description="Overall metadata confidence (0.0-1.0)"
                    ),

                    # ============================================================
                    # SOURCE TRACKING
                    # ============================================================
                    Property(
                        name="source_file",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Source file path"
                    ),
                    Property(
                        name="extraction_method",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Method: pdf_vision, docx_text, web_scrape"
                    ),
                    Property(
                        name="chunk_id",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Unique chunk identifier"
                    ),
                    Property(
                        name="word_count",
                        data_type=DataType.INT,
                        skip_vectorization=True,
                        description="Word count of chunk"
                    ),
                    Property(
                        name="extraction_timestamp",
                        data_type=DataType.DATE,
                        skip_vectorization=True,
                        description="Timestamp of extraction (RFC3339)"
                    ),
                ]
            )

            self.logger.info(f"Collection created successfully: {self.collection_name}")

            # Get collection reference
            self.collection = self.client.collections.get(self.collection_name)

            return True

        except Exception as e:
            self.logger.error(f"Error creating collection: {e}")
            return False

    def ingest_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingest chunks into Weaviate.

        Args:
            chunks: List of chunk dictionaries with metadata

        Returns:
            Statistics: {"success": N, "failed": N}
        """
        if not self.collection:
            self.collection = self.client.collections.get(self.collection_name)

        stats = {"success": 0, "failed": 0}

        try:
            # Use batch insert for efficiency
            with self.collection.batch.dynamic() as batch:
                for i, chunk in enumerate(chunks):
                    try:
                        # Prepare data object
                        data_object = self._prepare_data_object(chunk)

                        # Add to batch
                        batch.add_object(properties=data_object)

                        stats["success"] += 1

                        if (i + 1) % 10 == 0:
                            self.logger.info(f"Ingested {i + 1}/{len(chunks)} chunks")

                    except Exception as e:
                        self.logger.error(f"Error adding chunk {i}: {e}")
                        stats["failed"] += 1

            self.logger.info(f"Ingestion complete: {stats['success']} success, {stats['failed']} failed")

            return stats

        except Exception as e:
            self.logger.error(f"Batch ingestion error: {e}")
            return stats

    def _prepare_data_object(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare chunk data for Weaviate ingestion.

        Args:
            chunk: Chunk dictionary from pipeline

        Returns:
            Data object for Weaviate
        """
        # Get current timestamp if not provided
        timestamp = chunk.get("extraction_timestamp")
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Prepare data object with all fields
        data_object = {
            # Content
            "content": chunk.get("content", ""),
            "word_count": chunk.get("word_count", 0),

            # Path-based
            "owner_org_id": chunk.get("owner_org_id", "unknown"),
            "visibility_level": chunk.get("visibility_level", "unknown"),
            "site_type": chunk.get("site_type"),
            "breed": chunk.get("breed"),
            "category": chunk.get("category"),
            "subcategory": chunk.get("subcategory"),
            "climate_zone": chunk.get("climate_zone"),

            # Vision-based
            "species": chunk.get("species"),
            "genetic_line": chunk.get("genetic_line"),
            "company": chunk.get("company"),
            "document_type": chunk.get("document_type"),
            "target_audience": chunk.get("target_audience"),
            "technical_level": chunk.get("technical_level"),
            "topics": chunk.get("topics", []),

            # Document-level
            "language": chunk.get("language", "en"),
            "unit_system": chunk.get("unit_system", "metric"),

            # Confidence
            "path_confidence": chunk.get("path_confidence", 0.0),
            "vision_confidence": chunk.get("vision_confidence", 0.0),
            "overall_confidence": chunk.get("overall_confidence", 0.0),

            # Source tracking
            "source_file": chunk.get("source_file", ""),
            "extraction_method": chunk.get("extraction_method", ""),
            "chunk_id": chunk.get("chunk_id", ""),
            "extraction_timestamp": timestamp,
        }

        return data_object

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Statistics dictionary
        """
        try:
            if not self.collection:
                self.collection = self.client.collections.get(self.collection_name)

            # Get total count
            response = self.collection.aggregate.over_all(
                total_count=True
            )

            total_count = response.total_count if response else 0

            stats = {
                "collection_name": self.collection_name,
                "total_chunks": total_count,
                "status": "ready"
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {
                "collection_name": self.collection_name,
                "error": str(e)
            }

    def close(self):
        """Close Weaviate client connection"""
        if self.client:
            self.client.close()
            self.logger.info("Weaviate client closed")


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize ingester
    ingester = WeaviateIngesterV2(collection_name="InteliaKnowledgeBase")

    # Delete existing collection
    print("\nStep 1: Deleting existing collection...")
    ingester.delete_collection()

    # Create new collection
    print("\nStep 2: Creating new collection...")
    if ingester.create_collection():
        print("Collection created successfully!")

        # Show stats
        print("\nStep 3: Collection statistics...")
        stats = ingester.get_collection_stats()
        print(f"  Collection: {stats['collection_name']}")
        print(f"  Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  Status: {stats.get('status', 'unknown')}")
    else:
        print("Failed to create collection")
        sys.exit(1)

    # Close connection
    ingester.close()

    print("\nCollection setup complete!")
    print("Ready for chunk ingestion.")
