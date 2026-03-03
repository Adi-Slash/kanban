from app.ai import AIClientError
from app.schemas import AIOperation


def test_ai_smoke_returns_response_shape(auth_client) -> None:
    class _FakeClient:
        def smoke_check(self):
            return {"assistantMessage": "4", "model": "openai/gpt-oss-120b"}

    auth_client.app.state.ai_client = _FakeClient()
    auth_client.app.state.ai_client_error = None

    response = auth_client.post("/api/ai/smoke")
    assert response.status_code == 200
    assert response.json() == {"assistantMessage": "4", "model": "openai/gpt-oss-120b"}


def test_ai_smoke_returns_503_when_key_not_configured(auth_client) -> None:
    auth_client.app.state.ai_client = None
    auth_client.app.state.ai_client_error = AIClientError(
        "OpenRouter API key is not configured.", kind="config_error"
    )
    response = auth_client.post("/api/ai/smoke")
    assert response.status_code == 503


def test_ai_smoke_returns_504_on_timeout(auth_client) -> None:
    class _FakeClient:
        def smoke_check(self):
            raise AIClientError("OpenRouter request timed out.", kind="timeout")

    auth_client.app.state.ai_client = _FakeClient()
    auth_client.app.state.ai_client_error = None
    response = auth_client.post("/api/ai/smoke")
    assert response.status_code == 504


def test_ai_smoke_requires_auth(client) -> None:
    response = client.post("/api/ai/smoke")
    assert response.status_code == 401


def test_ai_chat_applies_operations_and_returns_updated_board(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    col_id = board["columns"][0]["id"]

    class _FakeClient:
        def build_plan(self, board_snapshot, user_message, conversation_history):
            return (
                "Added one card.",
                [
                    AIOperation(
                        type="create_card",
                        column_id=col_id,
                        title="AI created card",
                        details="from ai",
                    )
                ],
            )

    auth_client.app.state.ai_client = _FakeClient()
    auth_client.app.state.ai_client_error = None

    response = auth_client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={
            "message": "Please add one card",
            "history": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistantMessage"] == "Added one card."
    created_id = payload["board"]["columns"][0]["cardIds"][-1]
    assert payload["board"]["cards"][created_id]["title"] == "AI created card"


def test_ai_chat_rolls_back_on_failure(auth_client, board_id) -> None:
    board_before = auth_client.get(f"/api/boards/{board_id}").json()
    col_id = board_before["columns"][0]["id"]

    class _FakeClient:
        def build_plan(self, board_snapshot, user_message, conversation_history):
            return (
                "Attempted.",
                [
                    AIOperation(type="create_card", column_id=col_id, title="Should rollback"),
                    AIOperation(type="move_card", card_id="card-999999", column_id=col_id),
                ],
            )

    auth_client.app.state.ai_client = _FakeClient()
    auth_client.app.state.ai_client_error = None

    response = auth_client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={"message": "Do two", "history": []},
    )
    assert response.status_code == 400

    board_after = auth_client.get(f"/api/boards/{board_id}").json()
    assert len(board_after["cards"]) == len(board_before["cards"])


def test_ai_chat_returns_502_for_invalid_model_output(auth_client, board_id) -> None:
    class _FakeClient:
        def build_plan(self, board_snapshot, user_message, conversation_history):
            raise AIClientError("Model response was not valid JSON.", kind="model_output_error")

    auth_client.app.state.ai_client = _FakeClient()
    auth_client.app.state.ai_client_error = None

    response = auth_client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={"message": "hi", "history": []},
    )
    assert response.status_code == 502
