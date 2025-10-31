# Deployment Guide - Multi-Format Knowledge Extraction Pipeline

## Deployment Architecture

### Local Extraction → Cloud Storage

```
┌─────────────────────────────────────────────────────────────┐
│                   LOCAL MACHINE (Windows)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Knowledge Extraction Pipeline                         │ │
│  │                                                         │ │
│  │  - PDF Vision Extractor (Claude API)                   │ │
│  │  - DOCX Extractor                                      │ │
│  │  - Web Scraper                                         │ │
│  │  - Path-based Classifier                               │ │
│  │  - Metadata Enricher (Claude API)                      │ │
│  │  - Text Chunker                                        │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │                                    │
│                         │ HTTPS                              │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Local Document Storage                                │ │
│  │  C:/Software_Development/intelia-cognito/              │ │
│  │    knowledge-ingesters/Sources/                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS (Weaviate Client)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CLOUD - DigitalOcean                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Weaviate Vector Database                              │ │
│  │  https://intelia-expert-rag-9rhqrfcv.weaviate.network │ │
│  │                                                         │ │
│  │  Collection: KnowledgeChunks                           │ │
│  │  - Documents ingested from local machine               │ │
│  │  - Accessible by all applications                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  LLM Application (FastAPI)                             │ │
│  │  - Queries Weaviate for RAG                            │ │
│  │  - Serves client applications                          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Why Local Processing?

### Advantages

1. **Document Security**
   - Documents stay on local machine during processing
   - No need to upload sensitive PDFs to cloud storage
   - Full control over source documents

2. **Cost Optimization**
   - No cloud compute costs for extraction
   - Only pay for Weaviate storage and Claude API calls
   - Local processing is "free" (your machine)

3. **Development & Testing**
   - Easy to debug and iterate
   - Fast feedback loop
   - No deployment pipeline for changes

4. **Flexibility**
   - Process documents on-demand
   - No scheduling constraints
   - Can pause/resume processing

### Trade-offs

1. **Manual Execution**
   - Requires running script manually
   - Not automated (unless scheduled locally)
   - Machine must be on during processing

2. **Network Dependency**
   - Requires internet for:
     - Claude API calls
     - Weaviate ingestion
   - Local network speed affects performance

3. **Single-Machine Limit**
   - Can't distribute processing across machines
   - Limited by local machine resources
   - No automatic retry on machine restart

---

## Local Machine Setup

### Prerequisites

**Operating System**: Windows 10/11

**Python**: 3.11+ (already installed)

**Network**: Internet connection for API calls

### Installation Steps

#### 1. Navigate to Project Directory
```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\knowledge_extractor
```

#### 2. Install Dependencies
```bash
pip install -r requirements_multi_format.txt
```

Dependencies installed:
- `anthropic` - Claude API
- `PyMuPDF` - PDF processing
- `python-docx` - DOCX extraction
- `beautifulsoup4` - Web scraping
- `markdownify` - HTML to markdown
- `weaviate-client` - Weaviate connection
- `python-dotenv` - Environment variables

#### 3. Configure Environment Variables

Create/update `.env` file in project root:

**Location**: `C:\Software_Development\intelia-cognito\.env`

```bash
# Claude API (for Vision extraction and metadata enrichment)
CLAUDE_API_KEY=sk-ant-...

# OpenAI API (for embeddings in Weaviate)
OPENAI_API_KEY=sk-...

# Weaviate Cloud (DigitalOcean)
WEAVIATE_URL=https://intelia-expert-rag-9rhqrfcv.weaviate.network
WEAVIATE_API_KEY=...
```

#### 4. Verify Installation

Test with pilot document:
```bash
python multi_format_pipeline.py ^
  "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/public/veterinary_services/common/ascites.pdf" ^
  2
```

Expected output:
```
✓ Content extracted: 6224 characters
✓ Path classification: intelia / public_global / veterinary_services
✓ Metadata enrichment: 71% confidence
✓ Created 2 chunks
✓ SUCCESS
```

---

## Processing Workflow

### Option 1: Single Document Processing

Process one document at a time:

```bash
# PDF
python multi_format_pipeline.py path/to/document.pdf

# DOCX
python multi_format_pipeline.py path/to/document.docx

# Web page
python multi_format_pipeline.py https://example.com/article
```

### Option 2: Batch Processing

Process multiple documents:

```python
# batch_process.py
from multi_format_pipeline import MultiFormatPipeline
from pathlib import Path

pipeline = MultiFormatPipeline()

# Get all PDFs in veterinary_services
docs_dir = Path("C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/public/veterinary_services/common")

