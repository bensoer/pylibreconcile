from __future__ import annotations

from pylibreconcile import Change, ChangeType, DesiredState


def test_change_action_performed_defaults_to_true() -> None:
    change = Change(type=ChangeType.CREATE, desired_state=DesiredState())
    assert change.action_performed is True


def test_change_action_performed_explicit_false() -> None:
    change = Change(type=ChangeType.UPDATE, desired_state=DesiredState(), action_performed=False)
    assert change.action_performed is False


def test_change_action_performed_explicit_true() -> None:
    change = Change(type=ChangeType.DELETE, desired_state=DesiredState(), action_performed=True)
    assert change.action_performed is True
