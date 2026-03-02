import json
from io import BytesIO
from unittest.mock import patch
from urllib import error

import pytest

from app.ai import (
    AIClientError,
    OPENROUTER_MODEL,
    OPENROUTER_URL,
    OpenRouterClient,
    build_smoke_request_payload,
    parse_plan_response,
    parse_smoke_response,
)


def test_build_smoke_request_payload_uses_expected_model_and_prompt() -> None:
    payload = build_smoke_request_payload()

    assert payload["model"] == OPENROUTER_MODEL
    assert payload["messages"] == [{"role": "user", "content": "2+2"}]
    assert payload["temperature"] == 0


def test_parse_smoke_response_returns_assistant_message() -> None:
    result = parse_smoke_response(
        {"choices": [{"message": {"content": "The answer is 4."}}]}
    )

    assert result == "The answer is 4."


def test_parse_smoke_response_raises_for_missing_content() -> None:
    with pytest.raises(AIClientError):
        parse_smoke_response({"choices": []})


def test_openrouter_client_smoke_check_builds_post_request_and_parses_response() -> None:
    client = OpenRouterClient(api_key="test-key", timeout_seconds=3.0)
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"4"}}]}'

    def _fake_urlopen(req, timeout):
        captured["req"] = req
        captured["timeout"] = timeout
        return _FakeResponse()

    with patch("app.ai.request.urlopen", side_effect=_fake_urlopen):
        response = client.smoke_check()

    request_obj = captured["req"]
    assert request_obj.full_url == OPENROUTER_URL
    assert request_obj.get_method() == "POST"
    assert request_obj.get_header("Authorization") == "Bearer test-key"
    header_map = {key.lower(): value for key, value in request_obj.header_items()}
    assert header_map["content-type"] == "application/json"
    assert json.loads(request_obj.data.decode("utf-8")) == build_smoke_request_payload()
    assert captured["timeout"] == 3.0
    assert response == {"assistantMessage": "4", "model": OPENROUTER_MODEL}


def test_openrouter_client_smoke_check_raises_for_http_error() -> None:
    client = OpenRouterClient(api_key="test-key")

    with patch(
        "app.ai.request.urlopen",
        side_effect=error.HTTPError(
            url=OPENROUTER_URL,
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=BytesIO(b'{"error":"bad request"}'),
        ),
    ):
        with pytest.raises(AIClientError) as exc:
            client.smoke_check()

    assert "HTTP 400" in str(exc.value)


def test_parse_plan_response_returns_validated_plan() -> None:
    parsed = parse_plan_response(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"assistant_message":"Done.","operations":[{"type":"rename_column",'
                            '"column_id":"col-1","title":"Backlog Next"}]}'
                        )
                    }
                }
            ]
        }
    )
    assert parsed.assistant_message == "Done."
    assert len(parsed.operations) == 1
    assert parsed.operations[0].type == "rename_column"


def test_parse_plan_response_raises_for_invalid_json() -> None:
    with pytest.raises(AIClientError) as exc:
        parse_plan_response(
            {"choices": [{"message": {"content": "not-json"}}]}
        )
    assert "not valid JSON" in str(exc.value)
