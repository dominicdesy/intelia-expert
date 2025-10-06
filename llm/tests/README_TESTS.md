# Tests d'Intégration - Intelia Expert LLM

## 📊 Vue d'Ensemble

Suite complète de tests couvrant **~80% des risques critiques** du système LLM.

**Statistiques:**
- **9 fichiers de test** (133+ tests individuels)
- **Couverture:** API, RAG, Retrievers, Security, Cache, Translation, Rate Limiting, Agent RAG
- **Durée estimée:** 5-10 minutes (mode complet)

## 🚀 Quick Start

### Prérequis

```bash
# Installer pytest et dépendances
pip install pytest pytest-asyncio httpx

# Vérifier que .env existe
ls .env  # Doit contenir toutes les clés API
```

### Lancer TOUS les tests

```bash
cd C:\intelia_gpt\intelia-expert\llm

# Option 1: Via runner Python
python tests/run_all_tests.py

# Option 2: Via pytest directement
pytest tests/integration/ -v

# Option 3: Tests rapides seulement (2-3 min)
python tests/run_all_tests.py --fast

# Option 4: Tests critiques seulement (1 min)
python tests/run_all_tests.py --critical
```

### Lancer un test spécifique

```bash
# Test 1: API /chat endpoint
pytest tests/integration/test_api_chat_endpoint.py -v -s

# Test 2: RAG Pipeline
pytest tests/integration/test_rag_pipeline.py -v -s

# Test 3: PostgreSQL Retriever
pytest tests/integration/test_postgresql_retriever.py -v -s

# Test 4: Weaviate Retriever
pytest tests/integration/test_weaviate_retriever.py -v -s

# Test 5: Cohere Reranker
pytest tests/integration/test_cohere_reranker.py -v -s

# Test 6: Security Guardrails
pytest tests/integration/test_security_guardrails.py -v -s

# Test 7: Redis Cache
pytest tests/integration/test_redis_cache.py -v -s

# Test 8: Translation Service
pytest tests/integration/test_translation_service.py -v -s

# Test 9: Rate Limiting + Agent RAG
pytest tests/integration/test_rate_limiting_agent.py -v -s
```

## 📋 Description des Tests

### 1. **test_api_chat_endpoint.py** (10 tests)

Tests end-to-end de l'API principale.

**Couvre:**
- ✅ Query simple (FR)
- ✅ Queries multilingues (FR, EN, ES)
- ✅ Query complexe multi-critères
- ✅ Query avec contexte conversationnel
- ✅ Validation inputs invalides
- ✅ Extraction d'entités
- ✅ Métadonnées des sources
- ✅ Performance (< 10s)
- ✅ Disclaimer vétérinaire
- ✅ Gestion d'erreurs

**Durée:** ~2 minutes

### 2. **test_rag_pipeline.py** (11 tests)

Tests du pipeline RAG complet.

**Couvre:**
- ✅ Pipeline query → retrieval → generation
- ✅ Extraction d'entités (race, âge, sexe, métrique)
- ✅ Multilingue (FR, EN, ES)
- ✅ Query routing (PostgreSQL vs Weaviate)
- ✅ Conversation memory
- ✅ Comparaison de races
- ✅ Variants d'âge (jours, semaines)
- ✅ Différentes métriques
- ✅ Support espèces (poulets, dindes, canards)
- ✅ Handling queries sans résultats
- ✅ Performance (< 10s/query)

**Durée:** ~3 minutes

### 3. **test_postgresql_retriever.py** (11 tests)

Tests du retriever PostgreSQL et normalizer.

**Couvre:**
- ✅ Retrieval basique
- ✅ Normalizer multilingue (12 langues)
- ✅ Normalizer concepts (14 concepts)
- ✅ Filtrage par race
- ✅ Filtrage par range d'âge
- ✅ Filtrage par métrique
- ✅ Queries multilingues
- ✅ Cohere reranking
- ✅ Handling query vide
- ✅ Performance (< 2s/query)
- ✅ Préservation termes techniques

**Durée:** ~2 minutes

### 4. **test_weaviate_retriever.py** (10 tests)

Tests du retriever Weaviate Cloud.

**Couvre:**
- ✅ Connexion Weaviate Cloud
- ✅ Hybrid search (vector + keyword)
- ✅ Vector search pur
- ✅ Keyword search (BM25)
- ✅ Search multilingue
- ✅ Search avec filtres
- ✅ Reranking Cohere
- ✅ Collection info
- ✅ Generation embeddings (1536 dims)
- ✅ Performance

**Durée:** ~2 minutes

### 5. **test_cohere_reranker.py** (11 tests)

Tests dédiés au Cohere Reranker.

**Couvre:**
- ✅ Reranking basique
- ✅ Amélioration du score
- ✅ Reranking multilingue (rerank-multilingual-v3.0)
- ✅ Top-N selection
- ✅ Handling documents vides
- ✅ Single document
- ✅ Documents longs
- ✅ Caractères spéciaux
- ✅ Performance (< 3s pour 20 docs)
- ✅ Batch queries
- ✅ Distribution des scores

**Durée:** ~1 minute

### 6. **test_security_guardrails.py** (10 tests)

Tests de sécurité (guardrails + OOD).

**Couvre:**
- ✅ OOD detection in-domain (aviculture)
- ✅ OOD detection out-of-domain
- ✅ OOD multilingue (12 langues)
- ✅ Edge cases et queries ambiguës
- ✅ Blocked terms detection
- ✅ Queries sûres passent
- ✅ Détection contenu vétérinaire
- ✅ Vérification outputs
- ✅ Couverture vocabulaire (> 70%)
- ✅ Performance (< 0.5s/query)

