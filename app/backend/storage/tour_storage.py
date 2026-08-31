"""Tour storage module for saving tours to filesystem and SQLite index.

Tours are stored as:
    trips/{tour_type}/{slug}/
        ├── index.md      # Tour description (markdown)
        ├── gpx/          # GPX track files
        │   └── route.gpx
        └── maps/         # Map images (optional)

Deleted tours are moved to:
    trips/.trash/{tour_type}/{slug}/

SQLite is used as an index for fast listing and search.
"""

import contextlib
import logging
import re
import shutil
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT as DEFAULT_PROJECT_ROOT
from core.config import TRASH_DIR as DEFAULT_TRASH_DIR
from core.config import TRIPS_DIR as DEFAULT_TRIPS_DIR

from storage.db import Tour, create_tour, delete_tour_by_slug, generate_slug, get_tour_by_slug

logger = logging.getLogger(__name__)

# Project root and trips directory
PROJECT_ROOT = DEFAULT_PROJECT_ROOT
TRIPS_DIR = DEFAULT_TRIPS_DIR
TRASH_DIR = DEFAULT_TRASH_DIR

# Fixed namespace UUID for deterministic tour ID generation
TOUR_NAMESPACE = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRASH_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:_[0-9]{8}-[0-9]{6})?$")
MAP_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\.png$")


def is_valid_slug(slug: str) -> bool:
    """Validate that a slug is non-empty, max 100 chars, and contains only a-z, 0-9, hyphens."""
    if not slug or not isinstance(slug, str) or len(slug) > 100:
        return False
    return bool(SLUG_PATTERN.match(slug))


def is_valid_trash_name(name: str) -> bool:
    """Validate that a trash item name is safe and matches the expected format."""
    if not name or not isinstance(name, str) or len(name) > 150:
        return False
    return bool(TRASH_NAME_PATTERN.match(name))


def is_valid_map_filename(filename: str) -> bool:
    """Validate that an image filename is safe and ends with .png."""
    if not filename or not isinstance(filename, str) or len(filename) > 100:
        return False
    return bool(MAP_FILENAME_PATTERN.match(filename))


def _generate_tour_id(tour_type: str, slug: str) -> str:
    """Generate a stable, deterministic UUID for a tour based on tour_type and slug.

    This ensures the same tour always gets the same ID, even across server restarts.
    Uses uuid5 (SHA-1 based) for stability.
    """
    return str(uuid.uuid5(TOUR_NAMESPACE, f"{tour_type}:{slug}"))


