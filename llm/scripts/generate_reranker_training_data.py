#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate training data for fine-tuning cross-encoder re-ranker
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Generate training data for fine-tuning cross-encoder re-ranker

Strategy:
1. Extract (query, relevant_doc) pairs from PostgreSQL query logs
2. Add negative samples from Weaviate (non-relevant docs)
3. Export to format compatible with sentence-transformers

Output format:
[
    {"query": "...", "positive": "...", "negative": "..."},
    ...
]
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import random

# Import your existing components
from core.rag_engine import InteliaRAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_query_doc_pairs(
    rag_engine: InteliaRAGEngine,
    num_samples: int = 1000
) -> List[Tuple[str, str, float]]:
    """
    Extract (query, document, relevance) pairs from existing data

    Strategy:
    1. Use PostgreSQL query logs (if available)
    2. OR generate synthetic queries from Weaviate documents
    3. For each query, get top 20 docs from Weaviate
    4. Label top 3 as positive (1.0), bottom 5 as negative (0.0)
    """
    pairs = []

    # Example queries to start with (you can expand this)
    example_queries = [
        "Quel poids Ross 308 mâle 35 jours?",
        "Symptômes maladie Newcastle?",
        "Comment prévenir coccidiose?",
        "FCR Cobb 500 à 42 jours?",
        "Température idéale poulailler?",
        "Consommation eau poulets 21 jours?",
        "Vaccination Gumboro calendrier?",
        "Densité poulets par m2?",
        "Mortalité normale poulets?",
        "Alimentation démarrage poussins?",
        # Add more domain-specific queries...
    ]

    for query in example_queries[:num_samples]:
        try:
            # Search Weaviate for this query
            result = await rag_engine.process_query(
                query=query,
                user_id="training_data_generator",
                language="fr"
            )

            if result.context_docs and len(result.context_docs) >= 5:
                # Top 3 docs = positive samples (relevant)
                for doc in result.context_docs[:3]:
                    content = doc.get('content', '') if isinstance(doc, dict) else getattr(doc, 'content', '')
                    if content:
                        pairs.append((query, content, 1.0))
                        logger.info(f"✅ Positive pair: {query[:50]}...")

                # Bottom 5 docs = negative samples (less relevant)
                for doc in result.context_docs[-5:]:
                    content = doc.get('content', '') if isinstance(doc, dict) else getattr(doc, 'content', '')
                    if content:
                        pairs.append((query, content, 0.0))
                        logger.info(f"❌ Negative pair: {query[:50]}...")

        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            continue

    logger.info(f"📦 Generated {len(pairs)} training pairs")
    return pairs


def convert_to_training_format(
    pairs: List[Tuple[str, str, float]]
) -> List[Dict[str, str]]:
    """
    Convert (query, doc, score) to sentence-transformers format

    Format: {"query": "...", "positive": "...", "negative": "..."}
    """
    # Group by query
    queries_dict = {}
    for query, doc, score in pairs:
        if query not in queries_dict:
            queries_dict[query] = {"positives": [], "negatives": []}

        if score >= 0.5:
            queries_dict[query]["positives"].append(doc)
        else:
            queries_dict[query]["negatives"].append(doc)

    # Create training samples
    training_samples = []
    for query, docs in queries_dict.items():
        positives = docs["positives"]
        negatives = docs["negatives"]

        # Create triplets: (query, positive, negative)
        for pos in positives:
            if negatives:
                neg = random.choice(negatives)
                training_samples.append({
                    "query": query,
                    "positive": pos,
                    "negative": neg
                })

    logger.info(f"📊 Created {len(training_samples)} training triplets")
    return training_samples


async def main():
    """Generate training data for cross-encoder fine-tuning"""
    logger.info("🚀 Starting training data generation...")

    # Initialize RAG engine
    rag_engine = InteliaRAGEngine()

    # Extract query-document pairs
    pairs = await extract_query_doc_pairs(rag_engine, num_samples=100)

    if len(pairs) < 50:
        logger.warning(f"⚠️ Only {len(pairs)} pairs generated. Need at least 500 for fine-tuning.")
        logger.info("💡 Recommendation: Expand example_queries list or use PostgreSQL query logs")

    # Convert to training format
    training_data = convert_to_training_format(pairs)

    # Save to JSON
    output_path = Path("data/reranker_training_data.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Training data saved to {output_path}")
    logger.info(f"📦 {len(training_data)} triplets ready for fine-tuning")

    # Close engine
    await rag_engine.close()


if __name__ == "__main__":
    asyncio.run(main())
