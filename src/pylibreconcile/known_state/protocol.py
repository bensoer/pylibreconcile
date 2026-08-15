from typing import Protocol, runtime_checkable


@runtime_checkable
class KnownStateHandler(Protocol):
    """Interface for reading and writing a known-state key/value store."""

    def has_key(self, key: str) -> bool:
        """Return True if ``key`` is present in the known state."""
        ...

    def get_all_keys(self) -> list[str]:
        """Return every key present in the known state."""
        ...

    def get_value(self, key: str) -> str:
        """Return the value stored under ``key``, raising ``KeyError`` if missing."""
        ...

    def set_value(self, key: str, value: str) -> None:
        """Store ``value`` under ``key``."""
        ...
