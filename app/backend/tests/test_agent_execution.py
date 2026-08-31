"""Tests for core/agent.py execution loop and streaming logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from core.agent import run_agent
from pydantic_ai.messages import TextPart


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager providing sample tools."""
    manager = AsyncMock()
    manager.get_tool_declarations.return_value = [
        MagicMock(name="routing"),
        MagicMock(name="weather"),
    ]
    manager.call_tool.return_value = {
        "status": "ok",
        "route": [[52.5, 13.4], [52.4, 13.3]],
    }
    return manager


@pytest.mark.asyncio
async def test_run_agent_basic_text_response(mock_mcp_manager, monkeypatch):
    """Test run_agent yields model and tour events for simple text response."""

    class FakeModelResponse:
        def __init__(self):
            self.parts = [TextPart(content="# Berliner Park Tour\n\nSchöner Ausflug.")]

    class FakeModel:
        async def request(self, *args, **kwargs):
            return FakeModelResponse()

    monkeypatch.setattr("core.agent.get_model", lambda model_id=None: FakeModel())

    events = []
    async for event in run_agent(
        user_message="Schlage eine Park-Tour in Berlin vor",
        chat_history=[],
        mcp=mock_mcp_manager,
        language="de",
    ):
        events.append(event)

    event_types = [e["event"] for e in events]
    assert "model" in event_types
    assert "tour" in event_types
    assert "done" in event_types

    tour_event = next(e for e in events if e["event"] == "tour")
    assert "Berliner Park Tour" in tour_event["data"]["markdown"]
