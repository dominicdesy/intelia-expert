# Intégration Complète RAG ↔ LLM

**Version**: 2.0
**Date**: 2025-01-15
**Statut**: ✅ Complètement intégré et synchronisé

---

## Vue d'ensemble

Ce document explique comment les bases de données RAG (Weaviate + PostgreSQL) sont intégrées avec le système LLM pour maximiser l'accès aux données.

---

## 1. Pipeline de Requête

### Étape 1: Extraction d'entités (Intent Processing)

**Fichier**: `llm/utils/intent_processing.py`

Le LLM extrait les entités de la requête utilisateur:

```python
# Exemple de requête utilisateur
query = "What is the target weight for Ross 308 males at 21 days?"

# Entités extraites par le LLM
detected_entities = {
    "breed": "ross 308",
    "sex": "male",
    "age_days": 21,
    "metric": "weight",
    "species": "broiler"
}
```

### Étape 2: Construction des filtres (build_where_filter)

**Fichier**: `llm/utils/intent_processing.py` → `build_where_filter()`

Les entités sont transformées en filtres de base de données:

#### Pour Weaviate:
```python
where_filter = {
    "operator": "And",
    "operands": [
        {
            "path": ["breed"],
            "operator": "Equal",
            "valueText": "ross 308"  # ✅ NOUVEAU champ v2.0
        },
        {
            "path": ["sex"],
            "operator": "Equal",
            "valueText": "male"  # ✅ NOUVEAU champ v2.0
        },
        {
            "operator": "And",
            "operands": [
                {
                    "path": ["age_min_days"],
                    "operator": "LessThanEqual",
                    "valueInt": 21  # ✅ NOUVEAU champ v2.0
                },
                {
                    "path": ["age_max_days"],
                    "operator": "GreaterThanEqual",
                    "valueInt": 21  # ✅ NOUVEAU champ v2.0
                }
            ]
        }
    ]
}
```

#### Pour PostgreSQL:
```python
# Fichier: llm/retrieval/postgresql/query_builder.py
sql_query = """
SELECT
    m.metric_name,
    m.value_numeric,
    m.unit,
    d.sex,
    s.strain_name
FROM metrics m
JOIN documents d ON m.document_id = d.id
JOIN strains s ON d.strain_id = s.id
JOIN breeds b ON s.breed_id = b.id
WHERE
    s.strain_name LIKE '%308%'  -- Mapping breed via intents.json
    AND d.sex = 'male'  -- ✅ NOUVEAU champ v2.0
    AND m.age_min <= 21  -- ✅ NOUVEAU champ v2.0
    AND m.age_max >= 21  -- ✅ NOUVEAU champ v2.0
    AND m.metric_name LIKE '%weight%'
"""
```

### Étape 3: Récupération des données

#### Weaviate (recherche sémantique)
**Fichier**: `llm/retrieval/retriever_search.py` → `hybrid_search()`

```python
# Recherche hybride avec filtres
documents = await hybrid_search(
    query_vector=embedding,
    query_text="target weight Ross 308 males 21 days",
    top_k=15,
    where_filter=where_filter,  # Filtres construits à l'étape 2
    alpha=0.7  # 70% vectoriel, 30% BM25
)
```

#### PostgreSQL (métriques structurées)
**Fichier**: `llm/retrieval/postgresql/retriever.py` → `search_metrics()`

```python
# Recherche avec filtres SQL
metrics = await search_metrics(
    entities={
        "breed": "ross 308",
        "sex": "male",
        "age_days": 21,
        "metric": "weight"
    },
    limit=10
)
```

### Étape 4: Fusion et génération de réponse

**Fichier**: `llm/generation/generators.py` → `EnhancedResponseGenerator`

```python
# Fusion des résultats Weaviate + PostgreSQL
combined_context = {
    "textual_docs": weaviate_documents,  # Contexte sémantique
    "structured_metrics": postgresql_metrics,  # Métriques précises
    "query_entities": detected_entities
}

# Génération de la réponse finale
response = await generate_response(
    query=user_query,
    context=combined_context,
    model="gpt-4"
)
```

---

## 2. Mapping Entités → Champs BD

### Table de mapping complète

