"""Tests for the reconciler module."""

from pylibreconcile import DesiredState, Reconciler


def test_reconciler_iterable() -> None:
    """Verify Reconciler works with an iterable of DesiredState."""

    class ExampleState(DesiredState):
        id: int

    states = [ExampleState(id=1), ExampleState(id=2)]
    reconciler = Reconciler(states)
    result = reconciler.reconcile()
    assert len(result) == 2
