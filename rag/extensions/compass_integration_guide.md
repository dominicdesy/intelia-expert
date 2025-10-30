# Compass RAG Integration Guide

**Date**: 2025-10-30
**Version**: 1.0.0
**Status**: Phase 3 Implementation

---

## Overview

The Compass extension enables the RAG system to answer real-time questions about users' barn conditions by fetching live sensor data from Compass.

## Architecture

```
User Query: "Quelle est la température dans mon poulailler 2?"
    ↓
CompassExtension.is_compass_query() → True
    ↓
Extract barn_number="2", data_type="temperature"
    ↓
fetch_barn_data(user_token, "2")
    ↓
Backend API: GET /api/v1/compass/me/barns/2
    ↓
Compass API (via CompassAPIService)
    ↓
Real-time data: {temperature: 22.5°C, humidity: 65%, ...}
    ↓
Enrich context with barn data
    ↓
LLM generates response with real data
```

## Usage

### 1. Basic Integration in RAG Engine

```python
from extensions.compass_extension import get_compass_extension

# In your query processing pipeline
compass_extension = get_compass_extension()

# Check if query is about barn conditions
if compass_extension.is_compass_query(user_query):
    # Enrich context with real-time data
    enriched = await compass_extension.enrich_context(
        query=user_query,
        user_token=user_jwt_token,
        existing_context=retrieved_documents_context
    )

    # Use enriched context for LLM
    context = enriched["context"]
    barn_data = enriched["barn_data"]
```

### 2. Integration in Response Generator

```python
# In generators.py or response_generator.py

async def generate_response(
    self,
    query: str,
    context: str,
    user_token: Optional[str] = None
) -> str:
    """Generate response with Compass enrichment"""

    # Import Compass extension
    from extensions.compass_extension import get_compass_extension

    compass = get_compass_extension()

    # Enrich context if Compass query
    if user_token and compass.is_compass_query(query):
        enriched = await compass.enrich_context(
            query=query,
            user_token=user_token,
            existing_context=context
        )
        context = enriched["context"]

    # Add Compass system prompt if applicable
    if enriched.get("is_compass_query"):
        system_prompt += compass.create_compass_system_prompt()

    # Continue with normal response generation...
```

### 3. Integration in Chat Endpoint

```python
# In api/endpoints_chat/chat_routes.py or similar

from extensions.compass_extension import get_compass_extension

@router.post("/chat")
async def handle_chat(
    request: ChatRequest,
    user_token: str = Depends(get_user_token)
):
    """Chat endpoint with Compass support"""

    # Get RAG engine
    rag_engine = get_rag_engine()

    # Check for Compass query
    compass = get_compass_extension()

    if compass.is_compass_query(request.query):
        # Enrich with Compass data before RAG processing
        enriched = await compass.enrich_context(
            query=request.query,
            user_token=user_token
        )

        # Pass enriched context to RAG
        response = await rag_engine.generate_response(
            query=request.query,
            additional_context=enriched["context"],
            metadata={"compass_data": enriched["barn_data"]}
        )
    else:
        # Normal RAG processing
        response = await rag_engine.generate_response(
            query=request.query
        )

    return response
```

## Configuration

### Environment Variables

```bash
# Enable/disable Compass integration
COMPASS_ENABLED=true

# Backend API URL for Compass endpoints
BACKEND_URL=http://localhost:8000

# Compass API token (for backend)
COMPASS_API_TOKEN=your_token_here
```

### Disable Compass

Set `COMPASS_ENABLED=false` to disable the extension without removing code.

## Query Detection

The extension automatically detects Compass queries using keywords:

### Barn Keywords (Required)
- `poulailler`, `poulaillers`, `barn`, `barns`
- `bâtiment`, `batiment`, `étable`, `stable`

### Data Type Keywords (Optional)
- **Temperature**: `température`, `temp`, `temperature`, `chaleur`, `froid`
- **Humidity**: `humidité`, `humidity`, `humid`, `taux d'humidité`
- **Weight**: `poids`, `weight`, `masse`, `grammes`, `kg`
- **Age**: `âge`, `age`, `jours`, `days`, `troupeau`

