"""Tests for the BoltDBKnownStateHandler."""

from pathlib import Path

import pytest

from pylibreconcile.known_state.boltdb import BoltDBKnownStateHandler
from pylibreconcile.known_state.protocol import KnownStateHandler


def test_set_and_get_value(tmp_path: Path) -> None:
    """Round-trip a value."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    handler.set_value("key1", "value1")
    assert handler.get_value("key1") == "value1"


def test_has_key(tmp_path: Path) -> None:
    """Pre/post set."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    assert not handler.has_key("key1")
    handler.set_value("key1", "value1")
    assert handler.has_key("key1")


def test_get_all_keys(tmp_path: Path) -> None:
    """Multiple keys, order independent."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    handler.set_value("a", "1")
    handler.set_value("b", "2")
    assert sorted(handler.get_all_keys()) == ["a", "b"]


def test_get_missing_key_raises(tmp_path: Path) -> None:
    """KeyError for missing key."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    with pytest.raises(KeyError):
        handler.get_value("missing")


def test_persists_across_instances(tmp_path: Path) -> None:
    """Open, set, reopen, read."""
    path = tmp_path / "state.bolt"
    BoltDBKnownStateHandler(path).set_value("key1", "value1")
    reloaded = BoltDBKnownStateHandler(path)
    assert reloaded.get_value("key1") == "value1"
    assert reloaded.has_key("key1")


def test_nonexistent_file_is_empty(tmp_path: Path) -> None:
    """Handler on a missing file works (boltdb creates it)."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_overwrite_existing_value(tmp_path: Path) -> None:
    """Set twice, last wins."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    handler.set_value("key1", "first")
    handler.set_value("key1", "second")
    assert handler.get_value("key1") == "second"


def test_unicode_keys_and_values(tmp_path: Path) -> None:
    """Non-ASCII strings round-trip."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    key = "🗝️"
    value = "🎉"
    handler.set_value(key, value)
    assert handler.get_value(key) == value
    assert handler.has_key(key)
    assert sorted(handler.get_all_keys()) == [key]


def test_satisfies_protocol(tmp_path: Path) -> None:
    """Handler satisfies the KnownStateHandler protocol."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    assert isinstance(handler, KnownStateHandler)


def test_close_releases_lock(tmp_path: Path) -> None:
    """After close, a fresh handler can open without hanging."""
    path = tmp_path / "state.bolt"
    handler = BoltDBKnownStateHandler(path)
    handler.set_value("key", "value")
    handler.close()
    reloaded = BoltDBKnownStateHandler(path)
    assert reloaded.get_value("key") == "value"


def test_default_bucket_name(tmp_path: Path) -> None:
    """Default bucket name works."""
    handler = BoltDBKnownStateHandler(tmp_path / "state.bolt")
    handler.set_value("key", "value")
    assert handler.get_value("key") == "value"


def test_custom_bucket_name(tmp_path: Path) -> None:
    """Custom bucket_name creates a separate bucket."""
    path = tmp_path / "state.bolt"
    handler1 = BoltDBKnownStateHandler(path, bucket_name="bucket1")
    handler1.set_value("only_in_bucket1", "value1")
    handler1.close()
    handler2 = BoltDBKnownStateHandler(path, bucket_name="bucket2")
    handler2.set_value("only_in_bucket2", "value2")
    handler2.close()
    handler1 = BoltDBKnownStateHandler(path, bucket_name="bucket1")
    handler2 = BoltDBKnownStateHandler(path, bucket_name="bucket2")
    assert handler1.get_value("only_in_bucket1") == "value1"
    assert handler2.get_value("only_in_bucket2") == "value2"
    assert handler1.get_all_keys() == ["only_in_bucket1"]
    assert handler2.get_all_keys() == ["only_in_bucket2"]
