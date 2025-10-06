# Intelia Expert - LLM Module

Advanced Multi-LLM RAG System for Poultry Production

## 📚 Complete Documentation

**→ [docs/COMPLETE_SYSTEM_DOCUMENTATION.md](docs/COMPLETE_SYSTEM_DOCUMENTATION.md)**

This comprehensive guide covers:
- System architecture & components
- Quick start & deployment
- API reference
- Configuration
- Monitoring & operations
- Development guidelines
- Troubleshooting

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn api.main:app --reload --port 8000
```

## 🔑 Key Features

- ✅ **8 Specialized Domains** - Nutrition, Health, Production, Genetics, Management, Environment, Welfare, Economics
- ✅ **Multi-LLM Router** - GPT-4o, Claude 3.5, DeepSeek, Llama 3
- ✅ **Cohere Rerank v3** - Advanced result re-ranking
- ✅ **13 Languages** - French, English, Spanish, German, Dutch, Italian, Portuguese, Polish, Hindi, Indonesian, Thai, Chinese
- ✅ **Conversation Memory** - Multi-turn contextual dialogue
- ✅ **Quality Validation** - 6 automated quality checks
- ✅ **RAGAS Evaluation** - Automated quality metrics

## 📖 Documentation Structure

```
docs/
├── COMPLETE_SYSTEM_DOCUMENTATION.md    # Complete reference (1,000+ lines)
└── archive/                            # Historical documentation
    ├── DEPLOYMENT_CHECKLIST.md
    ├── DOMAIN_COVERAGE_ANALYSIS.md
    ├── INTEGRATION_VALIDATION_REPORT.md
    └── ... (39 archived files)
```

## 🏗️ Architecture

```
User Query → API Layer → RAG Engine → Query Router → Retrieval (PostgreSQL/Weaviate)
                                                   → Cohere Rerank
                                                   → Multi-LLM Router
                                                   → Response Validator
                                                   → Final Response
```

## 🔗 Quick Links

- [Complete Documentation](docs/COMPLETE_SYSTEM_DOCUMENTATION.md)
- [Configuration Guide](docs/COMPLETE_SYSTEM_DOCUMENTATION.md#configuration)
- [API Reference](docs/COMPLETE_SYSTEM_DOCUMENTATION.md#api-reference)
- [Deployment Guide](docs/COMPLETE_SYSTEM_DOCUMENTATION.md#deployment)
- [Troubleshooting](docs/COMPLETE_SYSTEM_DOCUMENTATION.md#troubleshooting)

## 📊 Status

**Version:** 5.1.0
**Architecture:** Multi-LLM RAG with Conversation Memory
**Integration Status:** 9/9 functions verified (100% coverage)
**Domain Coverage:** 8/8 domains (100% coverage)
**Languages:** 13 supported

## 🤝 Contributing

See development section in [Complete Documentation](docs/COMPLETE_SYSTEM_DOCUMENTATION.md#development)

---

**For complete system documentation, API reference, deployment guides, and troubleshooting:**

→ **[docs/COMPLETE_SYSTEM_DOCUMENTATION.md](docs/COMPLETE_SYSTEM_DOCUMENTATION.md)**
