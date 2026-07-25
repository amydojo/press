import pytest
from fastapi.testclient import TestClient

from press_generation_api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
