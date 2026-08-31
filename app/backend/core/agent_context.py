"""Context and state management for SSE event tracking during agent runs."""

from dataclasses import dataclass, field
from typing import Any

from i18n import Lang
from i18n import msg as i18n_msg

# Type alias for SSE events
type SSEEvent = dict[str, Any]


@dataclass
class AgentContext:
    """Context for tracking and emitting SSE events during agent execution."""

    language: str = "de"
    events: list[SSEEvent] = field(default_factory=list)
    gpx_content: str | None = None
    gpx_tracks: list[str] = field(default_factory=list)
    emitted_status_keys: set[str] = field(default_factory=set)

    def emit(self, event: str, data: dict[str, Any]) -> None:
        """Add an SSE event to the collection."""
        self.events.append({"event": event, "data": data})

    def drain_events(self) -> list[SSEEvent]:
        """Return pending SSE events and clear the event queue."""
        events = self.events
        self.events = []
        return events

    def emit_status(self, key: str) -> None:
        """Emit a status message if not already emitted."""
        if key not in self.emitted_status_keys:
            self.emitted_status_keys.add(key)
            lang = self.language if self.language in ("de", "en") else "de"
            self.emit("status", {"message": i18n_msg(key, lang)})

    def get_lang(self) -> Lang:
        """Get language as Lang type."""
        return self.language if self.language in ("de", "en") else "de"
