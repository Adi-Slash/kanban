from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_hello_endpoint_returns_expected_payload() -> None:
    response = client.get("/api/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "hello from fastapi"}
