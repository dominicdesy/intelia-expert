"""
Web Batch Processor - Process URLs from Excel file
Reads websites.xlsx (sheet: URL), processes each site, updates Status
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlparse
import pandas as pd

# Add document_extractor directory to path for imports
document_extractor_path = Path(__file__).parent.parent / "document_extractor"
sys.path.insert(0, str(document_extractor_path))

from multi_format_pipeline import MultiFormatPipeline
from weaviate_integration.ingester_v2 import WeaviateIngesterV2
from weaviate_integration.deduplication_tracker import DeduplicationTracker


class WebBatchProcessor:
    """
    Process web pages from Excel file with status tracking.

    Features:
    - Reads URLs from websites.xlsx (sheet: URL)
    - Processes only rows with Status = pending or empty
    - Updates Status to "processed" or "failed"
    - Adds processing metadata (date, chunks, errors)
    - Prevents duplicate processing via URL hash
    """

    def __init__(
        self,
        excel_file: str = "websites.xlsx",
        sheet_name: str = "URL",
        collection_name: str = "InteliaKnowledge"
    ):
        """
        Initialize web batch processor.

        Args:
            excel_file: Path to Excel file with URLs
            sheet_name: Sheet name to read (default: URL)
            collection_name: Weaviate collection name
        """
        self.excel_file = Path(excel_file)
        self.sheet_name = sheet_name
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.pipeline = MultiFormatPipeline()
        self.ingester = WeaviateIngesterV2(collection_name=collection_name)
        self.tracker = DeduplicationTracker(tracking_file="processed_websites.json")

        # Statistics
        self.stats = {
            "total_rows": 0,
            "already_processed": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0
        }

        # Rate limiting: Track last access time per domain
        # Format: {"domain.com": datetime}
        self.domain_last_access = {}
        self.domain_delay_seconds = 180  # 3 minutes between pages from same domain

    def _get_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain name (e.g., "thepoultrysite.com")
        """
        parsed = urlparse(url)
        return parsed.netloc

    def _wait_for_domain_rate_limit(self, url: str):
        """
        Wait if necessary to respect rate limit for domain.

        Args:
            url: URL to process
        """
        domain = self._get_domain(url)

        if domain in self.domain_last_access:
            last_access = self.domain_last_access[domain]
            elapsed = (datetime.now() - last_access).total_seconds()

            if elapsed < self.domain_delay_seconds:
                wait_time = self.domain_delay_seconds - elapsed
                print(f"  Rate limit: Waiting {wait_time:.1f}s for domain {domain}")
                time.sleep(wait_time)

        # Update last access time
        self.domain_last_access[domain] = datetime.now()

    def load_urls(self) -> pd.DataFrame:
        """
        Load URLs from Excel file.

        Returns:
            DataFrame with URL data
        """
        try:
            df = pd.read_excel(self.excel_file, sheet_name=self.sheet_name)

            # Validate columns
            required_cols = ["Website Address", "Classification"]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")

            # Add Status column if not present
            if "Status" not in df.columns:
                df["Status"] = None

            # Add metadata columns if not present
            if "Processed Date" not in df.columns:
                df["Processed Date"] = None
            if "Chunks Created" not in df.columns:
                df["Chunks Created"] = None
            if "Error Message" not in df.columns:
                df["Error Message"] = None

            self.logger.info(f"Loaded {len(df)} URLs from {self.excel_file}")
            return df

        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            raise

    def save_urls(self, df: pd.DataFrame):
        """
        Save updated DataFrame back to Excel.

        Args:
            df: Updated DataFrame
        """
        try:
            # Read existing file to preserve other sheets
            with pd.ExcelFile(self.excel_file) as xls:
                sheets = {sheet: pd.read_excel(xls, sheet) for sheet in xls.sheet_names}

            # Update URL sheet
            sheets[self.sheet_name] = df

            # Write all sheets back
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                for sheet_name, sheet_df in sheets.items():
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

            self.logger.info(f"Saved updates to {self.excel_file}")

        except Exception as e:
            self.logger.error(f"Error saving Excel file: {e}")
            raise

    def should_process_row(self, row: pd.Series) -> bool:
        """
        Check if row should be processed.

        Args:
            row: DataFrame row

        Returns:
            True if should process, False otherwise
        """
        status = row.get("Status")

        # Process if status is empty, NaN, or "pending"
        if pd.isna(status) or status == "" or status == "pending":
            return True

        return False

    def process_all(self, delay_seconds: int = 3, force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Process all URLs in Excel file.

        Args:
            delay_seconds: Delay between requests (rate limiting)
            force_reprocess: If True, reprocess even if marked as processed

        Returns:
            Processing statistics
        """
        print("\n" + "="*80)
        print("WEB BATCH PROCESSING - START")
        print("="*80)
        print(f"Excel File: {self.excel_file}")
        print(f"Sheet: {self.sheet_name}")
        print(f"Collection: {self.ingester.collection_name}")
        print(f"Force Reprocess: {force_reprocess}")

        # Load URLs
        df = self.load_urls()
        self.stats["total_rows"] = len(df)

        print(f"\nTotal URLs: {len(df)}")

        if len(df) == 0:
            print("\nNo URLs to process")
            return self.stats

        # Process each row
        start_time = datetime.now()

        for idx, row in df.iterrows():
            url = row["Website Address"]
            classification = row["Classification"]

            print(f"\n{'-'*80}")
            print(f"[{idx+1}/{len(df)}] {url}")
            print(f"Classification: {classification}")
            print(f"{'-'*80}")

            # Check if should process
            if not force_reprocess and not self.should_process_row(row):
                print(f"SKIPPED - Status: {row['Status']}")
                self.stats["skipped"] += 1
                continue

            # Check deduplication tracker
            if not force_reprocess and self.tracker.is_processed(url):
                processed_info = self.tracker.get_processed_info(url)
                print(f"SKIPPED - Already processed")
                print(f"  Date: {processed_info['processed_timestamp']}")
                print(f"  Chunks: {processed_info['chunks_created']}")
                self.stats["already_processed"] += 1

                # Update Excel status
                df.at[idx, "Status"] = "processed"
                df.at[idx, "Processed Date"] = processed_info["processed_timestamp"]
                df.at[idx, "Chunks Created"] = processed_info["chunks_created"]
                continue

            # Rate limiting: Wait if necessary for same domain
            self._wait_for_domain_rate_limit(url)

            # Process URL
            try:
                result = self._process_single_url(url, classification)

                if result["success"]:
                    self.stats["processed"] += 1
                    self.stats["total_chunks"] += result["chunks_created"]

                    # Update Excel
                    df.at[idx, "Status"] = "processed"
                    df.at[idx, "Processed Date"] = datetime.now().isoformat()
                    df.at[idx, "Chunks Created"] = result["chunks_created"]
                    df.at[idx, "Error Message"] = None

                    print(f"SUCCESS")
                    print(f"  Chunks created: {result['chunks_created']}")
                    print(f"  Ingested to Weaviate: {result['ingested']}")
                else:
                    self.stats["failed"] += 1

                    # Update Excel
                    df.at[idx, "Status"] = "failed"
                    df.at[idx, "Processed Date"] = datetime.now().isoformat()
                    df.at[idx, "Chunks Created"] = 0
                    df.at[idx, "Error Message"] = result.get("error", "Unknown error")

                    print(f"FAILED: {result.get('error', 'Unknown error')}")

            except Exception as e:
                self.stats["failed"] += 1
                self.logger.error(f"Error processing {url}: {e}")

                # Update Excel
                df.at[idx, "Status"] = "failed"
                df.at[idx, "Processed Date"] = datetime.now().isoformat()
                df.at[idx, "Chunks Created"] = 0
                df.at[idx, "Error Message"] = str(e)

                print(f"FAILED: {e}")

            # Save after each row (incremental save)
            self.save_urls(df)

            # Rate limiting delay
            if idx < len(df) - 1:
                time.sleep(delay_seconds)

        # Final statistics
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print(f"\n{'='*80}")
        print("WEB BATCH PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"Total URLs: {self.stats['total_rows']}")
        print(f"Already Processed (skipped): {self.stats['already_processed']}")
        print(f"Skipped (status): {self.stats['skipped']}")
        print(f"Newly Processed: {self.stats['processed']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Total Chunks Created: {self.stats['total_chunks']}")
        print(f"Elapsed Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")

        if self.stats['processed'] > 0:
            avg_time = elapsed / self.stats['processed']
            print(f"Average Time per URL: {avg_time:.1f}s")

        return self.stats

    def _process_single_url(self, url: str, classification_path: str) -> Dict[str, Any]:
        """
        Process a single URL end-to-end.

        Args:
            url: URL to process
            classification_path: Classification path (e.g., intelia/public/broiler_farms/management/common)

        Returns:
            Processing result dictionary
        """
        # Create a virtual file path for classification
        # Format: Sources/{classification_path}/webpage.html
        virtual_path = f"Sources/{classification_path}/webpage.html"

        # Step 1: Process URL (web scraping + classification + enrichment + chunking)
        pipeline_result = self.pipeline.process_file(url)

        if not pipeline_result.success:
            return {
                "success": False,
                "error": pipeline_result.error,
                "chunks_created": 0,
                "ingested": False
            }

        # Override path-based metadata with classification from Excel
        # (since web scraper uses URL as source, not a real file path)
        for chunk in pipeline_result.chunks_with_metadata:
            # Parse classification path
            parts = classification_path.strip("/").split("/")
            if len(parts) >= 2:
                chunk["owner_org_id"] = parts[0]  # e.g., "intelia"
                chunk["visibility_level"] = self._map_visibility(parts[1])  # e.g., "public" -> "public_global"

            if len(parts) >= 3:
                chunk["site_type"] = parts[2]  # e.g., "broiler_farms"

            if len(parts) >= 4:
                chunk["category"] = parts[3]  # e.g., "management"

            if len(parts) >= 5:
                chunk["subcategory"] = parts[4]  # e.g., "common"

            # Update source file to show it's from web
            chunk["source_file"] = url

        # Step 2: Ingest to Weaviate
        ingestion_stats = self.ingester.ingest_chunks(pipeline_result.chunks_with_metadata)

        if ingestion_stats["failed"] > 0:
            self.logger.warning(
                f"Partial ingestion failure: {ingestion_stats['failed']} chunks failed"
            )

        # Step 3: Mark as processed in tracker
        self.tracker.mark_as_processed(
            file_path=url,  # Use URL as "file path"
            chunks_created=len(pipeline_result.chunks_with_metadata),
            metadata_summary=pipeline_result.metadata_summary
        )

        return {
            "success": True,
            "chunks_created": len(pipeline_result.chunks_with_metadata),
            "ingested": ingestion_stats["success"] > 0,
            "ingestion_stats": ingestion_stats
        }

    def _map_visibility(self, visibility: str) -> str:
        """
        Map visibility from path to full visibility level.

        Args:
            visibility: Short visibility (public, internal)

        Returns:
            Full visibility level
        """
        mapping = {
            "public": "public_global",
            "internal": "intelia_internal"
        }
        return mapping.get(visibility, visibility)


# CLI Interface
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Default configuration
    excel_file = Path(__file__).parent / "websites.xlsx"
    sheet_name = "URL"
    collection_name = "InteliaKnowledge"
    force_reprocess = False

    # Parse command line arguments
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]

    if len(sys.argv) > 2:
        if sys.argv[2].lower() in ['true', '1', 'yes', 'force']:
            force_reprocess = True

    # Initialize processor
    processor = WebBatchProcessor(
        excel_file=excel_file,
        sheet_name=sheet_name,
        collection_name=collection_name
    )

    # Process all URLs
    stats = processor.process_all(
        delay_seconds=3,  # 3 second delay between requests
        force_reprocess=force_reprocess
    )

    # Exit code based on results
    if stats["failed"] > 0 and stats["processed"] == 0:
        sys.exit(1)  # Complete failure
    elif stats["failed"] > 0:
        sys.exit(2)  # Partial failure
    else:
        sys.exit(0)  # Success
