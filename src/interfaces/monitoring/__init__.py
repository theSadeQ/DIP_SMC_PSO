#==========================================================================================\\\
#========================= src/interfaces/monitoring/__init__.py ========================\\\
#==========================================================================================\\\
"""
Comprehensive monitoring and diagnostics system for the interfaces framework.
This module provides real-time monitoring, health checks, performance metrics,
system diagnostics, alerting, and dashboard capabilities for all interface
components including network communication, hardware devices, and HIL systems.
"""

from .health_monitor import (
    HealthStatus, HealthCheck, ComponentHealth,
    HealthMonitor, SystemHealthMonitor
)
from .metrics_collector import (
    MetricType, Metric, MetricsCollector,
    SystemMetricsCollector, create_metric
)
from .performance_tracker import (
    PerformanceTracker, PerformanceMetrics,
    ResourceMonitor, LatencyTracker
)
from .diagnostics import (
    DiagnosticLevel, DiagnosticResult, DiagnosticTest,
    SystemDiagnostics, ComponentDiagnostics
)
from .alerting import (
    AlertLevel, Alert, AlertRule, AlertManager,
    NotificationChannel, EmailNotifier, LogNotifier
)
from .dashboard import (
    DashboardConfig, MonitoringDashboard,
    MetricWidget, HealthWidget, AlertWidget
)
from .system_monitor import (
    SystemMonitor, MonitoringConfig,
    InterfaceSystemMonitor
)

__all__ = [
    # Health monitoring
    'HealthStatus', 'HealthCheck', 'ComponentHealth',
    'HealthMonitor', 'SystemHealthMonitor',

    # Metrics collection
    'MetricType', 'Metric', 'MetricsCollector',
    'SystemMetricsCollector', 'create_metric',

    # Performance tracking
    'PerformanceTracker', 'PerformanceMetrics',
    'ResourceMonitor', 'LatencyTracker',

    # Diagnostics
    'DiagnosticLevel', 'DiagnosticResult', 'DiagnosticTest',
    'SystemDiagnostics', 'ComponentDiagnostics',

    # Alerting
    'AlertLevel', 'Alert', 'AlertRule', 'AlertManager',
    'NotificationChannel', 'EmailNotifier', 'LogNotifier',

    # Dashboard
    'DashboardConfig', 'MonitoringDashboard',
    'MetricWidget', 'HealthWidget', 'AlertWidget',

    # System monitoring
    'SystemMonitor', 'MonitoringConfig',
    'InterfaceSystemMonitor'
]