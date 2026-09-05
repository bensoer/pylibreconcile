from __future__ import annotations

from collections.abc import Iterable

from .desired_state import DesiredState
from .known_state import KnownStateHandler
from .policy import Configuration, DriftPolicy
from .wiring import WiringContainer


class Reconciler:
    def __init__(
        self,
        desired_states: Iterable[DesiredState],
        known_state_handler: KnownStateHandler,
        config: Configuration = Configuration(),
    ) -> None:
        self._desired_states = list(desired_states)
        self._known_state_handler = known_state_handler
        self._config = config.with_defaults()
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
            if self._config.drift_policy is DriftPolicy.RECREATE and manager is None:
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
        config: Configuration | None = None,
    ) -> list[DesiredState]:
        if config is None:
            effective = self._config
        else:
            effective = config.applied_over(self._config)
        self._effective_config = effective
        self._validate_effective_policy_for_wiring(effective.drift_policy)
        return list(self._desired_states)

    def _validate_effective_policy_for_wiring(
        self,
        effective_drift: DriftPolicy | None,
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
