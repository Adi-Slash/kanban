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


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """Client with the default seed user already logged in."""
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def board_id(auth_client: TestClient) -> str:
    """The default seed board ID."""
    boards = auth_client.get("/api/boards").json()
    assert len(boards) > 0
    return boards[0]["id"]
