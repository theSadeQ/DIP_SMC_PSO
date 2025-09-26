"""
Fast SMC Demo
=================

This quick example simulates a simple first-order system with a sliding
mode-like control action to illustrate the characteristic reaching and
sliding behavior. It generates a single figure.

Notes
-----
- In CI fast mode (DOCS_FAST=1) the simulation runs fewer steps.
"""

import os
import numpy as np
import matplotlib.pyplot as plt


def sat(x, eps=0.05):
    # Smooth sign (saturation) to reduce chattering
    return np.clip(x / max(eps, 1e-6), -1.0, 1.0)


def simulate(T=2.0, dt=1e-3, k=2.5):
    n = int(T / dt)
    x = 1.0  # initial error
    xs = np.empty(n)
    t = np.arange(n) * dt
    for i in range(n):
        u = -k * sat(x)
        # Simple first-order plant: x_dot = -x + u
        x = x + dt * (-x + u)
        xs[i] = x
    return t, xs


def main():
    fast = os.environ.get("DOCS_FAST")
    T = 1.0 if fast else 3.0
    dt = 2e-3 if fast else 1e-3
    t, xs = simulate(T=T, dt=dt)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(t, xs, label="error x(t)")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("error")
    ax.set_title("Sliding-like control drives error to 0")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()


if __name__ == "__main__":
    main()

