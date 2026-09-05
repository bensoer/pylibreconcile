from __future__ import annotations

from pylibreconcile.desired_state import DesiredState
from pylibreconcile.observed_state import ObservedStateHandler
from pylibreconcile.resource_manager import ResourceManager


class WiringContainer:
    _instance: WiringContainer | None = None
    _wiring: dict[type[DesiredState], tuple[ObservedStateHandler | None, ResourceManager | None]]

    def __new__(cls) -> WiringContainer:
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._wiring = {}
            cls._instance = inst
        return cls._instance

    def register(
        self,
        desired_state_type: type[DesiredState],
        observed_state_handler: ObservedStateHandler | None = None,
        resource_manager: ResourceManager | None = None,
    ) -> None:
        if observed_state_handler is None and resource_manager is None:
            raise ValueError(
                f"register({desired_state_type.__name__}): at least one of "
                "observed_state_handler or resource_manager must be non-None"
            )
        self._wiring[desired_state_type] = (
            observed_state_handler,
            resource_manager,
        )

    def get(
        self,
        desired_state_type: type[DesiredState],
    ) -> tuple[ObservedStateHandler | None, ResourceManager | None] | None:
        for mro_cls in desired_state_type.__mro__:
            if mro_cls in self._wiring:
                return self._wiring[mro_cls]
        return None

    def clear(self) -> None:
        self._wiring.clear()

    def _register_pair(
        self,
        desired_state_type: type[DesiredState],
        observed_state_handler: ObservedStateHandler | None = None,
        resource_manager: ResourceManager | None = None,
    ) -> None:
        existing = self._wiring.get(desired_state_type)
        if existing is not None:
            prev_observed, prev_manager = existing
            if observed_state_handler is None:
                observed_state_handler = prev_observed
            if resource_manager is None:
                resource_manager = prev_manager
        self.register(
            desired_state_type=desired_state_type,
            observed_state_handler=observed_state_handler,
            resource_manager=resource_manager,
        )
