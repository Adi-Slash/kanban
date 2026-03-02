from app.ai import AIClientError
from app.schemas import AIOperation


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


def test_ai_chat_applies_operations_and_returns_updated_board(client) -> None:
    board = client.get("/api/board").json()
    source_column_id = board["columns"][0]["id"]

    class _FakeClient:
        def build_plan(self, board_snapshot, user_message, conversation_history):
            assert board_snapshot["columns"]
            assert user_message == "Please add one card"
            assert conversation_history == [{"role": "user", "content": "hello"}]
            return (
                "Added one card.",
                [
                    AIOperation(
                        type="create_card",
                        column_id=source_column_id,
                        title="AI created card",
                        details="from ai",
                    )
                ],
            )

    client.app.state.ai_client = _FakeClient()
    client.app.state.ai_client_error = None

    response = client.post(
        "/api/ai/chat",
        json={
            "message": "Please add one card",
            "history": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistantMessage"] == "Added one card."
    assert payload["operations"][0]["type"] == "create_card"
    created_id = payload["board"]["columns"][0]["cardIds"][-1]
    assert payload["board"]["cards"][created_id]["title"] == "AI created card"


def test_ai_chat_rolls_back_all_operations_on_failure(client) -> None:
    board_before = client.get("/api/board").json()
    source_column_id = board_before["columns"][0]["id"]

    class _FakeClient:
        def build_plan(self, board_snapshot, user_message, conversation_history):
            return (
                "Attempted updates.",
                [
                    AIOperation(
                        type="create_card",
                        column_id=source_column_id,
                        title="Should rollback",
                        details="temp",
                    ),
                    AIOperation(type="move_card", card_id="card-999999", column_id=source_column_id),
                ],
            )

    client.app.state.ai_client = _FakeClient()
    client.app.state.ai_client_error = None

    response = client.post("/api/ai/chat", json={"message": "Do two operations", "history": []})
    assert response.status_code == 400

    board_after = client.get("/api/board").json()
    assert board_after == board_before


def test_ai_chat_returns_502_for_invalid_model_output(client) -> None:
    class _FakeClient:
        def build_plan(self, board_snapshot, user_message, conversation_history):
            raise AIClientError("Model response was not valid JSON.", kind="model_output_error")

    client.app.state.ai_client = _FakeClient()
    client.app.state.ai_client_error = None

    response = client.post("/api/ai/chat", json={"message": "hi", "history": []})
    assert response.status_code == 502
