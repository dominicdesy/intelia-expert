# -*- coding: utf-8 -*-
"""
Base classes and mixins for common patterns

Consolidates repeated initialization and cleanup patterns found across:
- All RAG components (13 occurrences of __init__)
- All cache modules (10 occurrences of to_dict)
- All retrieval systems (9 occurrences of async def initialize)
- Multiple handlers (7 occurrences of async def close)

Usage:
    from core.base import InitializableMixin, CacheableComponent, StatefulComponent

    class MyRAGComponent(InitializableMixin):
        async def initialize(self):
            # Your initialization logic
            await super().initialize()

    class MyCache(CacheableComponent):
        def get_stats(self):
            # Your stats logic
            return {...}
"""

import logging
from abc import ABC, abstractmethod
from utils.types import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class InitializableMixin:
    """
    Mixin for components requiring initialization

    Provides:
    - Initialization state tracking
    - Error tracking during initialization
    - Standardized initialize/close lifecycle

    Example:
        >>> class MyComponent(InitializableMixin):
        >>>     async def initialize(self):
        >>>         # Your initialization
        >>>         self.db = await connect_db()
        >>>         await super().initialize()  # Mark as initialized
        >>>
        >>>     async def close(self):
        >>>         await self.db.close()
        >>>         await super().close()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_initialized = False
        self.initialization_errors: List[str] = []
        self.initialization_time: Optional[datetime] = None

    async def initialize(self):
        """
        Mark component as initialized

        Override this in subclasses and call super().initialize()
        at the end of your initialization logic.
        """
        self.is_initialized = True
        self.initialization_time = datetime.now()
        logger.info(f"{self.__class__.__name__} initialized successfully")

    async def close(self):
        """
        Cleanup resources

        Override this in subclasses to add cleanup logic.
        Call super().close() at the end.
        """
        self.is_initialized = False
        logger.info(f"{self.__class__.__name__} closed")

    def add_initialization_error(self, error: str):
        """Record an initialization error"""
        self.initialization_errors.append(error)
        logger.warning(f"Initialization error in {self.__class__.__name__}: {error}")

    def get_initialization_status(self) -> Dict[str, Any]:
        """Get initialization status"""
        return {
            "initialized": self.is_initialized,
            "errors": self.initialization_errors,
            "initialization_time": (
                self.initialization_time.isoformat()
                if self.initialization_time
                else None
            ),
        }


class CacheableComponent(ABC):
    """
    Base class for components with caching capabilities

    Provides:
    - Standard stats interface
    - Cache clearing
    - Cache configuration

    Example:
        >>> class MyCache(CacheableComponent):
        >>>     def get_stats(self) -> Dict:
        >>>         return {
        >>>             'hits': self.hits,
        >>>             'misses': self.misses,
        >>>             'hit_rate': self.hits / (self.hits + self.misses)
        >>>         }
        >>>
        >>>     def clear_cache(self):
        >>>         self.cache.clear()
        >>>         super().clear_cache()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_enabled = True

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        pass

    def clear_cache(self):
        """
        Clear cache

        Override in subclasses to implement cache clearing.
        """
        logger.info(f"Cache cleared for {self.__class__.__name__}")

    def enable_cache(self):
        """Enable caching"""
        self.cache_enabled = True
        logger.info(f"Cache enabled for {self.__class__.__name__}")

    def disable_cache(self):
        """Disable caching"""
        self.cache_enabled = False
        logger.info(f"Cache disabled for {self.__class__.__name__}")


class StatefulComponent(InitializableMixin):
    """
    Component with state tracking and statistics

    Combines initialization with state and statistics tracking.

    Example:
        >>> class MyEngine(StatefulComponent):
        >>>     async def initialize(self):
        >>>         # Initialization
        >>>         await super().initialize()
        >>>
        >>>     def increment_stat(self, stat: str):
        >>>         self.stats[stat] = self.stats.get(stat, 0) + 1
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats: Dict[str, Any] = {
            "requests_total": 0,
            "success_count": 0,
            "error_count": 0,
            "start_time": datetime.now().isoformat(),
        }
        self.degraded_mode = False

    def get_stats(self) -> Dict[str, Any]:
        """Get component statistics"""
        return {
            **self.stats,
            "degraded_mode": self.degraded_mode,
            "uptime_seconds": self._get_uptime(),
        }

    def _get_uptime(self) -> float:
        """Calculate uptime in seconds"""
        if self.initialization_time:
            return (datetime.now() - self.initialization_time).total_seconds()
        return 0.0

    def increment_stat(self, stat: str, value: int = 1):
        """Increment a statistic counter"""
        self.stats[stat] = self.stats.get(stat, 0) + value

    def set_stat(self, stat: str, value: Any):
        """Set a statistic value"""
        self.stats[stat] = value

    def reset_stats(self):
        """Reset all statistics"""
        self.stats = {
            "requests_total": 0,
            "success_count": 0,
            "error_count": 0,
            "start_time": datetime.now().isoformat(),
        }
        logger.info(f"Statistics reset for {self.__class__.__name__}")


class ConfigurableComponent(ABC):
    """
    Component with configuration support

    Provides:
    - Configuration loading and validation
    - Configuration updates
    - Configuration export

    Example:
        >>> class MyComponent(ConfigurableComponent):
        >>>     def load_config(self, config: Dict):
        >>>         self.timeout = config.get('timeout', 30)
        >>>         self.retries = config.get('retries', 3)
        >>>         super().load_config(config)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config: Dict[str, Any] = config or {}
        if self.config:
            self.load_config(self.config)

    @abstractmethod
    def load_config(self, config: Dict[str, Any]):
        """
        Load configuration

        Override in subclasses to implement config loading.

        Args:
            config: Configuration dictionary
        """
        pass

    def update_config(self, config: Dict[str, Any]):
        """
        Update configuration

        Args:
            config: Configuration updates
        """
        self.config.update(config)
        self.load_config(self.config)
        logger.info(f"Configuration updated for {self.__class__.__name__}")

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()


class FullyManagedComponent(
    StatefulComponent, CacheableComponent, ConfigurableComponent
):
    """
    Fully managed component with all common functionality

    Combines:
    - Initialization (InitializableMixin via StatefulComponent)
    - State tracking (StatefulComponent)
    - Caching (CacheableComponent)
    - Configuration (ConfigurableComponent)

    Use this for complex components that need all features.

    Example:
        >>> class MyRAGEngine(FullyManagedComponent):
        >>>     async def initialize(self):
        >>>         # Your initialization
        >>>         await super().initialize()
        >>>
        >>>     def load_config(self, config: Dict):
        >>>         self.model = config.get('model')
        >>>
        >>>     def get_stats(self) -> Dict:
        >>>         return {
        >>>             **super().get_stats(),
        >>>             'custom_stat': self.custom_value
        >>>         }
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, *args, **kwargs):
        # Initialize all parent classes
        super().__init__(config=config, *args, **kwargs)

    @abstractmethod
    def load_config(self, config: Dict[str, Any]):
        """Load configuration (must be implemented)"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics (must be implemented)"""
        pass


__all__ = [
    "InitializableMixin",
    "CacheableComponent",
    "StatefulComponent",
    "ConfigurableComponent",
    "FullyManagedComponent",
]
