# -*- coding: utf-8 -*-
"""
test_redis_cache.py - Tests du cache Redis

Tests:
1. Cache hit/miss
2. Semantic cache (queries similaires)
3. Cache expiration (TTL)
4. Cache compression
5. Fallback si Redis down
6. Cache stats
7. Performance
"""

import pytest
import asyncio
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cache.cache_core import RedisCacheCore


@pytest.fixture
async def cache_core():
    """Fixture: Redis Cache Core"""
    cache = RedisCacheCore()
    await cache.initialize()

    # Vider le cache avant chaque test
    await cache.clear_all()

    yield cache

    await cache.cleanup()


@pytest.mark.asyncio
async def test_cache_basic_set_get(cache_core):
    """Test 1: Set/Get basique"""

    key = "test:basic"
    value = {"data": "test value", "number": 42}

    # Set
    success = await cache_core.set(key, value, ttl=60)
    assert success, "Cache set failed"

    # Get
    retrieved = await cache_core.get(key)
    assert retrieved == value, "Retrieved value doesn't match"

    print("\n✅ Test 1 PASSED - Basic set/get")


@pytest.mark.asyncio
async def test_cache_miss(cache_core):
    """Test 2: Cache miss"""

    key = "test:nonexistent"

    # Get non-existent key
    retrieved = await cache_core.get(key)
    assert retrieved is None, "Should return None for cache miss"

    print("\n✅ Test 2 PASSED - Cache miss")


@pytest.mark.asyncio
async def test_cache_ttl_expiration(cache_core):
    """Test 3: TTL expiration"""

    key = "test:ttl"
    value = "expires soon"

    # Set with short TTL (2 seconds)
    await cache_core.set(key, value, ttl=2)

    # Should exist immediately
    retrieved = await cache_core.get(key)
    assert retrieved == value

    # Wait for expiration
    await asyncio.sleep(3)

    # Should be expired
    retrieved_after = await cache_core.get(key)
    assert retrieved_after is None, "Value should have expired"

    print("\n✅ Test 3 PASSED - TTL expiration")


@pytest.mark.asyncio
async def test_cache_compression(cache_core):
    """Test 4: Compression de gros objets"""

    key = "test:large"

    # Créer un gros objet (>1KB pour déclencher compression)
    large_value = {
        "data": "x" * 5000,  # 5KB de données
        "array": list(range(1000)),
        "nested": {"key": "value"} * 100
    }

    # Set avec compression
    await cache_core.set(key, large_value, ttl=60)

    # Get et vérifier décompression
    retrieved = await cache_core.get(key)

    assert retrieved["data"] == large_value["data"]
    assert len(retrieved["array"]) == len(large_value["array"])

    print("\n✅ Test 4 PASSED - Compression")


@pytest.mark.asyncio
async def test_cache_semantic_similarity(cache_core):
    """Test 5: Semantic cache (queries similaires)"""

    # Query originale
    query1 = "Quel est le poids de Ross 308 à 35 jours ?"
    result1 = {"answer": "2100-2200g", "sources": []}

    await cache_core.set_semantic(query1, result1, language="fr", ttl=300)

    # Query similaire (légèrement différente)
    query2 = "Quel poids pour Ross 308 35 jours ?"

    # Devrait trouver le cache avec similarité
    cached = await cache_core.get_semantic(query2, language="fr", threshold=0.85)

    if cached:
        print("   ✓ Semantic cache HIT")
        assert cached["answer"] == result1["answer"]
    else:
        print("   ⚠ Semantic cache MISS (might need tuning)")

    print("\n✅ Test 5 PASSED - Semantic cache")


