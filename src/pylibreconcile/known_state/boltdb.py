from __future__ import annotations

import sys
from pathlib import Path

from boltdb import BoltDB

from .protocol import KnownStateHandler

_DEFAULT_BUCKET = "known_state"


class BoltDBKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by an embedded boltdb file.

    Platform: Linux only. The PyPI ``boltdb`` package uses
    ``fcntl.lockf`` for file locking; macOS and Windows are not
    supported by the upstream package; construction raises
    `RuntimeError` on non-Linux platforms.

    The handler stores all keys in a single named bucket inside the
    file. Concurrent readers are supported by boltdb; only one writer
    at a time (per-process file lock). The handler itself is
    thread-safe in the same sense.
    """

    def __init__(
        self,
        path: Path,
        *,
        bucket_name: str = _DEFAULT_BUCKET,
    ) -> None:
        if sys.platform != "linux":
            raise RuntimeError(
                "BoltDBKnownStateHandler is only supported on Linux; "
                f"detected platform: {sys.platform!r}"
            )
        self._path = path
        self._bucket_name = bucket_name
        self._db = BoltDB(str(path))
        with self._db.update() as tx:
            name = bucket_name.encode("utf-8")
            bucket = tx.bucket(name)
            if bucket is None:
                tx.create_bucket(name)

    def has_key(self, key: str) -> bool:
        with self._db.view() as tx:
            bucket = tx.bucket(self._bucket_name.encode("utf-8"))
            return bucket.get(key.encode("utf-8")) is not None

    def get_all_keys(self) -> list[str]:
        keys: list[str] = []
        with self._db.view() as tx:
            bucket = tx.bucket(self._bucket_name.encode("utf-8"))
            for raw_key, _ in bucket:
                keys.append(raw_key.decode("utf-8"))
        return keys

    def get_value(self, key: str) -> str:
        with self._db.view() as tx:
            bucket = tx.bucket(self._bucket_name.encode("utf-8"))
            raw: bytes | None = bucket.get(key.encode("utf-8"))
        if raw is None:
            raise KeyError(key)
        return raw.decode("utf-8")

    def set_value(self, key: str, value: str) -> None:
        with self._db.update() as tx:
            bucket = tx.bucket(self._bucket_name.encode("utf-8"))
            bucket.put(key.encode("utf-8"), value.encode("utf-8"))

    def close(self) -> None:
        self._db.close()
