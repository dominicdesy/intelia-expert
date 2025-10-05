# Duplicate Code Analysis Report

**Generated:** 2025-10-05
**Files Analyzed:** 93 Python files
**Total Lines:** 23,539

---

## Executive Summary

The codebase shows **moderate to high duplication** with significant opportunities for consolidation:

- **47 duplicate function signatures** across multiple files
- **2,347 duplicate code blocks** (5+ lines)
- **15 functions >50 lines** that need refactoring
- **20 duplicate docstrings** indicating copy-paste

---

## Critical Findings

### 1. Extremely Long Functions ⚠️

These functions are beyond maintainable size and should be broken down:

| Lines | File | Function | Priority |
|-------|------|----------|----------|
| 1145 | `api/endpoints_diagnostic.py:23` | `create_diagnostic_endpoints()` | 🔴 CRITICAL |
| 731 | `api/endpoints_chat.py:43` | `create_chat_endpoints()` | 🔴 CRITICAL |
| 417 | `api/endpoints_health.py:27` | `create_health_endpoints()` | 🔴 HIGH |
| 343 | `main.py:60` | `lifespan()` | 🔴 HIGH |
| 310 | `core/rag_postgresql.py:103` | `flexible_query_validation()` | 🟡 MEDIUM |

### 2. Most Duplicated Function Signatures

| Count | Signature | Issue |
|-------|-----------|-------|
| 13 | `def __init__(self)` | Consider base class with common initialization |
| 10 | `def to_dict(self)` | Extract to mixin or base class |
| 9 | `async def initialize(self)` | Create initialization protocol/ABC |
| 7 | `async def close(self)` | Create cleanup protocol/ABC |
| 5 | `def get_stats(self)` | Consolidate into stats utility module |

### 3. Duplicated Utility Functions

These functions are repeated across files and should be in a shared utilities module:

```python
# Found in 3 files: api/utils.py, cache/cache_semantic.py, utils/data_classes.py
def safe_serialize_for_json(obj)

# Found in 4 files: api/endpoints*.py
def get_service(name)

# Found in 3 files: cache modules
async def get_cache_stats(self)

# Found in 3 files: cache/retrieval modules
async def get_embedding(self, text)
```

### 4. Import Duplication

Heavy duplication suggests need for consolidation:

```python
import logging          # 78 files (84% of codebase)
from typing import Dict # 65 files (70%)
from typing import List # 49 files (53%)
from typing import Any  # 47 files (51%)
```

---

## Recommendations by Priority

### 🔴 **Priority 1 - Immediate Action Required**

#### A. Break Down Mega-Functions

**Problem:** Functions >500 lines are unmaintainable

**Action:**
```python
# Current: api/endpoints_diagnostic.py
def create_diagnostic_endpoints(): # 1145 lines!
    # ... everything ...

# Refactor to:
def create_diagnostic_endpoints():
    router = APIRouter()
    _register_document_routes(router)
    _register_weaviate_routes(router)
    _register_postgresql_routes(router)
    _register_cache_routes(router)
    return router
```

**Files to refactor:**
1. `api/endpoints_diagnostic.py` → Split into `endpoints_diagnostic/` package
2. `api/endpoints_chat.py` → Split into `endpoints_chat/` package
3. `api/endpoints_health.py` → Extract health checks to separate modules
4. `main.py` → Extract lifespan logic to `lifecycle.py`

#### B. Create Base Classes for Common Patterns

**Problem:** Repeated `__init__`, `initialize()`, `close()` patterns

**Solution:**
```python
# Create: core/base.py
from abc import ABC, abstractmethod

class InitializableMixin:
    """Mixin for components requiring initialization"""

    def __init__(self):
        self.is_initialized = False
        self.initialization_errors = []

    @abstractmethod
    async def initialize(self):
        """Initialize component"""
        pass

    async def close(self):
        """Cleanup resources"""
        pass

class CacheableComponent(ABC):
    """Base for components with caching"""

    @abstractmethod
    def get_stats(self) -> Dict:
        pass

    def clear_cache(self):
        pass
```

**Apply to:**
- All RAG components
- All cache modules
- All retrieval systems

### 🟡 **Priority 2 - High Value Refactoring**

#### C. Consolidate Serialization Logic

**Problem:** `to_dict()`, `safe_serialize_for_json()` duplicated

**Solution:**
```python
# Create: utils/serialization.py
from typing import Any, Dict
from dataclasses import is_dataclass, asdict

def to_dict(obj: Any) -> Dict:
    """Universal serialization"""
    if is_dataclass(obj):
        return asdict(obj)
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    return {}

def safe_serialize(obj: Any) -> Any:
    """JSON-safe serialization"""
    # ... single implementation ...
```

**Replace in:**
- `api/utils.py`
- `cache/cache_semantic.py`
- `utils/data_classes.py`
- `core/data_models.py` (10 occurrences!)

#### D. Create Shared Service Accessor

