from __future__ import annotations

from pylibreconcile import DriftPolicy, ImportPolicy


def test_drift_policy_has_three_values() -> None:
    assert len(DriftPolicy) == 3


def test_drift_policy_values() -> None:
    assert set(DriftPolicy) == {DriftPolicy.FLAG, DriftPolicy.RECREATE, DriftPolicy.ABSTAIN}


def test_drift_policy_values_are_uppercase_strings() -> None:
    for policy in DriftPolicy:
        assert policy.value == policy.name


def test_import_policy_has_four_values() -> None:
    assert len(ImportPolicy) == 4


def test_import_policy_values() -> None:
    assert set(ImportPolicy) == {
        ImportPolicy.AUTO,
        ImportPolicy.WARN,
        ImportPolicy.REJECT,
        ImportPolicy.SKIP,
    }


def test_import_policy_values_are_uppercase_strings() -> None:
    for policy in ImportPolicy:
        assert policy.value == policy.name
