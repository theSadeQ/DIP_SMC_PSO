#==========================================================================================\\\
#======================== src/utils/monitoring/latency.py ==============================\\\
#==========================================================================================\\\

"""
Real-time latency monitoring for control loops.

Provides tools for monitoring control loop execution times and detecting
deadline violations in real-time systems.
"""

from __future__ import annotations
import time
from typing import List, Tuple
import numpy as np

class LatencyMonitor:
    """Measure and analyse loop latency.

    Parameters
    ----------
    dt : float
        Nominal control period (seconds).
    margin : float, optional
        Fraction of ``dt`` regarded as acceptable margin before
        flagging an overrun. Defaults to 0.9; a latency exceeding
        ``dt`` will always be counted as a missed deadline.
    """

    def __init__(self, dt: float, margin: float = 0.9) -> None:
        self.dt = float(dt)
        self.margin = float(margin)
        self.samples: List[float] = []

    def start(self) -> float:
        """Record the start time and return it."""
        return time.perf_counter()

    def end(self, start_time: float) -> bool:
        """Record the end time and determine if a deadline was missed.

        A miss occurs when the elapsed time exceeds ``dt`` multiplied by
        the margin. This slack margin allows the control loop to finish
        slightly before the nominal deadline and flags only significant
        overruns.

        Returns
        -------
        bool
            True if the elapsed time exceeds ``dt`` × ``margin``; False otherwise.
        """
        latency = time.perf_counter() - start_time
        self.samples.append(latency)
        # Compare against dt scaled by margin
        return latency > (self.dt * self.margin)

    def stats(self) -> Tuple[float, float]:
        """Return median and 95th percentile of recorded latencies."""
        if not self.samples:
            return 0.0, 0.0
        arr = np.array(self.samples)
        median = float(np.median(arr))
        p95 = float(np.quantile(arr, 0.95))
        return median, p95

    def missed_rate(self) -> float:
        """Return the fraction of samples that missed the deadline."""
        if not self.samples:
            return 0.0
        count = sum(1 for s in self.samples if s > self.dt)
        return count / len(self.samples)

    def enforce(self, m: int, k: int) -> bool:
        """Check a weakly‑hard (m,k) deadline miss constraint.

        In weakly‑hard real‑time models it is acceptable to miss up to
        ``m`` deadlines in any window of ``k`` consecutive samples.

        Parameters
        ----------
        m : int
            Maximum allowed number of misses in each window of ``k`` samples.
        k : int
            Window size for counting deadline misses.

        Returns
        -------
        bool
            ``True`` if no more than ``m`` misses occurred in the last
            ``k`` samples, else ``False``.
        """
        if k <= 0:
            return True
        n = len(self.samples)
        if n < k:
            # Not enough samples yet; assume constraint satisfied
            return True
        window = self.samples[-k:]
        miss_count = sum(1 for s in window if s > self.dt)
        return miss_count <= m

    def reset(self) -> None:
        """Clear all recorded samples."""
        self.samples.clear()

    def get_recent_stats(self, n: int = 100) -> Tuple[float, float]:
        """Get statistics for the most recent n samples."""
        if not self.samples:
            return 0.0, 0.0

        recent = self.samples[-n:] if len(self.samples) >= n else self.samples
        if not recent:
            return 0.0, 0.0

        arr = np.array(recent)
        median = float(np.median(arr))
        p95 = float(np.quantile(arr, 0.95))
        return median, p95