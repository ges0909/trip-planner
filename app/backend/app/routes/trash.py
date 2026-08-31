"""Trash endpoints — soft delete and restore."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from storage.tour_storage import (
    delete_from_trash,
    empty_trash,
    is_valid_slug,
    is_valid_trash_name,
    list_trash,
    move_to_trash,
    restore_from_trash,
)

router = APIRouter(prefix="/api", tags=["trash"])


@router.delete("/tours/{tour_type}/{slug}")
async def delete_tour_endpoint(tour_type: str, slug: str):
    """Move a tour to trash.

    Tours are not permanently deleted but moved to trips/.trash/
    for potential recovery.
    """
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)
    if not is_valid_slug(slug):
        return JSONResponse({"error": "Invalid slug"}, status_code=400)

    success = await move_to_trash(tour_type, slug)
    if not success:
        return JSONResponse({"error": "Tour not found"}, status_code=404)

    return {"status": "moved_to_trash", "tour_type": tour_type, "slug": slug}


@router.get("/trash")
async def list_trash_endpoint():
    """List all tours in trash."""
    return list_trash()


@router.post("/trash/{tour_type}/{trash_name}/restore")
async def restore_tour_endpoint(tour_type: str, trash_name: str):
    """Restore a tour from trash."""
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)
    if not is_valid_trash_name(trash_name):
        return JSONResponse({"error": "Invalid trash_name"}, status_code=400)

    tour = await restore_from_trash(tour_type, trash_name)
    if not tour:
        return JSONResponse({"error": "Tour not found in trash"}, status_code=404)

    return {
        "status": "restored",
        "id": tour.id,
        "title": tour.title,
        "tour_type": tour.tour_type,
        "slug": tour.slug,
    }


@router.delete("/trash/{tour_type}/{trash_name}")
async def delete_from_trash_endpoint(tour_type: str, trash_name: str):
    """Permanently delete a tour from trash."""
    if tour_type not in ("bike", "road"):
        return JSONResponse({"error": "Invalid tour_type"}, status_code=400)
    if not is_valid_trash_name(trash_name):
        return JSONResponse({"error": "Invalid trash_name"}, status_code=400)

    success = await delete_from_trash(tour_type, trash_name)
    if not success:
        return JSONResponse({"error": "Tour not found in trash"}, status_code=404)

    return {"status": "permanently_deleted"}


@router.delete("/trash")
async def empty_trash_endpoint():
    """Permanently delete all tours in trash."""
    count = await empty_trash()
    return {"status": "emptied", "deleted_count": count}
