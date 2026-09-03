"""Tour library endpoints — CRUD and GPX access."""

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from storage.db import list_tours
from storage.tour_storage import (
    get_tour_detail,
    get_tour_geojson,
    get_tour_gpx,
    get_tour_path,
    is_valid_map_filename,
    is_valid_slug,
    rename_tour,
    save_tour,
)

from app.schemas import CreateTourRequest, RenameTourRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tours", tags=["tours"])


@router.get("")
async def get_tours(tour_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """List tours, optionally filtered by type.

    Query params:
        - tour_type: Filter by "bike" or "road" (optional)
        - limit: Max number of results (default: 100)
    """
    if tour_type is not None and tour_type not in ("bike", "road"):
        return []

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


def validate_tour_params(tour_type: str, slug: str) -> JSONResponse | None:
    """Validate tour_type and slug path parameters."""
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)
    if not is_valid_slug(slug):
        return JSONResponse({"error": "Invalid slug"}, status_code=400)
    return None


@router.get("/{tour_type}/{slug}")
async def get_tour(tour_type: str, slug: str):
    """Get tour details including markdown content.

    Path params:
        - tour_type: "bike" or "road"
        - slug: Tour slug (URL-safe name)
    """
    if err := validate_tour_params(tour_type, slug):
        return err

    detail = await get_tour_detail(tour_type, slug)
    if not detail:
        return JSONResponse({"error": "Tour not found"}, status_code=404)

    return detail


@router.get("/{tour_type}/{slug}/gpx")
async def get_tour_gpx_file(tour_type: str, slug: str):
    """Download GPX file for a tour.

    Returns the GPX file as plain text with appropriate content type.
    """
    if err := validate_tour_params(tour_type, slug):
        return err

    gpx = get_tour_gpx(tour_type, slug)
    if not gpx:
        return JSONResponse({"error": "GPX not found"}, status_code=404)

    return PlainTextResponse(
        content=gpx,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f'attachment; filename="{slug}.gpx"'},
    )


@router.get("/{tour_type}/{slug}/geojson")
async def get_tour_geojson_endpoint(tour_type: str, slug: str):
    """Get GeoJSON FeatureCollection representation of the tour.

    Returns track LineString and waypoints.
    """
    if err := validate_tour_params(tour_type, slug):
        return err

    geojson_data = get_tour_geojson(tour_type, slug)
    if not geojson_data:
        return JSONResponse({"error": "GeoJSON not found"}, status_code=404)

    return geojson_data


@router.get("/{tour_type}/{slug}/maps/{filename}")
async def get_tour_map_image(tour_type: str, slug: str, filename: str):
    """Serve map images for a tour.

    Returns PNG images from the tour's maps/ directory.
    """
    if err := validate_tour_params(tour_type, slug):
        return err
    if not is_valid_map_filename(filename):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    try:
        map_path = get_tour_path(tour_type, slug) / "maps" / filename
    except ValueError:
        return JSONResponse({"error": "Invalid path"}, status_code=400)

    if not map_path.exists():
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return FileResponse(map_path, media_type="image/png")


@router.post("")
async def create_tour_endpoint(request: CreateTourRequest):
    """Save a new tour.

    Request body:
        - markdown: Tour content (required)
        - tour_type: "bike" or "road" (required)
        - gpx: GPX content (optional)
        - session_id: Link to chat session (optional)
    """
    markdown = request.markdown
    tour_type = request.tour_type
    gpx = request.gpx
    session_id = request.session_id

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
    except Exception:
        logger.exception("Failed to save tour")
        return JSONResponse({"error": "Failed to save tour"}, status_code=500)


@router.post("/{tour_type}/{slug}/rename")
async def rename_tour_endpoint(tour_type: str, slug: str, request: RenameTourRequest):
    """Rename a tour title."""
    if err := validate_tour_params(tour_type, slug):
        return err

    tour = await rename_tour(tour_type, slug, request.title)
    if not tour:
        return JSONResponse({"error": "Tour not found or invalid title"}, status_code=404)

    return {
        "status": "renamed",
        "id": tour.id,
        "title": tour.title,
        "tour_type": tour.tour_type,
        "slug": tour.slug,
        "summary": tour.summary,
    }
