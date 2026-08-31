"""Unit tests for schema minification and tool selection by trip mode."""

from core.compaction import (
    _compact_schema,
    _compact_tool_declarations,
    _select_tool_declarations,
)


def test_compact_schema_removes_titles_keeps_descriptions():
    """Schema compactor keeps validation keywords and descriptions while stripping titles."""
    full_schema = {
        "type": "object",
        "title": "CalculateRouteArgs",
        "description": "Tool argument description",
        "required": ["waypoints"],
        "properties": {
            "waypoints": {
                "type": "array",
                "title": "WaypointsTitle",
                "description": "List of lon/lat coordinates",
                "items": {"type": "array", "description": "Inner coord array"},
            },
            "profile": {
                "type": "string",
                "enum": ["trekking", "fastbike"],
                "description": "Bicycle routing profile",
            },
        },
    }

    compacted = _compact_schema(full_schema)
    assert compacted["type"] == "object"
    assert "title" not in compacted
    assert compacted["description"] == "Tool argument description"
    assert compacted["required"] == ["waypoints"]
    assert "waypoints" in compacted["properties"]
    assert "title" not in compacted["properties"]["waypoints"]
    assert compacted["properties"]["waypoints"]["description"] == "List of lon/lat coordinates"
    assert compacted["properties"]["profile"]["enum"] == ["trekking", "fastbike"]


def test_compact_tool_declarations():
    """Tool declarations keep name, description, and compacted parameters."""
    decls = [
        {
            "name": "mcp_brouter_calculate_route",
            "description": "Long prose description of the tool",
            "parameters": {
                "type": "object",
                "properties": {"test": {"type": "string"}},
            },
        }
    ]

    compacted = _compact_tool_declarations(decls)
    assert len(compacted) == 1
    assert compacted[0]["name"] == "mcp_brouter_calculate_route"
    assert compacted[0]["description"] == "Long prose description of the tool"
    assert "parameters" in compacted[0]


def test_select_tool_declarations_bike_mode():
    """Bike mode selects bike-specific MCP tools."""
    decls = [
        {"name": "mcp_brouter_calculate_route"},
        {"name": "mcp_osrm_calculate_car_route"},
        {"name": "mcp_wikivoyage_search_destinations"},
        {"name": "mcp_serpapi_flights_search_flights"},
    ]

    bike_tools = _select_tool_declarations(decls, "Ich plane eine Radtour von Berlin nach Potsdam")
    tool_names = [t["name"] for t in bike_tools]

    assert "mcp_brouter_calculate_route" in tool_names
    assert "mcp_wikivoyage_search_destinations" in tool_names
    assert "mcp_serpapi_flights_search_flights" not in tool_names


def test_select_tool_declarations_road_mode():
    """Road trip mode selects road-specific MCP tools."""
    decls = [
        {"name": "mcp_brouter_calculate_route"},
        {"name": "mcp_osrm_calculate_car_route"},
        {"name": "mcp_wikivoyage_search_destinations"},
        {"name": "mcp_serpapi_flights_search_flights"},
    ]

    road_tools = _select_tool_declarations(decls, "Roadtrip mit dem Auto durch Südfrankreich")
    tool_names = [t["name"] for t in road_tools]

    assert "mcp_osrm_calculate_car_route" in tool_names
    assert "mcp_wikivoyage_search_destinations" in tool_names
    assert "mcp_serpapi_flights_search_flights" in tool_names
