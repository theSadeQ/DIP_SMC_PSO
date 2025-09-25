#==========================================================================================\\\
#======================== src/interfaces/data_exchange/factory.py ======================\\\
#==========================================================================================\\\
"""
Factory for creating serializers and data exchange components.
This module provides a unified factory interface for creating
serializers, validators, and other data exchange components
with automatic configuration and optimization.
"""

from typing import Dict, Any, Optional, Type, Union
from enum import Enum
import logging

from .serializers import (
    SerializerInterface, SerializationFormat, SerializationError,
    JSONSerializer, MessagePackSerializer, PickleSerializer,
    BinarySerializer, CompressionSerializer,
    create_json_serializer, create_msgpack_serializer, create_compressed_serializer
)
from .schemas import SchemaValidator, DataSchema, MessageSchema
from .data_types import CompressionType


class SerializerPreset(Enum):
    """Predefined serializer configurations."""
    JSON_COMPACT = "json_compact"
    JSON_PRETTY = "json_pretty"
    JSON_COMPRESSED = "json_compressed"
    MSGPACK_FAST = "msgpack_fast"
    MSGPACK_COMPRESSED = "msgpack_compressed"
    BINARY_FAST = "binary_fast"
    PICKLE_SECURE = "pickle_secure"
    HIGH_COMPRESSION = "high_compression"
    REALTIME_OPTIMIZED = "realtime_optimized"


class OptimizationMode(Enum):
    """Optimization modes for serializer selection."""
    SPEED = "speed"
    SIZE = "size"
    COMPATIBILITY = "compatibility"
    RELIABILITY = "reliability"
    BALANCED = "balanced"


