import json
import os
from pathlib import Path
from socket import timeout as SocketTimeout
from urllib import error, request

from pydantic import ValidationError as PydanticValidationError

from app.schemas import AIOperation, AIPlan


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"


class AIClientError(Exception):
    def __init__(self, message: str, kind: str = "upstream_error") -> None:
        super().__init__(message)
        self.kind = kind


def load_openrouter_api_key() -> str:
    env_value = os.getenv("OPENROUTER_API_KEY")
    if env_value:
        return env_value

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        raise AIClientError("OpenRouter API key is not configured.", kind="config_error")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("OPENROUTER_API_KEY="):
            continue
        _, value = line.split("=", 1)
        key = value.strip().strip('"').strip("'")
        if key:
            return key
        break

    raise AIClientError("OpenRouter API key is not configured.", kind="config_error")


def build_smoke_request_payload() -> dict:
    return {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": "2+2"}],
        "temperature": 0,
    }


def parse_smoke_response(payload: dict) -> str:
    try:
        message = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIClientError(
            "OpenRouter response did not include expected message content.",
            kind="upstream_error",
        ) from exc

    if not isinstance(message, str) or not message.strip():
        raise AIClientError(
            "OpenRouter response message content was empty.",
            kind="upstream_error",
        )
    return message


def _extract_assistant_content(payload: dict) -> str:
    try:
        message = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIClientError(
            "OpenRouter response did not include expected message content.",
            kind="upstream_error",
        ) from exc

    if isinstance(message, list):
        # Some providers return content parts. Keep only textual parts for MVP.
        chunks: list[str] = []
        for part in message:
            if isinstance(part, dict) and part.get("type") == "text":
                text_value = part.get("text")
                if isinstance(text_value, str):
                    chunks.append(text_value)
        message = "\n".join(chunks)

    if not isinstance(message, str) or not message.strip():
        raise AIClientError(
            "OpenRouter response message content was empty.",
            kind="upstream_error",
        )
    return message


def parse_plan_response(payload: dict) -> AIPlan:
    content = _extract_assistant_content(payload).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIClientError(
            "Model response was not valid JSON.",
            kind="model_output_error",
        ) from exc

    try:
        return AIPlan.model_validate(parsed)
    except PydanticValidationError as exc:
        raise AIClientError(
            f"Model response JSON did not match required schema: {exc}",
            kind="model_output_error",
        ) from exc


class OpenRouterClient:
    def __init__(self, api_key: str, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def smoke_check(self) -> dict[str, str]:
        payload = build_smoke_request_payload()
        parsed = self._post_chat(payload)
        assistant_message = parse_smoke_response(parsed)
        return {
            "assistantMessage": assistant_message,
            "model": OPENROUTER_MODEL,
        }

    def build_plan(
        self,
        board_snapshot: dict,
        user_message: str,
        conversation_history: list[dict[str, str]],
    ) -> tuple[str, list[AIOperation]]:
        prompt_payload = {
            "board": board_snapshot,
            "conversation_history": conversation_history,
            "user_message": user_message,
        }
        schema_instruction = {
            "assistant_message": "string",
            "operations": [
                {
                    "type": "create_card|update_card|move_card|delete_card|rename_column",
                    "column_id": "string|null",
                    "card_id": "string|null",
                    "title": "string|null",
                    "details": "string|null",
                    "before_card_id": "string|null",
                }
            ],
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that plans Kanban updates. "
                        "Return only a strict JSON object with keys assistant_message and operations. "
                        "Do not include markdown fences. "
                        "Only use operation types: create_card, update_card, move_card, delete_card, rename_column. "
                        "Use existing board ids as provided."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Schema:\n"
                        + json.dumps(schema_instruction)
                        + "\n\nInput:\n"
                        + json.dumps(prompt_payload)
                    ),
                },
            ],
        }
        parsed_response = self._post_chat(payload)
        plan = parse_plan_response(parsed_response)
        return plan.assistant_message, plan.operations

    def _post_chat(self, payload: dict) -> dict:
        req = request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="ignore")
            raise AIClientError(
                f"OpenRouter returned HTTP {exc.code}: {response_text or 'no response body'}",
                kind="upstream_error",
            ) from exc
        except SocketTimeout as exc:
            raise AIClientError(
                "OpenRouter request timed out. Please try again.", kind="timeout"
            ) from exc
        except error.URLError as exc:
            if isinstance(exc.reason, SocketTimeout):
                raise AIClientError(
                    "OpenRouter request timed out. Please try again.", kind="timeout"
                ) from exc
            raise AIClientError(
                "Could not reach OpenRouter service.", kind="upstream_error"
            ) from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise AIClientError(
                "OpenRouter returned invalid JSON.", kind="upstream_error"
            ) from exc
