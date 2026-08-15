"""Tests for the pylibreconcile package."""

from pylibreconcile import hello


def test_hello() -> None:
    """Verify the placeholder hello function returns the expected greeting."""
    assert hello() == "Hello from pylibreconcile!"
