"""
Deduplication Tracker for Knowledge Extractor
Prevents reprocessing of already-ingested documents
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import logging


class DeduplicationTracker:
    """
    Tracks processed documents to prevent duplicate extraction.

    Features:
    - Tracks document hash (content-based)
    - Records processing timestamp
    - Records chunk count and metadata
    - Persistent storage in JSON
    - Query methods for batch processing
    """

    def __init__(self, tracking_file: str = "processed_documents.json"):
        """
        Initialize deduplication tracker.

        Args:
            tracking_file: Path to JSON file storing processed documents
        """
        self.tracking_file = Path(tracking_file)
        self.logger = logging.getLogger(__name__)
        self.processed_docs = self._load_tracking_data()

    def _load_tracking_data(self) -> Dict:
        """Load existing tracking data from JSON"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading tracking data: {e}")
                return {}
        return {}

    def _save_tracking_data(self):
        """Save tracking data to JSON"""
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_docs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving tracking data: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash hex string
        """
        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            return sha256_hash.hexdigest()

        except Exception as e:
            self.logger.error(f"Error hashing file {file_path}: {e}")
            return ""

    def is_processed(self, file_path: str | Path) -> bool:
        """
        Check if document has been processed.

        Args:
            file_path: Path to document

        Returns:
            True if already processed, False otherwise
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return False

        file_hash = self._calculate_file_hash(file_path)

        if not file_hash:
            return False

        # Check if hash exists in processed documents
        return file_hash in self.processed_docs

    def get_processed_info(self, file_path: str | Path) -> Optional[Dict]:
        """
        Get processing information for a document.

        Args:
            file_path: Path to document

        Returns:
            Processing info dict or None if not processed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        file_hash = self._calculate_file_hash(file_path)

        return self.processed_docs.get(file_hash)

    def mark_as_processed(
        self,
        file_path: str | Path,
        chunks_created: int,
        metadata_summary: Dict,
        weaviate_ids: Optional[List[str]] = None
    ):
        """
        Mark document as processed.

        Args:
            file_path: Path to document
            chunks_created: Number of chunks created
            metadata_summary: Metadata summary dict
            weaviate_ids: Optional list of Weaviate object IDs
        """
        file_path = Path(file_path)

        if not file_path.exists():
            self.logger.warning(f"Cannot mark non-existent file: {file_path}")
            return

        file_hash = self._calculate_file_hash(file_path)

        if not file_hash:
            self.logger.warning(f"Could not hash file: {file_path}")
            return

        # Record processing information
        self.processed_docs[file_hash] = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size_bytes": file_path.stat().st_size,
            "processed_timestamp": datetime.now().isoformat(),
            "chunks_created": chunks_created,
            "metadata_summary": metadata_summary,
            "weaviate_ids": weaviate_ids or [],
            "file_hash": file_hash
        }

        # Save to disk
        self._save_tracking_data()

        self.logger.info(f"Marked as processed: {file_path.name}")

    def remove_document(self, file_path: str | Path) -> bool:
        """
        Remove document from tracking (to allow reprocessing).

        Args:
            file_path: Path to document

        Returns:
            True if removed, False if not found
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return False

        file_hash = self._calculate_file_hash(file_path)

        if file_hash in self.processed_docs:
            del self.processed_docs[file_hash]
            self._save_tracking_data()
            self.logger.info(f"Removed from tracking: {file_path.name}")
            return True

        return False

    def get_all_processed_files(self) -> List[Dict]:
        """
        Get list of all processed files.

        Returns:
            List of processing info dicts
        """
        return list(self.processed_docs.values())

    def get_statistics(self) -> Dict:
        """
        Get statistics about processed documents.

        Returns:
            Statistics dictionary
        """
        if not self.processed_docs:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "total_size_mb": 0
            }

        total_chunks = sum(doc["chunks_created"] for doc in self.processed_docs.values())
        total_size_bytes = sum(doc.get("file_size_bytes", 0) for doc in self.processed_docs.values())

        return {
            "total_documents": len(self.processed_docs),
            "total_chunks": total_chunks,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "average_chunks_per_doc": round(total_chunks / len(self.processed_docs), 1)
        }

    def clear_all(self):
        """Clear all tracking data (use with caution!)"""
        self.processed_docs = {}
        self._save_tracking_data()
        self.logger.warning("Cleared all tracking data")


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize tracker
    tracker = DeduplicationTracker()

    print("\n" + "="*80)
    print("DEDUPLICATION TRACKER - TEST")
    print("="*80)

    # Show statistics
    stats = tracker.get_statistics()
    print(f"\nCurrent Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Total size: {stats['total_size_mb']} MB")

    if stats['total_documents'] > 0:
        print(f"  Average chunks/doc: {stats['average_chunks_per_doc']}")

    # List all processed files
    print(f"\nProcessed Files:")
    for doc in tracker.get_all_processed_files():
        print(f"  - {doc['file_name']} ({doc['chunks_created']} chunks) - {doc['processed_timestamp']}")

    print("\n" + "="*80)
    print("Deduplication tracker ready")
    print("="*80)
