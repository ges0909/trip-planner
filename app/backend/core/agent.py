"""pydantic-ai based agent with MCP tool integration and SSE event streaming.

This agent uses pydantic-ai for the model interface (provider-agnostic LLM calls)
while keeping our custom MCPManager for tool discovery and execution. This gives
us full control over SSE event emission during tool calls.
"""

import json
import logging
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from i18n import Lang
from i18n import msg as i18n_msg
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import ToolDefinition

from core.mcp_manager import MCPManager
from core.model_gateway import get_model
from core.context import build_system_prompt

logger = logging.getLogger(__name__)

# Type alias for SSE events
type SSEEvent = dict[str, Any]

# Geo-relevant tool detection by name pattern
GEO_ROUTE_PATTERNS = ("route", "calculate_car", "calculate_bike")
GEO_POINT_PATTERNS = ("geocode", "search_location")
GEO_POI_PATTERNS = ("search_pois",)

# Tool name → status message i18n key mapping
_TOOL_STATUS_CATEGORY: dict[str, str] = {
    # Routing
    "mcp_brouter_calculate_route": "status_routing",
    "mcp_osrm_calculate_car_route": "status_routing",
    "mcp_osrm_route_to_gpx": "status_routing",
    "mcp_openrouteservice_calculate_route": "status_routing",
    "mcp_openrouteservice_driving_time": "status_routing",
    "mcp_openrouteservice_isochrone": "status_routing",
    "mcp_openrouteservice_distance_matrix": "status_routing",
    # Location search
    "mcp_brouter_search_location": "status_location",
    "mcp_openrouteservice_geocode": "status_location",
    "mcp_open_meteo_geocoding": "status_location",
    # Weather
    "mcp_open_meteo_weather_forecast": "status_weather",
    # Public transport
    "mcp_vbb_search_stops": "status_transit",
    "mcp_vbb_get_departures": "status_transit",
    "mcp_vbb_get_journeys": "status_transit",
    # POIs
    "mcp_overpass_search_pois_along_route": "status_pois",
    # Trails
    "mcp_waymarkedtrails_search_routes": "status_trails",
    "mcp_waymarkedtrails_get_route_details": "status_trails",
    "mcp_waymarkedtrails_search_routes_in_region": "status_trails",
    "mcp_waymarkedtrails_get_route_segments": "status_trails",
    # Travel info
    "mcp_wikivoyage_search_destinations": "status_travel_info",
    "mcp_wikivoyage_get_article": "status_travel_info",
    "mcp_wikivoyage_get_section": "status_travel_info",
    "mcp_wikivoyage_get_article_sections": "status_travel_info",
    "mcp_wikivoyage_search_nearby": "status_travel_info",
    # Web search
    "mcp_tavily_web_search": "status_web_search",
    "mcp_tavily_web_extract": "status_web_search",
    # Rendering
    "mcp_brouter_render_gpx_map": "status_rendering",
    "mcp_brouter_render_elevation_profile": "status_rendering",
    # Travel content
    "mcp_travel_content_search_travel_articles": "status_web_search",
    "mcp_travel_content_search_travel_videos": "status_web_search",
    "mcp_travel_content_extract_route_tips": "status_web_search",
    # Travel videos
    "mcp_travel_videos_search_travel_videos": "status_web_search",
    "mcp_travel_videos_get_video_transcript": "status_web_search",
    "mcp_travel_videos_search_and_transcribe": "status_web_search",
    # Podcasts
    "mcp_podcasts_search_podcasts": "status_web_search",
    "mcp_podcasts_search_podcast_episodes": "status_web_search",
    "mcp_podcasts_get_podcast_episodes": "status_web_search",
    "mcp_podcasts_get_episode_transcript": "status_web_search",
    # Flights
    "mcp_serpapi_flights_search_flights": "status_flights",
    "mcp_serpapi_flights_search_airport": "status_flights",
}


def _is_route_tool(name: str) -> bool:
    """Check if a tool name indicates route geometry in the response."""
    return any(p in name for p in GEO_ROUTE_PATTERNS)


def _is_geocode_tool(name: str) -> bool:
    """Check if a tool name indicates geocoding results."""
    return any(p in name for p in GEO_POINT_PATTERNS)


def _is_poi_tool(name: str) -> bool:
    """Check if a tool name indicates POI search results."""
    return any(p in name for p in GEO_POI_PATTERNS)


def _get_status_categories(tool_names: list[str]) -> list[str]:
    """Deduplicate tool calls into unique status category keys."""
    seen: set[str] = set()
    categories: list[str] = []
    for name in tool_names:
        cat = _TOOL_STATUS_CATEGORY.get(name, "status_generic")
        if cat not in seen:
            seen.add(cat)
            categories.append(cat)
    return categories


