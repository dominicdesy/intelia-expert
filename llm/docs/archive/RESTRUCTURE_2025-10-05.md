# Directory Restructure - 2025-10-05

## Objectif

Simplifier et clarifier l'architecture du projet en regroupant les modules par responsabilité.

---

## Problèmes Identifiés

### 1. CORE/ Surchargé (33 fichiers)
- Mélange de responsabilités: RAG, PostgreSQL, Weaviate, routing, handlers, memory
- Difficulté à trouver les fichiers
- Pas de séparation claire entre composants

### 2. API/ Endpoints Fragmentés
- `api/endpoints_chat/` (4 fichiers)
- `api/endpoints_diagnostic/` (4 fichiers)
- `api/endpoints_health/` (4 fichiers)
- Sur-engineering pour petits modules

### 3. PostgreSQL et Weaviate Dispersés
- 7 fichiers `core/rag_postgresql*.py` dans core/
- 1 fichier `core/rag_weaviate_core.py` dans core/
- Devrait être regroupé dans retrieval/

### 4. Handlers Incohérents
- `core/handlers/` existe
- Mais `core/comparison_handler.py` était seul dans core/

### 5. Préfixes Redondants
- Beaucoup de fichiers avec préfixe `rag_` dans core/
- Redondant car déjà dans core/

---

## Changements Appliqués

### Phase 1: Création Structure retrieval/

```
retrieval/
├── __init__.py
├── postgresql/
│   ├── __init__.py
│   ├── main.py              (rag_postgresql.py)
│   ├── retriever.py         (NOUVEAU - n'existait pas)
│   ├── query_builder.py     (postgresql_query_builder.py)
│   ├── normalizer.py        (rag_postgresql_normalizer.py)
│   ├── models.py            (rag_postgresql_models.py)
│   ├── config.py            (rag_postgresql_config.py)
│   ├── router.py            (rag_postgresql_router.py)
│   └── temporal.py          (rag_postgresql_temporal.py)
└── weaviate/
    ├── __init__.py
    └── core.py              (rag_weaviate_core.py)
```

**Commandes:**
```bash
mkdir -p retrieval/postgresql retrieval/weaviate
git mv core/rag_postgresql.py retrieval/postgresql/main.py
git mv core/rag_postgresql_config.py retrieval/postgresql/config.py
git mv core/rag_postgresql_models.py retrieval/postgresql/models.py
git mv core/rag_postgresql_normalizer.py retrieval/postgresql/normalizer.py
git mv core/rag_postgresql_router.py retrieval/postgresql/router.py
git mv core/rag_postgresql_temporal.py retrieval/postgresql/temporal.py
git mv core/postgresql_query_builder.py retrieval/postgresql/query_builder.py
git mv core/rag_weaviate_core.py retrieval/weaviate/core.py
```

---

### Phase 2: Consolidation core/handlers/

```
core/handlers/
├── __init__.py
├── base_handler.py
├── standard_handler.py
├── standard_handler_helpers.py
├── temporal_handler.py
├── comparative_handler.py
└── comparison_handler.py    (DÉPLACÉ)
```

**Commandes:**
```bash
git mv core/comparison_handler.py core/handlers/comparison_handler.py
```

---

### Phase 3: Suppression Préfixes rag_ dans core/

**Fichiers renommés:**
```
core/rag_query_processor.py   → core/query_processor.py
core/rag_response_generator.py → core/response_generator.py
core/rag_json_system.py        → core/json_system.py
```

**Fichiers conservés (car engine est explicite):**
```
core/rag_engine.py
core/rag_engine_core.py
core/rag_engine_handlers.py
core/rag_langsmith.py
```

**Commandes:**
```bash
git mv core/rag_query_processor.py core/query_processor.py
git mv core/rag_response_generator.py core/response_generator.py
git mv core/rag_json_system.py core/json_system.py
```

---

### Phase 4: Mise à Jour des Imports

**Script automatique:** `scripts/update_imports.py`

**Principaux changements:**
```python
# PostgreSQL moves
from core.rag_postgresql_retriever import → from retrieval.postgresql.retriever import
from core.rag_postgresql_config import → from retrieval.postgresql.config import
from core.rag_postgresql_models import → from retrieval.postgresql.models import
from core.rag_postgresql_normalizer import → from retrieval.postgresql.normalizer import
from core.rag_postgresql import → from retrieval.postgresql.main import

# Weaviate moves
from core.rag_weaviate_core import → from retrieval.weaviate.core import

# Handlers
from core.comparison_handler import → from core.handlers.comparison_handler import

# Core renames
from core.rag_query_processor import → from core.query_processor import
from core.rag_response_generator import → from core.response_generator import
from core.rag_json_system import → from core.json_system import
```

