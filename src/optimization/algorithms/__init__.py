#==========================================================================================\\\
#======================== src/optimization/algorithms/__init__.py =====================\\\
#==========================================================================================\\\

"""Professional optimization algorithms for control engineering applications."""

# Swarm Intelligence Algorithms
from .swarm.pso import ParticleSwarmOptimizer, PSOTuner
# from .swarm.aco import AntColonyOptimization  # Module not implemented yet

# Evolutionary Algorithms
from .evolutionary.genetic import GeneticAlgorithm, GeneticAlgorithmConfig
from .evolutionary.differential import DifferentialEvolution
# from .evolutionary.cma_es import CMAES  # Not implemented yet

# Gradient-Based Algorithms
from .gradient_based.nelder_mead import NelderMead, NelderMeadConfig
from .gradient_based.bfgs import BFGSOptimizer, BFGSConfig

# Bayesian Optimization
# from .bayesian.gaussian_process import BayesianOptimization  # Not implemented yet

__all__ = [
    # Swarm Intelligence
    "ParticleSwarmOptimizer",
    "PSOTuner",  # Legacy compatibility
    # "AntColonyOptimization",  # Not available yet

    # Evolutionary
    "GeneticAlgorithm",
    "GeneticAlgorithmConfig",
    "DifferentialEvolution",
    # "CMAES",  # Not available yet

    # Gradient-Based
    "NelderMead",
    "NelderMeadConfig",
    "BFGSOptimizer",
    "BFGSConfig",

    # Bayesian
    # "BayesianOptimization"  # Not available yet
]