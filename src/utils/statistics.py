"""
Statistical utilities for performance analysis.

This module introduces functions for computing confidence intervals and
summarising simulation results.  When comparing controllers or tuning
parameters it is essential to run multiple trials and report confidence
intervals on performance metrics.  The central limit theorem states that
the distribution of sample means approaches a normal distribution as the
number of trials increases; conventionally 30 or more samples are
considered sufficient for the approximation to hold【539941773593996†L291-L352】.

Functions
---------

confidence_interval
    Compute the mean and half‑width of a confidence interval using the
    Student’s t‑distribution.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import t
from typing import Tuple

def confidence_interval(data: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
    """Return the mean and half‑width of a Student‑t confidence interval.

    Given an array of samples, compute the sample mean and the half‑width
    of the two‑sided confidence interval at the specified confidence
    level.  The half‑width is ``tcrit * s / sqrt(n)``, where ``tcrit`` is
    the t‑distribution critical value, ``s`` is the sample standard
    deviation (ddof=1) and ``n`` is the number of samples.  When fewer
    than two samples are provided the half‑width is returned as NaN.

    Parameters
    ----------
    data : np.ndarray
        One‑dimensional array of observations.
    confidence : float, optional
        Desired confidence level in (0,1).  Defaults to 0.95.

    Returns
    -------
    mean : float
        Sample mean.
    half_width : float
        Half‑width of the confidence interval.  ``NaN`` when ``n < 2``.
    """
    data = np.asarray(data, dtype=float).ravel()
    n = data.size
    mean = float(np.mean(data)) if n > 0 else np.nan
    if n < 2:
        return mean, float('nan')
    s = float(np.std(data, ddof=1))
    # Two‑sided t‑critical value
    alpha = 1.0 - confidence
    tcrit = float(t.ppf(1.0 - alpha / 2.0, df=n - 1))
    half_width = tcrit * s / np.sqrt(n)
    return mean, half_width

__all__ = ["confidence_interval"]