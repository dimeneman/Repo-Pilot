"""LLM client and Gemini integration tests."""
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.rag.llm_client import LLMClient, LLMResponse


def test_llm_client_default_provider():
    """Verify LLM client defaults to Gemini."""
    client = LLMClient()
    assert client.provider == "gemini"
    assert "gemini" in client.model
    assert hasattr(client, "gemini_key")
    assert not hasattr(client, "openai_key")


@pytest.mark.asyncio
async def test_llm_client_fallback_without_key():
    """Verify LLM client returns deterministic fallback when no API key is provided."""
    client = LLMClient()
    client.gemini_key = ""

    response = await client.generate(
        prompt="Context Chunk 1: src/auth.py (Lines 10-25)\nExplain the login flow.",
        system_prompt="You are a helpful coding assistant.",
    )

    assert isinstance(response, LLMResponse)
    assert response.model == "local-repopilot-engine"
    assert "src/auth.py" in response.content
    assert "GEMINI_API_KEY" in response.content


@pytest.mark.asyncio
async def test_llm_client_gemini_call():
    """Verify Gemini API invocation logic when API key is provided."""
    client = LLMClient()
    client.gemini_key = "fake-gemini-key"

    mock_response = MagicMock()
    mock_response.text = "Authentication is handled in `src/auth.py` via JWT tokens."
    mock_usage = MagicMock()
    mock_usage.total_token_count = 42
    mock_response.usage_metadata = mock_usage

    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = mock_response

    with patch("google.generativeai.configure") as mock_configure, \
         patch("google.generativeai.GenerativeModel", return_value=mock_model_instance) as mock_model_cls:

        response = await client.generate(
            prompt="Where is auth?",
            system_prompt="You are a helpful code assistant.",
        )

        mock_configure.assert_called_once_with(api_key="fake-gemini-key")
        assert response.content == "Authentication is handled in `src/auth.py` via JWT tokens."
        assert "gemini" in response.model
        assert response.tokens_used == 42


@pytest.mark.asyncio
async def test_llm_client_gemini_failure_falls_back():
    """Verify resilient fallback when Gemini API raises an exception."""
    client = LLMClient()
    client.gemini_key = "fake-gemini-key"

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel", side_effect=RuntimeError("Quota exceeded")):

        response = await client.generate(
            prompt="Where is auth?",
        )

        assert isinstance(response, LLMResponse)
        assert response.model == "local-repopilot-engine"

