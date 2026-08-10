"""Tour library endpoints — CRUD and GPX access."""

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from storage.db import list_tours
from storage.tour_storage import (
    get_tour_detail,
    get_tour_gpx,
    get_tour_path,
    save_tour,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tours", tags=["tours"])


@router.get("")
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


@router.get("/{tour_type}/{slug}")
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


@router.get("/{tour_type}/{slug}/gpx")
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


@router.get("/{tour_type}/{slug}/maps/{filename}")
async def get_tour_map_image(tour_type: str, slug: str, filename: str):
    """Serve map images for a tour.

    Returns PNG images from the tour's maps/ directory.
    """
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)

    # Security: only allow .png files, no path traversal
    if not filename.endswith(".png") or "/" in filename or "\\" in filename:
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    map_path = get_tour_path(tour_type, slug) / "maps" / filename
    if not map_path.exists():
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return FileResponse(map_path, media_type="image/png")


@router.post("")
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
