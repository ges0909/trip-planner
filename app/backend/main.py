"""FastAPI backend for the Trip Planner web app."""

import json
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from agent import run_agent
from db import (
    add_message,
    create_session,
    get_chat_history,
    get_session,
    init_db,
    list_sessions,
    list_tours,
    update_session,
)
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from i18n import msg
from mcp_manager import MCPManager, build_server_configs
from sse_starlette.sse import EventSourceResponse
from steering import _detect_tour_type
from tour_storage import (
    get_tour_detail,
    get_tour_gpx,
    save_tour,
    sync_filesystem_to_db,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Module-level MCP manager instance, accessible to endpoints
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    """Get the MCP manager instance. Raises if not initialized."""
    if _mcp_manager is None:
        raise RuntimeError("MCPManager not initialized")
    return _mcp_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and MCP manager."""
    global _mcp_manager

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Sync existing tours from filesystem to DB
    synced = await sync_filesystem_to_db()
    if synced:
        logger.info("Synced %d tours from filesystem to database", synced)

    # Initialize MCP manager
    configs = build_server_configs()
    _mcp_manager = MCPManager(configs)
    await _mcp_manager.discover_all_tools()
    logger.info(
        "MCP manager initialized with %d tool declarations",
        len(await _mcp_manager.get_tool_declarations()),
    )

    yield

    # Shutdown
    await _mcp_manager.shutdown()
    _mcp_manager = None
    logger.info("MCP manager shut down")


app = FastAPI(title="Gerrit on Tour API", lifespan=lifespan)


@app.post("/api/chat")
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
                mcp=get_mcp_manager(),
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
                    import re

                    heading_match = re.search(r"^#{1,3}\s+(.+)$", assistant_response, re.MULTILINE)
                    if heading_match:
                        title = heading_match.group(1).strip()[:100]
                        await update_session(session_id, title=title)
                        logger.debug("Updated session title: %s", title)

    return EventSourceResponse(event_generator())


@app.get("/api/sessions")
async def get_sessions(limit: int = 50) -> list[dict[str, Any]]:
    """List recent sessions."""
    sessions = await list_sessions(limit=limit)
    return [
        {
            "id": s.id,
            "title": s.title,
            "language": s.language,
            "tour_type": s.tour_type,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """Get session details including messages."""
    session = await get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    messages = await get_chat_history(session_id)
    return {
        "id": session.id,
        "title": session.title,
        "language": session.language,
        "tour_type": session.tour_type,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": messages,
    }


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    # Check for API keys
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    return {
        "status": "ok",
        "providers": {
            "google": has_gemini,
            "openai": has_openai,
            "anthropic": has_anthropic,
        },
    }


# ============================================================================
# Tour Library Endpoints
# ============================================================================


@app.get("/api/tours")
async def get_tours(tour_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """List tours, optionally filtered by type.

    Query params:
        - tour_type: Filter by "bike" or "road" (optional)
        - limit: Max number of results (default: 100)
    """
    tours = await list_tours(tour_type=tour_type, limit=limit)
    return [
        {
            "id": t.id,
            "title": t.title,
            "tour_type": t.tour_type,
            "slug": t.slug,
            "summary": t.summary,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        }
        for t in tours
    ]


@app.get("/api/tours/{tour_type}/{slug}")
async def get_tour(tour_type: str, slug: str):
    """Get tour details including markdown content.

    Path params:
        - tour_type: "bike" or "road"
        - slug: Tour slug (URL-safe name)
    """
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)

    detail = await get_tour_detail(tour_type, slug)
    if not detail:
        return JSONResponse({"error": "Tour not found"}, status_code=404)

    return detail


@app.get("/api/tours/{tour_type}/{slug}/gpx")
async def get_tour_gpx_file(tour_type: str, slug: str):
    """Download GPX file for a tour.

    Returns the GPX file as plain text with appropriate content type.
    """
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)

    gpx = get_tour_gpx(tour_type, slug)
    if not gpx:
        return JSONResponse({"error": "GPX not found"}, status_code=404)

    return PlainTextResponse(
        content=gpx,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f'attachment; filename="{slug}.gpx"'},
    )


@app.get("/api/tours/{tour_type}/{slug}/maps/{filename}")
async def get_tour_map_image(tour_type: str, slug: str, filename: str):
    """Serve map images for a tour.

    Returns PNG images from the tour's maps/ directory.
    """
    from fastapi.responses import FileResponse

    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)

    # Security: only allow .png files, no path traversal
    if not filename.endswith(".png") or "/" in filename or "\\" in filename:
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    from tour_storage import get_tour_path

    map_path = get_tour_path(tour_type, slug) / "maps" / filename
    if not map_path.exists():
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return FileResponse(map_path, media_type="image/png")


@app.post("/api/tours")
async def create_tour_endpoint(request: Request):
    """Save a new tour.

    Request body:
        - markdown: Tour content (required)
        - tour_type: "bike" or "road" (required)
        - gpx: GPX content (optional)
        - session_id: Link to chat session (optional)
    """
    body: dict[str, Any] = await request.json()
    markdown = body.get("markdown")
    tour_type = body.get("tour_type")
    gpx = body.get("gpx")
    session_id = body.get("session_id")

    if not markdown:
        return JSONResponse({"error": "markdown is required"}, status_code=400)
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "tour_type must be 'bike' or 'road'"}, status_code=400)

    try:
        tour = await save_tour(
            markdown=markdown,
            tour_type=tour_type,
            gpx_content=gpx,
            session_id=session_id,
        )
        return {
            "id": tour.id,
            "title": tour.title,
            "tour_type": tour.tour_type,
            "slug": tour.slug,
            "created_at": tour.created_at.isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to save tour")
        return JSONResponse({"error": str(e)}, status_code=500)


# Serve frontend static files (production)
FRONTEND_DIST: Path = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving frontend from %s", FRONTEND_DIST)
