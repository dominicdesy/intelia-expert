#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet du flux pour la question processing plants
"""

import sys
import asyncio
from pathlib import Path

# Load .env
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] .env loaded from {env_path}")
else:
    print(f"[WARN] .env not found at {env_path}")

# Add llm to path
sys.path.insert(0, str(Path(__file__).parent))

from core.rag_engine import InteliaRAGEngine  # noqa: E402


async def test_processing_plant_query():
    """Test la question processing plants avec le nouveau fallback"""

    print("=" * 80)
    print("Testing Processing Plants Query with LLM Fallback")
    print("=" * 80)

    # Initialize RAG engine
    engine = InteliaRAGEngine()
    await engine.initialize()

    # Test query
    query = "What are the main data points processing plants need from farms to plan efficiently?"

    print(f"\nQuery: {query}\n")

    try:
        # Process query
        result = await engine.generate_response(
            query=query, tenant_id="test_fallback", language="en"
        )

        # Display results
        print(f"Source: {result.source}")
        print(f"Answer length: {len(result.answer) if result.answer else 0} chars")
        print(f"\nAnswer:\n{result.answer}\n")

        # Check metadata
        print("Metadata:")
        for key, value in result.metadata.items():
            if key not in ["conversation_context_used", "conversation_context_length"]:
                print(f"  - {key}: {value}")

        # Verify fallback was used if no docs found
        if result.metadata.get("llm_fallback_used"):
            print("\n✅ LLM Fallback was successfully used!")
        elif result.context_docs and len(result.context_docs) > 0:
            print(f"\n✅ Found {len(result.context_docs)} documents")
        else:
            print("\n⚠️ No documents and no fallback used")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("[OK] Test completed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_processing_plant_query())
