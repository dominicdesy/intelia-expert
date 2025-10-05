# -*- coding: utf-8 -*-
"""
document_utils.py - Document utility methods for processing Document objects and dicts

This module provides utility methods for extracting content and metadata from documents
that can be either Document objects or dictionaries. These utilities ensure consistent
handling of both formats throughout the generation pipeline.
"""

import logging
from utils.types import Union
from core.data_models import Document

logger = logging.getLogger(__name__)


class DocumentUtils:
    """
    Utility class for processing Document objects and dictionaries.

    This class provides static methods for extracting content, metadata, and
    converting documents to unified dictionary format for caching and processing.
    All methods support both Document objects and dictionary representations.
    """

    @staticmethod
    def _get_doc_content(doc: Union[Document, dict]) -> str:
        """
        Extract content from a document (dict or Document object).

        Safely retrieves the content field from either a Document object or a dictionary
        representation. Logs a warning if content is empty in dictionary format.

        Args:
            doc: Document object or dictionary containing document data

        Returns:
            str: Content of the document, or empty string if not found

        Examples:
            >>> content = DocumentUtils._get_doc_content(document_obj)
            >>> content = DocumentUtils._get_doc_content({"content": "text", "metadata": {}})
        """
        if isinstance(doc, dict):
            content = doc.get("content", "")
            # Log warning for debugging if content is empty
            if not content:
                logger.warning(
                    f"⚠️ Document dict avec content vide: {doc.get('metadata', {})}"
                )
            return content
        return getattr(doc, "content", "")

    @staticmethod
    def _get_doc_metadata(
        doc: Union[Document, dict], key: str, default: str = "N/A"
    ) -> str:
        """
        Extract a metadata value from a document (dict or Document object).

        Safely retrieves a specific metadata field from either a Document object or a
        dictionary representation. Handles nested metadata structures and provides
        fallback to default value.

        Args:
            doc: Document object or dictionary containing document data
            key: Metadata key to retrieve
            default: Default value to return if key is not found (default: "N/A")

        Returns:
            str: Metadata value for the specified key, or default value if not found

        Examples:
            >>> title = DocumentUtils._get_doc_metadata(doc, "title")
            >>> source = DocumentUtils._get_doc_metadata(doc, "source", "Unknown")
        """
        if isinstance(doc, dict):
            return doc.get("metadata", {}).get(key, default)
        metadata = getattr(doc, "metadata", {})
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default

    @staticmethod
    def _doc_to_dict(doc: Union[Document, dict]) -> dict:
        """
        Convert Document object or dict to unified dictionary format for caching.

        Normalizes both Document objects and dictionary representations into a
        consistent dictionary format. This is essential for cache operations and
        ensures all downstream processing has a uniform data structure.

        The method handles both camelCase (geneticLine) and snake_case (genetic_line)
        metadata keys for compatibility.

        Args:
            doc: Document object or dictionary to convert

        Returns:
            dict: Normalized dictionary with the following structure:
                {
                    "content": str,
                    "title": str,
                    "source": str,
                    "score": float,
                    "genetic_line": str,
                    "species": str,
                    "explain_score": dict (optional, only if present in Document)
                }

        Examples:
            >>> doc_dict = DocumentUtils._doc_to_dict(document_obj)
            >>> doc_dict = DocumentUtils._doc_to_dict({"content": "...", "metadata": {...}})
        """
        if isinstance(doc, dict):
            # Already a dict, normalize the structure
            return {
                "content": doc.get("content", ""),
                "title": doc.get("metadata", {}).get("title", ""),
                "source": doc.get("metadata", {}).get("source", ""),
                "score": doc.get("score", 0.0),
                "genetic_line": doc.get("metadata", {}).get(
                    "geneticLine", doc.get("metadata", {}).get("genetic_line", "")
                ),
                "species": doc.get("metadata", {}).get("species", ""),
            }

        # Document object
        result = {
            "content": doc.content,
            "title": doc.metadata.get("title", ""),
            "source": doc.metadata.get("source", ""),
            "score": doc.score,
            "genetic_line": doc.metadata.get(
                "geneticLine", doc.metadata.get("genetic_line", "")
            ),
            "species": doc.metadata.get("species", ""),
        }
        if doc.explain_score:
            result["explain_score"] = doc.explain_score
        return result
