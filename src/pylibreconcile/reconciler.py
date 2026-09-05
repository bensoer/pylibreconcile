from __future__ import annotations

from collections.abc import Iterable

from .desired_state import DesiredState
from .known_state import KnownStateHandler
from .policy import DriftPolicy, ImportPolicy
from .wiring import WiringContainer


class Reconciler:
    def __init__(
        self,
        desired_states: Iterable[DesiredState],
        known_state_handler: KnownStateHandler,
        drift_policy: DriftPolicy = DriftPolicy.FLAG,
        import_policy: ImportPolicy = ImportPolicy.WARN,
    ) -> None:
        self._desired_states = list(desired_states)
        self._known_state_handler = known_state_handler
        self._drift_policy = drift_policy
        self._import_policy = import_policy
        self._validate_wiring_for_settings()

    def _validate_wiring_for_settings(self) -> None:
        unique_types: set[type[DesiredState]] = {type(d) for d in self._desired_states}
        missing: list[str] = []
        recreate_without_manager: list[str] = []
        for desired_state_type in unique_types:
            wiring = WiringContainer().get(desired_state_type)
            if wiring is None:
                missing.append(desired_state_type.__name__)
                continue
            observed, manager = wiring
            if observed is None and manager is None:
                missing.append(desired_state_type.__name__)
                continue
            if self._drift_policy is DriftPolicy.RECREATE and manager is None:
                recreate_without_manager.append(desired_state_type.__name__)
        if missing or recreate_without_manager:
            parts: list[str] = []
            if missing:
                parts.append(
                    "DesiredState types with no registered handlers: " + ", ".join(sorted(missing))
                )
            if recreate_without_manager:
                parts.append(
                    "DriftPolicy.RECREATE requires a ResourceManager for: "
                    + ", ".join(sorted(recreate_without_manager))
                )
            raise ValueError(
                "Reconciler.__init__: wiring does not satisfy policy. " + " | ".join(parts)
            )

    def reconcile(
        self,
        drift_policy: DriftPolicy | None = None,
        import_policy: ImportPolicy | None = None,
    ) -> list[DesiredState]:
        effective_drift = drift_policy if drift_policy is not None else self._drift_policy
        effective_import = import_policy if import_policy is not None else self._import_policy
        self._effective_drift_policy = effective_drift
        self._effective_import_policy = effective_import
        self._validate_effective_policy_for_wiring(effective_drift)
        return list(self._desired_states)

    def _validate_effective_policy_for_wiring(
        self,
        effective_drift: DriftPolicy,
    ) -> None:
        if effective_drift is not DriftPolicy.RECREATE:
            return
        unique_types: set[type[DesiredState]] = {type(d) for d in self._desired_states}
        recreate_without_manager: list[str] = []
        for desired_state_type in unique_types:
            wiring = WiringContainer().get(desired_state_type)
            if wiring is None:
                continue
            _observed, manager = wiring
            if manager is None:
                recreate_without_manager.append(desired_state_type.__name__)
        if recreate_without_manager:
            raise ValueError(
                "Reconciler.reconcile(drift_policy=RECREATE): "
                "missing ResourceManager for: " + ", ".join(sorted(recreate_without_manager))
            )
