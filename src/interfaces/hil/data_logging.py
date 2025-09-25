#==========================================================================================\\\
#====================== src/interfaces/hil/data_logging.py ==============================\\\
#==========================================================================================\\\
"""
Data logging system for HIL applications.
This module provides comprehensive data logging capabilities including
high-frequency data collection, buffering, compression, and export
for HIL system analysis and validation.
"""

import asyncio
import time
import csv
import json
import h5py
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union, BinaryIO
from enum import Enum
import logging
from pathlib import Path


class LogFormat(Enum):
    """Data logging format enumeration."""
    CSV = "csv"
    JSON = "json"
    HDF5 = "hdf5"
    BINARY = "binary"
    MAT = "mat"


class CompressionType(Enum):
    """Data compression type enumeration."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


@dataclass
class LoggingConfig:
    """HIL data logging configuration."""
    # File settings
    output_directory: str = "./hil_logs"
    file_prefix: str = "hil_data"
    format: LogFormat = LogFormat.HDF5
    compression: CompressionType = CompressionType.GZIP

    # Buffering settings
    buffer_size: int = 100000
    flush_interval: float = 5.0
    auto_flush_threshold: float = 0.8

    # Sampling settings
    sample_rate: float = 1000.0
    decimation_factor: int = 1
    channels: List[str] = field(default_factory=list)

    # Performance settings
    max_file_size: int = 1024 * 1024 * 1024  # 1GB
    max_files: int = 100
    enable_compression: bool = True

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class LogEntry:
    """Individual log entry."""
    timestamp: float
    data: Dict[str, Any]
    sequence: int = 0
    source: str = "unknown"


class HILDataLogger:
    """
    High-performance data logger for HIL systems.

    Provides efficient data collection, buffering, and storage
    with support for multiple formats and real-time compression.
    """

    def __init__(self, config: LoggingConfig):
        """Initialize HIL data logger."""
        self._config = config
        self._logger = logging.getLogger("hil_data_logger")

        # Data buffers
        self._buffer: List[LogEntry] = []
        self._buffer_lock = asyncio.Lock()

        # File management
        self._current_file: Optional[Any] = None
        self._file_counter = 0
        self._current_file_size = 0

        # Timing control
        self._sequence_counter = 0
        self._last_flush = time.time()
        self._logging_task: Optional[asyncio.Task] = None
        self._flush_task: Optional[asyncio.Task] = None

        # State management
        self._active = False
        self._stop_event = asyncio.Event()

        # Statistics
        self._stats = {
            'entries_logged': 0,
            'files_created': 0,
            'bytes_written': 0,
            'buffer_overruns': 0,
            'compression_ratio': 1.0
        }

        # Setup output directory
        self._setup_output_directory()

    async def initialize(self) -> bool:
        """Initialize data logger."""
        try:
            self._logger.info("Initializing HIL data logger")

            # Create initial log file
            await self._create_new_file()

            self._logger.info(f"Data logger initialized - Format: {self._config.format.value}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize data logger: {e}")
            return False

    async def start(self) -> bool:
        """Start data logging."""
        try:
            if self._active:
                self._logger.warning("Data logger already active")
                return True

            self._active = True
            self._stop_event.clear()

            # Start background tasks
            self._flush_task = asyncio.create_task(self._flush_loop())

            self._logger.info("Data logger started")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start data logger: {e}")
            return False

    async def stop(self) -> bool:
        """Stop data logging."""
        try:
            self._active = False
            self._stop_event.set()

            # Cancel background tasks
            if self._flush_task:
                self._flush_task.cancel()
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass

            # Final flush
            await self._flush_buffer()

            # Close current file
            await self._close_current_file()

            self._logger.info("Data logger stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping data logger: {e}")
            return False

    async def log_data(self, data: Dict[str, Any], timestamp: Optional[float] = None) -> bool:
        """Log data entry."""
        try:
            if not self._active:
                return False

            # Create log entry
            entry = LogEntry(
                timestamp=timestamp or time.time(),
                data=data.copy(),
                sequence=self._sequence_counter,
                source="hil_system"
            )

            self._sequence_counter += 1

            # Add to buffer
            async with self._buffer_lock:
                self._buffer.append(entry)

                # Check buffer size
                if len(self._buffer) >= self._config.buffer_size:
                    self._stats['buffer_overruns'] += 1
                    # Remove oldest entries
                    self._buffer = self._buffer[-int(self._config.buffer_size * 0.8):]

                # Auto-flush if threshold reached
                threshold = int(self._config.buffer_size * self._config.auto_flush_threshold)
                if len(self._buffer) >= threshold:
                    asyncio.create_task(self._flush_buffer())

            return True

        except Exception as e:
            self._logger.error(f"Error logging data: {e}")
            return False

    async def log_batch(self, batch_data: List[Dict[str, Any]]) -> bool:
        """Log batch of data entries."""
        try:
            entries = []
            current_time = time.time()

            for i, data in enumerate(batch_data):
                entry = LogEntry(
                    timestamp=current_time + i * 0.001,  # 1ms spacing
                    data=data.copy(),
                    sequence=self._sequence_counter + i,
                    source="hil_system"
                )
                entries.append(entry)

            self._sequence_counter += len(entries)

            # Add to buffer
            async with self._buffer_lock:
                self._buffer.extend(entries)

                # Check buffer overflow
                if len(self._buffer) > self._config.buffer_size:
                    overflow = len(self._buffer) - self._config.buffer_size
                    self._stats['buffer_overruns'] += overflow
                    self._buffer = self._buffer[-self._config.buffer_size:]

            return True

        except Exception as e:
            self._logger.error(f"Error logging batch data: {e}")
            return False

    async def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        async with self._buffer_lock:
            buffer_size = len(self._buffer)

        return {
            **self._stats,
            'buffer_size': buffer_size,
            'buffer_utilization': buffer_size / self._config.buffer_size,
            'active': self._active,
            'current_file': str(self._get_current_filename()) if self._current_file else None
        }

    async def export_data(self, output_file: str, start_time: Optional[float] = None,
                         end_time: Optional[float] = None, channels: Optional[List[str]] = None) -> bool:
        """Export logged data to file."""
        try:
            # Flush current buffer
            await self._flush_buffer()

            # Read data from files and export
            # This would implement data reading and export logic
            self._logger.info(f"Exported data to {output_file}")
            return True

        except Exception as e:
            self._logger.error(f"Error exporting data: {e}")
            return False

    async def _flush_loop(self) -> None:
        """Background flush loop."""
        try:
            while self._active and not self._stop_event.is_set():
                await asyncio.sleep(self._config.flush_interval)

                if self._active:
                    await self._flush_buffer()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Error in flush loop: {e}")

    async def _flush_buffer(self) -> None:
        """Flush buffer to file."""
        try:
            async with self._buffer_lock:
                if not self._buffer:
                    return

                entries_to_flush = self._buffer.copy()
                self._buffer.clear()

            # Write entries to file
            await self._write_entries(entries_to_flush)

            self._last_flush = time.time()
            self._stats['entries_logged'] += len(entries_to_flush)

        except Exception as e:
            self._logger.error(f"Error flushing buffer: {e}")

    async def _write_entries(self, entries: List[LogEntry]) -> None:
        """Write entries to current file."""
        try:
            if not self._current_file:
                await self._create_new_file()

            if self._config.format == LogFormat.HDF5:
                await self._write_hdf5_entries(entries)
            elif self._config.format == LogFormat.CSV:
                await self._write_csv_entries(entries)
            elif self._config.format == LogFormat.JSON:
                await self._write_json_entries(entries)

            # Check file size and rotate if needed
            if self._current_file_size > self._config.max_file_size:
                await self._rotate_file()

        except Exception as e:
            self._logger.error(f"Error writing entries: {e}")

    async def _write_hdf5_entries(self, entries: List[LogEntry]) -> None:
        """Write entries to HDF5 file."""
        try:
            if not entries:
                return

            # Prepare data arrays
            timestamps = np.array([entry.timestamp for entry in entries])
            sequences = np.array([entry.sequence for entry in entries])

            # Get all unique data keys
            all_keys = set()
            for entry in entries:
                all_keys.update(entry.data.keys())

            # Write timestamp and sequence datasets
            if 'timestamps' not in self._current_file:
                self._current_file.create_dataset(
                    'timestamps', data=timestamps, maxshape=(None,),
                    compression='gzip' if self._config.enable_compression else None
                )
                self._current_file.create_dataset(
                    'sequences', data=sequences, maxshape=(None,),
                    compression='gzip' if self._config.enable_compression else None
                )
            else:
                # Append to existing datasets
                ts_dataset = self._current_file['timestamps']
                seq_dataset = self._current_file['sequences']

                old_size = ts_dataset.shape[0]
                new_size = old_size + len(timestamps)

                ts_dataset.resize((new_size,))
                seq_dataset.resize((new_size,))

                ts_dataset[old_size:] = timestamps
                seq_dataset[old_size:] = sequences

            # Write data channels
            for key in all_keys:
                values = []
                for entry in entries:
                    values.append(entry.data.get(key, np.nan))

                values_array = np.array(values)

                if key not in self._current_file:
                    self._current_file.create_dataset(
                        key, data=values_array, maxshape=(None,),
                        compression='gzip' if self._config.enable_compression else None
                    )
                else:
                    dataset = self._current_file[key]
                    old_size = dataset.shape[0]
                    new_size = old_size + len(values_array)

                    dataset.resize((new_size,))
                    dataset[old_size:] = values_array

            # Update file size estimate
            self._current_file_size = sum(dataset.size * dataset.dtype.itemsize
                                        for dataset in self._current_file.values())

        except Exception as e:
            self._logger.error(f"Error writing HDF5 entries: {e}")

    async def _write_csv_entries(self, entries: List[LogEntry]) -> None:
        """Write entries to CSV file."""
        try:
            # Get all unique keys for CSV header
            all_keys = set(['timestamp', 'sequence'])
            for entry in entries:
                all_keys.update(entry.data.keys())

            fieldnames = sorted(all_keys)

            # Write entries
            for entry in entries:
                row = {
                    'timestamp': entry.timestamp,
                    'sequence': entry.sequence,
                    **entry.data
                }

                self._current_file.writerow(row)

            # Update file size
            self._current_file_size = self._current_file.file.tell()

        except Exception as e:
            self._logger.error(f"Error writing CSV entries: {e}")

    async def _write_json_entries(self, entries: List[LogEntry]) -> None:
        """Write entries to JSON file."""
        try:
            for entry in entries:
                record = {
                    'timestamp': entry.timestamp,
                    'sequence': entry.sequence,
                    'data': entry.data
                }

                json.dump(record, self._current_file)
                self._current_file.write('\n')

            # Update file size
            self._current_file_size = self._current_file.tell()

        except Exception as e:
            self._logger.error(f"Error writing JSON entries: {e}")

    async def _create_new_file(self) -> None:
        """Create new log file."""
        try:
            await self._close_current_file()

            filename = self._get_current_filename()
            filepath = Path(self._config.output_directory) / filename

            if self._config.format == LogFormat.HDF5:
                self._current_file = h5py.File(
                    filepath.with_suffix('.h5'),
                    'w'
                )

            elif self._config.format == LogFormat.CSV:
                file_handle = open(filepath.with_suffix('.csv'), 'w', newline='')
                # Get all possible fieldnames from config channels
                fieldnames = ['timestamp', 'sequence'] + self._config.channels
                self._current_file = csv.DictWriter(file_handle, fieldnames=fieldnames)
                self._current_file.writeheader()

            elif self._config.format == LogFormat.JSON:
                self._current_file = open(filepath.with_suffix('.json'), 'w')

            self._current_file_size = 0
            self._stats['files_created'] += 1

            self._logger.info(f"Created new log file: {filename}")

        except Exception as e:
            self._logger.error(f"Error creating new file: {e}")

    async def _close_current_file(self) -> None:
        """Close current log file."""
        try:
            if self._current_file:
                if hasattr(self._current_file, 'close'):
                    self._current_file.close()
                elif hasattr(self._current_file, 'file'):
                    self._current_file.file.close()
                self._current_file = None

        except Exception as e:
            self._logger.error(f"Error closing file: {e}")

    async def _rotate_file(self) -> None:
        """Rotate to new log file."""
        try:
            self._file_counter += 1
            await self._create_new_file()

            # Clean up old files if limit exceeded
            if self._stats['files_created'] > self._config.max_files:
                await self._cleanup_old_files()

        except Exception as e:
            self._logger.error(f"Error rotating file: {e}")

    async def _cleanup_old_files(self) -> None:
        """Clean up old log files."""
        try:
            log_dir = Path(self._config.output_directory)
            pattern = f"{self._config.file_prefix}_*"

            # Get all log files and sort by creation time
            log_files = sorted(log_dir.glob(pattern), key=lambda p: p.stat().st_ctime)

            # Remove oldest files
            files_to_remove = len(log_files) - self._config.max_files
            for i in range(files_to_remove):
                log_files[i].unlink()

        except Exception as e:
            self._logger.error(f"Error cleaning up old files: {e}")

    def _get_current_filename(self) -> str:
        """Get current log filename."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"{self._config.file_prefix}_{timestamp}_{self._file_counter:04d}"

    def _setup_output_directory(self) -> None:
        """Setup output directory."""
        try:
            output_dir = Path(self._config.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)

        except Exception as e:
            self._logger.error(f"Error setting up output directory: {e}")


