# Intelia LLM Service

OpenAI-compatible LLM inference API for Intelia, providing specialized AI for animal production.

**Version**: 1.0.0
**Provider**: HuggingFace Inference API (Phase 1) → vLLM self-hosted (Phase 2)

---

## Features

- ✅ **OpenAI-compatible API** - Drop-in replacement for OpenAI client libraries
- ✅ **Provider abstraction** - Seamless migration from HuggingFace API to self-hosted vLLM
- ✅ **Prometheus metrics** - Full observability for monitoring and alerting
- ✅ **Health checks** - Ready for production deployment
- ✅ **Fine-tuning ready** - Support for custom Llama 3.1 8B models

---

## Quick Start

### Local Development

```bash
# 1. Clone repository
cd llm/

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your HuggingFace API key

# 4. Run server
uvicorn app.main:app --reload --port 8081

# 5. Test API
curl http://localhost:8081/health
```

### Docker

```bash
# Build image
docker build -t intelia-llm:latest .

# Run container
docker run -p 8081:8081 \
  -e HUGGINGFACE_API_KEY=hf_xxxxx \
  -e HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct \
  intelia-llm:latest

# Check health
curl http://localhost:8081/health
```

---

## API Documentation

### Endpoints

#### POST `/v1/chat/completions`
OpenAI-compatible chat completion endpoint.

**Request:**
```json
{
  "model": "intelia-llama-3.1-8b-aviculture",
  "messages": [
    {"role": "user", "content": "Comment réduire la mortalité des poulets?"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "intelia-llama-3.1-8b-aviculture",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Pour réduire la mortalité des poulets..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 320,
    "total_tokens": 470
  }
}
```

#### GET `/v1/models`
List available models.

#### GET `/health`
Health check endpoint.

#### GET `/metrics`
Prometheus metrics (for monitoring).

#### GET `/docs`
Interactive API documentation (Swagger UI).

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `huggingface` | Provider: `huggingface` or `vllm` |
| `HUGGINGFACE_API_KEY` | Yes (Phase 1) | - | HuggingFace API token (starts with `hf_`) |
| `HUGGINGFACE_MODEL` | Yes (Phase 1) | `meta-llama/Llama-3.1-8B-Instruct` | Model ID on HuggingFace |
| `VLLM_URL` | Yes (Phase 2) | `http://localhost:8000` | vLLM server URL (self-hosted) |
| `PORT` | No | `8081` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `ENABLE_METRICS` | No | `true` | Enable Prometheus metrics |

---

## Usage with OpenAI Client

This service is **fully compatible** with OpenAI Python client:

```python
from openai import OpenAI

# Point to Intelia LLM service instead of OpenAI
client = OpenAI(
    base_url="http://llm:8081/v1",  # Internal URL
    api_key="dummy"  # Not used, but required by client
)

# Use exactly like OpenAI API
response = client.chat.completions.create(
    model="intelia-llama-3.1-8b-aviculture",
    messages=[
        {"role": "user", "content": "Comment réduire la mortalité des poulets?"}
    ]
)

print(response.choices[0].message.content)
```

---

## Integration with ai-service

The `ai-service` orchestrator calls `llm` for domain-specific queries:

```python
# In ai-service
import httpx

async def call_llm_service(message: str, context: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://llm:8081/v1/chat/completions",
            json={
                "model": "intelia-llama-3.1-8b-aviculture",
                "messages": [
                    {"role": "system", "content": f"Context: {context}"},
                    {"role": "user", "content": message}
                ]
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

---

## Monitoring

### Prometheus Metrics

Exposed at `GET /metrics`:

- `llm_requests_total` - Total inference requests
- `llm_inference_duration_seconds` - Latency histogram
- `llm_tokens_generated_total` - Total tokens generated
- `llm_tokens_prompt_total` - Total prompt tokens
- `llm_model_loaded` - Model availability (1=loaded, 0=not loaded)
- `llm_errors_total` - Total errors by type

### Grafana Dashboard

Configure Prometheus to scrape metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'intelia-llm'
    static_configs:
      - targets: ['llm:8081']
    metrics_path: '/metrics'
```

---

## Testing

### Manual Test

```bash
# Test health
curl http://localhost:8081/health

# Test chat completion
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "intelia-llama-3.1-8b-aviculture",
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 50
  }'
```

### Python Test Script

See `scripts/test_llm_access.py` for validation script.

---

## Deployment

### Digital Ocean App Platform

Service is deployed automatically via GitHub Actions when code is pushed to `main` branch.

**Configuration:**
- Service: `llm`
- Instance: Basic ($12/mois)
- Port: 8081
- Internal URL: `http://llm:8081`
- Environment variables configured in DO Console (secrets)

---

## Migration Path

### Phase 1: HuggingFace Serverless API (Current)
- **Cost**: ~$0.20/1M tokens (pay-per-use)
- **Latency**: 1-3s (cold start), <1s (warm)
- **Setup**: Zero infrastructure, just API key

### Phase 2: Self-hosted vLLM (Future)
- **Cost**: $245/mois (RunPod GPU) - fixed cost
- **Latency**: <500ms (always warm)
- **Setup**: GPU server with vLLM

**Migration is seamless** - just change environment variables:
```bash
# Phase 1 → Phase 2 (zero code changes)
LLM_PROVIDER=vllm
VLLM_URL=http://gpu-server:8000
```

---

## Troubleshooting

### Error: "Gated model - Access denied"
- Ensure you've accepted Meta Llama terms on HuggingFace
- Check your HuggingFace token has "Read access to gated repos" permission
- Wait for Meta approval (usually instant, max 2h)

### Error: "Invalid API key"
- Verify `HUGGINGFACE_API_KEY` starts with `hf_`
- Check token has "Inference" permission
- Test token: `huggingface-cli whoami`

### High latency (>5s)
- First request has cold start penalty (~2-3s)
- Subsequent requests should be <1s
- Consider upgrading to HF Inference Endpoint (dedicated)

### Service won't start
- Check logs: `docker logs <container_id>`
- Verify all required environment variables are set
- Test HuggingFace access locally (see `scripts/test_llm_access.py`)

---

## Development

### Project Structure

```
llm/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── dependencies.py      # Shared dependencies
│   ├── models/
│   │   ├── llm_client.py    # Provider abstraction
│   │   └── schemas.py       # Pydantic models
│   ├── routers/
│   │   ├── chat.py          # Chat completions endpoint
│   │   ├── models.py        # Models list endpoint
│   │   └── health.py        # Health & metrics
│   └── utils/
│       ├── logger.py        # Logging setup
│       └── metrics.py       # Prometheus metrics
├── scripts/
│   └── test_llm_access.py   # Test script
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### Adding New Providers

To add a new LLM provider:

1. Create provider class in `app/models/llm_client.py`:
```python
class MyProvider(LLMClient):
    async def generate(self, messages, **kwargs):
        # Implementation
        pass
```

2. Update factory in `llm_client.py`:
```python
def get_llm_client(provider, **kwargs):
    if provider == "myprovider":
        return MyProvider(...)
```

3. Update config in `app/config.py` to accept new env vars

---

## License

Proprietary - Intelia Inc.

---

## Support

For questions or issues:
- Check logs: `docker logs <container>`
- Health check: `curl http://llm:8081/health`
- Metrics: `curl http://llm:8081/metrics`
- API docs: http://llm:8081/docs

---

**Version**: 1.0.0
**Last Updated**: 2025-10-27