@dataclass
class AgentContext:
    """Context for tracking SSE events during agent execution."""

    language: str = "de"
    events: list[SSEEvent] = field(default_factory=list)
    gpx_content: str | None = None
    emitted_status_keys: set[str] = field(default_factory=set)

    def emit(self, event: str, data: dict[str, Any]) -> None:
        """Add an SSE event to the collection."""
        self.events.append({"event": event, "data": data})

    def emit_status(self, key: str) -> None:
        """Emit a status message if not already emitted."""
        if key not in self.emitted_status_keys:
            self.emitted_status_keys.add(key)
            lang = self.language if self.language in ("de", "en") else "de"
            self.emit("status", {"message": i18n_msg(key, lang)})

    def get_lang(self) -> Lang:
        """Get language as Lang type."""
        return self.language if self.language in ("de", "en") else "de"


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

    # Handle route tools
    if _is_route_tool(tool_name):
        geometry = result.get("geometry")
        if geometry:
            ctx.emit("map", {"route": [[lat, lon] for lat, lon in geometry]})

        gpx_content = result.get("gpx")
        if gpx_content:
            # Save GPX to temp file
            gpx_dir = os.path.join(tempfile.gettempdir(), "rad-touren-gpx")
            os.makedirs(gpx_dir, exist_ok=True)
            gpx_path = os.path.join(gpx_dir, "latest-route.gpx")
            with open(gpx_path, "w", encoding="utf-8") as f:
                f.write(gpx_content)
            logger.info("GPX saved to %s", gpx_path)

            # Store for later use
            ctx.gpx_content = gpx_content
            result["gpx_path"] = gpx_path

            # Extract and emit elevation profile
            elevation_data = _extract_elevation_from_gpx(gpx_content)
            if elevation_data:
                ctx.emit("elevation", {"profile": elevation_data})

            # Emit GPX for download
            ctx.emit("gpx", {"gpx": gpx_content})

        # Strip large fields before sending to LLM
        result.pop("geometry", None)
        result.pop("gpx", None)

    # Handle geocode tools
    elif _is_geocode_tool(tool_name):
        results_list = result.get("results", [])
        if results_list:
            coords = results_list[0].get("coordinates", [])
            if len(coords) == 2:
                ctx.emit("map", {"waypoints": [[coords[1], coords[0]]]})

    # Handle POI tools
    elif _is_poi_tool(tool_name):
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

    return result


def _gemini_decl_to_tool_def(decl: dict[str, Any]) -> ToolDefinition:
    """Convert Gemini-style FunctionDeclaration to pydantic-ai ToolDefinition."""
    params = decl.get("parameters", {})
    return ToolDefinition(
        name=decl["name"],
        description=decl.get("description", ""),
        parameters_json_schema=params if params else {"type": "object", "properties": {}},
    )


