from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pylibreconcile import Configuration, DriftPolicy, ImportPolicy


def test_configuration_with_defaults_resolves_none() -> None:
    """Configuration().with_defaults() should resolve None fields to defaults."""
    config = Configuration()
    defaulted = config.with_defaults()
    assert defaulted.drift_policy == DriftPolicy.FLAG
    assert defaulted.import_policy == ImportPolicy.WARN


def test_configuration_with_defaults_preserves_explicit() -> None:
    """Configuration with explicit values should preserve them when calling with_defaults()."""
    config = Configuration(drift_policy=DriftPolicy.RECREATE)
    defaulted = config.with_defaults()
    assert defaulted.drift_policy == DriftPolicy.RECREATE  # preserved
    assert defaulted.import_policy == ImportPolicy.WARN  # defaulted


def test_configuration_applied_over_uses_non_none() -> None:
    """applied_over should use non-None fields from the override config."""
    base = Configuration(drift_policy=DriftPolicy.FLAG, import_policy=ImportPolicy.WARN)
    override = Configuration(drift_policy=DriftPolicy.ABSTAIN)
    applied = override.applied_over(base)
    assert applied.drift_policy == DriftPolicy.ABSTAIN  # from override
    assert applied.import_policy == ImportPolicy.WARN  # from base


def test_configuration_applied_over_falls_back() -> None:
    """applied_over should fall back to base when override fields are None."""
    base = Configuration(drift_policy=DriftPolicy.FLAG, import_policy=ImportPolicy.WARN)
    override = Configuration()  # all None
    applied = override.applied_over(base)
    assert applied.drift_policy == DriftPolicy.FLAG  # from base
    assert applied.import_policy == ImportPolicy.WARN  # from base


def test_configuration_is_frozen() -> None:
    """Configuration should be frozen (immutable)."""
    config = Configuration()
    with pytest.raises(FrozenInstanceError):
        config.drift_policy = DriftPolicy.RECREATE  # type: ignore


def test_configuration_equality() -> None:
    """Two Configurations with the same fields should be equal."""
    config1 = Configuration(drift_policy=DriftPolicy.FLAG, import_policy=ImportPolicy.WARN)
    config2 = Configuration(drift_policy=DriftPolicy.FLAG, import_policy=ImportPolicy.WARN)
    assert config1 == config2

    # Different drift_policy
    config3 = Configuration(drift_policy=DriftPolicy.RECREATE, import_policy=ImportPolicy.WARN)
    assert config1 != config3

    # Different import_policy
    config4 = Configuration(drift_policy=DriftPolicy.FLAG, import_policy=ImportPolicy.AUTO)
    assert config1 != config4
