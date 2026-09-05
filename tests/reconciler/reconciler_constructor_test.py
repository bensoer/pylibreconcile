from __future__ import annotations

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


def test_constructor_stores_desired_states() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    assert len(reconciler._desired_states) == 2
    assert reconciler._desired_states[0] is states[0]
    assert reconciler._desired_states[1] is states[1]
    assert reconciler._config.drift_policy == DriftPolicy.FLAG
    assert reconciler._config.import_policy == ImportPolicy.WARN


def test_constructor_stores_known_state_handler() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    # We'll use a simple mock object for known_state_handler
    class MockKnownStateHandler:
        pass

    handler = MockKnownStateHandler()
    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=handler)
    assert reconciler._known_state_handler is handler
    assert reconciler._config.drift_policy == DriftPolicy.FLAG
    assert reconciler._config.import_policy == ImportPolicy.WARN


def test_constructor_default_drift_policy_is_flag() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    assert reconciler._config.drift_policy == DriftPolicy.FLAG
    assert reconciler._config.import_policy == ImportPolicy.WARN


def test_constructor_default_import_policy_is_warn() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(states, known_state_handler=None)  # type: ignore
    assert reconciler._config.drift_policy == DriftPolicy.FLAG
    assert reconciler._config.import_policy == ImportPolicy.WARN


def test_constructor_keeps_explicit_policy() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1)]
    reconciler = Reconciler(
        states,
        known_state_handler=None,  # type: ignore
        config=Configuration(
            drift_policy=DriftPolicy.ABSTAIN,
            import_policy=ImportPolicy.AUTO,
        ),
    )
    assert reconciler._config.drift_policy == DriftPolicy.ABSTAIN
    assert reconciler._config.import_policy == ImportPolicy.AUTO


def test_constructor_iterable_input_accepted() -> None:
    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler((s for s in states), known_state_handler=None)  # type: ignore
    assert len(reconciler._desired_states) == 2
    assert reconciler._desired_states[0] is states[0]
    assert reconciler._desired_states[1] is states[1]
    assert reconciler._config.drift_policy == DriftPolicy.FLAG
    assert reconciler._config.import_policy == ImportPolicy.WARN


def test_constructor_empty_iterable_accepted() -> None:
    # Should not raise - nothing to validate
    reconciler = Reconciler([], known_state_handler=None)  # type: ignore
    assert reconciler._config.drift_policy == DriftPolicy.FLAG
    assert reconciler._config.import_policy == ImportPolicy.WARN
