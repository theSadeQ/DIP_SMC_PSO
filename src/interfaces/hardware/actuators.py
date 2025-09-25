#==========================================================================================\\\
#======================= src/interfaces/hardware/actuators.py ===========================\\\
#==========================================================================================\\\
"""
Actuator interface framework for control systems.
This module provides standardized interfaces for various actuator types
commonly used in control systems, including servo motors, stepper motors,
pneumatic actuators, and other motion control devices.
"""

import asyncio
import time
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import logging

from .device_drivers import DeviceDriver, DeviceConfig, DeviceCapability, DeviceState


class ActuatorType(Enum):
    """Actuator type enumeration."""
    SERVO = "servo"
    STEPPER = "stepper"
    DC_MOTOR = "dc_motor"
    PNEUMATIC = "pneumatic"
    HYDRAULIC = "hydraulic"
    LINEAR = "linear"
    ROTARY = "rotary"
    VALVE = "valve"


class ActuatorMode(Enum):
    """Actuator control mode enumeration."""
    POSITION = "position"
    VELOCITY = "velocity"
    TORQUE = "torque"
    FORCE = "force"
    PRESSURE = "pressure"
    OPEN_LOOP = "open_loop"


@dataclass
class ActuatorCommand:
    """Actuator command data structure."""
    timestamp: float
    actuator_id: str
    command_type: ActuatorMode
    target_value: float
    unit: str
    priority: int = 0
    timeout: Optional[float] = None
    safety_checks: bool = True


@dataclass
class ActuatorStatus:
    """Actuator status data structure."""
    timestamp: float
    actuator_id: str
    current_position: Optional[float] = None
    current_velocity: Optional[float] = None
    current_force: Optional[float] = None
    target_position: Optional[float] = None
    target_velocity: Optional[float] = None
    target_force: Optional[float] = None
    error: Optional[float] = None
    is_moving: bool = False
    at_target: bool = False
    fault_status: Optional[str] = None


@dataclass
class ActuatorLimits:
    """Actuator operational limits."""
    min_position: Optional[float] = None
    max_position: Optional[float] = None
    max_velocity: Optional[float] = None
    max_acceleration: Optional[float] = None
    max_force: Optional[float] = None
    max_current: Optional[float] = None
    emergency_stop_enabled: bool = True


