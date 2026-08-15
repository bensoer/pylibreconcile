"""Tests for the AzureStorageKnownStateHandler."""

from unittest.mock import MagicMock, patch

import pytest

from pylibreconcile import AzureStorageKnownStateHandler

CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test"
CONTAINER_NAME = "container"


def _make_handler() -> tuple[AzureStorageKnownStateHandler, MagicMock]:
    container = MagicMock()
    with patch(
        "pylibreconcile.known_state.azure.ContainerClient.from_connection_string",
        return_value=container,
    ):
        handler = AzureStorageKnownStateHandler(CONNECTION_STRING, CONTAINER_NAME)
    return handler, container


def test_has_key() -> None:
    handler, container = _make_handler()
    container.get_blob_client.return_value.exists.return_value = True

    assert handler.has_key("blob1") is True
    container.get_blob_client.assert_called_with("blob1")


def test_has_key_missing() -> None:
    handler, container = _make_handler()
    container.get_blob_client.return_value.exists.return_value = False

    assert handler.has_key("blob1") is False


def test_get_all_keys() -> None:
    handler, container = _make_handler()
    container.list_blob_names.return_value = iter(["a", "b", "c"])

    assert handler.get_all_keys() == ["a", "b", "c"]


def test_get_value() -> None:
    handler, container = _make_handler()
    blob = container.get_blob_client.return_value
    blob.exists.return_value = True
    blob.download_blob.return_value.readall.return_value = "value1"

    assert handler.get_value("blob1") == "value1"


def test_get_missing_value_raises() -> None:
    handler, container = _make_handler()
    container.get_blob_client.return_value.exists.return_value = False

    with pytest.raises(KeyError):
        handler.get_value("missing")


def test_set_value() -> None:
    handler, container = _make_handler()
    blob = container.get_blob_client.return_value

    handler.set_value("blob1", "value1")
    blob.upload_blob.assert_called_once_with("value1", overwrite=True)
