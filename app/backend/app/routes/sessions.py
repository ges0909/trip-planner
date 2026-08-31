"""Session management endpoints."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from storage.db import (
    create_session,
    delete_all_sessions,
    delete_session,
    get_chat_history,
    get_last_viewed_tour,
    get_session,
    get_session_artifacts,
    list_sessions,
    update_last_viewed_tour,
)

from app.schemas import LastViewedTourRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sessions"])


def owner_token(x_client_token: str | None = Header(default=None)) -> str:
    return x_client_token or "legacy"


@router.get("/sessions")
async def get_sessions(
    limit: int = 50, token: Annotated[str, Depends(owner_token)] = "legacy"
) -> list[dict[str, Any]]:
    """List recent sessions."""
    sessions = await list_sessions(limit=min(max(limit, 1), 100), owner_token=token)
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
async def get_session_detail(
    session_id: str, token: Annotated[str, Depends(owner_token)] = "legacy"
):
    """Get session details including messages."""
    session = await get_session(session_id, token)
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
        "artifacts": await get_session_artifacts(session_id),
    }


@router.get("/sessions/{session_id}/last-viewed")
async def get_last_viewed_tour_endpoint(
    session_id: str, token: Annotated[str, Depends(owner_token)] = "legacy"
):
    """Get the last viewed tour for a session."""
    session = await get_session(session_id, token)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    tour = await get_last_viewed_tour(session_id)
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
async def set_last_viewed_tour_endpoint(
    session_id: str,
    request: LastViewedTourRequest,
    token: Annotated[str, Depends(owner_token)] = "legacy",
):
    """Set/update the last viewed tour for a session. Creates session if needed."""
    session = await get_session(session_id, token)
    if not session:
        await create_session(session_id=session_id, language="de", owner_token=token)

    success = await update_last_viewed_tour(session_id, request.tour_id)
    if not success:
        return JSONResponse({"error": "Failed to update last viewed tour"}, status_code=500)

    return {"status": "ok"}


@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(
    session_id: str, token: Annotated[str, Depends(owner_token)] = "legacy"
):
    """Delete a single session."""
    success = await delete_session(session_id, owner_token=token)
    if not success:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return {"status": "ok"}


@router.delete("/sessions")
async def delete_all_sessions_endpoint(
    token: Annotated[str, Depends(owner_token)] = "legacy",
):
    """Delete all sessions for the current owner."""
    count = await delete_all_sessions(owner_token=token)
    return {"status": "ok", "deleted_count": count}
