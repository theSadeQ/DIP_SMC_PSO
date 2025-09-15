#==========================================================================================\\
#============================ src/utils/latency_monitor.py ============================\\
#==========================================================================================\\
"""
Latency monitoring utilities.

Real‑time control systems must ensure that their control loop executes
within a fixed period.  If computations overrun the sample period the
actuator command may be delayed, potentially destabilising the system.
This module provides a simple latency monitor to record the execution
time of each iteration and detect missed deadlines.  Statistics such as
median and 95th percentile latency can be logged at the end of a run.

No citations are required for this utility because it contains no
algorithmic control logic.
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
        flagging an overrun.  Defaults to 0.9; a latency exceeding
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
        the margin.  This slack margin allows the control loop to finish
        slightly before the nominal deadline and flags only significant
        overruns.  Returning True signals that the deadline was
        exceeded【601274779172455†L860-L869】.

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
        ``m`` deadlines in any window of ``k`` consecutive samples【175885990258773†L54-L67】.  This
        method returns ``True`` if the constraint is satisfied and ``False``
        otherwise.  When the constraint is violated callers may apply
        fallback control logic (e.g., reuse the previous control or switch
        to a simpler controller).

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

__all__ = ["LatencyMonitor"]