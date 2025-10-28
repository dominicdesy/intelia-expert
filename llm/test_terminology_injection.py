"""
Test script for terminology injection system

This script tests:
1. Loading of extended glossary
2. Keyword matching
3. Category detection
4. Terminology formatting for prompts
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.domain_config.terminology_injector import get_terminology_injector
from app.domain_config.domains.aviculture.config import get_aviculture_config


def test_terminology_injector():
    """Test the terminology injector directly"""
    print("=" * 80)
    print("Testing Terminology Injector")
    print("=" * 80)

    injector = get_terminology_injector()

    # Get stats
    stats = injector.get_terminology_stats()
    print(f"\n Terminology Statistics:")
    print(f"  Extended glossary terms: {stats['extended_glossary_terms']}")
    print(f"  Value chain terms: {stats['value_chain_terms']}")
    print(f"  Total terms: {stats['total_terms']}")
    print(f"  Categories: {len(stats['categories'])}")
    print(f"  Indexed keywords: {stats['indexed_keywords']}")

    # Test queries
    test_queries = [
        {
            "query": "What is the hatchability rate for Ross 308 at day 21?",
            "description": "Hatchery query - should load hatchery terms"
        },
        {
            "query": "How to improve feed conversion ratio in broilers?",
            "description": "Nutrition query - should load nutrition terms"
        },
        {
            "query": "What are the symptoms of Newcastle disease?",
            "description": "Health query - should load health/disease terms"
        },
        {
            "query": "What is the breast yield for Cobb 500?",
            "description": "Processing query - should load processing terms"
        },
        {
            "query": "How to increase egg production in layers?",
            "description": "Layer production query - should load layer terms"
        }
    ]

    print("\n" + "=" * 80)
    print(" Testing Query Matching")
    print("=" * 80)

    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        description = test_case["description"]

        print(f"\n--- Test {i}: {description} ---")
        print(f"Query: \"{query}\"")

        # Detect categories
        categories = injector.detect_relevant_categories(query)
        print(f"\n Detected categories: {categories[:3]}")

        # Find matching terms
        matching_terms = injector.find_matching_terms(query, max_terms=10)
        print(f" Found {len(matching_terms)} matching terms")

        if matching_terms:
            print(f"\nTop 5 matching terms:")
            for j, term in enumerate(matching_terms[:5], 1):
                term_name = term.get('term', 'Unknown')
                category = term.get('category', 'N/A')
                definition = term.get('definition', '')[:80] + '...' if len(term.get('definition', '')) > 80 else term.get('definition', '')
                print(f"  {j}. {term_name} ({category})")
                print(f"     {definition}")

        # Format for prompt
        formatted = injector.format_terminology_for_prompt(
            query=query,
            max_tokens=500,
            language='en'
        )

        if formatted:
            print(f"\n Formatted terminology section ({len(formatted)} chars):")
            # Show first 300 chars
            preview = formatted[:300] + "..." if len(formatted) > 300 else formatted
            print(preview)


def test_aviculture_config_integration():
    """Test integration with AvicultureConfig"""
    print("\n" + "=" * 80)
    print(" Testing AvicultureConfig Integration")
    print("=" * 80)

    config = get_aviculture_config()

    test_query = "What is the optimal temperature for incubation of broiler eggs?"

    print(f"\nTest query: \"{test_query}\"")

    # Get system prompt WITHOUT terminology
    print("\n--- System Prompt WITHOUT Terminology ---")
    prompt_without = config.get_system_prompt(
        query_type="general_poultry",
        language="en",
        query=test_query,
        inject_terminology=False
    )
    print(f"Length: {len(prompt_without)} chars")
    print(prompt_without[:200] + "..." if len(prompt_without) > 200 else prompt_without)

    # Get system prompt WITH terminology
    print("\n--- System Prompt WITH Terminology ---")
    prompt_with = config.get_system_prompt(
        query_type="general_poultry",
        language="en",
        query=test_query,
        inject_terminology=True,
        max_terminology_tokens=500
    )
    print(f"Length: {len(prompt_with)} chars")

    # Show the difference
    added_length = len(prompt_with) - len(prompt_without)
    print(f"\n Terminology added {added_length} chars to the prompt")

    # Extract and show the terminology section
    if "## Relevant Technical Terminology" in prompt_with:
        terminology_section = prompt_with.split("## Relevant Technical Terminology")[1]
        print("\n Terminology section extracted:")
        print(terminology_section[:500] + "..." if len(terminology_section) > 500 else terminology_section)


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("TERMINOLOGY INJECTION SYSTEM - INTEGRATION TEST")
    print("=" * 80 + "\n")

    try:
        # Test 1: Direct injector testing
        test_terminology_injector()

        # Test 2: Integration with AvicultureConfig
        test_aviculture_config_integration()

        print("\n" + "=" * 80)
        print(" ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
