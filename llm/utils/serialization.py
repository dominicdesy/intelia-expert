# -*- coding: utf-8 -*-
"""
Central serialization utilities for LLM codebase

Consolidates duplicate serialization logic found across:
- api/utils.py
- cache/cache_semantic.py
- utils/data_classes.py
- core/data_models.py (10 occurrences!)

Usage:
    from utils.serialization import to_dict, safe_serialize
"""

import logging
from utils.types import Any, Dict
from datetime import datetime
from decimal import Decimal
from dataclasses import is_dataclass, asdict
from collections import deque

logger = logging.getLogger(__name__)


def to_dict(obj: Any) -> Dict:
    """
    Universal object-to-dict serialization

    Handles:
    - Dataclasses (using asdict)
    - Objects with to_dict() method
    - Objects with __dict__ attribute
    - Primitives (returns empty dict)

    Args:
        obj: Object to convert

    Returns:
        Dictionary representation

    Example:
        >>> @dataclass
        >>> class Person:
        >>>     name: str
        >>>     age: int
        >>>
        >>> person = Person("Alice", 30)
        >>> to_dict(person)
        {'name': 'Alice', 'age': 30}
    """
    if obj is None:
        return {}

    # Dataclass support
    if is_dataclass(obj):
        return asdict(obj)

    # Custom to_dict() method
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()

    # __dict__ attribute
    if hasattr(obj, "__dict__"):
        return obj.__dict__

    # Primitives and unsupported types
    return {}


def safe_serialize(obj: Any) -> Any:
    """
    JSON-safe serialization with comprehensive type handling

    Handles:
    - Basic types (str, int, float, bool, None)
    - datetime → ISO format string
    - Decimal → float
    - bytes → UTF-8 string
    - dict → recursively serialized dict
    - list/tuple/set/deque → recursively serialized list
    - Objects with to_dict() → dict representation
    - Other types → string representation

    Args:
        obj: Object to serialize

    Returns:
        JSON-compatible representation

    Example:
        >>> from datetime import datetime
        >>> safe_serialize({
        ...     'name': 'Alice',
        ...     'created': datetime(2024, 1, 1),
        ...     'score': Decimal('99.5')
        ... })
        {'name': 'Alice', 'created': '2024-01-01T00:00:00', 'score': 99.5}
    """
    # None
    if obj is None:
        return None

    # Basic JSON-compatible types
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # datetime → ISO format
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Decimal → float
    if isinstance(obj, Decimal):
        return float(obj)

    # bytes → UTF-8 string
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except Exception:
            return str(obj)

    # dict → recursively serialize
    if isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}

    # list/tuple/set/deque → recursively serialize
    if isinstance(obj, (list, tuple, set, deque)):
        return [safe_serialize(item) for item in obj]

    # Objects with to_dict()
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return safe_serialize(obj.to_dict())
        except Exception as e:
            logger.warning(f"Failed to serialize with to_dict(): {e}")

    # Fallback: convert to string
    try:
        return str(obj)
    except Exception:
        return repr(obj)


# Alias for backward compatibility
safe_serialize_for_json = safe_serialize


__all__ = [
    "to_dict",
    "safe_serialize",
    "safe_serialize_for_json",
]
