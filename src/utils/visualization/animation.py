#==========================================================================================\\\
#===================== src/utils/visualization/animation.py ============================\\\
#==========================================================================================\\\

"""
Animation utilities for dynamic system visualization.

Provides real-time and recorded animation capabilities for the double
inverted pendulum and control system visualization.
"""

from __future__ import annotations
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple, Optional, Callable
from matplotlib.patches import FancyArrowPatch, Rectangle

class DIPAnimator:
    """Animate a controlled double inverted pendulum."""

    def __init__(self, pendulum_model, figsize: Tuple[float, float] = (12, 7)):
        """Initialize the animator with pendulum model."""
        self.pendulum = pendulum_model
        self.fig, self.ax = plt.subplots(figsize=figsize)

        # Animation elements
        self.cart_patch = None
        self.link1_line = None
        self.link2_line = None
        self.force_arrow = None

        # Text displays
        self.time_text = self.ax.text(
            0.05, 0.95, "", transform=self.ax.transAxes,
            va="top", fontsize=12, bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
        )
        self.angle_text = self.ax.text(
            0.05, 0.85, "", transform=self.ax.transAxes,
            va="top", fontsize=12, bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
        )
        self.control_text = self.ax.text(
            0.05, 0.75, "", transform=self.ax.transAxes,
            va="top", fontsize=12, bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
        )

        self._setup_plot()

    def _setup_plot(self) -> None:
        """Setup the plot appearance and elements."""
        # Set axis properties
        self.ax.set_xlim(-3, 3)
        self.ax.set_ylim(-0.5, 3)
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel("Position (m)")
        self.ax.set_ylabel("Height (m)")
        self.ax.set_title("Double Inverted Pendulum Animation")

        # Draw ground line
        self.ax.axhline(y=0, color='brown', linewidth=3, label='Ground')

        # Initialize animation elements
        self.cart_patch = Rectangle((0, 0), 0.4, 0.2, facecolor='lightblue',
                                   edgecolor='black', linewidth=2)
        self.ax.add_patch(self.cart_patch)

        self.link1_line, = self.ax.plot([], [], 'ro-', linewidth=4, markersize=10, label='Link 1')
        self.link2_line, = self.ax.plot([], [], 'bo-', linewidth=4, markersize=10, label='Link 2')

        self.force_arrow = FancyArrowPatch((0, 0), (0, 0), arrowstyle='->',
                                          mutation_scale=20, color='red', linewidth=3)
        self.ax.add_patch(self.force_arrow)
        self.force_arrow.set_visible(False)

        self.ax.legend(loc='upper right')

    def _calculate_positions(self, state: np.ndarray) -> Tuple[float, ...]:
        """Calculate positions of cart and pendulum ends."""
        x, th1, th2 = state[0], state[1], state[2]
        l1, l2 = self.pendulum.l1, self.pendulum.l2

        # Cart position
        cart_x, cart_y = x, 0.1

        # Pendulum 1 end position
        p1_x = x + l1 * np.sin(th1)
        p1_y = cart_y + l1 * np.cos(th1)

        # Pendulum 2 end position
        p2_x = p1_x + l2 * np.sin(th2)
        p2_y = p1_y + l2 * np.cos(th2)

        return cart_x, cart_y, p1_x, p1_y, p2_x, p2_y

    def animate_frame(self, frame_data: Tuple[float, np.ndarray, float]) -> List:
        """Animate a single frame."""
        time, state, control_force = frame_data

        # Calculate positions
        cart_x, cart_y, p1_x, p1_y, p2_x, p2_y = self._calculate_positions(state)

        # Update cart
        cart_w, cart_h = 0.4, 0.2
        self.cart_patch.set_xy((cart_x - cart_w/2, cart_y - cart_h/2))

        # Update pendulum links
        self.link1_line.set_data([cart_x, p1_x], [cart_y, p1_y])
        self.link2_line.set_data([p1_x, p2_x], [p1_y, p2_y])

        # Update force arrow
        if abs(control_force) > 0.1:
            force_scale = 0.5
            arrow_end_x = cart_x + force_scale * np.sign(control_force)
            self.force_arrow.set_positions((cart_x, cart_y), (arrow_end_x, cart_y))
            self.force_arrow.set_visible(True)
        else:
            self.force_arrow.set_visible(False)

        # Update text displays
        self.time_text.set_text(f'Time: {time:.2f} s')
        self.angle_text.set_text(f'θ₁: {np.rad2deg(state[1]):.1f}°\nθ₂: {np.rad2deg(state[2]):.1f}°')
        self.control_text.set_text(f'Force: {control_force:.2f} N')

        return [self.cart_patch, self.link1_line, self.link2_line, self.force_arrow,
                self.time_text, self.angle_text, self.control_text]

    def create_animation(
        self,
        state_history: List[np.ndarray],
        control_history: List[float],
        time_history: List[float],
        interval: int = 50
    ) -> animation.FuncAnimation:
        """Create animation from simulation data."""

        # Prepare frame data
        frame_data = [(t, s, u) for t, s, u in zip(time_history, state_history, control_history)]

        # Create animation
        anim = animation.FuncAnimation(
            self.fig,
            self.animate_frame,
            frames=frame_data,
            interval=interval,
            blit=True,
            repeat=True
        )

        return anim

    def save_animation(
        self,
        state_history: List[np.ndarray],
        control_history: List[float],
        time_history: List[float],
        filename: str,
        fps: int = 20,
        **kwargs
    ) -> None:
        """Save animation to file."""
        anim = self.create_animation(state_history, control_history, time_history)

        # Default writer settings
        writer_kwargs = {
            'fps': fps,
            'metadata': {'artist': 'DIP Control System'},
        }
        writer_kwargs.update(kwargs)

        anim.save(filename, writer='pillow', **writer_kwargs)
        plt.close(self.fig)

class MultiSystemAnimator:
    """Animate multiple systems or comparison scenarios."""

    def __init__(self, num_systems: int, figsize: Tuple[float, float] = (16, 8)):
        """Initialize multi-system animator."""
        self.num_systems = num_systems
        self.fig, self.axes = plt.subplots(1, num_systems, figsize=figsize)

        if num_systems == 1:
            self.axes = [self.axes]

        self.animators = []
        for i, ax in enumerate(self.axes):
            # Create individual animator for each subplot
            animator = DIPAnimator(None, figsize)
            animator.ax = ax
            animator.fig = self.fig
            self.animators.append(animator)

    def create_comparison_animation(
        self,
        systems_data: List[Tuple[str, List[np.ndarray], List[float], List[float]]],
        interval: int = 50
    ) -> animation.FuncAnimation:
        """Create comparison animation for multiple systems."""

        def animate_all_frames(frame_idx):
            artists = []
            for i, (title, state_hist, control_hist, time_hist) in enumerate(systems_data):
                if frame_idx < len(state_hist):
                    frame_data = (time_hist[frame_idx], state_hist[frame_idx], control_hist[frame_idx])
                    frame_artists = self.animators[i].animate_frame(frame_data)
                    artists.extend(frame_artists)
                    self.axes[i].set_title(title)
            return artists

        # Find maximum number of frames
        max_frames = max(len(data[1]) for data in systems_data)

        anim = animation.FuncAnimation(
            self.fig,
            animate_all_frames,
            frames=max_frames,
            interval=interval,
            blit=True,
            repeat=True
        )

        return anim