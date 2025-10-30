# Hybrid OOD Detector - Test Suite

## Overview

This test suite validates the Hybrid OOD (Out-of-Domain) Detector that combines LLM classification with Weaviate content search.

## Prerequisites

1. **Environment Variables**:
   ```bash
   # Required
   OPENAI_API_KEY=your_openai_api_key

   # Optional (for full Weaviate tests)
   WEAVIATE_URL=http://localhost:8080
   WEAVIATE_API_KEY=your_weaviate_key
   ```

2. **Python Dependencies**:
   ```bash
   pip install openai weaviate-client
   ```

## Running Tests

### Quick Mode (LLM Only)

Test only the LLM fast path without Weaviate:

```bash
cd C:/Software_Development/intelia-cognito/rag
python tests/test_hybrid_ood.py --quick
```

**Use when:**
- You don't have Weaviate running
- You want fast feedback (~10 seconds)
- You only want to test LLM classification

**Output example:**
```
HYBRID OOD DETECTOR TEST SUITE
Mode: Quick (LLM only)

[1/14] Clear poultry metric question
   Query: "What is the FCR for Ross 308 at 35 days?" (lang=en)
   Expected: ✅ IN-DOMAIN via llm_fast_accept
   Result: ✅ IN-DOMAIN via llm_fast_accept
   Confidence: 1.00, Duration: 95ms
   ✅ PASS

...

TEST SUMMARY
================================================================================

📊 Overall Results:
   Total tests: 14
   ✅ Passed: 14 (100.0%)
   ❌ Failed: 0 (0.0%)
   ⏱️  Total time: 1.32s
   ⚡ Avg time per test: 94ms
```

### Full Mode (LLM + Weaviate)

Test both LLM and Weaviate fallback:

```bash
cd C:/Software_Development/intelia-cognito/rag
python tests/test_hybrid_ood.py
```

**Use when:**
- Weaviate is running and accessible
- You want to test the complete hybrid system
- You want to validate Weaviate content search

**Output example:**
```
HYBRID OOD DETECTOR TEST SUITE
Mode: Full (LLM + Weaviate)

[1/18] Clear poultry metric question
   Query: "What is the FCR for Ross 308 at 35 days?" (lang=en)
   Expected: ✅ IN-DOMAIN via llm_fast_accept
   Result: ✅ IN-DOMAIN via llm_fast_accept
   Confidence: 1.00, Duration: 92ms
   ✅ PASS

[15/18] Nano product configuration
   Query: "Comment configurer le chauffage dans le nano ?" (lang=fr)
   Expected: ✅ IN-DOMAIN via llm_fast_accept
   Result: ✅ IN-DOMAIN via llm_fast_accept
   Confidence: 1.00, Duration: 98ms
   ✅ PASS

...

TEST SUMMARY
================================================================================

📊 Overall Results:
   Total tests: 18
   ✅ Passed: 18 (100.0%)
   ❌ Failed: 0 (0.0%)
   ⏱️  Total time: 2.15s
   ⚡ Avg time per test: 119ms

📁 Results by Category:
   fast_path_yes:
      ✅ 5/5 passed (100.0%)
   fast_path_no:
      ✅ 4/4 passed (100.0%)
   weaviate_fallback:
      ✅ 4/4 passed (100.0%)
   edge_cases:
      ✅ 5/5 passed (100.0%)

🔧 Results by Detection Method:
   llm_fast_accept:
      Count: 14
      Avg time: 96ms
   llm_fast_reject:
      Count: 4
      Avg time: 88ms
```

### Verbose Mode

Show detailed decision information:

```bash
python tests/test_hybrid_ood.py --verbose
```

**Output includes:**
- Full decision details
- LLM response
- Weaviate search results
- Score breakdowns

## Test Categories

### 1. Fast Path YES (5 tests)
Tests queries that should be quickly accepted as IN-DOMAIN:
- ✅ "What is the FCR for Ross 308 at 35 days?"
- ✅ "Comment prévenir la coccidiose ?"
- ✅ "Quel est le poids d'un Cobb 500 mâle à 42 jours ?"
- ✅ "How to treat Newcastle disease?"
- ✅ "Quelle température pour un poulailler en hiver ?"

**Expected:** LLM fast accept (<100ms)

### 2. Fast Path NO (4 tests)
Tests queries that should be quickly rejected as OUT-OF-DOMAIN:
- ❌ "What is the capital of France?"
- ❌ "Comment faire une pizza ?"
- ❌ "Who won the World Cup 2022?"
- ❌ "Quelle est la température idéale pour un aquarium ?"