def _extract_title_from_markdown(markdown: str) -> str:
    """Extract title from first heading in markdown."""
    match = re.search(r"^#{1,3}\s+(.+)$", markdown, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled Tour"


def _extract_summary_from_markdown(markdown: str) -> str | None:
    """Extract first paragraph as summary (after title)."""
    # Skip title and find first non-empty paragraph
    lines = markdown.split("\n")
    in_summary = False
    summary_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Skip title
        if stripped.startswith("#"):
            in_summary = True
            continue
        # Skip empty lines before summary
        if not stripped and not summary_lines:
            continue
        # End at next heading or after first paragraph
        if stripped.startswith("#") or (not stripped and summary_lines):
            break
        if in_summary:
            summary_lines.append(stripped)

    if summary_lines:
        summary = " ".join(summary_lines)
        # Truncate to 500 chars
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary
    return None


async def save_tour(
    markdown: str,
    tour_type: str,
    gpx_content: str | None = None,
    session_id: str | None = None,
    slug: str | None = None,
) -> Tour:
    """Save a tour to filesystem and index in SQLite.

    Args:
        markdown: Tour description in markdown format.
        tour_type: Either "bike" or "road".
        gpx_content: Optional GPX track content.
        session_id: Optional session ID to link the tour to.
        slug: Optional custom slug. Auto-generated from title if not provided.

    Returns:
        The created Tour object.

    Raises:
        ValueError: If tour_type is not "bike" or "road".
    """
    if tour_type not in ("bike", "road"):
        raise ValueError(f"Invalid tour_type: {tour_type}. Must be 'bike' or 'road'.")

    # Extract title and summary
    title = _extract_title_from_markdown(markdown)
    summary = _extract_summary_from_markdown(markdown)

    # Generate slug if not provided
    if not slug:
        slug = generate_slug(title)

    # Check if slug exists, append number if needed
    existing = await get_tour_by_slug(slug)
    if existing:
        base_slug = slug
        counter = 2
        while existing:
            slug = f"{base_slug}-{counter}"
            existing = await get_tour_by_slug(slug)
            counter += 1

    # Create directory structure
    tour_dir = TRIPS_DIR / tour_type / slug
    tour_dir_created = False
    try:
        tour_dir.mkdir(parents=True, exist_ok=True)
        tour_dir_created = True

        # Write index.md
        index_path = tour_dir / "index.md"
        index_path.write_text(markdown, encoding="utf-8")
        logger.info("Saved tour markdown to %s", index_path)

        # Write GPX if provided
        if gpx_content:
            gpx_dir = tour_dir / "gpx"
            gpx_dir.mkdir(exist_ok=True)
            gpx_path = gpx_dir / "route.gpx"
            gpx_path.write_text(gpx_content, encoding="utf-8")
            logger.info("Saved GPX to %s", gpx_path)

        # Create maps directory (for future use)
        maps_dir = tour_dir / "maps"
        maps_dir.mkdir(exist_ok=True)

        # Index in SQLite using deterministic ID
        tour_id = _generate_tour_id(tour_type, slug)
        tour = await create_tour(
            tour_id=tour_id,
            title=title,
            tour_type=tour_type,
            slug=slug,
            session_id=session_id,
            summary=summary,
        )
        logger.info("Created tour: %s (slug: %s, type: %s)", title, slug, tour_type)
        return tour
    except Exception:
        # Atomic rollback: clean up partially written tour directory
        if tour_dir_created and tour_dir.exists():
            shutil.rmtree(tour_dir, ignore_errors=True)
            logger.warning("Rolled back partially saved tour at %s due to error", tour_dir)
        raise


def get_tour_path(tour_type: str, slug: str) -> Path:
    """Get the filesystem path for a tour."""
    if tour_type not in ("bike", "road") or not is_valid_slug(slug):
        raise ValueError(f"Invalid tour_type '{tour_type}' or slug '{slug}'")
    return TRIPS_DIR / tour_type / slug


def get_tour_markdown(tour_type: str, slug: str) -> str | None:
    """Read tour markdown from filesystem."""
    path = get_tour_path(tour_type, slug) / "index.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def get_tour_gpx(tour_type: str, slug: str) -> str | None:
    """Read tour GPX from filesystem.

    For tours with multiple GPX files, returns them combined.

    Looks for GPX files in this order:
    1. gpx/route.gpx (standard name for single-file tours)
    2. gpx/{slug}.gpx (named after tour)
    3. All .gpx files in gpx/ directory (combined for multi-day trips)
    """
    gpx_dir = get_tour_path(tour_type, slug) / "gpx"
    if not gpx_dir.exists():
        return None

    # Try standard name first
    route_gpx = gpx_dir / "route.gpx"
    if route_gpx.exists():
        return route_gpx.read_text(encoding="utf-8")

    # Try slug-named file
    slug_gpx = gpx_dir / f"{slug}.gpx"
    if slug_gpx.exists():
        return slug_gpx.read_text(encoding="utf-8")

    # Multiple GPX files: combine them into one
    gpx_files = sorted(gpx_dir.glob("*.gpx"))
    if not gpx_files:
        return None

    if len(gpx_files) == 1:
        return gpx_files[0].read_text(encoding="utf-8")

    # Combine multiple GPX files into one
    return _combine_gpx_files(gpx_files)


def _combine_gpx_files(gpx_files: list[Path]) -> str:
    """Combine multiple GPX files into a single GPX with multiple tracks.

    If an index.md exists in the parent directory, uses the order from the
    markdown headings (### Tag N · ...) to sort the tracks.
    """
    # Try to get order from index.md
    tour_dir = gpx_files[0].parent.parent
    index_md = tour_dir / "index.md"
    ordered_files = _order_gpx_by_markdown(gpx_files, index_md)

    # GPX namespace
    gpx_ns = "http://www.topografix.com/GPX/1/1"
    ET.register_namespace("", gpx_ns)

    # Create root GPX element (xmlns added automatically by register_namespace)
    root = ET.Element(
        "gpx",
        {
            "version": "1.1",
            "creator": "Tour Pilot",
        },
    )

    for gpx_file in ordered_files:
        try:
            tree = ET.parse(gpx_file)
            file_root = tree.getroot()

            # Extract tracks from this file (handle namespace)
            tracks = file_root.findall(f"{{{gpx_ns}}}trk")

            for trk in tracks:
                # Add track name from filename if not present
                name_elem = trk.find(f"{{{gpx_ns}}}name")
                if name_elem is None:
                    name_elem = ET.SubElement(trk, f"{{{gpx_ns}}}name")
                    name_elem.text = gpx_file.stem.replace("-", " → ")
                root.append(trk)
        except ET.ParseError:
            logger.warning("Failed to parse GPX file: %s", gpx_file)
            continue

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _order_gpx_by_markdown(gpx_files: list[Path], index_md: Path) -> list[Path]:
    """Order GPX files based on tag/day order in index.md.

    Looks for patterns like:
    - ### Tag 1 · ... · Bilbao → Bakio  -> bilbao-bakio.gpx
    - ![Tag 1: Bilbao → Bakio](maps/tag-01-bilbao-bakio.png)
    """
    if not index_md.exists():
        return sorted(gpx_files)

    content = index_md.read_text(encoding="utf-8")

    # Build a mapping of GPX filename stems to files
    stem_to_file = {f.stem.lower(): f for f in gpx_files}

    # Extract order from markdown using map image references (most reliable)
    # Pattern: maps/tag-NN-start-end.png
    map_pattern = re.compile(r"maps/tag-(\d+)-([^.)]+)\.png", re.IGNORECASE)

    ordered: list[tuple[int, Path]] = []
    used_stems: set[str] = set()

    for match in map_pattern.finditer(content):
        tag_num = int(match.group(1))
        route_slug = match.group(2).lower()  # e.g., "bilbao-bakio"

        if route_slug in stem_to_file and route_slug not in used_stems:
            ordered.append((tag_num, stem_to_file[route_slug]))
            used_stems.add(route_slug)

    # Sort by tag number
    ordered.sort(key=lambda x: x[0])

    # Add any remaining GPX files not matched (sorted alphabetically)
    result = [f for _, f in ordered]
    for f in sorted(gpx_files):
        if f.stem.lower() not in used_stems:
            result.append(f)

    return result


def has_tour_gpx(tour_type: str, slug: str) -> bool:
    """Check if tour has any GPX file."""
    gpx_dir = get_tour_path(tour_type, slug) / "gpx"
    if not gpx_dir.exists():
        return False
    return any(gpx_dir.glob("*.gpx"))


def tour_exists(tour_type: str, slug: str) -> bool:
    """Check if a tour exists on the filesystem."""
    return (get_tour_path(tour_type, slug) / "index.md").exists()


async def get_tour_detail(tour_type: str, slug: str) -> dict[str, Any] | None:
    """Get full tour details including markdown and GPX availability.

    Returns a dict with:
        - id, title, tour_type, slug, summary, created_at, updated_at (from DB)
        - markdown (from filesystem, with rewritten image URLs)
        - has_gpx (boolean)
    """
    from storage.db import get_tour_by_slug

    tour = await get_tour_by_slug(slug)
    if not tour or tour.tour_type != tour_type:
        return None

    markdown = get_tour_markdown(tour_type, slug)

    # Rewrite image URLs to use the API endpoint
    # maps/tag-01-bilbao-bakio.png → /api/tours/road/nordspanien/maps/tag-01-bilbao-bakio.png
    if markdown:
        markdown = re.sub(
            r"\(maps/([^)]+\.png)\)",
            rf"(/api/tours/{tour_type}/{slug}/maps/\1)",
            markdown,
        )

    gpx_content = get_tour_gpx(tour_type, slug)
    from core.geo_events import extract_tour_metrics

    metrics = extract_tour_metrics(gpx_content, markdown)

    return {
        "id": tour.id,
        "title": tour.title,
        "tour_type": tour.tour_type,
        "slug": tour.slug,
        "summary": tour.summary,
        "created_at": tour.created_at.isoformat(),
        "updated_at": tour.updated_at.isoformat(),
        "markdown": markdown,
        "has_gpx": bool(gpx_content),
        "metrics": metrics,
    }


async def sync_filesystem_to_db() -> int:
    """Scan trips/ directory and add missing tours to SQLite index.

    This is useful for indexing tours created outside the web app (e.g., via Kiro).

    Returns:
        Number of tours added.
    """
    added = 0

    for tour_type in ("bike", "road"):
        type_dir = TRIPS_DIR / tour_type
        if not type_dir.exists():
            continue

        for tour_dir in type_dir.iterdir():
            if not tour_dir.is_dir():
                continue

            slug = tour_dir.name
            index_path = tour_dir / "index.md"

            if not index_path.exists():
                continue

            # Check if already indexed
            existing = await get_tour_by_slug(slug)
            if existing:
                continue

            # Read and index
            markdown = index_path.read_text(encoding="utf-8")
            title = _extract_title_from_markdown(markdown)
            summary = _extract_summary_from_markdown(markdown)

            tour_id = _generate_tour_id(tour_type, slug)
            await create_tour(
                tour_id=tour_id,
                title=title,
                tour_type=tour_type,
                slug=slug,
                summary=summary,
            )
            added += 1
            logger.info("Indexed existing tour: %s/%s", tour_type, slug)

    return added


async def move_to_trash(tour_type: str, slug: str) -> bool:
    """Move a tour to the trash folder.

    Instead of deleting, moves the tour directory to trips/.trash/
    for potential recovery.

    Returns:
        True if successfully moved, False if tour not found.
    """
    if tour_type not in ("bike", "road") or not is_valid_slug(slug):
        return False

    try:
        tour_dir = get_tour_path(tour_type, slug)
    except ValueError:
        return False

    if not tour_dir.exists():
        return False

    # Create trash directory structure
    trash_type_dir = TRASH_DIR / tour_type
    trash_type_dir.mkdir(parents=True, exist_ok=True)

    # Add timestamp to avoid conflicts with previously deleted tours
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    trash_dest = trash_type_dir / f"{slug}_{timestamp}"

    # Move to trash
    shutil.move(str(tour_dir), str(trash_dest))
    logger.info("Moved tour to trash: %s -> %s", tour_dir, trash_dest)

    # Remove from database
    await delete_tour_by_slug(slug)

    return True


async def restore_from_trash(tour_type: str, trash_name: str) -> Tour | None:
    """Restore a tour from the trash folder.

    Args:
        tour_type: "bike" or "road"
        trash_name: The name in trash (e.g., "my-tour_20240809-143022")

    Returns:
        Restored Tour object or None if not found.
    """
    if tour_type not in ("bike", "road") or not is_valid_trash_name(trash_name):
        return None

    trash_path = TRASH_DIR / tour_type / trash_name
    if not trash_path.exists():
        return None

    # Validate before moving so a malformed trash entry remains recoverable.
    index_path = trash_path / "index.md"
    if not index_path.exists():
        logger.warning("Cannot restore trash entry without index.md: %s", trash_path)
        return None

    # Extract original slug (before timestamp)
    original_slug = trash_name.rsplit("_", 1)[0]

    # Check if slug is available, or generate new one
    existing = await get_tour_by_slug(original_slug)
    if existing:
        # Slug taken, append number
        base_slug = original_slug
        counter = 2
        while existing:
            original_slug = f"{base_slug}-{counter}"
            existing = await get_tour_by_slug(original_slug)
            counter += 1

    # Move back to trips directory
    dest_dir = TRIPS_DIR / tour_type / original_slug
    shutil.move(str(trash_path), str(dest_dir))
    logger.info("Restored tour from trash: %s -> %s", trash_path, dest_dir)

    # Re-index in database
    index_path = dest_dir / "index.md"

    markdown = index_path.read_text(encoding="utf-8")
    title = _extract_title_from_markdown(markdown)
    summary = _extract_summary_from_markdown(markdown)

    tour_id = _generate_tour_id(tour_type, original_slug)
    tour = await create_tour(
        tour_id=tour_id,
        title=title,
        tour_type=tour_type,
        slug=original_slug,
        summary=summary,
    )

    return tour


def list_trash() -> list[dict[str, Any]]:
    """List all tours in trash.

    Returns:
        List of dicts with tour_type, trash_name, original_slug, deleted_at, title.
    """
    result: list[dict[str, Any]] = []

    if not TRASH_DIR.exists():
        return result

    for tour_type in ("bike", "road"):
        type_dir = TRASH_DIR / tour_type
        if not type_dir.exists():
            continue

        for item in type_dir.iterdir():
            if not item.is_dir():
                continue

            # Parse name: slug_YYYYMMDD-HHMMSS
            parts = item.name.rsplit("_", 1)
            original_slug = parts[0]
            deleted_at = None
            if len(parts) == 2:
                with contextlib.suppress(ValueError):
                    deleted_at = datetime.strptime(parts[1], "%Y%m%d-%H%M%S")

            # Try to get title from index.md
            title = original_slug
            index_path = item / "index.md"
            if index_path.exists():
                markdown = index_path.read_text(encoding="utf-8")
                title = _extract_title_from_markdown(markdown)

            result.append(
                {
                    "tour_type": tour_type,
                    "trash_name": item.name,
                    "original_slug": original_slug,
                    "deleted_at": deleted_at.isoformat() if deleted_at else None,
                    "title": title,
                }
            )

    # Sort by deleted_at descending (most recent first)
    result.sort(key=lambda x: x["deleted_at"] or "", reverse=True)
    return result


async def empty_trash() -> int:
    """Permanently delete all tours in trash.

    Returns:
        Number of tours deleted.
    """
    if not TRASH_DIR.exists():
        return 0

    count = 0
    for tour_type in ("bike", "road"):
        type_dir = TRASH_DIR / tour_type
        if not type_dir.exists():
            continue

        for item in type_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                count += 1
                logger.info("Permanently deleted: %s", item)

    return count


async def delete_from_trash(tour_type: str, trash_name: str) -> bool:
    """Permanently delete a single tour from trash.

    Returns:
        True if deleted, False if not found.
    """
    if tour_type not in ("bike", "road") or not is_valid_trash_name(trash_name):
        return False

    trash_path = TRASH_DIR / tour_type / trash_name
    if not trash_path.exists():
        return False

    shutil.rmtree(trash_path)
    logger.info("Permanently deleted from trash: %s", trash_path)
    return True


def get_tour_geojson(tour_type: str, slug: str) -> dict[str, Any] | None:
    """Convert a tour's GPX track and waypoints to a GeoJSON FeatureCollection."""
    if tour_type not in ("bike", "road") or not is_valid_slug(slug):
        return None

    gpx_content = get_tour_gpx(tour_type, slug)
    if not gpx_content:
        return None

    try:
        gpx_ns = "http://www.topografix.com/GPX/1/1"
        root = ET.fromstring(gpx_content)
        coordinates: list[list[float]] = []

        for trkpt in root.findall(f".//{{{gpx_ns}}}trkpt"):
            lat = float(trkpt.get("lat", "0"))
            lon = float(trkpt.get("lon", "0"))
            ele_elem = trkpt.find(f"{{{gpx_ns}}}ele")
            if ele_elem is not None and ele_elem.text:
                coordinates.append([lon, lat, float(ele_elem.text)])
            else:
                coordinates.append([lon, lat])

        features: list[dict[str, Any]] = []
        if coordinates:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                    "properties": {
                        "name": slug,
                        "tour_type": tour_type,
                    },
                }
            )

        for wpt in root.findall(f".//{{{gpx_ns}}}wpt"):
            lat = float(wpt.get("lat", "0"))
            lon = float(wpt.get("lon", "0"))
            name_elem = wpt.find(f"{{{gpx_ns}}}name")
            name = name_elem.text if name_elem is not None else ""
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                    "properties": {
                        "name": name,
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }
    except Exception as e:
        logger.error("Failed to convert GPX to GeoJSON: %s", e)
        return None