| Entité LLM | Type | Champ Weaviate | Champ PostgreSQL | Priorité | Opérateur |
|-----------|------|----------------|------------------|----------|-----------|
| `breed` | TEXT | `breed` | `strains.strain_name` | 🔴 **HAUTE** | Equal / LIKE |
| `company` | TEXT | `company` | `companies.company_name` | 🟡 **MOYENNE** | Like / LIKE |
| `sex` | TEXT | `sex` | `documents.sex` | 🔴 **HAUTE** | Equal / = |
| `age_days` | INT | `age_min_days` + `age_max_days` | `metrics.age_min` + `metrics.age_max` | 🔴 **HAUTE** | Range / BETWEEN |
| `species` | TEXT | `species` | `strains.species` | 🟡 **MOYENNE** | Like / LIKE |
| `unit_system` | TEXT | `unit_system` | `documents.unit_system` | 🟢 **BASSE** | Equal / = |
| `data_type` | TEXT | `data_type` | `documents.data_type` | 🟢 **BASSE** | Like / LIKE |
| `metric` | TEXT | N/A | `metrics.metric_name` | 🔴 **HAUTE** | N/A / LIKE |
| `housing_system` | TEXT | `housing_system` | `documents.housing_system` | 🟢 **BASSE** | Like / = |
| `feather_color` | TEXT | `feather_color` | `documents.feather_color` | 🟢 **BASSE** | Like / = |

### Champs DEPRECATED (compatibilité maintenue)

| Ancien champ | Nouveau champ | Raison |
|-------------|---------------|--------|
| `geneticLine` | `breed` | Normalisation avec intents.json |
| `phase` | `age_min_days` + `age_max_days` | Précision temporelle |
| `age_band` | `age_min_days` + `age_max_days` | Filtrage par plage exacte |

---

## 3. Fichiers Clés de l'Intégration

### Configuration
| Fichier | Rôle | Dernière modification |
|---------|------|----------------------|
| `llm/config/intents.json` | Registre des breeds + mapping DB | v1.5 (2025-01-15) |
| `rag/.env` | Credentials BD (Weaviate + PostgreSQL) | 2025-01-15 |
| `llm/docs/DATABASE_SCHEMA.md` | Documentation structure BD | 2025-01-15 |

### Intent Processing & Filtrage
| Fichier | Fonction clé | Rôle |
|---------|-------------|------|
| `llm/utils/intent_processing.py` | `build_where_filter()` | Construit filtres Weaviate depuis entités |
| `llm/utils/breeds_registry.py` | `get_db_name()` | Mapping breed canonique → nom PostgreSQL |

### Retrievers
| Fichier | Classe | BD cible |
|---------|--------|----------|
| `llm/retrieval/retriever_core.py` | `HybridWeaviateRetriever` | Weaviate |
| `llm/retrieval/retriever_search.py` | `SearchMixin` | Weaviate (hybrid search) |
| `llm/retrieval/postgresql/retriever.py` | `PostgreSQLRetriever` | PostgreSQL |
| `llm/retrieval/postgresql/query_builder.py` | `SQLQueryNormalizer` | PostgreSQL (construction requêtes) |

### RAG Engine
| Fichier | Rôle |
|---------|------|
| `llm/core/rag_engine.py` | Orchestration complète (retrievers + generation) |
| `llm/core/rag_engine_core.py` | Core avec client OpenAI |
| `llm/generation/generators.py` | Génération de réponses avec fusion contexte |

---

## 4. Flux de Données Complet

```
┌─────────────────────────────────────────────────────────────────┐
│                      REQUÊTE UTILISATEUR                         │
│  "What is the target weight for Ross 308 males at 21 days?"    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│               INTENT PROCESSING (LLM)                            │
│  Extraction entités: breed, sex, age_days, metric               │
│  Fichier: llm/utils/intent_processing.py                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│            CONSTRUCTION FILTRES (build_where_filter)             │
│  Weaviate: breed=ross 308, sex=male, age_min≤21≤age_max        │
│  PostgreSQL: strain LIKE '%308%', sex='male', age BETWEEN       │
│  Fichier: llm/utils/intent_processing.py                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ├──────────────────┬──────────────────────────┐
                     ▼                  ▼                          ▼
         ┌─────────────────────┐  ┌──────────────┐  ┌────────────────────┐
         │  WEAVIATE RETRIEVER │  │  POSTGRESQL  │  │  UNIT CONVERTER    │
         │  Hybrid Search      │  │  RETRIEVER   │  │  Conversion unités │
         │  (sémantique)       │  │  (métriques) │  │  metric ↔ imperial │
         └──────────┬──────────┘  └──────┬───────┘  └─────────┬──────────┘
                    │                    │                     │
                    │  Contexte textuel  │  Métriques précises │  Conversions
                    │  (15 docs)         │  (10 metrics)       │  si nécessaire
                    │                    │                     │
                    └────────────────────┴─────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │        FUSION & RERANKING (RRF)         │
                    │  Intelligent RRF: fusion des sources    │
                    │  Fichier: llm/retrieval/retriever_rrf.py│
                    └──────────────────┬──────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │    ENHANCED RESPONSE GENERATOR (LLM)    │
                    │  Synthèse contexte + métriques          │
                    │  Fichier: llm/generation/generators.py  │
                    └──────────────────┬──────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │           RÉPONSE FINALE                │
                    │  "For Ross 308 males at 21 days, the   │
                    │   target body weight is 907g (2.00 lbs)│
                    │   with a daily gain of 58.4g..."       │
                    └─────────────────────────────────────────┘
```

