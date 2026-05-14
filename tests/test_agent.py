"""Tests for agent runner."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from puppycli.agent.runner import AgentRunner


@pytest.mark.asyncio
async def test_runner_requires_api_key(temp_config):
    """Runner should raise clear error when API key is missing."""
    temp_config.set("api_key", "")
    runner = AgentRunner(config=temp_config)

    with pytest.raises(ValueError, match="API key"):
        async for _ in runner.run_stream("hello"):
            pass


@pytest.mark.asyncio
async def test_runner_streams_tokens(temp_config):
    """Runner should yield tokens from stream events."""
    temp_config.set("api_key", "sk-test-123")
    runner = AgentRunner(config=temp_config)

    # Build an async generator for stream_events
    async def mock_stream_events():
        event = MagicMock()
        event.type = "raw_response_event"
        event.data.delta = "Hello "
        event.data.type = "response.output_text.delta"
        yield event
        event2 = MagicMock()
        event2.type = "raw_response_event"
        event2.data.delta = "World"
        event2.data.type = "response.output_text.delta"
        yield event2

    mock_result = MagicMock()
    mock_result.stream_events = mock_stream_events

    with (
        patch("puppycli.agent.runner.AsyncOpenAI"),
        patch("puppycli.agent.runner.set_default_openai_client"),
        patch("puppycli.agent.runner.Runner.run_streamed", return_value=mock_result),
    ):
        tokens = []
        async for token in runner.run_stream("Hi"):
            tokens.append(token)

        assert tokens == ["Hello ", "World"]


@pytest.mark.asyncio
async def test_runner_skips_non_delta_events(temp_config):
    """Runner should skip events that are not raw_response_event."""
    temp_config.set("api_key", "sk-test")
    runner = AgentRunner(config=temp_config)

    async def mock_stream_events():
        event = MagicMock()
        event.type = "other_event"
        yield event
        event2 = MagicMock()
        event2.type = "raw_response_event"
        event2.data.delta = "Only this"
        event2.data.type = "response.output_text.delta"
        yield event2

    mock_result = MagicMock()
    mock_result.stream_events = mock_stream_events

    with (
        patch("puppycli.agent.runner.AsyncOpenAI"),
        patch("puppycli.agent.runner.set_default_openai_client"),
        patch("puppycli.agent.runner.Runner.run_streamed", return_value=mock_result),
    ):
        tokens = []
        async for token in runner.run_stream("test"):
            tokens.append(token)

        assert tokens == ["Only this"]
