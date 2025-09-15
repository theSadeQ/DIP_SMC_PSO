#==========================================================================================\\\
#================================ src/controllers/__init__.py =============================\\\
#==========================================================================================\\\
"""Expose controller classes and keep backward-compatibility aliases."""

from .adaptive_smc import AdaptiveSMC
# Canonical class names
from .classic_smc import ClassicalSMC
from .classic_smc import ClassicalSMC as classic_smc  # old lowercase alias
from .sta_smc import SuperTwistingSMC

# ------------------------------------------------------------------------
# Back-compat aliases (older code expected these symbols / filenames)-----
# ------------------------------------------------------------------------
STASMC = SuperTwistingSMC            # sometimes used in notebooks

__all__ = [
    "classic_smc",       
    "ClassicalSMC",
    "SuperTwistingSMC",
    "STASMC",
    "AdaptiveSMC",
]

