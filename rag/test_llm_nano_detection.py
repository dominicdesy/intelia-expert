"""Test LLM classifier detection of Intelia products"""
import os
import json
from core.llm_query_classifier import LLMQueryClassifier

# Set API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

def test_nano_detection():
    classifier = LLMQueryClassifier()

    test_queries = [
        "Comment voir les températures dans le nano ?",
        "Comment configurer une alarme sur le compass ?",
        "Quelle est la température du poulailler 2 ?",
        "Comment rentrer la mortalité dans le nano ?",
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")

        result = classifier.classify(query, language="fr")

        print(f"Intent: {result.get('intent')}")
        print(f"Routing target: {result['routing']['target']}")
        print(f"Routing confidence: {result['routing']['confidence']}")
        print(f"Routing reason: {result['routing']['reason']}")

        entities = result.get('entities', {})
        print(f"\nEntities:")
        for key, value in entities.items():
            if value is not None:
                print(f"  {key}: {value}")

        print(f"\nFull JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_nano_detection()