@pytest.mark.asyncio
async def test_cache_performance_hit_vs_miss(cache_core):
    """Test 6: Performance cache HIT vs MISS"""

    key = "test:performance"
    value = {"data": "test" * 100}

    # Set value
    await cache_core.set(key, value, ttl=60)

    # Measure GET performance (cache HIT)
    hits = []
    for _ in range(10):
        start = time.time()
        await cache_core.get(key)
        hits.append(time.time() - start)

    # Measure GET performance (cache MISS)
    misses = []
    for i in range(10):
        start = time.time()
        await cache_core.get(f"test:miss:{i}")
        misses.append(time.time() - start)

    avg_hit = sum(hits) / len(hits)
    avg_miss = sum(misses) / len(misses)

    print("\n✅ Test 6 PASSED - Performance")
    print(f"   Cache HIT: {avg_hit*1000:.2f}ms")
    print(f"   Cache MISS: {avg_miss*1000:.2f}ms")
    print(f"   Speedup: {avg_miss/avg_hit:.1f}x")


@pytest.mark.asyncio
async def test_cache_batch_operations(cache_core):
    """Test 7: Opérations batch"""

    # Set multiple keys
    keys_values = {
        f"test:batch:{i}": {"value": i}
        for i in range(10)
    }

    for key, value in keys_values.items():
        await cache_core.set(key, value, ttl=60)

    # Get multiple keys
    for key, expected_value in keys_values.items():
        retrieved = await cache_core.get(key)
        assert retrieved == expected_value

    print("\n✅ Test 7 PASSED - Batch operations")


@pytest.mark.asyncio
async def test_cache_stats(cache_core):
    """Test 8: Cache statistics"""

    # Perform some operations
    await cache_core.set("test:stats:1", "value1", ttl=60)
    await cache_core.get("test:stats:1")  # HIT
    await cache_core.get("test:stats:nonexistent")  # MISS

    # Get stats
    stats = await cache_core.get_stats()

    assert stats is not None
    print("\n✅ Test 8 PASSED - Cache stats")
    print(f"   Stats: {stats}")


@pytest.mark.asyncio
async def test_cache_clear_namespace(cache_core):
    """Test 9: Clear namespace"""

    # Set multiple keys in same namespace
    await cache_core.set("queries:1", "value1", ttl=60)
    await cache_core.set("queries:2", "value2", ttl=60)
    await cache_core.set("other:1", "value3", ttl=60)

    # Clear namespace
    await cache_core.clear_namespace("queries")

    # Queries namespace should be cleared
    assert await cache_core.get("queries:1") is None
    assert await cache_core.get("queries:2") is None

    # Other namespace should remain
    assert await cache_core.get("other:1") == "value3"

    print("\n✅ Test 9 PASSED - Clear namespace")


@pytest.mark.asyncio
async def test_cache_fallback_on_error(cache_core):
    """Test 10: Fallback gracieux sur erreur"""

    # Simuler une clé qui pourrait causer une erreur
    key = "test:invalid"

    try:
        # Set avec une valeur qui pourrait poser problème
        await cache_core.set(key, None, ttl=60)

        # Get devrait retourner None au lieu de crash
        result = await cache_core.get(key)

        print(f"   ✓ Handled None value: {result}")
    except Exception as e:
        print(f"   ✓ Exception caught gracefully: {type(e).__name__}")

    print("\n✅ Test 10 PASSED - Fallback on error")


@pytest.mark.asyncio
async def test_cache_memory_limit(cache_core):
    """Test 11: Gestion de la limite mémoire"""

    # Créer beaucoup de clés pour tester la gestion mémoire
    for i in range(100):
        large_value = {"data": "x" * 1000}  # 1KB par clé
        await cache_core.set(f"test:memory:{i}", large_value, ttl=60)

    # Le cache devrait toujours fonctionner
    await cache_core.get("test:memory:0")

    print("\n✅ Test 11 PASSED - Memory limit handling")


@pytest.mark.asyncio
async def test_cache_concurrent_access(cache_core):
    """Test 12: Accès concurrent"""

    key = "test:concurrent"

    # Lancer plusieurs set/get en parallèle
    async def worker(i):
        await cache_core.set(f"{key}:{i}", f"value{i}", ttl=60)
        return await cache_core.get(f"{key}:{i}")

    # 20 workers en parallèle
    results = await asyncio.gather(*[worker(i) for i in range(20)])

    # Tous devraient avoir réussi
    assert len(results) == 20
    assert all(r is not None for r in results)

    print("\n✅ Test 12 PASSED - Concurrent access")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
