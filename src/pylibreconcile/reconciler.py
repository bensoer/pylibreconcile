from collections.abc import Iterable

from .change import Change, ChangeType
from .desired_state import DesiredState
from .known_state import KnownStateHandler


class Reconciler:
    def __init__(self, known_state_handler: KnownStateHandler) -> None:
        self._known_state_handler: KnownStateHandler = known_state_handler

    def get_change_set(self, desired_states: Iterable[DesiredState]) -> list[Change]:
        """Create a change set of desired states that need to be reconciled."""

        change_set: list[Change] = []

        # Find all the CREATES
        for desired_state in desired_states:
            # If not in the known state, thats a CREATE
            if not self._known_state_handler.exists(desired_state):
                change_set.append(Change(type=ChangeType.CREATE, desired_state=desired_state))
            # If it is in the known state, but not a match, thats an UPDATE
            elif not self._known_state_handler.is_match(desired_state):
                change_set.append(Change(type=ChangeType.UPDATE, desired_state=desired_state))
            # If it is in the known state, and a match, its good. NOOP
            else:
                pass

        # Find all the DELETES
        for known_state in self._known_state_handler.get_all():
            # If not in the desired states, thats a DELETE
            if known_state not in desired_states:
                change_set.append(Change(type=ChangeType.DELETE, desired_state=known_state))

        return change_set

    def reconcile(self) -> list[DesiredState]:
        return list(self._desired_states)
