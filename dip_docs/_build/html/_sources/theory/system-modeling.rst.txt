System Modeling
===============

Mathematical Notation
---------------------

The system dynamics are described by:

.. math::

   \ddot{q} = f(q, \dot{q}) + B(q)u


where :math:``q \in \mathbb{R}^4`` represents the system states (cart position and pendulum angles), :math:``u \in \mathbb{R}`` is the control input, and the control objective is to stabilize the system around the unstable equilibrium.

Bibliography
------------

References
----------

Bibliography coming soon - citations system is being configured.

Project Links
-------------

- 📚 ``Theory Overview <theory_overview.md>``_
- 🎮 ``Controller Documentation <controllers/index.md>``_
- 📖 ``API Reference <api/index.md>``_
- 🔬 ``Examples <examples/index.md>``_
=== DIRECTORY STRUCTURE ===
docs/.github/ISSUE_TEMPLATE/bug_report.md
docs/.github/ISSUE_TEMPLATE/feature_request.md
docs/.github/PULL_REQUEST_TEMPLATE.md
docs/analysis_plan.md
docs/api/index.md
docs/architecture.md
docs/CHANGELOG.md
docs/CLAUDE.md
docs/context.md
docs/CONTRIBUTING.md
docs/controllers/index.md
docs/index.md
docs/optimization/index.md
docs/plant_model.md
docs/presentation/0-Introduction & Motivation.md
docs/presentation/1-Problem Statement & Objectives.md
docs/presentation/2-Previous Works.md
docs/presentation/3-System Modling.md
docs/presentation/4-0-SMC.md
docs/presentation/5-Chattering & Mitigation.md
docs/presentation/6-PSO.md
docs/presentation/7-Simulation Setup.md
docs/presentation/8-Results and Discussion.md
docs/presentation/chattering-mitigation.md
docs/presentation/index.md
docs/presentation/introduction.md
docs/presentation/previous-works.md
docs/presentation/problem-statement.md
docs/presentation/pso-optimization.md
docs/presentation/results-discussion.md
docs/presentation/simulation-setup.md
docs/presentation/smc-theory.md
docs/presentation/system-modeling.md
docs/README.md
docs/RELEASE_CHECKLIST.md
docs/results_readme.md
docs/symbols.md
docs/test_protocols.md
docs/TESTING.md
docs/theory_overview.md
docs/use_cases.md

=== SAMPLE CONTENT FILES (for reference) ===
