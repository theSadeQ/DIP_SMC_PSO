#==========================================================================================\\
#======================= tests/test_app/test_streamlit_metrics.py =======================\\
#==========================================================================================\\
"""
Streamlit app — metrics edge cases for _compute_metrics.
"""

from __future__ import annotations

import numpy as np

from streamlit_app import _compute_metrics


def test_metrics_with_minimal_traces():
    # Length-1 trace, missing control input -> u size 0
    t = np.array([0.0])
    x1 = np.array([[0.0]])  # only x column present
    u = np.array([])
    m = _compute_metrics(t, x1, u)
    assert m["settling_time_s"] == 0.0
    assert m["rms_control_N"] == 0.0
    assert m["peak_abs_th1_deg"] == 0.0
    assert m["peak_abs_th2_deg"] == 0.0


def test_metrics_tolerances_affect_settling_time():
    # Two-step trace where angles settle only with relaxed tolerance
    t = np.array([0.0, 1.0, 2.0])
    # x, theta1, theta2
    x = np.array([
        [0.1, 0.06, 0.06],  # outside default tol_th=0.05
        [0.01, 0.04, 0.04],  # within relaxed tol
        [0.01, 0.04, 0.04],
    ])
    u = np.array([0.0, 0.0])

    # Default tolerances -> first all-within at i=1 (t=1.0)
    m1 = _compute_metrics(t, x, u)
    assert m1["settling_time_s"] == 1.0

    # Tighten tolerances -> settle later (at t=2.0)
    m2 = _compute_metrics(t, x, u, tol_x=0.005, tol_th=0.03)
    assert m2["settling_time_s"] == 2.0

