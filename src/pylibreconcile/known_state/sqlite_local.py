from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .protocol import KnownStateHandler


class LocalSQLiteKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by a local SQLite database file.

    A single ``sqlite3.Connection`` is opened in ``__init__`` and held for
    the lifetime of the instance. The connection is created with
    ``check_same_thread=False`` so it may be used from any thread; every
    public method is further serialised with an internal ``threading.Lock``
    to prevent concurrent writes from racing inside the SQLite engine.
    Values are stored as raw ``TEXT`` (no encoding), since SQLite preserves
    arbitrary UTF-8 natively.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        # check_same_thread=False because we serialise via _lock.
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS known_state ("
            "    key   TEXT PRIMARY KEY,"
            "    value TEXT NOT NULL"
            ")"
        )
        self._connection.commit()

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
