from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "pm-test.db"


@pytest.fixture
def client(temp_db_path: Path) -> TestClient:
    app = create_app(db_path=temp_db_path)
    with TestClient(app) as test_client:
        yield test_client
