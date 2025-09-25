#==========================================================================================\\\
#======================== src/interfaces/hardware/sensors.py ============================\\\
#==========================================================================================\\\
"""
Sensor interface framework for control systems.
This module provides standardized interfaces for various sensor types
commonly used in control systems, including analog sensors, digital sensors,
IMU sensors, and specialized measurement devices.
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


class SensorType(Enum):
    """Sensor type enumeration."""
    ANALOG = "analog"
    DIGITAL = "digital"
    IMU = "imu"
    ENCODER = "encoder"
    FORCE = "force"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    POSITION = "position"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"


@dataclass
class SensorReading:
    """Sensor reading data structure."""
    timestamp: float
    sensor_id: str
    channel: str
    value: float
    unit: str
    quality: float = 1.0  # 0.0 to 1.0
    status: str = "ok"
    raw_value: Optional[float] = None
    calibrated: bool = True


@dataclass
class SensorCalibration:
    """Sensor calibration parameters."""
    offset: float = 0.0
    scale: float = 1.0
    polynomial_coeffs: Optional[List[float]] = None
    temperature_compensation: Optional[Dict[str, float]] = None
    nonlinearity_correction: Optional[Dict[str, float]] = None
    last_calibrated: Optional[float] = None


class SensorInterface(DeviceDriver, ABC):
    """
    Abstract base class for sensor interfaces.

    This class defines the standard interface for all sensor types,
    providing common functionality for calibration, filtering,
    and data acquisition.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize sensor interface."""
        super().__init__(config)
        self._sensor_type = SensorType.ANALOG
        self._calibration: Dict[str, SensorCalibration] = {}
        self._readings_history: Dict[str, List[SensorReading]] = {}
        self._max_history_size = config.operational_params.get('max_history_size', 1000)
        self._noise_filter_enabled = config.operational_params.get('noise_filter_enabled', False)
        self._filter_window_size = config.operational_params.get('filter_window_size', 5)

    @property
    def sensor_type(self) -> SensorType:
        """Get sensor type."""
        return self._sensor_type

    @abstractmethod
    async def read_channel(self, channel: str) -> SensorReading:
        """
        Read from specific sensor channel.

        Parameters
        ----------
        channel : str
            Channel identifier

        Returns
        -------
        SensorReading
            Sensor reading data
        """
        pass

    async def read_all_channels(self) -> Dict[str, SensorReading]:
        """Read from all available channels."""
        readings = {}
        for capability in self._capabilities:
            if not capability.read_only:
                continue
            try:
                reading = await self.read_channel(capability.name)
                readings[capability.name] = reading
            except Exception as e:
                self._logger.warning(f"Failed to read channel {capability.name}: {e}")

        return readings

    async def get_reading_history(self, channel: str, count: Optional[int] = None) -> List[SensorReading]:
        """Get historical readings for channel."""
        history = self._readings_history.get(channel, [])
        if count is None:
            return history.copy()
        return history[-count:] if count <= len(history) else history.copy()

    async def calibrate_channel(self, channel: str, calibration: SensorCalibration) -> bool:
        """Calibrate specific channel."""
        try:
            self._calibration[channel] = calibration
            calibration.last_calibrated = time.time()
            self._logger.info(f"Calibrated channel {channel} on sensor {self.device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to calibrate channel {channel}: {e}")
            return False

    async def get_statistics(self, channel: str, window_size: Optional[int] = None) -> Dict[str, float]:
        """Get statistical analysis of channel readings."""
        history = await self.get_reading_history(channel, window_size)
        if not history:
            return {}

        values = [reading.value for reading in history]
        statistics = {
            'count': len(values),
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'median': np.median(values),
            'variance': np.var(values)
        }

        if len(values) > 1:
            statistics['range'] = statistics['max'] - statistics['min']
            statistics['coefficient_of_variation'] = statistics['std'] / statistics['mean'] if statistics['mean'] != 0 else 0

        return statistics

    def _apply_calibration(self, raw_value: float, channel: str) -> float:
        """Apply calibration to raw sensor value."""
        if channel not in self._calibration:
            return raw_value

        cal = self._calibration[channel]
        calibrated_value = raw_value * cal.scale + cal.offset

        # Apply polynomial correction if available
        if cal.polynomial_coeffs:
            poly_correction = sum(
                coeff * (calibrated_value ** i)
                for i, coeff in enumerate(cal.polynomial_coeffs)
            )
            calibrated_value += poly_correction

        return calibrated_value

    def _apply_noise_filter(self, reading: SensorReading, channel: str) -> SensorReading:
        """Apply noise filtering to sensor reading."""
        if not self._noise_filter_enabled:
            return reading

        history = self._readings_history.get(channel, [])
        if len(history) < self._filter_window_size:
            return reading

        # Simple moving average filter
        recent_values = [r.value for r in history[-self._filter_window_size:]]
        filtered_value = np.mean(recent_values)

        # Create filtered reading
        filtered_reading = SensorReading(
            timestamp=reading.timestamp,
            sensor_id=reading.sensor_id,
            channel=reading.channel,
            value=filtered_value,
            unit=reading.unit,
            quality=reading.quality,
            status=reading.status,
            raw_value=reading.value,  # Store original value
            calibrated=reading.calibrated
        )

        return filtered_reading

    def _store_reading(self, reading: SensorReading) -> None:
        """Store reading in history."""
        channel = reading.channel
        if channel not in self._readings_history:
            self._readings_history[channel] = []

        self._readings_history[channel].append(reading)

        # Limit history size
        if len(self._readings_history[channel]) > self._max_history_size:
            self._readings_history[channel].pop(0)


class AnalogSensor(SensorInterface):
    """
    Analog sensor implementation for continuous value measurements.

    Supports voltage, current, and resistance measurements with
    configurable ADC resolution and reference voltages.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize analog sensor."""
        super().__init__(config)
        self._sensor_type = SensorType.ANALOG
        self._adc_resolution = config.operational_params.get('adc_resolution', 12)
        self._reference_voltage = config.operational_params.get('reference_voltage', 5.0)
        self._measurement_range = config.operational_params.get('measurement_range', (0.0, 5.0))

        # Add analog capabilities
        self._add_analog_capabilities()

    async def initialize(self) -> bool:
        """Initialize analog sensor."""
        self._logger.info(f"Initializing analog sensor {self.device_id}")

        # Simulate ADC initialization
        await asyncio.sleep(0.1)

        # Perform initial calibration if configured
        initial_cal = self._config.calibration_params
        if initial_cal:
            for channel, cal_params in initial_cal.items():
                calibration = SensorCalibration(**cal_params)
                await self.calibrate_channel(channel, calibration)

        return True

    async def shutdown(self) -> bool:
        """Shutdown analog sensor."""
        self._logger.info(f"Shutting down analog sensor {self.device_id}")
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read analog sensor data."""
        if channel:
            reading = await self.read_channel(channel)
            return {channel: reading.value}
        else:
            readings = await self.read_all_channels()
            return {ch: reading.value for ch, reading in readings.items()}

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to analog sensor (for configuration)."""
        # Analog sensors typically don't support write operations
        # This could be used for configuration changes
        return True

    async def self_test(self) -> Dict[str, Any]:
        """Perform analog sensor self-test."""
        test_results = await super().self_test()

        # Test ADC functionality
        try:
            # Read from all channels
            readings = await self.read_all_channels()
            test_results['channel_count'] = len(readings)
            test_results['adc_functional'] = True

            # Check if readings are within expected ranges
            for channel, reading in readings.items():
                min_val, max_val = self._measurement_range
                if not (min_val <= reading.value <= max_val):
                    test_results[f'{channel}_range_check'] = False
                    test_results['overall_status'] = 'FAIL'
                else:
                    test_results[f'{channel}_range_check'] = True

        except Exception as e:
            test_results['adc_functional'] = False
            test_results['adc_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def read_channel(self, channel: str) -> SensorReading:
        """Read from specific analog channel."""
        try:
            # Simulate ADC reading
            raw_adc = await self._read_adc_channel(channel)

            # Convert ADC value to voltage
            voltage = (raw_adc / (2**self._adc_resolution)) * self._reference_voltage

            # Apply calibration
            calibrated_value = self._apply_calibration(voltage, channel)

            # Create reading
            reading = SensorReading(
                timestamp=time.time(),
                sensor_id=self.device_id,
                channel=channel,
                value=calibrated_value,
                unit="V",
                raw_value=voltage,
                calibrated=channel in self._calibration
            )

            # Apply filtering
            filtered_reading = self._apply_noise_filter(reading, channel)

            # Store in history
            self._store_reading(filtered_reading)

            return filtered_reading

        except Exception as e:
            self._logger.error(f"Failed to read analog channel {channel}: {e}")
            raise

    async def _read_adc_channel(self, channel: str) -> int:
        """Read raw ADC value from channel."""
        # Simulate ADC reading with some noise
        base_value = hash(channel) % (2**self._adc_resolution)
        noise = np.random.randint(-10, 11)
        raw_value = max(0, min(2**self._adc_resolution - 1, base_value + noise))
        return raw_value

    def _add_analog_capabilities(self) -> None:
        """Add analog sensor capabilities."""
        channel_count = self._config.operational_params.get('channel_count', 4)
        for i in range(channel_count):
            self.add_capability(DeviceCapability(
                name=f"analog_{i}",
                description=f"Analog input channel {i}",
                data_type="float",
                unit="V",
                range_min=self._measurement_range[0],
                range_max=self._measurement_range[1],
                resolution=self._reference_voltage / (2**self._adc_resolution),
                read_only=True
            ))


class DigitalSensor(SensorInterface):
    """
    Digital sensor implementation for binary state measurements.

    Supports GPIO, switch, and digital encoder inputs with
    configurable pull-up/pull-down resistors and debouncing.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize digital sensor."""
        super().__init__(config)
        self._sensor_type = SensorType.DIGITAL
        self._debounce_time = config.operational_params.get('debounce_time', 0.05)
        self._last_state_change: Dict[str, float] = {}
        self._current_states: Dict[str, bool] = {}

        # Add digital capabilities
        self._add_digital_capabilities()

    async def initialize(self) -> bool:
        """Initialize digital sensor."""
        self._logger.info(f"Initializing digital sensor {self.device_id}")

        # Initialize GPIO pins (simulated)
        await asyncio.sleep(0.1)

        # Initialize state tracking
        for capability in self._capabilities:
            self._current_states[capability.name] = False
            self._last_state_change[capability.name] = 0.0

        return True

    async def shutdown(self) -> bool:
        """Shutdown digital sensor."""
        self._logger.info(f"Shutting down digital sensor {self.device_id}")
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read digital sensor data."""
        if channel:
            reading = await self.read_channel(channel)
            return {channel: reading.value}
        else:
            readings = await self.read_all_channels()
            return {ch: reading.value for ch, reading in readings.items()}

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to digital sensor (for configuration)."""
        # Digital sensors typically don't support write operations
        return True

    async def self_test(self) -> Dict[str, Any]:
        """Perform digital sensor self-test."""
        test_results = await super().self_test()

        # Test GPIO functionality
        try:
            readings = await self.read_all_channels()
            test_results['gpio_functional'] = True
            test_results['channel_count'] = len(readings)

            # Test debouncing by checking state change tracking
            test_results['debounce_functional'] = len(self._last_state_change) > 0

        except Exception as e:
            test_results['gpio_functional'] = False
            test_results['gpio_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def read_channel(self, channel: str) -> SensorReading:
        """Read from specific digital channel."""
        try:
            # Read raw digital state
            raw_state = await self._read_gpio_channel(channel)

            # Apply debouncing
            debounced_state = self._apply_debouncing(raw_state, channel)

            # Create reading
            reading = SensorReading(
                timestamp=time.time(),
                sensor_id=self.device_id,
                channel=channel,
                value=float(debounced_state),
                unit="bool",
                raw_value=float(raw_state)
            )

            # Store in history
            self._store_reading(reading)

            return reading

        except Exception as e:
            self._logger.error(f"Failed to read digital channel {channel}: {e}")
            raise

    async def get_edge_events(self, channel: str, since: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get edge events (rising/falling) for digital channel."""
        if since is None:
            since = time.time() - 60.0  # Last minute by default

        history = await self.get_reading_history(channel)
        events = []

        for i in range(1, len(history)):
            prev_reading = history[i-1]
            curr_reading = history[i]

            if curr_reading.timestamp < since:
                continue

            if prev_reading.value != curr_reading.value:
                edge_type = "rising" if curr_reading.value > prev_reading.value else "falling"
                events.append({
                    'timestamp': curr_reading.timestamp,
                    'edge_type': edge_type,
                    'value': curr_reading.value
                })

        return events

    async def _read_gpio_channel(self, channel: str) -> bool:
        """Read raw GPIO state from channel."""
        # Simulate GPIO reading
        return (hash(f"{channel}_{time.time()}") % 100) < 30  # 30% chance of being high

    def _apply_debouncing(self, raw_state: bool, channel: str) -> bool:
        """Apply debouncing to digital signal."""
        current_time = time.time()
        last_change_time = self._last_state_change.get(channel, 0.0)
        current_state = self._current_states.get(channel, False)

        # Check if enough time has passed since last state change
        if (current_time - last_change_time) < self._debounce_time:
            return current_state

        # Update state if it has changed
        if raw_state != current_state:
            self._current_states[channel] = raw_state
            self._last_state_change[channel] = current_time

        return self._current_states[channel]

    def _add_digital_capabilities(self) -> None:
        """Add digital sensor capabilities."""
        pin_count = self._config.operational_params.get('pin_count', 8)
        for i in range(pin_count):
            self.add_capability(DeviceCapability(
                name=f"digital_{i}",
                description=f"Digital input pin {i}",
                data_type="bool",
                unit="bool",
                range_min=0.0,
                range_max=1.0,
                read_only=True
            ))