---

## 5. Vérification de l'Intégration

### Checklist de validation

- [x] **Schéma Weaviate** contient les 25 propriétés (dont breed, sex, age_min_days, age_max_days, unit_system)
- [x] **Schéma PostgreSQL** contient les colonnes sex, data_type, unit_system, age_min, age_max
- [x] **build_where_filter()** utilise les nouveaux champs v2.0 (breed, sex, age_min_days/age_max_days)
- [x] **PostgreSQLRetriever** utilise le breeds_registry pour mapping breed → strain_name
- [x] **intents.json** contient le registre des breeds avec db_name_mapping
- [x] **Documentation** DATABASE_SCHEMA.md est à jour
- [x] **Données** : 1932 chunks Weaviate + 3090 métriques PostgreSQL
- [x] **Unit Converter** supporte conversions metric ↔ imperial

### Tests d'intégration recommandés

```python
# Test 1: Filtrage par breed + sex + age
query = "Target weight for Ross 308 males at 21 days"
# Attendu: Filtre sur breed="ross 308", sex="male", age=21
# Résultat: Métriques PostgreSQL + contexte Weaviate filtrés

# Test 2: Comparaison multi-breed
query = "Compare Ross 308 vs Cobb 500 at 35 days"
# Attendu: Deux requêtes avec breed différents
# Résultat: Données des deux breeds pour comparaison

# Test 3: Conversion d'unités
query = "Weight in pounds for Ross 308 at 42 days"
# Attendu: Récupération metric + conversion → imperial
# Résultat: Poids en livres (lbs) avec conversion automatique
```

---

## 6. Performance & Optimisation

### Index utilisés

**Weaviate (HNSW vectoriel + filtres)**:
- Index vectoriel: 1536 dimensions
- Index propriétés: breed, sex, company, age_min_days, age_max_days, unit_system

**PostgreSQL (B-tree)**:
- `idx_metrics_age` : (age_min, age_max)
- `idx_documents_unit_system` : (unit_system)
- `idx_documents_data_type` : (data_type)
- Indexes sur strains, breeds, companies pour JOINs rapides

### Métriques de performance attendues

| Opération | Temps cible | Facteur limitant |
|-----------|-------------|------------------|
| Extraction entités (LLM) | < 500ms | Latence OpenAI API |
| Construction filtres | < 10ms | Traitement local |
| Weaviate hybrid search | < 200ms | Latence réseau + HNSW |
| PostgreSQL query | < 100ms | Complexité JOINs |
| Fusion + Reranking | < 50ms | Algorithme RRF |
| Génération réponse (LLM) | < 1500ms | Latence OpenAI API |
| **TOTAL** | **< 2.5s** | Bout-en-bout |

---

## 7. Troubleshooting

### Problème: Aucun résultat trouvé

**Causes possibles**:
1. Filtres trop restrictifs → Vérifier `build_where_filter()` logs
2. Breed non mappé → Vérifier `intents.json` db_name_mapping
3. Propriétés Weaviate manquantes → Vérifier schéma collection
4. PostgreSQL: strain_name incorrect → Vérifier breeds_registry

**Solution**: Activer `DISABLE_WHERE_FILTER=true` temporairement pour tester sans filtres

### Problème: Résultats non pertinents

**Causes possibles**:
1. Alpha hybride mal configuré (trop vectoriel ou trop BM25)
2. Reranking désactivé
3. Entités mal extraites par le LLM

**Solution**: Ajuster `fusion_config` dans `retriever_core.py`

### Problème: Unités incorrectes

**Causes possibles**:
1. `unit_system` non détecté dans PostgreSQL
2. UnitConverter non appelé

**Solution**: Vérifier `documents.unit_system` et forcer conversion si nécessaire

---

## 8. Prochaines Étapes

### En attente (quota Vectorize Iris)
- ⏳ Extraction de 6 PDFs supplémentaires (Manual of Poultry Diseases splits + Cobb supplement)
- ⏳ Ingestion vers Weaviate après extraction

### Améliorations futures
- [ ] Auto-détection language pour réponses multilingues
- [ ] Support queries complexes multi-entités (ex: "Compare males vs females")
- [ ] Cache Redis pour réponses fréquentes
- [ ] Monitoring métriques de récupération (précision, recall)

---

## Références

- **Documentation BD**: `llm/docs/DATABASE_SCHEMA.md`
- **Intents Registry**: `llm/config/intents.json`
- **Unit Converter**: `llm/retrieval/unit_converter.py`
- **Breeds Registry**: `llm/utils/breeds_registry.py`
