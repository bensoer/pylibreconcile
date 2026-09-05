"""Tests for the SQLiteKnownStateHandler."""

import sqlite3
import sys
from pathlib import Path

import pytest

from pylibreconcile import SQLiteKnownStateHandler


def test_set_and_get_value(tmp_path: Path) -> None:
    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
    handler.set_value("key1", "value1")
    assert handler.get_value("key1") == "value1"


def test_has_key(tmp_path: Path) -> None:
    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
    assert not handler.has_key("key1")
    handler.set_value("key1", "value1")
    assert handler.has_key("key1")


def test_get_all_keys(tmp_path: Path) -> None:
    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
    handler.set_value("a", "1")
    handler.set_value("b", "2")
    assert sorted(handler.get_all_keys()) == ["a", "b"]


def test_get_missing_key_raises(tmp_path: Path) -> None:
    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
    with pytest.raises(KeyError):
        handler.get_value("missing")


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    SQLiteKnownStateHandler(path).set_value("key1", "value1")
    reloaded = SQLiteKnownStateHandler(path)
    assert reloaded.get_value("key1") == "value1"
    assert reloaded.has_key("key1")


def test_nonexistent_file_is_empty(tmp_path: Path) -> None:
    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_schema_is_created_on_init(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    SQLiteKnownStateHandler(path)
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
    handler = SQLiteKnownStateHandler(path)
    original = "hello\nworld\twith\0chars"
    handler.set_value("key1", original)
    assert handler.get_value("key1") == original
    # Check on-disk storage is verbatim (not base64)
    with sqlite3.connect(path) as conn:
        cursor = conn.execute("SELECT value FROM known_state WHERE key = ?", ("key1",))
        stored = cursor.fetchone()[0]
        assert stored == original


def test_overwrite_existing_value(tmp_path: Path) -> None:
    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
    handler.set_value("key1", "first")
    handler.set_value("key1", "second")
    assert handler.get_value("key1") == "second"


def test_concurrent_writes_do_not_corrupt(tmp_path: Path) -> None:
    import concurrent.futures

    handler = SQLiteKnownStateHandler(tmp_path / "state.db")
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


def test_duplicate_path_raises(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    handler_a = SQLiteKnownStateHandler(path)
    with pytest.raises(RuntimeError) as excinfo:
        SQLiteKnownStateHandler(path)
    assert str(path.resolve()) in str(excinfo.value)
    assert "close()" in str(excinfo.value)
    handler_a.close()


def test_different_paths_create_independent_instances(tmp_path: Path) -> None:
    path_a = tmp_path / "state_a.db"
    path_b = tmp_path / "state_b.db"
    handler_a = SQLiteKnownStateHandler(path_a)
    handler_b = SQLiteKnownStateHandler(path_b)
    assert handler_a is not handler_b
    handler_a.set_value("key", "value_a")
    handler_b.set_value("key", "value_b")
    assert handler_a.get_value("key") == "value_a"
    assert handler_b.get_value("key") == "value_b"
    handler_a.close()
    handler_b.close()


def test_close_releases_singleton_slot(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    handler_a = SQLiteKnownStateHandler(path)
    handler_a.set_value("key", "value")
    handler_a.close()
    # Now we can create a new handler with the same path
    handler_b = SQLiteKnownStateHandler(path)
    assert handler_b.get_value("key") == "value"
    handler_b.close()


def test_context_manager_closes_on_exit(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    with SQLiteKnownStateHandler(path) as handler:
        handler.set_value("key", "value")
    # After the context manager, we can create a new handler
    handler_b = SQLiteKnownStateHandler(path)
    assert handler_b.get_value("key") == "value"
    handler_b.close()


def test_init_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    handler = SQLiteKnownStateHandler(path)
    # Calling __init__ again should be a no-op (early return)
    handler.__init__(path)  # should not raise
    # Verify the handler still works
    handler.set_value("key", "value")
    assert handler.get_value("key") == "value"


@pytest.mark.skipif(
    sys.platform == "win32", reason="Unix chmod(0o444) is not meaningful on Windows"
)
def test_init_raises_on_error(tmp_path: Path) -> None:
    # Make a read-only file to cause an error during table creation
    path = tmp_path / "state.db"
    path.touch()
    path.chmod(0o444)  # read-only
    with pytest.raises(sqlite3.Error):
        SQLiteKnownStateHandler(path)


def test_close_idempotent_and_registry(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    handler = SQLiteKnownStateHandler(path)
    # First close: should remove from registry
    handler.close()
    # After close, we should be able to create a new handler with the same path
    SQLiteKnownStateHandler(path)  # should not raise
    # Second close on the same handler: should not raise and should be a no-op
    handler.close()  # should not raise
