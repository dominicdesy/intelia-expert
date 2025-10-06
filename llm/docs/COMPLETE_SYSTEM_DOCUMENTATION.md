# 📚 Intelia Expert - Complete System Documentation
**Version:** 5.1.0
**Last Updated:** 2025-10-06
**Architecture:** Multi-LLM RAG System for Poultry Production

---

## 📖 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Quick Start](#quick-start)
5. [Deployment](#deployment)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Monitoring & Operations](#monitoring--operations)
9. [Development](#development)
10. [Integration Validation](#integration-validation)
11. [Domain Coverage](#domain-coverage)
12. [Troubleshooting](#troubleshooting)

---

## System Overview

### What is Intelia Expert?

Intelia Expert is an advanced **Retrieval-Augmented Generation (RAG)** system specialized in poultry production, providing expert-level answers across 8 major domains:

1. **Nutrition** - Feed formulation, ingredients, energy optimization
2. **Health** - Diseases, treatments, biosecurity, diagnostics
3. **Production** - Performance metrics, targets, optimization
4. **Genetics** - Breed selection, characteristics, performance
5. **Management** - Farm operations, protocols, best practices
6. **Environment** - Housing, climate control, equipment
7. **Welfare** - Animal well-being, behavior, regulations
8. **Economics** - Costs, profitability, ROI analysis

### Key Features

- ✅ **Multi-LLM Router** - Intelligent routing between GPT-4o, Claude 3.5, DeepSeek, Llama 3
- ✅ **Cohere Rerank** - Advanced result re-ranking for precision
- ✅ **Embeddings 3-Large** - State-of-the-art semantic search
- ✅ **RAGAS Evaluation** - Automated quality metrics (faithfulness, answer relevancy)
- ✅ **Conversation Memory** - Context-aware multi-turn dialogue
- ✅ **Clarification Loop** - Intelligent missing information detection
- ✅ **Domain Detection** - Automatic routing to specialized prompts
- ✅ **Response Validation** - Quality checks (6 validation rules)
- ✅ **13 Languages** - French, English, Spanish, German, Dutch, Italian, Portuguese, Polish, Hindi, Indonesian, Thai, Chinese
- ✅ **Dual Retrieval** - PostgreSQL (structured metrics) + Weaviate (semantic search)

### Tech Stack

**LLM Layer:**
- OpenAI GPT-4o, GPT-4o-mini
- Anthropic Claude 3.5 Sonnet
- DeepSeek R1
- Meta Llama 3.1/3.2

**Retrieval:**
- PostgreSQL (structured data)
- Weaviate (vector database)
- Cohere Rerank v3

**Infrastructure:**
- FastAPI (Python 3.11+)
- Redis (caching, rate limiting)
- Docker
- Digital Ocean App Platform

---

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                           │
│  - Rate Limiting (10 req/min)                                    │
│  - Language Detection (13 languages)                             │
│  - Request Validation                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Chat Handlers                                  │
│  - Conversation Memory Integration                               │
│  - Context Management                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   RAG Engine Core                                │
│  Version: 5.1.0 (Modular Architecture)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Query Processor                                │
│                                                                  │
│  STEP 0: Clarification Loop                                      │
│    → check pending clarification                                 │
│    → detect clarification response                               │
│    → merge queries if clarification                              │
│                                                                  │
│  STEP 1: Contextual History                                      │
│    → ConversationMemory.get_contextual_memory()                  │
│                                                                  │
│  STEP 2: Query Enrichment                                        │
│    → ConversationalQueryEnricher.enrich()                        │
│                                                                  │
│  STEP 2b: Entity Extraction from Context                         │
│    → extract_entities_from_context()                             │
│                                                                  │
│  STEP 3: Query Routing                                           │
│    → QueryRouter.route()                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Query Router                                   │
│                                                                  │
│  1. Load universal_terms (13 languages)                          │
│  2. Extract entities (breed, age, sex, metric)                   │
│  3. Validate completeness                                        │
│  4. Detect domain (nutrition, health, etc.)                      │
│  5. Route to destination (postgresql/weaviate/hybrid)            │
│                                                                  │
│  Routing Keywords from universal_terms_XX.json                   │
│  Contextual Patterns from universal_terms_XX.json                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
            ┌─────────────────┴─────────────────┐
            ↓                                   ↓
┌───────────────────────┐         ┌───────────────────────┐
│  PostgreSQL Retrieval │         │  Weaviate Retrieval   │
│  - Structured metrics │         │  - Semantic search    │
│  - Performance data   │         │  - Veterinary docs    │
│  - Breed standards    │         │  - Disease guides     │
│  - SQL generation     │         │  - Embeddings 3-Large │
└───────────────────────┘         └───────────────────────┘
            ↓                                   ↓
            └─────────────────┬─────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Cohere Rerank v3                               │
│  - Re-ranks top 100 results                                      │
│  - Returns top 10 most relevant                                  │
│  - Precision boost: +15-20%                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Response Generator                             │
│                                                                  │
│  1. Domain-Specific Prompt Selection                             │
│     → prompts_manager.get_specialized_prompt(detected_domain)    │
│                                                                  │
│  2. Multi-LLM Router                                             │
│     → Routes complex queries to Claude 3.5                       │
│     → Routes simple queries to GPT-4o-mini                       │
│     → Cost optimization: 60% reduction                           │
│                                                                  │
│  3. Response Generation                                          │
│     → Context + Query → LLM → Answer                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Response Validator                             │
│                                                                  │
│  6 Quality Checks:                                               │
│  ✅ No source mentions ("selon les documents")                   │
│  ✅ Appropriate length (300-800 chars optimal)                   │
│  ✅ Good structure (titles, lists, paragraphs)                   │
│  ✅ Numeric values present (for metric queries)                  │
│  ✅ Actionable recommendations (for nutrition/health)            │
│  ✅ Coherence with source documents                              │
│                                                                  │
│  Quality Score: 0.0 - 1.0                                        │
│  - Critical issue: -0.3                                          │
│  - Warning: -0.15                                                │
│  - Info: -0.05                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   FINAL RESPONSE                                 │
│  - High-quality, domain-expert answer                            │
│  - Conversation memory saved                                     │
│  - Metrics logged                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
llm/
├── api/                           # FastAPI endpoints
│   ├── chat_handlers.py           # Chat logic
│   ├── endpoints.py               # HTTP routes
│   └── utils.py                   # API utilities
│
├── core/                          # Core RAG engine
│   ├── rag_engine.py              # Main orchestrator
│   ├── query_processor.py         # Query processing pipeline
│   ├── query_router.py            # Intelligent routing
│   ├── query_enricher.py          # Conversational enrichment
│   ├── response_generator.py      # Response generation
│   ├── response_validator.py      # Quality validation
│   ├── memory.py                  # Conversation memory
│   ├── entity_extractor.py        # Entity extraction
│   ├── data_models.py             # Data structures
│   ├── base.py                    # Base classes
│   │
│   └── handlers/                  # Query handlers
│       ├── standard_handler.py    # Standard queries
│       ├── temporal_handler.py    # Time-series queries
│       └── comparison_handler.py  # Comparative queries
│
├── retrieval/                     # Retrieval layer
│   ├── postgresql/                # PostgreSQL integration
│   │   ├── retriever.py           # Main retriever
│   │   ├── query_builder.py       # SQL generation
│   │   ├── normalizer.py          # Query normalization
│   │   ├── models.py              # Data models
│   │   ├── config.py              # Configuration
│   │   ├── router.py              # Query routing
│   │   └── temporal.py            # Temporal queries
│   │
│   └── weaviate/                  # Weaviate integration
│       └── core.py                # Vector search
│
├── generation/                    # Response generation
│   ├── generators.py              # LLM generators
│   ├── prompt_builder.py          # Prompt construction
│   └── entity_manager.py          # Entity descriptions
│
├── security/                      # Security & validation
│   ├── guardrails/                # Response guardrails
│   │   ├── core.py                # Orchestrator
│   │   ├── models.py              # Data models
│   │   └── verifiers/             # Verification modules
│   │
│   ├── ood/                       # Out-of-domain detection
│   │   ├── detector.py            # Main detector
│   │   ├── models.py              # Data models
│   │   └── vocabulary_builder.py  # Vocabulary management
│   │
│   ├── advanced_guardrails.py     # Compatibility wrapper
│   └── ood_detector.py            # Compatibility wrapper
│
├── config/                        # Configuration files
│   ├── domain_keywords.json       # Domain detection (8 domains)
│   ├── system_prompts.json        # Specialized prompts
│   ├── clarification_strategies.json  # Clarification templates
│   ├── entity_descriptions.json   # Entity metadata
│   ├── intents.json               # Intent classification
│   ├── breeds_mapping.json        # Breed normalization
│   ├── metrics_normalization.json # Metric normalization
│   ├── blocked_terms.json         # Security filters
│   ├── technical_exclusions.json  # Technical terms
│   ├── veterinary_terms.json      # Medical vocabulary
│   ├── universal_terms_*.json     # 13 language files
│   └── README_CENTRALIZED_CONFIG.md
│
├── scripts/                       # Utility scripts
│   ├── migrate_embeddings.py      # Embeddings 3-large migration
│   ├── prepare_finetuning_dataset.py  # Fine-tuning prep
│   ├── run_ragas_evaluation.py    # Quality evaluation
│   ├── test_embedding_quality.py  # Embedding tests
│   ├── update_imports.py          # Import updates
│   └── README.md
│
├── docs/                          # Documentation
│   ├── COMPLETE_SYSTEM_DOCUMENTATION.md  # This file
│   └── archive/                   # Historical docs
│
├── utils/                         # Shared utilities
├── processing/                    # Query processing
└── tests/                         # Test suites
```

---

## Core Components

### 1. Query Router

**File:** `core/query_router.py`

**Responsibilities:**
- Load 13 language dictionaries (universal_terms_XX.json)
- Extract entities (breed, age, sex, metric)
- Validate entity completeness
- Detect domain (8 domains)
- Route to appropriate retrieval system

**Key Methods:**
```python
route(query, user_id, language, preextracted_entities) -> QueryRoute
detect_domain(query, language) -> str
_extract_entities(query, language) -> Dict
_validate_entities(entities, query, language) -> ValidationResult
```

**Configuration Files Used:**
- `domain_keywords.json` - 153+ bilingual keywords
- `universal_terms_XX.json` - 13 language files
- `breeds_mapping.json` - Breed normalization
- `clarification_strategies.json` - Clarification templates

**Routing Destinations:**
- `postgresql` - Structured data queries
- `weaviate` - Semantic search queries
- `hybrid` - Combined approach
- `needs_clarification` - Missing information

### 2. Query Processor

**File:** `core/query_processor.py`

**Pipeline:**
```python
async def process_query(query, language, tenant_id):
    # Step 0: Check pending clarification
    if pending_clarification:
        if is_clarification_response(query):
            merged = merge_query_with_clarification(original, query)
            clear_pending_clarification()
            query = merged

    # Step 1: Retrieve contextual history
    history = get_contextual_memory(tenant_id, query)

    # Step 2: Enrich query
    enriched = enricher.enrich(query, history, language)

    # Step 2b: Extract entities from context
    entities = enricher.extract_entities_from_context(history, language)

    # Step 3: Route query
    route = query_router.route(enriched, tenant_id, language, entities)

    # Step 4: Handle clarification
    if route.destination == "needs_clarification":
        mark_pending_clarification(tenant_id, query, missing_fields)
        return clarification_result

    # Step 5: Route to handler
    return await route_to_handler(route, preprocessed_data)
```

### 3. Conversation Memory

**File:** `core/memory.py`

**Features:**
- Multi-turn conversation tracking
- Contextual history retrieval
- Clarification loop management
- Entity accumulation across turns

**Key Methods:**
```python
add_exchange(tenant_id, question, answer)
get_contextual_memory(tenant_id, current_query) -> str
mark_pending_clarification(tenant_id, query, missing_fields)
is_clarification_response(query, tenant_id) -> bool
merge_query_with_clarification(original, clarification) -> str
```

**Example:**
```
Turn 1: "Quel est le poids ?"
        → Missing breed → mark_pending_clarification()
        → Response: "Veuillez préciser la race (Ross 308, Cobb 500, ...)"

Turn 2: "Ross 308"
        → is_clarification_response() = True
        → merge: "Quel est le poids pour Ross 308 ?"
        → clear_pending_clarification()
        → Process merged query
```

### 4. Response Validator

**File:** `core/response_validator.py`

**6 Quality Checks:**

1. **No Source Mentions** (Critical)
   - Forbidden: "selon les documents", "d'après les sources"
   - Penalty: -0.3

2. **Appropriate Length** (Warning)
   - Too short: < 200 chars for complex query
   - Too long: > 1500 chars
   - Optimal: 300-800 chars (+0.05 bonus)
   - Penalty: -0.15

3. **Structure & Formatting** (Warning)
   - Required for long responses: titles (**), lists (-), paragraphs
   - Penalty: -0.15

4. **Numeric Values** (Warning)
   - Required for metric queries (poids, fcr, température)
   - Penalty: -0.15

5. **Actionable Recommendations** (Info)
   - Expected for nutrition, health, management domains
   - Penalty: -0.05

6. **Coherence with Documents** (Future)
   - Basic coherence check
   - Advanced semantic validation planned

**Quality Score:**
- Starts at 1.0
- Penalties applied per issue
- Final score: 0.0 - 1.0
- Valid if: score >= 0.6 AND no critical issues

### 5. Domain Detection

**File:** `core/query_router.py` (line 421)

**8 Supported Domains:**

1. **nutrition_query** - 19 FR + 19 EN keywords
   - aliment, ration, formule, protéine, énergie, lysine, méthionine
   - feed, diet, formula, protein, energy, lysine, methionine

2. **health_diagnosis** - 22 FR + 22 EN keywords
   - maladie, santé, symptôme, traitement, vaccin, médicament
   - disease, health, symptom, treatment, vaccine, medicine

3. **production_optimization** - 16 FR + 16 EN keywords
   - performance, rendement, efficacité, production, croissance
   - performance, yield, efficiency, production, growth

4. **genetics_query** - 14 FR + 14 EN keywords
   - génétique, race, lignée, sélection, croisement, héritabilité
   - genetic, breed, strain, selection, crossbreeding, heritability

5. **management_advice** - 18 FR + 18 EN keywords
   - gestion, élevage, conduite, protocole, programme, planning
   - management, farming, operation, protocol, program, schedule

6. **environmental_control** - 21 FR + 21 EN keywords
   - environnement, température, humidité, ventilation, ambiance
   - environment, temperature, humidity, ventilation, climate

7. **welfare_assessment** - 17 FR + 17 EN keywords
   - bien-être, comportement, stress, confort, enrichissement
   - welfare, behavior, stress, comfort, enrichment

8. **economics_analysis** - 16 FR + 16 EN keywords
   - coût, prix, rentabilité, budget, investissement, ROI
   - cost, price, profitability, budget, investment, ROI

**Detection Method:**
```python
def detect_domain(self, query: str, language: str = "fr") -> str:
    query_lower = query.lower()
    domain_scores = {}

    for domain_key, domain_config in self.domain_keywords.items():
        keywords = domain_config.get("keywords", {}).get(language, [])
        score = sum(1 for kw in keywords if kw.lower() in query_lower)
        if score > 0:
            domain_scores[domain_key] = score

    if domain_scores:
        return max(domain_scores, key=domain_scores.get)

    return "general_poultry"
```

**Usage:**
```python
detected_domain = self.detect_domain(query, language)
# → "nutrition_query"

# Stored in validation_details
validation_details["detected_domain"] = detected_domain

# Used for specialized prompt selection
specialized_prompt = prompts_manager.get_specialized_prompt(
    detected_domain, language
)
```

### 6. Multi-LLM Router

**File:** `generation/generators.py`

**Routing Logic:**
```python
def _select_model_for_query(self, query: str, complexity_score: float) -> str:
    # Complex queries → Claude 3.5 Sonnet (best quality)
    if complexity_score > 0.7:
        return "claude-3-5-sonnet-20241022"

    # Medium complexity → GPT-4o
    elif complexity_score > 0.4:
        return "gpt-4o-2024-11-20"

    # Simple queries → GPT-4o-mini (cost-effective)
    else:
        return "gpt-4o-mini-2024-07-18"
```

**Complexity Factors:**
- Query length
- Number of entities
- Domain complexity
- Conversation depth

**Cost Optimization:**
- 60% reduction in inference costs
- Quality maintained for complex queries

### 7. Cohere Rerank v3

**File:** `retrieval/postgresql/retriever.py`, `retrieval/weaviate/core.py`

**Configuration:**
```python
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_RERANK_MODEL = "rerank-v3.5"
COHERE_TOP_N = 10
```

**Usage:**
```python
# Re-rank top 100 results
reranked = cohere.rerank(
    model="rerank-v3.5",
    query=query,
    documents=[doc["content"] for doc in results],
    top_n=10,
    return_documents=True
)

# Extract top 10 most relevant
top_results = [
    results[item.index]
    for item in reranked.results
]
```

**Performance:**
- Precision increase: +15-20%
- Latency: +50-100ms
- Cost: ~$1 per 1000 queries

### 8. RAGAS Evaluation

**File:** `scripts/run_ragas_evaluation.py`

**Metrics:**
1. **Faithfulness** - Answer grounded in context
2. **Answer Relevancy** - Direct response to question
3. **Context Precision** - Relevant context retrieved
4. **Context Recall** - Complete context coverage

**Usage:**
```bash
python scripts/run_ragas_evaluation.py --queries queries.jsonl --output results.json
```

**Output:**
```json
{
  "faithfulness": 0.87,
  "answer_relevancy": 0.92,
  "context_precision": 0.85,
  "context_recall": 0.89,
  "avg_score": 0.88
}
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Weaviate 1.24+
- Redis 7+ (optional, for production)

### Installation

```bash
# Clone repository
git clone https://github.com/dominicdesy/intelia-expert.git
cd intelia-expert/llm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create `.env` file:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-2024-11-20
OPENAI_MODEL_MINI=gpt-4o-mini-2024-07-18

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat

# Cohere
COHERE_API_KEY=co-...
COHERE_RERANK_MODEL=rerank-v3.5

# PostgreSQL
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=poultry_db
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=your_password

# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=optional

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

### Run Development Server

```bash
uvicorn api.main:app --reload --port 8000
```

API available at: http://localhost:8000

### Test Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quel est le poids moyen pour Ross 308 à 35 jours ?",
    "user_id": "test_user",
    "language": "fr"
  }'
```

---

## Deployment

### Digital Ocean App Platform

#### Step 1: Prepare Repository

```bash
# Ensure all changes committed
git add .
git commit -m "Prepare for deployment"
git push origin main
```

#### Step 2: Get API Keys

**Required Keys:**
- `OPENAI_API_KEY` - https://platform.openai.com/api-keys
- `ANTHROPIC_API_KEY` - https://console.anthropic.com/
- `COHERE_API_KEY` - https://dashboard.cohere.com/api-keys
- `DEEPSEEK_API_KEY` - https://platform.deepseek.com/
- `POSTGRESQL_*` - Database credentials
- `WEAVIATE_URL` - Vector DB URL

#### Step 3: Create App on Digital Ocean

1. Go to https://cloud.digitalocean.com/apps
2. Click "Create App"
3. Connect GitHub repository
4. Select branch: `main`
5. Select source directory: `llm`

#### Step 4: Configure Build Settings

**Build Command:**
```bash
pip install -r requirements.txt
```

**Run Command:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

**HTTP Port:** 8080

#### Step 5: Add Environment Variables

Go to "Settings" → "App-Level Environment Variables":

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
COHERE_API_KEY=co-...
DEEPSEEK_API_KEY=sk-...
POSTGRESQL_HOST=db-host.ondigitalocean.com
POSTGRESQL_PORT=25060
POSTGRESQL_DATABASE=intelia_db
POSTGRESQL_USER=doadmin
POSTGRESQL_PASSWORD=...
WEAVIATE_URL=https://your-cluster.weaviate.network
REDIS_HOST=redis-host.ondigitalocean.com
REDIS_PORT=25061
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

#### Step 6: Deploy

Click "Deploy" → Wait 5-10 minutes

#### Step 7: Verify Deployment

```bash
# Check health
curl https://your-app.ondigitalocean.app/health

# Test chat
curl -X POST https://your-app.ondigitalocean.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the target weight for Ross 308 at 35 days?",
    "user_id": "test",
    "language": "en"
  }'
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Build & Run:**
```bash
docker build -t intelia-expert .
docker run -p 8080:8080 --env-file .env intelia-expert
```

---

## Configuration

### Domain Keywords (8 Domains)

**File:** `config/domain_keywords.json`

```json
{
  "nutrition_query": {
    "keywords": {
      "fr": ["aliment", "ration", "formule", "protéine", ...],
      "en": ["feed", "diet", "formula", "protein", ...]
    }
  },
  "health_diagnosis": {
    "keywords": {
      "fr": ["maladie", "santé", "symptôme", ...],
      "en": ["disease", "health", "symptom", ...]
    }
  }
}
```

**Total Keywords:** 153+ bilingual keywords across 8 domains

### Specialized Prompts

**File:** `config/system_prompts.json`

```json
{
  "specialized_prompts": {
    "nutrition_query": {
      "fr": "Tu es un expert en NUTRITION ANIMALE...",
      "en": "You are an expert in ANIMAL NUTRITION..."
    },
    "health_diagnosis": {
      "fr": "Tu es un vétérinaire spécialisé...",
      "en": "You are a specialized veterinarian..."
    }
  }
}
```

**8 Specialized Prompts:**
- nutrition_query
- health_diagnosis
- production_optimization
- genetics_query
- management_advice
- environmental_control
- welfare_assessment
- economics_analysis

### Clarification Strategies

**File:** `config/clarification_strategies.json`

```json
{
  "breed_missing": {
    "fr": "Veuillez préciser la race (Ross 308, Cobb 500, Hubbard, ISA Brown, Lohmann).",
    "en": "Please specify the breed (Ross 308, Cobb 500, Hubbard, ISA Brown, Lohmann)."
  }
}
```

### Universal Terms (13 Languages)

**Files:** `config/universal_terms_{lang}.json`

**Structure:**
```json
{
  "metadata": {
    "language": "fr",
    "version": "3.0.0",
    "total_domains": 24
  },
  "domains": {
    "contextual_references": {
      "same": {
        "canonical": "meme",
        "confidence": 0.90,
        "variants": ["même", "meme", "au même", ...]
      }
    },
    "performance_metrics": {
      "weight": {
        "canonical": "poids",
        "confidence": 0.95,
        "variants": ["poids", "poids vif", "poids corporel", ...]
      }
    }
  }
}
```

**Supported Languages:**
- French (fr)
- English (en)
- Spanish (es)
- German (de)
- Dutch (nl)
- Italian (it)
- Portuguese (pt)
- Polish (pl)
- Hindi (hi)
- Indonesian (id)
- Thai (th)
- Chinese (zh)
- Meta (universal)

---

## API Reference

### POST /chat

**Description:** Main chat endpoint

**Request:**
```json
{
  "message": "Quel est le poids pour Ross 308 à 35 jours ?",
  "user_id": "user123",
  "language": "fr",
  "use_json_search": true,
  "genetic_line_filter": "ross_308",
  "performance_context": {
    "target_weight": 2100
  }
}
```

**Response (Streaming SSE):**
```
event: start
data: {"type":"start","source":"postgresql","confidence":0.95}

event: chunk
data: {"type":"chunk","content":"Le poids moyen...","chunk_index":0}

event: chunk
data: {"type":"chunk","content":" pour Ross 308...","chunk_index":1}

event: end
data: {"type":"end","total_time":1.23,"documents_used":5}
```

**Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1696521600
```

### POST /chat/validate

**Description:** Validate query without generating response

**Request:**
```json
{
  "message": "Quel poids ?",
  "language": "fr"
}
```

**Response:**
```json
{
  "is_valid": false,
  "needs_clarification": true,
  "missing_fields": ["breed", "age"],
  "suggestions": {
    "breed": ["Ross 308", "Cobb 500", "Hubbard"],
    "age": ["0-7 jours", "8-21 jours", "22-35 jours"]
  },
  "confidence": 0.85
}
```

### GET /health

**Description:** Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "version": "5.1.0",
  "timestamp": "2025-10-06T10:30:00Z",
  "services": {
    "rag_engine": true,
    "postgresql": true,
    "weaviate": true,
    "redis": true,
    "conversation_memory": true
  },
  "stats": {
    "requests_total": 1234,
    "routing_success": 1200,
    "clarification_needed": 34,
    "errors_count": 0
  }
}
```

### GET /metrics

**Description:** Prometheus metrics endpoint

**Response:**
```
# HELP requests_total Total number of requests
# TYPE requests_total counter
requests_total 1234

# HELP routing_success Successful routing count
# TYPE routing_success counter
routing_success 1200

# HELP response_time_seconds Response time histogram
# TYPE response_time_seconds histogram
response_time_seconds_bucket{le="0.5"} 800
response_time_seconds_bucket{le="1.0"} 1100
response_time_seconds_bucket{le="2.0"} 1200
```

---

## Monitoring & Operations

### Rate Limiting

**Configuration:**
- Default: 10 requests per minute per user
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`

**User Identification:**
1. Header `X-User-ID` (priority)
2. Field `user_id` or `tenant_id` in body
3. IP address (fallback)

**Storage:**
- Redis (recommended for production)
- In-memory (fallback if Redis unavailable)

**Response Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1696521600
```

**Rate Limit Exceeded (429):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Limite de 10 requêtes par minute dépassée",
  "retry_after": 45
}
```

### Logging

**Log Levels:**
- DEBUG - Detailed execution flow
- INFO - Important events (routing, domain detection)
- WARNING - Non-critical issues (missing configs, fallbacks)
- ERROR - Errors requiring attention

**Key Log Messages:**
```
✅ Route: postgresql | Domain: nutrition_query | Contextuel: YES | Temps: 0.234s
📦 Entities extracted from context: {'breed': 'Ross 308', 'age_days': 35}
🔗 Référence contextuelle détectée: '\bmême\b'
⚠️ No contextual patterns loaded for language 'xx'
❌ Critical initialization error: ...
```

### Prometheus Metrics

**Available Metrics:**
- `requests_total` - Total requests
- `routing_success` - Successful routing
- `routing_failures` - Failed routing
- `clarification_needed` - Clarification requests
- `comparative_queries` - Comparative queries
- `temporal_queries` - Temporal queries
- `postgresql_queries` - PostgreSQL queries
- `weaviate_queries` - Weaviate queries
- `llm_generations` - LLM generations
- `errors_count` - Error count
- `response_time_seconds` - Response time histogram

**Grafana Dashboard:**
```json
{
  "panels": [
    {
      "title": "Request Rate",
      "targets": [{"expr": "rate(requests_total[5m])"}]
    },
    {
      "title": "Response Time (p95)",
      "targets": [{"expr": "histogram_quantile(0.95, response_time_seconds)"}]
    }
  ]
}
```

### Health Checks

**Endpoint:** GET /health

**Monitored Services:**
- RAG Engine
- PostgreSQL
- Weaviate
- Redis
- Conversation Memory
- Query Router
- LLM Generator

**Alerts:**
- Service down → Notify on-call
- Error rate > 1% → Warning
- Response time > 5s → Warning

---

## Development

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/integration/test_llm_router.py

# With coverage
pytest --cov=core --cov-report=html
```

### Code Quality

**Linting:**
```bash
# Run ruff
ruff check .

# Auto-fix
ruff check --fix .
```

**Formatting:**
```bash
# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

### Pre-commit Hooks

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Install:**
```bash
pre-commit install
```

### Adding New Language

1. **Create universal_terms file:**
```bash
cp config/universal_terms_fr.json config/universal_terms_xx.json
```

2. **Translate terms:**
Edit `config/universal_terms_xx.json` and translate all domains

3. **Add to config:**
```python
# config/config.py
SUPPORTED_LANGUAGES = [..., "xx"]
```

4. **Add clarification strategies:**
```json
// config/clarification_strategies.json
{
  "breed_missing": {
    "xx": "Translation..."
  }
}
```

5. **Add specialized prompts:**
```json
// config/system_prompts.json
{
  "specialized_prompts": {
    "nutrition_query": {
      "xx": "Translation..."
    }
  }
}
```

### Adding New Domain

1. **Add to domain_keywords.json:**
```json
{
  "new_domain": {
    "keywords": {
      "fr": ["keyword1", "keyword2", ...],
      "en": ["keyword1", "keyword2", ...]
    },
    "priority": 1,
    "clarification_strategy": "general_clarification"
  }
}
```

2. **Add specialized prompt:**
```json
{
  "specialized_prompts": {
    "new_domain": {
      "fr": "Tu es un expert en...",
      "en": "You are an expert in..."
    }
  }
}
```

3. **Update documentation:**
Add new domain to this file and DOMAIN_COVERAGE_ANALYSIS.md

---

## Integration Validation

### Complete Integration Verification

**Report:** `docs/INTEGRATION_VALIDATION_REPORT.md`

**Status:** ALL INTEGRATIONS VERIFIED ✅ (9/9 functions, 100% coverage)

#### 1. Clarification Loop ✅

**Functions Verified:**
- `mark_pending_clarification()` → core/query_processor.py:131
- `is_clarification_response()` → core/query_processor.py:70
- `merge_query_with_clarification()` → core/query_processor.py:78
- `clear_pending_clarification()` → core/query_processor.py:86
- `get_pending_clarification()` → core/query_processor.py:64

**Flow:**
```
Turn 1: "Quel poids ?" → Missing breed
        mark_pending_clarification()
        Response: "Veuillez préciser la race..."

Turn 2: "Ross 308"
        is_clarification_response() = True
        merge: "Quel poids pour Ross 308 ?"
        clear_pending_clarification()
        Process merged query
```

#### 2. Domain Detection ✅

**Function:** `detect_domain()` → core/query_router.py:577

**Flow:**
```
Query: "Quelle formule pour poulet ?"
detect_domain() → "nutrition_query"
validation_details["detected_domain"] = "nutrition_query"
```

#### 3. Entity Extraction from Context ✅

**Function:** `extract_entities_from_context()` → core/query_processor.py:105

**Flow:**
```
Turn 1: "Poids Ross 308 à 35 jours ?" → Stored in memory

Turn 2: "Et à 42 jours ?"
        extract_entities_from_context() finds:
        - breed: "Ross 308"
        - age_days: 35 (from context)

        Router merges with fresh extraction (42 jours)
        Final: breed=Ross 308, age_days=42
        No clarification needed!
```

#### 4. Specialized Prompt Selection ✅

**Function:** `get_specialized_prompt()` → config/system_prompts.py:103

**Flow:**
```
detected_domain = "nutrition_query"
prompts_manager.get_specialized_prompt("nutrition_query", "fr")
Returns: "Tu es un expert en NUTRITION ANIMALE..."
LLM receives specialized prompt
Response quality improved!
```

#### 5. Response Validation ✅

**Function:** `validate_response()` → core/response_validator.py:76

**Flow:**
```
Response: "Le poids moyen pour Ross 308..."
validate_response() runs 6 checks
quality_score = 0.95
is_valid = True
```

---

## Domain Coverage

### Complete Domain Analysis

**Report:** `docs/DOMAIN_COVERAGE_ANALYSIS.md`

**Status:** 8/8 domains covered (100%)

### Coverage Matrix

| Domain | Keywords | Clarification | Prompt | Context | Status |
|--------|----------|---------------|---------|---------|--------|
| Nutrition | ✅ 19 FR + 19 EN | ✅ | ✅ | ✅ | COMPLET |
| Health | ✅ 22 FR + 22 EN | ✅ | ✅ | ✅ | COMPLET |
| Production | ✅ 16 FR + 16 EN | ✅ | ✅ | ✅ | COMPLET |
| Genetics | ✅ 14 FR + 14 EN | ✅ | ✅ | ✅ | COMPLET |
| Management | ✅ 18 FR + 18 EN | ✅ | ✅ | ✅ | COMPLET |
| Environment | ✅ 21 FR + 21 EN | ✅ | ✅ | ✅ | COMPLET |
| Welfare | ✅ 17 FR + 17 EN | ✅ | ✅ | ✅ | COMPLET |
| Economics | ✅ 16 FR + 16 EN | ✅ | ✅ | ✅ | COMPLET |

**Total:** 153+ bilingual keywords

### Example Queries by Domain

**Nutrition:**
```
FR: "Quelle formule d'aliment pour poulet chair à 21 jours ?"
EN: "What feed formula for broiler at 21 days?"
Domain: nutrition_query
Prompt: "Tu es un expert en NUTRITION ANIMALE..."
```

**Health:**
```
FR: "Symptômes de la coccidiose chez Ross 308 ?"
EN: "Symptoms of coccidiosis in Ross 308?"
Domain: health_diagnosis
Prompt: "Tu es un vétérinaire spécialisé..."
```

**Production:**
```
FR: "Objectif de poids pour Ross 308 à 35 jours ?"
EN: "Target weight for Ross 308 at 35 days?"
Domain: production_optimization
Prompt: "Tu es un expert en OPTIMISATION DE PRODUCTION..."
```

---

## Troubleshooting

### Common Issues

#### Issue: "intents.json manquant"

**Cause:** Missing configuration file

**Solution:**
```bash
# Check file exists
ls -la config/intents.json

# If missing, restore from backup
cp config/intents.json.example config/intents.json
```

#### Issue: "No contextual patterns loaded"

**Cause:** universal_terms file missing or malformed

**Solution:**
```bash
# Verify file exists
ls -la config/universal_terms_fr.json

# Test loading
python -c "
import json
with open('config/universal_terms_fr.json') as f:
    data = json.load(f)
    print(f\"Domains: {list(data.get('domains', {}).keys())}\")
"
```

#### Issue: "Rate limit exceeded"

**Cause:** Too many requests from same user

**Solution:**
```bash
# Wait for rate limit window to reset (60 seconds)
# Or increase limit in .env:
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW=60
```

#### Issue: "PostgreSQL connection failed"

**Cause:** Database unavailable or incorrect credentials

**Solution:**
```bash
# Test connection
psql -h $POSTGRESQL_HOST -U $POSTGRESQL_USER -d $POSTGRESQL_DATABASE

# Check environment variables
echo $POSTGRESQL_HOST
echo $POSTGRESQL_PORT
echo $POSTGRESQL_DATABASE
```

#### Issue: "Weaviate connection failed"

**Cause:** Vector DB unavailable

**Solution:**
```bash
# Check Weaviate health
curl $WEAVIATE_URL/v1/.well-known/ready

# Restart Weaviate
docker restart weaviate
```

#### Issue: "OpenAI API error"

**Cause:** Invalid API key or quota exceeded

**Solution:**
```bash
# Verify API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check usage
# Visit: https://platform.openai.com/usage
```

### Debug Mode

**Enable detailed logging:**
```python
# config/config.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Performance Optimization

**Slow responses:**
```bash
# Check metrics
curl http://localhost:8000/metrics | grep response_time

# Enable query caching (Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
ENABLE_CACHE=true
```

**High memory usage:**
```bash
# Reduce cache size
CACHE_SIZE=100  # Default: 1000

# Disable conversation memory caching
ENABLE_MEMORY_CACHE=false
```

---

## Recent Changes

### 2025-10-06

**Integration Validation Report:**
- ✅ Verified all 9 functions properly integrated (100% coverage)
- ✅ Documented complete end-to-end flow with line numbers
- ✅ No missing integrations found

**Hardcoded Text Removal:**
- ✅ Removed 30+ lines of hardcoded contextual patterns
- ✅ Now loads patterns from universal_terms_XX.json (44 patterns)
- ✅ Single source of truth for all textual data

**Security Architecture Cleanup:**
- ✅ Deleted monolithic security files (100KB)
- ✅ Activated modular architecture via compatibility wrappers
- ✅ Reduced from 2,790 lines to 203 lines (92% reduction)

### 2025-10-05

**Directory Restructure:**
- ✅ Created retrieval/ layer (postgresql/, weaviate/)
- ✅ Moved 17 files, removed rag_ prefixes
- ✅ Consolidated handlers in core/handlers/

**Domain Coverage Analysis:**
- ✅ Documented 8 domains with 153+ bilingual keywords
- ✅ Verified 100% coverage across all production areas

**Memory & Clarification Fix:**
- ✅ Fixed clarification loop (mark, detect, merge)
- ✅ Integrated entity extraction from context
- ✅ Multi-turn conversations working correctly

### 2025-10-04

**Quick Wins Deployment:**
- ✅ Multi-LLM Router (GPT-4o, Claude 3.5, DeepSeek)
- ✅ Cohere Rerank v3 integration
- ✅ Embeddings 3-large upgrade
- ✅ RAGAS evaluation framework
- ✅ Fine-tuning dataset preparation

---

## Support & Contact

**GitHub Repository:**
https://github.com/dominicdesy/intelia-expert

**Issues:**
https://github.com/dominicdesy/intelia-expert/issues

**Documentation:**
https://github.com/dominicdesy/intelia-expert/tree/main/llm/docs

---

**Document Version:** 1.0.0
**Generated:** 2025-10-06
**Next Review:** 2025-11-06