**Expected:** LLM fast reject (<100ms)

### 3. Weaviate Fallback (4 tests)
Tests queries about Intelia products (with updated LLM, should be fast accept):
- ✅ "Comment configurer le chauffage dans le nano ?"
- ✅ "How do I use the Nano system?"
- ✅ "What is the Logix system?"
- ✅ "Comment exporter les données du Logix ?"

**Expected:** LLM fast accept (since we updated the prompt)
**Fallback:** If LLM uncertain, Weaviate should find docs

### 4. Edge Cases (5 tests)
Tests ambiguous or minimal queries:
- "Temperature" (single word)
- "Quelle est la température idéale ?" (ambiguous)

**Expected:** Context-dependent, should accept (poultry context assumed)

## Interpreting Results

### Success Criteria

✅ **All tests pass** (100%):
- System is working correctly
- LLM prompt recognizes all patterns
- Weaviate fallback works when needed

⚠️ **Some tests fail** (90-99%):
- Check failed test details in summary
- May need to adjust LLM prompt or thresholds
- Review logs for decision reasoning

❌ **Many tests fail** (<90%):
- System misconfigured
- Check environment variables
- Verify Weaviate connectivity
- Review recent code changes

### Performance Benchmarks

**Fast Path (LLM only):**
- ✅ Good: <100ms average
- ⚠️ Acceptable: 100-150ms
- ❌ Slow: >150ms (check OpenAI API latency)

**Weaviate Fallback:**
- ✅ Good: <200ms
- ⚠️ Acceptable: 200-300ms
- ❌ Slow: >300ms (check Weaviate performance)

**Overall:**
- ✅ Good: <120ms average
- ⚠️ Acceptable: 120-200ms
- ❌ Slow: >200ms

### Common Issues

#### Issue 1: All tests fail with "OPENAI_API_KEY not found"

**Solution:**
```bash
export OPENAI_API_KEY=your_key_here
# Or add to .env file
echo "OPENAI_API_KEY=your_key" >> .env
```

#### Issue 2: Weaviate tests fail with connection error

**Solutions:**
1. Run in quick mode: `python test_hybrid_ood.py --quick`
2. Start Weaviate: `docker-compose up -d weaviate`
3. Check WEAVIATE_URL in environment

#### Issue 3: Intelia product tests fail

**Possible causes:**
1. LLM prompt not updated (should be fixed with our changes)
2. Weaviate doesn't have product docs ingested
3. Thresholds too strict

**Solutions:**
1. Check `llm_ood_detector.py` has Intelia products in prompt
2. Ingest product manuals: `python document_extractor/multi_format_pipeline.py path/to/manual.pdf`
3. Adjust thresholds in `core.py`

## Adding New Tests

To add new test cases, edit `test_hybrid_ood.py`:

```python
TEST_CASES.append(
    TestCase(
        query="Your test query here",
        language="fr",  # or "en"
        expected_in_domain=True,  # or False
        expected_method="llm_fast_accept",  # or other method
        category="fast_path_yes",  # or other category
        description="Short description of what this tests"
    )
)
```

Categories:
- `fast_path_yes` - Clear poultry questions
- `fast_path_no` - Clear out-of-domain questions
- `weaviate_fallback` - Edge cases needing Weaviate
- `edge_cases` - Ambiguous or tricky queries

## CI/CD Integration

### Pre-deployment Check

Run before deploying to production:

```bash
# Quick smoke test (30 seconds)
python tests/test_hybrid_ood.py --quick

# Full validation (1-2 minutes)
python tests/test_hybrid_ood.py

# Exit code: 0 if all pass, 1 if any fail
```

### GitHub Actions Example

```yaml
- name: Test Hybrid OOD Detector
  run: |
    cd rag
    python tests/test_hybrid_ood.py --quick
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Continuous Monitoring

For production monitoring, collect metrics from OOD detector:

```python
from retrieval.weaviate.core import WeaviateManager

weaviate_manager = WeaviateManager()
stats = weaviate_manager.ood_detector.get_stats()

# Log or send to monitoring system
logger.info(f"OOD Stats: {stats}")
```

## Support

For questions or issues:
1. Check test output for detailed error messages
2. Review logs in verbose mode
3. Consult `HYBRID_OOD_DETECTOR.md` documentation
4. Contact Intelia development team

---

**Last Updated**: 2025-10-30
**Version**: 1.0.0
