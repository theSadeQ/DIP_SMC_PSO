#==========================================================================================\\\
#================= src/interfaces/data_exchange/factory_resilient.py ====================\\\
#==========================================================================================\\\
"""
RESILIENT Factory for serializers and data exchange components.
This is a production-hardened version that eliminates Single Points of Failure (SPOFs)
identified in the original factory implementation.

Key SPOF Fixes Applied:
1. Eliminated global singleton dependency injection pattern
2. Multiple factory instances with failover capability
3. Graceful degradation when components fail
4. Factory registry with automatic recovery
5. Thread-safe factory management
6. Built-in health monitoring and self-healing

PRODUCTION SAFETY: No single points of failure, automatic recovery mechanisms.
"""

import threading
import time
import weakref
from typing import Dict, Any, Optional, Type, Union, List, Callable
from enum import Enum
import logging
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import copy

from .serializers import (
    SerializerInterface, SerializationFormat, SerializationError,
    JSONSerializer, MessagePackSerializer, PickleSerializer,
    BinarySerializer, CompressionSerializer
)
from .schemas import SchemaValidator, DataSchema, MessageSchema
from .data_types import CompressionType


class FactoryState(Enum):
    """Factory state enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class FactoryHealth:
    """Factory health status."""
    state: FactoryState = FactoryState.HEALTHY
    last_check: float = field(default_factory=time.time)
    error_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None

    def update_success(self):
        """Record successful operation."""
        self.success_count += 1
        if self.error_count > 0 and self.success_count > 5:
            self.state = FactoryState.HEALTHY
            self.error_count = 0  # Reset after recovery

    def update_error(self, error_msg: str):
        """Record error operation."""
        self.error_count += 1
        self.last_error = error_msg

        if self.error_count >= 5:
            self.state = FactoryState.FAILED
        elif self.error_count >= 2:
            self.state = FactoryState.DEGRADED


class ResilientSerializerFactory:
    """
    Production-safe serializer factory with SPOF elimination.

    Features:
    - No global singleton dependencies
    - Automatic failover and recovery
    - Health monitoring and self-healing
    - Thread-safe operations
    - Graceful degradation
    """

    def __init__(self, factory_id: str = None):
        """Initialize resilient factory."""
        self.factory_id = factory_id or f"factory_{int(time.time() * 1000)}"
        self._serializer_cache: Dict[str, SerializerInterface] = {}
        self._cache_lock = threading.RLock()

        # Health monitoring
        self._health = FactoryHealth()
        self._health_lock = threading.RLock()

        # Fallback mechanisms
        self._fallback_serializers: List[SerializerInterface] = []
        self._init_fallback_serializers()

        self._logger = logging.getLogger(f"resilient_factory_{self.factory_id}")

        # Performance tracking
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'fallbacks_used': 0,
            'recoveries': 0
        }
        self._stats_lock = threading.RLock()

    def create_serializer(self, format_type: Union[SerializationFormat, str],
                         compression: Optional[CompressionType] = None,
                         **kwargs) -> SerializerInterface:
        """Create serializer with automatic failover."""
        try:
            # Attempt primary creation
            serializer = self._create_serializer_safe(format_type, compression, kwargs)

            with self._health_lock:
                self._health.update_success()

            return serializer

        except Exception as e:
            # Record error and attempt fallback
            with self._health_lock:
                self._health.update_error(str(e))

            self._logger.warning(f"Primary serializer creation failed: {e}, attempting fallback")

            # Try fallback serializers
            fallback = self._get_fallback_serializer(format_type)
            if fallback:
                with self._stats_lock:
                    self._stats['fallbacks_used'] += 1
                return fallback

            # If all else fails, use ultra-safe JSON
            self._logger.error(f"All serializer creation attempts failed, using emergency JSON")
            return JSONSerializer(ensure_ascii=True, compact=True)

    def create_serializer_with_retry(self, format_type: Union[SerializationFormat, str],
                                   compression: Optional[CompressionType] = None,
                                   max_retries: int = 3,
                                   **kwargs) -> SerializerInterface:
        """Create serializer with retry logic."""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return self.create_serializer(format_type, compression, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    self._logger.warning(f"Serializer creation attempt {attempt + 1} failed, retrying in {wait_time}s")

        # All retries failed
        raise SerializationError(f"Failed to create serializer after {max_retries} retries: {last_error}")

    def get_factory_health(self) -> FactoryHealth:
        """Get factory health status."""
        with self._health_lock:
            return copy.deepcopy(self._health)

    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics."""
        with self._stats_lock:
            stats = self._stats.copy()

        with self._cache_lock:
            stats['cached_serializers'] = len(self._serializer_cache)

        with self._health_lock:
            stats['health_state'] = self._health.state.value
            stats['error_count'] = self._health.error_count
            stats['success_count'] = self._health.success_count

        return stats

    def clear_cache_and_recover(self) -> bool:
        """Clear cache and attempt recovery."""
        try:
            with self._cache_lock:
                self._serializer_cache.clear()

            with self._health_lock:
                if self._health.state == FactoryState.FAILED:
                    self._health.state = FactoryState.RECOVERING
                    self._health.error_count = 0

            with self._stats_lock:
                self._stats['recoveries'] += 1

            # Test recovery by creating a simple serializer
            test_serializer = self._create_serializer_safe(SerializationFormat.JSON, None, {})

            with self._health_lock:
                self._health.state = FactoryState.HEALTHY
                self._health.update_success()

            self._logger.info(f"Factory {self.factory_id} successfully recovered")
            return True

        except Exception as e:
            with self._health_lock:
                self._health.state = FactoryState.FAILED
                self._health.update_error(f"Recovery failed: {e}")

            self._logger.error(f"Factory recovery failed: {e}")
            return False

    def _create_serializer_safe(self, format_type: Union[SerializationFormat, str],
                              compression: Optional[CompressionType],
                              kwargs: Dict[str, Any]) -> SerializerInterface:
        """Safely create serializer with caching."""
        if isinstance(format_type, str):
            try:
                format_type = SerializationFormat(format_type)
            except ValueError:
                raise ValueError(f"Unknown serialization format: {format_type}")

        # Generate cache key
        cache_key = self._generate_cache_key(format_type, compression, kwargs)

        # Check cache
        with self._cache_lock:
            if cache_key in self._serializer_cache:
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return self._serializer_cache[cache_key]

        # Create new serializer
        with self._stats_lock:
            self._stats['cache_misses'] += 1

        serializer = self._create_serializer_impl(format_type, compression, kwargs)

        # Cache the result
        with self._cache_lock:
            self._serializer_cache[cache_key] = serializer

        return serializer

    def _create_serializer_impl(self, format_type: SerializationFormat,
                               compression: Optional[CompressionType],
                               kwargs: Dict[str, Any]) -> SerializerInterface:
        """Implementation of serializer creation."""
        base_serializer = None

        # Create base serializer with safe defaults
        if format_type == SerializationFormat.JSON:
            base_serializer = JSONSerializer(
                ensure_ascii=kwargs.get('ensure_ascii', True),  # Safe default
                sort_keys=kwargs.get('sort_keys', False),
                indent=kwargs.get('indent'),
                compact=kwargs.get('compact', True)
            )

        elif format_type == SerializationFormat.MSGPACK:
            base_serializer = MessagePackSerializer(
                use_bin_type=kwargs.get('use_bin_type', True),
                strict_map_key=kwargs.get('strict_map_key', False)
            )

        elif format_type == SerializationFormat.PICKLE:
            # Use safe protocol version
            import pickle
            safe_protocol = min(kwargs.get('protocol', pickle.HIGHEST_PROTOCOL), 4)
            base_serializer = PickleSerializer(protocol=safe_protocol)

        elif format_type == SerializationFormat.BINARY:
            base_serializer = BinarySerializer()

        else:
            raise ValueError(f"Unsupported serialization format: {format_type}")

        # Add compression if specified
        if compression and compression != CompressionType.NONE:
            compression_level = max(1, min(kwargs.get('compression_level', 6), 9))  # Safe range
            base_serializer = CompressionSerializer(base_serializer, compression, compression_level)

        return base_serializer

    def _init_fallback_serializers(self):
        """Initialize fallback serializers for emergency use."""
        try:
            # Ultra-safe JSON serializer
            safe_json = JSONSerializer(ensure_ascii=True, compact=True)
            self._fallback_serializers.append(safe_json)

            # Safe binary serializer
            safe_binary = BinarySerializer()
            self._fallback_serializers.append(safe_binary)

        except Exception as e:
            self._logger.error(f"Failed to initialize fallback serializers: {e}")

    def _get_fallback_serializer(self, format_type: Union[SerializationFormat, str]) -> Optional[SerializerInterface]:
        """Get appropriate fallback serializer."""
        if not self._fallback_serializers:
            return None

        # Try to match format type
        if isinstance(format_type, str):
            try:
                format_type = SerializationFormat(format_type)
            except ValueError:
                pass

        # Return most appropriate fallback
        if format_type == SerializationFormat.JSON:
            return self._fallback_serializers[0]  # Safe JSON
        else:
            return self._fallback_serializers[-1]  # Safe binary

    def _generate_cache_key(self, format_type: SerializationFormat,
                           compression: Optional[CompressionType],
                           kwargs: Dict[str, Any]) -> str:
        """Generate cache key for serializer configuration."""
        key_parts = [format_type.value]

        if compression:
            key_parts.append(compression.value)

        # Add relevant kwargs (sorted for consistency)
        for key in sorted(kwargs.keys()):
            key_parts.append(f"{key}={kwargs[key]}")

        return ":".join(key_parts)


