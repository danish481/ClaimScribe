import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("GEMINI_API_KEY", "")  # Force mock path

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