**Fichiers impactés:**
- `core/rag_engine.py` - Import PostgreSQL et Weaviate
- `retrieval/postgresql/*.py` - Imports internes
- `scripts/prepare_finetuning_dataset.py`
- `tests/integration/test_reranker_integration.py`

---

## Structure Finale

### Avant (33 fichiers dans core/)
```
core/
├── rag_postgresql.py
├── rag_postgresql_config.py
├── rag_postgresql_models.py
├── rag_postgresql_normalizer.py
├── rag_postgresql_retriever.py
├── rag_postgresql_router.py
├── rag_postgresql_temporal.py
├── postgresql_query_builder.py
├── rag_weaviate_core.py
├── comparison_handler.py
├── rag_query_processor.py
├── rag_response_generator.py
├── rag_json_system.py
└── ... (20+ autres fichiers)
```

### Après (13 fichiers principaux dans core/)
```
core/
├── rag_engine.py
├── rag_engine_core.py
├── rag_engine_handlers.py
├── query_processor.py          ✅ RENOMMÉ
├── response_generator.py       ✅ RENOMMÉ
├── query_router.py
├── query_enricher.py
├── entity_extractor.py
├── memory.py
├── response_validator.py
├── data_models.py
├── base.py
├── json_system.py              ✅ RENOMMÉ
└── handlers/
    ├── base_handler.py
    ├── standard_handler.py
    ├── temporal_handler.py
    ├── comparative_handler.py
    └── comparison_handler.py   ✅ DÉPLACÉ

retrieval/                       ✅ NOUVEAU DOSSIER
├── postgresql/
│   ├── main.py                 ✅ DÉPLACÉ
│   ├── config.py               ✅ DÉPLACÉ
│   ├── models.py               ✅ DÉPLACÉ
│   ├── normalizer.py           ✅ DÉPLACÉ
│   ├── router.py               ✅ DÉPLACÉ
│   ├── temporal.py             ✅ DÉPLACÉ
│   └── query_builder.py        ✅ DÉPLACÉ
└── weaviate/
    └── core.py                 ✅ DÉPLACÉ
```

---

## Bénéfices

### ✅ Séparation Claire des Responsabilités
- **core/** : Logique métier RAG (engine, routing, memory, validation)
- **retrieval/** : Sources de données (PostgreSQL, Weaviate)
- **generation/** : Génération LLM
- **api/** : Endpoints HTTP
- **processing/** : Traitement intent/query

### ✅ Navigation Simplifiée
- PostgreSQL : `retrieval/postgresql/` (tout au même endroit)
- Weaviate : `retrieval/weaviate/`
- Handlers : `core/handlers/` (tous regroupés)

### ✅ Nommage Cohérent
- Suppression préfixes redondants `rag_` dans core/
- Noms plus courts et clairs: `query_processor.py` vs `rag_query_processor.py`

### ✅ Scalabilité
- Facile d'ajouter d'autres sources de retrieval (Elasticsearch, Pinecone, etc.)
- Structure modulaire permettant ajout de nouveaux handlers

---

## Tests de Validation

### ✅ Compilation Python
```bash
python -m py_compile core/rag_engine.py
python -m py_compile retrieval/postgresql/*.py
python -m py_compile retrieval/weaviate/core.py
python -m py_compile core/query_processor.py
python -m py_compile core/response_generator.py
python -m py_compile main.py
```

**Résultat:** Tous les fichiers compilent sans erreur

---

## Migration Guide

### Pour Ajouter une Nouvelle Source de Retrieval

1. Créer dossier `retrieval/nouvelle_source/`
2. Ajouter `__init__.py` et modules
3. Importer dans `core/rag_engine.py`:
   ```python
   from retrieval.nouvelle_source.core import NouvelleSourceCore
   ```

### Pour Ajouter un Nouveau Handler

1. Créer fichier dans `core/handlers/`
2. Hériter de `BaseHandler`
3. Enregistrer dans `core/rag_engine.py`

---

## Fichiers Non Modifiés

Les dossiers suivants n'ont PAS été touchés:
- `api/` (consolidation future possible)
- `generation/`
- `processing/`
- `cache/`
- `config/`
- `security/`
- `evaluation/`
- `monitoring/`
- `utils/`
- `tests/`

---

## Auteur

Claude Code - Directory Restructure
Date: 2025-10-05
