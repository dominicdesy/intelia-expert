"""
Image Ingester for Weaviate
Version: 1.0.0
Last modified: 2025-10-31

Ingests image metadata to Weaviate (InteliaImages collection)
"""

import os
import logging
from typing import Dict, Any, List, Optional
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ImageIngester:
    """
    Ingest image metadata to Weaviate InteliaImages collection.

    Stores:
    - image_url (link to Digital Ocean Spaces)
    - caption/description
    - page_number
    - source_file
    - image_type (diagram, chart, photo, etc.)
    - dimensions, file size
    - linked_chunk_ids (references to text chunks)
    - classification metadata
    """

    def __init__(
        self,
        collection_name: str = "InteliaImages",
        weaviate_url: Optional[str] = None,
        weaviate_api_key: Optional[str] = None
    ):
        """
        Initialize image ingester.

        Args:
            collection_name: Weaviate collection name
            weaviate_url: Optional Weaviate URL override
            weaviate_api_key: Optional API key override
        """
        self.collection_name = collection_name

        # Get Weaviate credentials
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = weaviate_api_key or os.getenv("WEAVIATE_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.weaviate_url or not self.weaviate_api_key:
            raise ValueError(
                "Weaviate credentials not found. "
                "Set WEAVIATE_URL and WEAVIATE_API_KEY environment variables."
            )

        # Prepare headers with OpenAI API key (required for text2vec-openai vectorizer)
        headers = {}
        if self.openai_api_key:
            headers["X-OpenAI-Api-Key"] = self.openai_api_key

        # Connect to Weaviate
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=self.weaviate_url,
            auth_credentials=Auth.api_key(self.weaviate_api_key),
            headers=headers
        )

        logger.info(f"Connected to Weaviate: {self.weaviate_url}")

        # Ensure collection exists
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create InteliaImages collection if it doesn't exist."""
        try:
            # Check if collection exists
            if self.client.collections.exists(self.collection_name):
                logger.info(f"Collection '{self.collection_name}' already exists")
                return

            # Create collection with schema
            logger.info(f"Creating collection '{self.collection_name}'...")

            self.client.collections.create(
                name=self.collection_name,
                description="Image metadata from knowledge documents",

                # Vectorizer configuration (using text2vec-openai for caption-based search)
                # Note: CLIP not available, so we vectorize based on caption text only
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small"
                ),

                # Properties (metadata fields)
                properties=[
                    # Core image properties
                    Property(
                        name="image_id",
                        data_type=DataType.TEXT,
                        description="Unique image identifier"
                    ),
                    Property(
                        name="image_url",
                        data_type=DataType.TEXT,
                        description="URL to image in Digital Ocean Spaces"
                    ),
                    Property(
                        name="caption",
                        data_type=DataType.TEXT,
                        description="Image caption/description"
                    ),
                    Property(
                        name="image_type",
                        data_type=DataType.TEXT,
                        description="Type: diagram, chart, photo, table, infographic"
                    ),

                    # Source information
                    Property(
                        name="source_file",
                        data_type=DataType.TEXT,
                        description="Original PDF file path"
                    ),
                    Property(
                        name="page_number",
                        data_type=DataType.INT,
                        description="Page number in source document"
                    ),

                    # Image metadata
                    Property(
                        name="width",
                        data_type=DataType.INT,
                        description="Image width in pixels"
                    ),
                    Property(
                        name="height",
                        data_type=DataType.INT,
                        description="Image height in pixels"
                    ),
                    Property(
                        name="file_size_kb",
                        data_type=DataType.NUMBER,
                        description="File size in KB"
                    ),
                    Property(
                        name="format",
                        data_type=DataType.TEXT,
                        description="Image format (png, jpg, etc.)"
                    ),

                    # Links to text chunks
                    Property(
                        name="linked_chunk_ids",
                        data_type=DataType.TEXT_ARRAY,
                        description="IDs of related text chunks"
                    ),

                    # Classification metadata (same as InteliaKnowledge)
                    Property(
                        name="owner_org_id",
                        data_type=DataType.TEXT,
                        description="Organization ID (e.g., intelia)"
                    ),
                    Property(
                        name="visibility_level",
                        data_type=DataType.TEXT,
                        description="Visibility level (public_global, intelia_internal)"
                    ),
                    Property(
                        name="site_type",
                        data_type=DataType.TEXT,
                        description="Site type (broiler_farms, layer_farms, etc.)"
                    ),
                    Property(
                        name="category",
                        data_type=DataType.TEXT,
                        description="Document category"
                    ),

                    # Timestamps
                    Property(
                        name="extracted_at",
                        data_type=DataType.TEXT,
                        description="Extraction timestamp (ISO format)"
                    )
                ]
            )

            logger.info(f"✓ Collection '{self.collection_name}' created successfully")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    def ingest_image(self, image_metadata: Dict[str, Any]) -> bool:
        """
        Ingest a single image metadata object to Weaviate.

        Args:
            image_metadata: Dictionary with image metadata

        Returns:
            True if successful

        Example:
            {
                "image_id": "nano_manual_page5_img1",
                "image_url": "https://...",
                "caption": "Figure 1: Ventilation diagram",
                "image_type": "diagram",
                "page_number": 5,
                "source_file": "nano-manual.pdf",
                "width": 1200,
                "height": 800,
                "file_size_kb": 245.3,
                "format": "png",
                "linked_chunk_ids": ["chunk_001", "chunk_002"],
                "owner_org_id": "intelia",
                "visibility_level": "public_global",
                "site_type": "broiler_farms",
                "category": "management",
                "extracted_at": "2025-10-31T00:00:00Z"
            }
        """
        try:
            collection = self.client.collections.get(self.collection_name)

            # Insert image metadata
            uuid = collection.data.insert(
                properties=image_metadata
            )

            logger.info(f"✓ Ingested image: {image_metadata.get('image_id')} → UUID: {uuid}")
            return True

        except Exception as e:
            logger.error(f"Error ingesting image {image_metadata.get('image_id')}: {e}")
            return False

    def ingest_images(self, images: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingest multiple images in batch.

        Args:
            images: List of image metadata dictionaries

        Returns:
            Statistics: {"success": count, "failed": count}
        """
        stats = {"success": 0, "failed": 0}

        collection = self.client.collections.get(self.collection_name)

        # Use batch insert for better performance
        with collection.batch.dynamic() as batch:
            for image_metadata in images:
                try:
                    batch.add_object(
                        properties=image_metadata
                    )
                    stats["success"] += 1
                except Exception as e:
                    logger.error(f"Error ingesting {image_metadata.get('image_id')}: {e}")
                    stats["failed"] += 1

        logger.info(f"Batch ingestion complete: {stats['success']} success, {stats['failed']} failed")
        return stats

    def search_images(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search images by text query (uses CLIP embeddings).

        Args:
            query: Search query
            limit: Max results
            filters: Optional metadata filters

        Returns:
            List of matching images with metadata
        """
        try:
            collection = self.client.collections.get(self.collection_name)

            # Build query
            query_builder = collection.query.near_text(
                query=query,
                limit=limit
            )

            # Add filters if provided
            if filters:
                # TODO: Implement filter logic
                pass

            # Execute search
            response = query_builder.do()

            # Format results
            results = []
            for obj in response.objects:
                results.append({
                    "uuid": str(obj.uuid),
                    "image_url": obj.properties.get("image_url"),
                    "caption": obj.properties.get("caption"),
                    "image_type": obj.properties.get("image_type"),
                    "page_number": obj.properties.get("page_number"),
                    "source_file": obj.properties.get("source_file"),
                    "distance": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None
                })

            return results

        except Exception as e:
            logger.error(f"Error searching images: {e}")
            return []

    def get_images_by_chunk(self, chunk_id: str) -> List[Dict[str, Any]]:
        """
        Get all images linked to a specific text chunk.

        Args:
            chunk_id: Text chunk ID

        Returns:
            List of linked images
        """
        try:
            collection = self.client.collections.get(self.collection_name)

            # Query with filter on linked_chunk_ids
            response = collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("linked_chunk_ids").contains_any([chunk_id])
            )

            results = []
            for obj in response.objects:
                results.append({
                    "uuid": str(obj.uuid),
                    "image_url": obj.properties.get("image_url"),
                    "caption": obj.properties.get("caption"),
                    "page_number": obj.properties.get("page_number")
                })

            return results

        except Exception as e:
            logger.error(f"Error getting images for chunk {chunk_id}: {e}")
            return []

    def close(self):
        """Close Weaviate connection."""
        self.client.close()
        logger.info("Weaviate connection closed")


# Example usage
if __name__ == "__main__":
    """Test image ingester."""

    # Initialize ingester
    ingester = ImageIngester()

    # Test image metadata
    test_image = {
        "image_id": "test_manual_page1_img1",
        "image_url": "https://intelia.nyc3.cdn.digitaloceanspaces.com/test/test_image.png",
        "caption": "Test diagram showing poultry housing layout",
        "image_type": "diagram",
        "page_number": 1,
        "source_file": "test_manual.pdf",
        "width": 1200,
        "height": 800,
        "file_size_kb": 245.3,
        "format": "png",
        "linked_chunk_ids": ["chunk_test_001"],
        "owner_org_id": "intelia",
        "visibility_level": "public_global",
        "site_type": "broiler_farms",
        "category": "housing",
        "extracted_at": "2025-10-31T00:00:00Z"
    }

    # Ingest
    success = ingester.ingest_image(test_image)
    print(f"Ingestion successful: {success}")

    # Search
    results = ingester.search_images("housing diagram", limit=5)
    print(f"Found {len(results)} images")
    for result in results:
        print(f"  - {result['caption']} ({result['image_url']})")

    # Close connection
    ingester.close()