for pdf_file in docs_dir.glob("*.pdf"):
    print(f"\nProcessing: {pdf_file.name}")
    result = pipeline.process_file(str(pdf_file))

    if result.success:
        print(f"  ✓ {result.chunks_created} chunks created")
    else:
        print(f"  ✗ Error: {result.error}")
```

Run:
```bash
python batch_process.py
```

### Option 3: Directory Processing (Recommended)

Process entire directory structure:

```python
# process_all.py
from multi_format_pipeline import MultiFormatPipeline
from pathlib import Path
import time

pipeline = MultiFormatPipeline()
base_dir = Path("C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/public")

total_processed = 0
total_failed = 0

for pdf_file in base_dir.rglob("*.pdf"):
    print(f"\n[{total_processed + 1}] Processing: {pdf_file.relative_to(base_dir)}")

    result = pipeline.process_file(str(pdf_file))

    if result.success:
        print(f"  ✓ {result.chunks_created} chunks | Confidence: {result.metadata_summary['overall_confidence']:.2%}")
        total_processed += 1
    else:
        print(f"  ✗ Error: {result.error}")
        total_failed += 1

    # Rate limiting: pause between documents
    time.sleep(2)

print(f"\n{'='*80}")
print(f"BATCH PROCESSING COMPLETE")
print(f"{'='*80}")
print(f"Total Processed: {total_processed}")
print(f"Total Failed: {total_failed}")
print(f"Success Rate: {total_processed/(total_processed+total_failed)*100:.1f}%")
```

---

## Network Configuration

### Firewall Rules

Allow outbound connections to:

1. **Claude API**
   - `https://api.anthropic.com`
   - Port: 443 (HTTPS)

2. **Weaviate Cloud**
   - `https://intelia-expert-rag-9rhqrfcv.weaviate.network`
   - Port: 443 (HTTPS)

3. **OpenAI API** (for embeddings via Weaviate)
   - `https://api.openai.com`
   - Port: 443 (HTTPS)

### Proxy Configuration

If behind corporate proxy, set environment variables:

```bash
set HTTP_PROXY=http://proxy.company.com:8080
set HTTPS_PROXY=http://proxy.company.com:8080
```

---

## Monitoring & Logging

### Console Output

Pipeline provides real-time console output:

```
Initializing Multi-Format Knowledge Extraction Pipeline...
Loaded path rules for: intelia
Pipeline initialized successfully

================================================================================
PROCESSING: veterinary_services/common/ascites.pdf
================================================================================

Processing 2/3 pages from ascites.pdf
  Processing page 1/2...
  Processing page 2/2...
OK Content extracted: 6224 characters
  Method: pdf_vision

Step 2: Path-based classification...
OK Path classification complete
  Org: intelia
  Site: veterinary_services
  Breed: None
  Confidence: 1.00

Step 3: Metadata enrichment...
Enriching metadata...
OK Metadata enrichment complete
  Species: chicken
  Genetic Line: unknown
  Document Type: technical_note
  Overall Confidence: 0.71

Step 4: Text chunking (600 words, 120 overlap)...
OK Created 2 chunks

Step 5: Preparing chunks for ingestion...
OK 2 chunks ready for Weaviate

================================================================================
PIPELINE RESULT
================================================================================
SUCCESS
```

### Log Files

Create log file for batch processing:

```python
import logging

logging.basicConfig(
    filename='extraction.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Progress Tracking

For large batches, track progress in CSV:

```python
import csv
from datetime import datetime

with open('processing_log.csv', 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        datetime.now(),
        file_path,
        result.success,
        result.chunks_created,
        result.metadata_summary.get('overall_confidence', 0)
    ])
```

---

## Cost Estimation

### Claude API Costs (per document)

**Model**: claude-3-opus-20240229

| Document Type | Pages | Vision Calls | Enrichment Calls | Total Cost |
|---------------|-------|--------------|------------------|------------|
| Simple PDF | 2 | 2 | 1 | ~$0.03 |
| Medium PDF | 10 | 10 | 1 | ~$0.15 |
| Complex PDF | 50 | 50 | 1 | ~$0.75 |
| DOCX | N/A | 0 | 1 | ~$0.01 |

**Pricing** (as of Oct 2025):
- Input: $15 per 1M tokens
- Output: $75 per 1M tokens
- Average page: ~2000 tokens input, ~500 tokens output

### Batch Processing Costs

**54 PDFs in library**:
- Estimated total pages: ~500
- Estimated cost: ~$7.50

**500 PDFs (future)**:
- Estimated total pages: ~5000
- Estimated cost: ~$75

### Weaviate Storage Costs

**DigitalOcean Weaviate**:
- Included in existing Weaviate plan
- ~1-2 MB per 1000 chunks
- 54 PDFs × 10 chunks avg = 540 chunks = ~1 MB

**No additional cost** for current document volume.

---

## Scheduling & Automation

### Option 1: Windows Task Scheduler

Create scheduled task to run extraction:

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 2 AM
4. Action: Start a program
   - Program: `C:\Python311\python.exe`
   - Arguments: `C:\Software_Development\intelia-cognito\knowledge-ingesters\knowledge_extractor\process_all.py`
   - Start in: `C:\Software_Development\intelia-cognito\knowledge-ingesters\knowledge_extractor`

### Option 2: Manual Execution

Run on-demand when new documents are added:

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\knowledge_extractor
python process_all.py
```

