#==========================================================================================\\\
#====================== src/interfaces/hardware/daq_systems.py ==========================\\\
#==========================================================================================\\\
"""
Data acquisition (DAQ) system interfaces for control systems.
This module provides standardized interfaces for various DAQ systems
including National Instruments DAQ, ADC converters, and multi-channel
data acquisition hardware commonly used in control applications.
"""

import asyncio
import time
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
import logging

from .device_drivers import DeviceDriver, DeviceConfig, DeviceCapability, DeviceState

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType, TerminalConfiguration
    NIDAQMX_AVAILABLE = True
except ImportError:
    NIDAQMX_AVAILABLE = False


class DAQMode(Enum):
    """DAQ operation mode enumeration."""
    SINGLE_POINT = "single_point"
    CONTINUOUS = "continuous"
    FINITE = "finite"
    ON_DEMAND = "on_demand"


class ChannelType(Enum):
    """DAQ channel type enumeration."""
    ANALOG_INPUT = "analog_input"
    ANALOG_OUTPUT = "analog_output"
    DIGITAL_INPUT = "digital_input"
    DIGITAL_OUTPUT = "digital_output"
    COUNTER = "counter"
    PWM = "pwm"


@dataclass
class ChannelConfig:
    """DAQ channel configuration."""
    name: str
    channel_type: ChannelType
    physical_channel: str
    min_val: float = -10.0
    max_val: float = 10.0
    units: str = "V"
    terminal_config: str = "default"
    coupling: str = "dc"
    sample_rate: float = 1000.0
    enabled: bool = True


@dataclass
class DAQSample:
    """DAQ sample data structure."""
    timestamp: float
    channel_name: str
    value: Union[float, bool, int]
    unit: str
    quality: float = 1.0
    sample_number: int = 0


@dataclass
class DAQBuffer:
    """DAQ buffer for storing samples."""
    channel_name: str
    samples: List[DAQSample] = field(default_factory=list)
    max_size: int = 10000
    overflow_count: int = 0

    def add_sample(self, sample: DAQSample) -> None:
        """Add sample to buffer."""
        if len(self.samples) >= self.max_size:
            self.samples.pop(0)
            self.overflow_count += 1
        self.samples.append(sample)

    def get_latest(self, count: int = 1) -> List[DAQSample]:
        """Get latest samples."""
        return self.samples[-count:] if count <= len(self.samples) else self.samples.copy()

    def clear(self) -> None:
        """Clear buffer."""
        self.samples.clear()
        self.overflow_count = 0


