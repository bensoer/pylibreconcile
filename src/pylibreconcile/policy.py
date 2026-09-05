from __future__ import annotations

from enum import Enum


class DriftPolicy(Enum):
    """How the Reconciler should respond to detected drift.

    Drift = Desired exists, Observed does not, Known exists.
    See `docs/context/overview.md` decision matrix.
    """

    FLAG = "FLAG"
    """Report drift via ``Change``; do not correct. Requires
    ``ObservedStateHandler`` only; ``ResourceManager`` optional."""

    RECREATE = "RECREATE"
    """Auto-correct drift by re-invoking the ``ResourceManager``'s
    ``create`` / ``update``. Requires a ``ResourceManager`` for every
    ``DesiredState`` type in scope."""

    ABSTAIN = "ABSTAIN"
    """Skip drift silently. ``ResourceManager`` may be present or
    absent; no validation against wiring."""


class ImportPolicy(Enum):
    """How the Reconciler should respond to detected import cases.

    Import = Desired exists, Observed exists, Known does not.
    See `docs/context/overview.md` decision matrix and D-Q9.
    """

    AUTO = "AUTO"
    """Auto-import and continue. Imported resource becomes managed."""

    WARN = "WARN"
    """Auto-import but include the imported item in the return value
    so the caller can log it. Default."""

    REJECT = "REJECT"
    """Raise / fail immediately on import detection."""

    SKIP = "SKIP"
    """Do nothing; leave the resource unmanaged; continue."""