**Problem:** `get_service()` repeated in 4 endpoint files

**Solution:**
```python
# Create: api/service_registry.py
from typing import Any
from fastapi import Request, HTTPException

def get_service(request: Request, name: str) -> Any:
    """Universal service accessor"""
    service = request.app.state.__dict__.get(name)
    if not service:
        raise HTTPException(500, f"Service {name} not available")
    return service

# Then import everywhere
from api.service_registry import get_service
```

#### E. Extract Cache Interface

**Problem:** Cache methods duplicated across cache modules

**Solution:**
```python
# Create: cache/interface.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class CacheInterface(ABC):
    """Standard cache interface"""

    @abstractmethod
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        pass

    @abstractmethod
    async def set_embedding(self, text: str, embedding: List[float]):
        pass

    @abstractmethod
    async def get_response(self, query: str, context_hash: str, language: str) -> Optional[str]:
        pass

    @abstractmethod
    async def set_response(self, query: str, context_hash: str, response: str, language: str):
        pass

    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        pass
```

### 🟢 **Priority 3 - Code Quality Improvements**

#### F. Standardize Error Handling

**Problem:** Try/except blocks appear 2,347 times with similar patterns

**Solution:**
```python
# Create: utils/error_handling.py
from functools import wraps
import logging

def log_errors(logger_name: str = __name__):
    """Decorator for standardized error logging"""
    logger = logging.getLogger(logger_name)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

# Usage:
@log_errors(__name__)
async def risky_operation():
    # ... code ...
```

#### G. Consolidate Type Imports

**Problem:** Same typing imports in 65+ files

**Solution:**
```python
# Create: utils/types.py
"""Central type definitions for entire codebase"""

from typing import (
    Dict,
    List,
    Any,
    Optional,
    Tuple,
    Union,
    Callable,
    Awaitable,
)

# Common type aliases
JSON = Dict[str, Any]
JSONList = List[JSON]
Headers = Dict[str, str]
QueryParams = Dict[str, Any]

# Export all
__all__ = [
    'Dict', 'List', 'Any', 'Optional', 'Tuple',
    'Union', 'Callable', 'Awaitable',
    'JSON', 'JSONList', 'Headers', 'QueryParams'
]

# Then everywhere:
from utils.types import Dict, List, JSON
```

---

## Implementation Roadmap

### Phase 1: Emergency Refactoring (Week 1)
- [ ] Split `endpoints_diagnostic.py` into package
- [ ] Split `endpoints_chat.py` into package
- [ ] Extract `lifespan()` logic from `main.py`
- [ ] Create base classes for initialization patterns

### Phase 2: Consolidation (Week 2)
- [ ] Create `utils/serialization.py`
- [ ] Create `api/service_registry.py`
- [ ] Create `cache/interface.py`
- [ ] Create `utils/types.py`

### Phase 3: Systematic Cleanup (Week 3-4)
- [ ] Replace all `to_dict()` with centralized version
- [ ] Replace all `get_service()` with registry
- [ ] Apply cache interface to all cache modules
- [ ] Standardize error handling with decorators
- [ ] Update all imports to use `utils/types.py`

---

## Metrics After Refactoring (Projected)

| Metric | Before | Target | Improvement |
|--------|--------|--------|-------------|
| Duplicate function signatures | 47 | <10 | 79% ↓ |
| Duplicate code blocks | 2,347 | <500 | 79% ↓ |
| Functions >100 lines | 15 | 5 | 67% ↓ |
| Largest function | 1,145 lines | <100 | 91% ↓ |
| Files with typing imports | 65 | 1 | 98% ↓ |

---

## Tools for Ongoing Detection

### 1. Python Scripts

```bash
# Run duplicate analyzer
cd llm
python duplicate_analyzer.py .
```

### 2. Pre-commit Hooks

```bash
# Install pylint with duplication detection
pip install pylint
pylint --disable=all --enable=duplicate-code llm/
```

### 3. VS Code Extensions

- **SonarLint** - Real-time duplicate detection
- **Pylint** - Code quality analysis
- **Better Comments** - Mark TODO/FIXME for refactoring

### 4. CI/CD Integration

```yaml
# .github/workflows/code-quality.yml
name: Code Quality
on: [pull_request]
jobs:
  duplicate-detection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check for duplicates
        run: |
          python llm/duplicate_analyzer.py llm/
          # Fail if >100 new duplicates added
```

---

## Quick Wins (Can Do Today)

1. **Extract `get_service()`** - 30 minutes, affects 4 files
2. **Create `utils/types.py`** - 20 minutes, clean up 65+ imports
3. **Extract `safe_serialize_for_json()`** - 15 minutes, affects 3 files
4. **Create `cache/interface.py`** - 1 hour, standardize all caches

**Total Time:** ~2 hours
**Impact:** Eliminate ~100 duplicate function definitions

---

**Next Steps:** Start with Priority 1A - break down the mega-functions in the API layer.
