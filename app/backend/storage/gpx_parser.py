"""GPX parsing and combination utilities."""

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)

GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"


def order_gpx_by_markdown(gpx_files: list[Path], index_md: Path) -> list[Path]:
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


def combine_gpx_files(gpx_files: list[Path]) -> str:
    """Combine multiple GPX files into a single GPX with multiple tracks.

    If an index.md exists in the parent directory, uses the order from the
    markdown headings (### Tag N · ...) to sort the tracks.
    """
    if not gpx_files:
        return ""

    tour_dir = gpx_files[0].parent.parent
    index_md = tour_dir / "index.md"
    ordered_files = order_gpx_by_markdown(gpx_files, index_md)

    ET.register_namespace("", GPX_NAMESPACE)

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
            tracks = file_root.findall(f"{{{GPX_NAMESPACE}}}trk")

            for trk in tracks:
                name_elem = trk.find(f"{{{GPX_NAMESPACE}}}name")
                if name_elem is None:
                    name_elem = ET.SubElement(trk, f"{{{GPX_NAMESPACE}}}name")
                    name_elem.text = gpx_file.stem.replace("-", " → ")
                root.append(trk)
        except ET.ParseError:
            logger.warning("Failed to parse GPX file: %s", gpx_file)
            continue

    return ET.tostring(root, encoding="unicode", xml_declaration=True)
