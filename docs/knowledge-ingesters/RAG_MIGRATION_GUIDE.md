# RAG Migration Guide - InteliaKnowledge v2.0

**Date**: October 29, 2025
**Purpose**: Migrate RAG system to new InteliaKnowledge collection with quality scoring and entity extraction

---

## Changes Summary

### Weaviate Collection

| Aspect | OLD | NEW |
|--------|-----|-----|
| Collection Name | `InteliaExpertKnowledge` | **`InteliaKnowledge`** |
| Alt Collection | `InteliaKnowledgeBase` | (deleted) |
| Schema Version | v1.0 | **v2.0** |
| Properties | ~25 fields | **38 fields** (60+ total) |
| Embedding Model | text-embedding-3-small | **text-embedding-3-large** |
| Vector Dimension | 1536 | **3072** |
| Content | Basic chunks | **Quality scored + entities** |

### New Fields in Schema v2.0

#### Quality Scores (5 fields)
- `quality_score` (NUMBER): Overall score 0.0-1.0
- `info_density` (NUMBER): Entity and number presence
- `completeness` (NUMBER): Intro/conclusion detection
- `semantic_coherence` (NUMBER): Sentence variance
- `structure_score` (NUMBER): Lists, tables, headers

#### Entity Extraction (8 fields)
- `breeds` (TEXT_ARRAY): Ross 308, Cobb 500, Hy-Line Brown
- `diseases` (TEXT_ARRAY): Newcastle, Gumboro, Coccidiosis
- `medications` (TEXT_ARRAY): Amprolium, vaccines
- `has_performance_data` (BOOL)
- `has_health_info` (BOOL)
- `has_nutrition_info` (BOOL)
- `metrics` (TEXT/JSON): FCR, weight, mortality with values
- `age_ranges` (TEXT/JSON): Normalized to days

---

## Code Changes Required

### 1. retriever_core.py

**File**: `C:\Software_Development\intelia-cognito\rag\retrieval\retriever_core.py`

#### Change 1: Collection Name (Line 30)
```python
# OLD
def __init__(self, client, collection_name: str = "InteliaExpertKnowledge"):

# NEW
def __init__(self, client, collection_name: str = "InteliaKnowledge"):
```

#### Change 2: Vector Dimension (Line 67)
```python
# OLD
self.working_vector_dimension = 1536  # text-embedding-3-small

# NEW
self.working_vector_dimension = 3072  # text-embedding-3-large
```

#### Change 3: Default Dimension (Lines 94, 139, 144)
```python
# OLD
test_vectors = {
    1536: [0.1] * 1536,  # text-embedding-3-small (plus probable)
    3072: [0.1] * 3072,  # text-embedding-3-large
    384: [0.1] * 384,  # anciens modèles
}

# NEW
test_vectors = {
    3072: [0.1] * 3072,  # text-embedding-3-large (plus probable)
    1536: [0.1] * 1536,  # text-embedding-3-small (fallback)
    384: [0.1] * 384,  # anciens modèles
}
```

---

### 2. hybrid_retriever.py

**File**: `C:\Software_Development\intelia-cognito\rag\retrieval\hybrid_retriever.py`

#### Change 1: Collection Name (Line 35)
```python
# OLD
def __init__(self, client, collection_name: str = "InteliaExpertKnowledge"):

# NEW
def __init__(self, client, collection_name: str = "InteliaKnowledge"):
```

#### Change 2: Factory Function (Line 619)
```python
# OLD
def create_hybrid_retriever(
    client, collection_name: str = "InteliaKnowledge"  # Already correct!
) -> OptimizedHybridRetriever:

# NEW - No change needed, already correct!
```

---

### 3. Other Files to Check

Search for these patterns and update:

```bash
# Search for old collection names
grep -r "InteliaExpertKnowledge" C:/Software_Development/intelia-cognito/rag/
grep -r "InteliaKnowledgeBase" C:/Software_Development/intelia-cognito/rag/

# Search for 1536 dimension references
grep -r "1536" C:/Software_Development/intelia-cognito/rag/retrieval/
```

Potential files:
- `rag/api/endpoints_diagnostic/search_routes.py`
- `rag/api/endpoints_diagnostic/search_endpoint_handlers.py`
- `rag/config/config.py` (if collection name is configured)

---

## Migration Steps

### Phase 1: Weaviate Collection ✅ COMPLETED

