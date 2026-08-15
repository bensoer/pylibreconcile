from __future__ import annotations

import json
from pathlib import Path

from .protocol import KnownStateHandler


class LocalJSONKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by a local JSON file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        with self._path.open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _save(self, data: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def has_key(self, key: str) -> bool:
        return key in self._load()

    def get_all_keys(self) -> list[str]:
        return list(self._load().keys())

    def get_value(self, key: str) -> str:
        data = self._load()
        if key not in data:
            raise KeyError(key)
        return data[key]

    def set_value(self, key: str, value: str) -> None:
        data = self._load()
        data[key] = value
        self._save(data)
