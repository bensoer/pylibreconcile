"""Tests for the KnownStateHandler protocol."""

from pathlib import Path

from pylibreconcile import (
    AWSS3KnownStateHandler,
    AzureStorageKnownStateHandler,
    KnownStateHandler,
    LocalJSONKnownStateHandler,
)


def test_local_handler_is_instance_of_protocol() -> None:
    """Verify a concrete handler satisfies the KnownStateHandler protocol."""

    handler = LocalJSONKnownStateHandler(Path("state.json"))
    assert isinstance(handler, KnownStateHandler)


def test_structural_conformance() -> None:
    """Verify a class with the required methods is recognized as a handler."""

    class Dummy:
        def has_key(self, key: str) -> bool:
            return False

        def get_all_keys(self) -> list[str]:
            return []

        def get_value(self, key: str) -> str:
            return ""

        def set_value(self, key: str, value: str) -> None:
            pass

    assert isinstance(Dummy(), KnownStateHandler)


def test_incomplete_class_is_not_handler() -> None:
    """Verify a class missing required methods is not recognized as a handler."""

    class Incomplete:
        def has_key(self, key: str) -> bool:
            return False

    assert not isinstance(Incomplete(), KnownStateHandler)


def test_cloud_handlers_are_subclasses() -> None:
    """Verify the cloud handlers are subclasses of KnownStateHandler."""

    assert issubclass(AzureStorageKnownStateHandler, KnownStateHandler)
    assert issubclass(AWSS3KnownStateHandler, KnownStateHandler)
    assert issubclass(LocalJSONKnownStateHandler, KnownStateHandler)
