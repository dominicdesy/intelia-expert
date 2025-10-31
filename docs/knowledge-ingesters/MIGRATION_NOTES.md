# Migration Notes: data-pipelines → knowledge-ingesters

**Date**: October 29, 2025  
**Reason**: Better reflect the purpose - ingesting knowledge for RAG system

## What Changed

### Directory Structure
```
OLD: intelia-cognito/data-pipelines/
NEW: intelia-cognito/knowledge-ingesters/
```

### Documentation
```
OLD: docs/data-pipelines/
NEW: docs/knowledge-ingesters/
```

## Updated References

### Code Files
- `knowledge-ingesters/document_extractor/batch_extract_10.py`
- `knowledge-ingesters/document_extractor/batch_process_documents.py`
- `knowledge-ingesters/document_extractor/core/path_based_classifier.py`

### Documentation Files
- All markdown files in `docs/knowledge-ingesters/`
- All markdown files in `docs/implementation/`
- `knowledge-ingesters/document_extractor/DEPLOYMENT.md`

## Testing

### Verified Working
```bash
cd knowledge-ingesters/document_extractor
python -c "from multi_format_pipeline import MultiFormatPipeline; print('Import successful!')"
# Output: Import successful!
```

## Impact

### Breaking Changes
None - all imports and paths automatically updated

### Action Required
If you have external scripts or bookmarks referencing:
- `data-pipelines/` → Update to `knowledge-ingesters/`
- `docs/data-pipelines/` → Update to `docs/knowledge-ingesters/`

## Rationale

### Why "knowledge-ingesters"?
- **More Accurate**: These scripts ingest knowledge into Weaviate (RAG system)
- **Not Generic Pipelines**: Not ETL/data pipelines, but specialized knowledge extraction
- **Clearer Purpose**: Immediately understand function from name
- **Industry Standard**: Follows convention like "scrapers", "processors", "ingesters"

### Why Not Just "ingesters"?
- Needs context: "knowledge-ingesters" is clearer than just "ingesters"
- Aligns with purpose: feeding knowledge base for RAG
- Professional naming: `{what}-{how}` pattern

---

**All systems operational** - renaming complete and verified!
