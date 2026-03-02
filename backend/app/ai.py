import json
import os
from pathlib import Path
from socket import timeout as SocketTimeout
from urllib import error, request


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


class OpenRouterClient:
    def __init__(self, api_key: str, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def smoke_check(self) -> dict[str, str]:
        payload = build_smoke_request_payload()
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
            parsed = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise AIClientError(
                "OpenRouter returned invalid JSON.", kind="upstream_error"
            ) from exc

        assistant_message = parse_smoke_response(parsed)
        return {
            "assistantMessage": assistant_message,
            "model": OPENROUTER_MODEL,
        }
