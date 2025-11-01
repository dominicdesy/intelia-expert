"""Test entity extraction for nano detection"""
import asyncio
import logging
from core.entity_extractor import EntityExtractor

logging.basicConfig(level=logging.DEBUG)

async def test():
    extractor = EntityExtractor()

    query = "Comment voir les températures dans le nano ?"

    print(f"\n{'='*80}")
    print(f"Testing query: {query}")
    print(f"{'='*80}\n")

    result = extractor.extract(query)

    print(f"\n{'='*80}")
    print("Extraction result:")
    print(f"{'='*80}")
    print(f"intelia_product: {result.intelia_product}")
    print(f"metric_type: {result.metric_type}")
    print(f"confidence_breakdown: {result.confidence_breakdown}")
    print(f"\nFull dict:")
    for k, v in result.to_dict().items():
        if v is not None and v != 0.0 and v != {} and v != []:
            print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(test())
