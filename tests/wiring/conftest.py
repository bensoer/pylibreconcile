import pytest

from pylibreconcile import WiringContainer


@pytest.fixture(autouse=True)
def _wiring_container_reset() -> None:
    WiringContainer().clear()
