"""Tests for AgentAPIClient — Perplexity API wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.agent_api import AgentAPIClient, AgentAPIResponse

FAKE_REQUEST = httpx.Request("POST", "https://api.perplexity.ai/chat/completions")

MOCK_PERPLEXITY_RESPONSE = {
    "choices": [
        {"message": {"content": '{"legal_name": "Dell Technologies", "domain": "dell.com"}'}}
    ],
    "citations": [
        "https://www.dell.com/about",
        "https://investors.delltechnologies.com",
    ],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 200,
    },
}


class TestAgentAPIClient:
    """AgentAPIClient — Perplexity API wrapper."""

    @pytest.fixture
    def client(self) -> AgentAPIClient:
        return AgentAPIClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_pro_search_returns_parsed_response(self, client: AgentAPIClient) -> None:
        mock_response = httpx.Response(
            status_code=200,
            json=MOCK_PERPLEXITY_RESPONSE,
            request=FAKE_REQUEST,
        )
        with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await client.research(
                system_prompt="You are a researcher.",
                user_prompt="Research dell.com",
                model="sonar-pro",
            )
            assert isinstance(result, AgentAPIResponse)
            assert '"Dell Technologies"' in result.content
            assert len(result.citations) == 2
            assert result.usage_input_tokens == 150
            assert result.usage_output_tokens == 200

    @pytest.mark.asyncio
    async def test_empty_choices_raises(self, client: AgentAPIClient) -> None:
        mock_response = httpx.Response(
            status_code=200,
            json={"choices": [], "citations": []},
            request=FAKE_REQUEST,
        )
        with (
            patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response),
            pytest.raises(ValueError, match="No choices"),
        ):
            await client.research(
                system_prompt="test",
                user_prompt="test",
                model="sonar-pro",
            )

    @pytest.mark.asyncio
    async def test_http_error_propagates(self, client: AgentAPIClient) -> None:
        mock_response = httpx.Response(status_code=429)
        mock_response.request = httpx.Request("POST", "https://api.perplexity.ai/chat/completions")
        with (
            patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await client.research(
                system_prompt="test",
                user_prompt="test",
                model="sonar-pro",
            )

    @pytest.mark.asyncio
    async def test_strips_markdown_code_fences(self, client: AgentAPIClient) -> None:
        fenced_response = {
            "choices": [{"message": {"content": '```json\n{"name": "Dell"}\n```'}}],
            "citations": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_response = httpx.Response(status_code=200, json=fenced_response, request=FAKE_REQUEST)
        with patch.object(client._http, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await client.research(
                system_prompt="test",
                user_prompt="test",
                model="sonar-pro",
            )
            assert "```" not in result.content
            assert '"Dell"' in result.content