class DAQInterface(DeviceDriver, ABC):
    """
    Abstract base class for DAQ system interfaces.

    This class defines the standard interface for all DAQ systems,
    providing common functionality for multi-channel data acquisition,
    configuration management, and synchronization.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize DAQ interface."""
        super().__init__(config)
        self._channels: Dict[str, ChannelConfig] = {}
        self._buffers: Dict[str, DAQBuffer] = {}
        self._acquisition_mode = DAQMode.SINGLE_POINT
        self._sample_rate = config.operational_params.get('sample_rate', 1000.0)
        self._buffer_size = config.operational_params.get('buffer_size', 10000)
        self._acquisition_task: Optional[asyncio.Task] = None
        self._is_acquiring = False
        self._sample_count = 0

    @property
    def is_acquiring(self) -> bool:
        """Check if DAQ is currently acquiring data."""
        return self._is_acquiring

    @property
    def sample_rate(self) -> float:
        """Get current sample rate."""
        return self._sample_rate

    @property
    def channels(self) -> Dict[str, ChannelConfig]:
        """Get channel configurations."""
        return self._channels.copy()

    @abstractmethod
    async def configure_channel(self, channel_config: ChannelConfig) -> bool:
        """
        Configure a DAQ channel.

        Parameters
        ----------
        channel_config : ChannelConfig
            Channel configuration

        Returns
        -------
        bool
            True if configuration successful
        """
        pass

    @abstractmethod
    async def read_channel(self, channel_name: str) -> DAQSample:
        """
        Read single sample from channel.

        Parameters
        ----------
        channel_name : str
            Channel to read from

        Returns
        -------
        DAQSample
            Sample data
        """
        pass

    @abstractmethod
    async def write_channel(self, channel_name: str, value: Union[float, bool]) -> bool:
        """
        Write value to output channel.

        Parameters
        ----------
        channel_name : str
            Channel to write to
        value : Union[float, bool]
            Value to write

        Returns
        -------
        bool
            True if write successful
        """
        pass

    @abstractmethod
    async def start_acquisition(self, mode: DAQMode = DAQMode.CONTINUOUS) -> bool:
        """
        Start data acquisition.

        Parameters
        ----------
        mode : DAQMode
            Acquisition mode

        Returns
        -------
        bool
            True if acquisition started
        """
        pass

    @abstractmethod
    async def stop_acquisition(self) -> bool:
        """
        Stop data acquisition.

        Returns
        -------
        bool
            True if acquisition stopped
        """
        pass

    async def add_channel(self, channel_config: ChannelConfig) -> bool:
        """Add channel to DAQ system."""
        try:
            if await self.configure_channel(channel_config):
                self._channels[channel_config.name] = channel_config
                self._buffers[channel_config.name] = DAQBuffer(
                    channel_name=channel_config.name,
                    max_size=self._buffer_size
                )
                self._logger.info(f"Added channel {channel_config.name} to DAQ {self.device_id}")
                return True
            return False
        except Exception as e:
            self._logger.error(f"Failed to add channel {channel_config.name}: {e}")
            return False

    async def remove_channel(self, channel_name: str) -> bool:
        """Remove channel from DAQ system."""
        try:
            if channel_name in self._channels:
                del self._channels[channel_name]
                del self._buffers[channel_name]
                self._logger.info(f"Removed channel {channel_name} from DAQ {self.device_id}")
                return True
            return False
        except Exception as e:
            self._logger.error(f"Failed to remove channel {channel_name}: {e}")
            return False

    async def read_all_channels(self) -> Dict[str, DAQSample]:
        """Read from all configured channels."""
        samples = {}
        for channel_name in self._channels:
            try:
                sample = await self.read_channel(channel_name)
                samples[channel_name] = sample
            except Exception as e:
                self._logger.warning(f"Failed to read channel {channel_name}: {e}")
        return samples

    async def get_buffer_data(self, channel_name: str, count: Optional[int] = None) -> List[DAQSample]:
        """Get buffered data from channel."""
        if channel_name not in self._buffers:
            return []

        buffer = self._buffers[channel_name]
        if count is None:
            return buffer.samples.copy()
        return buffer.get_latest(count)

    async def clear_buffers(self) -> None:
        """Clear all channel buffers."""
        for buffer in self._buffers.values():
            buffer.clear()

    async def set_sample_rate(self, sample_rate: float) -> bool:
        """Set DAQ sample rate."""
        try:
            if self._is_acquiring:
                self._logger.warning("Cannot change sample rate during acquisition")
                return False

            self._sample_rate = sample_rate
            self._logger.info(f"Set sample rate to {sample_rate} Hz for DAQ {self.device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to set sample rate: {e}")
            return False

    def _store_sample(self, sample: DAQSample) -> None:
        """Store sample in buffer."""
        if sample.channel_name in self._buffers:
            self._buffers[sample.channel_name].add_sample(sample)


