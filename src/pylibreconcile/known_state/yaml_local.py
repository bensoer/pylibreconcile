from __future__ import annotations

import base64
import threading
from pathlib import Path

import yaml

from .protocol import KnownStateHandler


class LocalYAMLKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by a local YAML file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        with self._path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file)
        if not isinstance(data, dict):
            return {}
        return {str(key): base64.b64decode(value).decode("utf-8") for key, value in data.items()}

    def _save(self, data: dict[str, str]) -> None:
        encoded = {
            key: base64.b64encode(value.encode("utf-8")).decode("ascii")
            for key, value in data.items()
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(encoded, file, default_flow_style=False, allow_unicode=True)

    def has_key(self, key: str) -> bool:
        with self._lock:
            return key in self._load()

    def get_all_keys(self) -> list[str]:
        with self._lock:
            return list(self._load().keys())

    def get_value(self, key: str) -> str:
        with self._lock:
            data = self._load()
            if key not in data:
                raise KeyError(key)
            return data[key]

    def set_value(self, key: str, value: str) -> None:
        with self._lock:
            data = self._load()
            data[key] = value
            self._save(data)
