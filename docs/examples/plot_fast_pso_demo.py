"""
Fast PSO Convergence Demo
=========================

This example shows a tiny Particle Swarm on a simple quadratic objective to
illustrate convergence. It generates a single convergence plot.

Notes
-----
- In CI fast mode (DOCS_FAST=1) the number of iterations is reduced.
"""

import os
import numpy as np
import matplotlib.pyplot as plt


def sphere(x):
    return np.sum(x * x)


def tiny_pso(dim=2, n_particles=10, iters=50, w=0.6, c1=1.2, c2=1.2):
    rng = np.random.default_rng(0)
    x = rng.uniform(-2, 2, size=(n_particles, dim))
    v = rng.normal(0, 0.2, size=(n_particles, dim))
    pbest = x.copy()
    pbest_cost = np.apply_along_axis(sphere, 1, pbest)
    gbest_idx = np.argmin(pbest_cost)
    gbest = pbest[gbest_idx].copy()
    gbest_cost = [pbest_cost[gbest_idx]]

    for _ in range(iters):
        r1 = rng.random((n_particles, dim))
        r2 = rng.random((n_particles, dim))
        v = w * v + c1 * r1 * (pbest - x) + c2 * r2 * (gbest - x)
        x = x + v
        cost = np.apply_along_axis(sphere, 1, x)
        improved = cost < pbest_cost
        pbest[improved] = x[improved]
        pbest_cost[improved] = cost[improved]
        gbest_idx = np.argmin(pbest_cost)
        gbest = pbest[gbest_idx]
        gbest_cost.append(pbest_cost[gbest_idx])
    return np.array(gbest_cost)


def main():
    fast = os.environ.get("DOCS_FAST")
    iters = 20 if fast else 80
    curve = tiny_pso(iters=iters)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(curve, lw=2)
    ax.set_xlabel("iteration")
    ax.set_ylabel("best cost")
    ax.set_title("Tiny PSO converges on sphere function")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()


if __name__ == "__main__":
    main()

