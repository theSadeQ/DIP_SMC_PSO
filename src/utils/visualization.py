"""
Utility for visualising a double–inverted-pendulum simulation.

The `Visualizer` animates cart-pole motion and **returns** the
`matplotlib.animation.FuncAnimation` object so callers (e.g. Streamlit
or a Jupyter notebook) can decide how to display or save it.
"""

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from typing import Tuple


class Visualizer:
    """Animate a controlled double–inverted pendulum."""

    def __init__(self, pendulum_model):
        self.pendulum = pendulum_model
        self.fig, self.ax = plt.subplots(figsize=(12, 7))

        # Live text read-outs
        self.time_text = self.ax.text(
            0.05, 0.95, "", transform=self.ax.transAxes, va="top", fontsize=12
        )
        self.angle_text = self.ax.text(
            0.05, 0.90, "", transform=self.ax.transAxes, va="top", fontsize=12
        )

        # Pre-create a single FancyArrowPatch for reuse (so set_positions works)
        from matplotlib.patches import FancyArrowPatch

        self.force_arrow = FancyArrowPatch(
            (0, 0), (0, 0), arrowstyle="->", mutation_scale=10
        )
        self.ax.add_patch(self.force_arrow)
        self.force_arrow.set_visible(False)

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _calculate_positions(self, state: np.ndarray) -> Tuple[float, ...]:
        x, th1, th2 = state[0], state[1], state[2]
        l1, l2 = self.pendulum.l1, self.pendulum.l2

        cart_x, cart_y = x, 0.0
        p1_x = cart_x + (2 * l1) * np.sin(th1)
        p1_y = cart_y + (2 * l1) * np.cos(th1)
        p2_x = p1_x + (2 * l2) * np.sin(th2)
        p2_y = p1_y + (2 * l2) * np.cos(th2)

        return cart_x, cart_y, p1_x, p1_y, p2_x, p2_y

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def animate(
        self,
        time_history: np.ndarray,
        state_history: np.ndarray,
        control_history: np.ndarray,
        dt: float = 0.02,
    ):
        """
        Creates **and returns** the animation object.

        Parameters
        ----------
        time_history : np.ndarray
            Simulation time stamps.
        state_history : np.ndarray
            2-D array of state vectors over time.
        control_history : np.ndarray
            Control input (cart force) at each time step.
        dt : float, optional
            Time step in seconds (default = 0.02).

        Returns
        -------
        matplotlib.animation.FuncAnimation
        """
        # -- Pre-compute link/cart endpoints for speed ------------------
        frames = [self._calculate_positions(s) for s in state_history]
        all_x = [f[0] for f in frames]

        x_pad = 1.0
        y_max = self.pendulum.L1 + 2 * self.pendulum.l2
        self.ax.set_xlim(min(all_x) - x_pad, max(all_x) + x_pad)
        self.ax.set_ylim(-1.5, y_max + x_pad)
        self.ax.set_aspect("equal")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title("Double-Inverted Pendulum Simulation")

        # -- Static ground line ----------------------------------------
        cart_w, cart_h = 0.4, 0.2
        ground_y = -cart_h / 2
        self.ax.plot(self.ax.get_xlim(), [ground_y, ground_y], "k-", lw=2)

        # -- Patches & line artists (no explicit colours) --------------
        cart = self.ax.add_patch(plt.Rectangle((0, 0), cart_w, cart_h))
        (link1,) = self.ax.plot([], [], "o-", lw=3, markersize=8)
        (link2,) = self.ax.plot([], [], "o-", lw=3, markersize=8)

        # -- Frame update ----------------------------------------------
        def _update(i: int):
            cart_x, _, p1_x, p1_y, p2_x, p2_y = frames[i]

            # Cart
            cart.set_xy((cart_x - cart_w / 2, ground_y))

            # Links
            link1.set_data([cart_x, p1_x], [0, p1_y])
            link2.set_data([p1_x, p2_x], [p1_y, p2_y])

            # Text
            self.time_text.set_text(f"t = {time_history[i]:.2f} s")
            th1_deg = np.rad2deg(state_history[i, 1])
            th2_deg = np.rad2deg(state_history[i, 2])
            self.angle_text.set_text(f"θ₁ = {th1_deg:.1f}°\nθ₂ = {th2_deg:.1f}°")

            # Force arrow (reuse the same artist to avoid leaks)
            force = float(control_history[i]) if i < len(control_history) else 0.0
            if abs(force) > 0.1:
                a_start = cart_x - np.sign(force) * (cart_w / 2 + 0.05)
                a_len = np.sign(force) * (0.3 * np.log1p(abs(force)))
                # Update arrow endpoints
                self.force_arrow.set_positions((a_start, 0), (a_start + a_len, 0))
                self.force_arrow.set_visible(True)
            else:
                # Hide the arrow when force is negligible
                self.force_arrow.set_visible(False)

            return cart, link1, link2, self.time_text, self.angle_text

        # -- Build animation -------------------------------------------
        self.ani = animation.FuncAnimation(
            self.fig,
            _update,
            frames=len(state_history),
            interval=dt * 1000,
            blit=False,
            repeat=False,
        )
        # Close the figure to prevent buildup of open figures in scripts or CI
        plt.close(self.fig)
        return self.ani