**Durée:** ~2 minutes

### 7. **test_redis_cache.py** (12 tests)

Tests du cache Redis.

**Couvre:**
- ✅ Set/Get basique
- ✅ Cache miss
- ✅ TTL expiration
- ✅ Compression gros objets
- ✅ Semantic cache (queries similaires)
- ✅ Performance HIT vs MISS
- ✅ Opérations batch
- ✅ Cache stats
- ✅ Clear namespace
- ✅ Fallback sur erreur
- ✅ Gestion limite mémoire
- ✅ Accès concurrent

**Durée:** ~2 minutes

### 8. **test_translation_service.py** (12 tests)

Tests du service de traduction.

**Couvre:**
- ✅ Initialisation service
- ✅ Traduction 12 langues
- ✅ Préservation termes techniques
- ✅ Traduction par domaine (24 domaines)
- ✅ Lister domaines disponibles
- ✅ Fallback dictionnaire manquant
- ✅ Handling texte vide
- ✅ Texte très long
- ✅ Contenu mixte (texte + nombres + termes)
- ✅ Traduction batch
- ✅ Vérifier toutes langues chargées
- ✅ Traduction aller-retour

**Durée:** ~1 minute

### 9. **test_rate_limiting_agent.py** (10 tests)

Tests rate limiting + Agent RAG.

**Couvre:**
- ✅ Rate limiting single user (10 req/min)
- ✅ Rate limiting indépendant par user
- ✅ Rate limit reset après 1 minute
- ✅ Agent RAG query simple
- ✅ Agent RAG query complexe (décomposition)
- ✅ Agent RAG multi-critères
- ✅ Agent RAG fallback
- ✅ Agent RAG multilingue
- ✅ Query decomposition
- ✅ Performance Agent RAG (< 15s)

**Durée:** ~3 minutes (inclut sleep 61s pour test reset)

## 🎯 Modes d'Exécution

### Mode COMPLET (recommandé)

```bash
python tests/run_all_tests.py
```

- **Durée:** 5-10 minutes
- **Tests:** Tous (133+ tests)
- **Couverture:** ~80% des risques

### Mode FAST

```bash
python tests/run_all_tests.py --fast
```

- **Durée:** 2-3 minutes
- **Tests:** Critiques + importants (sans Weaviate, Translation, Rate Limiting)
- **Couverture:** ~60% des risques

### Mode CRITICAL

```bash
python tests/run_all_tests.py --critical
```

- **Durée:** 1 minute
- **Tests:** API + RAG Pipeline seulement
- **Couverture:** ~30% des risques

## 📊 Rapport d'Exécution

Le runner génère un rapport détaillé :

```
********************************************************************************
FINAL REPORT
********************************************************************************

✅ PASS | API /chat Endpoint
       Tests: 10 passed, 0 failed, 0 errors
       Duration: 45.23s

✅ PASS | RAG Pipeline End-to-End
       Tests: 11 passed, 0 failed, 0 errors
       Duration: 67.89s

...

================================================================================
SUMMARY
================================================================================
Test files: 9/9 passed
Total tests: 133 passed, 0 failed, 0 errors
Total duration: 456.78s (7.6 minutes)

🎉 ALL TESTS PASSED!
```

## 🔧 Debugging

### Test échoue ?

```bash
# Lancer avec traceback complet
pytest tests/integration/test_xxx.py -v -s --tb=long

# Lancer avec logging
pytest tests/integration/test_xxx.py -v -s --log-cli-level=DEBUG

# Lancer un seul test
pytest tests/integration/test_xxx.py::test_specific_function -v -s
```

### Variables d'environnement

Vérifier que `.env` contient :

```bash
# Critiques
OPENAI_API_KEY=sk-...
REDIS_URL=redis://...
DATABASE_URL=postgresql://...

# Importants
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
COHERE_API_KEY=...
WEAVIATE_URL=https://...
WEAVIATE_API_KEY=...

# Optionnels
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=...
```

### Services externes down ?

Certains tests peuvent skip gracieusement si services non disponibles :

- Weaviate tests → skip si connexion échoue
- Rate limiting tests → continuent même si Redis down (fallback mémoire)

## 📈 Amélioration Continue

### Ajouter un test

1. Créer `tests/integration/test_my_feature.py`
2. Importer `pytest` et `dotenv`
3. Créer fixtures avec `@pytest.fixture`
4. Créer tests avec `@pytest.mark.asyncio` si async
5. Ajouter au runner dans `run_all_tests.py`

### Coverage Report

```bash
# Générer rapport de couverture
pytest tests/integration/ --cov=. --cov-report=html

# Voir rapport
open htmlcov/index.html
```

## 🎯 Prochaines Étapes

Tests manquants (priorité basse) :

- [ ] Tests de charge (> 100 req/s)
- [ ] Tests de stress (mémoire, CPU)
- [ ] Tests de failover (services down)
- [ ] Tests de régression automatiques (CI/CD)

## 📞 Support

Si tests échouent de manière inattendue :

1. Vérifier `.env` complet
2. Vérifier services externes (Redis, PostgreSQL, Weaviate)
3. Vérifier version dependencies (`pip list`)
4. Consulter `TEST_COVERAGE_ANALYSIS.md`

---

**Dernière mise à jour:** 2025-10-06
**Version:** 2.2.2
