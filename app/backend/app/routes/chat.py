"""Chat endpoint — SSE streaming with agent."""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Any

import fastapi
from core.agent import run_agent
from core.context import _detect_tour_type
from core.mcp_manager import MCPManager
from core.title_generator import generate_session_title
from i18n import msg
from sse_starlette.sse import EventSourceResponse
from storage.db import (
    add_message,
    create_session,
    get_chat_history,
    get_session,
    save_session_artifacts,
    update_session,
)

from app.schemas import ChatRequest

logger = logging.getLogger(__name__)

router = fastapi.APIRouter(prefix="/api", tags=["chat"])


def format_sse_event(event_name: str, payload: dict[str, Any]) -> dict[str, str]:
    """Format an event dictionary for SSE transmission."""
    return {
        "event": event_name,
        "data": json.dumps(payload, ensure_ascii=False),
    }


def get_mcp_manager(request: fastapi.Request) -> MCPManager:
    """Dependency provider: get MCP manager from app state."""
    manager = getattr(request.app.state, "mcp_manager", None)
    if manager is None:
        raise RuntimeError("MCPManager is not initialized on app.state")
    return manager


@router.post("/chat")
async def chat(
    request: ChatRequest,
    mcp: Annotated[MCPManager, fastapi.Depends(get_mcp_manager)],
    x_client_token: Annotated[str | None, fastapi.Header()] = None,
) -> EventSourceResponse:
    """Handle chat messages and stream responses via SSE.

    Request body:
        - message: User message (required)
        - session_id: Session ID (optional, auto-generated if not provided)
        - language: Response language "de" or "en" (default: "de")

    SSE Events:
        - session: Session ID assignment
        - model: Individual model request
        - status: Progress updates (e.g., "Calculating route...")
        - tool: Individual MCP tool invocation
        - map: Map data (route, waypoints, pois)
        - elevation: Elevation profile data
        - gpx: GPX file content for download
        - tour: Final tour markdown
        - error: Error message
        - done: Completion signal with iteration count
    """
    message = request.message
    session_id = request.session_id
    language = request.language
    owner_token = x_client_token or "legacy"

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
    session = await get_session(session_id, owner_token)
    initial_title = message.strip()[:60]
    if not session:
        tour_type = _detect_tour_type(message)
        await create_session(
            session_id=session_id,
            title=initial_title,
            language=language,
            tour_type=tour_type if tour_type != "general" else None,
            owner_token=owner_token,
        )
        logger.debug(
            "Created new session: %s (tour_type: %s, title: %s)",
            session_id,
            tour_type,
            initial_title,
        )
    else:
        tour_type = session.tour_type or _detect_tour_type(message)
        if not session.title:
            await update_session(
                session_id,
                title=initial_title,
                tour_type=tour_type if tour_type in ("bike", "road") else None,
            )
        elif session.tour_type is None and tour_type in ("bike", "road"):
            await update_session(session_id, tour_type=tour_type)

    # Get chat history from database
    chat_history = await get_chat_history(session_id)

    async def event_generator() -> AsyncGenerator[dict[str, str]]:
        lang = language if language in ("de", "en") else "de"

        # First, send session_id to client (for new sessions)
        yield format_sse_event("session", {"session_id": session_id})

        assistant_response: str = ""
        has_error: bool = False
        gpx_content: str | None = None
        map_data: dict[str, list] = {"waypoints": [], "routes": [], "pois": []}
        elevation_data: list = []

        try:
            async for event in run_agent(
                user_message=message,
                chat_history=chat_history,
                mcp=mcp,
                language=lang,
            ):
                # Capture assistant response for history
                if event["event"] == "tour" and "markdown" in event["data"]:
                    assistant_response = event["data"]["markdown"]
                    # The client needs the detected type to offer a safe save action.
                    # General chat responses deliberately remain unsaveable.
                    event["data"]["tour_type"] = (
                        tour_type if tour_type in ("bike", "road") else None
                    )
                if event["event"] == "error":
                    has_error = True
                if event["event"] == "gpx":
                    gpx_content = event["data"].get("gpx")
                elif event["event"] == "map":
                    for key in map_data:
                        map_data[key].extend(event["data"].get(key, []))
                elif event["event"] == "elevation":
                    elevation_data = event["data"].get("profile", [])

                yield format_sse_event(event["event"], event["data"])
        except Exception as e:
            logger.exception("Unhandled exception in event generator")
            has_error = True
            yield format_sse_event("error", {"error": msg("internal_error", lang, detail=str(e))})
            return

        # Save messages to database and generate concise session title (only on success)
        if not has_error:
            await add_message(session_id, "user", message)
            if assistant_response:
                await add_message(session_id, "assistant", assistant_response)
                await save_session_artifacts(session_id, gpx_content, map_data, elevation_data)

                # Generate LLM concise title over updated chat history per turn
                full_history = await get_chat_history(session_id)
                concise_title = await generate_session_title(full_history, lang)
                await update_session(session_id, title=concise_title)
                logger.info("Session %s: updated LLM title: %s", session_id, concise_title)

                yield {
                    "event": "title",
                    "data": json.dumps(
                        {"session_id": session_id, "title": concise_title},
                        ensure_ascii=False,
                    ),
                }

    return EventSourceResponse(event_generator())
