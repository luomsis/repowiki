"""Error vocabulary shared by every module (exit codes: 1 = usage/state, 2 = conflict).

Lives in a leaf module on purpose: nothing here imports anything, so command
modules can raise these without importing back into :mod:`repowiki.cli`.
:class:`UsageError` and :class:`StateError` map to exit code 1,
:class:`ConflictError` to exit code 2 (the mapping lives in cli.main).
"""

from __future__ import annotations


class ConflictError(Exception):
    """State conflict, e.g. task already claimed by a live worker."""


class StateError(Exception):
    """Persisted state is unreadable (e.g. corrupt index.json); data-preserving abort."""


class UsageError(Exception):
    """User/input error reported with exit code 1."""
