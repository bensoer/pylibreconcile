from __future__ import annotations

import pytest

from pylibreconcile import DesiredState, DriftPolicy, Reconciler
from pylibreconcile.wiring import register_observed_state_handler, register_resource_manager


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


def test_constructor_accepts_observer_only_with_flag() -> None:
    @register_observed_state_handler(FakeObserver())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    # Should not raise
    Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.FLAG)  # type: ignore


def test_constructor_accepts_manager_only_with_flag() -> None:
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    # Should not raise
    Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.FLAG)  # type: ignore


def test_constructor_accepts_both_with_flag() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    # Should not raise
    Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.FLAG)  # type: ignore


def test_constructor_accepts_any_wiring_with_abstain() -> None:
    # Observer-only
    @register_observed_state_handler(FakeObserver())
    class ObserverOnlyState(DesiredState):
        id: int

    # Manager-only
    @register_resource_manager(FakeManager())
    class ManagerOnlyState(DesiredState):
        id: int

    # Both
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class BothState(DesiredState):
        id: int

    states = [ObserverOnlyState(id=1), ManagerOnlyState(id=2), BothState(id=3)]
    # Should not raise for any combination with ABSTAIN
    Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.ABSTAIN)  # type: ignore


def test_constructor_recreate_requires_manager() -> None:
    @register_observed_state_handler(FakeObserver())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    with pytest.raises(
        ValueError, match=r"Reconciler.__init__: wiring does not satisfy policy.*ResourceManager"
    ):
        Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.RECREATE)  # type: ignore


def test_constructor_recreate_with_manager_succeeds() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    # Should not raise
    Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.RECREATE)  # type: ignore


def test_constructor_rejects_no_wiring() -> None:
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    with pytest.raises(
        ValueError, match=r"Reconciler.__init__: wiring does not satisfy policy.*ExampleState"
    ):
        Reconciler(states, known_state_handler=None)  # type: ignore


def test_constructor_validates_each_unique_type() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class TypeA(DesiredState):
        id: int

    class TypeB(DesiredState):
        id: int

    states = [TypeA(id=1), TypeB(id=2)]
    with pytest.raises(
        ValueError, match=r"Reconciler.__init__: wiring does not satisfy policy.*TypeB"
    ):
        Reconciler(states, known_state_handler=None)  # type: ignore


def test_constructor_uses_mro_walk() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ParentState(DesiredState):
        id: int

    class ChildState(ParentState):
        id: int

    states = [ChildState(id=1)]
    # Should not raise - MRO walk finds ParentState's wiring
    Reconciler(states, known_state_handler=None)  # type: ignore


def test_constructor_mro_walk_with_recreate() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ParentState(DesiredState):
        id: int

    class ChildState(ParentState):
        id: int

    states = [ChildState(id=1)]
    # Should not raise - MRO walk finds ParentState's manager
    Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.RECREATE)  # type: ignore


def test_constructor_mro_walk_recreate_without_manager() -> None:
    @register_observed_state_handler(FakeObserver())
    class ParentState(DesiredState):
        id: int

    class ChildState(ParentState):
        id: int

    states = [ChildState(id=1)]
    with pytest.raises(
        ValueError, match=r"Reconciler.__init__: wiring does not satisfy policy.*ResourceManager"
    ):
        Reconciler(states, known_state_handler=None, drift_policy=DriftPolicy.RECREATE)  # type: ignore


def test_constructor_empty_iterable_accepted() -> None:
    # Should not raise - nothing to validate
    Reconciler([], known_state_handler=None, drift_policy=DriftPolicy.FLAG)  # type: ignore


def test_constructor_rejects_bare_desired_state() -> None:
    """Passing a bare DesiredState (no subclass, no wiring) should raise ValueError."""
    states = [DesiredState()]
    with pytest.raises(ValueError, match=r".*DesiredState.*"):
        Reconciler(states, known_state_handler=None)  # type: ignore
