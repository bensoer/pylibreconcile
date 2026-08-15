from collections.abc import Iterable

from .core import DesiredState


class Reconciler:
    def __init__(self, desired_states: Iterable[DesiredState]) -> None:
        self._desired_states = list(desired_states)

    def reconcile(self) -> list[DesiredState]:
        return list(self._desired_states)
