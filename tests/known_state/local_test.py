"""Tests for the LocalJSONKnownStateHandler."""

from pathlib import Path

import pytest

from pylibreconcile import LocalJSONKnownStateHandler


def test_set_and_get_value(tmp_path: Path) -> None:
    handler = LocalJSONKnownStateHandler(tmp_path / "state.json")
    handler.set_value("key1", "value1")
    assert handler.get_value("key1") == "value1"


def test_has_key(tmp_path: Path) -> None:
    handler = LocalJSONKnownStateHandler(tmp_path / "state.json")
    assert not handler.has_key("key1")
    handler.set_value("key1", "value1")
    assert handler.has_key("key1")


def test_get_all_keys(tmp_path: Path) -> None:
    handler = LocalJSONKnownStateHandler(tmp_path / "state.json")
    handler.set_value("a", "1")
    handler.set_value("b", "2")
    assert sorted(handler.get_all_keys()) == ["a", "b"]


def test_get_missing_key_raises(tmp_path: Path) -> None:
    handler = LocalJSONKnownStateHandler(tmp_path / "state.json")
    with pytest.raises(KeyError):
        handler.get_value("missing")


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    LocalJSONKnownStateHandler(path).set_value("key1", "value1")
    reloaded = LocalJSONKnownStateHandler(path)
    assert reloaded.get_value("key1") == "value1"
    assert reloaded.has_key("key1")


def test_nonexistent_file_is_empty(tmp_path: Path) -> None:
    handler = LocalJSONKnownStateHandler(tmp_path / "state.json")
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_load_coerces_values_to_str(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"a": 1, "b": true, "c": "keep"}')
    handler = LocalJSONKnownStateHandler(path)
    assert handler.get_value("a") == "1"
    assert handler.get_value("b") == "True"
    assert handler.get_value("c") == "keep"


def test_non_dict_json_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("[1, 2, 3]")
    handler = LocalJSONKnownStateHandler(path)
    assert handler.get_all_keys() == []
    assert not handler.has_key("any")


def test_overwrite_existing_value(tmp_path: Path) -> None:
    handler = LocalJSONKnownStateHandler(tmp_path / "state.json")
    handler.set_value("key1", "first")
    handler.set_value("key1", "second")
    assert handler.get_value("key1") == "second"
