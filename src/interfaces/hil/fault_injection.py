#==========================================================================================\\\
#===================== src/interfaces/hil/fault_injection.py ===========================\\\
#==========================================================================================\\\
"""
Fault injection system for HIL testing and validation.
This module provides comprehensive fault injection capabilities including
sensor faults, actuator faults, communication failures, and system-level
fault scenarios for robust control system testing.
"""

import asyncio
import time
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
import logging


class FaultType(Enum):
    """Fault type enumeration."""
    SENSOR_BIAS = "sensor_bias"
    SENSOR_DRIFT = "sensor_drift"
    SENSOR_NOISE = "sensor_noise"
    SENSOR_STUCK = "sensor_stuck"
    SENSOR_DROPOUT = "sensor_dropout"
    ACTUATOR_BIAS = "actuator_bias"
    ACTUATOR_STUCK = "actuator_stuck"
    ACTUATOR_SATURATION = "actuator_saturation"
    ACTUATOR_DEADBAND = "actuator_deadband"
    COMMUNICATION_DELAY = "communication_delay"
    COMMUNICATION_LOSS = "communication_loss"
    COMMUNICATION_CORRUPTION = "communication_corruption"
    POWER_SUPPLY_DROP = "power_supply_drop"
    SYSTEM_OVERLOAD = "system_overload"


