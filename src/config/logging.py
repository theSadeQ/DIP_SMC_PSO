#==========================================================================================\\\
#=================================== src/config/logging.py ==============================\\\
#==========================================================================================\\\
"""
Centralised logging configuration with provenance stamping.

This module configures the root logger to record run provenance in every
log message.  Provenance fields include the short Git commit SHA of
the working directory, a hash of the configuration dictionary and the
master random seed.  The logger is configured using a filter that
adds these fields to each ``LogRecord`` and a format string that
prefixes messages with ``[commit|cfg_hash|seed=<seed>]``.  By
including such metadata in logs, researchers can unambiguously trace
results back to the precise code and configuration that generated
them, satisfying reproducibility guidelines【985132039892507†L364-L377】.

The design of this module is inspired by best practices for
reproducible computational research.  Sandve et al. (2013) emphasise
that analyses involving randomness must record the underlying random
seed so that results can be replicated exactly【985132039892507†L364-L377】.
Similarly, tagging logs with the commit SHA and configuration hash
allows others to verify that they are running the same code base and
parameters.  Logging provenance promotes transparency and fosters
confidence in published results.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from typing import Any, Dict

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # Safe fallback when PyYAML is unavailable


class ProvenanceFilter(logging.Filter):
    """Inject commit, configuration hash and seed into log records.

    Parameters
    ----------
    commit_sha : str
        Short Git commit SHA (or "unknown" if unavailable).
    config_hash : str
        Truncated SHA‑256 hash of the configuration dictionary.
    seed : int
        Master random seed recorded in logs.
    """

    def __init__(self, commit_sha: str, config_hash: str, seed: int) -> None:
        super().__init__()
        self.commit_sha = commit_sha
        self.config_hash = config_hash
        self.seed = seed

    def filter(self, record: logging.LogRecord) -> bool:
        # Attach provenance attributes to the record.  These names
        # correspond to the placeholders used in the log format string.
        record.commit = self.commit_sha
        record.cfg_hash = self.config_hash
        record.seed = self.seed
        return True


def _compute_config_hash(config: Dict[str, Any]) -> str:
    """Compute a truncated SHA‑256 hash of a configuration dictionary.

    When PyYAML is available the configuration is serialised via
    ``yaml.safe_dump`` to obtain a canonical representation.  When
    unavailable, ``repr`` is used as a fallback.  The full SHA‑256
    digest is computed and truncated to the first eight hexadecimal
    characters to produce a compact identifier.  Hashing the
    configuration ensures that even small changes in parameter values
    produce different identifiers, facilitating provenance tracking.
    """
    if config is None:
        return "00000000"
    try:
        if yaml is not None:
            dumped = yaml.safe_dump(config, sort_keys=True)
        else:
            dumped = repr(config)
        digest = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
        return digest[:8]
    except Exception:
        # Fallback to a constant when hashing fails
        return "00000000"


def _get_git_commit() -> str:
    """Return the short Git commit SHA of the current working tree.

    If the repository is not under version control or Git is not
    installed, return "unknown".  The commit SHA is determined by
    invoking ``git rev-parse --short HEAD`` via subprocess.  Any
    exceptions are caught and masked to preserve robustness.
    """
    try:
        # Use subprocess to query the Git commit.  The ``text`` flag
        # ensures a string result on both Python 3.8 and 3.11.
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return sha if sha else "unknown"
    except Exception:
        return "unknown"


def configure_provenance_logging(config: Dict[str, Any], seed: int, *, level: int = logging.INFO) -> None:
    """Configure the root logger with provenance stamping.

    This helper sets up logging such that each log record includes
    provenance metadata.  It should be called once near the start of
    an application, before any logging calls are made.  Subsequent
    calls will reconfigure the root logger and may override previous
    handlers.

    Parameters
    ----------
    config : dict
        The configuration dictionary to hash.  Nested structures are
        supported.  Passing ``None`` results in a constant hash.
    seed : int
        The master random seed to record.  According to reproducibility
        guidelines, this value should be stored in logs so that
        stochastic runs can be reproduced exactly【985132039892507†L364-L377】.
    level : int, optional
        Logging level for the root logger.  Defaults to ``logging.INFO``.
    """
    commit = _get_git_commit()
    cfg_hash = _compute_config_hash(config)
    seed_val = int(seed) if seed is not None else 0

    # Do NOT call logging.basicConfig here (tests assert no basicConfig on import).
    # Instead, attach a provenance filter to the root logger so records carry fields.
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Avoid duplicate filters on repeated calls
    have_filter = any(isinstance(f, ProvenanceFilter) for f in root_logger.filters)
    if not have_filter:
        root_logger.addFilter(ProvenanceFilter(commit, cfg_hash, seed_val))
    # If no handlers are configured, attach a minimal StreamHandler with a formatter
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter("[%(commit)s|%(cfg_hash)s|seed=%(seed)s] %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(fmt)
        handler.setLevel(level)
        root_logger.addHandler(handler)

    # Log a startup message summarising the provenance.  This makes
    # provenance visible at the beginning of the log and aids in
    # debugging.  The commit and configuration hash identify the code
    # and configuration used, while the seed ensures deterministic
    # initialisation【985132039892507†L364-L377】.
    logging.info(
        f"Provenance configured: commit={commit}, cfg_hash={cfg_hash}, seed={seed_val}"
    )


__all__ = ["configure_provenance_logging", "ProvenanceFilter"]
