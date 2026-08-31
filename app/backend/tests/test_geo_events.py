"""Unit tests for GPX parsing, elevation profiling, and geo event extraction."""

from core.agent_context import AgentContext
from core.geo_events import (
    _extract_elevation_from_gpx,
    _is_geocode_tool,
    _is_poi_tool,
    _is_route_tool,
    _process_tool_result,
)

SAMPLE_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BRouter" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Test Route</name>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050">
        <ele>34.5</ele>
      </trkpt>
      <trkpt lat="52.5250" lon="13.4100">
        <ele>42.0</ele>
      </trkpt>
      <trkpt lat="52.5300" lon="13.4150">
        <ele>38.0</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def test_extract_elevation_from_valid_gpx():
    """Valid GPX produces distance/elevation point pairs."""
    profile = _extract_elevation_from_gpx(SAMPLE_GPX)
    assert profile is not None
    assert len(profile) >= 2
    # Distance of first point should be 0.0
    assert profile[0][0] == 0.0
    assert profile[0][1] == 34.5
    # Last point has elevation 38.0
    assert profile[-1][1] == 38.0
    assert profile[-1][0] > 0.0


def test_extract_elevation_from_invalid_or_short_gpx():
    """Empty or single-point GPX returns None gracefully."""
    assert _extract_elevation_from_gpx("") is None
    assert _extract_elevation_from_gpx("<gpx></gpx>") is None

    single_point = """<?xml version="1.0"?>
    <gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
      <trk><trkseg><trkpt lat="52.5" lon="13.4"><ele>10.0</ele></trkpt></trkseg></trk>
    </gpx>"""
    assert _extract_elevation_from_gpx(single_point) is None


def test_tool_type_detection():
    """Tool names are correctly classified by geo category."""
    assert _is_route_tool("mcp_brouter_calculate_route")
    assert _is_route_tool("mcp_osrm_calculate_car_route")
    assert not _is_route_tool("mcp_tavily_web_search")

    assert _is_geocode_tool("mcp_brouter_search_location")
    assert _is_geocode_tool("mcp_openrouteservice_geocode")
    assert not _is_geocode_tool("mcp_brouter_calculate_route")

    assert _is_poi_tool("mcp_overpass_search_pois_along_route")
    assert not _is_poi_tool("mcp_brouter_calculate_route")


def test_process_tool_result_route_with_gpx():
    """Route tool results emit map, elevation, and gpx events."""
    ctx = AgentContext(language="de")
    raw_result = {
        "geometry": [[52.52, 13.40], [52.53, 13.41]],
        "gpx": SAMPLE_GPX,
        "distance": 1500,
    }

    processed = _process_tool_result("mcp_brouter_calculate_route", {}, raw_result, ctx)
    events = ctx.drain_events()

    event_types = [e["event"] for e in events]
    assert "map" in event_types
    assert "elevation" in event_types
    assert "gpx" in event_types

    # Heavy payload fields are stripped from LLM result
    assert "geometry" not in processed
    assert "gpx" not in processed
    assert "gpx_path" in processed
    assert ctx.gpx_content == SAMPLE_GPX


def test_process_car_route_result_with_gpx():
    """Car routes stream their GPX so saved road trips retain route data."""
    ctx = AgentContext(language="de")
    raw_result = {
        "geometry": [[52.52, 13.40], [52.53, 13.41]],
        "gpx": SAMPLE_GPX,
    }

    _process_tool_result("mcp_osrm_calculate_car_route", {}, raw_result, ctx)

    assert ctx.gpx_content == SAMPLE_GPX
    assert any(event["event"] == "gpx" for event in ctx.drain_events())


def test_process_tool_result_geocode():
    """Geocode tool results emit waypoint map events."""
    ctx = AgentContext(language="de")
    raw_result = {
        "results": [
            {"name": "Berlin", "coordinates": [13.4050, 52.5200]}  # [lon, lat]
        ]
    }

    _process_tool_result("mcp_brouter_search_location", {}, raw_result, ctx)
    events = ctx.drain_events()

    assert len(events) == 1
    assert events[0]["event"] == "map"
    assert events[0]["data"]["waypoints"] == [[52.5200, 13.4050]]


