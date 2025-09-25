#==========================================================================================\\\
#==================== src/interfaces/hardware/device_drivers.py =======================\\\
#==========================================================================================\\\
"""
Base device driver framework for hardware abstraction.
This module provides the foundational classes and interfaces for implementing
device drivers in control systems, including device lifecycle management,
error handling, and standardized communication patterns.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
import logging

from ..core.data_types import DeviceInfo, InterfaceType


class DeviceState(Enum):
    """Device operational state enumeration."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class DeviceError(Exception):
    """Base exception for device-related errors."""
    def __init__(self, message: str, device_id: str, error_code: Optional[str] = None):
        self.device_id = device_id
        self.error_code = error_code
        super().__init__(f"Device {device_id}: {message}")


@dataclass
class DeviceCapability:
    """Device capability description."""
    name: str
    description: str
    data_type: str
    unit: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    resolution: Optional[float] = None
    read_only: bool = False


@dataclass
class DeviceConfig:
    """Device configuration structure."""
    device_id: str
    device_type: str
    connection_params: Dict[str, Any] = field(default_factory=dict)
    operational_params: Dict[str, Any] = field(default_factory=dict)
    calibration_params: Dict[str, Any] = field(default_factory=dict)
    safety_limits: Dict[str, tuple] = field(default_factory=dict)
    update_rate: float = 10.0  # Hz
    timeout: float = 1.0
    retry_attempts: int = 3
    enable_logging: bool = True


@dataclass
class DeviceStatus:
    """Device status information."""
    device_id: str
    state: DeviceState = DeviceState.UNKNOWN
    last_update: float = field(default_factory=time.time)
    error_count: int = 0
    warning_count: int = 0
    uptime: float = 0.0
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)

    def update_timestamp(self):
        """Update the last update timestamp."""
        self.last_update = time.time()

    def add_metric(self, name: str, value: float):
        """Add a performance metric."""
        self.metrics[name] = value

    def add_alert(self, message: str):
        """Add an alert message."""
        self.alerts.append(f"{time.time()}: {message}")
        if len(self.alerts) > 100:  # Keep only last 100 alerts
            self.alerts.pop(0)


