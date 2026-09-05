from __future__ import annotations

import pytest

from pylibreconcile import WiringContainer, DesiredState
from pylibreconcile.desired_state import DesiredState as BaseDesiredState
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


def test_singleton_returns_same_instance() -> None:
    assert WiringContainer() is WiringContainer()


def test_clear_resets_registry() -> None:
    container = WiringContainer()
    container.register(BaseDesiredState, FakeObserver(), FakeManager())
    assert container.get(BaseDesiredState) is not None
    container.clear()
    assert container.get(BaseDesiredState) is None


def test_register_with_observer_only() -> None:
    container = WiringContainer()
    # Should not raise
    container.register(BaseDesiredState, observed_state_handler=FakeObserver())


def test_register_with_manager_only() -> None:
    container = WiringContainer()
    # Should not raise
    container.register(BaseDesiredState, resource_manager=FakeManager())


def test_register_with_both() -> None:
    container = WiringContainer()
    # Should not raise
    container.register(BaseDesiredState, FakeObserver(), FakeManager())


def test_register_with_neither_raises() -> None:
    container = WiringContainer()
    class TestState(DesiredState):
        pass

    with pytest.raises(ValueError) as excinfo:
        container.register(TestState, None, None)
    assert "at least one of" in str(excinfo.value)
    assert "TestState" in str(excinfo.value)


def test_get_returns_registered_pair() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()
    container.register(BaseDesiredState, observer, manager)
    result = container.get(BaseDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_get_returns_none_for_unregistered() -> None:
    container = WiringContainer()
    assert container.get(BaseDesiredState) is None


def test_get_walks_mro() -> None:
    class A(BaseDesiredState):
        pass

    class B(A):
        pass

    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()
    container.register(A, observer, manager)

    # B is not registered, but should get A's wiring via MRO
    result = container.get(B)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_get_walks_mro_returns_closest_first() -> None:
    class A(BaseDesiredState):
        pass

    class B(A):
        pass

    container = WiringContainer()
    observer_a = FakeObserver()
    manager_a = FakeManager()
    observer_b = FakeObserver()
    manager_b = FakeManager()

    container.register(A, observer_a, manager_a)
    container.register(B, observer_b, manager_b)

    result = container.get(B)
    assert result is not None
    # Should return B's wiring, not A's
    assert result[0] is observer_b
    assert result[1] is manager_b


def test_clear_then_register_works() -> None:
    container = WiringContainer()
    container.register(BaseDesiredState, FakeObserver(), FakeManager())
    container.clear()
    # Register again after clear
    container.register(BaseDesiredState, FakeObserver(), FakeManager())
    assert container.get(BaseDesiredState) is not None


def test_register_overwrites() -> None:
    container = WiringContainer()
    observer1 = FakeObserver()
    manager1 = FakeManager()
    observer2 = FakeObserver()
    manager2 = FakeManager()

    container.register(BaseDesiredState, observer1, manager1)
    container.register(BaseDesiredState, observer2, manager2)

    result = container.get(BaseDesiredState)
    assert result is not None
    assert result[0] is observer2
    assert result[1] is manager2


def test_register_pair_merges_partial_registrations() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()

    # First call with only observer
    container._register_pair(BaseDesiredState, observed_state_handler=observer)
    # Second call with only manager
    container._register_pair(BaseDesiredState, resource_manager=manager)

    result = container.get(BaseDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_register_pair_first_call_with_only_one_does_not_raise() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    # This should not raise because we are using _register_pair with only one set
    container._register_pair(BaseDesiredState, observed_state_handler=observer)
    # Now get should return (observer, None)
    result = container.get(BaseDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None