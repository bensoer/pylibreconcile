from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Configuration:
    """Reconciler policy settings.

    All fields default to ``None``; call ``with_defaults()`` to
    resolve ``None`` fields to their system defaults. Pass per-call
    ``Configuration`` objects with only the fields you want to
    override set — ``applied_over`` merges non-``None`` fields
    over a base ``Configuration``.
    """

    drift_policy: DriftPolicy | None = None
    import_policy: ImportPolicy | None = None

    def with_defaults(self) -> Configuration:
        """Return a new Configuration with None fields resolved to defaults."""
        return Configuration(
            drift_policy=self.drift_policy if self.drift_policy is not None else DriftPolicy.FLAG,
            import_policy=self.import_policy
            if self.import_policy is not None
            else ImportPolicy.WARN,
        )

    def applied_over(self, base: Configuration) -> Configuration:
        """Return a new Configuration where every non-None field in self replaces the
        corresponding field in base."""
        return Configuration(
            drift_policy=self.drift_policy if self.drift_policy is not None else base.drift_policy,
            import_policy=self.import_policy
            if self.import_policy is not None
            else base.import_policy,
        )