class DeviceDriver(ABC):
    """
    Abstract base class for all device drivers.

    This class defines the standard interface that all device drivers
    must implement, providing consistent patterns for device lifecycle
    management, communication, and error handling.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize device driver with configuration."""
        self._config = config
        self._status = DeviceStatus(device_id=config.device_id)
        self._capabilities: List[DeviceCapability] = []
        self._logger = logging.getLogger(f"device_{config.device_id}")
        self._error_handlers: List[Callable] = []
        self._status_callbacks: List[Callable] = []
        self._update_task: Optional[asyncio.Task] = None
        self._last_read_time = 0.0

    @property
    def device_id(self) -> str:
        """Get device identifier."""
        return self._config.device_id

    @property
    def device_type(self) -> str:
        """Get device type."""
        return self._config.device_type

    @property
    def state(self) -> DeviceState:
        """Get current device state."""
        return self._status.state

    @property
    def status(self) -> DeviceStatus:
        """Get device status."""
        return self._status

    @property
    def capabilities(self) -> List[DeviceCapability]:
        """Get device capabilities."""
        return self._capabilities.copy()

    @property
    def config(self) -> DeviceConfig:
        """Get device configuration."""
        return self._config

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the device.

        Returns
        -------
        bool
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the device gracefully.

        Returns
        -------
        bool
            True if shutdown successful, False otherwise
        """
        pass

    @abstractmethod
    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Read data from the device.

        Parameters
        ----------
        channel : str, optional
            Specific channel to read from

        Returns
        -------
        Dict[str, Any]
            Dictionary of channel names to values
        """
        pass

    @abstractmethod
    async def write_data(self, data: Dict[str, Any]) -> bool:
        """
        Write data to the device.

        Parameters
        ----------
        data : Dict[str, Any]
            Dictionary of channel names to values

        Returns
        -------
        bool
            True if write successful, False otherwise
        """
        pass

    @abstractmethod
    async def self_test(self) -> Dict[str, Any]:
        """
        Perform device self-test.

        Returns
        -------
        Dict[str, Any]
            Self-test results
        """
        pass

    async def start(self) -> bool:
        """Start device operation."""
        try:
            self._status.state = DeviceState.INITIALIZING
            self._notify_status_change()

            if not await self.initialize():
                self._status.state = DeviceState.ERROR
                self._notify_status_change()
                return False

            self._status.state = DeviceState.RUNNING
            self._status.uptime = time.time()
            self._notify_status_change()

            # Start update task if update rate is specified
            if self._config.update_rate > 0:
                self._update_task = asyncio.create_task(self._update_loop())

            self._logger.info(f"Device {self.device_id} started successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start device {self.device_id}: {e}")
            self._status.state = DeviceState.ERROR
            self._notify_status_change()
            await self._handle_error(e)
            return False

    async def stop(self) -> bool:
        """Stop device operation."""
        try:
            # Cancel update task
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass

            # Shutdown device
            await self.shutdown()

            self._status.state = DeviceState.OFFLINE
            self._notify_status_change()

            self._logger.info(f"Device {self.device_id} stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping device {self.device_id}: {e}")
            await self._handle_error(e)
            return False

    async def restart(self) -> bool:
        """Restart device operation."""
        self._logger.info(f"Restarting device {self.device_id}")
        await self.stop()
        await asyncio.sleep(1.0)  # Brief pause before restart
        return await self.start()

    async def calibrate(self, calibration_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Calibrate the device.

        Parameters
        ----------
        calibration_data : Dict[str, Any], optional
            Calibration parameters

        Returns
        -------
        bool
            True if calibration successful
        """
        try:
            self._logger.info(f"Calibrating device {self.device_id}")
            # Default implementation - override in subclasses
            return True
        except Exception as e:
            self._logger.error(f"Calibration failed for device {self.device_id}: {e}")
            await self._handle_error(e)
            return False

    async def reset(self) -> bool:
        """
        Reset device to default state.

        Returns
        -------
        bool
            True if reset successful
        """
        try:
            self._logger.info(f"Resetting device {self.device_id}")
            self._status.error_count = 0
            self._status.warning_count = 0
            self._status.alerts.clear()
            return True
        except Exception as e:
            self._logger.error(f"Reset failed for device {self.device_id}: {e}")
            await self._handle_error(e)
            return False

    def add_capability(self, capability: DeviceCapability) -> None:
        """Add device capability."""
        self._capabilities.append(capability)

    def get_capability(self, name: str) -> Optional[DeviceCapability]:
        """Get specific capability by name."""
        for cap in self._capabilities:
            if cap.name == name:
                return cap
        return None

    def add_error_handler(self, handler: Callable) -> None:
        """Add error handler callback."""
        self._error_handlers.append(handler)

    def add_status_callback(self, callback: Callable) -> None:
        """Add status change callback."""
        self._status_callbacks.append(callback)

    async def _update_loop(self) -> None:
        """Continuous update loop for device monitoring."""
        try:
            update_interval = 1.0 / self._config.update_rate

            while self._status.state == DeviceState.RUNNING:
                try:
                    # Update device status
                    await self._update_status()

                    # Check for safety violations
                    await self._check_safety_limits()

                    await asyncio.sleep(update_interval)

                except Exception as e:
                    self._logger.warning(f"Error in update loop for device {self.device_id}: {e}")
                    self._status.error_count += 1

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Update loop failed for device {self.device_id}: {e}")
            self._status.state = DeviceState.ERROR
            await self._handle_error(e)

    async def _update_status(self) -> None:
        """Update device status information."""
        current_time = time.time()
        if self._status.uptime > 0:
            self._status.uptime = current_time - self._status.uptime

        self._status.update_timestamp()

        # Update metrics
        if current_time - self._last_read_time > 1.0:  # Update every second
            try:
                data = await self.read_data()
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        self._status.add_metric(f"last_{key}", float(value))
                self._last_read_time = current_time
            except Exception as e:
                self._logger.debug(f"Error reading data in status update: {e}")

    async def _check_safety_limits(self) -> None:
        """Check safety limits and trigger alerts if violated."""
        try:
            data = await self.read_data()
            for channel, value in data.items():
                if channel in self._config.safety_limits:
                    min_val, max_val = self._config.safety_limits[channel]
                    if not (min_val <= value <= max_val):
                        alert_msg = f"Safety limit violation: {channel}={value} not in [{min_val}, {max_val}]"
                        self._status.add_alert(alert_msg)
                        self._logger.warning(alert_msg)
        except Exception as e:
            self._logger.debug(f"Error checking safety limits: {e}")

    async def _handle_error(self, error: Exception) -> None:
        """Handle device errors."""
        self._status.error_count += 1

        # Call error handlers
        for handler in self._error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(self, error)
                else:
                    handler(self, error)
            except Exception as handler_error:
                self._logger.error(f"Error in error handler: {handler_error}")

    def _notify_status_change(self) -> None:
        """Notify status change callbacks."""
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self, self._status))
                else:
                    callback(self, self._status)
            except Exception as e:
                self._logger.error(f"Error in status callback: {e}")


class BaseDevice(DeviceDriver):
    """
    Base implementation of DeviceDriver with common functionality.

    This class provides default implementations for common device operations
    and can be used as a starting point for simple device drivers.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize base device."""
        super().__init__(config)
        self._data_cache: Dict[str, Any] = {}
        self._last_cache_update = 0.0
        self._cache_timeout = 0.1  # 100ms cache timeout

    async def initialize(self) -> bool:
        """Initialize base device."""
        self._logger.info(f"Initializing base device {self.device_id}")

        # Perform basic initialization
        await asyncio.sleep(0.1)  # Simulate initialization delay

        # Add basic capabilities
        self.add_capability(DeviceCapability(
            name="status",
            description="Device status information",
            data_type="dict",
            read_only=True
        ))

        return True

    async def shutdown(self) -> bool:
        """Shutdown base device."""
        self._logger.info(f"Shutting down base device {self.device_id}")
        self._data_cache.clear()
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read data from base device."""
        current_time = time.time()

        # Check cache validity
        if (current_time - self._last_cache_update) < self._cache_timeout:
            if channel:
                return {channel: self._data_cache.get(channel)} if channel in self._data_cache else {}
            return self._data_cache.copy()

        # Update cache with fresh data
        await self._update_data_cache()
        self._last_cache_update = current_time

        if channel:
            return {channel: self._data_cache.get(channel)} if channel in self._data_cache else {}
        return self._data_cache.copy()

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to base device."""
        try:
            for channel, value in data.items():
                self._logger.debug(f"Writing {channel}={value} to device {self.device_id}")
                # Base implementation just logs the write
                # Override in subclasses for actual hardware interaction

            return True

        except Exception as e:
            self._logger.error(f"Error writing data to device {self.device_id}: {e}")
            return False

    async def self_test(self) -> Dict[str, Any]:
        """Perform base device self-test."""
        test_results = {
            'timestamp': time.time(),
            'device_id': self.device_id,
            'communication': True,
            'initialization': self._status.state != DeviceState.ERROR,
            'data_integrity': True,
            'overall_status': 'PASS'
        }

        # Check if device is responsive
        try:
            await self.read_data()
        except Exception:
            test_results['communication'] = False
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def _update_data_cache(self) -> None:
        """Update internal data cache."""
        # Base implementation provides synthetic data
        # Override in subclasses for actual device data
        self._data_cache = {
            'timestamp': time.time(),
            'device_id': self.device_id,
            'status': self._status.state.value,
            'uptime': self._status.uptime,
            'error_count': self._status.error_count
        }


class DeviceManager:
    """
    Manager for multiple device drivers.

    This class provides centralized management of multiple devices,
    including lifecycle coordination, status monitoring, and
    coordinated operations.
    """

    def __init__(self):
        """Initialize device manager."""
        self._devices: Dict[str, DeviceDriver] = {}
        self._logger = logging.getLogger("device_manager")

    def add_device(self, device: DeviceDriver) -> None:
        """Add device to manager."""
        device_id = device.device_id
        if device_id in self._devices:
            raise ValueError(f"Device {device_id} already exists in manager")

        self._devices[device_id] = device
        self._logger.info(f"Added device {device_id} to manager")

    def remove_device(self, device_id: str) -> Optional[DeviceDriver]:
        """Remove device from manager."""
        device = self._devices.pop(device_id, None)
        if device:
            self._logger.info(f"Removed device {device_id} from manager")
        return device

    def get_device(self, device_id: str) -> Optional[DeviceDriver]:
        """Get device by ID."""
        return self._devices.get(device_id)

    def list_devices(self) -> List[str]:
        """List all device IDs."""
        return list(self._devices.keys())

    def get_devices_by_type(self, device_type: str) -> List[DeviceDriver]:
        """Get all devices of specific type."""
        return [
            device for device in self._devices.values()
            if device.device_type == device_type
        ]

    async def start_all(self) -> Dict[str, bool]:
        """Start all devices."""
        results = {}
        for device_id, device in self._devices.items():
            try:
                results[device_id] = await device.start()
            except Exception as e:
                self._logger.error(f"Failed to start device {device_id}: {e}")
                results[device_id] = False

        return results

    async def stop_all(self) -> Dict[str, bool]:
        """Stop all devices."""
        results = {}
        for device_id, device in self._devices.items():
            try:
                results[device_id] = await device.stop()
            except Exception as e:
                self._logger.error(f"Failed to stop device {device_id}: {e}")
                results[device_id] = False

        return results

    async def restart_all(self) -> Dict[str, bool]:
        """Restart all devices."""
        results = {}
        for device_id, device in self._devices.items():
            try:
                results[device_id] = await device.restart()
            except Exception as e:
                self._logger.error(f"Failed to restart device {device_id}: {e}")
                results[device_id] = False

        return results

    def get_status_summary(self) -> Dict[str, Any]:
        """Get status summary for all devices."""
        summary = {
            'total_devices': len(self._devices),
            'states': {},
            'error_count': 0,
            'warning_count': 0,
            'devices': {}
        }

        for device_id, device in self._devices.items():
            state = device.state.value
            summary['states'][state] = summary['states'].get(state, 0) + 1
            summary['error_count'] += device.status.error_count
            summary['warning_count'] += device.status.warning_count
            summary['devices'][device_id] = {
                'state': state,
                'type': device.device_type,
                'last_update': device.status.last_update,
                'error_count': device.status.error_count
            }

        return summary

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all devices."""
        results = {}
        for device_id, device in self._devices.items():
            try:
                results[device_id] = await device.self_test()
            except Exception as e:
                self._logger.error(f"Health check failed for device {device_id}: {e}")
                results[device_id] = {
                    'overall_status': 'FAIL',
                    'error': str(e)
                }

        return results