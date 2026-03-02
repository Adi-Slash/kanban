import os

import pytest

from app.ai import OPENROUTER_MODEL


@pytest.mark.integration
def test_openrouter_smoke_optional_integration(client) -> None:
    if os.getenv("RUN_OPENROUTER_INTEGRATION") != "1":
        pytest.skip("Set RUN_OPENROUTER_INTEGRATION=1 to enable OpenRouter integration test.")
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY is required for integration test.")

    response = client.post("/api/ai/smoke")
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == OPENROUTER_MODEL
    assert isinstance(payload["assistantMessage"], str)
    assert payload["assistantMessage"].strip()
