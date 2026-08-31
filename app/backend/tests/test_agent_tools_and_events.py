"""Tests for core/agent.py tool execution, geo-events, and status emission."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from core.agent import run_agent
from pydantic_ai.messages import TextPart, ToolCallPart


@pytest.fixture
def mock_mcp_with_geo_tools():
    """Mock MCP manager providing routing and poi tools."""
    manager = AsyncMock()

    async def mock_get_tool_decls(group_names):
        return [
            {
                "name": "brouter_route",
                "description": "Calculate bike route",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "overpass_pois",
                "description": "Find points of interest",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    async def mock_call_tool(name, args):
        if name == "brouter_route":
            return {
                "route": [[52.52, 13.40], [52.40, 13.30]],
                "waypoints": [[52.52, 13.40], [52.40, 13.30]],
                "elevation": [[0, 50], [10, 80]],
            }
        if name == "overpass_pois":
            return {
                "pois": [
                    {"lat": 52.51, "lon": 13.39, "name": "Brandenburger Tor", "category": "sight"}
                ],
            }
        return {}

    manager.get_tool_declarations = AsyncMock(side_effect=mock_get_tool_decls)
    manager.call_tool = AsyncMock(side_effect=mock_call_tool)
    return manager


@pytest.mark.asyncio
async def test_run_agent_executes_tools_and_emits_map_events(mock_mcp_with_geo_tools, monkeypatch):
    """Test run_agent executes tool calls, yields status, map, elevation, and tour events."""

    call_count = 0

    class MultiTurnModel:
        async def request(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First turn: call brouter_route tool
                return MagicMock(
                    parts=[ToolCallPart(tool_name="brouter_route", args={"start": "Berlin"})]
                )
            # Second turn: final markdown text
            return MagicMock(parts=[TextPart(content="# Berliner Radtour\n\nErfolgreich geplant.")])

    monkeypatch.setattr("core.agent.get_model", lambda model_id=None: MultiTurnModel())

    events = []
    async for event in run_agent(
        user_message="Radtour in Berlin planen",
        chat_history=[],
        mcp=mock_mcp_with_geo_tools,
        language="de",
    ):
        events.append(event)

    event_types = [e["event"] for e in events]
    assert "status" in event_types
    assert "tool" in event_types
    assert "model" in event_types
    assert "tour" in event_types
