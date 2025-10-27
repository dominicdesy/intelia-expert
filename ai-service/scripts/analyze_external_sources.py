#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyze External Sources Activity Logs
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Analyze External Sources Activity Logs

Usage:
    python analyze_external_sources.py [days]
    python analyze_external_sources.py --export csv
    python analyze_external_sources.py --top-queries 10
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from external_sources.activity_logger import (
    get_activity_logger,
    ExternalSourcesActivityLogger
)


def print_summary(days: int = 30):
    """Print summary of external sources activity"""
    logger = get_activity_logger()
    logger.print_summary(days=days)


def export_to_csv(output_file: str = "external_sources_activity.csv"):
    """Export activity logs to CSV"""
    logger = get_activity_logger()
    activities = logger.get_recent_activities(limit=10000)

    if not activities:
        print("No activities found")
        return

    import csv

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'timestamp', 'request_id', 'query', 'language',
            'weaviate_confidence', 'triggered_reason',
            'sources_queried', 'total_documents_found',
            'search_duration_ms', 'best_document_found',
            'best_document_title', 'best_document_source',
            'best_document_score', 'document_ingested',
            'estimated_cost_usd', 'tenant_id'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for activity in activities:
            row = {
                'timestamp': activity['timestamp'],
                'request_id': activity['request_id'],
                'query': activity['query'][:100],  # Truncate
                'language': activity['language'],
                'weaviate_confidence': activity['weaviate_confidence'],
                'triggered_reason': activity['triggered_reason'],
                'sources_queried': '; '.join(activity['sources_queried']),
                'total_documents_found': activity['total_documents_found'],
                'search_duration_ms': activity['search_duration_ms'],
                'best_document_found': activity['best_document_found'],
                'best_document_title': activity.get('best_document_title', '')[:100],
                'best_document_source': activity.get('best_document_source', ''),
                'best_document_score': activity.get('best_document_score', ''),
                'document_ingested': activity['document_ingested'],
                'estimated_cost_usd': activity.get('estimated_cost_usd', 0.0),
                'tenant_id': activity.get('tenant_id', ''),
            }
            writer.writerow(row)

    print(f"✅ Exported {len(activities)} activities to {output_file}")


def show_top_queries(limit: int = 10):
    """Show top queries that triggered external searches"""
    logger = get_activity_logger()
    activities = logger.get_recent_activities(limit=10000)

    if not activities:
        print("No activities found")
        return

    # Count queries
    query_counts = defaultdict(int)
    query_details = {}

    for activity in activities:
        query = activity['query']
        query_counts[query] += 1

        if query not in query_details:
            query_details[query] = {
                'language': activity['language'],
                'avg_confidence': [],
                'docs_found': [],
                'ingested': 0,
            }

        query_details[query]['avg_confidence'].append(activity['weaviate_confidence'])
        query_details[query]['docs_found'].append(activity['total_documents_found'])
        if activity['document_ingested']:
            query_details[query]['ingested'] += 1

    # Sort by count
    top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    print("\n" + "=" * 100)
    print(f"TOP {limit} QUERIES TRIGGERING EXTERNAL SEARCHES")
    print("=" * 100)

    for i, (query, count) in enumerate(top_queries, 1):
        details = query_details[query]
        avg_conf = sum(details['avg_confidence']) / len(details['avg_confidence'])
        avg_docs = sum(details['docs_found']) / len(details['docs_found'])

        print(f"\n{i}. Query: {query[:80]}...")
        print(f"   Count: {count}")
        print(f"   Language: {details['language']}")
        print(f"   Avg Weaviate Confidence: {avg_conf:.2f}")
        print(f"   Avg Documents Found: {avg_docs:.1f}")
        print(f"   Documents Ingested: {details['ingested']}")

    print("\n" + "=" * 100 + "\n")


def show_cost_analysis(days: int = 30):
    """Show cost analysis"""
    logger = get_activity_logger()

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    stats = logger.get_statistics(
        start_date=start_date.isoformat() + "Z",
        end_date=end_date.isoformat() + "Z"
    )

    print("\n" + "=" * 80)
    print(f"COST ANALYSIS (Last {days} days)")
    print("=" * 80)

    print(f"\n💰 Total Cost: ${stats.total_cost_usd:.4f}")
    print(f"📥 Documents Ingested: {stats.total_documents_ingested}")

    if stats.total_documents_ingested > 0:
        cost_per_doc = stats.total_cost_usd / stats.total_documents_ingested
        print(f"💵 Cost per Document: ${cost_per_doc:.6f}")

    print(f"\n🔍 Total Searches: {stats.total_searches}")

    if stats.total_searches > 0:
        cost_per_search = stats.total_cost_usd / stats.total_searches
        print(f"💸 Cost per Search: ${cost_per_search:.6f}")

    # Projection
    if days >= 7:
        daily_cost = stats.total_cost_usd / days
        monthly_cost = daily_cost * 30
        yearly_cost = daily_cost * 365

        print(f"\n📊 Projections:")
        print(f"   Daily: ${daily_cost:.4f}")
        print(f"   Monthly: ${monthly_cost:.4f}")
        print(f"   Yearly: ${yearly_cost:.4f}")

    print("\n" + "=" * 80 + "\n")


