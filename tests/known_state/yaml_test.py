"""Tests for the LocalYAMLKnownStateHandler."""

import base64
from pathlib import Path

import pytest
import yaml

from pylibreconcile import LocalYAMLKnownStateHandler


def test_set_and_get_value(tmp_path: Path) -> None:
    handler = LocalYAMLKnownStateHandler(tmp_path / "state.yaml")
    handler.set_value("key1", "value1")
    assert handler.get_value("key1") == "value1"


def test_has_key(tmp_path: Path) -> None:
    handler = LocalYAMLKnownStateHandler(tmp_path / "state.yaml")
    assert not handler.has_key("key1")
    handler.set_value("key1", "value1")
    assert handler.has_key("key1")


def test_get_all_keys(tmp_path: Path) -> None:
    handler = LocalYAMLKnownStateHandler(tmp_path / "state.yaml")
    handler.set_value("a", "1")
    handler.set_value("b", "2")
    assert sorted(handler.get_all_keys()) == ["a", "b"]


def test_get_missing_key_raises(tmp_path: Path) -> None:
    handler = LocalYAMLKnownStateHandler(tmp_path / "state.yaml")
    with pytest.raises(KeyError):
        handler.get_value("missing")


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.yaml"
    LocalYAMLKnownStateHandler(path).set_value("key1", "value1")
    reloaded = LocalYAMLKnownStateHandler(path)
    assert reloaded.get_value("key1") == "value1"
    assert reloaded.has_key("key1")


def test_nonexistent_file_is_empty(tmp_path: Path) -> None:
    handler = LocalYAMLKnownStateHandler(tmp_path / "state.yaml")
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_values_are_base64_encoded_on_disk(tmp_path: Path) -> None:
    path = tmp_path / "state.yaml"
    handler = LocalYAMLKnownStateHandler(path)
    handler.set_value("key1", "hello\nworld\twith\0chars")
    raw = yaml.safe_load(path.read_text())
    assert raw["key1"] == base64.b64encode(b"hello\nworld\twith\0chars").decode()
    assert handler.get_value("key1") == "hello\nworld\twith\0chars"


def test_non_dict_yaml_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.yaml"
    path.write_text("[1, 2, 3]")
    handler = LocalYAMLKnownStateHandler(path)
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_overwrite_existing_value(tmp_path: Path) -> None:
    handler = LocalYAMLKnownStateHandler(tmp_path / "state.yaml")
    handler.set_value("key1", "first")
    handler.set_value("key1", "second")
    assert handler.get_value("key1") == "second"
