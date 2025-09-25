#==========================================================================================\\\
#===================== src/interfaces/hil/real_time_sync.py =============================\\\
#==========================================================================================\\\
"""
Real-time synchronization and scheduling for HIL systems.
This module provides real-time capabilities including high-priority scheduling,
deadline monitoring, and timing constraint enforcement for deterministic
control system execution.
"""

import asyncio
import time
import threading
import os
import signal
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Dict, Any
from enum import Enum
import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    # Linux-specific real-time capabilities
    import ctypes
    import ctypes.util
    RT_AVAILABLE = os.name == 'posix'
except ImportError:
    RT_AVAILABLE = False


class SchedulingPolicy(Enum):
    """Real-time scheduling policy enumeration."""
    SCHED_FIFO = "fifo"
    SCHED_RR = "round_robin"
    SCHED_DEADLINE = "deadline"
    SCHED_OTHER = "other"


class TimingViolationType(Enum):
    """Timing violation type enumeration."""
    DEADLINE_MISS = "deadline_miss"
    JITTER_EXCEED = "jitter_exceed"
    OVERRUN = "overrun"
    UNDERRUN = "underrun"


@dataclass
class TimingConstraints:
    """Real-time timing constraints."""
    period: float  # Execution period in seconds
    deadline: Optional[float] = None  # Deadline relative to period start
    jitter_tolerance: float = 0.0001  # Maximum allowed jitter (100μs)
    worst_case_execution_time: Optional[float] = None
    priority: int = 99  # Real-time priority (1-99)
    cpu_affinity: Optional[List[int]] = None


@dataclass
class TimingEvent:
    """Timing event record."""
    timestamp: float
    event_type: str
    violation_type: Optional[TimingViolationType] = None
    actual_time: Optional[float] = None
    expected_time: Optional[float] = None
    deviation: Optional[float] = None


class DeadlineMissHandler:
    """Handler for deadline miss events."""

    def __init__(self):
        self._handlers: List[Callable[[TimingEvent], None]] = []
        self._statistics = {
            'total_deadlines': 0,
            'missed_deadlines': 0,
            'max_overrun': 0.0,
            'avg_overrun': 0.0
        }

    def add_handler(self, handler: Callable[[TimingEvent], None]) -> None:
        """Add deadline miss handler."""
        self._handlers.append(handler)

    def handle_deadline_miss(self, event: TimingEvent) -> None:
        """Handle deadline miss event."""
        self._statistics['missed_deadlines'] += 1

        if event.deviation:
            self._statistics['max_overrun'] = max(
                self._statistics['max_overrun'],
                event.deviation
            )

            # Update average overrun
            missed = self._statistics['missed_deadlines']
            if missed > 1:
                self._statistics['avg_overrun'] = (
                    (self._statistics['avg_overrun'] * (missed - 1) + event.deviation) / missed
                )
            else:
                self._statistics['avg_overrun'] = event.deviation

        # Call registered handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logging.error(f"Error in deadline miss handler: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get deadline miss statistics."""
        stats = self._statistics.copy()
        if stats['total_deadlines'] > 0:
            stats['miss_rate'] = stats['missed_deadlines'] / stats['total_deadlines']
        else:
            stats['miss_rate'] = 0.0
        return stats


