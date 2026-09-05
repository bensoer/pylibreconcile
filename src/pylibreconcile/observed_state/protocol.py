from typing import Protocol, runtime_checkable

from pylibreconcile.desired_state import DesiredState


@runtime_checkable
class ObservedStateHandler(Protocol):
    def exists(self, desired_state: DesiredState) -> bool:
        """Return True if the desired state exists in the observed state."""
        ...

    def is_match(self, desired_state: DesiredState) -> bool:
        """Return True if the desired state matches the observed state."""
        ...
