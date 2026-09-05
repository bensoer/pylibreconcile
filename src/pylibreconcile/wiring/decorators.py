from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pylibreconcile.desired_state import DesiredState
from pylibreconcile.observed_state import ObservedStateHandler
from pylibreconcile.resource_manager import ResourceManager

from .container import WiringContainer

_T = TypeVar("_T", bound=type[DesiredState])


def register_observed_state_handler(
    instance: ObservedStateHandler,
) -> Callable[[_T], _T]:
    def decorator(cls: _T) -> _T:
        WiringContainer()._set_observed_state_handler(cls, instance)
        return cls

    return decorator


def register_resource_manager(
    instance: ResourceManager,
) -> Callable[[_T], _T]:
    def decorator(cls: _T) -> _T:
        WiringContainer()._set_resource_manager(cls, instance)
        return cls

    return decorator
