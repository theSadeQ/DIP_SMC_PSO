#==========================================================================================\\\
#==================== src/interfaces/data_exchange/performance.py =====================\\\
#==========================================================================================\\\
"""
Performance-optimized serialization with monitoring and metrics.
This module provides high-performance serialization capabilities
with comprehensive performance monitoring, metrics collection,
and adaptive optimization based on runtime characteristics.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum
import logging
import statistics
from collections import deque, defaultdict

from .serializers import SerializerInterface, SerializationFormat
from .data_types import SerializableData


class MetricType(Enum):
    """Performance metric types."""
    SERIALIZATION_TIME = "serialization_time"
    DESERIALIZATION_TIME = "deserialization_time"
    SERIALIZED_SIZE = "serialized_size"
    COMPRESSION_RATIO = "compression_ratio"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    metric_type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    operation_id: Optional[str] = None
    data_size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SerializationMetrics:
    """Comprehensive serialization performance metrics."""
    total_operations: int = 0
    total_bytes_processed: int = 0
    total_serialization_time: float = 0.0
    total_deserialization_time: float = 0.0

    # Statistics
    avg_serialization_time: float = 0.0
    avg_deserialization_time: float = 0.0
    avg_serialized_size: float = 0.0
    avg_compression_ratio: float = 1.0

    # Percentiles
    p50_serialization_time: float = 0.0
    p95_serialization_time: float = 0.0
    p99_serialization_time: float = 0.0

    # Rates
    operations_per_second: float = 0.0
    bytes_per_second: float = 0.0
    error_rate: float = 0.0

    # Errors
    total_errors: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)

    # Timing history
    serialization_times: List[float] = field(default_factory=list)
    deserialization_times: List[float] = field(default_factory=list)
    serialized_sizes: List[int] = field(default_factory=list)

    def update_statistics(self) -> None:
        """Update computed statistics from raw data."""
        if self.total_operations > 0:
            self.avg_serialization_time = self.total_serialization_time / self.total_operations
            self.avg_deserialization_time = self.total_deserialization_time / self.total_operations

        if self.serialized_sizes:
            self.avg_serialized_size = statistics.mean(self.serialized_sizes)

        if self.serialization_times:
            sorted_times = sorted(self.serialization_times)
            n = len(sorted_times)
            self.p50_serialization_time = sorted_times[int(n * 0.5)]
            self.p95_serialization_time = sorted_times[int(n * 0.95)]
            self.p99_serialization_time = sorted_times[int(n * 0.99)]

        # Calculate rates
        if self.total_serialization_time > 0:
            self.operations_per_second = self.total_operations / self.total_serialization_time
            self.bytes_per_second = self.total_bytes_processed / self.total_serialization_time

        if self.total_operations > 0:
            self.error_rate = self.total_errors / self.total_operations

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            'operations': {
                'total': self.total_operations,
                'per_second': self.operations_per_second,
                'error_rate': self.error_rate
            },
            'timing': {
                'avg_serialize_ms': self.avg_serialization_time * 1000,
                'avg_deserialize_ms': self.avg_deserialization_time * 1000,
                'p95_serialize_ms': self.p95_serialization_time * 1000,
                'p99_serialize_ms': self.p99_serialization_time * 1000
            },
            'throughput': {
                'bytes_per_second': self.bytes_per_second,
                'avg_size_bytes': self.avg_serialized_size,
                'total_bytes': self.total_bytes_processed
            },
            'compression': {
                'avg_ratio': self.avg_compression_ratio
            },
            'errors': {
                'total': self.total_errors,
                'by_type': dict(self.error_types)
            }
        }


class PerformanceMonitor:
    """Real-time performance monitoring for serialization operations."""

    def __init__(self, window_size: int = 1000, enable_detailed_logging: bool = False):
        self._window_size = window_size
        self._enable_detailed_logging = enable_detailed_logging

        # Thread-safe metrics storage
        self._lock = threading.RLock()
        self._metrics: Dict[str, SerializationMetrics] = defaultdict(SerializationMetrics)
        self._recent_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

        # Performance thresholds
        self._performance_thresholds = {
            'serialization_time_ms': 10.0,  # 10ms
            'deserialization_time_ms': 10.0,
            'error_rate': 0.01  # 1%
        }

        # Alerting
        self._alert_handlers: List[Callable[[str, Dict[str, Any]], None]] = []

        self._logger = logging.getLogger("performance_monitor")

    def record_operation(self, serializer_id: str, operation_type: str,
                        duration: float, data_size: int,
                        success: bool = True, error_type: Optional[str] = None) -> None:
        """Record a serialization operation."""
        with self._lock:
            metrics = self._metrics[serializer_id]

            # Update counters
            metrics.total_operations += 1
            if data_size > 0:
                metrics.total_bytes_processed += data_size

            # Update timing
            if operation_type == 'serialize':
                metrics.total_serialization_time += duration
                metrics.serialization_times.append(duration)
                if len(metrics.serialization_times) > self._window_size:
                    metrics.serialization_times.pop(0)
            elif operation_type == 'deserialize':
                metrics.total_deserialization_time += duration
                metrics.deserialization_times.append(duration)
                if len(metrics.deserialization_times) > self._window_size:
                    metrics.deserialization_times.pop(0)

            # Update size tracking
            if data_size > 0:
                metrics.serialized_sizes.append(data_size)
                if len(metrics.serialized_sizes) > self._window_size:
                    metrics.serialized_sizes.pop(0)

            # Error tracking
            if not success:
                metrics.total_errors += 1
                if error_type:
                    metrics.error_types[error_type] = metrics.error_types.get(error_type, 0) + 1

            # Update statistics
            metrics.update_statistics()

            # Store recent metric
            metric = PerformanceMetric(
                metric_type=MetricType.SERIALIZATION_TIME if operation_type == 'serialize' else MetricType.DESERIALIZATION_TIME,
                value=duration,
                data_size=data_size,
                metadata={'success': success, 'error_type': error_type}
            )
            self._recent_metrics[serializer_id].append(metric)

            # Check for performance alerts
            self._check_performance_alerts(serializer_id, metrics)

            if self._enable_detailed_logging:
                self._logger.debug(f"{serializer_id}: {operation_type} {duration*1000:.2f}ms, {data_size} bytes, success={success}")

    def get_metrics(self, serializer_id: Optional[str] = None) -> Union[SerializationMetrics, Dict[str, SerializationMetrics]]:
        """Get metrics for a specific serializer or all serializers."""
        with self._lock:
            if serializer_id:
                return self._metrics.get(serializer_id, SerializationMetrics())
            else:
                return dict(self._metrics)

    def get_summary(self, serializer_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary."""
        if serializer_id:
            metrics = self.get_metrics(serializer_id)
            return {serializer_id: metrics.get_summary()}
        else:
            metrics_dict = self.get_metrics()
            return {sid: metrics.get_summary() for sid, metrics in metrics_dict.items()}

    def reset_metrics(self, serializer_id: Optional[str] = None) -> None:
        """Reset metrics for specific serializer or all serializers."""
        with self._lock:
            if serializer_id:
                if serializer_id in self._metrics:
                    self._metrics[serializer_id] = SerializationMetrics()
                    self._recent_metrics[serializer_id].clear()
            else:
                self._metrics.clear()
                self._recent_metrics.clear()

    def set_performance_threshold(self, metric_name: str, threshold: float) -> None:
        """Set performance threshold for alerting."""
        self._performance_thresholds[metric_name] = threshold

    def add_alert_handler(self, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add performance alert handler."""
        self._alert_handlers.append(handler)

    def _check_performance_alerts(self, serializer_id: str, metrics: SerializationMetrics) -> None:
        """Check for performance threshold violations."""
        alerts = []

        # Check serialization time
        if (metrics.avg_serialization_time * 1000 >
            self._performance_thresholds.get('serialization_time_ms', float('inf'))):
            alerts.append({
                'type': 'high_serialization_time',
                'value': metrics.avg_serialization_time * 1000,
                'threshold': self._performance_thresholds['serialization_time_ms']
            })

        # Check deserialization time
        if (metrics.avg_deserialization_time * 1000 >
            self._performance_thresholds.get('deserialization_time_ms', float('inf'))):
            alerts.append({
                'type': 'high_deserialization_time',
                'value': metrics.avg_deserialization_time * 1000,
                'threshold': self._performance_thresholds['deserialization_time_ms']
            })

        # Check error rate
        if metrics.error_rate > self._performance_thresholds.get('error_rate', 1.0):
            alerts.append({
                'type': 'high_error_rate',
                'value': metrics.error_rate,
                'threshold': self._performance_thresholds['error_rate']
            })

        # Send alerts
        for alert in alerts:
            for handler in self._alert_handlers:
                try:
                    handler(serializer_id, alert)
                except Exception as e:
                    self._logger.error(f"Error in alert handler: {e}")

    def get_recent_metrics(self, serializer_id: str, count: Optional[int] = None) -> List[PerformanceMetric]:
        """Get recent metrics for a serializer."""
        with self._lock:
            metrics = list(self._recent_metrics.get(serializer_id, []))
            if count is not None:
                return metrics[-count:]
            return metrics


class PerformanceSerializer(SerializerInterface):
    """Performance-aware serializer wrapper with monitoring and adaptive optimization."""

    def __init__(self, base_serializer: SerializerInterface,
                 monitor: Optional[PerformanceMonitor] = None,
                 enable_adaptive_optimization: bool = True):
        self._base_serializer = base_serializer
        self._monitor = monitor or PerformanceMonitor()
        self._enable_adaptive_optimization = enable_adaptive_optimization

        # Adaptive optimization state
        self._optimization_window = 100
        self._optimization_threshold = 0.1  # 10% improvement threshold
        self._last_optimization_check = 0

        # Serializer ID for monitoring
        self._serializer_id = f"{base_serializer.__class__.__name__}_{id(self)}"

        self._logger = logging.getLogger("performance_serializer")

    @property
    def format_type(self) -> SerializationFormat:
        return self._base_serializer.format_type

    @property
    def content_type(self) -> str:
        return self._base_serializer.content_type

    def serialize(self, data: Any) -> bytes:
        """Serialize data with performance monitoring."""
        start_time = time.perf_counter()
        success = True
        error_type = None
        result = None

        try:
            result = self._base_serializer.serialize(data)
            return result

        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise

        finally:
            duration = time.perf_counter() - start_time
            data_size = len(result) if result else 0

            # Record performance metrics
            self._monitor.record_operation(
                self._serializer_id, 'serialize', duration, data_size, success, error_type
            )

            # Check for adaptive optimization
            if self._enable_adaptive_optimization:
                self._check_adaptive_optimization()

    def deserialize(self, data: bytes, target_type: Optional[type] = None) -> Any:
        """Deserialize data with performance monitoring."""
        start_time = time.perf_counter()
        success = True
        error_type = None

        try:
            result = self._base_serializer.deserialize(data, target_type)
            return result

        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise

        finally:
            duration = time.perf_counter() - start_time
            data_size = len(data)

            # Record performance metrics
            self._monitor.record_operation(
                self._serializer_id, 'deserialize', duration, data_size, success, error_type
            )

    def get_performance_metrics(self) -> SerializationMetrics:
        """Get performance metrics for this serializer."""
        return self._monitor.get_metrics(self._serializer_id)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for this serializer."""
        return self._monitor.get_summary(self._serializer_id)

    def reset_performance_metrics(self) -> None:
        """Reset performance metrics for this serializer."""
        self._monitor.reset_metrics(self._serializer_id)

    def set_performance_threshold(self, metric_name: str, threshold: float) -> None:
        """Set performance threshold for this serializer."""
        self._monitor.set_performance_threshold(metric_name, threshold)

    def _check_adaptive_optimization(self) -> None:
        """Check if adaptive optimization should be triggered."""
        metrics = self.get_performance_metrics()

        # Only check periodically
        if metrics.total_operations - self._last_optimization_check < self._optimization_window:
            return

        self._last_optimization_check = metrics.total_operations

        # Analyze recent performance
        recent_metrics = self._monitor.get_recent_metrics(self._serializer_id, self._optimization_window)
        if len(recent_metrics) < self._optimization_window:
            return

        # Check for performance degradation
        serialize_times = [m.value for m in recent_metrics if m.metric_type == MetricType.SERIALIZATION_TIME]
        if serialize_times:
            recent_avg = statistics.mean(serialize_times[-50:])  # Last 50 operations
            older_avg = statistics.mean(serialize_times[:50])   # First 50 operations

            if recent_avg > older_avg * (1 + self._optimization_threshold):
                self._logger.warning(
                    f"Performance degradation detected for {self._serializer_id}: "
                    f"{recent_avg*1000:.2f}ms vs {older_avg*1000:.2f}ms"
                )

                # Trigger optimization suggestions
                self._suggest_optimizations(metrics)

    def _suggest_optimizations(self, metrics: SerializationMetrics) -> None:
        """Suggest performance optimizations."""
        suggestions = []

        if metrics.avg_serialization_time > 0.010:  # > 10ms
            suggestions.append("Consider using binary serialization for better performance")

        if metrics.avg_compression_ratio < 1.5 and hasattr(self._base_serializer, '_compression_type'):
            suggestions.append("Compression ratio is low, consider different compression algorithm")

        if metrics.error_rate > 0.01:  # > 1%
            suggestions.append("High error rate detected, check data validation")

        if suggestions:
            self._logger.info(f"Optimization suggestions for {self._serializer_id}: {suggestions}")


class BatchSerializer:
    """High-performance batch serialization for multiple data items."""

    def __init__(self, base_serializer: SerializerInterface,
                 batch_size: int = 100,
                 monitor: Optional[PerformanceMonitor] = None):
        self._base_serializer = base_serializer
        self._batch_size = batch_size
        self._monitor = monitor or PerformanceMonitor()
        self._batch_buffer: List[Any] = []
        self._serializer_id = f"batch_{base_serializer.__class__.__name__}_{id(self)}"

    def add_to_batch(self, data: Any) -> Optional[List[bytes]]:
        """Add data to batch and return serialized batch if full."""
        self._batch_buffer.append(data)

        if len(self._batch_buffer) >= self._batch_size:
            return self.flush_batch()

        return None

    def flush_batch(self) -> List[bytes]:
        """Serialize and return all items in current batch."""
        if not self._batch_buffer:
            return []

        start_time = time.perf_counter()
        results = []
        total_size = 0

        try:
            for item in self._batch_buffer:
                serialized = self._base_serializer.serialize(item)
                results.append(serialized)
                total_size += len(serialized)

            duration = time.perf_counter() - start_time
            self._monitor.record_operation(
                self._serializer_id, 'batch_serialize', duration, total_size, True
            )

            return results

        except Exception as e:
            duration = time.perf_counter() - start_time
            self._monitor.record_operation(
                self._serializer_id, 'batch_serialize', duration, 0, False, type(e).__name__
            )
            raise

        finally:
            self._batch_buffer.clear()

    def get_batch_metrics(self) -> SerializationMetrics:
        """Get batch processing metrics."""
        return self._monitor.get_metrics(self._serializer_id)


# Global performance monitor instance
_global_monitor = PerformanceMonitor()


def get_global_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    return _global_monitor


def create_performance_serializer(base_serializer: SerializerInterface,
                                 monitor: Optional[PerformanceMonitor] = None) -> PerformanceSerializer:
    """Create performance-aware serializer wrapper."""
    return PerformanceSerializer(base_serializer, monitor or _global_monitor)


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary for all monitored serializers."""
    return _global_monitor.get_summary()