### Option 3: Watch Folder (Future)

Monitor directory for new files and process automatically:

```python
# watch_and_process.py (future implementation)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DocumentHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.pdf'):
            process_document(event.src_path)

observer = Observer()
observer.schedule(DocumentHandler(), path=watch_dir, recursive=True)
observer.start()
```

---

## Backup & Recovery

### Document Backup

Source documents are already backed up:
- **Location**: `C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/`
- **Recommendation**: Regular backups to external drive or cloud storage

### Processing State

For batch processing, implement checkpoint system:

```python
# Save checkpoint
import json

checkpoint = {
    "last_processed": str(last_file),
    "total_processed": total_processed,
    "timestamp": datetime.now().isoformat()
}

with open('checkpoint.json', 'w') as f:
    json.dump(checkpoint, f)

# Resume from checkpoint
try:
    with open('checkpoint.json', 'r') as f:
        checkpoint = json.load(f)
        last_processed = Path(checkpoint['last_processed'])
except FileNotFoundError:
    last_processed = None
```

---

## Troubleshooting

### Common Issues

#### 1. Claude API Key Not Found
```
Error: CLAUDE_API_KEY not found in environment
```

**Solution**: Check `.env` file exists and contains `CLAUDE_API_KEY=...`

#### 2. Weaviate Connection Failed
```
Error: Could not connect to Weaviate
```

**Solution**:
- Check internet connection
- Verify `WEAVIATE_URL` and `WEAVIATE_API_KEY` in `.env`
- Test connection: `ping intelia-expert-rag-9rhqrfcv.weaviate.network`

#### 3. PDF Extraction Failed
```
Error: PyMuPDF not installed
```

**Solution**: `pip install PyMuPDF`

#### 4. Rate Limiting
```
Error: 429 Too Many Requests
```

**Solution**: Add delays between documents in batch processing:
```python
import time
time.sleep(2)  # 2 seconds between documents
```

### Performance Issues

#### Slow Processing

**Cause**: Network latency to Claude API

**Solutions**:
- Process during off-peak hours
- Use wired connection instead of WiFi
- Close bandwidth-heavy applications

#### Memory Usage

**Cause**: Large PDFs with many pages

**Solutions**:
- Process in smaller batches
- Limit max pages per document
- Close other applications

---

## Security Considerations

### Local Machine Security

1. **API Keys**: Never commit `.env` to git
2. **Document Access**: Restrict access to `Sources/` directory
3. **Network**: Use secure WiFi or wired connection
4. **Logs**: Don't log sensitive document content

### Weaviate Security

1. **API Key Rotation**: Rotate Weaviate API key periodically
2. **Access Control**: Use visibility_level metadata for filtering
3. **Audit Logs**: Track who accesses what data

---

## Future Migration to Cloud

If needed, extraction can be migrated to cloud:

### Option 1: DigitalOcean Droplet

Deploy extraction pipeline on same network as Weaviate:

```
DigitalOcean Droplet (extraction) → Weaviate (same network)
                ↑
        Upload documents (one-time)
```

**Benefits**: Lower latency, automated scheduling, always on

### Option 2: AWS Lambda / Azure Functions

Serverless extraction triggered by S3/Blob upload:

```
Upload document → S3 → Lambda → Extract → Weaviate
```

**Benefits**: Auto-scaling, pay-per-use, no server management

---

## Conclusion

**Current Setup**: Local extraction on Windows → Cloud Weaviate on DigitalOcean

**Advantages**:
- ✅ Document security (local)
- ✅ Cost optimization (no cloud compute)
- ✅ Easy development & testing
- ✅ Full control over processing

**Next Steps**:
1. Process all 54 PDFs in library
2. Set up batch processing script
3. Configure scheduled execution (optional)
4. Monitor costs and performance

**Status**: ✅ Ready for production batch processing