class IMUSensor(SensorInterface):
    """
    Inertial Measurement Unit sensor implementation.

    Provides accelerometer, gyroscope, and magnetometer readings
    with sensor fusion and orientation calculation capabilities.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize IMU sensor."""
        super().__init__(config)
        self._sensor_type = SensorType.IMU
        self._accelerometer_range = config.operational_params.get('accelerometer_range', 16)  # ±g
        self._gyroscope_range = config.operational_params.get('gyroscope_range', 2000)  # ±dps
        self._magnetometer_enabled = config.operational_params.get('magnetometer_enabled', True)
        self._fusion_enabled = config.operational_params.get('sensor_fusion_enabled', True)

        # Orientation tracking
        self._orientation = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        self._last_fusion_update = 0.0

        # Add IMU capabilities
        self._add_imu_capabilities()

    async def initialize(self) -> bool:
        """Initialize IMU sensor."""
        self._logger.info(f"Initializing IMU sensor {self.device_id}")

        # Initialize IMU chip (simulated)
        await asyncio.sleep(0.2)

        # Perform initial calibration if configured
        if 'gyro_bias' in self._config.calibration_params:
            gyro_cal = SensorCalibration(**self._config.calibration_params['gyro_bias'])
            await self.calibrate_channel('gyro_bias', gyro_cal)

        return True

    async def shutdown(self) -> bool:
        """Shutdown IMU sensor."""
        self._logger.info(f"Shutting down IMU sensor {self.device_id}")
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read IMU sensor data."""
        if channel:
            reading = await self.read_channel(channel)
            return {channel: reading.value}
        else:
            # Read all IMU channels
            imu_data = await self._read_imu_data()
            return imu_data

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to IMU sensor (for configuration)."""
        # IMU sensors typically don't support write operations
        return True

    async def self_test(self) -> Dict[str, Any]:
        """Perform IMU sensor self-test."""
        test_results = await super().self_test()

        try:
            # Test accelerometer
            accel_data = await self._read_accelerometer()
            accel_magnitude = np.sqrt(sum(v**2 for v in accel_data.values()))
            test_results['accelerometer_functional'] = 0.8 < accel_magnitude < 1.2  # ~1g

            # Test gyroscope
            gyro_data = await self._read_gyroscope()
            gyro_magnitude = np.sqrt(sum(v**2 for v in gyro_data.values()))
            test_results['gyroscope_functional'] = gyro_magnitude < 10.0  # Low noise when stationary

            # Test magnetometer if enabled
            if self._magnetometer_enabled:
                mag_data = await self._read_magnetometer()
                mag_magnitude = np.sqrt(sum(v**2 for v in mag_data.values()))
                test_results['magnetometer_functional'] = 0.2 < mag_magnitude < 1.0

            test_results['imu_overall'] = all([
                test_results.get('accelerometer_functional', False),
                test_results.get('gyroscope_functional', False),
                test_results.get('magnetometer_functional', True)  # Optional
            ])

        except Exception as e:
            test_results['imu_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def read_channel(self, channel: str) -> SensorReading:
        """Read from specific IMU channel."""
        try:
            current_time = time.time()

            # Read appropriate sensor data based on channel
            if channel.startswith('accel_'):
                data = await self._read_accelerometer()
                axis = channel.split('_')[1]
                value = data[axis]
                unit = "g"
            elif channel.startswith('gyro_'):
                data = await self._read_gyroscope()
                axis = channel.split('_')[1]
                value = data[axis]
                unit = "dps"
            elif channel.startswith('mag_'):
                data = await self._read_magnetometer()
                axis = channel.split('_')[1]
                value = data[axis]
                unit = "uT"
            elif channel.startswith('orientation_'):
                await self._update_sensor_fusion()
                axis = channel.split('_')[1]
                value = self._orientation[axis]
                unit = "deg"
            else:
                raise ValueError(f"Unknown IMU channel: {channel}")

            # Create reading
            reading = SensorReading(
                timestamp=current_time,
                sensor_id=self.device_id,
                channel=channel,
                value=value,
                unit=unit
            )

            # Store in history
            self._store_reading(reading)

            return reading

        except Exception as e:
            self._logger.error(f"Failed to read IMU channel {channel}: {e}")
            raise

    async def get_orientation(self) -> Dict[str, float]:
        """Get current orientation (roll, pitch, yaw)."""
        await self._update_sensor_fusion()
        return self._orientation.copy()

    async def _read_imu_data(self) -> Dict[str, float]:
        """Read all IMU sensor data."""
        data = {}

        # Read accelerometer
        accel_data = await self._read_accelerometer()
        data.update({f"accel_{axis}": value for axis, value in accel_data.items()})

        # Read gyroscope
        gyro_data = await self._read_gyroscope()
        data.update({f"gyro_{axis}": value for axis, value in gyro_data.items()})

        # Read magnetometer if enabled
        if self._magnetometer_enabled:
            mag_data = await self._read_magnetometer()
            data.update({f"mag_{axis}": value for axis, value in mag_data.items()})

        # Update sensor fusion
        if self._fusion_enabled:
            await self._update_sensor_fusion()
            data.update({f"orientation_{axis}": value for axis, value in self._orientation.items()})

        return data

    async def _read_accelerometer(self) -> Dict[str, float]:
        """Read accelerometer data."""
        # Simulate accelerometer readings
        return {
            'x': np.random.normal(0.0, 0.1),  # Simulated gravity + noise
            'y': np.random.normal(0.0, 0.1),
            'z': np.random.normal(1.0, 0.1)   # Gravity in Z-axis
        }

    async def _read_gyroscope(self) -> Dict[str, float]:
        """Read gyroscope data."""
        # Simulate gyroscope readings
        return {
            'x': np.random.normal(0.0, 1.0),  # Simulated angular velocity
            'y': np.random.normal(0.0, 1.0),
            'z': np.random.normal(0.0, 1.0)
        }

    async def _read_magnetometer(self) -> Dict[str, float]:
        """Read magnetometer data."""
        # Simulate magnetometer readings
        return {
            'x': np.random.normal(0.3, 0.05),  # Simulated magnetic field
            'y': np.random.normal(0.1, 0.05),
            'z': np.random.normal(-0.5, 0.05)
        }

    async def _update_sensor_fusion(self) -> None:
        """Update sensor fusion for orientation calculation."""
        current_time = time.time()
        dt = current_time - self._last_fusion_update

        if dt < 0.01:  # Update at most every 10ms
            return

        try:
            # Simple complementary filter (in practice, use more sophisticated algorithms)
            accel_data = await self._read_accelerometer()
            gyro_data = await self._read_gyroscope()

            # Calculate orientation from accelerometer
            accel_roll = np.degrees(np.arctan2(accel_data['y'], accel_data['z']))
            accel_pitch = np.degrees(np.arctan2(-accel_data['x'],
                                               np.sqrt(accel_data['y']**2 + accel_data['z']**2)))

            # Integrate gyroscope for orientation change
            if self._last_fusion_update > 0:
                self._orientation['roll'] = 0.98 * (self._orientation['roll'] + gyro_data['x'] * dt) + 0.02 * accel_roll
                self._orientation['pitch'] = 0.98 * (self._orientation['pitch'] + gyro_data['y'] * dt) + 0.02 * accel_pitch
                self._orientation['yaw'] += gyro_data['z'] * dt  # Yaw drift without magnetometer

            self._last_fusion_update = current_time

        except Exception as e:
            self._logger.error(f"Error in sensor fusion: {e}")

    def _add_imu_capabilities(self) -> None:
        """Add IMU sensor capabilities."""
        # Accelerometer channels
        for axis in ['x', 'y', 'z']:
            self.add_capability(DeviceCapability(
                name=f"accel_{axis}",
                description=f"Accelerometer {axis.upper()}-axis",
                data_type="float",
                unit="g",
                range_min=-self._accelerometer_range,
                range_max=self._accelerometer_range,
                read_only=True
            ))

        # Gyroscope channels
        for axis in ['x', 'y', 'z']:
            self.add_capability(DeviceCapability(
                name=f"gyro_{axis}",
                description=f"Gyroscope {axis.upper()}-axis",
                data_type="float",
                unit="dps",
                range_min=-self._gyroscope_range,
                range_max=self._gyroscope_range,
                read_only=True
            ))

        # Magnetometer channels (if enabled)
        if self._magnetometer_enabled:
            for axis in ['x', 'y', 'z']:
                self.add_capability(DeviceCapability(
                    name=f"mag_{axis}",
                    description=f"Magnetometer {axis.upper()}-axis",
                    data_type="float",
                    unit="uT",
                    range_min=-100.0,
                    range_max=100.0,
                    read_only=True
                ))

        # Orientation channels (if fusion enabled)
        if self._fusion_enabled:
            for axis in ['roll', 'pitch', 'yaw']:
                self.add_capability(DeviceCapability(
                    name=f"orientation_{axis}",
                    description=f"Orientation {axis}",
                    data_type="float",
                    unit="deg",
                    range_min=-180.0,
                    range_max=180.0,
                    read_only=True
                ))