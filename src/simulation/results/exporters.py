#==========================================================================================\\\
#======================= src/simulation/results/exporters.py =======================\\\
#==========================================================================================\\\

"""Export simulation results to various formats."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
import numpy as np


class CSVExporter:
    """Export simulation results to CSV format."""

    def export(self, result_container: Any, filepath: str) -> None:
        """Export single simulation results to CSV."""
        states = result_container.get_states()
        times = result_container.get_times()

        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            state_cols = [f'state_{i}' for i in range(states.shape[1])]
            header = ['time'] + state_cols
            if hasattr(result_container, 'controls') and result_container.controls is not None:
                header.append('control')
            writer.writerow(header)

            # Write data
            for i, (t, state) in enumerate(zip(times, states)):
                row = [t] + state.tolist()
                if hasattr(result_container, 'controls') and result_container.controls is not None:
                    if i < len(result_container.controls):
                        row.append(result_container.controls[i])
                writer.writerow(row)

    def export_batch(self, batch_container: Any, filepath: str) -> None:
        """Export batch simulation results to CSV."""
        base_path = Path(filepath)

        for batch_idx in range(batch_container.get_batch_count()):
            batch_filepath = base_path.parent / f"{base_path.stem}_batch_{batch_idx}{base_path.suffix}"

            # Create a temporary container for this batch
            temp_container = type('TempContainer', (), {})()
            temp_container.get_states = lambda: batch_container.get_states(batch_idx)
            temp_container.get_times = lambda: batch_container.get_times(batch_idx)
            temp_container.controls = batch_container.batch_data.get(batch_idx, {}).get('controls')

            self.export(temp_container, str(batch_filepath))


class HDF5Exporter:
    """Export simulation results to HDF5 format."""

    def export(self, result_container: Any, filepath: str) -> None:
        """Export single simulation results to HDF5."""
        try:
            import h5py
        except ImportError:
            raise ImportError("h5py required for HDF5 export")

        with h5py.File(filepath, 'w') as f:
            f.create_dataset('times', data=result_container.get_times())
            f.create_dataset('states', data=result_container.get_states())

            if hasattr(result_container, 'controls') and result_container.controls is not None:
                f.create_dataset('controls', data=result_container.controls)

            # Store metadata
            if hasattr(result_container, 'metadata'):
                metadata_group = f.create_group('metadata')
                for key, value in result_container.metadata.items():
                    if isinstance(value, (int, float, str)):
                        metadata_group.attrs[key] = value

    def export_batch(self, batch_container: Any, filepath: str) -> None:
        """Export batch simulation results to HDF5."""
        try:
            import h5py
        except ImportError:
            raise ImportError("h5py required for HDF5 export")

        with h5py.File(filepath, 'w') as f:
            for batch_idx in range(batch_container.get_batch_count()):
                batch_group = f.create_group(f'batch_{batch_idx}')
                batch_group.create_dataset('times', data=batch_container.get_times(batch_idx))
                batch_group.create_dataset('states', data=batch_container.get_states(batch_idx))

                batch_data = batch_container.batch_data.get(batch_idx, {})
                if batch_data.get('controls') is not None:
                    batch_group.create_dataset('controls', data=batch_data['controls'])