"""Session management endpoints."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from storage.db import get_chat_history, get_session, list_sessions

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
