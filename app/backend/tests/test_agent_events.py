"""Tests for queued agent SSE events."""

from core.agent import AgentContext


def test_drain_events_returns_pending_events_once() -> None:
    """Draining preserves event order and clears the queue."""
    context = AgentContext()
    context.emit("status", {"message": "Searching locations"})
    context.emit("map", {"waypoints": [[52.52, 13.4]]})

    assert context.drain_events() == [
        {"event": "status", "data": {"message": "Searching locations"}},
        {"event": "map", "data": {"waypoints": [[52.52, 13.4]]}},
    ]
    assert context.drain_events() == []