async def run_agent(
    user_message: str,
    chat_history: list[dict[str, str]],
    mcp: MCPManager,
    language: str = "de",
) -> AsyncGenerator[SSEEvent, None]:
    """Run the pydantic-ai agent loop, yielding SSE events.

    This function implements a manual agent loop that:
    1. Uses pydantic-ai's Model interface for LLM calls (provider-agnostic)
    2. Uses MCPManager for tool discovery and execution
    3. Emits SSE events for real-time frontend updates

    Args:
        user_message: The user's input message.
        chat_history: Previous conversation messages.
        mcp: MCPManager instance for tool access.
        language: Output language code ("de" or "en").

    Yields:
        SSE events as dicts with keys: {"event": str, "data": dict}
    """
    lang: Lang = language if language in ("de", "en") else "de"
    ctx = AgentContext(language=language)

    logger.info("Agent started: lang=%s, history=%d messages", lang, len(chat_history))

    # Get model from gateway
    try:
        model = get_model()
    except RuntimeError as e:
        logger.error("Failed to get model: %s", e)
        yield {"event": "error", "data": {"error": i18n_msg("no_api_key", lang)}}
        return

    # Get tool declarations from MCP
    mcp_declarations = await mcp.get_tool_declarations()
    tool_names = [d["name"] for d in mcp_declarations]

    # Build system prompt
    system_prompt = build_system_prompt(
        tool_names=tool_names,
        language=language,
        user_message=user_message,
    )

    logger.debug("System prompt length: %d chars", len(system_prompt))

    # Convert MCP declarations to pydantic-ai ToolDefinitions
    tool_defs = [_gemini_decl_to_tool_def(decl) for decl in mcp_declarations]

    # Build initial message history with system prompt first
    messages: list[ModelMessage] = []

    # Add system prompt as first message
    messages.append(ModelRequest(parts=[SystemPromptPart(content=system_prompt)]))

    # Add chat history
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] in ("model", "assistant"):
            messages.append(ModelResponse(parts=[TextPart(content=msg["content"])]))

    # Add current user message
    messages.append(ModelRequest(parts=[UserPromptPart(content=user_message)]))

    # Model settings
    model_settings = ModelSettings(
        temperature=0.7,
    )

    # Agent loop
    max_iterations = 25
    recovery_count = 0
    max_recoveries = 2

    for iteration in range(max_iterations):
        logger.info("Iteration %d: calling model", iteration + 1)

        try:
            # Call model with tools
            request_params = ModelRequestParameters(
                function_tools=tool_defs,
                allow_text_output=True,
                output_mode="text",
            )
            response = await model.request(
                messages=messages,
                model_settings=model_settings,
                model_request_parameters=request_params,
            )
        except Exception as e:
            logger.exception("Model request failed")
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "rate" in error_str:
                yield {"event": "error", "data": {"error": i18n_msg("quota_exhausted", lang)}}
            elif "503" in error_str or "500" in error_str:
                yield {
                    "event": "error",
                    "data": {"error": i18n_msg("server_unavailable", lang, code="503")},
                }
            else:
                yield {
                    "event": "error",
                    "data": {"error": i18n_msg("unexpected_error", lang, detail=str(e))},
                }
            return

        # Extract parts from response
        response_parts = response.parts if hasattr(response, "parts") else []

        # Check for tool calls
        tool_calls = [p for p in response_parts if isinstance(p, ToolCallPart)]
        text_parts = [p for p in response_parts if isinstance(p, TextPart)]

        if not tool_calls:
            # No tool calls — final response
            final_text = "".join(p.content for p in text_parts if p.content)

            if not final_text and recovery_count < max_recoveries:
                # Empty response — nudge model
                recovery_count += 1
                logger.info("Empty response, nudging model (recovery %d)", recovery_count)
                messages.append(
                    ModelRequest(
                        parts=[
                            UserPromptPart(
                                content="Please provide your complete response based on all information gathered."
                            )
                        ]
                    )
                )
                continue

            # Extract route name from first heading
            heading_match = re.search(r"^#{1,3}\s+(.+)$", final_text, re.MULTILINE)
            route_name = heading_match.group(1).strip() if heading_match else "unnamed"

            logger.info(
                "Agent done: %d iterations, response %d chars", iteration + 1, len(final_text)
            )
            logger.info("Tour generation complete: %s", route_name)

            # Emit collected events first
            for evt in ctx.events:
                yield evt

            yield {"event": "tour", "data": {"markdown": final_text}}
            yield {"event": "done", "data": {"iterations": iteration + 1}}
            return

        # Execute tool calls
        logger.info("Iteration %d: %d tool call(s)", iteration + 1, len(tool_calls))

        # Add model response to history
        messages.append(ModelResponse(parts=response_parts))

        # Emit status messages for tool categories
        call_names = [tc.tool_name for tc in tool_calls]
        for category_key in _get_status_categories(call_names):
            ctx.emit_status(category_key)

        # Yield status events immediately
        for evt in ctx.events[-len(_get_status_categories(call_names)) :]:
            if evt["event"] == "status":
                yield evt

        # Execute tools and collect results
        tool_return_parts: list[ToolReturnPart] = []

        for tc in tool_calls:
            tool_name = tc.tool_name
            tool_args = tc.args if isinstance(tc.args, dict) else {}
            tool_call_id = tc.tool_call_id

            logger.info(
                "Tool call: %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False)[:150]
            )

            try:
                result = await mcp.call_tool(tool_name, tool_args)

                # Process result and emit geo events
                result = _process_tool_result(tool_name, tool_args, result, ctx)

                # Yield geo events immediately
                for evt in ctx.events:
                    if evt not in [e for e in ctx.events if e.get("_yielded")]:
                        evt["_yielded"] = True
                        if evt["event"] != "status":  # Status already yielded
                            yield evt

                result_str = json.dumps(result, ensure_ascii=False, default=str)

                # Truncate large results
                if len(result_str) > 8000:
                    logger.info(
                        "Truncating %s result from %d to 8000 chars", tool_name, len(result_str)
                    )
                    result_str = result_str[:8000] + '..."}'

                logger.debug("Tool %s result: %s", tool_name, result_str[:200])

            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                result_str = json.dumps({"error": str(e)})

            tool_return_parts.append(
                ToolReturnPart(
                    tool_name=tool_name,
                    content=result_str,
                    tool_call_id=tool_call_id,
                )
            )

        # Add tool results to conversation
        messages.append(ModelRequest(parts=tool_return_parts))

    # Max iterations reached
    logger.warning("Max iterations (%d) reached", max_iterations)
    yield {"event": "error", "data": {"error": i18n_msg("max_iterations", lang)}}
