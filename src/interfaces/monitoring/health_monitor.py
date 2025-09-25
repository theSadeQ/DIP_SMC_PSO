#==========================================================================================\\\
#=================== src/interfaces/monitoring/health_monitor.py =======================\\\
#==========================================================================================\\\
"""
Health monitoring system for interface components.
This module provides comprehensive health checking capabilities
for monitoring the status and operational health of all
interface components including network connections, hardware
devices, and system services.
"""

import asyncio
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
import logging


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class CheckResult(Enum):
    """Health check result enumeration."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class HealthCheck:
    """Individual health check definition."""
    name: str
    description: str = ""
    check_function: Optional[Callable[[], bool]] = None
    async_check_function: Optional[Callable[[], bool]] = None
    interval: float = 30.0  # seconds
    timeout: float = 5.0   # seconds
    critical: bool = False
    enabled: bool = True
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Retry configuration
    retry_count: int = 1
    retry_delay: float = 1.0

    def __post_init__(self):
        if not self.check_function and not self.async_check_function:
            raise ValueError("Either check_function or async_check_function must be provided")


@dataclass
class HealthCheckResult:
    """Result of a health check execution."""
    check_name: str
    result: CheckResult
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    message: str = ""
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    retry_attempt: int = 0

    @property
    def is_healthy(self) -> bool:
        return self.result == CheckResult.PASS

    @property
    def is_critical_failure(self) -> bool:
        return self.result == CheckResult.FAIL


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    component_name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: float = field(default_factory=time.time)
    uptime: float = 0.0
    check_results: List[HealthCheckResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def update_status(self, new_status: HealthStatus) -> None:
        """Update component health status."""
        if self.status != new_status:
            self.status = new_status
            self.last_check = time.time()

    def add_check_result(self, result: HealthCheckResult, max_history: int = 100) -> None:
        """Add health check result and maintain history."""
        self.check_results.append(result)
        self.last_check = time.time()

        # Maintain limited history
        if len(self.check_results) > max_history:
            self.check_results = self.check_results[-max_history:]

        # Update overall status based on recent results
        self._update_overall_status()

    def _update_overall_status(self) -> None:
        """Update overall status based on recent check results."""
        if not self.check_results:
            self.status = HealthStatus.UNKNOWN
            return

        recent_results = self.check_results[-10:]  # Last 10 checks

        # Count result types
        pass_count = sum(1 for r in recent_results if r.result == CheckResult.PASS)
        fail_count = sum(1 for r in recent_results if r.result == CheckResult.FAIL)
        warn_count = sum(1 for r in recent_results if r.result == CheckResult.WARN)

        total_checks = len(recent_results)

        # Determine status
        if fail_count > 0:
            if fail_count / total_checks >= 0.5:  # 50% or more failures
                self.status = HealthStatus.CRITICAL
            else:
                self.status = HealthStatus.DEGRADED
        elif warn_count > 0:
            if warn_count / total_checks >= 0.3:  # 30% or more warnings
                self.status = HealthStatus.WARNING
            else:
                self.status = HealthStatus.HEALTHY
        elif pass_count == total_checks:
            self.status = HealthStatus.HEALTHY
        else:
            self.status = HealthStatus.UNKNOWN

    def get_success_rate(self, window_size: int = 10) -> float:
        """Get success rate for recent checks."""
        if not self.check_results:
            return 0.0

        recent_results = self.check_results[-window_size:]
        pass_count = sum(1 for r in recent_results if r.result == CheckResult.PASS)
        return pass_count / len(recent_results)

    def get_average_response_time(self, window_size: int = 10) -> float:
        """Get average response time for recent checks."""
        if not self.check_results:
            return 0.0

        recent_results = self.check_results[-window_size:]
        total_duration = sum(r.duration for r in recent_results)
        return total_duration / len(recent_results)


class HealthMonitor:
    """Health monitor for individual components."""

    def __init__(self, component_name: str):
        self._component_name = component_name
        self._health_checks: Dict[str, HealthCheck] = {}
        self._component_health = ComponentHealth(component_name)
        self._running = False
        self._check_tasks: Dict[str, asyncio.Task] = {}
        self._lock = threading.RLock()
        self._status_change_handlers: List[Callable[[ComponentHealth], None]] = []
        self._logger = logging.getLogger(f"health_monitor_{component_name}")

    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add health check to monitor."""
        with self._lock:
            self._health_checks[health_check.name] = health_check
            self._logger.info(f"Added health check: {health_check.name}")

    def remove_health_check(self, check_name: str) -> bool:
        """Remove health check from monitor."""
        with self._lock:
            if check_name in self._health_checks:
                del self._health_checks[check_name]

                # Cancel running task if exists
                if check_name in self._check_tasks:
                    self._check_tasks[check_name].cancel()
                    del self._check_tasks[check_name]

                self._logger.info(f"Removed health check: {check_name}")
                return True
            return False

    def enable_check(self, check_name: str) -> bool:
        """Enable a health check."""
        with self._lock:
            if check_name in self._health_checks:
                self._health_checks[check_name].enabled = True
                return True
            return False

    def disable_check(self, check_name: str) -> bool:
        """Disable a health check."""
        with self._lock:
            if check_name in self._health_checks:
                self._health_checks[check_name].enabled = False

                # Cancel running task
                if check_name in self._check_tasks:
                    self._check_tasks[check_name].cancel()
                    del self._check_tasks[check_name]

                return True
            return False

    async def start_monitoring(self) -> bool:
        """Start health monitoring."""
        if self._running:
            return False

        try:
            self._running = True

            # Start check tasks for all enabled checks
            for check_name, health_check in self._health_checks.items():
                if health_check.enabled:
                    task = asyncio.create_task(self._run_health_check_loop(health_check))
                    self._check_tasks[check_name] = task

            self._logger.info(f"Started health monitoring for {self._component_name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start health monitoring: {e}")
            self._running = False
            return False

    async def stop_monitoring(self) -> bool:
        """Stop health monitoring."""
        if not self._running:
            return True

        try:
            self._running = False

            # Cancel all check tasks
            for task in self._check_tasks.values():
                task.cancel()

            # Wait for tasks to complete
            if self._check_tasks:
                await asyncio.gather(*self._check_tasks.values(), return_exceptions=True)

            self._check_tasks.clear()
            self._logger.info(f"Stopped health monitoring for {self._component_name}")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping health monitoring: {e}")
            return False

    async def run_single_check(self, check_name: str) -> Optional[HealthCheckResult]:
        """Run a single health check immediately."""
        with self._lock:
            if check_name not in self._health_checks:
                return None

            health_check = self._health_checks[check_name]

        return await self._execute_health_check(health_check)

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks immediately."""
        results = {}

        with self._lock:
            checks_to_run = list(self._health_checks.items())

        for check_name, health_check in checks_to_run:
            if health_check.enabled:
                result = await self._execute_health_check(health_check)
                if result:
                    results[check_name] = result

        return results

    def get_component_health(self) -> ComponentHealth:
        """Get current component health status."""
        with self._lock:
            return self._component_health

    def add_status_change_handler(self, handler: Callable[[ComponentHealth], None]) -> None:
        """Add handler for status changes."""
        self._status_change_handlers.append(handler)

    def update_component_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update component metrics."""
        with self._lock:
            self._component_health.metrics.update(metrics)

    async def _run_health_check_loop(self, health_check: HealthCheck) -> None:
        """Run health check in a loop with specified interval."""
        while self._running:
            try:
                if health_check.enabled:
                    result = await self._execute_health_check(health_check)
                    if result:
                        self._process_check_result(result, health_check)

                # Wait for next interval
                await asyncio.sleep(health_check.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in health check loop for {health_check.name}: {e}")
                await asyncio.sleep(health_check.interval)  # Continue after error

    async def _execute_health_check(self, health_check: HealthCheck) -> Optional[HealthCheckResult]:
        """Execute a single health check with retry logic."""
        for attempt in range(health_check.retry_count + 1):
            start_time = time.perf_counter()
            result = None

            try:
                # Execute check with timeout
                if health_check.async_check_function:
                    check_result = await asyncio.wait_for(
                        health_check.async_check_function(),
                        timeout=health_check.timeout
                    )
                else:
                    # Run sync function in thread pool
                    check_result = await asyncio.get_event_loop().run_in_executor(
                        None, health_check.check_function
                    )

                duration = time.perf_counter() - start_time

                # Create result
                result = HealthCheckResult(
                    check_name=health_check.name,
                    result=CheckResult.PASS if check_result else CheckResult.FAIL,
                    duration=duration,
                    message="Check passed" if check_result else "Check failed",
                    retry_attempt=attempt
                )

                # If successful or on last attempt, return result
                if check_result or attempt == health_check.retry_count:
                    return result

            except asyncio.TimeoutError:
                duration = time.perf_counter() - start_time
                result = HealthCheckResult(
                    check_name=health_check.name,
                    result=CheckResult.FAIL,
                    duration=duration,
                    message=f"Check timed out after {health_check.timeout}s",
                    error="timeout",
                    retry_attempt=attempt
                )

            except Exception as e:
                duration = time.perf_counter() - start_time
                result = HealthCheckResult(
                    check_name=health_check.name,
                    result=CheckResult.FAIL,
                    duration=duration,
                    message=f"Check failed with error: {e}",
                    error=str(e),
                    retry_attempt=attempt
                )

            # If this was the last retry attempt, return the result
            if attempt == health_check.retry_count:
                return result

            # Wait before retry
            if health_check.retry_delay > 0:
                await asyncio.sleep(health_check.retry_delay)

        return result

    def _process_check_result(self, result: HealthCheckResult, health_check: HealthCheck) -> None:
        """Process health check result and update component status."""
        with self._lock:
            previous_status = self._component_health.status

            # Add result to component health
            self._component_health.add_check_result(result)

            # Check if status changed
            if self._component_health.status != previous_status:
                self._logger.info(
                    f"Health status changed for {self._component_name}: "
                    f"{previous_status.value} -> {self._component_health.status.value}"
                )

                # Notify status change handlers
                for handler in self._status_change_handlers:
                    try:
                        handler(self._component_health)
                    except Exception as e:
                        self._logger.error(f"Error in status change handler: {e}")


class SystemHealthMonitor:
    """System-wide health monitor coordinating multiple component monitors."""

    def __init__(self):
        self._component_monitors: Dict[str, HealthMonitor] = {}
        self._running = False
        self._system_health_handlers: List[Callable[[Dict[str, ComponentHealth]], None]] = []
        self._lock = threading.RLock()
        self._logger = logging.getLogger("system_health_monitor")

    def add_component_monitor(self, monitor: HealthMonitor) -> None:
        """Add component monitor to system."""
        with self._lock:
            component_name = monitor._component_name
            self._component_monitors[component_name] = monitor

            # Add status change handler
            monitor.add_status_change_handler(self._on_component_status_change)

            self._logger.info(f"Added component monitor: {component_name}")

    def remove_component_monitor(self, component_name: str) -> bool:
        """Remove component monitor from system."""
        with self._lock:
            if component_name in self._component_monitors:
                monitor = self._component_monitors[component_name]

                # Stop monitoring if running
                if self._running:
                    asyncio.create_task(monitor.stop_monitoring())

                del self._component_monitors[component_name]
                self._logger.info(f"Removed component monitor: {component_name}")
                return True
            return False

    async def start_system_monitoring(self) -> bool:
        """Start monitoring all components."""
        if self._running:
            return False

        try:
            self._running = True

            # Start all component monitors
            start_tasks = []
            for monitor in self._component_monitors.values():
                start_tasks.append(monitor.start_monitoring())

            results = await asyncio.gather(*start_tasks, return_exceptions=True)

            # Check if all monitors started successfully
            success_count = sum(1 for result in results if result is True)

            self._logger.info(
                f"Started system health monitoring: {success_count}/{len(results)} "
                f"component monitors started successfully"
            )

            return success_count > 0

        except Exception as e:
            self._logger.error(f"Failed to start system health monitoring: {e}")
            self._running = False
            return False

    async def stop_system_monitoring(self) -> bool:
        """Stop monitoring all components."""
        if not self._running:
            return True

        try:
            self._running = False

            # Stop all component monitors
            stop_tasks = []
            for monitor in self._component_monitors.values():
                stop_tasks.append(monitor.stop_monitoring())

            await asyncio.gather(*stop_tasks, return_exceptions=True)

            self._logger.info("Stopped system health monitoring")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping system health monitoring: {e}")
            return False

    def get_system_health(self) -> Dict[str, ComponentHealth]:
        """Get health status of all components."""
        with self._lock:
            system_health = {}
            for component_name, monitor in self._component_monitors.items():
                system_health[component_name] = monitor.get_component_health()
            return system_health

    def get_overall_system_status(self) -> HealthStatus:
        """Get overall system health status."""
        component_healths = self.get_system_health()

        if not component_healths:
            return HealthStatus.UNKNOWN

        # Aggregate component statuses
        critical_count = sum(1 for h in component_healths.values() if h.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for h in component_healths.values() if h.status == HealthStatus.WARNING)
        degraded_count = sum(1 for h in component_healths.values() if h.status == HealthStatus.DEGRADED)
        healthy_count = sum(1 for h in component_healths.values() if h.status == HealthStatus.HEALTHY)

        total_components = len(component_healths)

        # Determine overall status
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        elif warning_count > 0:
            return HealthStatus.WARNING
        elif healthy_count == total_components:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def add_system_health_handler(self, handler: Callable[[Dict[str, ComponentHealth]], None]) -> None:
        """Add handler for system health changes."""
        self._system_health_handlers.append(handler)

    async def run_system_health_check(self) -> Dict[str, Dict[str, HealthCheckResult]]:
        """Run health checks for all components."""
        results = {}

        check_tasks = []
        component_names = []

        with self._lock:
            for component_name, monitor in self._component_monitors.items():
                check_tasks.append(monitor.run_all_checks())
                component_names.append(component_name)

        if check_tasks:
            component_results = await asyncio.gather(*check_tasks, return_exceptions=True)

            for component_name, result in zip(component_names, component_results):
                if isinstance(result, dict):
                    results[component_name] = result
                else:
                    self._logger.error(f"Error running checks for {component_name}: {result}")

        return results

    def _on_component_status_change(self, component_health: ComponentHealth) -> None:
        """Handle component status change."""
        self._logger.info(
            f"Component status change: {component_health.component_name} "
            f"-> {component_health.status.value}"
        )

        # Notify system health handlers
        system_health = self.get_system_health()
        for handler in self._system_health_handlers:
            try:
                handler(system_health)
            except Exception as e:
                self._logger.error(f"Error in system health handler: {e}")


# Factory functions for common health checks
def create_ping_check(name: str, host: str, timeout: float = 5.0, interval: float = 30.0) -> HealthCheck:
    """Create network ping health check."""
    import subprocess
    import platform

    def ping_host() -> bool:
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", host]
            result = subprocess.run(command, capture_output=True, timeout=timeout)
            return result.returncode == 0
        except Exception:
            return False

    return HealthCheck(
        name=name,
        description=f"Ping connectivity to {host}",
        check_function=ping_host,
        interval=interval,
        timeout=timeout,
        tags={"network", "connectivity"}
    )


def create_port_check(name: str, host: str, port: int, timeout: float = 5.0, interval: float = 30.0) -> HealthCheck:
    """Create TCP port connectivity health check."""
    import socket

    def check_port() -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    return HealthCheck(
        name=name,
        description=f"TCP connectivity to {host}:{port}",
        check_function=check_port,
        interval=interval,
        timeout=timeout,
        tags={"network", "port", "tcp"}
    )


def create_memory_check(name: str, threshold_percent: float = 90.0, interval: float = 60.0) -> HealthCheck:
    """Create memory usage health check."""
    import psutil

    def check_memory() -> bool:
        try:
            memory = psutil.virtual_memory()
            return memory.percent < threshold_percent
        except Exception:
            return False

    return HealthCheck(
        name=name,
        description=f"Memory usage below {threshold_percent}%",
        check_function=check_memory,
        interval=interval,
        tags={"system", "memory", "resources"}
    )


def create_disk_check(name: str, path: str = "/", threshold_percent: float = 90.0, interval: float = 60.0) -> HealthCheck:
    """Create disk usage health check."""
    import psutil

    def check_disk() -> bool:
        try:
            disk = psutil.disk_usage(path)
            usage_percent = (disk.used / disk.total) * 100
            return usage_percent < threshold_percent
        except Exception:
            return False

    return HealthCheck(
        name=name,
        description=f"Disk usage for {path} below {threshold_percent}%",
        check_function=check_disk,
        interval=interval,
        tags={"system", "disk", "storage"}
    )