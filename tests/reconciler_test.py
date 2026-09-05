"""Tests for the reconciler module."""

from pathlib import Path

from pylibreconcile import (
    DesiredState,
    LocalJSONKnownStateHandler,
    Reconciler,
    register_observed_state_handler,
    register_resource_manager,
)


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


def test_reconciler_iterable(tmp_path: Path) -> None:
    """Verify Reconciler works with an iterable of DesiredState."""

    @register_observed_state_handler(FakeObserver())
    @register_resource_manager(FakeManager())
    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler(
        desired_states=states,
        known_state_handler=LocalJSONKnownStateHandler(tmp_path / "state.json"),
    )
    result = reconciler.reconcile()
    assert len(result) == 2
