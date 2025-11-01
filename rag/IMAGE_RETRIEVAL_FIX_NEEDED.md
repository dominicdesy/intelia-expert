# Image Retrieval - Fix Required

## Problem Identified

**Images are NOT being retrieved in RAG responses** even though:
- ✅ 310 images are correctly stored in Weaviate `InteliaImages` collection
- ✅ ImageRetriever code is correct
- ✅ Integration in `response_generator.py` is correct
- ✅ Direct tests with fake documents work perfectly

## Root Cause

The `source_file` field is **NOT being copied** from Weaviate objects to the `context_docs` dictionaries.

### Technical Details

When Weaviate returns document objects, they are converted to dictionaries in `retrieval/hybrid_retriever.py` at lines 200-213, 250-263, and 319-343.

**Current code** (lines 200-213):
```python
doc = {
    "content": obj.properties.get("content", ""),
    "metadata": {
        "title": obj.properties.get("title", ""),
        "source": obj.properties.get("source", ""),
        "geneticLine": obj.properties.get("geneticLine", ""),
        "species": obj.properties.get("species", ""),
        "phase": obj.properties.get("phase", ""),
        "age_band": obj.properties.get("age_band", ""),
        "search_type": "vector_only",
    },
    ...
}
```

**Missing**: `source_file` is never copied from `obj.properties`!

### How ImageRetriever Works

The `ImageRetriever.get_images_for_chunks()` method (line 71 in `image_retriever.py`) looks for `source_file` in chunks:

```python
source_file = chunk.get("source_file") or chunk.get("metadata", {}).get("source_file")
```

Since `source_file` is not in the chunk dict or in metadata, **no source files are found**, so **no images are retrieved**.

## Solution

Add `source_file` to the metadata dictionary in 3 locations in `retrieval/hybrid_retriever.py`:

### Location 1: Vector-only search (around line 200)
```python
doc = {
    "content": obj.properties.get("content", ""),
    "metadata": {
        "title": obj.properties.get("title", ""),
        "source": obj.properties.get("source", ""),
        "source_file": obj.properties.get("source_file", ""),  # ADD THIS LINE
        "geneticLine": obj.properties.get("geneticLine", ""),
        "species": obj.properties.get("species", ""),
        "phase": obj.properties.get("phase", ""),
        "age_band": obj.properties.get("age_band", ""),
        "search_type": "vector_only",
    },
    ...
}
```

### Location 2: BM25-only search (around line 250)
```python
doc = {
    "content": obj.properties.get("content", ""),
    "metadata": {
        "title": obj.properties.get("title", ""),
        "source": obj.properties.get("source", ""),
        "source_file": obj.properties.get("source_file", ""),  # ADD THIS LINE
        "geneticLine": obj.properties.get("geneticLine", ""),
        "species": obj.properties.get("species", ""),
        "phase": obj.properties.get("phase", ""),
        "age_band": obj.properties.get("age_band", ""),
        "search_type": "bm25_only",
    },
    ...
}
```

### Location 3: Hybrid search (around line 319)
```python
doc = {
    "content": obj.properties.get("content", ""),
    "metadata": {
        "title": obj.properties.get("title", ""),
        "source": obj.properties.get("source", ""),
        "source_file": obj.properties.get("source_file", ""),  # ADD THIS LINE
        "geneticLine": obj.properties.get("geneticLine", ""),
        "species": obj.properties.get("species", ""),
        "phase": obj.properties.get("phase", ""),
        "age_band": obj.properties.get("age_band", ""),
        "hybrid_used": True,
        "alpha": alpha,
        "explain_score": explain_score,
    },
    ...
}
```

## Testing After Fix

Once the fix is applied, run:

```bash
cd C:/Software_Development/intelia-cognito/rag
python final_image_test.py
```

Expected output:
- Test 1: Should find 3+ images from Nano manual
- Test 2: Should find 3+ images from Nano manual

## Evidence

### Test Results Before Fix

```
[Test 2/2]
Query: Comment installer le systeme Nano pour volailles?
Results:
  Context docs: 97
  Images: 0  ❌
  [INFO] No images found
```

### Debug Output

```
First doc:
  Type: <class 'dict'>
  Keys: ['content', 'metadata']
  [ERROR] source_file NOT in metadata
  metadata keys: ['source', 'title', 'authors', 'year', 'citations', 'url']
```

### Direct Test (Confirms ImageRetriever Works)

```python
# From debug_image_matching.py
fake_chunks = [{
    "source_file": "C:\\Software_Development\\...\\Nano EN.docx",
    "content": "Test content"
}]

images_found = image_retriever.get_images_for_chunks(fake_chunks)
# Result: 3 images found ✅
```

This proves the ImageRetriever is functional - it just needs `source_file` in the chunks.

## Files to Modify

1. `retrieval/hybrid_retriever.py` - Add `source_file` to metadata (3 locations)

## Files Already Modified (Working Correctly)

1. ✅ `core/data_models.py` - RAGResult has `images` field
2. ✅ `core/response_generator.py` - Image retrieval integration
3. ✅ `core/rag_engine.py` - Passes weaviate_client
4. ✅ `retrieval/image_retriever.py` - Image retrieval logic
5. ✅ `retrieval/weaviate/core.py` - gRPC timeout fixed

## Summary

This is a **simple one-line fix** repeated in 3 locations. Once `source_file` is added to the metadata dict, image retrieval will work end-to-end.
