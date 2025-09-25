#==========================================================================================\\\
#=================== src/simulation/orchestrators/parallel.py ======================\\\
#==========================================================================================\\\

"""Parallel simulation orchestrator for multi-threaded execution."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional
import numpy as np

from .base import BaseOrchestrator
from .sequential import SequentialOrchestrator
from ..core.interfaces import ResultContainer
from ..results.containers import BatchResultContainer


class ParallelOrchestrator(BaseOrchestrator):
    """Parallel simulation orchestrator for multi-threaded execution.

    This orchestrator executes multiple simulations in parallel using
    a thread pool, providing performance improvements for independent
    simulation runs such as Monte Carlo analysis.
    """

    def __init__(self, context, max_workers: Optional[int] = None):
        """Initialize parallel orchestrator.

        Parameters
        ----------
        context : SimulationContext
            Simulation context
        max_workers : int, optional
            Maximum number of worker threads (default: CPU count)
        """
        super().__init__(context)
        self.max_workers = max_workers

    def execute(self,
               initial_state: np.ndarray,
               control_inputs: np.ndarray,
               dt: float,
               horizon: int,
               **kwargs) -> ResultContainer:
        """Execute parallel simulation.

        Parameters
        ----------
        initial_state : np.ndarray
            Initial state(s) - shape (state_dim,) or (batch_size, state_dim)
        control_inputs : np.ndarray
            Control input sequence(s)
        dt : float
            Time step
        horizon : int
            Simulation horizon
        **kwargs
            Additional options

        Returns
        -------
        ResultContainer
            Parallel simulation results
        """
        self._validate_simulation_inputs(initial_state, control_inputs, dt, horizon)

        start_time = time.perf_counter()

        # Determine if this is a batch of simulations
        initial_state = np.atleast_2d(initial_state)
        batch_size = initial_state.shape[0]

        if batch_size == 1:
            # Single simulation - use sequential orchestrator
            sequential = SequentialOrchestrator(self.context)
            result = sequential.execute(initial_state[0], control_inputs, dt, horizon, **kwargs)
        else:
            # Multiple simulations - execute in parallel
            result = self._execute_parallel_batch(initial_state, control_inputs, dt, horizon, **kwargs)

        # Update statistics
        execution_time = time.perf_counter() - start_time
        total_steps = batch_size * horizon
        self._update_stats(total_steps, execution_time)

        return result

    def _execute_parallel_batch(self,
                               initial_states: np.ndarray,
                               control_inputs: np.ndarray,
                               dt: float,
                               horizon: int,
                               **kwargs) -> ResultContainer:
        """Execute batch simulations in parallel."""
        batch_size = initial_states.shape[0]

        # Prepare individual simulation parameters
        simulation_params = []
        for i in range(batch_size):
            initial_state = initial_states[i]

            # Extract control inputs for this simulation
            if control_inputs.ndim == 1:
                # Single control sequence for all
                controls = control_inputs
            elif control_inputs.ndim == 2:
                if control_inputs.shape[0] == batch_size:
                    # Batch of control sequences
                    controls = control_inputs[i]
                else:
                    # Single control sequence with multiple inputs per step
                    controls = control_inputs
            elif control_inputs.ndim == 3:
                # Batch of multi-input control sequences
                controls = control_inputs[i]
            else:
                controls = control_inputs

            simulation_params.append((initial_state, controls, dt, horizon, kwargs.copy()))

        # Execute simulations in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all simulations
            future_to_index = {
                executor.submit(self._run_single_simulation, *params): i
                for i, params in enumerate(simulation_params)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results.append((index, result))
                except Exception as e:
                    # Handle failed simulation
                    print(f"Simulation {index} failed: {e}")
                    results.append((index, None))

        # Sort results by original index
        results.sort(key=lambda x: x[0])

        # Combine into batch result container
        batch_result = BatchResultContainer()
        for index, result in results:
            if result is not None:
                states = result.get_states()
                times = result.get_times()
                controls = getattr(result, 'controls', None)

                batch_result.add_trajectory(states, times,
                                          controls=controls, batch_index=index)

        return batch_result

    def _run_single_simulation(self,
                             initial_state: np.ndarray,
                             control_inputs: np.ndarray,
                             dt: float,
                             horizon: int,
                             kwargs: dict) -> ResultContainer:
        """Run a single simulation using sequential orchestrator.

        This method creates a new sequential orchestrator for each worker
        to avoid thread safety issues.
        """
        # Create a new context for this thread
        context = type(self.context)(self.context.config.model_dump_json())
        sequential = SequentialOrchestrator(context)

        return sequential.execute(initial_state, control_inputs, dt, horizon, **kwargs)


class WorkerPool:
    """Reusable worker pool for parallel simulations."""

    def __init__(self, max_workers: Optional[int] = None):
        """Initialize worker pool.

        Parameters
        ----------
        max_workers : int, optional
            Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.executor = None

    def __enter__(self):
        """Enter context manager."""
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.executor:
            self.executor.shutdown(wait=True)

    def map_simulations(self,
                       simulation_fn: Callable,
                       parameters: List[Any]) -> List[Any]:
        """Map simulation function over parameter list.

        Parameters
        ----------
        simulation_fn : callable
            Simulation function to execute
        parameters : list
            List of parameter tuples for each simulation

        Returns
        -------
        list
            List of simulation results
        """
        if self.executor is None:
            raise RuntimeError("Worker pool not initialized. Use as context manager.")

        futures = [self.executor.submit(simulation_fn, *params) for params in parameters]
        results = []

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Simulation failed: {e}")
                results.append(None)

        return results


def run_parallel_simulations(
    simulation_configs: List[dict],
    max_workers: Optional[int] = None
) -> List[ResultContainer]:
    """Run multiple simulations in parallel.

    Parameters
    ----------
    simulation_configs : list
        List of simulation configuration dictionaries
    max_workers : int, optional
        Maximum number of worker threads

    Returns
    -------
    list
        List of simulation results
    """
    def run_single_config(config):
        from ..core.simulation_context import SimulationContext

        # Create context and orchestrator for this configuration
        context = SimulationContext(config.get('config_path', 'config.yaml'))
        orchestrator = SequentialOrchestrator(context)

        return orchestrator.execute(
            config['initial_state'],
            config['control_inputs'],
            config['dt'],
            config['horizon'],
            **config.get('kwargs', {})
        )

    with WorkerPool(max_workers) as pool:
        results = pool.map_simulations(run_single_config,
                                     [(config,) for config in simulation_configs])

    return results