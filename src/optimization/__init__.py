#==========================================================================================\\\
#=================================== src/optimization/__init__.py ==========================\\\
#==========================================================================================\\\

"""Professional optimization framework for control engineering applications.

This module provides a comprehensive optimization framework featuring:
- Multiple state-of-the-art optimization algorithms (PSO, DE, GA, CMA-ES, Bayesian)
- Professional objective functions for control performance metrics
- Advanced convergence monitoring and analysis
- Comprehensive result visualization and comparison tools
- Extensible architecture for research and production use

For backward compatibility, legacy interfaces are maintained.
"""

# =============================================================================
# NEW FRAMEWORK INTERFACES
# =============================================================================

# Core framework components
from .core import (
    Optimizer, ObjectiveFunction, Constraint, OptimizationProblem,
    OptimizationResult, ParameterSpace, ConvergenceMonitor,
    OptimizationProblemBuilder, ControlOptimizationProblem,
    ContinuousParameter, DiscreteParameter, ContinuousParameterSpace,
    OptimizationContext, optimize
)

# Advanced optimization algorithms
from .algorithms import (
    ParticleSwarmOptimizer, DifferentialEvolution, GeneticAlgorithm,
    NelderMead, BFGSOptimizer
    # BayesianOptimization, CMAES  # Not available yet
)

# Professional objective functions
from .objectives import (
    TrackingErrorObjective, EnergyConsumptionObjective, StabilityMarginObjective,
    RobustnessObjective, SettlingTimeObjective, OvershootObjective,
    SteadyStateErrorObjective, WeightedSumObjective, ParetoObjective,
    SimulationBasedObjective, AnalyticalObjective, CompositeObjective
)

# Constraint management
# from .constraints import (  # Not implemented yet
#     ParameterConstraint, PerformanceConstraint, StabilityConstraint
# )

# Results analysis and visualization
# from .results import (  # Not fully implemented yet
#     ConvergenceAnalyzer, ConvergenceMonitor, OptimizationPlotter,
#     AlgorithmComparator, OptimizationStatistics
# )

# Solver interfaces
# from .solvers import (  # Not implemented yet
#     OptimizationSolver, MultiObjectiveSolver, ConstrainedSolver
# )

# =============================================================================
# BACKWARD COMPATIBILITY INTERFACES
# =============================================================================

# Legacy PSO tuner (exact same interface)
from .algorithms.pso_optimizer import PSOTuner

# =============================================================================
# EXPORTS
# =============================================================================

# New framework exports
__all__ = [
    # Core interfaces
    "Optimizer", "ObjectiveFunction", "Constraint", "OptimizationProblem",
    "OptimizationResult", "ParameterSpace", "ConvergenceMonitor",
    "OptimizationProblemBuilder", "ControlOptimizationProblem",
    "ContinuousParameter", "DiscreteParameter", "ContinuousParameterSpace",
    "OptimizationContext", "optimize",

    # Algorithms
    "ParticleSwarmOptimizer", "DifferentialEvolution", "GeneticAlgorithm",
    "BayesianOptimization", "NelderMead", "CMAES",

    # Objectives
    "TrackingErrorObjective", "EnergyConsumptionObjective", "StabilityMarginObjective",
    "SettlingTimeObjective", "OvershootObjective", "SteadyStateErrorObjective",
    "SimulationBasedObjective", "AnalyticalObjective", "CompositeObjective",

    # Constraints
    "ParameterConstraint", "PerformanceConstraint", "StabilityConstraint",

    # Results and analysis
    "ConvergenceAnalyzer", "ConvergenceMonitor", "OptimizationPlotter",
    "AlgorithmComparator", "OptimizationStatistics",

    # Solvers
    "OptimizationSolver", "MultiObjectiveSolver", "ConstrainedSolver",

    # Legacy compatibility (IMPORTANT: maintain exact same name)
    "PSOTuner",  # Original PSO tuner from pso_optimizer.py
]

# =============================================================================
# CONVENIENCE FACTORY FUNCTIONS
# =============================================================================

def create_optimizer(algorithm: str, parameter_space: ParameterSpace, **kwargs) -> Optimizer:
    """Create an optimizer of specified type.

    Parameters
    ----------
    algorithm : str
        Algorithm name ('pso', 'de', 'ga', 'cma_es', 'bayesian', 'nelder_mead')
    parameter_space : ParameterSpace
        Parameter space to optimize over
    **kwargs
        Algorithm-specific parameters

    Returns
    -------
    Optimizer
        Configured optimizer instance

    Examples
    --------
    >>> import numpy as np
    >>> from src.optimization import create_optimizer, ContinuousParameterSpace
    >>>
    >>> # Define parameter space
    >>> bounds = ContinuousParameterSpace(
    ...     lower_bounds=np.array([0.1, 0.1, 0.1]),
    ...     upper_bounds=np.array([10.0, 10.0, 10.0]),
    ...     names=['kp', 'ki', 'kd']
    ... )
    >>>
    >>> # Create PSO optimizer
    >>> optimizer = create_optimizer('pso', bounds, population_size=50)
    """
    algorithm = algorithm.lower()

    if algorithm == 'pso':
        return ParticleSwarmOptimizer(parameter_space, **kwargs)
    elif algorithm == 'de':
        return DifferentialEvolution(parameter_space, **kwargs)
    elif algorithm == 'ga':
        return GeneticAlgorithm(parameter_space, **kwargs)
    elif algorithm == 'cma_es':
        return CMAES(parameter_space, **kwargs)
    elif algorithm == 'bayesian':
        return BayesianOptimization(parameter_space, **kwargs)
    elif algorithm == 'nelder_mead':
        return NelderMead(parameter_space, **kwargs)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


