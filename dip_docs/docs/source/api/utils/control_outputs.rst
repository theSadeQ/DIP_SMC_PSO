========================
Control Outputs
========================
.. currentmodule:: src.utils.control_outputs

Overview
--------
Structured return types for controllers.

Examples
--------
.. doctest::

   >>> from src.utils.control_outputs import ClassicalSMCOutput, AdaptiveSMCOutput, STAOutput, HybridSTAOutput
   >>> # Classical SMC returns saturated input, empty state, and an optional history
   >>> o1 = ClassicalSMCOutput(u=7.5, state=(), history={"sigma": 0.12})
   >>> (o1.u, o1.state, isinstance(tuple(o1), tuple))
   (7.5, (), True)

   >>> # Adaptive SMC includes adaptation state and current sliding surface sigma
   >>> o2 = AdaptiveSMCOutput(u=6.0, state=(0.98,), history={"z": 0.1}, sigma=0.05)
   >>> (o2.u > 0) and ("z" in o2.history) and (abs(o2.sigma) < 1.0)
   True

   >>> # Super-Twisting controller returns two auxiliary states (e.g., z, sigma)
   >>> o3 = STAOutput(u=-3.2, state=(0.01, -0.15), history={})
   >>> (len(o3.state) >= 2) and isinstance(o3.history, dict)
   True

   >>> # Hybrid adaptive STA variant bundles gains/integral state & sigma
   >>> o4 = HybridSTAOutput(u=4.0, state=(1.2, 0.8, 0.0), history={"k1": [1.2]}, sigma=0.02)
   >>> (o4.u, round(o4.sigma, 2))
   (4.0, 0.02)

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.utils.control_outputs

Detailed API
------------
.. automodule:: src.utils.control_outputs
   :members:
   :undoc-members:
   :show-inheritance:
