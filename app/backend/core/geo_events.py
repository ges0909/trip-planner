"""GPX parsing, elevation profiling, and geo-event extraction from MCP tool results."""

import contextlib
import logging
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from typing import Any

from core.agent_context import AgentContext
from core.tool_metadata import is_geocode_tool, is_poi_tool, is_route_tool

logger = logging.getLogger(__name__)

# Geo-relevant tool detection by name pattern (re-exported for test compatibility)
GEO_ROUTE_PATTERNS = ("route", "calculate_car", "calculate_bike")
GEO_POINT_PATTERNS = ("geocode", "search_location")
GEO_POI_PATTERNS = ("search_pois",)


def _is_route_tool(name: str) -> bool:
    """Check if a tool name indicates route geometry in the response."""
    return is_route_tool(name) or any(p in name for p in GEO_ROUTE_PATTERNS)


def _is_geocode_tool(name: str) -> bool:
    """Check if a tool name indicates geocoding results."""
    return is_geocode_tool(name) or any(p in name for p in GEO_POINT_PATTERNS)


def _is_poi_tool(name: str) -> bool:
    """Check if a tool name indicates POI search results."""
    return is_poi_tool(name) or any(p in name for p in GEO_POI_PATTERNS)


def _extract_elevation_from_gpx(gpx_content: str) -> list[list[float]] | None:
    """Extract elevation profile from GPX content.

    Returns list of [distance_km, elevation_m] pairs, or None if extraction fails.
    """
    try:
        gpx_ns = "http://www.topografix.com/GPX/1/1"
        root = ET.fromstring(gpx_content)
        points: list[tuple[float, float, float]] = []

        for trkpt in root.findall(f".//{{{gpx_ns}}}trkpt"):
            lat = float(trkpt.get("lat", "0"))
            lon = float(trkpt.get("lon", "0"))
            ele_elem = trkpt.find(f"{{{gpx_ns}}}ele")
            if ele_elem is not None and ele_elem.text:
                ele = float(ele_elem.text)
                points.append((lat, lon, ele))

        if len(points) < 2:
            return None

        # Calculate cumulative distance
        cum_dist = [0.0]
        for i in range(1, len(points)):
            dlat = (points[i][0] - points[i - 1][0]) * 111320
            dlon = (points[i][1] - points[i - 1][1]) * 111320 * math.cos(math.radians(points[i][0]))
            cum_dist.append(cum_dist[-1] + math.sqrt(dlat**2 + dlon**2))

        total_m = cum_dist[-1]

        # Sample to ~200 points for the chart
        step = max(1, len(points) // 200)
        elevation_data: list[list[float]] = []
        for i in range(0, len(points), step):
            elevation_data.append([round(cum_dist[i] / 1000, 2), round(points[i][2], 1)])

        # Always include last point
        if elevation_data[-1][0] != round(total_m / 1000, 2):
            elevation_data.append([round(total_m / 1000, 2), round(points[-1][2], 1)])

        logger.info("Elevation profile: %d points, %.1f km", len(elevation_data), total_m / 1000)
        return elevation_data
    except Exception as exc:
        logger.debug("Failed to extract elevation: %s", exc)
        return None


def _combine_gpx_strings(gpx_strings: list[str]) -> str:
    """Combine multiple GPX XML strings into a single multi-track GPX document."""
    valid_strings = [s for s in gpx_strings if s and ("<trk" in s or "<wpt" in s)]
    if not valid_strings:
        return ""
    if len(valid_strings) == 1:
        return valid_strings[0]

    gpx_ns = "http://www.topografix.com/GPX/1/1"
    ET.register_namespace("", gpx_ns)
    root = ET.Element(
        "gpx",
        {
            "version": "1.1",
            "creator": "Tour Pilot",
        },
    )

    for i, gpx_str in enumerate(valid_strings, 1):
        try:
            tree_root = ET.fromstring(gpx_str)
            tracks = tree_root.findall(f".//{{{gpx_ns}}}trk")
            if not tracks:
                tracks = tree_root.findall(".//trk")
            for trk in tracks:
                name_elem = trk.find(f"{{{gpx_ns}}}name")
                if name_elem is None:
                    name_elem = trk.find("name")
                if name_elem is None:
                    name_elem = ET.SubElement(trk, f"{{{gpx_ns}}}name")
                    name_elem.text = f"Etappe {i}"
                root.append(trk)
        except ET.ParseError:
            continue

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def extract_tour_metrics(gpx_content: str | None, markdown: str = "") -> dict[str, Any]:
    """Calculate structured metrics (distance, elevation gain, duration, difficulty) from GPX or text."""
    metrics: dict[str, Any] = {
        "distance_km": None,
        "elevation_gain_m": None,
        "duration_hours": None,
        "point_count": 0,
        "difficulty": None,
        "route_type": None,
        "start_location": None,
    }

    if gpx_content:
        try:
            gpx_ns = "http://www.topografix.com/GPX/1/1"
            root = ET.fromstring(gpx_content)
            points: list[tuple[float, float, float | None]] = []

            for trkpt in root.findall(f".//{{{gpx_ns}}}trkpt"):
                lat = float(trkpt.get("lat", "0"))
                lon = float(trkpt.get("lon", "0"))
                ele_elem = trkpt.find(f"{{{gpx_ns}}}ele")
                ele = float(ele_elem.text) if (ele_elem is not None and ele_elem.text) else None
                points.append((lat, lon, ele))

            metrics["point_count"] = len(points)

            if len(points) >= 2:
                total_distance_m = 0.0
                elevation_gain_m = 0.0

                for i in range(1, len(points)):
                    dlat = (points[i][0] - points[i - 1][0]) * 111320
                    dlon = (
                        (points[i][1] - points[i - 1][1])
                        * 111320
                        * math.cos(math.radians(points[i][0]))
                    )
                    total_distance_m += math.sqrt(dlat**2 + dlon**2)

                    curr_ele = points[i][2]
                    prev_ele = points[i - 1][2]
                    if curr_ele is not None and prev_ele is not None and curr_ele > prev_ele:
                        elevation_gain_m += curr_ele - prev_ele

                metrics["distance_km"] = round(total_distance_m / 1000, 1)
                metrics["elevation_gain_m"] = round(elevation_gain_m, 0)
        except Exception as e:
            logger.debug("Failed to extract metrics from GPX: %s", e)

    # Text extraction fallbacks and enrichments
    if markdown:
        # Distance
        if metrics["distance_km"] is None:
            dist_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:km|Kilometer)", markdown, re.IGNORECASE)
            if dist_match:
                with contextlib.suppress(ValueError):
                    metrics["distance_km"] = float(dist_match.group(1).replace(",", "."))

        # Duration
        dur_match = re.search(
            r"\*\*Fahrzeit:\*\*\s*(?:ca\.\s*)?(\d+(?:[.,]\d+)?)(?:–\d+(?:[.,]\d+)?)?\s*(?:Std|h|Stunden)",
            markdown,
            re.IGNORECASE,
        )
        if dur_match:
            with contextlib.suppress(ValueError):
                metrics["duration_hours"] = float(dur_match.group(1).replace(",", "."))
        elif metrics["distance_km"] is not None:
            metrics["duration_hours"] = round(metrics["distance_km"] / 18.0, 1)

        # Route type (e.g. Rundtour, Streckentour)
        type_match = re.search(r"\*\*Routentyp:\*\*\s*([^,\n]+)", markdown, re.IGNORECASE)
        if type_match:
            metrics["route_type"] = type_match.group(1).strip()

        # Start location
        start_match = re.search(r"\*\*Start(?:/Ziel)?:\*\*\s*([^\n]+)", markdown, re.IGNORECASE)
        if start_match:
            metrics["start_location"] = start_match.group(1).strip()

    # Difficulty classification based on distance and elevation
    dist = metrics["distance_km"] or 0.0
    ele = metrics["elevation_gain_m"] or 0.0
    if dist > 0:
        if dist < 45 and ele < 300:
            metrics["difficulty"] = "easy"
        elif dist < 85 and ele < 800:
            metrics["difficulty"] = "moderate"
        else:
            metrics["difficulty"] = "challenging"

    return metrics