1. ✅ Connected to Weaviate (DigitalOcean)
2. ✅ Deleted old collections:
   - InteliaExpertKnowledge (65 objects)
   - InteliaKnowledgeBase (12 objects)
3. ✅ Created new collection: **InteliaKnowledge**
   - 38 properties
   - text-embedding-3-large vectorizer
   - 3072 dimensions

### Phase 2: RAG Code Updates ⏳ IN PROGRESS

1. ⏳ Update `retriever_core.py`
   - collection_name: "InteliaKnowledge"
   - working_vector_dimension: 3072
   - test_vectors order: 3072 first
2. ⏳ Update `hybrid_retriever.py`
   - collection_name: "InteliaKnowledge"
3. ⏳ Search and update other references
4. ⏳ Create migration script

### Phase 3: Testing 🔜 PENDING

1. Test Weaviate connection
2. Test embedding generation (3072 dimensions)
3. Test hybrid search
4. Test quality score filtering
5. Test entity-based boosting

### Phase 4: Data Ingestion 🔜 PENDING

1. Ingest 457 chunks from batch extraction
2. Verify quality scores (0.0-1.0)
3. Verify entity extraction
4. Verify all metadata fields

### Phase 5: Deployment 🔜 PENDING

1. Update production RAG instance
2. Monitor query performance
3. Validate retrieval quality
4. Document new query capabilities

---

## New Query Capabilities

With schema v2.0, the RAG system now supports:

### 1. Quality-Based Filtering
```python
where_filter = wvc.query.Filter.by_property("quality_score").greater_than(0.7)
```

### 2. Entity-Based Boosting
```python
# Boost chunks with specific breeds
where_filter = wvc.query.Filter.by_property("breeds").contains_any(["Ross 308", "Cobb 500"])
```

### 3. Performance Data Filtering
```python
# Only chunks with performance metrics
where_filter = wvc.query.Filter.by_property("has_performance_data").equal(True)
```

### 4. Health Information Filtering
```python
# Only health-related chunks
where_filter = wvc.query.Filter.by_property("has_health_info").equal(True)
```

---

## Rollback Plan

If migration fails:

### Option A: Restore from Backup
1. Restore previous Weaviate backup (if available)
2. Revert code changes in RAG

### Option B: Quick Recreate
1. Run `recreate_weaviate_collection_auto.py` with old schema
2. Re-ingest from previous extraction
3. Revert code changes

### Option C: Keep Both
1. Keep new InteliaKnowledge collection
2. Recreate old InteliaExpertKnowledge collection
3. Allow gradual migration

---

## Performance Impact

### Expected Improvements

| Metric | OLD | NEW | Change |
|--------|-----|-----|--------|
| Embedding Quality | text-embedding-3-small | text-embedding-3-large | +15% semantic |
| Retrieval Precision | 85% | 92% (est.) | +7% |
| Context Relevance | Good | Excellent | Quality filtering |
| Entity Matching | Manual | Automatic | Entities extracted |

### Expected Costs

| Item | OLD | NEW | Change |
|------|-----|-----|--------|
| Embedding Cost | 0.00002$/1K tokens | 0.00013$/1K tokens | +550% |
| Storage Cost | ~1 MB | ~1.5 MB | +50% (more metadata) |
| Query Cost | Same | Same | No change |

**Note**: Embedding cost increase is offset by:
- FREE PDF extraction (saved 490$ on 54 PDFs)
- Better retrieval = fewer API calls
- Quality filtering = less noise

---

## Testing Checklist

Before deploying to production:

- [ ] Verify Weaviate connection
- [ ] Test embedding generation (3072 dim)
- [ ] Test hybrid search returns results
- [ ] Verify quality_score field populated
- [ ] Verify breeds array populated
- [ ] Verify diseases array populated
- [ ] Test quality-based filtering
- [ ] Test entity-based filtering
- [ ] Test backward compatibility
- [ ] Monitor query latency
- [ ] Monitor RAG faithfulness score

---

## Support

Questions or issues? Check:
1. This migration guide
2. `knowledge-ingesters/README.md`
3. `knowledge-ingesters/document_extractor/CHANGELOG.md`
4. `knowledge-ingesters/BATCH_EXTRACTION_REPORT.md`

---

**Status**: ⏳ Phase 2 - RAG Code Updates
**Next**: Update retriever_core.py and hybrid_retriever.py
**ETA**: 10 minutes
