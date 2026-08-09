"""Tour storage module for saving tours to filesystem and SQLite index.

Tours are stored as:
    trips/{tour_type}/{slug}/
        ├── index.md      # Tour description (markdown)
        ├── gpx/          # GPX track files
        │   └── route.gpx
        └── maps/         # Map images (optional)

SQLite is used as an index for fast listing and search.
"""

import logging
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from db import Tour, create_tour, generate_slug, get_tour_by_slug

logger = logging.getLogger(__name__)

# Project root and trips directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRIPS_DIR = PROJECT_ROOT / "trips"


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
    tour_dir.mkdir(parents=True, exist_ok=True)

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

    # Index in SQLite
    tour_id = str(uuid.uuid4())
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


def get_tour_path(tour_type: str, slug: str) -> Path:
    """Get the filesystem path for a tour."""
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
            "creator": "Gerrit on Tour",
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
    from db import get_tour_by_slug

    tour = await get_tour_by_slug(slug)
    if not tour:
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

    return {
        "id": tour.id,
        "title": tour.title,
        "tour_type": tour.tour_type,
        "slug": tour.slug,
        "summary": tour.summary,
        "created_at": tour.created_at.isoformat(),
        "updated_at": tour.updated_at.isoformat(),
        "markdown": markdown,
        "has_gpx": has_tour_gpx(tour_type, slug),
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

            tour_id = str(uuid.uuid4())
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