class ActuatorInterface(DeviceDriver, ABC):
    """
    Abstract base class for actuator interfaces.

    This class defines the standard interface for all actuator types,
    providing common functionality for motion control, safety limits,
    and position feedback.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize actuator interface."""
        super().__init__(config)
        self._actuator_type = ActuatorType.SERVO
        self._control_mode = ActuatorMode.POSITION
        self._limits = ActuatorLimits()
        self._current_status = ActuatorStatus(
            timestamp=time.time(),
            actuator_id=self.device_id
        )
        self._command_queue: List[ActuatorCommand] = []
        self._max_queue_size = config.operational_params.get('max_queue_size', 100)
        self._position_tolerance = config.operational_params.get('position_tolerance', 0.01)
        self._safety_enabled = config.operational_params.get('safety_enabled', True)

    @property
    def actuator_type(self) -> ActuatorType:
        """Get actuator type."""
        return self._actuator_type

    @property
    def control_mode(self) -> ActuatorMode:
        """Get current control mode."""
        return self._control_mode

    @property
    def current_status(self) -> ActuatorStatus:
        """Get current actuator status."""
        return self._current_status

    @property
    def limits(self) -> ActuatorLimits:
        """Get actuator limits."""
        return self._limits

    @abstractmethod
    async def move_to_position(self, position: float, velocity: Optional[float] = None) -> bool:
        """
        Move actuator to specific position.

        Parameters
        ----------
        position : float
            Target position
        velocity : float, optional
            Movement velocity

        Returns
        -------
        bool
            True if command accepted, False otherwise
        """
        pass

    @abstractmethod
    async def set_velocity(self, velocity: float) -> bool:
        """
        Set actuator velocity.

        Parameters
        ----------
        velocity : float
            Target velocity

        Returns
        -------
        bool
            True if command accepted, False otherwise
        """
        pass

    @abstractmethod
    async def set_force(self, force: float) -> bool:
        """
        Set actuator force/torque.

        Parameters
        ----------
        force : float
            Target force or torque

        Returns
        -------
        bool
            True if command accepted, False otherwise
        """
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop actuator motion.

        Returns
        -------
        bool
            True if stop successful, False otherwise
        """
        pass

    @abstractmethod
    async def home(self) -> bool:
        """
        Move actuator to home position.

        Returns
        -------
        bool
            True if homing successful, False otherwise
        """
        pass

    async def set_control_mode(self, mode: ActuatorMode) -> bool:
        """Set actuator control mode."""
        try:
            self._control_mode = mode
            self._logger.info(f"Set control mode to {mode.value} for actuator {self.device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to set control mode: {e}")
            return False

    async def set_limits(self, limits: ActuatorLimits) -> bool:
        """Set actuator operational limits."""
        try:
            self._limits = limits
            self._logger.info(f"Updated limits for actuator {self.device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to set limits: {e}")
            return False

    async def is_at_target(self, tolerance: Optional[float] = None) -> bool:
        """Check if actuator is at target position."""
        if tolerance is None:
            tolerance = self._position_tolerance

        if (self._current_status.current_position is None or
            self._current_status.target_position is None):
            return False

        error = abs(self._current_status.current_position - self._current_status.target_position)
        return error <= tolerance

    async def wait_for_motion_complete(self, timeout: Optional[float] = None) -> bool:
        """Wait for actuator to reach target position."""
        start_time = time.time()

        while True:
            if await self.is_at_target():
                return True

            if timeout and (time.time() - start_time) > timeout:
                self._logger.warning(f"Motion timeout for actuator {self.device_id}")
                return False

            await asyncio.sleep(0.01)  # 10ms polling

    async def emergency_stop(self) -> bool:
        """Perform emergency stop."""
        try:
            self._logger.warning(f"Emergency stop triggered for actuator {self.device_id}")
            await self.stop()
            self._current_status.fault_status = "emergency_stop"
            return True
        except Exception as e:
            self._logger.error(f"Emergency stop failed: {e}")
            return False

    async def clear_faults(self) -> bool:
        """Clear actuator fault conditions."""
        try:
            self._current_status.fault_status = None
            self._logger.info(f"Cleared faults for actuator {self.device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to clear faults: {e}")
            return False

    def _check_safety_limits(self, command: ActuatorCommand) -> bool:
        """Check if command violates safety limits."""
        if not self._safety_enabled:
            return True

        if command.command_type == ActuatorMode.POSITION:
            if (self._limits.min_position is not None and
                command.target_value < self._limits.min_position):
                return False
            if (self._limits.max_position is not None and
                command.target_value > self._limits.max_position):
                return False

        elif command.command_type == ActuatorMode.VELOCITY:
            if (self._limits.max_velocity is not None and
                abs(command.target_value) > self._limits.max_velocity):
                return False

        elif command.command_type == ActuatorMode.FORCE:
            if (self._limits.max_force is not None and
                abs(command.target_value) > self._limits.max_force):
                return False

        return True

    async def _add_command_to_queue(self, command: ActuatorCommand) -> bool:
        """Add command to execution queue."""
        if not command.safety_checks or self._check_safety_limits(command):
            if len(self._command_queue) >= self._max_queue_size:
                self._command_queue.pop(0)  # Remove oldest command

            self._command_queue.append(command)
            return True
        else:
            self._logger.warning(f"Command rejected due to safety limits: {command}")
            return False


class ServoActuator(ActuatorInterface):
    """
    Servo motor actuator implementation.

    Provides position control with encoder feedback, velocity control,
    and PID control loop functionality.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize servo actuator."""
        super().__init__(config)
        self._actuator_type = ActuatorType.SERVO
        self._encoder_resolution = config.operational_params.get('encoder_resolution', 4096)
        self._gear_ratio = config.operational_params.get('gear_ratio', 1.0)
        self._max_rpm = config.operational_params.get('max_rpm', 3000)

        # PID parameters
        self._pid_gains = config.operational_params.get('pid_gains', {'kp': 1.0, 'ki': 0.1, 'kd': 0.01})
        self._pid_error_sum = 0.0
        self._pid_last_error = 0.0

        # Initialize servo capabilities
        self._add_servo_capabilities()

    async def initialize(self) -> bool:
        """Initialize servo actuator."""
        self._logger.info(f"Initializing servo actuator {self.device_id}")

        # Initialize servo controller (simulated)
        await asyncio.sleep(0.2)

        # Set initial position
        self._current_status.current_position = 0.0
        self._current_status.target_position = 0.0

        # Configure limits from config
        limits_config = self._config.operational_params.get('limits', {})
        self._limits = ActuatorLimits(
            min_position=limits_config.get('min_position', -360.0),
            max_position=limits_config.get('max_position', 360.0),
            max_velocity=limits_config.get('max_velocity', self._max_rpm * 6.0),  # deg/s
            max_acceleration=limits_config.get('max_acceleration', 1000.0),
            max_force=limits_config.get('max_force', 10.0)
        )

        return True

    async def shutdown(self) -> bool:
        """Shutdown servo actuator."""
        self._logger.info(f"Shutting down servo actuator {self.device_id}")
        await self.stop()
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read servo actuator data."""
        await self._update_status()

        if channel:
            if channel == "position":
                return {"position": self._current_status.current_position}
            elif channel == "velocity":
                return {"velocity": self._current_status.current_velocity}
            elif channel == "error":
                return {"error": self._current_status.error}
            else:
                return {}
        else:
            return {
                "position": self._current_status.current_position,
                "velocity": self._current_status.current_velocity,
                "target_position": self._current_status.target_position,
                "error": self._current_status.error,
                "is_moving": self._current_status.is_moving,
                "at_target": self._current_status.at_target
            }

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to servo actuator."""
        try:
            if "position" in data:
                return await self.move_to_position(data["position"])
            elif "velocity" in data:
                return await self.set_velocity(data["velocity"])
            elif "force" in data:
                return await self.set_force(data["force"])
            return True
        except Exception as e:
            self._logger.error(f"Failed to write data to servo: {e}")
            return False

    async def self_test(self) -> Dict[str, Any]:
        """Perform servo actuator self-test."""
        test_results = await super().self_test()

        try:
            # Test position control
            initial_position = self._current_status.current_position
            test_position = initial_position + 10.0  # Move 10 degrees

            # Check if position is within limits
            if (self._limits.min_position <= test_position <= self._limits.max_position):
                await self.move_to_position(test_position)
                await asyncio.sleep(0.5)  # Wait for movement

                position_error = abs(self._current_status.current_position - test_position)
                test_results['position_control'] = position_error < 1.0

                # Return to initial position
                await self.move_to_position(initial_position)
            else:
                test_results['position_control'] = True  # Skip if can't test safely

            # Test velocity control
            await self.set_velocity(100.0)  # 100 deg/s
            await asyncio.sleep(0.1)
            test_results['velocity_control'] = abs(self._current_status.current_velocity - 100.0) < 10.0

            await self.stop()

            # Test encoder feedback
            test_results['encoder_functional'] = self._current_status.current_position is not None

        except Exception as e:
            test_results['servo_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def move_to_position(self, position: float, velocity: Optional[float] = None) -> bool:
        """Move servo to specific position."""
        try:
            command = ActuatorCommand(
                timestamp=time.time(),
                actuator_id=self.device_id,
                command_type=ActuatorMode.POSITION,
                target_value=position,
                unit="deg"
            )

            if not await self._add_command_to_queue(command):
                return False

            self._current_status.target_position = position
            self._current_status.is_moving = True

            # Start position control task
            asyncio.create_task(self._position_control_loop(position, velocity))

            return True

        except Exception as e:
            self._logger.error(f"Failed to move to position {position}: {e}")
            return False

    async def set_velocity(self, velocity: float) -> bool:
        """Set servo velocity."""
        try:
            command = ActuatorCommand(
                timestamp=time.time(),
                actuator_id=self.device_id,
                command_type=ActuatorMode.VELOCITY,
                target_value=velocity,
                unit="deg/s"
            )

            if not await self._add_command_to_queue(command):
                return False

            self._current_status.target_velocity = velocity

            # Start velocity control
            asyncio.create_task(self._velocity_control_loop(velocity))

            return True

        except Exception as e:
            self._logger.error(f"Failed to set velocity {velocity}: {e}")
            return False

    async def set_force(self, force: float) -> bool:
        """Set servo force/torque."""
        try:
            command = ActuatorCommand(
                timestamp=time.time(),
                actuator_id=self.device_id,
                command_type=ActuatorMode.FORCE,
                target_value=force,
                unit="Nm"
            )

            if not await self._add_command_to_queue(command):
                return False

            self._current_status.target_force = force
            return True

        except Exception as e:
            self._logger.error(f"Failed to set force {force}: {e}")
            return False

    async def stop(self) -> bool:
        """Stop servo motion."""
        try:
            self._current_status.target_velocity = 0.0
            self._current_status.is_moving = False
            self._logger.info(f"Stopped servo actuator {self.device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to stop servo: {e}")
            return False

    async def home(self) -> bool:
        """Move servo to home position."""
        try:
            home_position = self._config.operational_params.get('home_position', 0.0)
            return await self.move_to_position(home_position)
        except Exception as e:
            self._logger.error(f"Failed to home servo: {e}")
            return False

    async def _position_control_loop(self, target_position: float, max_velocity: Optional[float] = None) -> None:
        """Position control loop with PID controller."""
        try:
            if max_velocity is None:
                max_velocity = self._limits.max_velocity or 360.0

            while self._current_status.is_moving:
                current_pos = self._current_status.current_position
                error = target_position - current_pos

                # PID calculation
                self._pid_error_sum += error * 0.01  # Assuming 100Hz control loop
                derivative = (error - self._pid_last_error) / 0.01

                pid_output = (self._pid_gains['kp'] * error +
                             self._pid_gains['ki'] * self._pid_error_sum +
                             self._pid_gains['kd'] * derivative)

                # Limit velocity
                velocity = max(-max_velocity, min(max_velocity, pid_output))

                # Update position (simplified integration)
                new_position = current_pos + velocity * 0.01
                self._current_status.current_position = new_position
                self._current_status.current_velocity = velocity
                self._current_status.error = error

                # Check if at target
                if abs(error) < self._position_tolerance:
                    self._current_status.is_moving = False
                    self._current_status.at_target = True

                self._pid_last_error = error
                await asyncio.sleep(0.01)  # 100Hz control loop

        except Exception as e:
            self._logger.error(f"Position control loop error: {e}")
            self._current_status.is_moving = False

    async def _velocity_control_loop(self, target_velocity: float) -> None:
        """Velocity control loop."""
        try:
            while abs(target_velocity) > 0.1:  # Stop when velocity is near zero
                # Simple velocity control (in practice, use more sophisticated control)
                self._current_status.current_velocity = target_velocity

                # Update position based on velocity
                if self._current_status.current_position is not None:
                    self._current_status.current_position += target_velocity * 0.01

                await asyncio.sleep(0.01)  # 100Hz control loop

        except Exception as e:
            self._logger.error(f"Velocity control loop error: {e}")

    async def _update_status(self) -> None:
        """Update servo status."""
        self._current_status.timestamp = time.time()

        # Simulate encoder feedback (in practice, read from actual encoder)
        if self._current_status.current_position is None:
            self._current_status.current_position = 0.0

        # Check if at target
        if self._current_status.target_position is not None:
            self._current_status.at_target = await self.is_at_target()

    def _add_servo_capabilities(self) -> None:
        """Add servo actuator capabilities."""
        self.add_capability(DeviceCapability(
            name="position",
            description="Servo position",
            data_type="float",
            unit="deg",
            range_min=self._limits.min_position,
            range_max=self._limits.max_position,
            read_only=False
        ))

        self.add_capability(DeviceCapability(
            name="velocity",
            description="Servo velocity",
            data_type="float",
            unit="deg/s",
            range_min=-self._limits.max_velocity,
            range_max=self._limits.max_velocity,
            read_only=False
        ))

        self.add_capability(DeviceCapability(
            name="force",
            description="Servo torque",
            data_type="float",
            unit="Nm",
            range_min=-self._limits.max_force,
            range_max=self._limits.max_force,
            read_only=False
        ))


class StepperMotor(ActuatorInterface):
    """
    Stepper motor actuator implementation.

    Provides precise position control through step counting,
    with configurable step size and acceleration profiles.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize stepper motor."""
        super().__init__(config)
        self._actuator_type = ActuatorType.STEPPER
        self._steps_per_revolution = config.operational_params.get('steps_per_revolution', 200)
        self._microstep_resolution = config.operational_params.get('microstep_resolution', 16)
        self._current_step = 0
        self._target_step = 0

        # Initialize stepper capabilities
        self._add_stepper_capabilities()

    async def initialize(self) -> bool:
        """Initialize stepper motor."""
        self._logger.info(f"Initializing stepper motor {self.device_id}")

        # Initialize stepper driver (simulated)
        await asyncio.sleep(0.1)

        self._current_status.current_position = 0.0
        return True

    async def shutdown(self) -> bool:
        """Shutdown stepper motor."""
        await self.stop()
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read stepper motor data."""
        position_deg = (self._current_step / (self._steps_per_revolution * self._microstep_resolution)) * 360.0
        self._current_status.current_position = position_deg

        if channel == "position":
            return {"position": position_deg}
        elif channel == "steps":
            return {"steps": self._current_step}
        else:
            return {
                "position": position_deg,
                "steps": self._current_step,
                "target_steps": self._target_step,
                "is_moving": self._current_status.is_moving
            }

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to stepper motor."""
        if "position" in data:
            return await self.move_to_position(data["position"])
        elif "steps" in data:
            return await self.move_to_step(data["steps"])
        return True

    async def self_test(self) -> Dict[str, Any]:
        """Perform stepper motor self-test."""
        test_results = await super().self_test()

        try:
            # Test step movement
            initial_step = self._current_step
            await self.move_steps(100)  # Move 100 steps
            await asyncio.sleep(0.2)

            step_error = abs(self._current_step - (initial_step + 100))
            test_results['step_accuracy'] = step_error < 2

            # Return to initial position
            await self.move_to_step(initial_step)

        except Exception as e:
            test_results['stepper_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def move_to_position(self, position: float, velocity: Optional[float] = None) -> bool:
        """Move stepper to specific position."""
        try:
            # Convert position to steps
            target_step = int((position / 360.0) * self._steps_per_revolution * self._microstep_resolution)
            return await self.move_to_step(target_step)
        except Exception as e:
            self._logger.error(f"Failed to move to position {position}: {e}")
            return False

    async def move_to_step(self, target_step: int) -> bool:
        """Move stepper to specific step."""
        try:
            self._target_step = target_step
            self._current_status.is_moving = True

            # Start stepping
            asyncio.create_task(self._step_control_loop(target_step))
            return True

        except Exception as e:
            self._logger.error(f"Failed to move to step {target_step}: {e}")
            return False

    async def move_steps(self, step_count: int) -> bool:
        """Move stepper by relative step count."""
        target_step = self._current_step + step_count
        return await self.move_to_step(target_step)

    async def set_velocity(self, velocity: float) -> bool:
        """Set stepper velocity (not directly applicable)."""
        # Stepper motors use step rate rather than continuous velocity
        self._logger.warning("Velocity control not directly applicable to stepper motors")
        return False

    async def set_force(self, force: float) -> bool:
        """Set stepper force (holding torque)."""
        # Stepper motors have fixed holding torque
        self._logger.warning("Force control not applicable to stepper motors")
        return False

    async def stop(self) -> bool:
        """Stop stepper motion."""
        self._current_status.is_moving = False
        return True

    async def home(self) -> bool:
        """Home stepper motor."""
        return await self.move_to_step(0)

    async def _step_control_loop(self, target_step: int) -> None:
        """Step control loop."""
        try:
            step_direction = 1 if target_step > self._current_step else -1
            step_rate = 1000  # Steps per second

            while self._current_step != target_step and self._current_status.is_moving:
                self._current_step += step_direction
                await asyncio.sleep(1.0 / step_rate)

            self._current_status.is_moving = False
            self._current_status.at_target = True

        except Exception as e:
            self._logger.error(f"Step control loop error: {e}")
            self._current_status.is_moving = False

    def _add_stepper_capabilities(self) -> None:
        """Add stepper motor capabilities."""
        max_steps = self._steps_per_revolution * self._microstep_resolution * 10  # 10 revolutions

        self.add_capability(DeviceCapability(
            name="position",
            description="Stepper position",
            data_type="float",
            unit="deg",
            range_min=-3600.0,  # -10 revolutions
            range_max=3600.0,   # +10 revolutions
            read_only=False
        ))

        self.add_capability(DeviceCapability(
            name="steps",
            description="Step count",
            data_type="int",
            unit="steps",
            range_min=-max_steps,
            range_max=max_steps,
            read_only=False
        ))


class PneumaticActuator(ActuatorInterface):
    """
    Pneumatic actuator implementation.

    Provides pressure-based control for linear and rotary
    pneumatic actuators with pressure feedback.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize pneumatic actuator."""
        super().__init__(config)
        self._actuator_type = ActuatorType.PNEUMATIC
        self._max_pressure = config.operational_params.get('max_pressure', 6.0)  # bar
        self._cylinder_diameter = config.operational_params.get('cylinder_diameter', 50.0)  # mm
        self._stroke_length = config.operational_params.get('stroke_length', 100.0)  # mm
        self._current_pressure = 0.0

        # Initialize pneumatic capabilities
        self._add_pneumatic_capabilities()

    async def initialize(self) -> bool:
        """Initialize pneumatic actuator."""
        self._logger.info(f"Initializing pneumatic actuator {self.device_id}")

        # Initialize pneumatic valves and pressure sensors (simulated)
        await asyncio.sleep(0.1)

        self._current_status.current_position = 0.0
        return True

    async def shutdown(self) -> bool:
        """Shutdown pneumatic actuator."""
        await self.set_pressure(0.0)  # Release pressure
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read pneumatic actuator data."""
        if channel == "position":
            return {"position": self._current_status.current_position}
        elif channel == "pressure":
            return {"pressure": self._current_pressure}
        elif channel == "force":
            return {"force": self._current_status.current_force}
        else:
            return {
                "position": self._current_status.current_position,
                "pressure": self._current_pressure,
                "force": self._current_status.current_force,
                "is_moving": self._current_status.is_moving
            }

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to pneumatic actuator."""
        if "pressure" in data:
            return await self.set_pressure(data["pressure"])
        elif "position" in data:
            return await self.move_to_position(data["position"])
        return True

    async def self_test(self) -> Dict[str, Any]:
        """Perform pneumatic actuator self-test."""
        test_results = await super().self_test()

        try:
            # Test pressure control
            await self.set_pressure(2.0)  # 2 bar
            await asyncio.sleep(0.5)
            test_results['pressure_control'] = abs(self._current_pressure - 2.0) < 0.2

            # Test position control
            initial_position = self._current_status.current_position
            await self.move_to_position(50.0)  # Move to middle
            await asyncio.sleep(1.0)
            position_error = abs(self._current_status.current_position - 50.0)
            test_results['position_control'] = position_error < 5.0

            # Return to initial state
            await self.move_to_position(initial_position)
            await self.set_pressure(0.0)

        except Exception as e:
            test_results['pneumatic_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def move_to_position(self, position: float, velocity: Optional[float] = None) -> bool:
        """Move pneumatic actuator to position."""
        try:
            # Calculate required pressure for position
            pressure_ratio = position / self._stroke_length
            required_pressure = pressure_ratio * self._max_pressure

            self._current_status.target_position = position
            return await self.set_pressure(required_pressure)

        except Exception as e:
            self._logger.error(f"Failed to move to position {position}: {e}")
            return False

    async def set_pressure(self, pressure: float) -> bool:
        """Set pneumatic pressure."""
        try:
            if pressure > self._max_pressure:
                self._logger.warning(f"Pressure {pressure} exceeds maximum {self._max_pressure}")
                pressure = self._max_pressure

            self._current_pressure = pressure

            # Calculate position based on pressure
            position_ratio = pressure / self._max_pressure
            new_position = position_ratio * self._stroke_length
            self._current_status.current_position = new_position

            # Calculate force
            cylinder_area = np.pi * (self._cylinder_diameter / 2) ** 2  # mm²
            force = pressure * 100000 * (cylinder_area / 1000000)  # Convert to Newtons
            self._current_status.current_force = force

            return True

        except Exception as e:
            self._logger.error(f"Failed to set pressure {pressure}: {e}")
            return False

    async def set_velocity(self, velocity: float) -> bool:
        """Set pneumatic velocity (flow rate control)."""
        # Pneumatic velocity control typically done through flow restrictors
        self._logger.warning("Velocity control requires flow rate control valves")
        return False

    async def set_force(self, force: float) -> bool:
        """Set pneumatic force."""
        try:
            # Calculate required pressure for force
            cylinder_area = np.pi * (self._cylinder_diameter / 2) ** 2  # mm²
            required_pressure = force / (100000 * (cylinder_area / 1000000))  # bar
            return await self.set_pressure(required_pressure)

        except Exception as e:
            self._logger.error(f"Failed to set force {force}: {e}")
            return False

    async def stop(self) -> bool:
        """Stop pneumatic motion."""
        # For pneumatic actuators, "stop" typically means hold current position
        return True

    async def home(self) -> bool:
        """Move pneumatic actuator to home position."""
        return await self.move_to_position(0.0)

    def _add_pneumatic_capabilities(self) -> None:
        """Add pneumatic actuator capabilities."""
        self.add_capability(DeviceCapability(
            name="position",
            description="Pneumatic actuator position",
            data_type="float",
            unit="mm",
            range_min=0.0,
            range_max=self._stroke_length,
            read_only=False
        ))

        self.add_capability(DeviceCapability(
            name="pressure",
            description="Pneumatic pressure",
            data_type="float",
            unit="bar",
            range_min=0.0,
            range_max=self._max_pressure,
            read_only=False
        ))

        # Calculate maximum force
        cylinder_area = np.pi * (self._cylinder_diameter / 2) ** 2  # mm²
        max_force = self._max_pressure * 100000 * (cylinder_area / 1000000)  # Newtons

        self.add_capability(DeviceCapability(
            name="force",
            description="Pneumatic force",
            data_type="float",
            unit="N",
            range_min=0.0,
            range_max=max_force,
            read_only=True
        ))