# Analyse de Couverture des Tests - Intelia Expert LLM

**Date:** 2025-10-06
**Version:** 2.2.2

## Statistiques Actuelles

- **Fichiers source:** ~143 fichiers Python
- **Fichiers de test:** 7 fichiers
- **Tests qui passent:** 22/22 (100%)
- **Ratio de couverture:** ~5% (très faible)

## Tests Existants (22 tests)

### ✅ Testé (22 tests)
- **Proactive Assistant** (6 tests) - Follow-up generation multilingue
- **Hybrid Extraction** (4 tests) - Extraction d'entités (regex, keywords, LLM NER)
- **Adaptive Length** (6 tests) - Calcul de longueur adaptive
- **LLM Ensemble** (6 tests) - Multi-LLM arbitrage (OpenAI, Anthropic, DeepSeek)

## Modules Critiques NON Testés

### 🔴 CRITIQUE - Zéro Test

#### 1. **API Endpoints** (0 tests)
**Fichiers:**
- `api/endpoints.py` - Router principal centralisé
- `api/endpoints_chat.py` - Endpoint /chat principal
- `api/endpoints_diagnostic.py` - Diagnostics système
- `api/endpoints_health.py` - Health checks
- `api/chat_handlers.py` - Handlers de chat

**Risques:**
- Endpoint /chat non testé (point d'entrée principal)
- Validation des inputs non vérifiée
- Erreurs de sérialisation possibles
- Rate limiting non testé en conditions réelles

**Tests nécessaires:**
- Test /chat avec query simple
- Test /chat avec query complexe multilingue
- Test /health endpoint
- Test /diagnostic endpoints
- Test validation d'inputs invalides
- Test rate limiting (10 req/min)
- Test gestion d'erreurs

#### 2. **RAG Core** (0 tests)
**Fichiers:**
- `core/rag_engine.py` - Moteur RAG principal
- `core/rag_engine_core.py` - Core logic
- `core/query_router.py` - Routing de queries
- `core/entity_extractor.py` - Extraction d'entités v3.0
- `core/hybrid_entity_extractor.py` - Extraction hybride

**Risques:**
- Pipeline RAG complet non vérifié end-to-end
- Query routing non testé (PostgreSQL vs Weaviate)
- Entity extraction limitée aux tests unitaires isolés

**Tests nécessaires:**
- Test pipeline RAG complet (query -> retrieval -> generation)
- Test routing vers PostgreSQL vs Weaviate
- Test avec 12 langues supportées
- Test avec différentes espèces/races (Ross 308, Cobb 500, etc.)
- Test métriques (poids, FCR, mortalité, etc.)
- Test extraction d'âge (jours, semaines)

#### 3. **Retrievers** (0 tests)
**Fichiers:**
- `retrieval/postgresql/retriever.py` - Retriever PostgreSQL
- `retrieval/postgresql/normalizer.py` - Query normalizer (14 concepts, 12 langues)
- `retrieval/weaviate/core.py` - Weaviate Core
- `retrieval/weaviate/retriever.py` - Weaviate retriever
- `retrieval/reranker.py` - Cohere Reranker

**Risques:**
- PostgreSQL retriever non testé (source principale de données)
- Normalizer multilingue non vérifié (14 concepts x 12 langues = 168 mappings)
- Weaviate retriever non testé
- Reranker Cohere non vérifié

**Tests nécessaires:**
- Test PostgreSQL retriever avec queries réelles
- Test normalizer multilingue (12 langues)
- Test Weaviate retriever (si données disponibles)
- Test Cohere reranker (top-3 selection)
- Test fallback PostgreSQL si Weaviate down

#### 4. **Generation** (0 tests end-to-end)
**Fichiers:**
- `generation/response_generator.py` - Générateur principal
- `generation/generators.py` - EnhancedResponseGenerator
- `generation/veterinary_handler.py` - Handler vétérinaire
- `generation/proactive_assistant.py` - Tested ✅
- `generation/llm_ensemble.py` - Tested ✅

**Risques:**
- Response generation multilingue non testée complètement
- Disclaimers vétérinaires non vérifiés
- Entity manager non testé

**Tests nécessaires:**
- Test génération FR/EN/ES avec disclaimers
- Test follow-up generation intégré
- Test veterinary handler avec termes médicaux
- Test response length adaptation

#### 5. **Security** (0 tests)
**Fichiers:**
- `security/guardrails/core.py` - GuardrailsOrchestrator
- `security/guardrails/claims_extractor.py` - Extraction de claims
- `security/ood/detector.py` - Out-of-domain detection (12 langues)
- `security/ood/vocabulary_builder.py` - Builder de vocabulaire
- `security/advanced_guardrails.py` - Guardrails legacy

**Risques:**
- Guardrails non testés (security critical!)
- OOD detection non vérifiée (12 langues)
- Claims extraction non testée
- Blocage de queries dangereuses non vérifié

**Tests nécessaires:**
- Test OOD detection (queries in-domain vs out-of-domain)
- Test multilingue (12 langues)
- Test blocked terms (blocked_terms.json)
- Test claims extraction
- Test guardrails orchestrator

#### 6. **Cache Redis** (0 tests)
**Fichiers:**
- `cache/cache_core.py` - RedisCacheCore
- `cache/redis_cache_manager.py` - Cache manager
- `cache/semantic_cache.py` - Semantic caching

**Risques:**
- Cache Redis non testé (performance critique)
- Semantic cache non vérifié
- Cache stats non testées
- Fallback sans cache non vérifié

**Tests nécessaires:**
- Test cache hit/miss
- Test semantic cache (queries similaires)
- Test cache expiration (TTL)
- Test compression
- Test fallback si Redis down
- Test cache stats

#### 7. **Translation** (0 tests)
**Fichiers:**
- `utils/translation_service.py` - UniversalTranslationService
- `utils/language_detection.py` - Détection de langue

**Risques:**
- Service de traduction non testé (12 dictionnaires x 24 domaines = 288 dictionnaires)
- Détection de langue non vérifiée
- Technical exclusions non testées

**Tests nécessaires:**
- Test traduction pour 12 langues
- Test 24 domaines techniques
- Test exclusions techniques (ne pas traduire "Ross 308", "FCR", etc.)
- Test détection de langue
- Test fallback si dictionnaire manquant

#### 8. **Agent RAG** (0 tests)
**Fichiers:**
- `extensions/agent_rag_extension.py` - Agent RAG pour queries complexes

**Risques:**
- Query decomposition non testée
- Multi-document synthesis non vérifiée
- Fallback intent processor non testé

**Tests nécessaires:**
- Test query decomposition
- Test multi-document synthesis
- Test fallback query_router
- Test avec queries complexes multi-critères

#### 9. **Processing** (0 tests)
**Fichiers:**
- `processing/intent_processor.py` - Intent classification
- `processing/query_processor.py` - Query processing

**Risques:**
- Intent classification non testée (5 intents)
- Query processing non vérifié

**Tests nécessaires:**
- Test intent classification (5 intents)
- Test slot extraction
- Test multilingue

#### 10. **Monitoring** (0 tests)
**Fichiers:**
- `utils/monitoring.py` - SystemHealthMonitor

**Risques:**
- Health checks non testés
- Startup validation non vérifiée

**Tests nécessaires:**
- Test health checks
- Test startup requirements
- Test mode dégradé vs complet

## Recommandations par Priorité

### 🔴 PRIORITÉ 1 - Tests End-to-End (CRITIQUE)

**Test 1: Pipeline RAG Complet**
```python
async def test_rag_pipeline_end_to_end():
    """Test complet: query -> retrieval -> generation -> response"""

    queries = [
        {"text": "Quel poids pour Ross 308 à 35 jours ?", "lang": "fr"},
        {"text": "What is the weight of Ross 308 at 35 days?", "lang": "en"},
        {"text": "¿Cuál es el peso de Ross 308 a los 35 días?", "lang": "es"},
    ]

    for query in queries:
        response = await rag_engine.query(
            text=query["text"],
            language=query["lang"]
        )

        assert response is not None
        assert len(response["answer"]) > 50
        assert response["language"] == query["lang"]
        assert "sources" in response
        assert len(response["sources"]) > 0
```

**Test 2: API Endpoint /chat**
```python
async def test_chat_endpoint():
    """Test l'endpoint /chat principal"""

    response = client.post("/chat", json={
        "message": "Quel poids pour Ross 308 à 35 jours ?",
        "language": "fr",
        "user_id": "test_user"
    })

    assert response.status_code == 200
    data = response.json()

    assert "response" in data
    assert "sources" in data
    assert "follow_up" in data  # Proactive assistant
    assert len(data["response"]) > 50
```

### 🟡 PRIORITÉ 2 - Tests de Retrievers

**Test 3: PostgreSQL Retriever + Normalizer**
```python
async def test_postgresql_retriever_multilingual():
    """Test retriever PostgreSQL avec normalizer multilingue"""

    queries_12_langs = [
        ("Poids Ross 308", "fr"),
        ("Weight Ross 308", "en"),
        ("Peso Ross 308", "es"),
        # ... 9 autres langues
    ]

    for query, lang in queries_12_langs:
        results = await pg_retriever.retrieve(query, language=lang)

        assert len(results) > 0
        assert results[0].score > 0.5
```

**Test 4: Cohere Reranker**
```python
async def test_cohere_reranker():
    """Test Cohere reranker (rerank-multilingual-v3.0)"""

    docs = [...10 documents...]
    query = "Quel est le poids optimal pour Ross 308 à 35 jours ?"

    reranked = await reranker.rerank(query, docs, top_n=3)

    assert len(reranked) == 3
    assert reranked[0].score > reranked[1].score
```

### 🟢 PRIORITÉ 3 - Tests de Sécurité

**Test 5: OOD Detection (12 langues)**
```python
async def test_ood_detector_multilingual():
    """Test OOD detection pour 12 langues"""

    in_domain = [
        "Quel poids pour Ross 308 ?",  # FR - IN
        "What is Ross 308 weight?",    # EN - IN
        "¿Peso de Ross 308?",          # ES - IN
    ]

    out_domain = [
        "Comment réparer ma voiture ?",  # FR - OUT
        "Recipe for chocolate cake",     # EN - OUT
        "¿Cómo aprender piano?",        # ES - OUT
    ]

    for query in in_domain:
        result = await ood_detector.detect(query)
        assert result["is_in_domain"] == True

    for query in out_domain:
        result = await ood_detector.detect(query)
        assert result["is_in_domain"] == False
```

**Test 6: Guardrails + Blocked Terms**
```python
async def test_guardrails_blocked_terms():
    """Test guardrails avec blocked_terms.json"""

    blocked = [
        "Comment tuer un poulet ?",
        "Poison for chickens",
    ]

    for query in blocked:
        result = await guardrails.check(query)
        assert result["blocked"] == True
        assert result["reason"] is not None
```

### 🟣 PRIORITÉ 4 - Tests de Performance

**Test 7: Cache Redis**
```python
async def test_redis_cache_performance():
    """Test cache hit/miss et performance"""

    query = "Poids Ross 308 35 jours"

    # First call - MISS
    start = time.time()
    result1 = await rag_engine.query(query)
    time_miss = time.time() - start

    # Second call - HIT
    start = time.time()
    result2 = await rag_engine.query(query)
    time_hit = time.time() - start

    assert result1 == result2
    assert time_hit < time_miss * 0.2  # Cache 5x plus rapide
```

**Test 8: Rate Limiting**
```python
async def test_rate_limiting():
    """Test rate limiting (10 req/min/user)"""

    user_id = "test_user"

    # 10 requêtes OK
    for i in range(10):
        response = client.post("/chat", json={
            "message": f"Query {i}",
            "user_id": user_id
        })
        assert response.status_code == 200

    # 11ème requête = 429 Too Many Requests
    response = client.post("/chat", json={
        "message": "Query 11",
        "user_id": user_id
    })
    assert response.status_code == 429
```

### 🔵 PRIORITÉ 5 - Tests de Translation

**Test 9: Translation Service (12 langues x 24 domaines)**
```python
async def test_translation_service_coverage():
    """Test service de traduction pour 12 langues"""

    languages = ["fr", "en", "es", "de", "it", "pt", "pl", "nl", "id", "hi", "zh", "th"]
    domains = ["genetic_lines", "clinical_signs", "substrate_materials", ...]

    for lang in languages:
        for domain in domains:
            result = translation_service.translate(
                text="Ross 308 weight",
                from_lang="en",
                to_lang=lang,
                domain=domain
            )

            assert result is not None
            assert "Ross 308" in result  # Technical term preserved
```

## Plan d'Action Recommandé

### Option A: Tests Essentiels (2-3 heures)
**Focus:** Tests end-to-end critiques seulement
- ✅ Test /chat endpoint (30 min)
- ✅ Test RAG pipeline complet (1h)
- ✅ Test retrievers PostgreSQL + Weaviate (1h)
- ✅ Test OOD detection multilingue (30 min)

**Couverture:** ~30% des risques critiques

### Option B: Tests Complets (1-2 jours)
**Focus:** Couverture complète de tous les modules
- ✅ Tous les tests de l'Option A
- ✅ Tests de sécurité (guardrails, blocked terms)
- ✅ Tests de cache Redis
- ✅ Tests de translation (12 langues)
- ✅ Tests de performance
- ✅ Tests de rate limiting
- ✅ Tests Agent RAG
- ✅ Tests monitoring

**Couverture:** ~80% des risques

### Option C: Tests de Régression Continue (Setup CI/CD)
**Focus:** Tests automatiques sur chaque commit
- ✅ GitHub Actions avec pytest
- ✅ Tests sur chaque push vers main
- ✅ Coverage reports automatiques
- ✅ Tests de performance sur schedule

**Bénéfice:** Protection continue

## Conclusion

**État actuel:** Le système fonctionne à 100% en production (Mode COMPLET), mais seulement **5% du code est testé**.

**Risque:** Modifications futures peuvent casser des fonctionnalités critiques sans détection.

**Recommandation:** Minimum **Option A (tests essentiels)**, idéalement **Option B (tests complets)**.

**Note importante:** Les 22 tests actuels sont excellents mais ne couvrent que des modules isolés. Le pipeline RAG complet (API -> Routing -> Retrieval -> Generation -> Response) n'a **jamais été testé end-to-end**.