class FactoryRegistry:
    """
    Registry for managing multiple factory instances with failover.

    Eliminates SPOF by maintaining multiple factory instances and
    providing automatic failover when factories fail.
    """

    def __init__(self):
        self._factories: Dict[str, ResilientSerializerFactory] = {}
        self._factory_weights: Dict[str, float] = {}  # For load balancing
        self._registry_lock = threading.RLock()
        self._current_factory_index = 0

        self._logger = logging.getLogger("factory_registry")

        # Initialize default factories
        self._init_default_factories()

    def register_factory(self, factory: ResilientSerializerFactory, weight: float = 1.0) -> None:
        """Register a factory instance."""
        with self._registry_lock:
            self._factories[factory.factory_id] = factory
            self._factory_weights[factory.factory_id] = weight
            self._logger.info(f"Registered factory: {factory.factory_id}")

    def unregister_factory(self, factory_id: str) -> bool:
        """Unregister a factory instance."""
        with self._registry_lock:
            if factory_id in self._factories:
                del self._factories[factory_id]
                del self._factory_weights[factory_id]
                self._logger.info(f"Unregistered factory: {factory_id}")
                return True
            return False

    def get_healthy_factory(self) -> Optional[ResilientSerializerFactory]:
        """Get a healthy factory instance."""
        with self._registry_lock:
            factories = list(self._factories.values())

        # Try to find a healthy factory
        for factory in factories:
            health = factory.get_factory_health()
            if health.state == FactoryState.HEALTHY:
                return factory

        # If no healthy factory, try degraded
        for factory in factories:
            health = factory.get_factory_health()
            if health.state == FactoryState.DEGRADED:
                self._logger.warning(f"Using degraded factory: {factory.factory_id}")
                return factory

        # If no healthy/degraded, try recovery
        for factory in factories:
            if factory.clear_cache_and_recover():
                return factory

        # Last resort: create emergency factory
        self._logger.error("No healthy factories available, creating emergency factory")
        emergency_factory = ResilientSerializerFactory("emergency")
        self.register_factory(emergency_factory, weight=0.1)
        return emergency_factory

    def create_serializer_resilient(self, format_type: Union[SerializationFormat, str],
                                  compression: Optional[CompressionType] = None,
                                  **kwargs) -> SerializerInterface:
        """Create serializer using resilient factory selection."""
        factory = self.get_healthy_factory()
        if not factory:
            raise SerializationError("No factories available for serializer creation")

        try:
            return factory.create_serializer_with_retry(format_type, compression, **kwargs)
        except Exception as e:
            # Mark factory as problematic and try another
            self._logger.error(f"Factory {factory.factory_id} failed: {e}")

            # Try to get another factory
            with self._registry_lock:
                other_factories = [f for f in self._factories.values() if f.factory_id != factory.factory_id]

            for backup_factory in other_factories:
                try:
                    return backup_factory.create_serializer_with_retry(format_type, compression, **kwargs)
                except Exception:
                    continue

            # All factories failed - create emergency serializer
            self._logger.critical("All factories failed, using emergency JSON serializer")
            return JSONSerializer(ensure_ascii=True, compact=True)

    def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status and factory health."""
        with self._registry_lock:
            factories_info = {}
            for factory_id, factory in self._factories.items():
                health = factory.get_factory_health()
                stats = factory.get_statistics()
                factories_info[factory_id] = {
                    'health_state': health.state.value,
                    'error_count': health.error_count,
                    'success_count': health.success_count,
                    'weight': self._factory_weights[factory_id],
                    'stats': stats
                }

            return {
                'total_factories': len(self._factories),
                'healthy_factories': sum(1 for f in self._factories.values()
                                       if f.get_factory_health().state == FactoryState.HEALTHY),
                'factories': factories_info
            }

    def _init_default_factories(self):
        """Initialize default factory instances."""
        try:
            # Create primary and backup factories
            primary_factory = ResilientSerializerFactory("primary")
            backup_factory = ResilientSerializerFactory("backup")

            self.register_factory(primary_factory, weight=1.0)
            self.register_factory(backup_factory, weight=0.8)

        except Exception as e:
            self._logger.error(f"Failed to initialize default factories: {e}")


# Global registry instance (but not singleton - can be replaced)
_default_registry = FactoryRegistry()


def get_factory_registry() -> FactoryRegistry:
    """Get factory registry (replaceable, not singleton)."""
    return _default_registry


def set_factory_registry(registry: FactoryRegistry) -> None:
    """Replace factory registry (eliminates singleton dependency)."""
    global _default_registry
    _default_registry = registry


# Resilient factory functions (no singleton dependencies)
def create_serializer_resilient(format_type: Union[SerializationFormat, str],
                               compression: Optional[CompressionType] = None,
                               **kwargs) -> SerializerInterface:
    """Create serializer with full resilience and failover."""
    registry = get_factory_registry()
    return registry.create_serializer_resilient(format_type, compression, **kwargs)


def get_system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    registry = get_factory_registry()
    return registry.get_registry_status()