"""Tests for the AWSS3KnownStateHandler."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from pylibreconcile import AWSS3KnownStateHandler

BUCKET_NAME = "bucket"


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "mock"}}, "Operation")


def _make_handler(client: MagicMock) -> AWSS3KnownStateHandler:
    return AWSS3KnownStateHandler(BUCKET_NAME, client=client)


def test_has_key() -> None:
    client = MagicMock()
    handler = _make_handler(client)

    assert handler.has_key("key1") is True
    client.head_object.assert_called_once_with(Bucket=BUCKET_NAME, Key="key1")


def test_has_key_missing() -> None:
    client = MagicMock()
    client.head_object.side_effect = _client_error("404")
    handler = _make_handler(client)

    assert handler.has_key("key1") is False


def test_get_all_keys() -> None:
    client = MagicMock()
    paginator = client.get_paginator.return_value
    paginator.paginate.return_value = [
        {"Contents": [{"Key": "a"}, {"Key": "b"}]},
        {"Contents": [{"Key": "c"}]},
    ]
    handler = _make_handler(client)

    assert handler.get_all_keys() == ["a", "b", "c"]
    client.get_paginator.assert_called_once_with("list_objects_v2")


def test_get_value() -> None:
    client = MagicMock()
    body = MagicMock()
    body.read.return_value = b"value1"
    client.get_object.return_value = {"Body": body}
    handler = _make_handler(client)

    assert handler.get_value("key1") == "value1"
    client.get_object.assert_called_once_with(Bucket=BUCKET_NAME, Key="key1")


def test_get_missing_value_raises() -> None:
    client = MagicMock()
    client.get_object.side_effect = _client_error("NoSuchKey")
    handler = _make_handler(client)

    with pytest.raises(KeyError):
        handler.get_value("key1")


def test_set_value() -> None:
    client = MagicMock()
    handler = _make_handler(client)

    handler.set_value("key1", "value1")
    client.put_object.assert_called_once_with(Bucket=BUCKET_NAME, Key="key1", Body="value1")
