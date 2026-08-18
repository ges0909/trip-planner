"""Session management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from storage.db import (
    create_session,
    get_chat_history,
    get_last_viewed_tour,
    get_session,
    list_sessions,
    update_last_viewed_tour,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions")
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


@router.get("/sessions/{session_id}")
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


@router.get("/sessions/{session_id}/last-viewed")
async def get_last_viewed_tour_endpoint(session_id: str):
    """Get the last viewed tour for a session."""
    logger.info(f"GET /sessions/{session_id}/last-viewed")
    session = await get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        return JSONResponse({"error": "Session not found"}, status_code=404)

    tour = await get_last_viewed_tour(session_id)
    logger.info(f"Last viewed tour for {session_id}: {tour}")
    if not tour:
        return {"tour": None}

    return {
        "tour": {
            "id": tour.id,
            "title": tour.title,
            "tour_type": tour.tour_type,
            "slug": tour.slug,
        }
    }


@router.put("/sessions/{session_id}/last-viewed")
async def set_last_viewed_tour_endpoint(session_id: str, tour_id: str = Body(..., embed=True)):
    """Set/update the last viewed tour for a session. Creates session if needed."""
    logger.info(f"PUT /sessions/{session_id}/last-viewed with tour_id={tour_id}")
    
    session = await get_session(session_id)
    if not session:
        logger.info(f"Creating new session: {session_id}")
        # Auto-create session if it doesn't exist
        session = await create_session(session_id=session_id, language="de")

    logger.info(f"Updating last_viewed_tour: session={session_id}, tour={tour_id}")
    success = await update_last_viewed_tour(session_id, tour_id)
    if not success:
        logger.error(f"Failed to update last_viewed_tour: {session_id} -> {tour_id}")
        return JSONResponse(
            {"error": "Failed to update last viewed tour"}, status_code=500
        )

    logger.info(f"✅ Successfully updated last_viewed_tour: {session_id} -> {tour_id}")
    return {"status": "ok"}
