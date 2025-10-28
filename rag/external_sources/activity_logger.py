# -*- coding: utf-8 -*-
"""
External Sources Activity Logger
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
External Sources Activity Logger
Tracks all external source searches, document ingestions, and costs
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import structlog

logger = logging.getLogger(__name__)
structured_logger = structlog.get_logger()


@dataclass
class ExternalSearchActivity:
    """Record of an external source search activity"""

    timestamp: str
    request_id: str
    query: str
    language: str
    weaviate_confidence: float
    triggered_reason: str  # "low_confidence", "no_results", etc.

    # Search results
    sources_queried: List[str]
    total_documents_found: int
    search_duration_ms: float

    # Best document selected
    best_document_found: bool
    best_document_title: Optional[str] = None
    best_document_source: Optional[str] = None
    best_document_score: Optional[float] = None
    best_document_year: Optional[int] = None
    best_document_citations: Optional[int] = None

    # Ingestion
    document_ingested: bool = False
    document_already_existed: bool = False
    ingestion_duration_ms: Optional[float] = None

    # Cost tracking
    estimated_embedding_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None

    # Metadata
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class ExternalSourcesStats:
    """Aggregated statistics for external sources usage"""

    total_searches: int = 0
    total_documents_ingested: int = 0
    total_documents_found: int = 0
    total_cost_usd: float = 0.0

    # Per-source statistics
    searches_by_source: Dict[str, int] = None
    documents_by_source: Dict[str, int] = None

    # Performance
    avg_search_duration_ms: float = 0.0
    avg_ingestion_duration_ms: float = 0.0

    # Time range
    first_activity: Optional[str] = None
    last_activity: Optional[str] = None


class ExternalSourcesActivityLogger:
    """
    Logger for external sources activities with structured logging and JSON persistence
    """

    # Cost constants (OpenAI text-embedding-3-small)
    EMBEDDING_COST_PER_1M_TOKENS = 0.02  # $0.02 per 1M tokens
    AVG_TOKENS_PER_DOCUMENT = 90  # Average tokens for title + abstract

    def __init__(self, log_dir: str = None):
        """
        Initialize activity logger

        Args:
            log_dir: Directory for storing activity logs
                    (default: $EXTERNAL_SOURCES_LOG_DIR or /app/logs/external_sources)
        """
        import os

        # Use environment variable if set, otherwise use default
        if log_dir is None:
            log_dir = os.getenv(
                "EXTERNAL_SOURCES_LOG_DIR", "/app/logs/external_sources"
            )

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Separate files for different purposes
        self.activity_log_file = self.log_dir / "activity.jsonl"
        self.daily_stats_file = self.log_dir / "daily_stats.json"
        self.monthly_stats_file = self.log_dir / "monthly_stats.json"

        logger.info(f"✅ ExternalSourcesActivityLogger initialized: {self.log_dir}")

    def log_search_activity(
        self,
        request_id: str,
        query: str,
        language: str,
        weaviate_confidence: float,
        triggered_reason: str,
        sources_queried: List[str],
        total_documents_found: int,
        search_duration_ms: float,
        best_document: Optional[Any] = None,
        document_ingested: bool = False,
        document_already_existed: bool = False,
        ingestion_duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        Log a complete external search activity

        Args:
            request_id: Unique request identifier
            query: User query that triggered search
            language: Query language
            weaviate_confidence: Weaviate confidence score
            triggered_reason: Why external search was triggered
            sources_queried: List of external sources queried
            total_documents_found: Total documents found across all sources
            search_duration_ms: Search duration in milliseconds
            best_document: Best document selected (ExternalDocument object)
            document_ingested: Whether document was ingested
            document_already_existed: Whether document already existed
            ingestion_duration_ms: Ingestion duration in milliseconds
            tenant_id: Tenant/user identifier
            session_id: Session identifier
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Extract best document info
        best_doc_found = best_document is not None
        best_doc_title = best_document.title if best_document else None
        best_doc_source = best_document.source if best_document else None
        best_doc_score = best_document.composite_score if best_document else None
        best_doc_year = best_document.year if best_document else None
        best_doc_citations = best_document.citation_count if best_document else None

        # Estimate cost
        estimated_tokens = None
        estimated_cost = None
        if document_ingested and best_document:
            # Estimate tokens from title + abstract length
            text_length = len(best_document.title) + len(best_document.abstract)
            estimated_tokens = int(text_length / 4)  # Rough estimate: 4 chars per token
            estimated_cost = (
                estimated_tokens / 1_000_000
            ) * self.EMBEDDING_COST_PER_1M_TOKENS

        # Create activity record
        activity = ExternalSearchActivity(
            timestamp=timestamp,
            request_id=request_id,
            query=query,
            language=language,
            weaviate_confidence=weaviate_confidence,
            triggered_reason=triggered_reason,
            sources_queried=sources_queried,
            total_documents_found=total_documents_found,
            search_duration_ms=search_duration_ms,
            best_document_found=best_doc_found,
            best_document_title=best_doc_title,
            best_document_source=best_doc_source,
            best_document_score=best_doc_score,
            best_document_year=best_doc_year,
            best_document_citations=best_doc_citations,
            document_ingested=document_ingested,
            document_already_existed=document_already_existed,
            ingestion_duration_ms=ingestion_duration_ms,
            estimated_embedding_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
            tenant_id=tenant_id,
            session_id=session_id,
        )

        # Write to JSONL file (one JSON object per line)
        try:
            with open(self.activity_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(activity), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"❌ Failed to write activity log: {e}")

        # Structured logging for real-time monitoring
        structured_logger.info(
            "external_search_activity",
            request_id=request_id,
            query=query[:100],  # Truncate long queries
            language=language,
            weaviate_confidence=weaviate_confidence,
            triggered_reason=triggered_reason,
            sources_queried=sources_queried,
            documents_found=total_documents_found,
            search_duration_ms=search_duration_ms,
            best_document_found=best_doc_found,
            best_document_source=best_doc_source,
            best_document_score=best_doc_score,
            document_ingested=document_ingested,
            document_already_existed=document_already_existed,
            estimated_cost_usd=estimated_cost,
            tenant_id=tenant_id,
        )

        # Console log for important events
        if document_ingested:
            logger.info(
                f"📥 EXTERNAL DOC INGESTED | Query: '{query[:60]}...' | "
                f"Source: {best_doc_source} | Title: '{best_doc_title[:80]}...' | "
                f"Cost: ${estimated_cost:.6f}"
            )
        elif best_doc_found and document_already_existed:
            logger.info(
                f"♻️ EXTERNAL DOC EXISTS | Query: '{query[:60]}...' | "
                f"Source: {best_doc_source} | Title: '{best_doc_title[:80]}...'"
            )
        elif best_doc_found:
            logger.info(
                f"✅ EXTERNAL DOC FOUND | Query: '{query[:60]}...' | "
                f"Source: {best_doc_source} | Title: '{best_doc_title[:80]}...'"
            )
        else:
            logger.info(
                f"ℹ️ NO EXTERNAL DOCS | Query: '{query[:60]}...' | "
                f"Sources: {', '.join(sources_queried)} | Found: {total_documents_found}"
            )

    def get_statistics(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> ExternalSourcesStats:
        """
        Calculate statistics from activity logs

        Args:
            start_date: Start date (ISO format, optional)
            end_date: End date (ISO format, optional)

        Returns:
            ExternalSourcesStats object with aggregated statistics
        """
        stats = ExternalSourcesStats(searches_by_source={}, documents_by_source={})

        if not self.activity_log_file.exists():
            return stats

        try:
            activities = []
            with open(self.activity_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        activity = json.loads(line)

                        # Filter by date range if specified
                        if start_date and activity["timestamp"] < start_date:
                            continue
                        if end_date and activity["timestamp"] > end_date:
                            continue

                        activities.append(activity)

            if not activities:
                return stats

            # Calculate aggregates
            stats.total_searches = len(activities)
            stats.total_documents_found = sum(
                a["total_documents_found"] for a in activities
            )
            stats.total_documents_ingested = sum(
                1 for a in activities if a["document_ingested"]
            )
            stats.total_cost_usd = sum(
                a.get("estimated_cost_usd", 0.0) or 0.0 for a in activities
            )

            # Per-source statistics
            for activity in activities:
                for source in activity.get("sources_queried", []):
                    stats.searches_by_source[source] = (
                        stats.searches_by_source.get(source, 0) + 1
                    )

                if activity.get("document_ingested") and activity.get(
                    "best_document_source"
                ):
                    source = activity["best_document_source"]
                    stats.documents_by_source[source] = (
                        stats.documents_by_source.get(source, 0) + 1
                    )

            # Performance averages
            search_durations = [a["search_duration_ms"] for a in activities]
            stats.avg_search_duration_ms = (
                sum(search_durations) / len(search_durations)
                if search_durations
                else 0.0
            )

            ingestion_durations = [
                a["ingestion_duration_ms"]
                for a in activities
                if a.get("ingestion_duration_ms") is not None
            ]
            stats.avg_ingestion_duration_ms = (
                sum(ingestion_durations) / len(ingestion_durations)
                if ingestion_durations
                else 0.0
            )

            # Time range
            stats.first_activity = activities[0]["timestamp"]
            stats.last_activity = activities[-1]["timestamp"]

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to calculate statistics: {e}")
            return stats

    def get_recent_activities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get most recent activities

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of activity dictionaries (most recent first)
        """
        if not self.activity_log_file.exists():
            return []

        try:
            activities = []
            with open(self.activity_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        activities.append(json.loads(line))

            # Return most recent first
            return activities[-limit:][::-1]

        except Exception as e:
            logger.error(f"❌ Failed to get recent activities: {e}")
            return []

    def print_summary(self, days: int = 30):
        """
        Print a human-readable summary of external sources usage

        Args:
            days: Number of days to include in summary
        """
        from datetime import timedelta

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        stats = self.get_statistics(
            start_date=start_date.isoformat() + "Z", end_date=end_date.isoformat() + "Z"
        )

        print("\n" + "=" * 80)
        print(f"EXTERNAL SOURCES ACTIVITY SUMMARY (Last {days} days)")
        print("=" * 80)

        print("\n📊 Overall Statistics:")
        print(f"  Total Searches: {stats.total_searches}")
        print(f"  Documents Found: {stats.total_documents_found}")
        print(f"  Documents Ingested: {stats.total_documents_ingested}")
        print(f"  Total Cost: ${stats.total_cost_usd:.4f}")

        if stats.total_searches > 0:
            print("\n⚡ Performance:")
            print(f"  Avg Search Duration: {stats.avg_search_duration_ms:.0f}ms")
            print(f"  Avg Ingestion Duration: {stats.avg_ingestion_duration_ms:.0f}ms")

        if stats.searches_by_source:
            print("\n🔍 Searches by Source:")
            for source, count in sorted(
                stats.searches_by_source.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {source}: {count}")

        if stats.documents_by_source:
            print("\n📥 Documents Ingested by Source:")
            for source, count in sorted(
                stats.documents_by_source.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {source}: {count}")

        print("\n" + "=" * 80 + "\n")


# Global instance
_activity_logger = None


def get_activity_logger() -> ExternalSourcesActivityLogger:
    """Get or create global activity logger instance"""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ExternalSourcesActivityLogger()
    return _activity_logger


# Convenience functions
def log_external_search(
    request_id: str,
    query: str,
    language: str,
    weaviate_confidence: float,
    triggered_reason: str,
    sources_queried: List[str],
    total_documents_found: int,
    search_duration_ms: float,
    best_document: Optional[Any] = None,
    document_ingested: bool = False,
    document_already_existed: bool = False,
    ingestion_duration_ms: Optional[float] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Log external search activity (convenience function)"""
    logger_instance = get_activity_logger()
    logger_instance.log_search_activity(
        request_id=request_id,
        query=query,
        language=language,
        weaviate_confidence=weaviate_confidence,
        triggered_reason=triggered_reason,
        sources_queried=sources_queried,
        total_documents_found=total_documents_found,
        search_duration_ms=search_duration_ms,
        best_document=best_document,
        document_ingested=document_ingested,
        document_already_existed=document_already_existed,
        ingestion_duration_ms=ingestion_duration_ms,
        tenant_id=tenant_id,
        session_id=session_id,
    )


def get_external_sources_stats(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> ExternalSourcesStats:
    """Get external sources statistics (convenience function)"""
    logger_instance = get_activity_logger()
    return logger_instance.get_statistics(start_date=start_date, end_date=end_date)


def print_external_sources_summary(days: int = 30):
    """Print external sources summary (convenience function)"""
    logger_instance = get_activity_logger()
    logger_instance.print_summary(days=days)


# CLI for manual analysis
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    else:
        days = 30

    print_external_sources_summary(days=days)
