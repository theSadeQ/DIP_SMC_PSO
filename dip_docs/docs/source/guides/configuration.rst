Configuration
=============

Project configuration is typically managed via a YAML/JSON file (e.g., ``config.yaml``).
Key sections often include:

- ``simulation``: time-step (dt), duration
- ``controller``: controller type, gains
- ``pso``: swarm size, iterations, bounds
- ``sensors``: quantization, noise

Example (YAML):

.. code-block:: yaml

   simulation:
     dt: 0.01
     duration: 10.0
   
   controller:
     type: sta_smc
     gains:
       k1: 10.0
       k2: 2.5
   
   pso:
     particles: 24
     iters: 40
   
   sensors:
     quantization_angle: 0.01
     quantization_position: 0.0005
