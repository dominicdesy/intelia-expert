# Terminology Files - Migration Notice

## ⚠️ Important: Terminology has been migrated to LLM Service

As of **2025-10-27**, all poultry terminology has been migrated and enhanced in the **LLM service**.

### Deprecated Files

- `poultry_terminology.json` → **DEPRECATED** (renamed to `.OLD`)
  - This file is outdated and should not be used
  - See LLM service for current terminology

### Current Terminology Location

All terminology is now managed in the **LLM service**:

```
llm/app/domain_config/domains/aviculture/
├── poultry_terminology.json          # Enhanced base terminology (10 terms)
├── value_chain_terminology.json      # Value chain coverage (104 terms)
└── extended_glossary.json            # PDF glossary extraction (1,476 terms)
```

**Total: 1,580 terminology terms**

### How to Use Terminology

The LLM service automatically injects relevant terminology based on query content.

**Example API call**:
```bash
curl -X POST http://localhost:8081/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the FCR for Ross 308?",
    "domain": "aviculture",
    "language": "en",
    "query_type": "genetics_performance"
  }'
```

The system will automatically:
1. Detect relevant terminology categories
2. Match keywords in the query
3. Inject 10-15 most relevant terms into the system prompt
4. Generate response with precise technical vocabulary

### Features

✅ **Intelligent Injection**: Only relevant terms loaded (not all 1,580)
✅ **Category Detection**: 9 domain categories (hatchery, nutrition, health, etc.)
✅ **Keyword Matching**: 1,679 indexed keywords for fast lookup
✅ **Multilingual**: Supports EN/FR (expandable to 16 languages)
✅ **Token Aware**: Respects token budget limits (~400-500 tokens added)

### Files Still in AI-Service (Not Migrated)

These files remain in ai-service because they serve different purposes:

- `domain_keywords.json` - Used for query routing in ai-service
- Other OOD/security related vocabulary - Specific to ai-service guardrails

### Questions?

See documentation:
- `llm/TERMINOLOGY_ENRICHMENT.md` - Complete terminology system documentation
- `MIGRATION_STATUS.md` - Migration status and architecture

---

**Last Updated**: 2025-10-27
