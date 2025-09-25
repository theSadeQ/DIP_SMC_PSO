#==========================================================================================\\\
#==================== src/utils/visualization/movie_generator.py ======================\\\
#==========================================================================================\\\

"""
Complete visualization plan for the entire DIP control project.

Provides comprehensive movie generation capabilities for documenting
and presenting the complete control engineering project with professional
quality animations and analysis visualizations.
"""

from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import os
from dataclasses import dataclass
from .animation import DIPAnimator, MultiSystemAnimator
from .static_plots import ControlPlotter, SystemVisualization

@dataclass
class MovieScene:
    """Configuration for a movie scene."""
    title: str
    duration: float  # seconds
    data: Dict[str, Any]
    scene_type: str  # 'animation', 'static', 'comparison', 'analysis'
    description: str

class ProjectMovieGenerator:
    """
    Complete visualization plan generator for the entire DIP control project.

    Creates professional-quality movies that document:
    - System dynamics and behavior
    - Control algorithm performance
    - Comparison studies
    - Optimization results
    - Statistical analysis
    """

    def __init__(self, output_dir: str = "project_movies"):
        """Initialize movie generator."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.animator = DIPAnimator(None)
        self.plotter = ControlPlotter()
        self.system_viz = SystemVisualization()

    def create_complete_project_movie(
        self,
        project_data: Dict[str, Any],
        movie_title: str = "DIP Control Engineering Project",
        fps: int = 30
    ) -> str:
        """
        Create a complete movie documenting the entire project.

        Movie Structure:
        1. Introduction and system overview
        2. Plant dynamics demonstration
        3. Controller implementations
        4. Comparative analysis
        5. Optimization results
        6. Statistical validation
        7. Conclusions and future work
        """

        scenes = self._create_movie_scenes(project_data)
        movie_path = os.path.join(self.output_dir, f"{movie_title.replace(' ', '_')}.mp4")

        return self._compile_scenes_to_movie(scenes, movie_path, fps)

    def _create_movie_scenes(self, project_data: Dict[str, Any]) -> List[MovieScene]:
        """Create all movie scenes for the complete project documentation."""

        scenes = []

        # Scene 1: Project Introduction
        scenes.append(MovieScene(
            title="Project Introduction",
            duration=10.0,
            data=project_data.get('overview', {}),
            scene_type='static',
            description="Overview of the double inverted pendulum control project"
        ))

        # Scene 2: System Dynamics
        scenes.append(MovieScene(
            title="System Dynamics",
            duration=15.0,
            data=project_data.get('plant_dynamics', {}),
            scene_type='animation',
            description="Demonstration of uncontrolled system dynamics"
        ))

        # Scene 3: Controller Implementations
        for controller_name, controller_data in project_data.get('controllers', {}).items():
            scenes.append(MovieScene(
                title=f"{controller_name} Controller",
                duration=20.0,
                data=controller_data,
                scene_type='animation',
                description=f"Performance demonstration of {controller_name}"
            ))

        # Scene 4: Comparative Analysis
        scenes.append(MovieScene(
            title="Controller Comparison",
            duration=25.0,
            data=project_data.get('comparison', {}),
            scene_type='comparison',
            description="Side-by-side comparison of all controllers"
        ))

        # Scene 5: Optimization Results
        if 'optimization' in project_data:
            scenes.append(MovieScene(
                title="Parameter Optimization",
                duration=20.0,
                data=project_data['optimization'],
                scene_type='analysis',
                description="PSO optimization results and convergence"
            ))

        # Scene 6: Statistical Analysis
        if 'statistics' in project_data:
            scenes.append(MovieScene(
                title="Statistical Validation",
                duration=15.0,
                data=project_data['statistics'],
                scene_type='analysis',
                description="Monte Carlo analysis and confidence intervals"
            ))

        # Scene 7: Robustness Analysis
        if 'robustness' in project_data:
            scenes.append(MovieScene(
                title="Robustness Analysis",
                duration=18.0,
                data=project_data['robustness'],
                scene_type='analysis',
                description="System performance under uncertainties"
            ))

        return scenes

    def _compile_scenes_to_movie(self, scenes: List[MovieScene], output_path: str, fps: int) -> str:
        """Compile all scenes into a single movie file."""

        # Create individual scene animations
        scene_files = []

        for i, scene in enumerate(scenes):
            scene_path = os.path.join(self.output_dir, f"scene_{i:02d}_{scene.title.replace(' ', '_')}.mp4")

            if scene.scene_type == 'animation':
                self._create_animation_scene(scene, scene_path, fps)
            elif scene.scene_type == 'static':
                self._create_static_scene(scene, scene_path, fps)
            elif scene.scene_type == 'comparison':
                self._create_comparison_scene(scene, scene_path, fps)
            elif scene.scene_type == 'analysis':
                self._create_analysis_scene(scene, scene_path, fps)

            scene_files.append(scene_path)

        # Compile scenes using ffmpeg (if available)
        try:
            self._merge_videos(scene_files, output_path)
        except Exception as e:
            print(f"Video compilation failed: {e}")
            print("Individual scene files created successfully:")
            for file in scene_files:
                print(f"  - {file}")

        return output_path

    def _create_animation_scene(self, scene: MovieScene, output_path: str, fps: int) -> None:
        """Create an animated scene."""
        data = scene.data

        # Extract simulation data
        time_history = data.get('time', [])
        state_history = data.get('states', [])
        control_history = data.get('controls', [])

        if not all([time_history, state_history, control_history]):
            print(f"Warning: Insufficient data for animation scene '{scene.title}'")
            return

        # Create animation
        animator = DIPAnimator(None, figsize=(16, 9))

        # Add title and description
        animator.fig.suptitle(scene.title, fontsize=20, fontweight='bold')
        animator.ax.text(0.02, 0.02, scene.description, transform=animator.ax.transAxes,
                        fontsize=12, bbox=dict(boxstyle="round", facecolor="white", alpha=0.9))

        # Save animation
        animator.save_animation(state_history, control_history, time_history, output_path, fps=fps)

    def _create_static_scene(self, scene: MovieScene, output_path: str, fps: int) -> None:
        """Create a static information scene."""
        fig, ax = plt.subplots(figsize=(16, 9))

        # Create informational slide
        ax.text(0.5, 0.8, scene.title, ha='center', va='center', fontsize=32, fontweight='bold')
        ax.text(0.5, 0.6, scene.description, ha='center', va='center', fontsize=18, wrap=True)

        # Add project information
        if 'project_info' in scene.data:
            info_text = self._format_project_info(scene.data['project_info'])
            ax.text(0.5, 0.3, info_text, ha='center', va='center', fontsize=14)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Save as static video (repeated frames)
        frames = int(scene.duration * fps)

        def animate_static(frame):
            return []

        anim = animation.FuncAnimation(fig, animate_static, frames=frames, interval=1000/fps)
        anim.save(output_path, writer='pillow', fps=fps)
        plt.close(fig)

    def _create_comparison_scene(self, scene: MovieScene, output_path: str, fps: int) -> None:
        """Create a controller comparison scene."""
        data = scene.data
        controllers = data.get('controllers', {})

        if len(controllers) < 2:
            print(f"Warning: Not enough controllers for comparison scene '{scene.title}'")
            return

        # Prepare data for multi-system animation
        systems_data = []
        for name, controller_data in controllers.items():
            systems_data.append((
                name,
                controller_data.get('states', []),
                controller_data.get('controls', []),
                controller_data.get('time', [])
            ))

        # Create multi-system animator
        multi_animator = MultiSystemAnimator(len(systems_data), figsize=(20, 10))

        # Add overall title
        multi_animator.fig.suptitle(scene.title, fontsize=20, fontweight='bold')

        # Create and save animation
        anim = multi_animator.create_comparison_animation(systems_data, interval=1000//fps)
        anim.save(output_path, writer='pillow', fps=fps)
        plt.close(multi_animator.fig)

    def _create_analysis_scene(self, scene: MovieScene, output_path: str, fps: int) -> None:
        """Create an analysis visualization scene."""
        data = scene.data

        # Create analysis plots
        fig = plt.figure(figsize=(16, 9))

        if scene.title == "Parameter Optimization":
            self._create_optimization_analysis(fig, data)
        elif scene.title == "Statistical Validation":
            self._create_statistical_analysis(fig, data)
        elif scene.title == "Robustness Analysis":
            self._create_robustness_analysis(fig, data)

        fig.suptitle(scene.title, fontsize=20, fontweight='bold')

        # Save as animated plot progression
        frames = int(scene.duration * fps)

        def animate_analysis(frame):
            # Gradually reveal analysis results
            alpha = min(1.0, frame / (frames * 0.3))
            for ax in fig.get_axes():
                for artist in ax.get_children():
                    if hasattr(artist, 'set_alpha'):
                        artist.set_alpha(alpha)
            return fig.get_children()

        anim = animation.FuncAnimation(fig, animate_analysis, frames=frames, interval=1000/fps)
        anim.save(output_path, writer='pillow', fps=fps)
        plt.close(fig)

    def _create_optimization_analysis(self, fig: plt.Figure, data: Dict[str, Any]) -> None:
        """Create PSO optimization analysis plots."""
        gs = fig.add_gridspec(2, 2)

        # Convergence plot
        ax1 = fig.add_subplot(gs[0, :])
        if 'convergence' in data:
            ax1.plot(data['convergence'], linewidth=2)
            ax1.set_title("PSO Convergence")
            ax1.set_xlabel("Iteration")
            ax1.set_ylabel("Best Fitness")
            ax1.grid(True, alpha=0.3)

        # Parameter evolution
        ax2 = fig.add_subplot(gs[1, 0])
        if 'parameter_evolution' in data:
            for i, param_hist in enumerate(data['parameter_evolution']):
                ax2.plot(param_hist, label=f'Param {i+1}')
            ax2.set_title("Parameter Evolution")
            ax2.set_xlabel("Iteration")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        # Final performance
        ax3 = fig.add_subplot(gs[1, 1])
        if 'final_performance' in data:
            performance = data['final_performance']
            ax3.bar(performance.keys(), performance.values())
            ax3.set_title("Final Performance Metrics")
            ax3.tick_params(axis='x', rotation=45)

    def _create_statistical_analysis(self, fig: plt.Figure, data: Dict[str, Any]) -> None:
        """Create statistical analysis plots."""
        gs = fig.add_gridspec(2, 2)

        # Performance distributions
        ax1 = fig.add_subplot(gs[0, :])
        if 'performance_distributions' in data:
            for controller, values in data['performance_distributions'].items():
                ax1.hist(values, alpha=0.7, label=controller, bins=30)
            ax1.set_title("Performance Distributions")
            ax1.set_xlabel("Performance Metric")
            ax1.set_ylabel("Frequency")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Confidence intervals
        ax2 = fig.add_subplot(gs[1, 0])
        if 'confidence_intervals' in data:
            controllers = list(data['confidence_intervals'].keys())
            means = [data['confidence_intervals'][c]['mean'] for c in controllers]
            errors = [data['confidence_intervals'][c]['error'] for c in controllers]
            ax2.errorbar(range(len(controllers)), means, yerr=errors, fmt='o', capsize=5)
            ax2.set_xticks(range(len(controllers)))
            ax2.set_xticklabels(controllers, rotation=45)
            ax2.set_title("Performance Confidence Intervals")
            ax2.grid(True, alpha=0.3)

    def _format_project_info(self, info: Dict[str, Any]) -> str:
        """Format project information for display."""
        lines = []
        for key, value in info.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _merge_videos(self, video_files: List[str], output_path: str) -> None:
        """Merge multiple video files using ffmpeg."""
        import subprocess

        # Create file list for ffmpeg
        list_file = os.path.join(self.output_dir, "video_list.txt")
        with open(list_file, 'w') as f:
            for video_file in video_files:
                f.write(f"file '{video_file}'\n")

        # Run ffmpeg
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file,
            '-c', 'copy', output_path, '-y'
        ]

        subprocess.run(cmd, check=True)
        os.remove(list_file)

    def create_project_trailer(self, project_data: Dict[str, Any], duration: float = 60.0) -> str:
        """Create a short trailer/summary of the project."""
        trailer_data = {
            'overview': project_data.get('overview', {}),
            'highlights': self._extract_highlights(project_data),
            'results_summary': self._summarize_results(project_data)
        }

        trailer_path = os.path.join(self.output_dir, "project_trailer.mp4")

        # Create condensed version of key scenes
        scenes = [
            MovieScene("Project Overview", 10.0, trailer_data['overview'], 'static',
                      "Brief introduction to the DIP control project"),
            MovieScene("Key Results", 30.0, trailer_data['highlights'], 'comparison',
                      "Highlights of controller performance"),
            MovieScene("Summary", 20.0, trailer_data['results_summary'], 'analysis',
                      "Summary of achievements and conclusions")
        ]

        return self._compile_scenes_to_movie(scenes, trailer_path, fps=30)

    def _extract_highlights(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract highlight results for trailer."""
        # Select best performing controllers and key results
        highlights = {}

        if 'controllers' in project_data:
            # Select top 2-3 performing controllers
            controllers = project_data['controllers']
            highlights['controllers'] = dict(list(controllers.items())[:3])

        return highlights

    def _summarize_results(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize key project results."""
        summary = {}

        if 'final_metrics' in project_data:
            summary['metrics'] = project_data['final_metrics']

        if 'conclusions' in project_data:
            summary['conclusions'] = project_data['conclusions']

        return summary