class RealTimeScheduler:
    """
    Real-time scheduler for HIL systems.

    Provides deterministic scheduling with deadline monitoring,
    CPU affinity control, and real-time priority management.
    """

    def __init__(self, sample_time: float, priority: int = 99, cpu_affinity: Optional[List[int]] = None):
        """Initialize real-time scheduler."""
        self._sample_time = sample_time
        self._priority = priority
        self._cpu_affinity = cpu_affinity
        self._constraints = TimingConstraints(
            period=sample_time,
            deadline=sample_time * 0.9,  # 90% of period
            priority=priority,
            cpu_affinity=cpu_affinity
        )

        # Timing control
        self._start_time = 0.0
        self._iteration = 0
        self._next_period = 0.0
        self._running = False

        # Monitoring
        self._deadline_handler = DeadlineMissHandler()
        self._timing_events: List[TimingEvent] = []
        self._performance_stats = {
            'iterations': 0,
            'total_jitter': 0.0,
            'max_jitter': 0.0,
            'deadline_misses': 0
        }

        # Real-time setup
        self._original_priority: Optional[int] = None
        self._original_affinity: Optional[List[int]] = None
        self._logger = logging.getLogger("rt_scheduler")

    async def start(self) -> bool:
        """Start real-time scheduler."""
        try:
            self._logger.info("Starting real-time scheduler")

            # Configure real-time properties
            await self._configure_real_time()

            # Initialize timing
            self._start_time = time.time()
            self._next_period = self._start_time + self._sample_time
            self._iteration = 0
            self._running = True

            self._logger.info(f"Real-time scheduler started with {self._sample_time*1000:.2f}ms period")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start real-time scheduler: {e}")
            return False

    async def stop(self) -> bool:
        """Stop real-time scheduler."""
        try:
            self._running = False

            # Restore original settings
            await self._restore_settings()

            self._logger.info("Real-time scheduler stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping real-time scheduler: {e}")
            return False

    async def wait_for_next_period(self) -> bool:
        """Wait for next scheduling period."""
        if not self._running:
            return False

        current_time = time.time()
        period_start = self._start_time + (self._iteration * self._sample_time)

        # Check for deadline miss
        if self._constraints.deadline:
            deadline = period_start + self._constraints.deadline
            if current_time > deadline:
                await self._handle_deadline_miss(current_time, deadline)

        # Calculate sleep time
        sleep_time = self._next_period - current_time

        if sleep_time > 0:
            # Use high-precision sleep
            await self._precise_sleep(sleep_time)
        else:
            # Late arrival - record jitter
            jitter = abs(sleep_time)
            self._record_jitter(jitter)

        # Update for next iteration
        self._iteration += 1
        self._next_period = self._start_time + (self._iteration * self._sample_time)
        self._performance_stats['iterations'] += 1

        return True

    async def set_constraints(self, constraints: TimingConstraints) -> bool:
        """Set timing constraints."""
        try:
            self._constraints = constraints
            self._sample_time = constraints.period

            # Update real-time configuration if running
            if self._running:
                await self._configure_real_time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to set timing constraints: {e}")
            return False

    def get_timing_statistics(self) -> Dict[str, Any]:
        """Get timing performance statistics."""
        stats = self._performance_stats.copy()

        if stats['iterations'] > 0:
            stats['avg_jitter'] = stats['total_jitter'] / stats['iterations']
            stats['deadline_miss_rate'] = stats['deadline_misses'] / stats['iterations']
        else:
            stats['avg_jitter'] = 0.0
            stats['deadline_miss_rate'] = 0.0

        stats.update(self._deadline_handler.get_statistics())
        return stats

    def add_deadline_miss_handler(self, handler: Callable[[TimingEvent], None]) -> None:
        """Add deadline miss handler."""
        self._deadline_handler.add_handler(handler)

    async def _configure_real_time(self) -> None:
        """Configure real-time scheduling properties."""
        try:
            if RT_AVAILABLE and os.name == 'posix':
                await self._configure_linux_rt()
            elif PSUTIL_AVAILABLE:
                await self._configure_psutil_rt()
            else:
                self._logger.warning("Real-time capabilities not available")

        except Exception as e:
            self._logger.warning(f"Failed to configure real-time properties: {e}")

    async def _configure_linux_rt(self) -> None:
        """Configure Linux real-time scheduling."""
        try:
            import os

            # Get current process
            pid = os.getpid()

            # Set CPU affinity if specified
            if self._constraints.cpu_affinity:
                self._original_affinity = list(os.sched_getaffinity(pid))
                os.sched_setaffinity(pid, self._constraints.cpu_affinity)
                self._logger.info(f"Set CPU affinity to {self._constraints.cpu_affinity}")

            # Set real-time priority
            try:
                # Store original priority
                self._original_priority = os.getpriority(os.PRIO_PROCESS, pid)

                # Set FIFO scheduling with high priority
                os.sched_setscheduler(pid, os.SCHED_FIFO, os.sched_param(self._priority))
                self._logger.info(f"Set real-time priority to {self._priority}")

            except PermissionError:
                self._logger.warning("Insufficient permissions for real-time scheduling")
                # Fall back to nice priority
                os.nice(-10)  # Higher priority

        except Exception as e:
            self._logger.warning(f"Linux real-time configuration failed: {e}")

    async def _configure_psutil_rt(self) -> None:
        """Configure real-time properties using psutil."""
        try:
            process = psutil.Process()

            # Set high priority
            if hasattr(psutil, 'HIGH_PRIORITY_CLASS'):
                process.nice(psutil.HIGH_PRIORITY_CLASS)
            else:
                process.nice(-10)  # Unix nice value

            # Set CPU affinity if specified and available
            if self._constraints.cpu_affinity and hasattr(process, 'cpu_affinity'):
                self._original_affinity = process.cpu_affinity()
                process.cpu_affinity(self._constraints.cpu_affinity)

            self._logger.info("Configured high priority using psutil")

        except Exception as e:
            self._logger.warning(f"psutil configuration failed: {e}")

    async def _restore_settings(self) -> None:
        """Restore original scheduling settings."""
        try:
            if RT_AVAILABLE and os.name == 'posix':
                pid = os.getpid()

                # Restore CPU affinity
                if self._original_affinity:
                    os.sched_setaffinity(pid, self._original_affinity)

                # Restore priority and scheduling
                if self._original_priority is not None:
                    try:
                        os.sched_setscheduler(pid, os.SCHED_OTHER, os.sched_param(0))
                        os.setpriority(os.PRIO_PROCESS, pid, self._original_priority)
                    except (OSError, PermissionError):
                        pass

        except Exception as e:
            self._logger.warning(f"Failed to restore settings: {e}")

    async def _precise_sleep(self, sleep_time: float) -> None:
        """High-precision sleep implementation."""
        if sleep_time <= 0:
            return

        # For very short sleeps, use busy waiting for precision
        if sleep_time < 0.001:  # Less than 1ms
            end_time = time.time() + sleep_time
            while time.time() < end_time:
                pass  # Busy wait
        else:
            # Use asyncio sleep for longer periods
            await asyncio.sleep(sleep_time)

    async def _handle_deadline_miss(self, current_time: float, deadline: float) -> None:
        """Handle deadline miss event."""
        overrun = current_time - deadline

        event = TimingEvent(
            timestamp=current_time,
            event_type="deadline_miss",
            violation_type=TimingViolationType.DEADLINE_MISS,
            actual_time=current_time,
            expected_time=deadline,
            deviation=overrun
        )

        self._timing_events.append(event)
        self._performance_stats['deadline_misses'] += 1
        self._deadline_handler.handle_deadline_miss(event)

        # Keep only recent events
        if len(self._timing_events) > 1000:
            self._timing_events.pop(0)

    def _record_jitter(self, jitter: float) -> None:
        """Record timing jitter."""
        self._performance_stats['total_jitter'] += jitter
        self._performance_stats['max_jitter'] = max(
            self._performance_stats['max_jitter'],
            jitter
        )

        # Check jitter tolerance
        if jitter > self._constraints.jitter_tolerance:
            event = TimingEvent(
                timestamp=time.time(),
                event_type="jitter_exceed",
                violation_type=TimingViolationType.JITTER_EXCEED,
                deviation=jitter
            )
            self._timing_events.append(event)


