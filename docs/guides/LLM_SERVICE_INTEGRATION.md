# LLM Service Integration Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend / API                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      ai-service (Port 8000)                  │
│  - RAG Expert (PostgreSQL + Weaviate)                       │
│  - Entity Extraction                                         │
│  - Query Classification                                      │
│  - Context Retrieval                                         │
│  - Prompt Construction                                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTP (if USE_LLM_SERVICE=true)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    llm service (Port 8081)                   │
│  - Domain Configuration (Aviculture)                         │
│  - Provider Routing (Intelia Llama / GPT-4o / Claude)       │
│  - Adaptive Token Calculation (200-1500 tokens)             │
│  - Response Post-Processing                                  │
│  - Veterinary Disclaimers                                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ LLM Providers      │
                    │ - HuggingFace      │
                    │ - OpenAI           │
                    │ - Anthropic        │
                    └────────────────────┘
```

## Phase 1: Domain Configuration ✅

**Migrated to `llm/config/aviculture/`:**
- `system_prompts.json` (200 lines) - Specialized prompts by query type
- `poultry_terminology.json` - Multilingual technical vocabulary
- `veterinary_terms.json` - Health/disease terminology
- `languages.json` - System messages in 12 languages
- `config.py` (295 lines) - Domain configuration manager

**Utilities migrated to `llm/app/utils/`:**
- `adaptive_length.py` (449 lines) - Dynamic max_tokens calculation
- `post_processor.py` (245 lines) - Response formatting + disclaimers

## Phase 2: Intelligent Generation API ✅

**New endpoints in LLM service:**

### `POST /v1/generate`
Intelligent generation with domain-aware configuration.

**Request:**
```json
{
  "query": "What is the weight of a Ross 308 at 21 days?",
  "domain": "aviculture",
  "language": "en",
  "query_type": "genetics_performance",
  "entities": {"breed": "Ross 308", "age_days": 21},
  "context_docs": [...],
  "post_process": true,
  "add_disclaimer": true
}
```

**Response:**
```json
{
  "generated_text": "For a Ross 308 at 21 days: male 912 grams, female 887 grams, mixed 900 grams.",
  "provider": "intelia_llama",
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "prompt_tokens": 1245,
  "completion_tokens": 45,
  "total_tokens": 1290,
  "complexity": "simple",
  "calculated_max_tokens": 400,
  "post_processed": true,
  "disclaimer_added": false
}
```

### `POST /v1/route`
Provider routing recommendation.

**Request:**
```json
{
  "query": "Ross 308 weight at 33 days",
  "domain": "aviculture"
}
```

**Response:**
```json
{
  "provider": "intelia_llama",
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "reason": "Domain-specific query detected (aviculture)",
  "is_aviculture": true,
  "confidence": 0.9
}
```

### `POST /v1/calculate-tokens`
Calculate optimal max_tokens based on query complexity.

**Request:**
```json
{
  "query": "Compare Ross 308 and Cobb 500 at 21 and 42 days",
  "query_type": "comparative",
  "entities": {"breed": "Ross 308, Cobb 500", "age_days": "21, 42"}
}
```

**Response:**
```json
{
  "max_tokens": 1080,
  "complexity": "complex",
  "token_range": [900, 1200],
  "factors": {
    "query_length": 10,
    "entity_count": 2,
    "query_type": "comparative",
    "keywords": ["comparative"]
  }
}
```

### `POST /v1/post-process`
Post-process LLM response with formatting cleanup and disclaimers.

**Request:**
```json
{
  "response": "**Header:** Raw LLM output\n\n1. Item one",
  "query": "What are symptoms of coccidiosis?",
  "language": "en",
  "domain": "aviculture"
}
```

**Response:**
```json
{
  "processed_text": "Raw LLM output\n\nItem one\n\n**Important**: This information is provided for educational purposes...",
  "disclaimer_added": true,
  "is_veterinary": true
}
```

## Phase 3: ai-service Integration ✅

**Files created:**
- `ai-service/generation/llm_service_client.py` (330 lines) - HTTP client

**Files modified:**
- `ai-service/generation/generators.py` - Added USE_LLM_SERVICE flag
- `ai-service/.env` - Added LLM service configuration

**Environment variables:**
```bash
# ai-service/.env
USE_LLM_SERVICE=false  # Set to 'true' to use LLM service
LLM_SERVICE_URL=http://localhost:8081
```

## How to Use

### Option 1: Direct LLM Router (Current - Default)
```bash
# ai-service/.env
USE_LLM_SERVICE=false
```

ai-service uses internal LLM router directly (no HTTP calls).

### Option 2: Via LLM Service (New - Recommended)
```bash
# ai-service/.env
USE_LLM_SERVICE=true
LLM_SERVICE_URL=http://localhost:8081
```

1. **Start LLM service:**
```bash
cd llm
# Configure HUGGINGFACE_API_KEY in .env
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

