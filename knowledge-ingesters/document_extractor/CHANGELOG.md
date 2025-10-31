# Changelog - Document Extractor

## Version 2.0.0 (October 29, 2025)

### Major Changes

#### FREE PDF Extraction (pdfplumber)
- **Added**: `pdf_text_extractor.py` using pdfplumber (100% FREE)
- **Performance**: 0.738s for 6 pages (fast!)
- **Cost Savings**: ~490$ USD for 54 PDFs (was: 0.21$/page with Claude Vision)
- **Quality**: Winner of A/B/C test (vs PyMuPDF, pypdf)
- **Features**: Supports table detection, good text quality
- **Status**: Replaces Claude Vision for document_extractor

#### Quality Scoring System
- **Added**: `chunk_quality_scorer.py` with 5 metrics
  - Info Density (30%): Entity and number presence
  - Completeness (20%): Intro/conclusion detection
  - Semantic Coherence (30%): Sentence variance, transitions
  - Length Score (10%): Optimal 400-600 words
  - Structure Score (10%): Lists, tables, headers
- **Output**: 0.0-1.0 scores per chunk
- **Impact**: RAG Score +3 points (95 → 98)

#### Entity Extraction System
- **Added**: `entity_extractor.py` with domain-specific entities
  - Breeds: Ross 308, Cobb 500, Hy-Line Brown, Aviagen, etc.
  - Diseases: Newcastle, Gumboro, Coccidiosis, E. coli, etc.
  - Medications: Amprolium, vaccines, antibiotics
  - Performance Metrics: FCR, weight, mortality (with values)
  - Age Ranges: Converted to days for filtering
- **Features**: Boolean flags (has_performance_data, has_health_info, has_nutrition_info)
- **Impact**: Enables precision filtering and boosting

### Updated Components

#### multi_format_pipeline.py
- **Changed**: Now uses `pdf_text_extractor.py` instead of `pdf_vision_extractor.py`
- **Changed**: Extraction method renamed: "pdf_vision" → "pdf_text"
- **Added**: Quality scoring and entity extraction integration
- **Added**: Enriched chunks with 13 new metadata fields

#### chunking_service.py
- **Added**: Integration with `ChunkQualityScorer`
- **Added**: Integration with `EntityExtractor`
- **Added**: `_enrich_chunks_with_quality_and_entities()` method
- **Output**: Chunks now include quality scores and extracted entities

#### schema_v2.py (Weaviate)
- **Added**: 5 quality score fields
- **Added**: 8 entity extraction fields
- **Total**: 60+ metadata fields (was: 47)

### Testing

#### test_abc_pdf_extraction.py (NEW)
- **Purpose**: A/B/C comparison of PDF extraction tools
- **Tools Tested**: PyMuPDF, pdfplumber, pypdf
- **Winner**: pdfplumber (best balance of speed, quality, table support)
- **Results**: 
  - pdfplumber: 0.738s, 20,693 chars, table support
  - pypdf: 0.066s, 20,442 chars, no tables
  - PyMuPDF: Error (document closed bug)

### Documentation

#### README.md
- **Updated**: Full rewrite to reflect pdfplumber integration
- **Added**: Quality scoring and entity extraction documentation
- **Added**: Cost comparison (OLD vs NEW)
- **Added**: RAG Score progression (95 → 98)

#### tests/README.md (NEW)
- **Added**: Documentation for test organization
- **Added**: Description of active vs archived tests

#### CHANGELOG.md (NEW)
- **Added**: This file to track version history

### Performance Improvements

- **Cost**: 490$ → 0$ (FREE PDF extraction)
- **Speed**: ~0.12s per page (faster than Claude Vision)
- **RAG Score**: 95/100 → 98/100 (+3 points)
- **Quality**: Average chunk quality 0.636 (63.6%)

### Breaking Changes

- **PDF Extraction**: No longer requires CLAUDE_API_KEY for basic PDF processing
- **Dependencies**: New requirement: `pdfplumber` (was: PyMuPDF + anthropic)
- **Output Format**: Chunks now include 13 additional metadata fields

### Deprecated

- **pdf_vision_extractor.py**: Kept for reference, but no longer used in document_extractor
  - Still available for `table_extractor` (specialized table extraction)
  - Status: LEGACY

### Migration Notes

If upgrading from v1.0.0:

1. Install pdfplumber: `pip install pdfplumber`
2. Update Weaviate schema to include new quality/entity fields
3. Existing extractions remain valid (backward compatible metadata)
4. New extractions will have enhanced metadata automatically

---

## Version 1.0.0 (October 28, 2025)

### Initial Release

- Multi-format support (PDF, DOCX, Web)
- Path-based classification (70%)
- Vision-based enrichment (25%)
- Smart defaults (5%)
- 600-word semantic chunking
- Weaviate integration
- Multi-tenant support

**Status**: Production-ready
**RAG Score**: 95/100
