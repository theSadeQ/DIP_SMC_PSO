========================
Latency Monitor
========================
.. currentmodule:: src.utils.latency_monitor

Overview
--------
Latency monitoring utilities.

Examples
--------
.. doctest::

   >>> from src.utils.latency_monitor import LatencyMonitor
   >>> # 50 Hz control loop (dt=0.02 s); immediate end => no miss
   >>> lm = LatencyMonitor(dt=0.02, margin=0.9)
   >>> st = lm.start()
   >>> missed_now = lm.end(st)
   >>> missed_now
   False

   >>> # Add a few recorded latencies (seconds) for analysis
   >>> lm.samples.extend([0.018, 0.019, 0.022, 0.017, 0.019])  # one miss (> dt)
   >>> round(lm.missed_rate(), 2)
   0.2
   >>> med, p95 = lm.stats()
   >>> (0.017 <= med <= 0.022) and (p95 >= med)
   True
   >>> # Weakly-hard constraint: at most 1 miss in the last 3 samples
   >>> lm.enforce(m=1, k=3)
   True

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.latency_monitor

Detailed API
------------
.. automodule:: src.utils.latency_monitor
   :members:
   :undoc-members:
   :show-inheritance:
