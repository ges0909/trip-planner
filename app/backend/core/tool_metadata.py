"""Metadata and classification helpers for MCP tools."""

ROUTE_TOOL_PATTERNS = ("route", "calculate_car", "calculate_bike")
GEOCODE_TOOL_PATTERNS = ("geocode", "search_location")
POI_TOOL_PATTERNS = ("search_pois",)

TOOL_STATUS_CATEGORIES: dict[str, str] = {
    "mcp_brouter_calculate_route": "status_routing",
    "mcp_osrm_calculate_car_route": "status_routing",
    "mcp_osrm_route_to_gpx": "status_routing",
    "mcp_openrouteservice_calculate_route": "status_routing",
    "mcp_openrouteservice_driving_time": "status_routing",
    "mcp_openrouteservice_isochrone": "status_routing",
    "mcp_openrouteservice_distance_matrix": "status_routing",
    "mcp_brouter_search_location": "status_location",
    "mcp_openrouteservice_geocode": "status_location",
    "mcp_open_meteo_geocoding": "status_location",
    "mcp_open_meteo_weather_forecast": "status_weather",
    "mcp_vbb_search_stops": "status_transit",
    "mcp_vbb_get_departures": "status_transit",
    "mcp_vbb_get_journeys": "status_transit",
    "mcp_overpass_search_pois_along_route": "status_pois",
    "mcp_waymarkedtrails_search_routes": "status_trails",
    "mcp_waymarkedtrails_get_route_details": "status_trails",
    "mcp_waymarkedtrails_search_routes_in_region": "status_trails",
    "mcp_waymarkedtrails_get_route_segments": "status_trails",
    "mcp_wikivoyage_search_destinations": "status_travel_info",
    "mcp_wikivoyage_get_article": "status_travel_info",
    "mcp_wikivoyage_get_section": "status_travel_info",
    "mcp_wikivoyage_get_article_sections": "status_travel_info",
    "mcp_wikivoyage_search_nearby": "status_travel_info",
    "mcp_tavily_web_search": "status_web_search",
    "mcp_tavily_web_extract": "status_web_search",
    "mcp_brouter_render_gpx_map": "status_rendering",
    "mcp_brouter_render_elevation_profile": "status_rendering",
    "mcp_travel_content_search_travel_articles": "status_web_search",
    "mcp_travel_content_search_travel_videos": "status_web_search",
    "mcp_travel_content_extract_route_tips": "status_web_search",
    "mcp_travel_videos_search_travel_videos": "status_web_search",
    "mcp_travel_videos_get_video_transcript": "status_web_search",
    "mcp_travel_videos_search_and_transcribe": "status_web_search",
    "mcp_podcasts_search_podcasts": "status_web_search",
    "mcp_podcasts_search_podcast_episodes": "status_web_search",
    "mcp_podcasts_get_podcast_episodes": "status_web_search",
    "mcp_podcasts_get_episode_transcript": "status_web_search",
    "mcp_serpapi_flights_search_flights": "status_flights",
    "mcp_serpapi_flights_search_airport": "status_flights",
}


def is_route_tool(name: str) -> bool:
    """Check whether a tool response can contain route geometry."""
    return any(pattern in name for pattern in ROUTE_TOOL_PATTERNS)


def is_geocode_tool(name: str) -> bool:
    """Check whether a tool response can contain location coordinates."""
    return any(pattern in name for pattern in GEOCODE_TOOL_PATTERNS)


def is_poi_tool(name: str) -> bool:
    """Check whether a tool response can contain points of interest."""
    return any(pattern in name for pattern in POI_TOOL_PATTERNS)


def get_status_categories(tool_names: list[str]) -> list[str]:
    """Return unique status categories in tool call order."""
    seen: set[str] = set()
    categories: list[str] = []
    for name in tool_names:
        category = TOOL_STATUS_CATEGORIES.get(name, "status_generic")
        if category not in seen:
            seen.add(category)
            categories.append(category)
    return categories