def test_process_tool_result_poi_text():
    """POI tool results parse formatted markdown text into POI markers."""
    ctx = AgentContext(language="de")
    raw_result = {
        "text": "Found POIs:\n- **Café Einstein** (cafe) [52.5050, 13.3850]\n- **Brandenburger Tor** (historic) [52.5163, 13.3777]"
    }

    _process_tool_result("mcp_overpass_search_pois_along_route", {}, raw_result, ctx)
    events = ctx.drain_events()

    assert len(events) == 1
    assert events[0]["event"] == "map"
    pois = events[0]["data"]["pois"]
    assert len(pois) == 2
    assert pois[0]["name"] == "Café Einstein"
    assert pois[0]["category"] == "cafe"
    assert pois[0]["lat"] == 52.5050
    assert pois[0]["lon"] == 13.3850


def test_process_tool_result_render_gpx_map_args():
    """render_gpx_map emits POIs passed in tool arguments."""
    ctx = AgentContext(language="de")
    tool_args = {"pois": [{"lat": 52.52, "lon": 13.40, "name": "Start", "category": "info"}]}

    _process_tool_result("mcp_brouter_render_gpx_map", tool_args, {"status": "ok"}, ctx)
    events = ctx.drain_events()

    assert any(e["event"] == "map" and len(e["data"].get("pois", [])) == 1 for e in events)


def test_extract_tour_metrics_from_gpx():
    """Extract metrics correctly calculates distance, elevation gain, and difficulty from GPX."""
    from core.geo_events import extract_tour_metrics

    metrics = extract_tour_metrics(SAMPLE_GPX)
    assert metrics["point_count"] == 3
    assert metrics["distance_km"] is not None
    assert metrics["distance_km"] > 0
    assert metrics["elevation_gain_m"] == 8.0  # from 34.5m to 42.0m -> 7.5m rounded to 8m
    assert metrics["difficulty"] in ("easy", "moderate", "challenging")


def test_extract_tour_metrics_from_markdown():
    """Extract metrics parses distance, duration, route type, and start from markdown."""
    from core.geo_events import extract_tour_metrics

    markdown = """# Spreewald-Runde
**Distanz:** 55,5 km
**Fahrzeit:** ca. 3,5 Std.
**Routentyp:** Rundtour, flach
**Start/Ziel:** Lübben Bhf
"""
    metrics = extract_tour_metrics(None, markdown)
    assert metrics["distance_km"] == 55.5
    assert metrics["duration_hours"] == 3.5
    assert metrics["route_type"] == "Rundtour"
    assert metrics["start_location"] == "Lübben Bhf"
    assert metrics["difficulty"] == "moderate"


def test_combine_gpx_strings_multi_track():
    """_combine_gpx_strings merges multiple GPX tracks into a unified document."""
    from core.geo_events import _combine_gpx_strings

    gpx1 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>Etappe 1</name><trkseg><trkpt lat="52.52" lon="13.40"/></trkseg></trk>
</gpx>"""

    gpx2 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>Etappe 2</name><trkseg><trkpt lat="52.40" lon="13.50"/></trkseg></trk>
</gpx>"""

    combined = _combine_gpx_strings([gpx1, gpx2])
    assert "<trk>" in combined or "<trk " in combined
    assert combined.count("<trk>") + combined.count("<trk ") == 2
    assert "Etappe 1" in combined
    assert "Etappe 2" in combined


def test_process_tool_result_accumulates_multi_segment_gpx():
    """Consecutive route tool calls accumulate into combined multi-track GPX."""
    ctx = AgentContext(language="de")

    res1 = {
        "geometry": [[52.52, 13.40], [52.53, 13.41]],
        "gpx": SAMPLE_GPX,
    }
    _process_tool_result("mcp_osrm_calculate_car_route", {}, res1, ctx)
    events1 = ctx.drain_events()
    assert any(e["event"] == "gpx" for e in events1)
    assert len(ctx.gpx_tracks) == 1

    res2 = {
        "geometry": [[52.53, 13.41], [52.54, 13.42]],
        "gpx": SAMPLE_GPX,
    }
    _process_tool_result("mcp_osrm_calculate_car_route", {}, res2, ctx)
    events2 = ctx.drain_events()
    gpx_events = [e for e in events2 if e["event"] == "gpx"]
    assert len(gpx_events) == 1
    assert len(ctx.gpx_tracks) == 2
    assert ctx.gpx_content is not None
    assert ctx.gpx_content.count("<trk>") + ctx.gpx_content.count("<trk ") == 2