class FaultSeverity(Enum):
    """Fault severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FaultProfile:
    """Fault injection profile configuration."""
    fault_type: FaultType
    severity: FaultSeverity
    target_device: str
    target_channel: Optional[str] = None

    # Timing parameters
    start_time: float = 0.0
    duration: Optional[float] = None
    intermittent: bool = False
    intermittent_period: float = 1.0

    # Fault parameters
    magnitude: float = 1.0
    offset: float = 0.0
    noise_level: float = 0.1
    pattern: str = "constant"  # constant, ramp, sine, random

    # Recovery parameters
    recoverable: bool = True
    recovery_time: Optional[float] = None

    # Conditional parameters
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FaultScenario:
    """Complete fault scenario with multiple fault profiles."""
    name: str
    description: str
    profiles: List[FaultProfile] = field(default_factory=list)
    scenario_duration: Optional[float] = None
    repeat_count: int = 1
    randomize_timing: bool = False
    timing_variation: float = 0.1


@dataclass
class FaultEvent:
    """Fault event record."""
    timestamp: float
    fault_id: str
    event_type: str  # "inject", "remove", "modify"
    fault_type: FaultType
    target_device: str
    target_channel: Optional[str]
    magnitude: float
    success: bool = True
    error_message: Optional[str] = None


class FaultInjector:
    """
    Comprehensive fault injection system for HIL testing.

    Provides systematic fault injection capabilities for sensors,
    actuators, communication, and system-level components to validate
    control system robustness and fault tolerance.
    """

    def __init__(self, device_manager: 'DeviceManager',
                 communication_interfaces: Dict[str, Any]):
        """Initialize fault injector."""
        self._device_manager = device_manager
        self._communication_interfaces = communication_interfaces

        # Active faults tracking
        self._active_faults: Dict[str, FaultProfile] = {}
        self._fault_tasks: Dict[str, asyncio.Task] = {}
        self._fault_history: List[FaultEvent] = []

        # Fault scenarios
        self._scenarios: Dict[str, FaultScenario] = {}
        self._active_scenario: Optional[FaultScenario] = None
        self._scenario_task: Optional[asyncio.Task] = None

        # Configuration
        self._logger = logging.getLogger("fault_injector")
        self._enabled = True
        self._safety_limits = {}

        # Statistics
        self._stats = {
            'total_faults_injected': 0,
            'active_faults': 0,
            'scenarios_executed': 0,
            'fault_types_used': set()
        }

    @property
    def enabled(self) -> bool:
        """Check if fault injection is enabled."""
        return self._enabled

    @property
    def active_faults(self) -> Dict[str, FaultProfile]:
        """Get currently active faults."""
        return self._active_faults.copy()

    @property
    def statistics(self) -> Dict[str, Any]:
        """Get fault injection statistics."""
        stats = self._stats.copy()
        stats['fault_types_used'] = list(stats['fault_types_used'])
        return stats

    def enable(self) -> None:
        """Enable fault injection."""
        self._enabled = True
        self._logger.info("Fault injection enabled")

    def disable(self) -> None:
        """Disable fault injection."""
        self._enabled = False
        self._logger.info("Fault injection disabled")

    async def inject_fault(self, fault_id: str, profile: FaultProfile) -> bool:
        """Inject a specific fault."""
        try:
            if not self._enabled:
                self._logger.warning("Fault injection is disabled")
                return False

            if fault_id in self._active_faults:
                self._logger.warning(f"Fault {fault_id} already active")
                return False

            # Validate fault profile
            if not await self._validate_fault_profile(profile):
                return False

            # Start fault injection
            self._active_faults[fault_id] = profile
            self._fault_tasks[fault_id] = asyncio.create_task(
                self._execute_fault(fault_id, profile)
            )

            # Record event
            event = FaultEvent(
                timestamp=time.time(),
                fault_id=fault_id,
                event_type="inject",
                fault_type=profile.fault_type,
                target_device=profile.target_device,
                target_channel=profile.target_channel,
                magnitude=profile.magnitude
            )
            self._record_fault_event(event)

            self._logger.info(f"Injected fault {fault_id}: {profile.fault_type.value}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to inject fault {fault_id}: {e}")
            return False

    async def remove_fault(self, fault_id: str) -> bool:
        """Remove an active fault."""
        try:
            if fault_id not in self._active_faults:
                self._logger.warning(f"Fault {fault_id} not active")
                return False

            # Cancel fault task
            if fault_id in self._fault_tasks:
                self._fault_tasks[fault_id].cancel()
                try:
                    await self._fault_tasks[fault_id]
                except asyncio.CancelledError:
                    pass
                del self._fault_tasks[fault_id]

            # Remove from active faults
            profile = self._active_faults.pop(fault_id)

            # Record event
            event = FaultEvent(
                timestamp=time.time(),
                fault_id=fault_id,
                event_type="remove",
                fault_type=profile.fault_type,
                target_device=profile.target_device,
                target_channel=profile.target_channel,
                magnitude=0.0
            )
            self._record_fault_event(event)

            self._logger.info(f"Removed fault {fault_id}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to remove fault {fault_id}: {e}")
            return False

    async def clear_all_faults(self) -> bool:
        """Clear all active faults."""
        try:
            fault_ids = list(self._active_faults.keys())
            for fault_id in fault_ids:
                await self.remove_fault(fault_id)

            self._logger.info("Cleared all active faults")
            return True

        except Exception as e:
            self._logger.error(f"Failed to clear all faults: {e}")
            return False

    async def configure_scenario(self, scenario: FaultScenario) -> bool:
        """Configure fault scenario."""
        try:
            self._scenarios[scenario.name] = scenario
            self._logger.info(f"Configured fault scenario: {scenario.name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to configure scenario {scenario.name}: {e}")
            return False

    async def execute_scenario(self, scenario_name: str) -> bool:
        """Execute fault scenario."""
        try:
            if scenario_name not in self._scenarios:
                self._logger.error(f"Scenario {scenario_name} not found")
                return False

            scenario = self._scenarios[scenario_name]

            if self._scenario_task and not self._scenario_task.done():
                self._logger.warning("Another scenario is already running")
                return False

            self._active_scenario = scenario
            self._scenario_task = asyncio.create_task(
                self._execute_scenario_task(scenario)
            )

            self._logger.info(f"Started executing scenario: {scenario_name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to execute scenario {scenario_name}: {e}")
            return False

    async def stop_scenario(self) -> bool:
        """Stop current scenario execution."""
        try:
            if self._scenario_task:
                self._scenario_task.cancel()
                try:
                    await self._scenario_task
                except asyncio.CancelledError:
                    pass

            # Clear all faults from scenario
            await self.clear_all_faults()

            self._active_scenario = None
            self._logger.info("Stopped scenario execution")
            return True

        except Exception as e:
            self._logger.error(f"Failed to stop scenario: {e}")
            return False

    def get_fault_history(self, since: Optional[float] = None,
                         fault_type: Optional[FaultType] = None) -> List[FaultEvent]:
        """Get fault event history."""
        history = self._fault_history

        if since:
            history = [event for event in history if event.timestamp >= since]

        if fault_type:
            history = [event for event in history if event.fault_type == fault_type]

        return history

    async def _execute_fault(self, fault_id: str, profile: FaultProfile) -> None:
        """Execute fault injection task."""
        try:
            # Wait for start time
            if profile.start_time > 0:
                await asyncio.sleep(profile.start_time)

            start_time = time.time()
            device = self._device_manager.get_device(profile.target_device)

            if not device:
                raise Exception(f"Device {profile.target_device} not found")

            while True:
                # Apply fault based on type
                await self._apply_fault(device, profile)

                # Check duration
                if profile.duration and (time.time() - start_time) >= profile.duration:
                    break

                # Handle intermittent faults
                if profile.intermittent:
                    await asyncio.sleep(profile.intermittent_period)
                else:
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

        except asyncio.CancelledError:
            # Clean up fault
            await self._cleanup_fault(fault_id, profile)
            raise
        except Exception as e:
            self._logger.error(f"Error in fault execution {fault_id}: {e}")
            # Record failed event
            event = FaultEvent(
                timestamp=time.time(),
                fault_id=fault_id,
                event_type="error",
                fault_type=profile.fault_type,
                target_device=profile.target_device,
                target_channel=profile.target_channel,
                magnitude=profile.magnitude,
                success=False,
                error_message=str(e)
            )
            self._record_fault_event(event)

    async def _apply_fault(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply specific fault to device."""
        try:
            if profile.fault_type == FaultType.SENSOR_BIAS:
                await self._apply_sensor_bias(device, profile)
            elif profile.fault_type == FaultType.SENSOR_DRIFT:
                await self._apply_sensor_drift(device, profile)
            elif profile.fault_type == FaultType.SENSOR_NOISE:
                await self._apply_sensor_noise(device, profile)
            elif profile.fault_type == FaultType.SENSOR_STUCK:
                await self._apply_sensor_stuck(device, profile)
            elif profile.fault_type == FaultType.ACTUATOR_BIAS:
                await self._apply_actuator_bias(device, profile)
            elif profile.fault_type == FaultType.ACTUATOR_STUCK:
                await self._apply_actuator_stuck(device, profile)
            elif profile.fault_type == FaultType.COMMUNICATION_DELAY:
                await self._apply_communication_delay(profile)
            elif profile.fault_type == FaultType.COMMUNICATION_LOSS:
                await self._apply_communication_loss(profile)
            else:
                self._logger.warning(f"Unsupported fault type: {profile.fault_type}")

        except Exception as e:
            self._logger.error(f"Failed to apply fault {profile.fault_type}: {e}")

    async def _apply_sensor_bias(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply sensor bias fault."""
        # This would modify sensor readings by adding a bias
        # Implementation depends on device interface
        pass

    async def _apply_sensor_drift(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply sensor drift fault."""
        # This would implement gradual sensor drift over time
        elapsed_time = time.time() - profile.start_time
        drift_value = profile.magnitude * elapsed_time / 3600.0  # per hour
        # Apply drift to sensor readings
        pass

    async def _apply_sensor_noise(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply sensor noise fault."""
        # This would add random noise to sensor readings
        noise = np.random.normal(0, profile.noise_level)
        # Apply noise to sensor readings
        pass

    async def _apply_sensor_stuck(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply sensor stuck fault."""
        # This would freeze sensor readings at current value
        pass

    async def _apply_actuator_bias(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply actuator bias fault."""
        # This would modify actuator commands by adding bias
        pass

    async def _apply_actuator_stuck(self, device: 'DeviceDriver', profile: FaultProfile) -> None:
        """Apply actuator stuck fault."""
        # This would prevent actuator from responding to commands
        pass

    async def _apply_communication_delay(self, profile: FaultProfile) -> None:
        """Apply communication delay fault."""
        # This would introduce delays in communication
        delay = profile.magnitude / 1000.0  # Convert ms to seconds
        await asyncio.sleep(delay)

    async def _apply_communication_loss(self, profile: FaultProfile) -> None:
        """Apply communication loss fault."""
        # This would simulate communication dropouts
        if random.random() < profile.magnitude:
            # Simulate packet loss
            pass

    async def _execute_scenario_task(self, scenario: FaultScenario) -> None:
        """Execute complete fault scenario."""
        try:
            self._logger.info(f"Executing scenario: {scenario.name}")

            for repeat in range(scenario.repeat_count):
                if repeat > 0:
                    self._logger.info(f"Scenario repeat {repeat + 1}/{scenario.repeat_count}")

                # Schedule all fault profiles
                fault_tasks = []
                for i, profile in enumerate(scenario.profiles):
                    fault_id = f"{scenario.name}_fault_{i}_{repeat}"

                    # Add timing variation if enabled
                    if scenario.randomize_timing:
                        variation = random.uniform(-scenario.timing_variation,
                                                 scenario.timing_variation)
                        profile.start_time += variation

                    # Start fault injection
                    task = asyncio.create_task(
                        self._inject_scenario_fault(fault_id, profile)
                    )
                    fault_tasks.append(task)

                # Wait for scenario completion
                if scenario.scenario_duration:
                    await asyncio.sleep(scenario.scenario_duration)
                else:
                    # Wait for all faults to complete
                    await asyncio.gather(*fault_tasks, return_exceptions=True)

                # Clear faults between repeats
                if repeat < scenario.repeat_count - 1:
                    await self.clear_all_faults()
                    await asyncio.sleep(1.0)  # Brief pause between repeats

            self._stats['scenarios_executed'] += 1
            self._logger.info(f"Completed scenario: {scenario.name}")

        except asyncio.CancelledError:
            self._logger.info(f"Scenario {scenario.name} cancelled")
            await self.clear_all_faults()
            raise
        except Exception as e:
            self._logger.error(f"Error executing scenario {scenario.name}: {e}")

    async def _inject_scenario_fault(self, fault_id: str, profile: FaultProfile) -> None:
        """Inject fault as part of scenario."""
        await self.inject_fault(fault_id, profile)

        # Wait for fault completion
        if fault_id in self._fault_tasks:
            try:
                await self._fault_tasks[fault_id]
            except asyncio.CancelledError:
                pass

    async def _validate_fault_profile(self, profile: FaultProfile) -> bool:
        """Validate fault profile configuration."""
        # Check if target device exists
        device = self._device_manager.get_device(profile.target_device)
        if not device:
            self._logger.error(f"Target device {profile.target_device} not found")
            return False

        # Check safety limits
        if profile.target_device in self._safety_limits:
            limits = self._safety_limits[profile.target_device]
            if profile.magnitude > limits.get('max_magnitude', float('inf')):
                self._logger.error(f"Fault magnitude exceeds safety limits")
                return False

        return True

    async def _cleanup_fault(self, fault_id: str, profile: FaultProfile) -> None:
        """Clean up fault after completion or cancellation."""
        try:
            # Remove fault modifications
            device = self._device_manager.get_device(profile.target_device)
            if device:
                # Device-specific cleanup would be implemented here
                pass

            self._logger.debug(f"Cleaned up fault {fault_id}")

        except Exception as e:
            self._logger.error(f"Error cleaning up fault {fault_id}: {e}")

    def _record_fault_event(self, event: FaultEvent) -> None:
        """Record fault event in history."""
        self._fault_history.append(event)

        # Update statistics
        if event.event_type == "inject":
            self._stats['total_faults_injected'] += 1
            self._stats['fault_types_used'].add(event.fault_type.value)

        self._stats['active_faults'] = len(self._active_faults)

        # Limit history size
        if len(self._fault_history) > 10000:
            self._fault_history = self._fault_history[-5000:]

    def set_safety_limits(self, device_id: str, limits: Dict[str, Any]) -> None:
        """Set safety limits for fault injection."""
        self._safety_limits[device_id] = limits
        self._logger.info(f"Set safety limits for device {device_id}")


# Utility functions for common fault scenarios
def create_sensor_fault_scenario(sensor_name: str, fault_types: List[FaultType],
                                duration: float = 60.0) -> FaultScenario:
    """Create common sensor fault scenario."""
    profiles = []
    start_offset = 0.0

    for fault_type in fault_types:
        profile = FaultProfile(
            fault_type=fault_type,
            severity=FaultSeverity.MEDIUM,
            target_device=sensor_name,
            start_time=start_offset,
            duration=duration / len(fault_types),
            magnitude=0.1 if "noise" in fault_type.value else 1.0
        )
        profiles.append(profile)
        start_offset += duration / len(fault_types)

    return FaultScenario(
        name=f"{sensor_name}_fault_sequence",
        description=f"Sequential fault injection for {sensor_name}",
        profiles=profiles,
        scenario_duration=duration
    )


def create_actuator_fault_scenario(actuator_name: str, severity: FaultSeverity = FaultSeverity.MEDIUM) -> FaultScenario:
    """Create common actuator fault scenario."""
    profiles = [
        FaultProfile(
            fault_type=FaultType.ACTUATOR_BIAS,
            severity=severity,
            target_device=actuator_name,
            start_time=0.0,
            duration=30.0,
            magnitude=0.1
        ),
        FaultProfile(
            fault_type=FaultType.ACTUATOR_STUCK,
            severity=severity,
            target_device=actuator_name,
            start_time=35.0,
            duration=15.0,
            magnitude=1.0
        )
    ]

    return FaultScenario(
        name=f"{actuator_name}_fault_scenario",
        description=f"Actuator fault scenario for {actuator_name}",
        profiles=profiles,
        scenario_duration=60.0
    )