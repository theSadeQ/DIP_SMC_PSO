#==========================================================================================\\\
#======================= src/simulation/results/containers.py =======================\\\
#==========================================================================================\\\

"""Result container implementations for simulation data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from ..core.interfaces import ResultContainer


class StandardResultContainer(ResultContainer):
    """Standard result container for single simulations."""

    def __init__(self):
        """Initialize standard result container."""
        self.states = None
        self.times = None
        self.controls = None
        self.metadata = {}

    def add_trajectory(self, states: np.ndarray, times: np.ndarray, **metadata) -> None:
        """Add trajectory data to container."""
        self.states = states.copy()
        self.times = times.copy()

        # Store additional data in metadata
        for key, value in metadata.items():
            if key == 'controls':
                self.controls = np.array(value) if value is not None else None
            else:
                self.metadata[key] = value

    def get_states(self) -> np.ndarray:
        """Get state trajectories."""
        return self.states if self.states is not None else np.array([])

    def get_times(self) -> np.ndarray:
        """Get time vectors."""
        return self.times if self.times is not None else np.array([])

    def export(self, format_type: str, filepath: str) -> None:
        """Export results to specified format."""
        if format_type.lower() == 'csv':
            from .exporters import CSVExporter
            exporter = CSVExporter()
            exporter.export(self, filepath)
        elif format_type.lower() == 'hdf5':
            from .exporters import HDF5Exporter
            exporter = HDF5Exporter()
            exporter.export(self, filepath)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


class BatchResultContainer(ResultContainer):
    """Batch result container for multiple simulations."""

    def __init__(self):
        """Initialize batch result container."""
        self.batch_data = {}
        self.metadata = {}

    def add_trajectory(self, states: np.ndarray, times: np.ndarray, **metadata) -> None:
        """Add trajectory data to batch container."""
        batch_index = metadata.get('batch_index', len(self.batch_data))

        self.batch_data[batch_index] = {
            'states': states.copy(),
            'times': times.copy(),
            'controls': metadata.get('controls', None),
            'metadata': {k: v for k, v in metadata.items() if k not in ['batch_index', 'controls']}
        }

    def get_states(self, batch_index: Optional[int] = None) -> np.ndarray:
        """Get state trajectories for specific batch or all batches."""
        if batch_index is not None:
            data = self.batch_data.get(batch_index, {})
            return data.get('states', np.array([]))
        else:
            # Return all states as 3D array
            all_states = []
            for i in sorted(self.batch_data.keys()):
                all_states.append(self.batch_data[i]['states'])
            return np.array(all_states) if all_states else np.array([])

    def get_times(self, batch_index: Optional[int] = None) -> np.ndarray:
        """Get time vectors for specific batch or all batches."""
        if batch_index is not None:
            data = self.batch_data.get(batch_index, {})
            return data.get('times', np.array([]))
        else:
            # Return time vector (assuming all batches have same times)
            if self.batch_data:
                first_batch = next(iter(self.batch_data.values()))
                return first_batch.get('times', np.array([]))
            return np.array([])

    def export(self, format_type: str, filepath: str) -> None:
        """Export batch results to specified format."""
        if format_type.lower() == 'csv':
            from .exporters import CSVExporter
            exporter = CSVExporter()
            exporter.export_batch(self, filepath)
        elif format_type.lower() == 'hdf5':
            from .exporters import HDF5Exporter
            exporter = HDF5Exporter()
            exporter.export_batch(self, filepath)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def get_batch_count(self) -> int:
        """Get number of batches."""
        return len(self.batch_data)