### Example Queries

**Detected as Compass queries**:
- ✅ "Quelle est la température dans mon poulailler 2?"
- ✅ "Combien pèsent les poulets dans le barn 3?"
- ✅ "Quel âge a le troupeau du poulailler 1?"
- ✅ "Conditions actuelles poulailler 2"
- ✅ "Humidité dans mes poulaillers"

**NOT detected** (missing keywords):
- ❌ "Comment gérer la température?" (no barn mention)
- ❌ "Quel est le poids idéal?" (no barn mention)
- ❌ "Mes poulets sont malades" (not about conditions)

## Barn Number Extraction

The extension extracts barn numbers from natural language:

```python
compass.extract_barn_numbers("température poulailler 2")
# Returns: ["2"]

compass.extract_barn_numbers("poulaillers 1 et 3")
# Returns: ["1", "3"]

compass.extract_barn_numbers("mon poulailler")
# Returns: [] (will fetch all barns)
```

## Response Format

### Enriched Context

```
=== DONNÉES TEMPS RÉEL COMPASS ===
Poulailler 2 (Poulailler Est):
- Température: 22.5°C
- Humidité: 65.0%
- Poids moyen: 2450g
- Âge du troupeau: 35 jours

Poulailler 3 (Poulailler Ouest):
- Température: 23.1°C
- Humidité: 63.0%
- Poids moyen: 2520g
- Âge du troupeau: 35 jours
=== FIN DONNÉES COMPASS ===
```

### Metadata

```json
{
  "is_compass_query": true,
  "context": "... enriched context ...",
  "barn_data": [
    {
      "barn_number": "2",
      "barn_name": "Poulailler Est",
      "temperature": 22.5,
      "humidity": 65.0,
      "weight": 2450.0,
      "age": 35,
      "has_data": true
    }
  ],
  "requested_barns": ["2"],
  "requested_data_types": ["temperature"]
}
```

## Error Handling

### API Errors

If Compass API fails, the extension returns gracefully:

```python
CompassBarnInfo(
    barn_number="2",
    barn_name="Poulailler 2",
    error="Données non disponibles (code 404)"
)
```

### Timeouts

10-second timeout on API calls:
```python
try:
    response = requests.get(url, headers=headers, timeout=10)
except requests.exceptions.Timeout:
    # Return error info without crashing
```

### Missing Data

If specific sensors are offline:
```python
CompassBarnInfo(
    barn_number="2",
    barn_name="Poulailler Est",
    temperature=22.5,
    humidity=None,  # Sensor offline
    weight=2450.0,
    age=35
)
```

The LLM will mention: "Les données d'humidité ne sont pas disponibles actuellement."

## Testing

### Unit Tests

```python
import pytest
from extensions.compass_extension import CompassExtension

def test_barn_keyword_detection():
    compass = CompassExtension()

    assert compass.is_compass_query("température poulailler 2")
    assert compass.is_compass_query("poids barn 3")
    assert not compass.is_compass_query("comment nourrir les poulets")

def test_barn_number_extraction():
    compass = CompassExtension()

    assert compass.extract_barn_numbers("poulailler 2") == ["2"]
    assert compass.extract_barn_numbers("barns 1 et 3") == ["1", "3"]
    assert compass.extract_barn_numbers("mon poulailler") == []

def test_data_type_detection():
    compass = CompassExtension()

    assert "temperature" in compass.detect_data_types("quelle température")
    assert "humidity" in compass.detect_data_types("taux d'humidité")
    assert "weight" in compass.detect_data_types("combien pèsent")
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_context_enrichment():
    compass = CompassExtension()

    # Mock user token
    user_token = "mock_jwt_token"

    # Test enrichment
    enriched = await compass.enrich_context(
        query="température poulailler 2",
        user_token=user_token
    )

    assert enriched["is_compass_query"] == True
    assert "DONNÉES TEMPS RÉEL COMPASS" in enriched["context"]
    assert len(enriched["barn_data"]) > 0
```

### End-to-End Test

