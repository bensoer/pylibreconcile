"""Tests for the LocalSQLiteKnownStateHandler."""

import sqlite3
from pathlib import Path

import pytest

from pylibreconcile import LocalSQLiteKnownStateHandler


def test_set_and_get_value(tmp_path: Path) -> None:
    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    handler.set_value("key1", "value1")
    assert handler.get_value("key1") == "value1"


def test_has_key(tmp_path: Path) -> None:
    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    assert not handler.has_key("key1")
    handler.set_value("key1", "value1")
    assert handler.has_key("key1")


def test_get_all_keys(tmp_path: Path) -> None:
    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    handler.set_value("a", "1")
    handler.set_value("b", "2")
    assert sorted(handler.get_all_keys()) == ["a", "b"]


def test_get_missing_key_raises(tmp_path: Path) -> None:
    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    with pytest.raises(KeyError):
        handler.get_value("missing")


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    LocalSQLiteKnownStateHandler(path).set_value("key1", "value1")
    reloaded = LocalSQLiteKnownStateHandler(path)
    assert reloaded.get_value("key1") == "value1"
    assert reloaded.has_key("key1")


def test_nonexistent_file_is_empty(tmp_path: Path) -> None:
    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_schema_is_created_on_init(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    LocalSQLiteKnownStateHandler(path)
    with sqlite3.connect(path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='known_state'"
        )
        assert cursor.fetchone() is not None
        cursor = conn.execute("PRAGMA table_info(known_state)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {"key": "TEXT", "value": "TEXT"}


def test_values_stored_verbatim(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    handler = LocalSQLiteKnownStateHandler(path)
    original = "hello\nworld\twith\0chars"
    handler.set_value("key1", original)
    assert handler.get_value("key1") == original
    # Check on-disk storage is verbatim (not base64)
    with sqlite3.connect(path) as conn:
        cursor = conn.execute("SELECT value FROM known_state WHERE key = ?", ("key1",))
        stored = cursor.fetchone()[0]
        assert stored == original


def test_overwrite_existing_value(tmp_path: Path) -> None:
    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    handler.set_value("key1", "first")
    handler.set_value("key1", "second")
    assert handler.get_value("key1") == "second"


def test_concurrent_writes_do_not_corrupt(tmp_path: Path) -> None:
    import concurrent.futures

    handler = LocalSQLiteKnownStateHandler(tmp_path / "state.db")
    num_keys = 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i in range(num_keys):
            key = f"key{i}"
            value = f"value{i}"
            futures.append(executor.submit(handler.set_value, key, value))
        # Wait for all to complete
        concurrent.futures.wait(futures)
        # Check for exceptions
        for f in futures:
            f.result()  # Will raise if there was an exception

    # After all writes, read back
    assert len(handler.get_all_keys()) == num_keys
    for i in range(num_keys):
        assert handler.get_value(f"key{i}") == f"value{i}"