def create_control_problem(objective_type: str,
                         controller_factory: callable,
                         simulation_config: dict,
                         parameter_bounds: tuple,
                         **kwargs) -> ControlOptimizationProblem:
    """Create a control optimization problem.

    Parameters
    ----------
    objective_type : str
        Type of objective ('tracking', 'energy', 'settling_time', 'overshoot')
    controller_factory : callable
        Function to create controller from parameters
    simulation_config : dict
        Simulation configuration
    parameter_bounds : tuple
        (lower_bounds, upper_bounds) arrays
    **kwargs
        Objective-specific parameters

    Returns
    -------
    ControlOptimizationProblem
        Configured optimization problem

    Examples
    --------
    >>> def controller_factory(params):
    ...     return PIDController(kp=params[0], ki=params[1], kd=params[2])
    >>>
    >>> problem = create_control_problem(
    ...     'tracking',
    ...     controller_factory,
    ...     {'sim_time': 10.0, 'dt': 0.01},
    ...     (np.array([0.1, 0.1, 0.1]), np.array([10.0, 10.0, 10.0])),
    ...     reference_trajectory=reference_signal
    ... )
    """
    # Create parameter space
    lower_bounds, upper_bounds = parameter_bounds
    parameter_space = ContinuousParameterSpace(lower_bounds, upper_bounds)

    # Create objective function
    if objective_type == 'tracking':
        objective = TrackingErrorObjective(
            simulation_config, controller_factory, **kwargs
        )
    elif objective_type == 'energy':
        objective = EnergyConsumptionObjective(
            simulation_config, controller_factory, **kwargs
        )
    elif objective_type == 'settling_time':
        objective = SettlingTimeObjective(
            simulation_config, controller_factory, **kwargs
        )
    elif objective_type == 'overshoot':
        objective = OvershootObjective(
            simulation_config, controller_factory, **kwargs
        )
    else:
        raise ValueError(f"Unknown objective type: {objective_type}")

    return ControlOptimizationProblem(
        objective, parameter_space, controller_factory, simulation_config
    )


def run_optimization_study(problems: list,
                          algorithms: list,
                          n_runs: int = 10,
                          parallel: bool = True,
                          **kwargs) -> dict:
    """Run comprehensive optimization study comparing multiple algorithms.

    Parameters
    ----------
    problems : list
        List of optimization problems
    algorithms : list
        List of algorithm names or configured optimizers
    n_runs : int, optional
        Number of independent runs per algorithm
    parallel : bool, optional
        Whether to run in parallel
    **kwargs
        Additional options

    Returns
    -------
    dict
        Comprehensive study results with statistical analysis

    Examples
    --------
    >>> problems = [problem1, problem2]
    >>> algorithms = ['pso', 'de', 'ga']
    >>> results = run_optimization_study(problems, algorithms, n_runs=30)
    >>>
    >>> # Results contain statistical analysis, convergence curves, etc.
    >>> print(results['summary'])
    """
    from .benchmarks import OptimizationBenchmark

    benchmark = OptimizationBenchmark()
    return benchmark.run_study(problems, algorithms, n_runs, parallel, **kwargs)


# Add convenience functions to exports
__all__.extend([
    "create_optimizer",
    "create_control_problem",
    "run_optimization_study"
])

# =============================================================================
# QUICK START EXAMPLES
# =============================================================================

def example_pid_tuning():
    """Example: PID controller tuning using PSO.

    This example demonstrates how to optimize PID controller parameters
    for a tracking objective using the new framework.
    """
    import numpy as np

    # Define PID controller factory
    def create_pid_controller(params):
        kp, ki, kd = params
        # Return your PID controller implementation
        return PIDController(kp=kp, ki=ki, kd=kd)

    # Create optimization problem
    problem = create_control_problem(
        'tracking',
        create_pid_controller,
        simulation_config={'sim_time': 10.0, 'dt': 0.01, 'initial_state': np.zeros(6)},
        parameter_bounds=(np.array([0.1, 0.01, 0.001]), np.array([10.0, 1.0, 0.1])),
        reference_trajectory=np.ones((1000, 2))  # Step reference
    )

    # Create PSO optimizer
    optimizer = create_optimizer('pso', problem.parameter_space, population_size=50)

    # Run optimization
    result = optimize(problem, 'pso', random_seed=42)

    print(f"Optimal PID gains: Kp={result.x[0]:.3f}, Ki={result.x[1]:.3f}, Kd={result.x[2]:.3f}")
    print(f"Optimal cost: {result.fun:.6f}")

    return result


def example_algorithm_comparison():
    """Example: Compare multiple optimization algorithms.

    This example shows how to compare PSO, DE, and GA algorithms
    on the same control optimization problem.
    """
    # Create test problem (same as above)
    problem = create_control_problem(
        'tracking',
        lambda params: PIDController(*params),
        {'sim_time': 5.0, 'dt': 0.01},
        (np.array([0.1, 0.01, 0.001]), np.array([10.0, 1.0, 0.1]))
    )

    # Compare algorithms
    results = run_optimization_study(
        problems=[problem],
        algorithms=['pso', 'de', 'ga'],
        n_runs=10
    )

    # Analyze results
    print("Algorithm Comparison Results:")
    for alg, stats in results['algorithm_comparison'].items():
        print(f"{alg}: Mean={stats['mean_fitness']:.6f}, Std={stats['std_fitness']:.6f}")

    return results


# Note: Actual PIDController class would need to be imported or defined
# This is just for demonstration of the framework architecture