```bash
# 1. Start backend with Compass enabled
cd backend
uvicorn app.main:app --reload

# 2. Configure test user with barn 2 → device 849
# (Via admin UI or SQL)

# 3. Test query via RAG
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quelle est la température dans mon poulailler 2?",
    "language": "fr"
  }'

# Expected response:
# "D'après les données temps réel, la température dans votre Poulailler Est
# (poulailler 2) est actuellement de 22.5°C..."
```

## Performance Considerations

### Latency

- **API Call**: ~100-300ms (Compass API)
- **Context Enrichment**: ~10-20ms
- **Total Overhead**: ~150-350ms per Compass query

### Caching (Future)

Consider adding Redis cache for frequently queried barns:
```python
# Cache barn data for 30 seconds
cache_key = f"compass:barn:{user_id}:{barn_number}"
cached_data = redis.get(cache_key)

if cached_data:
    return json.loads(cached_data)

# Fetch from API
data = await fetch_barn_data(...)

# Cache for 30 seconds
redis.setex(cache_key, 30, json.dumps(data))
```

### Rate Limiting

The backend API should implement rate limiting for Compass calls:
- Max 10 requests/minute per user
- Max 100 requests/minute globally

## Security

### Token Validation

User JWT tokens are validated by backend before Compass API access:
```python
# Backend middleware validates token
# Only authenticated users can access /api/v1/compass/me/*
```

### Data Isolation

RLS policies ensure users only see their own barns:
```sql
-- In user_compass_config table
CREATE POLICY "users_view_own_compass_config"
    ON user_compass_config
    FOR SELECT
    USING (auth.uid() = user_id);
```

### API Token

Compass API token is:
- Stored in backend environment variables only
- Never exposed to frontend or RAG
- Rotated periodically (admin responsibility)

## Troubleshooting

### "Données non disponibles"

**Possible causes**:
1. User doesn't have Compass enabled
2. Barn not configured for user
3. Compass API down
4. Network timeout

**Check**:
```sql
-- Verify user config
SELECT * FROM user_compass_config WHERE user_id = 'USER_UUID';

-- Check if barn exists
SELECT barns FROM user_compass_config
WHERE user_id = 'USER_UUID'
AND barns @> '[{"client_number": "2"}]'::jsonb;
```

### Extension Not Detecting Queries

**Check**:
1. COMPASS_ENABLED environment variable
2. Query contains barn keywords
3. Logs: `compass_extension.is_compass_query()` returns False

**Debug**:
```python
compass = get_compass_extension()
query = "température poulailler 2"

print(f"Is Compass query: {compass.is_compass_query(query)}")
print(f"Barn numbers: {compass.extract_barn_numbers(query)}")
print(f"Data types: {compass.detect_data_types(query)}")
```

### Backend API Errors

**Check**:
```bash
# Test backend endpoint directly
curl -H "Authorization: Bearer YOUR_JWT" \
     http://localhost:8000/api/v1/compass/me/barns/2

# Expected: 200 OK with barn data
# If 404: Barn not configured
# If 401: Token invalid
# If 503: Compass API down
```

## Future Enhancements

### 1. Historical Data

Add support for historical queries:
```python
"Quelle était la température hier dans le poulailler 2?"
```

### 2. Alerts Integration

Proactive notifications:
```python
"La température dans le poulailler 2 dépasse 30°C!"
```

### 3. Multi-Barn Comparison

Comparative analysis:
```python
"Compare les conditions entre mes poulaillers 1 et 2"
```

### 4. Predictive Analytics

Use Compass predictions:
```python
"Quel sera le poids prévu dans 7 jours?"
```

### 5. Charts & Visualizations

Return structured data for charts:
```json
{
  "response": "...",
  "chart_data": {
    "type": "line",
    "data": [...]
  }
}
```

## References

- Backend API: `backend/app/api/v1/compass.py`
- Compass Service: `backend/app/services/compass_api_service.py`
- Integration Analysis: `docs/COMPASS_INTEGRATION_ANALYSIS.md`
- Phase 1 Complete: `docs/implementation/COMPASS_INTEGRATION_PHASE1_COMPLETE.md`

---

**Last Updated**: 2025-10-30
**Status**: Phase 3 In Progress