def _process_tool_result(
    tool_name: str,
    tool_args: dict[str, Any],
    result: Any,
    ctx: AgentContext,
) -> Any:
    """Process tool result and emit SSE events for geo data.

    Returns the (possibly modified) result to pass back to the LLM.
    """
    # Extract POI coordinates from render_gpx_map arguments
    if tool_name == "mcp_brouter_render_gpx_map" and tool_args.get("pois"):
        pois_arg = tool_args["pois"]
        poi_list: list[dict[str, Any]] = []
        for poi in pois_arg:
            lat_p = poi.get("lat")
            lon_p = poi.get("lon")
            if lat_p is not None and lon_p is not None:
                poi_list.append(
                    {
                        "lat": lat_p,
                        "lon": lon_p,
                        "name": poi.get("name", ""),
                        "category": poi.get("category", ""),
                    }
                )
        if poi_list:
            logger.info("Emitting %d POI markers from render_gpx_map args", len(poi_list))
            ctx.emit("map", {"pois": poi_list})

    if not isinstance(result, dict):
        return result

    # Handle POI tools
    if _is_poi_tool(tool_name):
        text = result.get("text", "")
        if text:
            poi_list: list[dict[str, Any]] = []
            for m in re.finditer(
                r"\*\*(.+?)\*\*\s*\(([^)]*)\)\s*\[(-?\d+\.\d+),\s*(-?\d+\.\d+)\]",
                text,
            ):
                poi_list.append(
                    {
                        "lat": float(m.group(3)),
                        "lon": float(m.group(4)),
                        "name": m.group(1),
                        "category": m.group(2),
                    }
                )
            if poi_list:
                logger.info("Emitting %d POI markers from overpass text", len(poi_list))
                ctx.emit("map", {"pois": poi_list})

    # Handle geocode tools
    elif _is_geocode_tool(tool_name):
        results_list = result.get("results", [])
        if results_list:
            coords = results_list[0].get("coordinates", [])
            if len(coords) == 2:
                ctx.emit("map", {"waypoints": [[coords[1], coords[0]]]})

    # Handle route tools
    elif _is_route_tool(tool_name):
        geometry = result.get("geometry")
        if geometry:
            ctx.emit("map", {"route": [[lat, lon] for lat, lon in geometry]})

        gpx_content = result.get("gpx")
        if gpx_content:
            if not hasattr(ctx, "gpx_tracks"):
                ctx.gpx_tracks = []
            ctx.gpx_tracks.append(gpx_content)
            combined_gpx = _combine_gpx_strings(ctx.gpx_tracks)
            ctx.gpx_content = combined_gpx

            # Save GPX to temp file
            gpx_dir = os.path.join(tempfile.gettempdir(), "rad-touren-gpx")
            os.makedirs(gpx_dir, exist_ok=True)
            gpx_path = os.path.join(gpx_dir, "latest-route.gpx")
            with open(gpx_path, "w", encoding="utf-8") as f:
                f.write(combined_gpx)
            logger.info("GPX saved to %s (tracks: %d)", gpx_path, len(ctx.gpx_tracks))

            result["gpx_path"] = gpx_path

            # Extract and emit elevation profile
            elevation_data = _extract_elevation_from_gpx(combined_gpx)
            if elevation_data:
                ctx.emit("elevation", {"profile": elevation_data})

            # Emit GPX for download
            ctx.emit("gpx", {"gpx": combined_gpx})

        # Strip large fields before sending to LLM
        result.pop("geometry", None)
        result.pop("gpx", None)

    return result