class SerializerFactory:
    """Factory for creating and managing serializers."""

    def __init__(self):
        self._serializer_cache: Dict[str, SerializerInterface] = {}
        self._preset_configs = self._initialize_presets()
        self._logger = logging.getLogger("serializer_factory")

    def create_serializer(self, format_type: Union[SerializationFormat, str],
                         compression: Optional[CompressionType] = None,
                         **kwargs) -> SerializerInterface:
        """Create serializer with specified format and options."""
        if isinstance(format_type, str):
            try:
                format_type = SerializationFormat(format_type)
            except ValueError:
                raise ValueError(f"Unknown serialization format: {format_type}")

        # Generate cache key
        cache_key = self._generate_cache_key(format_type, compression, kwargs)

        # Check cache
        if cache_key in self._serializer_cache:
            return self._serializer_cache[cache_key]

        # Create serializer
        serializer = self._create_serializer_impl(format_type, compression, kwargs)

        # Cache and return
        self._serializer_cache[cache_key] = serializer
        return serializer

    def create_from_preset(self, preset: Union[SerializerPreset, str]) -> SerializerInterface:
        """Create serializer from predefined preset."""
        if isinstance(preset, str):
            try:
                preset = SerializerPreset(preset)
            except ValueError:
                raise ValueError(f"Unknown serializer preset: {preset}")

        if preset not in self._preset_configs:
            raise ValueError(f"Preset configuration not found: {preset}")

        config = self._preset_configs[preset]
        return self.create_serializer(**config)

    def create_optimized(self, optimization_mode: OptimizationMode,
                        data_characteristics: Optional[Dict[str, Any]] = None) -> SerializerInterface:
        """Create serializer optimized for specific use case."""
        config = self._get_optimized_config(optimization_mode, data_characteristics)
        return self.create_serializer(**config)

    def auto_select_serializer(self, sample_data: Any,
                             requirements: Optional[Dict[str, Any]] = None) -> SerializerInterface:
        """Automatically select best serializer based on data analysis."""
        analysis = self._analyze_data_characteristics(sample_data)
        requirements = requirements or {}

        # Merge analysis with requirements
        combined_requirements = {**analysis, **requirements}

        # Select optimization mode
        if requirements.get('real_time', False):
            mode = OptimizationMode.SPEED
        elif requirements.get('minimize_size', False):
            mode = OptimizationMode.SIZE
        elif requirements.get('cross_platform', False):
            mode = OptimizationMode.COMPATIBILITY
        else:
            mode = OptimizationMode.BALANCED

        return self.create_optimized(mode, combined_requirements)

    def benchmark_serializers(self, test_data: Any,
                             formats: Optional[list] = None) -> Dict[str, Dict[str, float]]:
        """Benchmark different serializers with test data."""
        if formats is None:
            formats = [
                SerializationFormat.JSON,
                SerializationFormat.MSGPACK,
                SerializationFormat.PICKLE,
                SerializationFormat.BINARY
            ]

        results = {}

        for format_type in formats:
            try:
                serializer = self.create_serializer(format_type)
                performance = self._benchmark_serializer(serializer, test_data)
                results[format_type.value] = performance
            except Exception as e:
                self._logger.warning(f"Failed to benchmark {format_type}: {e}")
                results[format_type.value] = {'error': str(e)}

        return results

    def clear_cache(self) -> None:
        """Clear serializer cache."""
        self._serializer_cache.clear()

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_serializers': len(self._serializer_cache),
            'cache_keys': list(self._serializer_cache.keys())
        }

    def _create_serializer_impl(self, format_type: SerializationFormat,
                               compression: Optional[CompressionType],
                               kwargs: Dict[str, Any]) -> SerializerInterface:
        """Internal serializer creation implementation."""
        base_serializer = None

        # Create base serializer
        if format_type == SerializationFormat.JSON:
            base_serializer = JSONSerializer(
                ensure_ascii=kwargs.get('ensure_ascii', False),
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
            base_serializer = PickleSerializer(
                protocol=kwargs.get('protocol', pickle.HIGHEST_PROTOCOL)
            )

        elif format_type == SerializationFormat.BINARY:
            base_serializer = BinarySerializer()

        elif format_type in [SerializationFormat.JSON_COMPRESSED, SerializationFormat.MSGPACK_COMPRESSED]:
            # Create compressed serializer
            if format_type == SerializationFormat.JSON_COMPRESSED:
                base_format = SerializationFormat.JSON
            else:
                base_format = SerializationFormat.MSGPACK

            base_serializer = self._create_serializer_impl(base_format, None, kwargs)
            compression = compression or CompressionType.GZIP

        else:
            raise ValueError(f"Unsupported serialization format: {format_type}")

        # Wrap with compression if specified
        if compression and compression != CompressionType.NONE:
            compression_level = kwargs.get('compression_level', 6)
            return CompressionSerializer(base_serializer, compression, compression_level)

        return base_serializer

    def _initialize_presets(self) -> Dict[SerializerPreset, Dict[str, Any]]:
        """Initialize predefined serializer configurations."""
        return {
            SerializerPreset.JSON_COMPACT: {
                'format_type': SerializationFormat.JSON,
                'compact': True,
                'ensure_ascii': False
            },

            SerializerPreset.JSON_PRETTY: {
                'format_type': SerializationFormat.JSON,
                'compact': False,
                'indent': 2,
                'sort_keys': True
            },

            SerializerPreset.JSON_COMPRESSED: {
                'format_type': SerializationFormat.JSON,
                'compression': CompressionType.GZIP,
                'compression_level': 6,
                'compact': True
            },

            SerializerPreset.MSGPACK_FAST: {
                'format_type': SerializationFormat.MSGPACK,
                'use_bin_type': True,
                'strict_map_key': False
            },

            SerializerPreset.MSGPACK_COMPRESSED: {
                'format_type': SerializationFormat.MSGPACK,
                'compression': CompressionType.LZ4,
                'compression_level': 3
            },

            SerializerPreset.BINARY_FAST: {
                'format_type': SerializationFormat.BINARY
            },

            SerializerPreset.PICKLE_SECURE: {
                'format_type': SerializationFormat.PICKLE,
                'protocol': 4  # Secure protocol version
            },

            SerializerPreset.HIGH_COMPRESSION: {
                'format_type': SerializationFormat.MSGPACK,
                'compression': CompressionType.ZSTD,
                'compression_level': 15
            },

            SerializerPreset.REALTIME_OPTIMIZED: {
                'format_type': SerializationFormat.BINARY
            }
        }

    def _get_optimized_config(self, mode: OptimizationMode,
                             characteristics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get optimized configuration for specific mode."""
        characteristics = characteristics or {}

        if mode == OptimizationMode.SPEED:
            # Prioritize serialization speed
            if characteristics.get('data_size', 'medium') == 'small':
                return {'format_type': SerializationFormat.BINARY}
            else:
                return {'format_type': SerializationFormat.MSGPACK}

        elif mode == OptimizationMode.SIZE:
            # Prioritize output size
            return {
                'format_type': SerializationFormat.MSGPACK,
                'compression': CompressionType.ZSTD,
                'compression_level': 12
            }

        elif mode == OptimizationMode.COMPATIBILITY:
            # Prioritize cross-platform compatibility
            return {
                'format_type': SerializationFormat.JSON,
                'ensure_ascii': True,
                'compact': True
            }

        elif mode == OptimizationMode.RELIABILITY:
            # Prioritize data integrity
            return {
                'format_type': SerializationFormat.MSGPACK,
                'compression': CompressionType.GZIP,
                'compression_level': 6
            }

        else:  # BALANCED
            # Balanced configuration
            if characteristics.get('has_binary_data', False):
                return {'format_type': SerializationFormat.MSGPACK}
            else:
                return {
                    'format_type': SerializationFormat.JSON,
                    'compression': CompressionType.GZIP,
                    'compression_level': 3
                }

    def _analyze_data_characteristics(self, data: Any) -> Dict[str, Any]:
        """Analyze data to determine characteristics for optimization."""
        import sys

        characteristics = {}

        # Analyze data size
        try:
            size = sys.getsizeof(data)
            if size < 1024:  # < 1KB
                characteristics['data_size'] = 'small'
            elif size < 1024 * 1024:  # < 1MB
                characteristics['data_size'] = 'medium'
            else:
                characteristics['data_size'] = 'large'
        except Exception:
            characteristics['data_size'] = 'unknown'

        # Check for binary data
        characteristics['has_binary_data'] = self._contains_binary_data(data)

        # Check data complexity
        characteristics['complexity'] = self._assess_complexity(data)

        # Check for repeated patterns
        characteristics['has_repetition'] = self._has_repetitive_patterns(data)

        return characteristics

    def _contains_binary_data(self, data: Any) -> bool:
        """Check if data contains binary content."""
        if isinstance(data, bytes):
            return True
        elif isinstance(data, dict):
            return any(self._contains_binary_data(v) for v in data.values())
        elif isinstance(data, (list, tuple)):
            return any(self._contains_binary_data(item) for item in data)
        return False

    def _assess_complexity(self, data: Any, depth: int = 0) -> str:
        """Assess data structure complexity."""
        if depth > 5:
            return 'high'

        if isinstance(data, (int, float, str, bool, type(None))):
            return 'low'
        elif isinstance(data, dict):
            if len(data) > 10:
                return 'high'
            complexities = [self._assess_complexity(v, depth + 1) for v in data.values()]
            if 'high' in complexities:
                return 'high'
            elif 'medium' in complexities:
                return 'medium'
            return 'low'
        elif isinstance(data, (list, tuple)):
            if len(data) > 100:
                return 'high'
            elif len(data) > 10:
                return 'medium'
            return 'low'
        else:
            return 'medium'

    def _has_repetitive_patterns(self, data: Any) -> bool:
        """Check for repetitive patterns that benefit from compression."""
        try:
            if isinstance(data, str) and len(data) > 100:
                # Simple repetition check for strings
                unique_chars = len(set(data))
                return unique_chars < len(data) * 0.3

            elif isinstance(data, (list, tuple)) and len(data) > 10:
                # Check for repeated elements
                unique_items = len(set(str(item) for item in data))
                return unique_items < len(data) * 0.5

            return False
        except Exception:
            return False

    def _benchmark_serializer(self, serializer: SerializerInterface,
                             test_data: Any, iterations: int = 100) -> Dict[str, float]:
        """Benchmark a serializer with test data."""
        import time

        # Serialization benchmark
        start_time = time.perf_counter()
        for _ in range(iterations):
            serialized = serializer.serialize(test_data)
        serialize_time = (time.perf_counter() - start_time) / iterations

        # Deserialization benchmark
        start_time = time.perf_counter()
        for _ in range(iterations):
            deserialized = serializer.deserialize(serialized)
        deserialize_time = (time.perf_counter() - start_time) / iterations

        # Size measurement
        serialized_size = len(serialized)

        return {
            'serialize_time_ms': serialize_time * 1000,
            'deserialize_time_ms': deserialize_time * 1000,
            'total_time_ms': (serialize_time + deserialize_time) * 1000,
            'serialized_size_bytes': serialized_size,
            'compression_ratio': serializer.get_compression_ratio(test_data)
        }

    def _generate_cache_key(self, format_type: SerializationFormat,
                           compression: Optional[CompressionType],
                           kwargs: Dict[str, Any]) -> str:
        """Generate cache key for serializer configuration."""
        key_parts = [format_type.value]

        if compression:
            key_parts.append(compression.value)

        # Add relevant kwargs
        for key in sorted(kwargs.keys()):
            key_parts.append(f"{key}={kwargs[key]}")

        return ":".join(key_parts)


# Global factory instance
_global_factory = SerializerFactory()


def create_serializer(format_type: Union[SerializationFormat, str],
                     compression: Optional[CompressionType] = None,
                     **kwargs) -> SerializerInterface:
    """Create serializer using global factory."""
    return _global_factory.create_serializer(format_type, compression, **kwargs)


def create_from_preset(preset: Union[SerializerPreset, str]) -> SerializerInterface:
    """Create serializer from preset using global factory."""
    return _global_factory.create_from_preset(preset)


def auto_select_serializer(sample_data: Any,
                          requirements: Optional[Dict[str, Any]] = None) -> SerializerInterface:
    """Auto-select optimal serializer using global factory."""
    return _global_factory.auto_select_serializer(sample_data, requirements)


def benchmark_serializers(test_data: Any,
                         formats: Optional[list] = None) -> Dict[str, Dict[str, float]]:
    """Benchmark serializers using global factory."""
    return _global_factory.benchmark_serializers(test_data, formats)


def get_recommended_serializer(use_case: str) -> SerializerInterface:
    """Get recommended serializer for common use cases."""
    recommendations = {
        'api_communication': SerializerPreset.JSON_COMPACT,
        'real_time_control': SerializerPreset.BINARY_FAST,
        'data_logging': SerializerPreset.MSGPACK_COMPRESSED,
        'configuration': SerializerPreset.JSON_PRETTY,
        'telemetry': SerializerPreset.MSGPACK_FAST,
        'archival': SerializerPreset.HIGH_COMPRESSION,
        'inter_process': SerializerPreset.PICKLE_SECURE,
        'network_minimal': SerializerPreset.REALTIME_OPTIMIZED
    }

    if use_case not in recommendations:
        raise ValueError(f"Unknown use case: {use_case}. Available: {list(recommendations.keys())}")

    return create_from_preset(recommendations[use_case])