class HighResolutionTimer:
    """High-resolution timer for precise timing control."""

    def __init__(self):
        self._start_time = 0.0

    def start(self) -> None:
        """Start timer."""
        self._start_time = time.perf_counter()

    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return time.perf_counter() - self._start_time

    def elapsed_ns(self) -> int:
        """Get elapsed time in nanoseconds."""
        return time.perf_counter_ns() - int(self._start_time * 1e9)

    @staticmethod
    def sleep_until(target_time: float) -> None:
        """Sleep until specific time."""
        while time.perf_counter() < target_time:
            pass


class RTThreadScheduler:
    """Real-time thread scheduler for CPU-intensive tasks."""

    def __init__(self):
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def create_rt_thread(self, target: Callable, priority: int = 99,
                        cpu_affinity: Optional[List[int]] = None) -> threading.Thread:
        """Create real-time thread."""
        def rt_wrapper():
            try:
                # Configure thread for real-time
                if RT_AVAILABLE and os.name == 'posix':
                    # Set thread priority
                    try:
                        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(priority))
                    except (OSError, PermissionError):
                        pass

                # Run target function
                target()

            except Exception as e:
                logging.error(f"Real-time thread error: {e}")

        thread = threading.Thread(target=rt_wrapper, daemon=True)
        self._threads.append(thread)
        return thread

    def start_all_threads(self) -> None:
        """Start all created threads."""
        for thread in self._threads:
            thread.start()

    def stop_all_threads(self) -> None:
        """Stop all threads."""
        self._stop_event.set()
        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=1.0)


class TimingSynchronizer:
    """Synchronize multiple real-time processes."""

    def __init__(self, num_processes: int):
        self._num_processes = num_processes
        self._barriers: List[threading.Barrier] = []
        self._sync_points: List[float] = []

    def create_sync_point(self) -> int:
        """Create synchronization point."""
        barrier = threading.Barrier(self._num_processes)
        self._barriers.append(barrier)
        self._sync_points.append(time.time())
        return len(self._barriers) - 1

    def wait_sync_point(self, sync_id: int, timeout: Optional[float] = None) -> bool:
        """Wait at synchronization point."""
        try:
            if sync_id < len(self._barriers):
                self._barriers[sync_id].wait(timeout)
                return True
            return False
        except threading.BrokenBarrierError:
            return False

    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        return {
            'sync_points': len(self._sync_points),
            'processes': self._num_processes,
            'last_sync': self._sync_points[-1] if self._sync_points else None
        }