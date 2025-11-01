# -*- coding: utf-8 -*-
"""
image_retriever.py - Retrieves images associated with text chunks
Version: 1.0.0
Last modified: 2025-10-31

Retrieves images from Weaviate InteliaImages collection that are related to
retrieved text chunks based on source_file matching.
"""

import logging
from typing import List, Dict, Any, Optional
from utils.imports_and_dependencies import wvc

logger = logging.getLogger(__name__)


class ImageRetriever:
    """
    Retrieve images associated with RAG text results.

    Strategy: For each text chunk returned by RAG, find images from the
    same source document that provide visual context.
    """

    def __init__(self, client, images_collection_name: str = "InteliaImages"):
        """
        Initialize image retriever.

        Args:
            client: Weaviate client instance
            images_collection_name: Name of the images collection
        """
        self.client = client
        self.images_collection_name = images_collection_name
        self.is_v4 = hasattr(client, "collections")

    def get_images_for_chunks(
        self,
        chunks: List[Dict[str, Any]],
        max_images_per_chunk: int = 3,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve images associated with text chunks.

        Strategy:
        1. If query provided: Use semantic search on image captions for relevance
        2. Fallback: Match by source_file only

        Args:
            chunks: List of text chunk dictionaries from RAG retrieval
            max_images_per_chunk: Maximum images to retrieve per document
            query: Optional user query for semantic image search

        Returns:
            List of image metadata dictionaries with URLs
        """
        if not chunks:
            return []

        # Check if images collection exists
        try:
            if not self.client.collections.exists(self.images_collection_name):
                logger.warning(f"Images collection '{self.images_collection_name}' does not exist")
                return []
        except Exception as e:
            logger.error(f"Error checking images collection: {e}")
            return []

        images = []
        seen_image_ids = set()

        # Extract unique source files from chunks
        source_files = set()
        logger.debug(f"Processing {len(chunks)} chunks to extract source files")

        for i, chunk in enumerate(chunks):
            # Handle both dict and Document objects
            if isinstance(chunk, dict):
                source_file = chunk.get("source_file") or chunk.get("metadata", {}).get("source_file")
                if i < 3:  # Log first 3 for debugging
                    logger.debug(f"Chunk {i} (dict): source_file = {source_file}")
            else:
                # Document object - use .get() method which checks metadata
                source_file = chunk.get("source_file") if hasattr(chunk, 'get') else None
                if i < 3:  # Log first 3 for debugging
                    chunk_type = type(chunk).__name__
                    has_get = hasattr(chunk, 'get')
                    has_metadata = hasattr(chunk, 'metadata')
                    logger.debug(f"Chunk {i} ({chunk_type}): has_get={has_get}, has_metadata={has_metadata}, source_file={source_file}")
                    if has_metadata:
                        metadata_keys = list(chunk.metadata.keys())[:10]
                        logger.debug(f"  metadata keys: {metadata_keys}")

            if source_file:
                source_files.add(source_file)

        logger.info(f"Extracted {len(source_files)} unique source files from {len(chunks)} chunks")
        if not source_files:
            logger.warning("No source files found in chunks - cannot retrieve images")
            return []

        logger.info(f"Searching for images from {len(source_files)} source file(s)")

        collection = self.client.collections.get(self.images_collection_name)

        # Strategy 1: Semantic search if query provided
        if query:
            logger.info(f"Using semantic search with query: '{query[:50]}...'")
            try:
                # Search images by caption similarity, filtered by source files
                for source_file in source_files:
                    response = collection.query.near_text(
                        query=query,
                        filters=wvc.query.Filter.by_property("source_file").contains_any([source_file]),
                        limit=max_images_per_chunk
                    )

                    for obj in response.objects:
                        image_id = obj.properties.get("image_id")

                        # Avoid duplicates
                        if image_id and image_id not in seen_image_ids:
                            seen_image_ids.add(image_id)

                            images.append({
                                "image_id": image_id,
                                "image_url": obj.properties.get("image_url"),
                                "caption": obj.properties.get("caption"),
                                "image_type": obj.properties.get("image_type"),
                                "source_file": obj.properties.get("source_file"),
                                "width": obj.properties.get("width"),
                                "height": obj.properties.get("height"),
                                "format": obj.properties.get("format"),
                                "relevance_score": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None
                            })

                    logger.info(f"Found {len(response.objects)} semantically relevant images for source file")

                # If semantic search worked, we're done
                if len(images) > 0:
                    logger.info(f"✅ Semantic search successful: {len(images)} relevant images found")
                    return images

            except Exception as e:
                logger.error(f"Error in semantic image search: {e}", exc_info=True)
                logger.info("Falling back to source_file matching only")
                # Fallback to strategy 2
                query = None

        # Strategy 2: Match by source_file only (fallback or when no query)
        if not query or len(images) == 0:
            logger.info("Using source_file matching only")
            for source_file in source_files:
                try:
                    # Query images from this source file
                    response = collection.query.fetch_objects(
                        filters=wvc.query.Filter.by_property("source_file").contains_any([source_file]),
                        limit=max_images_per_chunk
                    )

                    for obj in response.objects:
                        image_id = obj.properties.get("image_id")

                        # Avoid duplicates
                        if image_id and image_id not in seen_image_ids:
                            seen_image_ids.add(image_id)

                            images.append({
                                "image_id": image_id,
                                "image_url": obj.properties.get("image_url"),
                                "caption": obj.properties.get("caption"),
                                "image_type": obj.properties.get("image_type"),
                                "source_file": obj.properties.get("source_file"),
                                "width": obj.properties.get("width"),
                                "height": obj.properties.get("height"),
                                "format": obj.properties.get("format"),
                            })

                    logger.debug(f"Found {len(response.objects)} images for {source_file}")

                except Exception as e:
                    logger.error(f"Error retrieving images for {source_file}: {e}")
                    continue

        logger.info(f"Retrieved {len(images)} total images for {len(chunks)} chunks")
        return images

    def get_images_by_query(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search images directly by text query (caption-based search).

        Args:
            query: Search query
            limit: Maximum number of images to return
            filters: Optional metadata filters

        Returns:
            List of image metadata dictionaries
        """
        try:
            if not self.client.collections.exists(self.images_collection_name):
                logger.warning(f"Images collection '{self.images_collection_name}' does not exist")
                return []

            collection = self.client.collections.get(self.images_collection_name)

            # Search using caption embeddings
            response = collection.query.near_text(
                query=query,
                limit=limit
            )

            images = []
            for obj in response.objects:
                images.append({
                    "image_id": obj.properties.get("image_id"),
                    "image_url": obj.properties.get("image_url"),
                    "caption": obj.properties.get("caption"),
                    "image_type": obj.properties.get("image_type"),
                    "source_file": obj.properties.get("source_file"),
                    "relevance_score": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None
                })

            logger.info(f"Image search for '{query}': found {len(images)} images")
            return images

        except Exception as e:
            logger.error(f"Error searching images: {e}")
            return []
