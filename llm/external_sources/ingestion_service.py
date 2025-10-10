# -*- coding: utf-8 -*-
"""
Document Ingestion Service - Ingests external documents into Weaviate
"""

import logging
import uuid
from typing import List, Dict, Any
from datetime import datetime

from .models import ExternalDocument

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Service for ingesting external documents into Weaviate

    Features:
    - Chunks documents (500 tokens, 50 overlap)
    - Generates embeddings via Weaviate (automatic)
    - Stores metadata (source, citations, query context)
    - Handles errors gracefully
    """

    def __init__(self, weaviate_client):
        """
        Initialize ingestion service

        Args:
            weaviate_client: Weaviate client instance
        """
        self.weaviate_client = weaviate_client
        self.collection_name = "Document"  # Weaviate collection name

        logger.info(f"✅ DocumentIngestionService initialized")

    async def ingest_document(
        self,
        document: ExternalDocument,
        query_context: str,
        language: str = "en"
    ) -> bool:
        """
        Ingest external document into Weaviate

        Args:
            document: External document to ingest
            query_context: Original query that triggered this document
            language: Language of the query

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                f"📥 Ingesting document: '{document.title[:60]}...' "
                f"from {document.source}"
            )

            # Chunk document
            chunks = self._chunk_document(document)
            logger.info(f"  Split into {len(chunks)} chunks")

            # Upload chunks to Weaviate
            uploaded = 0
            for i, chunk in enumerate(chunks):
                success = await self._upload_chunk(
                    chunk=chunk,
                    chunk_index=i,
                    total_chunks=len(chunks),
                    document=document,
                    query_context=query_context,
                    language=language
                )

                if success:
                    uploaded += 1

            if uploaded > 0:
                logger.info(
                    f"✅ Successfully uploaded {uploaded}/{len(chunks)} chunks "
                    f"for document: {document.title[:60]}..."
                )
                return True
            else:
                logger.error(f"❌ Failed to upload any chunks")
                return False

        except Exception as e:
            logger.error(f"❌ Document ingestion failed: {e}")
            return False

    def _chunk_document(
        self,
        document: ExternalDocument,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Chunk document into overlapping pieces

        Args:
            document: Document to chunk
            chunk_size: Target chunk size in tokens (approximated by words)
            overlap: Overlap size in tokens

        Returns:
            List of chunk dicts with text and metadata
        """
        # Get full content (abstract or full text)
        content = document.get_content()

        # Simple word-based chunking (approximates tokens)
        words = content.split()

        chunks = []
        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            # Add title as context at beginning of first chunk
            if start == 0:
                chunk_text = f"{document.title}\n\n{chunk_text}"

            chunks.append({
                "text": chunk_text,
                "start_word": start,
                "end_word": end
            })

            # Move start forward with overlap
            start = end - overlap if end < len(words) else end

        return chunks

    async def _upload_chunk(
        self,
        chunk: Dict[str, Any],
        chunk_index: int,
        total_chunks: int,
        document: ExternalDocument,
        query_context: str,
        language: str
    ) -> bool:
        """
        Upload a single chunk to Weaviate

        Args:
            chunk: Chunk dict with text
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            document: Original document
            query_context: Original query
            language: Query language

        Returns:
            True if successful
        """
        try:
            # Build properties for Weaviate
            properties = {
                "content": chunk["text"],
                "title": document.title,
                "source": document.source,
                "source_type": "external_document",
                "url": document.url,
                "authors": ", ".join(document.authors),
                "year": document.year,
                "language": language,

                # External source metadata
                "doi": document.doi or "",
                "pmid": document.pmid or "",
                "pmcid": document.pmcid or "",
                "citation_count": document.citation_count,
                "journal": document.journal or "",

                # Ingestion metadata
                "ingested_from_query": query_context,
                "ingested_at": datetime.now().isoformat(),
                "relevance_score": document.relevance_score,
                "composite_score": document.composite_score,

                # Chunk metadata
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "is_first_chunk": chunk_index == 0,
                "is_last_chunk": chunk_index == total_chunks - 1
            }

            # Upload to Weaviate (embeddings generated automatically)
            self.weaviate_client.data_object.create(
                data_object=properties,
                class_name=self.collection_name
            )

            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to upload chunk {chunk_index + 1}/{total_chunks}: {e}"
            )
            return False

    def check_document_exists(self, document: ExternalDocument) -> bool:
        """
        Check if document already exists in Weaviate

        Args:
            document: Document to check

        Returns:
            True if document exists
        """
        try:
            # Query by DOI, PMID, or title
            where_filter = None

            if document.doi:
                where_filter = {
                    "path": ["doi"],
                    "operator": "Equal",
                    "valueString": document.doi
                }
            elif document.pmid:
                where_filter = {
                    "path": ["pmid"],
                    "operator": "Equal",
                    "valueString": document.pmid
                }
            else:
                # Fallback to title match
                where_filter = {
                    "path": ["title"],
                    "operator": "Equal",
                    "valueString": document.title
                }

            result = (
                self.weaviate_client.query
                .get(self.collection_name, ["uuid"])
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )

            exists = len(result.get("data", {}).get("Get", {}).get(self.collection_name, [])) > 0

            if exists:
                logger.info(f"✅ Document already exists: {document.title[:60]}...")

            return exists

        except Exception as e:
            logger.warning(f"⚠️ Error checking document existence: {e}")
            return False
