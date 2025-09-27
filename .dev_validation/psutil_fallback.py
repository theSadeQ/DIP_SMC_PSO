#==========================================================================================\\\
#============================= psutil_fallback.py ==================================\\\
#==========================================================================================\\\
"""
Fallback module for psutil functionality.

This module provides basic system monitoring functionality when psutil
is not available, allowing tests to run without the optional dependency.
"""

import time
import os
from typing import Dict, Any, Optional, List


class Process:
    """Mock Process class for when psutil is not available."""

    def __init__(self, pid: Optional[int] = None):
        self.pid = pid or os.getpid()
        self._start_time = time.time()

    def memory_info(self) -> 'MemoryInfo':
        """Return mock memory info."""
        # Return reasonable mock values
        return MemoryInfo(rss=50 * 1024 * 1024, vms=100 * 1024 * 1024)  # 50MB RSS, 100MB VMS

    def memory_percent(self) -> float:
        """Return mock memory percentage."""
        return 5.0  # Mock 5% memory usage

    def cpu_percent(self, interval: Optional[float] = None) -> float:
        """Return mock CPU percentage."""
        if interval:
            time.sleep(interval)
        return 10.0  # Mock 10% CPU usage

    def is_running(self) -> bool:
        """Return True for mock process."""
        return True

    def create_time(self) -> float:
        """Return mock process creation time."""
        return self._start_time


class MemoryInfo:
    """Mock memory info class."""

    def __init__(self, rss: int, vms: int):
        self.rss = rss
        self.vms = vms


def virtual_memory() -> 'VirtualMemory':
    """Return mock virtual memory info."""
    total = 8 * 1024 * 1024 * 1024  # Mock 8GB total memory
    available = 4 * 1024 * 1024 * 1024  # Mock 4GB available
    percent = ((total - available) / total) * 100

    return VirtualMemory(
        total=total,
        available=available,
        percent=percent,
        used=total - available,
        free=available
    )


class VirtualMemory:
    """Mock virtual memory class."""

    def __init__(self, total: int, available: int, percent: float, used: int, free: int):
        self.total = total
        self.available = available
        self.percent = percent
        self.used = used
        self.free = free


def cpu_percent(interval: Optional[float] = None, percpu: bool = False) -> float:
    """Return mock CPU percentage."""
    if interval:
        time.sleep(interval)

    if percpu:
        # Mock 4 cores
        return [8.0, 12.0, 9.5, 11.2]

    return 10.0  # Mock 10% overall CPU usage


def cpu_count(logical: bool = True) -> int:
    """Return mock CPU count."""
    if logical:
        return 8  # Mock 8 logical cores
    else:
        return 4  # Mock 4 physical cores


def disk_usage(path: str) -> 'DiskUsage':
    """Return mock disk usage."""
    total = 500 * 1024 * 1024 * 1024  # Mock 500GB total
    used = 250 * 1024 * 1024 * 1024   # Mock 250GB used
    free = total - used

    return DiskUsage(total=total, used=used, free=free)


class DiskUsage:
    """Mock disk usage class."""

    def __init__(self, total: int, used: int, free: int):
        self.total = total
        self.used = used
        self.free = free


def boot_time() -> float:
    """Return mock boot time."""
    return time.time() - (24 * 3600)  # Mock system booted 24 hours ago


# Try to import psutil, fall back to mock implementation
PSUTIL_AVAILABLE = False
try:
    import psutil as _psutil
    # Re-export everything from real psutil if available
    Process = _psutil.Process
    virtual_memory = _psutil.virtual_memory
    cpu_percent = _psutil.cpu_percent
    cpu_count = _psutil.cpu_count
    disk_usage = _psutil.disk_usage
    boot_time = _psutil.boot_time
    PSUTIL_AVAILABLE = True

except ImportError:
    # Use mock implementations defined above (already defined)
    pass


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information."""
    try:
        mem = virtual_memory()
        return {
            'psutil_available': PSUTIL_AVAILABLE,
            'memory_total': mem.total,
            'memory_available': mem.available,
            'memory_percent': mem.percent,
            'cpu_count': cpu_count(),
            'cpu_percent': cpu_percent(),
            'boot_time': boot_time(),
        }
    except Exception:
        return {
            'psutil_available': False,
            'error': 'System monitoring unavailable'
        }