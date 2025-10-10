# FAITHFULNESS ROOT CAUSE ANALYSIS - RAGAS Weaviate V2

## Executive Summary

**Faithfulness Score: 41.32%** (Should be >90%)

**ROOT CAUSE**: Language mismatch between question/context (English) and forced answer language (French)

## Detailed Analysis

### Problem Discovery

When analyzing Question 1 from the v2 dataset:

**Question (English):**
```
What is the scientific name for ascites in broiler chickens?
```

**Retrieved Context (English):**
```
The disease is more scientifically known as pulmonary hypertension syndrome
```

**LLM Answer (French):**
```
Le terme scientifique pour désigner l'ascite chez les poulets de chair est "hydropéritoine".
```

**Issues:**
1. ❌ Answer is in French, but question/context are in English
2. ❌ LLM invented term "hydropéritoine" (not in context)
3. ❌ Correct answer "Pulmonary hypertension syndrome" is in the context but not used
4. ❌ RAGAS Faithfulness correctly detects this as unfaithful to the retrieved contexts

### Root Cause Location

**File:** `llm/scripts/run_ragas_evaluation.py`
**Line:** 96

```python
result = await rag_engine.generate_response(
    query=question,
    language="fr",  # ← HARDCODED FRENCH FOR ALL QUESTIONS!
    conversation_id=f"ragas_eval_{datetime.now().timestamp()}",
)
```

### Impact on Faithfulness Scores

| Question | Language | Faithfulness | Issue |
|----------|----------|--------------|-------|
| Q1 | EN | 14.29% | Invented "hydropéritoine" instead of "pulmonary hypertension syndrome" |
| Q2 | EN | 57.14% | Added interpretation beyond contexts |
| Q3 | FR | 22.22% | Over-elaborated recommendations |
| Q4 | EN | 44.44% | Translation introduced imprecision |
| Q5 | EN | 55.56% | Mixed symptoms from different severity levels |
| Q6 | EN | 45.00% | Added context about CEO vaccines not explicitly stated |
| Q7 | EN | 22.22% | Generic transmission info vs specific 18-36h incubation |
| Q8 | EN | 42.11% | Added details about "high affinity" and mortality |
| Q9 | EN | 72.73% | Best score - stayed close to context |
| Q10 | FR | 37.50% | Translation of medical terms introduced errors |

**Average: 41.32%**

### Why This Matters

1. **Translation Errors**: LLM must translate English technical terms to French, creating opportunities for hallucination
2. **Lost Precision**: "Pulmonary hypertension syndrome" → "hydropéritoine" (incorrect medical term)
3. **Context Mismatch**: RAGAS compares French answer against English contexts
4. **False Failures**: System may work correctly but scores poorly due to language mismatch

## Solution

**Fix:** Detect language from question and pass correct language to RAG

```python
# Before (WRONG)
language="fr",  # Hardcoded!

# After (CORRECT)
from core.query_interpreter import detect_language
language = detect_language(question)
```

## Expected Impact

- **Faithfulness**: 41.32% → 80-90% (2x improvement)
- **Context Precision**: 100% (already perfect) ✓
- **Context Recall**: 96.67% (already excellent) ✓
- **Overall Score**: 82.36% → 90%+ (professional-grade)

## Next Steps

1. ✅ Document root cause (this file)
2. Fix language detection in run_ragas_evaluation.py
3. Re-run RAGAS v2 evaluation with correct language
4. Verify Faithfulness improvements

---

**Created:** 2025-01-XX
**Status:** ROOT CAUSE IDENTIFIED
**Priority:** HIGH (blocks accurate RAGAS evaluation)
