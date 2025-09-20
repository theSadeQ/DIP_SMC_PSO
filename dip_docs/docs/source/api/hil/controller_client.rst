========================
Controller Client
========================
.. currentmodule:: src.hil.controller_client

Overview
--------
Hardware-in-the-loop controller client that connects to a plant server over TCP sockets. The client runs control algorithms locally and communicates with a remote plant simulation, enabling distributed HIL testing of double-inverted pendulum controllers.

Examples
--------
.. doctest::

   >>> from src.hil.controller_client import HILControllerClient, run_client
   >>> import numpy as np
   >>> # Create HIL client for remote plant connection
   >>> client = HILControllerClient(
   ...     host="localhost",
   ...     port=12345,
   ...     controller_type="classical_smc"
   ... )
   >>> # Run HIL simulation with specified steps
   >>> results_path = run_client("config.yaml", steps=100)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.hil.controller_client

Detailed API
------------
.. automodule:: src.hil.controller_client
   :members:
   :undoc-members:
   :show-inheritance: