from __future__ import annotations

import pytest

from pylibreconcile import DesiredState, WiringContainer


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


class CustomDesiredState(DesiredState):
    pass


def test_singleton_returns_same_instance() -> None:
    container = WiringContainer()
    assert WiringContainer() is WiringContainer()
    assert hasattr(container, "_wiring")
    assert container._wiring == {}


def test_clear_resets_registry() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    container.register(CustomDesiredState, observed_state_handler=observer)
    assert container.get(CustomDesiredState) is not None
    container.clear()
    assert container.get(CustomDesiredState) is None


def test_register_with_observer_only() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    container.register(CustomDesiredState, observed_state_handler=observer)
    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None


def test_register_with_manager_only() -> None:
    container = WiringContainer()
    manager = FakeManager()
    container.register(CustomDesiredState, resource_manager=manager)
    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is None
    assert result[1] is manager


def test_register_with_both() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()
    container.register(CustomDesiredState, observer, manager)
    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_register_with_neither_raises() -> None:
    container = WiringContainer()

    with pytest.raises(ValueError, match="at least one of") as excinfo:
        container.register(CustomDesiredState, None, None)
    assert "CustomDesiredState" in str(excinfo.value)


def test_register_with_no_args_raises() -> None:
    container = WiringContainer()
    with pytest.raises(ValueError, match="at least one of"):
        container.register(CustomDesiredState)


def test_get_returns_registered_pair() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()
    container.register(CustomDesiredState, observer, manager)
    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_get_returns_none_for_unregistered() -> None:
    container = WiringContainer()
    result = container.get(CustomDesiredState)
    assert result is None


def test_get_walks_mro() -> None:
    class A(CustomDesiredState):
        pass

    class B(A):
        pass

    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()
    container.register(A, observer, manager)

    result = container.get(B)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_get_walks_mro_returns_closest_first() -> None:
    class A(CustomDesiredState):
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
    assert result[0] is observer_b
    assert result[1] is manager_b


def test_clear_then_register_works() -> None:
    container = WiringContainer()
    container.register(CustomDesiredState, FakeObserver(), FakeManager())
    container.clear()
    container.register(CustomDesiredState, FakeObserver(), FakeManager())
    assert container.get(CustomDesiredState) is not None


def test_register_overwrites() -> None:
    container = WiringContainer()
    observer1 = FakeObserver()
    manager1 = FakeManager()
    observer2 = FakeObserver()
    manager2 = FakeManager()

    container.register(CustomDesiredState, observer1, manager1)
    container.register(CustomDesiredState, observer2, manager2)

    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is observer2
    assert result[1] is manager2


def test_register_pair_merges_partial_registrations() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    manager = FakeManager()

    container._register_pair(CustomDesiredState, observed_state_handler=observer)
    container._register_pair(CustomDesiredState, resource_manager=manager)

    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is manager


def test_register_pair_first_call_with_only_one_does_not_raise() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    container._register_pair(CustomDesiredState, observed_state_handler=observer)
    result = container.get(CustomDesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None


def test_register_base_desired_state() -> None:
    container = WiringContainer()
    observer = FakeObserver()
    container.register(DesiredState, observed_state_handler=observer)
    result = container.get(DesiredState)
    assert result is not None
    assert result[0] is observer
    assert result[1] is None
