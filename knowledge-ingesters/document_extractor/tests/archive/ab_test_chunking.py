#!/usr/bin/env python3
"""
A/B Test: Chunking Strategy Comparison (600 words vs 1200 words)
Phase 1: 5 documents (quick validation ~15 min)
Phase 2: 20 documents (comprehensive ~60 min)

Automatically tests both chunking strategies and generates comparison report.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Import knowledge extractor components
try:
    from core.chunking_service import ChunkingService, ChunkConfig
    from weaviate_integration.ingester import WeaviateIngester
    from knowledge_extractor import IntelligentKnowledgeExtractor
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)


class ABTestChunking:
    """A/B test comparing 600 words vs 1200 words chunking strategies"""

    def __init__(self, phase: int = 1):
        self.phase = phase
        self.num_docs = 5 if phase == 1 else 20
        self.test_id = f"ab_test_phase{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Collection names for A/B test
        self.collection_600 = f"ABTest_Chunking_600words_{self.test_id}"
        self.collection_1200 = f"ABTest_Chunking_1200words_{self.test_id}"

        # Results storage
        self.results = {
            "test_id": self.test_id,
            "phase": phase,
            "num_documents": self.num_docs,
            "timestamp": datetime.now().isoformat(),
            "config_600": {
                "min_chunk_words": 50,
                "max_chunk_words": 600,
                "overlap_words": 120
            },
            "config_1200": {
                "min_chunk_words": 50,
                "max_chunk_words": 1200,
                "overlap_words": 240
            },
            "extraction_results": {},
            "comparison": {}
        }

        logger.info(f"🧪 A/B Test Phase {phase} initialized: {self.num_docs} documents")

    def select_test_documents(self) -> List[Tuple[str, str]]:
        """Select representative documents for testing"""
        knowledge_dir = Path(__file__).parent.parent / "documents" / "Knowledge"

        # Get all JSON files
        all_json_files = sorted(knowledge_dir.glob("*_extracted.json"))

        if len(all_json_files) < self.num_docs:
            logger.warning(f"Only {len(all_json_files)} files available, expected {self.num_docs}")
            self.num_docs = len(all_json_files)

        # Select diverse documents (small, medium, large)
        selected = []

        # Priority files for Phase 1 (quick test)
        priority_files = [
            "ascites_extracted.json",  # Small, focused
            "Aviagen-ROSS-Broiler-Handbook-EN_extracted.json",  # Large, comprehensive
            "AviaTech_Staph_extracted.json",  # Medium
            "biosec-poultry-farms_extracted.json",  # Small
            "Breeder-Management-Guide_extracted.json"  # Large
        ]

        # For Phase 1: use priority files
        if self.phase == 1:
            for filename in priority_files[:5]:
                json_path = knowledge_dir / filename
                txt_path = knowledge_dir / filename.replace(".json", ".txt")

                if json_path.exists() and txt_path.exists():
                    selected.append((str(json_path), str(txt_path)))
                    logger.info(f"✓ Selected: {filename}")

        # For Phase 2: add more files
        else:
            # First add priority files
            for filename in priority_files:
                json_path = knowledge_dir / filename
                txt_path = knowledge_dir / filename.replace(".json", ".txt")

                if json_path.exists() and txt_path.exists():
                    selected.append((str(json_path), str(txt_path)))

            # Then add more files to reach 20
            for json_path in all_json_files:
                if len(selected) >= self.num_docs:
                    break

                txt_path = Path(str(json_path).replace(".json", ".txt"))
                if txt_path.exists():
                    pair = (str(json_path), str(txt_path))
                    if pair not in selected:
                        selected.append(pair)
                        logger.info(f"✓ Selected: {json_path.name}")

        logger.info(f"📄 Selected {len(selected)} document pairs for testing")
        return selected[:self.num_docs]

    async def run_extraction_with_config(
        self,
        collection_name: str,
        chunk_config: Dict[str, int],
        documents: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Run knowledge extraction with specific chunking configuration"""

        logger.info(f"\n{'='*60}")
        logger.info(f"🔧 Extraction: {collection_name}")
        logger.info(f"📊 Config: {chunk_config}")
        logger.info(f"{'='*60}\n")

        # Create custom extractor with specific chunk config
        extractor = IntelligentKnowledgeExtractor(
            collection_name=collection_name,
            cache_enabled=False,  # Disable cache for clean test
            force_reprocess=True
        )

        # Override chunking config in content_segmenter
        extractor.content_segmenter.chunking_service.config = ChunkConfig(
            min_chunk_words=chunk_config["min_chunk_words"],
            max_chunk_words=chunk_config["max_chunk_words"],
            overlap_words=chunk_config["overlap_words"],
            prefer_markdown_sections=True,
            prefer_paragraph_boundaries=True,
            prefer_sentence_boundaries=True
        )

        # Process documents
        results = {
            "total_documents": len(documents),
            "total_chunks": 0,
            "total_segments": 0,
            "documents_processed": [],
            "errors": []
        }

        start_time = time.time()

        for json_file, txt_file in documents:
            try:
                logger.info(f"📝 Processing: {Path(json_file).name}")

                result = await extractor.process_document(json_file, txt_file)

                # Check if processing was successful (no error field and some chunks created)
                if "error" not in result and result.get("injection_success", 0) > 0:
                    chunks_created = result.get("injection_success", 0)
                    segments_created = result.get("segments_created", 0)

                    results["total_chunks"] += chunks_created
                    results["total_segments"] += segments_created
                    results["documents_processed"].append({
                        "file": Path(json_file).name,
                        "chunks": chunks_created,
                        "segments": segments_created
                    })
                else:
                    results["errors"].append({
                        "file": Path(json_file).name,
                        "error": result.get("error", "No chunks created")
                    })

                # Small pause between documents
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ Error processing {Path(json_file).name}: {e}")
                results["errors"].append({
                    "file": Path(json_file).name,
                    "error": str(e)
                })

        results["duration_seconds"] = time.time() - start_time
        results["avg_chunks_per_doc"] = (
            results["total_chunks"] / results["total_documents"]
            if results["total_documents"] > 0 else 0
        )

        logger.info(f"\n✅ Extraction Complete:")
        logger.info(f"   Documents: {results['total_documents']}")
        logger.info(f"   Total Chunks: {results['total_chunks']}")
        logger.info(f"   Avg Chunks/Doc: {results['avg_chunks_per_doc']:.1f}")
        logger.info(f"   Duration: {results['duration_seconds']:.1f}s")

        return results

    def generate_comparison_report(self) -> str:
        """Generate markdown comparison report"""

        report = f"""# A/B Test: Chunking Strategy Comparison
## Phase {self.phase} - {self.num_docs} Documents

**Test ID**: `{self.test_id}`
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Configuration Comparison

| Parameter | Config A (600 words) | Config B (1200 words) | Ratio |
|-----------|---------------------|----------------------|-------|
| **min_chunk_words** | {self.results['config_600']['min_chunk_words']} | {self.results['config_1200']['min_chunk_words']} | 1:1 |
| **max_chunk_words** | {self.results['config_600']['max_chunk_words']} | {self.results['config_1200']['max_chunk_words']} | 1:2 |
| **overlap_words** | {self.results['config_600']['overlap_words']} | {self.results['config_1200']['overlap_words']} | 1:2 |

---

## Extraction Results

"""

        # Add extraction comparison if available
        if "extraction_600" in self.results["extraction_results"]:
            res_600 = self.results["extraction_results"]["extraction_600"]
            res_1200 = self.results["extraction_results"]["extraction_1200"]

            report += f"""### Documents Processed

| Metric | 600 words | 1200 words | Difference |
|--------|-----------|------------|------------|
| **Documents** | {res_600['total_documents']} | {res_1200['total_documents']} | - |
| **Total Chunks** | {res_600['total_chunks']} | {res_1200['total_chunks']} | {res_600['total_chunks'] - res_1200['total_chunks']:+d} |
| **Avg Chunks/Doc** | {res_600['avg_chunks_per_doc']:.1f} | {res_1200['avg_chunks_per_doc']:.1f} | {res_600['avg_chunks_per_doc'] - res_1200['avg_chunks_per_doc']:+.1f} |
| **Duration** | {res_600['duration_seconds']:.1f}s | {res_1200['duration_seconds']:.1f}s | {res_600['duration_seconds'] - res_1200['duration_seconds']:+.1f}s |

### Key Observations

- **Chunk Count**: 600-word config produces **{((res_600['total_chunks'] / res_1200['total_chunks'] - 1) * 100) if res_1200['total_chunks'] > 0 else 0:.0f}%** more chunks
- **Granularity**: {res_600['avg_chunks_per_doc']:.1f} vs {res_1200['avg_chunks_per_doc']:.1f} chunks per document on average
- **Processing Time**: Similar performance (~{abs(res_600['duration_seconds'] - res_1200['duration_seconds']):.0f}s difference)

"""

        report += f"""
---

## Next Steps

### For Phase 1 (Current):
1. ✅ Complete extraction with both configs
2. ⏳ Run RAGAS evaluation on sample queries
3. ⏳ Compare Context Recall and Precision
4. ⏳ Proceed to Phase 2 if results are promising

### For Phase 2:
- Expand to 20 documents for comprehensive validation
- Test with production-like query set
- Final recommendation based on empirical data

---

## Test Collections

- **600 words**: `{self.collection_600}`
- **1200 words**: `{self.collection_1200}`

**Note**: These are temporary test collections and can be deleted after analysis.

"""

        return report

    async def run_phase(self) -> Dict[str, Any]:
        """Execute complete A/B test phase"""

        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Starting A/B Test Phase {self.phase}")
        logger.info(f"{'='*60}\n")

        # Step 1: Select documents
        documents = self.select_test_documents()
        self.results["documents"] = [Path(json).name for json, txt in documents]

        # Step 2: Run extraction with 600-word config
        logger.info("\n📊 TEST A: 600 words chunks (OPTIMAL)")
        extraction_600 = await self.run_extraction_with_config(
            self.collection_600,
            self.results["config_600"],
            documents
        )
        self.results["extraction_results"]["extraction_600"] = extraction_600

        # Step 3: Run extraction with 1200-word config
        logger.info("\n📊 TEST B: 1200 words chunks (CURRENT)")
        extraction_1200 = await self.run_extraction_with_config(
            self.collection_1200,
            self.results["config_1200"],
            documents
        )
        self.results["extraction_results"]["extraction_1200"] = extraction_1200

        # Step 4: Generate report
        report_md = self.generate_comparison_report()

        # Save results
        output_dir = Path(__file__).parent / "ab_test_results"
        output_dir.mkdir(exist_ok=True)

        # Save JSON results
        json_path = output_dir / f"{self.test_id}_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        # Save markdown report
        md_path = output_dir / f"{self.test_id}_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Phase {self.phase} Complete!")
        logger.info(f"📄 Results: {json_path}")
        logger.info(f"📄 Report: {md_path}")
        logger.info(f"{'='*60}\n")

        # Print report
        print(report_md)

        return self.results


async def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="A/B Test Chunking Strategy")
    parser.add_argument("--phase", type=int, choices=[1, 2], default=1,
                       help="Test phase: 1=5 docs (quick), 2=20 docs (comprehensive)")

    args = parser.parse_args()

    test = ABTestChunking(phase=args.phase)
    results = await test.run_phase()

    logger.info("\n🎉 A/B Test completed successfully!")
    logger.info(f"📊 Collections created:")
    logger.info(f"   - {test.collection_600}")
    logger.info(f"   - {test.collection_1200}")
    logger.info("\n💡 Next: Run RAGAS evaluation to compare RAG performance")


if __name__ == "__main__":
    asyncio.run(main())
