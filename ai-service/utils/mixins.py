# -*- coding: utf-8 -*-
"""
Mixins for common serialization patterns
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Mixins for common serialization patterns

Provides standardized serialization for dataclasses and custom objects,
eliminating duplicate to_dict() implementations across the codebase.

Usage:
    from utils.mixins import SerializableMixin
    from dataclasses import dataclass

    @dataclass
    class MyResult(SerializableMixin):
        status: str
        value: int

    result = MyResult("success", 42)
    result.to_dict()  # {'status': 'success', 'value': 42}
"""

import logging
from dataclasses import is_dataclass, fields
from enum import Enum
from utils.types import Dict, Any
from utils.serialization import safe_serialize

logger = logging.getLogger(__name__)


class SerializableMixin:
    """
    Mixin providing standardized to_dict() serialization

    Works with:
    - Dataclasses (uses asdict with custom value_serializer)
    - Regular classes (uses __dict__)
    - Handles Enums, nested objects, and complex types

    Example:
        >>> from dataclasses import dataclass
        >>> from enum import Enum
        >>>
        >>> class Status(Enum):
        >>>     SUCCESS = "success"
        >>>
        >>> @dataclass
        >>> class Result(SerializableMixin):
        >>>     status: Status
        >>>     value: int
        >>>
        >>> result = Result(Status.SUCCESS, 42)
        >>> result.to_dict()
        {'status': 'success', 'value': 42}
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert object to dictionary with proper serialization

        Returns:
            Dictionary representation with all values JSON-serializable
        """
        if is_dataclass(self):
            try:
                # Manual extraction with proper Enum handling
                result = {}
                for field in fields(self):
                    value = getattr(self, field.name)

                    # Handle Enums - extract .value
                    if isinstance(value, Enum):
                        result[field.name] = value.value
                    # Handle nested SerializableMixin objects
                    elif hasattr(value, "to_dict") and callable(value.to_dict):
                        result[field.name] = value.to_dict()
                    # Use safe_serialize for other types
                    else:
                        result[field.name] = safe_serialize(value)

                return result
            except Exception as e:
                logger.warning(
                    f"Failed to serialize dataclass {type(self).__name__}: {e}"
                )
                return self._manual_serialize()
        else:
            # For non-dataclass objects, use __dict__ with safe_serialize
            try:
                return safe_serialize(self.__dict__)
            except Exception as e:
                logger.warning(f"Failed to serialize {type(self).__name__}: {e}")
                return {}

    def _manual_serialize(self) -> Dict[str, Any]:
        """
        Manual serialization fallback for complex dataclasses

        Handles edge cases where asdict() fails
        """
        result = {}

        if is_dataclass(self):
            for field in fields(self):
                value = getattr(self, field.name)
                result[field.name] = safe_serialize(value)
        else:
            result = safe_serialize(self.__dict__)

        return result


class AutoSerializableMixin(SerializableMixin):
    """
    Enhanced serializable mixin with exclude fields support

    Example:
        >>> @dataclass
        >>> class Result(AutoSerializableMixin):
        >>>     value: int
        >>>     _internal: str  # Will be excluded (starts with _)
        >>>
        >>>     _exclude_fields = {'_internal'}  # Explicit exclusion
    """

    _exclude_fields = set()  # Fields to exclude from serialization

    def to_dict(self, exclude_private=True) -> Dict[str, Any]:
        """
        Convert to dict with optional filtering

        Args:
            exclude_private: If True, exclude fields starting with _

        Returns:
            Filtered dictionary representation
        """
        data = super().to_dict()

        # Filter excluded fields
        if self._exclude_fields:
            data = {k: v for k, v in data.items() if k not in self._exclude_fields}

        # Filter private fields
        if exclude_private:
            data = {k: v for k, v in data.items() if not k.startswith("_")}

        return data


class DataclassSerializableMixin(SerializableMixin):
    """
    Serializable mixin that ONLY includes dataclass fields

    Use this when you want automatic serialization but don't want
    to include computed properties or methods.

    Example:
        >>> @dataclass
        >>> class Result(DataclassSerializableMixin):
        >>>     value: int
        >>>
        >>>     @property
        >>>     def doubled(self):
        >>>         return self.value * 2
        >>>
        >>> result = Result(42)
        >>> result.to_dict()  # {'value': 42} - 'doubled' not included
    """

    pass  # Uses parent implementation which only processes dataclass fields


__all__ = [
    "SerializableMixin",
    "AutoSerializableMixin",
    "DataclassSerializableMixin",
]
