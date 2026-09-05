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

    # Not sure if this is right
    desired_state: DesiredState
