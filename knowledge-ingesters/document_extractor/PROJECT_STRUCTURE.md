# Document Extractor - Project Structure

## Overview
```
document_extractor/
├── core/                    # Core extraction and processing modules
├── weaviate_integration/    # Weaviate schema and ingestion
├── config/                  # Configuration files (path rules)
├── tests/                   # Test scripts
└── docs/                    # Documentation (in /docs/data-pipelines/document_extractor/)
```

## Core Modules

### Extraction
- `core/pdf_text_extractor.py` - **NEW** FREE PDF extraction (pdfplumber)
- `core/pdf_vision_extractor.py` - LEGACY Claude Vision extraction
- `core/docx_extractor.py` - DOCX text extraction
- `core/web_scraper.py` - Web page scraping

### Classification & Enrichment
- `core/path_based_classifier.py` - Path-based metadata (70%)
- `core/metadata_enricher.py` - Vision-based metadata (25% + 5%)

### Processing
- `core/chunking_service.py` - Semantic chunking + quality + entities
- `core/chunk_quality_scorer.py` - **NEW** Quality scoring (5 metrics)
- `core/entity_extractor.py` - **NEW** Entity extraction (breeds, diseases, etc.)

### Integration
- `weaviate_integration/schema_v2.py` - Weaviate schema (60+ fields)
- `multi_format_pipeline.py` - **MAIN** End-to-end pipeline

## Configuration

- `config/path_rules/intelia.yaml` - Path classification rules for intelia org

## Testing

### Active Tests
- `test_abc_pdf_extraction.py` - A/B/C comparison of PDF extractors
- `test_end_to_end.py` - End-to-end pipeline testing
- `batch_extract_10.py` - Batch extraction for 10 PDFs
- `batch_process_documents.py` - Production batch processing

### Archived Tests (tests/archive/)
- `ab_test_chunking.py` - OLD chunking strategy tests
- `knowledge_extractor.py` - LEGACY old extraction system
- `weaviate_cleanup.py` - Utility for Weaviate cleanup

## Documentation

- `README.md` - Main documentation (Quick Start, Features, Usage)
- `CHANGELOG.md` - Version history and changes
- `ARCHITECTURE.md` - System architecture and design decisions
- `DEPLOYMENT.md` - Deployment guide
- `tests/README.md` - Test organization and descriptions
- `PROJECT_STRUCTURE.md` - This file

## Data Flow

```
1. Input: PDF/DOCX/Web URL
   ↓
2. Extraction (FREE pdfplumber for PDFs!)
   ↓
3. Path-based Classification (70%)
   ↓
4. Vision-based Enrichment (25% + 5%)
   ↓
5. Semantic Chunking (600 words, 120 overlap)
   ↓
6. Quality Scoring (5 metrics)
   ↓
7. Entity Extraction (breeds, diseases, meds, metrics)
   ↓
8. Weaviate Ingestion (60+ metadata fields)
```

## Key Features by Version

### v2.0.0 (Current)
- FREE PDF extraction (pdfplumber)
- Quality scoring system
- Entity extraction system
- 60+ metadata fields
- RAG Score: 98/100
- Cost: 0$ for PDFs

### v1.0.0 (Previous)
- Claude Vision PDF extraction
- 47 metadata fields
- RAG Score: 95/100
- Cost: 0.21$/page for PDFs

## Quick Commands

### Extract a document
```bash
python multi_format_pipeline.py path/to/document.pdf
```

### Run A/B/C test
```bash
python test_abc_pdf_extraction.py
```

### Batch extraction (10 PDFs)
```bash
python batch_extract_10.py
```

## Dependencies

### Required
- pdfplumber (NEW - FREE PDF extraction)
- beautifulsoup4 (web scraping)
- markdownify (HTML to markdown)
- python-docx (DOCX extraction)
- requests (HTTP requests)
- pillow (image processing)
- python-dotenv (environment variables)

### Optional
- anthropic (for metadata enrichment only)

## Environment Variables

- `CLAUDE_API_KEY` - Optional (only for metadata enrichment)
- `OPENAI_API_KEY` - Required (for Weaviate embeddings)

---

**Version**: 2.0.0
**Status**: Production-ready
**RAG Score**: 98/100
