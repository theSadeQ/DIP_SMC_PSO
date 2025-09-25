#==========================================================================================\\\
#================== src/interfaces/monitoring/metrics_collector.py =====================\\\
#==========================================================================================\\\
"""
Comprehensive metrics collection system for interface monitoring.
This module provides efficient collection, aggregation, and storage
of various metrics including performance counters, resource usage,
business metrics, and custom measurements across all interface
components.
"""

import time
import threading
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Callable, Iterator
from enum import Enum
from collections import defaultdict, deque
import logging


class MetricType(Enum):
    """Metric type enumeration."""
    COUNTER = "counter"          # Monotonically increasing value
    GAUGE = "gauge"             # Current value that can go up or down
    HISTOGRAM = "histogram"     # Distribution of values
    SUMMARY = "summary"         # Summary statistics
    TIMER = "timer"            # Duration measurements
    RATE = "rate"              # Rate of change


class AggregationType(Enum):
    """Metric aggregation type."""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    P95 = "p95"
    P99 = "p99"
    STDDEV = "stddev"


@dataclass
class MetricValue:
    """Individual metric value with timestamp."""
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition and storage."""
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    # Value storage
    values: deque = field(default_factory=lambda: deque(maxlen=10000))

    # Aggregated values
    current_value: Optional[Union[int, float]] = None
    total_value: Union[int, float] = 0.0
    count: int = 0
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None

    # Timing
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # Configuration
    retention_window: float = 3600.0  # 1 hour
    alert_thresholds: Dict[str, float] = field(default_factory=dict)

    def add_value(self, value: Union[int, float], tags: Optional[Dict[str, str]] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add new value to metric."""
        metric_value = MetricValue(
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )

        self.values.append(metric_value)
        self.last_updated = time.time()
        self.count += 1

        # Update aggregated values based on metric type
        if self.metric_type == MetricType.COUNTER:
            self.total_value += value
            self.current_value = self.total_value
        elif self.metric_type == MetricType.GAUGE:
            self.current_value = value
        elif self.metric_type in [MetricType.HISTOGRAM, MetricType.SUMMARY, MetricType.TIMER]:
            self.current_value = value
            self.total_value += value
        elif self.metric_type == MetricType.RATE:
            self.current_value = value

        # Update min/max
        if self.min_value is None or value < self.min_value:
            self.min_value = value
        if self.max_value is None or value > self.max_value:
            self.max_value = value

    def get_current_value(self) -> Optional[Union[int, float]]:
        """Get current metric value."""
        return self.current_value

    def get_aggregated_value(self, aggregation: AggregationType,
                           window_seconds: Optional[float] = None) -> Optional[float]:
        """Get aggregated value over specified window."""
        if not self.values:
            return None

        # Filter values by time window if specified
        if window_seconds:
            cutoff_time = time.time() - window_seconds
            recent_values = [v.value for v in self.values if v.timestamp >= cutoff_time]
        else:
            recent_values = [v.value for v in self.values]

        if not recent_values:
            return None

        if aggregation == AggregationType.SUM:
            return sum(recent_values)
        elif aggregation == AggregationType.AVERAGE:
            return statistics.mean(recent_values)
        elif aggregation == AggregationType.MIN:
            return min(recent_values)
        elif aggregation == AggregationType.MAX:
            return max(recent_values)
        elif aggregation == AggregationType.COUNT:
            return len(recent_values)
        elif aggregation == AggregationType.MEDIAN:
            return statistics.median(recent_values)
        elif aggregation == AggregationType.P95:
            return self._percentile(recent_values, 0.95)
        elif aggregation == AggregationType.P99:
            return self._percentile(recent_values, 0.99)
        elif aggregation == AggregationType.STDDEV:
            return statistics.stdev(recent_values) if len(recent_values) > 1 else 0.0
        else:
            return None

    def get_rate(self, window_seconds: float = 60.0) -> Optional[float]:
        """Calculate rate of change over time window."""
        if len(self.values) < 2:
            return None

        cutoff_time = time.time() - window_seconds
        recent_values = [(v.timestamp, v.value) for v in self.values if v.timestamp >= cutoff_time]

        if len(recent_values) < 2:
            return None

        # Sort by timestamp
        recent_values.sort(key=lambda x: x[0])

        # Calculate rate
        time_diff = recent_values[-1][0] - recent_values[0][0]
        if time_diff <= 0:
            return None

        if self.metric_type == MetricType.COUNTER:
            # For counters, rate is the difference divided by time
            value_diff = recent_values[-1][1] - recent_values[0][1]
            return value_diff / time_diff
        else:
            # For other types, calculate average rate of change
            total_change = sum(abs(recent_values[i][1] - recent_values[i-1][1])
                             for i in range(1, len(recent_values)))
            return total_change / time_diff

    def clean_old_values(self) -> None:
        """Remove values outside retention window."""
        if not self.retention_window:
            return

        cutoff_time = time.time() - self.retention_window

        # Remove old values
        while self.values and self.values[0].timestamp < cutoff_time:
            self.values.popleft()

    def get_histogram_buckets(self, bucket_count: int = 10) -> Dict[str, int]:
        """Get histogram distribution of values."""
        if not self.values:
            return {}

        values = [v.value for v in self.values]
        min_val, max_val = min(values), max(values)

        if min_val == max_val:
            return {str(min_val): len(values)}

        bucket_size = (max_val - min_val) / bucket_count
        buckets = defaultdict(int)

        for value in values:
            bucket_index = min(int((value - min_val) / bucket_size), bucket_count - 1)
            bucket_start = min_val + bucket_index * bucket_size
            bucket_end = bucket_start + bucket_size
            bucket_key = f"{bucket_start:.2f}-{bucket_end:.2f}"
            buckets[bucket_key] += 1

        return dict(buckets)

    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(percentile * (len(sorted_values) - 1))
        return sorted_values[index]


