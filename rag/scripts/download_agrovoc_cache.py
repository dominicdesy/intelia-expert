# -*- coding: utf-8 -*-
"""
Download AGROVOC poultry terms cache for all supported languages
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Download AGROVOC poultry terms cache for all supported languages

This script downloads all poultry-related terms from AGROVOC FAO database
for the 10 languages supported by AGROVOC (fr, en, es, de, it, pt, pl, hi, th, zh).

Output: llm/services/agrovoc_poultry_cache.json
"""

import requests
import json
import time
from typing import Dict, Set, List

# AGROVOC supported languages (10/12 of Intelia Expert's languages)
AGROVOC_LANGUAGES = ["fr", "en", "es", "de", "it", "pt", "pl", "hi", "th", "zh"]

# AGROVOC SPARQL endpoint
SPARQL_ENDPOINT = "https://agrovoc.fao.org/sparql"

# Key poultry-related concept URIs in AGROVOC
POULTRY_CONCEPTS = [
    "http://aims.fao.org/aos/agrovoc/c_6105",  # poultry
    "http://aims.fao.org/aos/agrovoc/c_1521",  # chickens
    "http://aims.fao.org/aos/agrovoc/c_1328",  # broilers
    "http://aims.fao.org/aos/agrovoc/c_4397",  # layers
    "http://aims.fao.org/aos/agrovoc/c_6106",  # poultry diseases
    "http://aims.fao.org/aos/agrovoc/c_6107",  # poultry farming
    "http://aims.fao.org/aos/agrovoc/c_6108",  # poultry meat
    "http://aims.fao.org/aos/agrovoc/c_6109",  # poultry products
]


def download_terms_for_concept(
    concept_uri: str, language: str, max_depth: int = 2
) -> Set[str]:
    """
    Download all terms for a concept and its narrower concepts (up to max_depth)

    Args:
        concept_uri: AGROVOC concept URI
        language: Language code (en, fr, es, etc.)
        max_depth: Maximum depth for narrower concepts (default: 2)

    Returns:
        Set of terms (prefLabel and altLabel)
    """
    query = f"""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT DISTINCT ?label
    WHERE {{
        <{concept_uri}> skos:narrower{{0,{max_depth}}} ?concept .
        ?concept skos:prefLabel|skos:altLabel ?label .
        FILTER(LANG(?label) = "{language}")
    }}
    """

    try:
        response = requests.get(
            SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            terms = set()

            for binding in results["results"]["bindings"]:
                label = binding["label"]["value"].lower()
                terms.add(label)

            return terms
        else:
            print(
                f"  [ERROR] HTTP {response.status_code} for {concept_uri} ({language})"
            )
            return set()

    except Exception as e:
        print(f"  [ERROR] {str(e)[:50]} for {concept_uri} ({language})")
        return set()


def download_agrovoc_cache() -> Dict[str, List[str]]:
    """
    Download AGROVOC poultry terms cache for all supported languages

    Returns:
        Dictionary mapping "language:term" -> True
    """
    print("=" * 80)
    print("DOWNLOADING AGROVOC POULTRY TERMS CACHE")
    print("=" * 80)
    print(f"Languages: {', '.join(AGROVOC_LANGUAGES)}")
    print(f"Concepts: {len(POULTRY_CONCEPTS)}")
    print(f"Total queries: {len(AGROVOC_LANGUAGES) * len(POULTRY_CONCEPTS)}")
    print()

    cache = {}

    for language in AGROVOC_LANGUAGES:
        print(f"Processing {language}...")
        language_terms = set()

        for i, concept_uri in enumerate(POULTRY_CONCEPTS, 1):
            concept_name = concept_uri.split("/")[-1]
            print(f"  [{i}/{len(POULTRY_CONCEPTS)}] {concept_name}...", end=" ")

            terms = download_terms_for_concept(concept_uri, language)
            language_terms.update(terms)

            print(f"{len(terms)} terms")

            # Rate limiting (be nice to FAO servers)
            time.sleep(0.5)

        print(f"  Total: {len(language_terms)} unique terms for {language}")
        print()

        # Store terms as "language:term" keys for fast lookup
        for term in language_terms:
            cache_key = f"{language}:{term}"
            cache[cache_key] = True

    return cache


def save_cache(cache: Dict[str, bool], filename: str = None):
    """Save cache to JSON file in services/ directory"""
    if filename is None:
        # Save in llm/services/ directory
        from pathlib import Path

        services_dir = Path(__file__).parent.parent / "services"
        filename = str(services_dir / "agrovoc_poultry_cache.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print(f"Cache saved to: {filename}")
    print(f"Total entries: {len(cache)}")
    print(f"File size: {len(json.dumps(cache)) / 1024:.1f} KB")
    print("=" * 80)


def generate_stats(cache: Dict[str, bool]):
    """Generate statistics about the cache"""
    stats = {}

    for key in cache.keys():
        lang = key.split(":")[0]
        if lang not in stats:
            stats[lang] = 0
        stats[lang] += 1

    print("\nSTATISTICS BY LANGUAGE:")
    print("-" * 40)
    for lang in sorted(stats.keys()):
        print(f"  {lang}: {stats[lang]:,} terms")
    print("-" * 40)
    print(f"  TOTAL: {len(cache):,} entries")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("AGROVOC POULTRY TERMS CACHE DOWNLOADER")
    print("=" * 80)
    print()
    print("This will download all poultry-related terms from AGROVOC")
    print("for 10 languages (fr, en, es, de, it, pt, pl, hi, th, zh).")
    print()
    print("Estimated time: 2-5 minutes")
    print("=" * 80)
    print()

    # Download cache
    cache = download_agrovoc_cache()

    # Generate statistics
    generate_stats(cache)

    # Save cache
    save_cache(cache)

    print("\n[SUCCESS] AGROVOC cache downloaded successfully!")
    print("\nYou can now use this cache in your application with:")
    print("  from services.agrovoc_service import AGROVOCService")
    print("  agrovoc = AGROVOCService()")
    print("  agrovoc.is_poultry_term('spaghetti breast', 'en')  # -> True")
