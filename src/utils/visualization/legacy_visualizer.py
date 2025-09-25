#==========================================================================================\\
#============================ src/utils/visualization.py ============================\\
#==========================================================================================\\
"""
Utility for visualising a double–inverted-pendulum simulation.

The `Visualizer` animates cart-pole motion and **returns** the
`matplotlib.animation.FuncAnimation` object so callers (e.g. Streamlit
or a Jupyter notebook) can decide how to display or save it.
"""

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple


class Visualizer:
    """Animate a controlled double–inverted pendulum."""

    def __init__(self, pendulum_model):
        self.pendulum = pendulum_model
        self.fig, self.ax = plt.subplots(figsize=(12, 7))

        # Live text read-outs
        self.time_text = self.ax.text(
            0.05, 0.95, "", transform=self.ax.transAxes,
            va="top", fontsize=12
        )
        self.angle_text = self.ax.text(
            0.05, 0.90, "", transform=self.ax.transAxes,
            va="top", fontsize=12
        )

        # Pre-create a single FancyArrowPatch for reuse (so set_positions works)
        from matplotlib.patches import FancyArrowPatch
        self.force_arrow = FancyArrowPatch((0, 0), (0, 0),
                                          arrowstyle='->',
                                          mutation_scale=10)
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
        link1, = self.ax.plot([], [], "o-", lw=3, markersize=8)
        link2, = self.ax.plot([], [], "o-", lw=3, markersize=8)

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
                a_len   = np.sign(force) * (0.3 * np.log1p(abs(force)))
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

    def save_animation(self, filename: str, **kwargs):
        """
        Save the animation to file.

        Parameters
        ----------
        filename : str
            Output filename. Extension determines format (.mp4, .gif, .mov, etc.)
        **kwargs
            Additional arguments passed to animation.save()

        Examples
        --------
        >>> vis = Visualizer(pendulum_model)
        >>> ani = vis.animate(t, x, u)
        >>> vis.save_animation("simulation.mp4", fps=30, bitrate=1800)
        >>> vis.save_animation("simulation.gif", fps=10)
        """
        if not hasattr(self, 'ani') or self.ani is None:
            raise ValueError("No animation to save. Call animate() first.")

        # Set default parameters based on file extension
        ext = filename.lower().split('.')[-1]
        default_kwargs = {
            'mp4': {'fps': 30, 'bitrate': 1800},
            'gif': {'fps': 10},
            'mov': {'fps': 30, 'bitrate': 1800}
        }

        if ext in default_kwargs:
            for key, value in default_kwargs[ext].items():
                kwargs.setdefault(key, value)

        self.ani.save(filename, **kwargs)
        print(f"Animation saved to: {filename}")

    def save_static_plot(self, state_history: np.ndarray, filename: str,
                        time_step: int = -1, **kwargs):
        """
        Save a static snapshot of the pendulum at a specific time step.

        Parameters
        ----------
        state_history : np.ndarray
            2-D array of state vectors over time
        filename : str
            Output filename for the static plot
        time_step : int, optional
            Time step to visualize (default: -1 for final state)
        **kwargs
            Additional arguments passed to plt.savefig()

        Examples
        --------
        >>> vis.save_static_plot(state_history, "final_state.png")
        >>> vis.save_static_plot(state_history, "midpoint.png", time_step=50, dpi=300)
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        state = state_history[time_step]
        cart_x, cart_y, p1_x, p1_y, p2_x, p2_y = self._calculate_positions(state)

        # Set axis limits
        all_x = [cart_x, p1_x, p2_x]
        all_y = [cart_y, p1_y, p2_y]
        margin = 1.0
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)

        # Draw ground
        cart_w, cart_h = 0.4, 0.2
        ground_y = -cart_h / 2
        ax.plot(ax.get_xlim(), [ground_y, ground_y], "k-", lw=2, label="Ground")

        # Draw cart
        cart = plt.Rectangle((cart_x - cart_w/2, ground_y), cart_w, cart_h,
                           facecolor='lightblue', edgecolor='black', linewidth=2)
        ax.add_patch(cart)

        # Draw links
        ax.plot([cart_x, p1_x], [0, p1_y], "ro-", lw=4, markersize=10, label="Link 1")
        ax.plot([p1_x, p2_x], [p1_y, p2_y], "bo-", lw=4, markersize=10, label="Link 2")

        # Add angle annotations
        th1_deg = np.rad2deg(state[1])
        th2_deg = np.rad2deg(state[2])
        ax.text(0.02, 0.98, f"θ₁ = {th1_deg:.1f}°\nθ₂ = {th2_deg:.1f}°",
                transform=ax.transAxes, va='top', fontsize=12,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

        ax.set_xlabel("Position (m)")
        ax.set_ylabel("Height (m)")
        ax.set_title(f"Double Inverted Pendulum - Time Step {time_step}")
        ax.legend()

        plt.tight_layout()
        plt.savefig(filename, **kwargs)
        plt.close(fig)
        print(f"Static plot saved to: {filename}")

    def create_phase_plot(self, state_history: np.ndarray, filename: str = None, **kwargs):
        """
        Create phase space plots for the pendulum angles.

        Parameters
        ----------
        state_history : np.ndarray
            2-D array of state vectors over time [x, th1, th2, xdot, th1dot, th2dot]
        filename : str, optional
            If provided, save the plot to this file
        **kwargs
            Additional arguments passed to plt.savefig() if filename is provided

        Returns
        -------
        matplotlib.figure.Figure
            The created figure object

        Examples
        --------
        >>> fig = vis.create_phase_plot(state_history)
        >>> vis.create_phase_plot(state_history, "phase_plot.png", dpi=300)
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # Extract state variables
        th1 = np.rad2deg(state_history[:, 1])
        th2 = np.rad2deg(state_history[:, 2])
        th1_dot = np.rad2deg(state_history[:, 4])
        th2_dot = np.rad2deg(state_history[:, 5])

        # Phase plots
        axes[0, 0].plot(th1, th1_dot, 'r-', alpha=0.7, linewidth=2)
        axes[0, 0].set_xlabel("θ₁ (degrees)")
        axes[0, 0].set_ylabel("θ̇₁ (degrees/s)")
        axes[0, 0].set_title("Link 1 Phase Space")
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].plot(th2, th2_dot, 'b-', alpha=0.7, linewidth=2)
        axes[0, 1].set_xlabel("θ₂ (degrees)")
        axes[0, 1].set_ylabel("θ̇₂ (degrees/s)")
        axes[0, 1].set_title("Link 2 Phase Space")
        axes[0, 1].grid(True, alpha=0.3)

        # Time series
        t = np.arange(len(state_history)) * 0.01  # Assuming 0.01s timestep
        axes[1, 0].plot(t, th1, 'r-', label='θ₁', linewidth=2)
        axes[1, 0].plot(t, th2, 'b-', label='θ₂', linewidth=2)
        axes[1, 0].set_xlabel("Time (s)")
        axes[1, 0].set_ylabel("Angle (degrees)")
        axes[1, 0].set_title("Angle Time Series")
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].plot(t, th1_dot, 'r-', label='θ̇₁', linewidth=2)
        axes[1, 1].plot(t, th2_dot, 'b-', label='θ̇₂', linewidth=2)
        axes[1, 1].set_xlabel("Time (s)")
        axes[1, 1].set_ylabel("Angular Velocity (degrees/s)")
        axes[1, 1].set_title("Angular Velocity Time Series")
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if filename:
            plt.savefig(filename, **kwargs)
            print(f"Phase plot saved to: {filename}")
            plt.close(fig)

        return fig
