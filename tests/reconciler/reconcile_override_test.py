from __future__ import annotations

import pytest

from pylibreconcile import DesiredState, DriftPolicy, ImportPolicy, Reconciler
from pylibreconcile.policy import Configuration
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


def test_reconcile_accepts_no_kwargs() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    # Should not raise
    reconciler.reconcile()


def test_reconcile_accepts_drift_policy_override() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    # Should not raise
    reconciler.reconcile(config=Configuration(drift_policy=DriftPolicy.FLAG))


def test_reconcile_accepts_import_policy_override() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    # Should not raise
    reconciler.reconcile(config=Configuration(import_policy=ImportPolicy.AUTO))


def test_reconcile_stores_effective_drift_policy() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    reconciler.reconcile(config=Configuration(drift_policy=DriftPolicy.RECREATE))
    assert reconciler._effective_config.drift_policy == DriftPolicy.RECREATE


def test_reconcile_stores_effective_import_policy() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    reconciler.reconcile(config=Configuration(import_policy=ImportPolicy.AUTO))
    assert reconciler._effective_config.import_policy == ImportPolicy.AUTO


def test_reconcile_override_none_falls_back_to_constructor() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(
        states,
        known_state_handler=None,  # type: ignore
        config=Configuration(drift_policy=DriftPolicy.ABSTAIN),
    )
    # Call with explicit None should fall back to constructor value
    reconciler.reconcile(config=None)
    assert reconciler._effective_config.drift_policy == DriftPolicy.ABSTAIN


def test_reconcile_recreate_override_validates_wiring() -> None:
    # Register observer-only (no manager)
    @register_observed_state_handler(FakeObserver())
    class ObserverOnlyState(DesiredState):
        id: int

    states = [ObserverOnlyState(id=1)]
    # Constructor uses FLAG (doesn't require manager)
    reconciler = Reconciler(
        states, known_state_handler=None, config=Configuration(drift_policy=DriftPolicy.FLAG)
    )  # type: ignore
    # Override to RECREATE should validate wiring and fail
    with pytest.raises(
        ValueError, match=r"Reconciler.reconcile\(drift_policy=RECREATE\):.*ResourceManager"
    ):
        reconciler.reconcile(config=Configuration(drift_policy=DriftPolicy.RECREATE))


def test_reconcile_recreate_override_with_manager_succeeds() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    # Constructor uses FLAG
    reconciler = Reconciler(
        states, known_state_handler=None, config=Configuration(drift_policy=DriftPolicy.FLAG)
    )  # type: ignore
    # Override to RECREATE should succeed since we have both observer and manager
    reconciler.reconcile(
        config=Configuration(drift_policy=DriftPolicy.RECREATE)
    )  # Should not raise


def test_reconcile_stub_returns_input_list() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    state1 = ExampleState(id=1)
    state2 = ExampleState(id=2)
    state3 = ExampleState(id=3)
    states = [state1, state2, state3]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    result = reconciler.reconcile()
    # Stub returns list(self._desired_states) - a new list with same elements
    assert len(result) == 3
    assert result[0] is state1
    assert result[1] is state2
    assert result[2] is state3


def test_reconcile_accepts_abstain_override() -> None:
    """reconcile() with drift_policy=ABSTAIN should succeed without error."""
    observer = FakeObserver()

    @register_observed_state_handler(observer)
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(
        states, known_state_handler=None, config=Configuration(drift_policy=DriftPolicy.FLAG)
    )  # type: ignore
    reconciler.reconcile(config=Configuration(drift_policy=DriftPolicy.ABSTAIN))


def test_reconcile_multiple_calls_with_different_overrides() -> None:
    """Call reconcile() twice with different drift_policy values, verify each stores correctly."""
    observer = FakeObserver()
    manager = FakeManager()

    @register_observed_state_handler(observer)
    @register_resource_manager(manager)
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(
        states, known_state_handler=None, config=Configuration(drift_policy=DriftPolicy.FLAG)
    )  # type: ignore

    reconciler.reconcile(config=Configuration(drift_policy=DriftPolicy.FLAG))
    assert reconciler._effective_config.drift_policy == DriftPolicy.FLAG

    reconciler.reconcile(config=Configuration(drift_policy=DriftPolicy.RECREATE))
    assert reconciler._effective_config.drift_policy == DriftPolicy.RECREATE

    reconciler.reconcile(config=None)
    assert reconciler._effective_config.drift_policy == DriftPolicy.FLAG
