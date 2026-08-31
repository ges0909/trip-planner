"""Tests for SSE Chat endpoint (/api/chat)."""

import asyncio
from unittest.mock import AsyncMock

import pytest
import storage.db as db
import storage.tour_storage as tour_storage
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def chat_client(tmp_path, monkeypatch):
    """Provide a TestClient with a fresh temporary SQLite DB and trips directory."""
    test_db = tmp_path / "test_chat.db"
    test_trips = tmp_path / "trips"
    test_trash = test_trips / ".trash"

    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(tour_storage, "TRIPS_DIR", test_trips)
    monkeypatch.setattr(tour_storage, "TRASH_DIR", test_trash)

    asyncio.run(db.init_db())

    mock_mcp = AsyncMock()
    mock_mcp.get_tool_declarations.return_value = []
    mock_mcp.call_tool.return_value = {}
    app.state.mcp_manager = mock_mcp

    with TestClient(app) as client:
        yield client


def test_chat_endpoint_streaming_events(chat_client, monkeypatch):
    """Test POST /api/chat streams SSE events correctly."""

    async def mock_run_agent(user_message, chat_history, mcp, language):
        yield {"event": "status", "data": {"message": "Berechne..."}}
        yield {"event": "tool", "data": {"name": "routing"}}
        yield {
            "event": "map",
            "data": {
                "waypoints": [[52.5, 13.4]],
                "routes": [[[52.5, 13.4], [52.4, 13.3]]],
                "pois": [{"lat": 52.5, "lon": 13.4, "name": "Start"}],
            },
        }
        yield {"event": "elevation", "data": {"profile": [[0, 100], [10, 150]]}}
        yield {"event": "gpx", "data": {"gpx": "<gpx></gpx>"}}
        yield {
            "event": "tour",
            "data": {
                "markdown": "# Wannsee Radtour\n\nTages-Radtour am Wannsee.",
                "tour_type": "bike",
            },
        }
        yield {"event": "done", "data": {"iterations": 1}}

    monkeypatch.setattr("app.routes.chat.run_agent", mock_run_agent)
    monkeypatch.setattr(
        "app.routes.chat.generate_session_title",
        AsyncMock(return_value="Radtour Wannsee · 45 km"),
    )

    response = chat_client.post(
        "/api/chat",
        json={
            "message": "Erstelle eine Radtour am Wannsee",
            "language": "de",
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    content = response.text
    assert "event: session" in content
    assert "event: status" in content
    assert "event: tool" in content
    assert "event: map" in content
    assert "event: elevation" in content
    assert "event: gpx" in content
    assert "event: tour" in content
    assert "event: title" in content
    assert "Radtour Wannsee · 45 km" in content


def test_chat_endpoint_error_handling(chat_client, monkeypatch):
    """Test POST /api/chat handles errors gracefully."""

    async def mock_failing_agent(user_message, chat_history, mcp, language):
        raise RuntimeError("LLM connection failed")
        yield {}  # unreachable generator yield

    monkeypatch.setattr("app.routes.chat.run_agent", mock_failing_agent)

    response = chat_client.post(
        "/api/chat",
        json={
            "message": "Fehlerhafte Anfrage",
            "language": "de",
        },
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "LLM connection failed" in response.text
