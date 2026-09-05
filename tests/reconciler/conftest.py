import pytest

from pylibreconcile.wiring.container import WiringContainer


@pytest.fixture(autouse=True)
def _wiring_container_reset() -> None:
    WiringContainer._instance = None
