from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from weakref import WeakValueDictionary

from .protocol import KnownStateHandler


class SQLiteKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by a local SQLite database file.

    Lifecycle & singleton (D-SQL-9)
        At most one ``SQLiteKnownStateHandler`` instance is allowed per
        canonical database path. ``Path.resolve()`` canonicalises the
        constructor's ``path`` so equivalent spellings (e.g. ``./state.db``
        vs ``/abs/dir/state.db``) map to the same singleton slot. The
        slots are held in a class-level ``weakref.WeakValueDictionary``
        keyed by the resolved ``Path``; constructing a second instance
        whose resolved path already has a live handler raises
        ``RuntimeError`` (the message names the conflicting path and
        points at ``close()``). Because the dictionary holds only weak
        references, a handler whose last external reference is dropped is
        garbage-collected and its slot is freed automatically.

        The registry lock guarding the check-and-register sequence is held
        only during ``__init__`` and ``close()``; normal reads and writes
        are serialised by the instance's own ``threading.Lock`` and never
        contend with singleton bookkeeping.

    Open-if-exists
        If the database file already exists at ``path``, ``sqlite3.connect``
        opens it and ``CREATE TABLE IF NOT EXISTS`` is a no-op when the
        ``known_state`` table is already present, so a pre-existing file
        with data is picked up transparently. A brand-new path is created
        on first use. A path whose parent directory does not exist surfaces
        ``sqlite3``'s usual ``OperationalError``.

    Storage
        Values live in a single ``known_state`` table (``key TEXT PRIMARY
        KEY``, ``value TEXT NOT NULL``) and are stored verbatim as ``TEXT``
        — no base64 (unlike the JSON/YAML handlers). The connection is
        opened with ``check_same_thread=False`` and every public method
        acquires the per-instance ``threading.Lock`` before issuing a
        parameterised query, so writes are serialised at the application
        layer as the ``sqlite3`` docs require.

    Cleanup
        ``close()`` removes the instance from the singleton registry (only
        if it still owns the slot) and closes the connection. It is safe to
        call more than once; a second call is a no-op. The context-manager
        protocol delegates to ``close()``: ``__enter__`` returns ``self``
        and ``__exit__`` calls ``close()`` without suppressing exceptions
        raised inside the ``with`` block.
    """

    _instances: WeakValueDictionary[Path, SQLiteKnownStateHandler] = WeakValueDictionary()
    _registry_lock: threading.Lock = threading.Lock()

    def __init__(self, path: Path) -> None:
        if hasattr(self, "_connection"):
            return
        key = path.resolve()
        with SQLiteKnownStateHandler._registry_lock:
            if key in SQLiteKnownStateHandler._instances:
                raise RuntimeError(
                    "SQLiteKnownStateHandler already constructed for resolved "
                    f"path {key!r}; call close() (or use a 'with' block) on the "
                    "existing instance to release the singleton slot first."
                )
            connection = sqlite3.connect(path, check_same_thread=False)
            try:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS known_state ("
                    "    key   TEXT PRIMARY KEY,"
                    "    value TEXT NOT NULL"
                    ")"
                )
                connection.commit()
            except sqlite3.Error:
                connection.close()
                raise
            self._path = path
            self._resolved_path = key
            self._lock = threading.Lock()
            self._connection = connection
            SQLiteKnownStateHandler._instances[key] = self

    def has_key(self, key: str) -> bool:
        with self._lock:
            cursor = self._connection.execute("SELECT 1 FROM known_state WHERE key = ?", (key,))
            return cursor.fetchone() is not None

    def get_all_keys(self) -> list[str]:
        with self._lock:
            cursor = self._connection.execute("SELECT key FROM known_state")
            return [row[0] for row in cursor.fetchall()]

    def get_value(self, key: str) -> str:
        with self._lock:
            cursor = self._connection.execute("SELECT value FROM known_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(key)
            value: str = row[0]
            return value

    def set_value(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO known_state (key, value) VALUES (?, ?)",
                (key, value),
            )
            self._connection.commit()

    def close(self) -> None:
        """Release the singleton slot for this handler's path and close the connection.

        Removes ``self`` from the per-path registry only when it still owns
        the slot (defensive against a racing re-registration), then closes
        the underlying ``sqlite3`` connection. Calling this method more
        than once is a no-op: the registry lookup yields ``None`` and
        ``Connection.close()`` is itself idempotent.
        """
        with SQLiteKnownStateHandler._registry_lock:
            existing = SQLiteKnownStateHandler._instances.get(self._resolved_path)
            if existing is self:
                del SQLiteKnownStateHandler._instances[self._resolved_path]
        self._connection.close()

    def __enter__(self) -> SQLiteKnownStateHandler:
        """Enter the context-manager block, returning ``self``."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the context-manager block, closing the handler via ``close()``."""
        self.close()
