#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify msgpack compatibility with cache data types
"""

import msgpack
import sys

def test_embedding_serialization():
    """Test embedding list serialization"""
    print("Testing embedding serialization...")

    # Simulate an embedding vector (list of floats)
    embedding = [0.123, -0.456, 0.789, 1.234, -2.345] * 10  # 50 floats

    # Serialize with msgpack
    serialized = msgpack.packb(embedding, use_bin_type=True)

    # Deserialize
    deserialized = msgpack.unpackb(serialized, raw=False)

    # Verify
    assert len(embedding) == len(deserialized), "Length mismatch"
    for i, (orig, deser) in enumerate(zip(embedding, deserialized)):
        assert abs(orig - deser) < 0.0001, f"Value mismatch at index {i}"

    print("[OK] Embedding serialization OK")
    return True

def test_intent_result_serialization():
    """Test intent result dictionary serialization"""
    print("Testing intent result serialization...")

    # Simulate intent result data
    intent_result = {
        "intent_type": "performance_query",
        "confidence": 0.95,
        "detected_entities": {
            "line": "ross308",
            "metric": "fcr",
            "age": "35j"
        },
        "expanded_query": "Quel est le FCR pour Ross 308 à 35 jours?"
    }

    # Serialize with msgpack
    serialized = msgpack.packb(intent_result, use_bin_type=True)

    # Deserialize
    deserialized = msgpack.unpackb(serialized, raw=False)

    # Verify
    assert deserialized["intent_type"] == intent_result["intent_type"]
    assert abs(deserialized["confidence"] - intent_result["confidence"]) < 0.0001
    assert deserialized["detected_entities"]["line"] == "ross308"
    assert deserialized["expanded_query"] == intent_result["expanded_query"]

    print("[OK] Intent result serialization OK")
    return True

def test_nested_structures():
    """Test nested data structures"""
    print("Testing nested structures...")

    # Complex nested structure
    data = {
        "query": "Test query",
        "results": [
            {"id": 1, "score": 0.95, "metadata": {"source": "pubmed"}},
            {"id": 2, "score": 0.87, "metadata": {"source": "local"}}
        ],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
        "config": {
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }

    # Serialize with msgpack
    serialized = msgpack.packb(data, use_bin_type=True)

    # Deserialize
    deserialized = msgpack.unpackb(serialized, raw=False)

    # Verify structure
    assert deserialized["query"] == data["query"]
    assert len(deserialized["results"]) == 2
    assert deserialized["results"][0]["score"] == 0.95
    assert deserialized["embeddings"][1][1] == 0.4
    assert deserialized["config"]["temperature"] == 0.7

    print("[OK] Nested structures OK")
    return True

def test_unicode_strings():
    """Test Unicode string handling"""
    print("Testing Unicode strings...")

    # French text with accents
    data = {
        "question": "Quelle est la température idéale pour Ross 308?",
        "answer": "La température recommandée est de 32°C au démarrage"
    }

    # Serialize with msgpack
    serialized = msgpack.packb(data, use_bin_type=True)

    # Deserialize
    deserialized = msgpack.unpackb(serialized, raw=False)

    # Verify
    assert deserialized["question"] == data["question"]
    assert deserialized["answer"] == data["answer"]
    assert "température" in deserialized["question"]
    assert "°C" in deserialized["answer"]

    print("[OK] Unicode strings OK")
    return True

def test_size_comparison():
    """Compare msgpack vs pickle size"""
    print("\nSize comparison (msgpack vs pickle)...")

    import pickle

    # Large embedding vector
    embedding = [float(i) * 0.001 for i in range(1536)]  # OpenAI embedding size

    msgpack_size = len(msgpack.packb(embedding, use_bin_type=True))
    pickle_size = len(pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL))

    print(f"  Embedding (1536 floats):")
    print(f"    msgpack: {msgpack_size} bytes")
    print(f"    pickle:  {pickle_size} bytes")
    print(f"    Difference: {((msgpack_size - pickle_size) / pickle_size * 100):+.1f}%")

    # Intent result
    intent_data = {
        "intent_type": "performance_query",
        "confidence": 0.95,
        "detected_entities": {"line": "ross308", "metric": "fcr", "age": "35j"},
        "expanded_query": "Quel est le FCR pour Ross 308 à 35 jours?"
    }

    msgpack_size = len(msgpack.packb(intent_data, use_bin_type=True))
    pickle_size = len(pickle.dumps(intent_data, protocol=pickle.HIGHEST_PROTOCOL))

    print(f"  Intent result dict:")
    print(f"    msgpack: {msgpack_size} bytes")
    print(f"    pickle:  {pickle_size} bytes")
    print(f"    Difference: {((msgpack_size - pickle_size) / pickle_size * 100):+.1f}%")

    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("MSGPACK MIGRATION COMPATIBILITY TESTS")
    print("=" * 60)
    print()

    tests = [
        test_embedding_serialization,
        test_intent_result_serialization,
        test_nested_structures,
        test_unicode_strings,
        test_size_comparison
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[FAILED] {test.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print()
        print("[SUCCESS] All tests passed! msgpack migration is compatible.")
        return 0
    else:
        print()
        print("[ERROR] Some tests failed. Please review the errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