class MetricsCollector:
    """Main metrics collection and management system."""

    def __init__(self, retention_window: float = 3600.0):
        self._metrics: Dict[str, Metric] = {}
        self._retention_window = retention_window
        self._lock = threading.RLock()
        self._collectors: List[Callable[[], Dict[str, Any]]] = []
        self._cleanup_interval = 300.0  # 5 minutes
        self._last_cleanup = time.time()
        self._logger = logging.getLogger("metrics_collector")

    def create_metric(self, name: str, metric_type: MetricType,
                     description: str = "", unit: str = "",
                     tags: Optional[Dict[str, str]] = None) -> Metric:
        """Create new metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]

            metric = Metric(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                tags=tags or {},
                retention_window=self._retention_window
            )

            self._metrics[name] = metric
            self._logger.debug(f"Created metric: {name} ({metric_type.value})")
            return metric

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def increment_counter(self, name: str, value: Union[int, float] = 1,
                         tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.COUNTER)
            metric.add_value(value, tags)

    def set_gauge(self, name: str, value: Union[int, float],
                  tags: Optional[Dict[str, str]] = None) -> None:
        """Set gauge metric value."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.GAUGE)
            metric.add_value(value, tags)

    def record_histogram(self, name: str, value: Union[int, float],
                        tags: Optional[Dict[str, str]] = None) -> None:
        """Record histogram value."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.HISTOGRAM)
            metric.add_value(value, tags)

    def record_timer(self, name: str, duration: float,
                    tags: Optional[Dict[str, str]] = None) -> None:
        """Record timer duration."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.TIMER)
            metric.add_value(duration, tags)

    def record_rate(self, name: str, rate: float,
                   tags: Optional[Dict[str, str]] = None) -> None:
        """Record rate metric."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.RATE)
            metric.add_value(rate, tags)

    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics."""
        with self._lock:
            self._cleanup_if_needed()
            return dict(self._metrics)

    def get_metrics_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all metrics."""
        with self._lock:
            self._cleanup_if_needed()
            summary = {}

            for name, metric in self._metrics.items():
                summary[name] = {
                    'type': metric.metric_type.value,
                    'description': metric.description,
                    'unit': metric.unit,
                    'current_value': metric.get_current_value(),
                    'count': metric.count,
                    'min': metric.min_value,
                    'max': metric.max_value,
                    'avg': metric.get_aggregated_value(AggregationType.AVERAGE),
                    'last_updated': metric.last_updated,
                    'tags': metric.tags
                }

            return summary

    def add_collector(self, collector: Callable[[], Dict[str, Any]]) -> None:
        """Add metrics collector function."""
        self._collectors.append(collector)

    def collect_all(self) -> None:
        """Run all registered collectors."""
        for collector in self._collectors:
            try:
                metrics_data = collector()
                for name, value in metrics_data.items():
                    if isinstance(value, dict):
                        metric_type = MetricType(value.get('type', 'gauge'))
                        metric_value = value.get('value', 0)
                        tags = value.get('tags', {})
                        self._record_metric_value(name, metric_type, metric_value, tags)
                    else:
                        self.set_gauge(name, value)
            except Exception as e:
                self._logger.error(f"Error in metrics collector: {e}")

    def export_metrics(self, format_type: str = "prometheus") -> str:
        """Export metrics in specified format."""
        if format_type == "prometheus":
            return self._export_prometheus_format()
        elif format_type == "json":
            import json
            return json.dumps(self.get_metrics_summary(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def reset_metric(self, name: str) -> bool:
        """Reset metric values."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                metric.values.clear()
                metric.current_value = None
                metric.total_value = 0.0
                metric.count = 0
                metric.min_value = None
                metric.max_value = None
                return True
            return False

    def delete_metric(self, name: str) -> bool:
        """Delete metric."""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                return True
            return False

    def _get_or_create_metric(self, name: str, metric_type: MetricType) -> Metric:
        """Get existing metric or create new one."""
        if name not in self._metrics:
            return self.create_metric(name, metric_type)
        return self._metrics[name]

    def _record_metric_value(self, name: str, metric_type: MetricType,
                           value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Record metric value with appropriate method."""
        if metric_type == MetricType.COUNTER:
            self.increment_counter(name, value, tags)
        elif metric_type == MetricType.GAUGE:
            self.set_gauge(name, value, tags)
        elif metric_type == MetricType.HISTOGRAM:
            self.record_histogram(name, value, tags)
        elif metric_type == MetricType.TIMER:
            self.record_timer(name, value, tags)
        elif metric_type == MetricType.RATE:
            self.record_rate(name, value, tags)

    def _cleanup_if_needed(self) -> None:
        """Clean up old metric values if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            for metric in self._metrics.values():
                metric.clean_old_values()
            self._last_cleanup = current_time

    def _export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        for name, metric in self._metrics.items():
            # Add metric help
            if metric.description:
                lines.append(f"# HELP {name} {metric.description}")

            # Add metric type
            prom_type = {
                MetricType.COUNTER: "counter",
                MetricType.GAUGE: "gauge",
                MetricType.HISTOGRAM: "histogram",
                MetricType.SUMMARY: "summary",
                MetricType.TIMER: "histogram",
                MetricType.RATE: "gauge"
            }.get(metric.metric_type, "gauge")

            lines.append(f"# TYPE {name} {prom_type}")

            # Add current value
            current_value = metric.get_current_value()
            if current_value is not None:
                tags_str = ""
                if metric.tags:
                    tag_pairs = [f'{k}="{v}"' for k, v in metric.tags.items()]
                    tags_str = "{" + ",".join(tag_pairs) + "}"

                lines.append(f"{name}{tags_str} {current_value}")

        return "\n".join(lines)


class SystemMetricsCollector:
    """System-level metrics collector for system resources."""

    def __init__(self, collector: MetricsCollector):
        self._collector = collector
        self._enabled = True
        self._collection_interval = 30.0  # 30 seconds
        self._collection_task = None
        self._logger = logging.getLogger("system_metrics_collector")

    async def start_collection(self) -> None:
        """Start automatic system metrics collection."""
        if self._collection_task:
            return

        import asyncio
        self._collection_task = asyncio.create_task(self._collection_loop())
        self._logger.info("Started system metrics collection")

    async def stop_collection(self) -> None:
        """Stop automatic system metrics collection."""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            self._collection_task = None
            self._logger.info("Stopped system metrics collection")

    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system metrics."""
        metrics = {}

        try:
            import psutil

            # CPU metrics
            metrics['system_cpu_percent'] = psutil.cpu_percent(interval=None)
            metrics['system_cpu_count'] = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics['system_memory_total'] = memory.total
            metrics['system_memory_used'] = memory.used
            metrics['system_memory_percent'] = memory.percent
            metrics['system_memory_available'] = memory.available

            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['system_disk_total'] = disk.total
            metrics['system_disk_used'] = disk.used
            metrics['system_disk_percent'] = (disk.used / disk.total) * 100

            # Network metrics
            network = psutil.net_io_counters()
            if network:
                metrics['system_network_bytes_sent'] = network.bytes_sent
                metrics['system_network_bytes_recv'] = network.bytes_recv
                metrics['system_network_packets_sent'] = network.packets_sent
                metrics['system_network_packets_recv'] = network.packets_recv

            # Process metrics
            process = psutil.Process()
            metrics['process_cpu_percent'] = process.cpu_percent()
            metrics['process_memory_rss'] = process.memory_info().rss
            metrics['process_memory_vms'] = process.memory_info().vms
            metrics['process_num_threads'] = process.num_threads()

        except ImportError:
            self._logger.warning("psutil not available, system metrics collection disabled")
        except Exception as e:
            self._logger.error(f"Error collecting system metrics: {e}")

        return metrics

    async def _collection_loop(self) -> None:
        """Main collection loop."""
        import asyncio

        while self._enabled:
            try:
                metrics = self.collect_system_metrics()

                # Record all metrics
                for name, value in metrics.items():
                    if name.startswith('system_'):
                        self._collector.set_gauge(name, value, {'source': 'system'})
                    elif name.startswith('process_'):
                        self._collector.set_gauge(name, value, {'source': 'process'})

                await asyncio.sleep(self._collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(self._collection_interval)


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, metric_name: str,
                 tags: Optional[Dict[str, str]] = None):
        self._collector = collector
        self._metric_name = metric_name
        self._tags = tags
        self._start_time = None

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start_time is not None:
            duration = time.perf_counter() - self._start_time
            self._collector.record_timer(self._metric_name, duration, self._tags)


# Factory functions and utilities
def create_metric(name: str, metric_type: MetricType, description: str = "",
                 unit: str = "", tags: Optional[Dict[str, str]] = None) -> Metric:
    """Create a metric instance."""
    return Metric(
        name=name,
        metric_type=metric_type,
        description=description,
        unit=unit,
        tags=tags or {}
    )


def timer(collector: MetricsCollector, metric_name: str,
          tags: Optional[Dict[str, str]] = None) -> TimerContext:
    """Create timer context manager."""
    return TimerContext(collector, metric_name, tags)


# Decorator for timing functions
def timed_function(collector: MetricsCollector, metric_name: Optional[str] = None,
                  tags: Optional[Dict[str, str]] = None):
    """Decorator to time function execution."""
    def decorator(func):
        nonlocal metric_name
        if metric_name is None:
            metric_name = f"function_{func.__name__}_duration"

        def wrapper(*args, **kwargs):
            with timer(collector, metric_name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator