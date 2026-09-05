from typing import Protocol, runtime_checkable

from pylibreconcile.desired_state import DesiredState


@runtime_checkable
class ResourceManager(Protocol):
    def create(self, desired_state: DesiredState) -> None:
        """Create the desired state in the observed state."""
        ...

    def update(self, desired_state: DesiredState) -> None:
        """Update the observed state to match the desired state."""
        ...

    def delete(self, desired_state: DesiredState) -> None:
        """Delete the desired state from the observed state."""
        ...