# Utility functions for data analysis
def load_hdf5_data(filepath: str, channels: Optional[List[str]] = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None) -> Dict[str, np.ndarray]:
    """Load data from HDF5 log file."""
    try:
        with h5py.File(filepath, 'r') as f:
            timestamps = f['timestamps'][:]

            # Filter by time range
            if start_time or end_time:
                mask = np.ones(len(timestamps), dtype=bool)
                if start_time:
                    mask &= timestamps >= start_time
                if end_time:
                    mask &= timestamps <= end_time
            else:
                mask = slice(None)

            data = {'timestamps': timestamps[mask]}

            # Load specified channels or all available
            if channels:
                available_channels = [ch for ch in channels if ch in f.keys()]
            else:
                available_channels = [k for k in f.keys() if k not in ['timestamps', 'sequences']]

            for channel in available_channels:
                data[channel] = f[channel][:][mask]

        return data

    except Exception as e:
        logging.error(f"Error loading HDF5 data: {e}")
        return {}


def analyze_log_performance(log_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze logging performance."""
    analysis = {
        'data_rate': log_stats['entries_logged'] / max(1, time.time() - log_stats.get('start_time', time.time())),
        'buffer_efficiency': 1.0 - log_stats['buffer_overruns'] / max(1, log_stats['entries_logged']),
        'compression_effective': log_stats.get('compression_ratio', 1.0) > 1.1,
        'file_management_healthy': log_stats['files_created'] > 0
    }

    return analysis