class NIDAQInterface(DAQInterface):
    """
    National Instruments DAQ interface implementation.

    Provides integration with NI-DAQmx for high-performance data
    acquisition using National Instruments hardware.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize NI-DAQ interface."""
        if not NIDAQMX_AVAILABLE:
            raise ImportError("NI-DAQmx not available. Install with: pip install nidaqmx")

        super().__init__(config)
        self._task: Optional[nidaqmx.Task] = None
        self._device_name = config.connection_params.get('device_name', 'Dev1')

    async def initialize(self) -> bool:
        """Initialize NI-DAQ interface."""
        self._logger.info(f"Initializing NI-DAQ interface {self.device_id}")

        try:
            # Verify device exists
            system = nidaqmx.system.System.local()
            devices = [device.name for device in system.devices]

            if self._device_name not in devices:
                self._logger.error(f"Device {self._device_name} not found. Available: {devices}")
                return False

            self._logger.info(f"NI-DAQ device {self._device_name} found and ready")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize NI-DAQ: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown NI-DAQ interface."""
        await self.stop_acquisition()
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read data from NI-DAQ."""
        if channel:
            sample = await self.read_channel(channel)
            return {channel: sample.value}
        else:
            samples = await self.read_all_channels()
            return {name: sample.value for name, sample in samples.items()}

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to NI-DAQ output channels."""
        try:
            for channel_name, value in data.items():
                if channel_name in self._channels:
                    await self.write_channel(channel_name, value)
            return True
        except Exception as e:
            self._logger.error(f"Failed to write data to NI-DAQ: {e}")
            return False

    async def self_test(self) -> Dict[str, Any]:
        """Perform NI-DAQ self-test."""
        test_results = await super().self_test()

        try:
            # Test device communication
            system = nidaqmx.system.System.local()
            device = system.devices[self._device_name]
            test_results['device_present'] = True
            test_results['device_type'] = device.product_type

            # Test analog input channels
            ai_channels = device.ai_physical_chans.channel_names
            test_results['ai_channels_available'] = len(ai_channels)

            # Test analog output channels
            ao_channels = device.ao_physical_chans.channel_names
            test_results['ao_channels_available'] = len(ao_channels)

            # Test digital I/O
            di_lines = device.di_lines.channel_names
            do_lines = device.do_lines.channel_names
            test_results['digital_lines_available'] = len(di_lines) + len(do_lines)

        except Exception as e:
            test_results['nidaq_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def configure_channel(self, channel_config: ChannelConfig) -> bool:
        """Configure NI-DAQ channel."""
        try:
            physical_channel = f"{self._device_name}/{channel_config.physical_channel}"

            # Add capability based on channel type
            if channel_config.channel_type == ChannelType.ANALOG_INPUT:
                capability = DeviceCapability(
                    name=channel_config.name,
                    description=f"Analog input {channel_config.physical_channel}",
                    data_type="float",
                    unit=channel_config.units,
                    range_min=channel_config.min_val,
                    range_max=channel_config.max_val,
                    read_only=True
                )
            elif channel_config.channel_type == ChannelType.ANALOG_OUTPUT:
                capability = DeviceCapability(
                    name=channel_config.name,
                    description=f"Analog output {channel_config.physical_channel}",
                    data_type="float",
                    unit=channel_config.units,
                    range_min=channel_config.min_val,
                    range_max=channel_config.max_val,
                    read_only=False
                )
            else:
                capability = DeviceCapability(
                    name=channel_config.name,
                    description=f"Channel {channel_config.physical_channel}",
                    data_type="float",
                    read_only=channel_config.channel_type in [ChannelType.ANALOG_INPUT, ChannelType.DIGITAL_INPUT]
                )

            self.add_capability(capability)
            self._logger.info(f"Configured NI-DAQ channel {channel_config.name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to configure channel {channel_config.name}: {e}")
            return False

    async def read_channel(self, channel_name: str) -> DAQSample:
        """Read single sample from NI-DAQ channel."""
        try:
            if channel_name not in self._channels:
                raise ValueError(f"Channel {channel_name} not configured")

            channel_config = self._channels[channel_name]
            physical_channel = f"{self._device_name}/{channel_config.physical_channel}"

            # Create temporary task for single-point read
            with nidaqmx.Task() as task:
                if channel_config.channel_type == ChannelType.ANALOG_INPUT:
                    task.ai_channels.add_ai_voltage_chan(
                        physical_channel,
                        min_val=channel_config.min_val,
                        max_val=channel_config.max_val
                    )
                    value = task.read()
                elif channel_config.channel_type == ChannelType.DIGITAL_INPUT:
                    task.di_channels.add_di_chan(physical_channel)
                    value = task.read()
                else:
                    raise ValueError(f"Cannot read from output channel {channel_name}")

                sample = DAQSample(
                    timestamp=time.time(),
                    channel_name=channel_name,
                    value=float(value) if isinstance(value, (int, float)) else value,
                    unit=channel_config.units,
                    sample_number=self._sample_count
                )

                self._sample_count += 1
                self._store_sample(sample)
                return sample

        except Exception as e:
            self._logger.error(f"Failed to read channel {channel_name}: {e}")
            raise

    async def write_channel(self, channel_name: str, value: Union[float, bool]) -> bool:
        """Write value to NI-DAQ output channel."""
        try:
            if channel_name not in self._channels:
                raise ValueError(f"Channel {channel_name} not configured")

            channel_config = self._channels[channel_name]
            physical_channel = f"{self._device_name}/{channel_config.physical_channel}"

            # Create temporary task for single-point write
            with nidaqmx.Task() as task:
                if channel_config.channel_type == ChannelType.ANALOG_OUTPUT:
                    task.ao_channels.add_ao_voltage_chan(
                        physical_channel,
                        min_val=channel_config.min_val,
                        max_val=channel_config.max_val
                    )
                    task.write(float(value))
                elif channel_config.channel_type == ChannelType.DIGITAL_OUTPUT:
                    task.do_channels.add_do_chan(physical_channel)
                    task.write(bool(value))
                else:
                    raise ValueError(f"Cannot write to input channel {channel_name}")

                return True

        except Exception as e:
            self._logger.error(f"Failed to write to channel {channel_name}: {e}")
            return False

    async def start_acquisition(self, mode: DAQMode = DAQMode.CONTINUOUS) -> bool:
        """Start NI-DAQ continuous acquisition."""
        try:
            if self._is_acquiring:
                self._logger.warning("Acquisition already in progress")
                return False

            input_channels = [
                (name, config) for name, config in self._channels.items()
                if config.channel_type in [ChannelType.ANALOG_INPUT, ChannelType.DIGITAL_INPUT]
            ]

            if not input_channels:
                self._logger.warning("No input channels configured for acquisition")
                return False

            self._acquisition_mode = mode
            self._is_acquiring = True

            # Start acquisition task
            self._acquisition_task = asyncio.create_task(self._acquisition_loop(input_channels))

            self._logger.info(f"Started NI-DAQ acquisition in {mode.value} mode")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start acquisition: {e}")
            self._is_acquiring = False
            return False

    async def stop_acquisition(self) -> bool:
        """Stop NI-DAQ acquisition."""
        try:
            self._is_acquiring = False

            if self._acquisition_task:
                self._acquisition_task.cancel()
                try:
                    await self._acquisition_task
                except asyncio.CancelledError:
                    pass

            if self._task:
                self._task.close()
                self._task = None

            self._logger.info("Stopped NI-DAQ acquisition")
            return True

        except Exception as e:
            self._logger.error(f"Failed to stop acquisition: {e}")
            return False

    async def _acquisition_loop(self, input_channels: List[Tuple[str, ChannelConfig]]) -> None:
        """Continuous acquisition loop."""
        try:
            while self._is_acquiring:
                # Read from all input channels
                for channel_name, channel_config in input_channels:
                    try:
                        sample = await self.read_channel(channel_name)
                        # Sample is already stored by read_channel
                    except Exception as e:
                        self._logger.warning(f"Error reading channel {channel_name}: {e}")

                # Wait for next sample
                await asyncio.sleep(1.0 / self._sample_rate)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Acquisition loop error: {e}")
            self._is_acquiring = False


class AdcInterface(DAQInterface):
    """
    Generic ADC interface implementation.

    Provides basic analog-to-digital conversion functionality
    for simple ADC chips and modules.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize ADC interface."""
        super().__init__(config)
        self._resolution = config.operational_params.get('resolution', 12)
        self._reference_voltage = config.operational_params.get('reference_voltage', 3.3)
        self._channel_count = config.operational_params.get('channel_count', 8)

        # Initialize ADC channels
        self._init_adc_channels()

    async def initialize(self) -> bool:
        """Initialize ADC interface."""
        self._logger.info(f"Initializing ADC interface {self.device_id}")

        # Initialize SPI/I2C communication (simulated)
        await asyncio.sleep(0.1)

        return True

    async def shutdown(self) -> bool:
        """Shutdown ADC interface."""
        await self.stop_acquisition()
        return True

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read data from ADC."""
        if channel:
            sample = await self.read_channel(channel)
            return {channel: sample.value}
        else:
            samples = await self.read_all_channels()
            return {name: sample.value for name, sample in samples.items()}

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to ADC (configuration only)."""
        # ADCs typically don't have output channels
        return True

    async def self_test(self) -> Dict[str, Any]:
        """Perform ADC self-test."""
        test_results = await super().self_test()

        try:
            # Test all channels
            for channel_name in self._channels:
                sample = await self.read_channel(channel_name)
                # Check if reading is within expected range
                if 0.0 <= sample.value <= self._reference_voltage:
                    test_results[f'{channel_name}_functional'] = True
                else:
                    test_results[f'{channel_name}_functional'] = False
                    test_results['overall_status'] = 'FAIL'

            test_results['resolution'] = self._resolution
            test_results['reference_voltage'] = self._reference_voltage

        except Exception as e:
            test_results['adc_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def configure_channel(self, channel_config: ChannelConfig) -> bool:
        """Configure ADC channel."""
        try:
            # Add capability
            capability = DeviceCapability(
                name=channel_config.name,
                description=f"ADC channel {channel_config.physical_channel}",
                data_type="float",
                unit="V",
                range_min=0.0,
                range_max=self._reference_voltage,
                resolution=self._reference_voltage / (2**self._resolution),
                read_only=True
            )

            self.add_capability(capability)
            self._logger.info(f"Configured ADC channel {channel_config.name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to configure ADC channel: {e}")
            return False

    async def read_channel(self, channel_name: str) -> DAQSample:
        """Read single sample from ADC channel."""
        try:
            if channel_name not in self._channels:
                raise ValueError(f"Channel {channel_name} not configured")

            # Simulate ADC reading
            raw_value = await self._read_adc_raw(channel_name)
            voltage = (raw_value / (2**self._resolution)) * self._reference_voltage

            sample = DAQSample(
                timestamp=time.time(),
                channel_name=channel_name,
                value=voltage,
                unit="V",
                sample_number=self._sample_count
            )

            self._sample_count += 1
            self._store_sample(sample)
            return sample

        except Exception as e:
            self._logger.error(f"Failed to read ADC channel {channel_name}: {e}")
            raise

    async def write_channel(self, channel_name: str, value: Union[float, bool]) -> bool:
        """Write value to ADC channel (not applicable)."""
        self._logger.warning("ADC channels are read-only")
        return False

    async def start_acquisition(self, mode: DAQMode = DAQMode.CONTINUOUS) -> bool:
        """Start ADC continuous acquisition."""
        try:
            if self._is_acquiring:
                return False

            self._acquisition_mode = mode
            self._is_acquiring = True

            # Start acquisition task
            self._acquisition_task = asyncio.create_task(self._adc_acquisition_loop())

            self._logger.info("Started ADC acquisition")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start ADC acquisition: {e}")
            return False

    async def stop_acquisition(self) -> bool:
        """Stop ADC acquisition."""
        try:
            self._is_acquiring = False

            if self._acquisition_task:
                self._acquisition_task.cancel()
                try:
                    await self._acquisition_task
                except asyncio.CancelledError:
                    pass

            self._logger.info("Stopped ADC acquisition")
            return True

        except Exception as e:
            self._logger.error(f"Failed to stop ADC acquisition: {e}")
            return False

    async def _read_adc_raw(self, channel_name: str) -> int:
        """Read raw ADC value."""
        # Simulate ADC reading with some noise
        channel_index = int(channel_name.split('_')[-1]) if '_' in channel_name else 0
        base_value = (hash(f"{channel_name}_{time.time()}") % (2**self._resolution))
        noise = np.random.randint(-10, 11)
        return max(0, min(2**self._resolution - 1, base_value + noise))

    async def _adc_acquisition_loop(self) -> None:
        """ADC acquisition loop."""
        try:
            while self._is_acquiring:
                # Read from all channels
                for channel_name in self._channels:
                    try:
                        await self.read_channel(channel_name)
                    except Exception as e:
                        self._logger.warning(f"Error reading ADC channel {channel_name}: {e}")

                # Wait for next sample
                await asyncio.sleep(1.0 / self._sample_rate)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"ADC acquisition loop error: {e}")
            self._is_acquiring = False

    def _init_adc_channels(self) -> None:
        """Initialize default ADC channels."""
        for i in range(self._channel_count):
            channel_config = ChannelConfig(
                name=f"adc_{i}",
                channel_type=ChannelType.ANALOG_INPUT,
                physical_channel=f"ai{i}",
                min_val=0.0,
                max_val=self._reference_voltage,
                units="V"
            )
            # Add to channels without going through configure_channel
            # to avoid the async requirement during init
            self._channels[channel_config.name] = channel_config
            self._buffers[channel_config.name] = DAQBuffer(
                channel_name=channel_config.name,
                max_size=self._buffer_size
            )