def show_source_performance():
    """Show performance by source"""
    logger = get_activity_logger()
    activities = logger.get_recent_activities(limit=10000)

    if not activities:
        print("No activities found")
        return

    source_stats = defaultdict(lambda: {
        'searches': 0,
        'documents_found': 0,
        'best_selected': 0,
        'ingested': 0,
        'search_times': [],
    })

    for activity in activities:
        for source in activity['sources_queried']:
            source_stats[source]['searches'] += 1

        if activity['best_document_found']:
            best_source = activity.get('best_document_source')
            if best_source:
                source_stats[best_source]['best_selected'] += 1

                if activity['document_ingested']:
                    source_stats[best_source]['ingested'] += 1

        source_stats[activity['sources_queried'][0]]['search_times'].append(
            activity['search_duration_ms']
        )

    print("\n" + "=" * 80)
    print("PERFORMANCE BY SOURCE")
    print("=" * 80)

    for source, stats in sorted(source_stats.items()):
        avg_time = sum(stats['search_times']) / len(stats['search_times']) if stats['search_times'] else 0

        print(f"\n📚 {source.upper()}")
        print(f"   Searches: {stats['searches']}")
        print(f"   Best Document Selected: {stats['best_selected']}")
        print(f"   Documents Ingested: {stats['ingested']}")
        print(f"   Avg Search Time: {avg_time:.0f}ms")

        if stats['searches'] > 0:
            selection_rate = (stats['best_selected'] / stats['searches']) * 100
            print(f"   Selection Rate: {selection_rate:.1f}%")

    print("\n" + "=" * 80 + "\n")


def show_ingestion_timeline(days: int = 7):
    """Show ingestion timeline"""
    logger = get_activity_logger()

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    activities = logger.get_recent_activities(limit=10000)

    # Filter by date
    filtered = [
        a for a in activities
        if start_date.isoformat() + "Z" <= a['timestamp'] <= end_date.isoformat() + "Z"
    ]

    # Group by date
    by_date = defaultdict(lambda: {'searches': 0, 'ingested': 0, 'cost': 0.0})

    for activity in filtered:
        date = activity['timestamp'][:10]  # YYYY-MM-DD
        by_date[date]['searches'] += 1
        if activity['document_ingested']:
            by_date[date]['ingested'] += 1
            by_date[date]['cost'] += activity.get('estimated_cost_usd', 0.0)

    print("\n" + "=" * 80)
    print(f"INGESTION TIMELINE (Last {days} days)")
    print("=" * 80)

    for date in sorted(by_date.keys()):
        stats = by_date[date]
        print(f"\n📅 {date}")
        print(f"   Searches: {stats['searches']}")
        print(f"   Ingested: {stats['ingested']}")
        print(f"   Cost: ${stats['cost']:.4f}")

    print("\n" + "=" * 80 + "\n")


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        # Default: show 30-day summary
        print_summary(days=30)
        return

    command = sys.argv[1]

    if command == "--export":
        format_type = sys.argv[2] if len(sys.argv) > 2 else "csv"
        if format_type == "csv":
            output_file = sys.argv[3] if len(sys.argv) > 3 else "external_sources_activity.csv"
            export_to_csv(output_file)
        else:
            print(f"Unknown export format: {format_type}")

    elif command == "--top-queries":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_top_queries(limit=limit)

    elif command == "--cost":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        show_cost_analysis(days=days)

    elif command == "--sources":
        show_source_performance()

    elif command == "--timeline":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        show_ingestion_timeline(days=days)

    elif command == "--help":
        print("""
External Sources Activity Analyzer

Usage:
    python analyze_external_sources.py [days]              # Show summary for N days (default: 30)
    python analyze_external_sources.py --export csv [file] # Export to CSV
    python analyze_external_sources.py --top-queries [N]   # Show top N queries (default: 10)
    python analyze_external_sources.py --cost [days]       # Show cost analysis
    python analyze_external_sources.py --sources           # Show performance by source
    python analyze_external_sources.py --timeline [days]   # Show ingestion timeline
    python analyze_external_sources.py --help              # Show this help

Examples:
    python analyze_external_sources.py 7
    python analyze_external_sources.py --export csv activity.csv
    python analyze_external_sources.py --top-queries 20
    python analyze_external_sources.py --cost 90
    python analyze_external_sources.py --sources
    python analyze_external_sources.py --timeline 14
        """)

    elif command.isdigit():
        # Number of days
        days = int(command)
        print_summary(days=days)

    else:
        print(f"Unknown command: {command}")
        print("Run with --help for usage information")


if __name__ == "__main__":
    main()
