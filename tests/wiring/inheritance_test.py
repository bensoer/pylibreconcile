from __future__ import annotations

import pytest

from pylibreconcile import WiringContainer, DesiredState
from pylibreconcile.wiring.decorators import (
    register_observed_state_handler,
    register_resource_manager,
)
from pylibreconcile.observed_state import ObservedStateHandler
from pylibreconcile.resource_manager import ResourceManager


class FakeObserver:
    def exists(self, desired_state: DesiredState) -> bool:
        return True

    def is_match(self, desired_state: DesiredState) -> bool:
        return True


class FakeManager:
    def create(self, desired_state: DesiredState) -> None:
        pass

    def update(self, desired_state: DesiredState) -> None:
        pass

    def delete(self, desired_state: DesiredState) -> None:
        pass


def test_one_level_inheritance_walks_mro() -> None:
    @register_observed_state_handler(FakeObserver())
    class A(DesiredState):
        pass

    class B(A):
        pass

    container = WiringContainer()
    result = container.get(B)
    assert result is not None
    assert isinstance(result[0], FakeObserver)
    assert result[1] is None


def test_three_level_inheritance_walks_mro() -> None:
    @register_observed_state_handler(FakeObserver())
    class A(DesiredState):
        pass

    class B(A):
        pass

    class C(B):
        pass

    container = WiringContainer()
    result = container.get(C)
    assert result is not None
    assert isinstance(result[0], FakeObserver)
    assert result[1] is None


def test_child_decoration_overrides_parent() -> None:
    observer_a = FakeObserver()
    manager_a = FakeManager()
    observer_b = FakeObserver()
    manager_b = FakeManager()

    @register_observed_state_handler(observer_a)
    @register_resource_manager(manager_a)
    class A(DesiredState):
        pass

    @register_observed_state_handler(observer_b)
    @register_resource_manager(manager_b)
    class B(A):
        pass

    container = WiringContainer()
    result = container.get(B)
    assert result is not None
    # Should return B's wiring, not A's
    assert result[0] is observer_b
    assert result[1] is manager_b