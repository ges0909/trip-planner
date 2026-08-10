"""Chat endpoint — SSE streaming with agent."""

import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from core.agent import run_agent
from core.steering import _detect_tour_type
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from i18n import msg
from sse_starlette.sse import EventSourceResponse
from storage.db import (
    add_message,
    create_session,
    get_chat_history,
    get_session,
    update_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# Reference to MCP manager, set by main app
_get_mcp_manager: Any = None


def set_mcp_manager_getter(getter):
    """Set the function to get MCP manager instance."""
    global _get_mcp_manager
    _get_mcp_manager = getter


@router.post("/chat")
async def chat(request: Request) -> EventSourceResponse:
    """Handle chat messages and stream responses via SSE.

    Request body:
        - message: User message (required)
        - session_id: Session ID (optional, auto-generated if not provided)
        - language: Response language "de" or "en" (default: "de")

    SSE Events:
        - status: Progress updates (e.g., "Calculating route...")
        - map: Map data (route, waypoints, pois)
        - elevation: Elevation profile data
        - gpx: GPX file content for download
        - tour: Final tour markdown
        - error: Error message
        - done: Completion signal with iteration count
    """
    body: dict[str, Any] = await request.json()
    message: str = body.get("message", "")
    session_id: str | None = body.get("session_id")
    language: str = body.get("language", "de")

    if not message:
        return JSONResponse({"error": "No message provided"}, status_code=400)

    # Auto-generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info("Generated new session ID: %s", session_id)

    logger.info(
        "Chat request: session=%s, lang=%s, message=%s",
        session_id,
        language,
        message[:80],
    )

    # Ensure session exists in database
    session = await get_session(session_id)
    if not session:
        tour_type = _detect_tour_type(message)
        await create_session(
            session_id=session_id,
            language=language,
            tour_type=tour_type if tour_type != "general" else None,
        )
        logger.debug("Created new session: %s (tour_type: %s)", session_id, tour_type)

    # Get chat history from database
    chat_history = await get_chat_history(session_id)

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        lang = language if language in ("de", "en") else "de"

        # First, send session_id to client (for new sessions)
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session_id}, ensure_ascii=False),
        }

        assistant_response: str = ""
        has_error: bool = False

        try:
            async for event in run_agent(
                user_message=message,
                chat_history=chat_history,
                mcp=_get_mcp_manager(),
                language=lang,
            ):
                # Capture assistant response for history
                if event["event"] == "tour" and "markdown" in event["data"]:
                    assistant_response = event["data"]["markdown"]
                if event["event"] == "error":
                    has_error = True

                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"], ensure_ascii=False),
                }
        except Exception as e:
            logger.exception("Unhandled exception in event generator")
            has_error = True
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": msg("internal_error", lang, detail=str(e))},
                    ensure_ascii=False,
                ),
            }
            return

        # Save messages to database (only on success)
        if not has_error:
            await add_message(session_id, "user", message)
            if assistant_response:
                await add_message(session_id, "assistant", assistant_response)
                logger.info(
                    "Session %s: saved messages (history now %d)",
                    session_id,
                    len(chat_history) + 2,
                )

                # Update session title from first response heading
                if not session or not session.title:
                    heading_match = re.search(r"^#{1,3}\s+(.+)$", assistant_response, re.MULTILINE)
                    if heading_match:
                        title = heading_match.group(1).strip()[:100]
                        await update_session(session_id, title=title)
                        logger.debug("Updated session title: %s", title)

    return EventSourceResponse(event_generator())
