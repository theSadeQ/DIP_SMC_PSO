========================
Plant Server
========================
.. currentmodule:: src.hil.plant_server

Overview
--------
Hardware-in-the-loop plant server that simulates double-inverted pendulum dynamics and serves state information over TCP sockets. The server runs plant dynamics locally and accepts control inputs from remote controller clients, enabling distributed HIL testing architectures.

Examples
--------
.. doctest::

   >>> from src.hil.plant_server import PlantServer, start_server
   >>> # Start HIL plant server for remote controller connections
   >>> server = start_server("config.yaml", max_steps=1000)
   >>> # Server runs in background, serving plant dynamics
   >>> # Controller clients can connect to receive states and send control inputs

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.hil.plant_server

Detailed API
------------
.. automodule:: src.hil.plant_server
   :members:
   :undoc-members:
   :show-inheritance: