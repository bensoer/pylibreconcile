from dataclasses import dataclass
from enum import Enum

from .desired_state import DesiredState


class ChangeType(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class Change:
    type: ChangeType
    desired_state: DesiredState
    action_performed: bool = True
    """True if the Reconciler actually performed the action.

    False ONLY when drift was detected AND ``DriftPolicy.FLAG``
    caused the Reconciler to report the drift without recreating.
    All other code paths leave this True. The future reconcile
    loop (Seed 6) populates this correctly; today every Change
    that the existing code constructs will have the default True.
    """