2. **Start ai-service:**
```bash
cd ai-service
# Set USE_LLM_SERVICE=true in .env
python main.py
```

3. **Test integration:**
```bash
python test_llm_service_integration.py
```

## Benefits of LLM Service

### ✅ Separation of Concerns
- **ai-service**: RAG expert (PostgreSQL + Weaviate, entity extraction, context retrieval)
- **llm service**: LLM engine (provider routing, token optimization, post-processing)

### ✅ Multi-Domain Ready
Current: Aviculture-optimized
Future: Add new domains by creating config files:
```
llm/config/
├── aviculture/  (current)
├── agriculture/ (future)
└── aquaculture/ (future)
```

### ✅ Cost Optimization
- Intelligent provider routing (Intelia Llama for aviculture = $0.0004/query)
- Adaptive token calculation (200-1500 tokens based on complexity)
- Provider preferences per domain

### ✅ Quality Control
- 9 formatting cleanup rules
- Automatic veterinary disclaimers
- Multilingual support (12 languages)

## Testing

### Test LLM Service Endpoints
```bash
cd llm
python test_generation_api.py
```

### Test Integration
```bash
python test_llm_service_integration.py
```

### Test with Real Queries
```bash
# Terminal 1: Start LLM service
cd llm && uvicorn app.main:app --port 8081

# Terminal 2: Start ai-service with LLM service enabled
cd ai-service
# Set USE_LLM_SERVICE=true in .env
python main.py

# Terminal 3: Test query
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Ross 308 weight at 21 days", "language": "en"}'
```

## Monitoring

### LLM Service Metrics (Port 8081)
```bash
curl http://localhost:8081/metrics
```

Metrics include:
- `llm_tokens_total` - Token usage by provider
- `llm_requests_total` - Request counts
- `llm_cost_total` - Estimated costs

### ai-service Metrics (Port 8000)
```bash
curl http://localhost:8000/metrics
```

## Migration Path

1. **Current (Default)**: `USE_LLM_SERVICE=false`
   - ai-service uses internal LLM router
   - No changes required
   - Works as before

2. **Transition**: Run both modes in parallel
   - Test LLM service with `USE_LLM_SERVICE=true` on staging
   - Compare metrics and responses
   - Gradually increase traffic

3. **Future**: `USE_LLM_SERVICE=true` (Production)
   - All LLM logic in dedicated service
   - Easier to scale and optimize
   - Multi-domain support

## Cost Comparison

**Before (GPT-4o only):**
- $15.00 per 1M tokens
- Typical query: $0.02

**After (with Intelia Llama for aviculture):**
- Aviculture queries → Intelia Llama: $0.20 per 1M tokens ($0.0004/query)
- General queries → GPT-4o: $15.00 per 1M tokens
- **98.5% cost savings on aviculture queries**

## Files Summary

### Created (Phase 1-3)
- `llm/config/aviculture/config.py` (295 lines)
- `llm/config/aviculture/system_prompts.json` (200 lines)
- `llm/config/aviculture/poultry_terminology.json` (830 lines)
- `llm/config/aviculture/veterinary_terms.json` (219 lines)
- `llm/config/aviculture/languages.json` (254 lines)
- `llm/app/utils/adaptive_length.py` (449 lines)
- `llm/app/utils/post_processor.py` (245 lines)
- `llm/app/models/generation_schemas.py` (172 lines)
- `llm/app/routers/generation.py` (389 lines)
- `llm/test_generation_api.py` (152 lines)
- `ai-service/generation/llm_service_client.py` (330 lines)
- `test_llm_service_integration.py` (200 lines)

**Total: 3,735 lines of intelligent LLM infrastructure**

## Next Steps

1. ✅ Phase 1: Domain configuration migrated
2. ✅ Phase 2: API endpoints created
3. ✅ Phase 3: ai-service integration
4. ⏳ Phase 4: Production testing & monitoring
5. ⏳ Phase 5: Remove duplicate LLM logic from ai-service

## Support

For issues or questions:
1. Check logs: `llm/logs/` and `ai-service/logs/`
2. Review Prometheus metrics
3. Test endpoints individually using the test scripts
