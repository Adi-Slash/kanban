from app.ai import AIClientError


def test_ai_smoke_returns_response_shape(client) -> None:
    class _FakeClient:
        def smoke_check(self):
            return {"assistantMessage": "4", "model": "openai/gpt-oss-120b"}

    client.app.state.ai_client = _FakeClient()
    client.app.state.ai_client_error = None

    response = client.post("/api/ai/smoke")

    assert response.status_code == 200
    assert response.json() == {"assistantMessage": "4", "model": "openai/gpt-oss-120b"}


def test_ai_smoke_returns_503_when_key_not_configured(client) -> None:
    client.app.state.ai_client = None
    client.app.state.ai_client_error = AIClientError(
        "OpenRouter API key is not configured.", kind="config_error"
    )

    response = client.post("/api/ai/smoke")

    assert response.status_code == 503
    assert response.json()["detail"] == "OpenRouter API key is not configured."


def test_ai_smoke_returns_504_on_timeout(client) -> None:
    class _FakeClient:
        def smoke_check(self):
            raise AIClientError("OpenRouter request timed out. Please try again.", kind="timeout")

    client.app.state.ai_client = _FakeClient()
    client.app.state.ai_client_error = None

    response = client.post("/api/ai/smoke")

    assert response.status_code == 504
    assert response.json()["detail"] == "OpenRouter request timed out. Please try again."


def test_ai_smoke_returns_502_on_upstream_failure(client) -> None:
    class _FakeClient:
        def smoke_check(self):
            raise AIClientError("Could not reach OpenRouter service.", kind="upstream_error")

    client.app.state.ai_client = _FakeClient()
    client.app.state.ai_client_error = None

    response = client.post("/api/ai/smoke")

    assert response.status_code == 502
    assert response.json()["detail"] == "Could not reach OpenRouter service."
