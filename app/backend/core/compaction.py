"""Context token estimation, schema minification, and message compaction."""

import json
from dataclasses import asdict
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ToolReturnPart,
)

from core.context import _detect_tour_type

MAX_CHAT_HISTORY_MESSAGES = 6
MAX_CONTEXT_TOKENS = 12000
MAX_TOOL_RESULT_CHARS = 4000
MAX_RESPONSE_TOKENS = 8192
COMPACTED_TOOL_RESULT = "[Earlier tool result omitted; use the newer results and gathered facts.]"


def _estimate_context_tokens(messages: list[ModelMessage], model_id: str = "") -> int:
    """Estimate tokens for pydantic-ai messages using a ~4 chars per token heuristic."""
    serialized = "\n".join(
        json.dumps(asdict(message), ensure_ascii=False, default=str) for message in messages
    )
    return max(1, len(serialized) // 4)


def _compact_messages(messages: list[ModelMessage], model_id: str) -> list[ModelMessage]:
    """Replace old tool payloads when the in-memory request gets too large."""
    if _estimate_context_tokens(messages, model_id) <= MAX_CONTEXT_TOKENS:
        return messages

    compacted = list(messages)
    for message_index, message in enumerate(compacted):
        if message_index == 0:
            continue

        parts = getattr(message, "parts", [])
        replacement_parts = []
        changed = False
        for part in parts:
            if isinstance(part, ToolReturnPart) and isinstance(part.content, str):
                replacement_parts.append(
                    ToolReturnPart(
                        tool_name=part.tool_name,
                        content=COMPACTED_TOOL_RESULT,
                        tool_call_id=part.tool_call_id,
                    )
                )
                changed = True
            else:
                replacement_parts.append(part)

        if changed:
            compacted[message_index] = ModelRequest(parts=replacement_parts)
            if _estimate_context_tokens(compacted, model_id) <= MAX_CONTEXT_TOKENS:
                break

    return compacted


def _compact_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields needed to validate tool arguments."""
    compacted: dict[str, Any] = {}
    for key in ("type", "enum", "required", "description"):
        if key in schema:
            compacted[key] = schema[key]
    if "items" in schema and isinstance(schema["items"], dict):
        compacted["items"] = _compact_schema(schema["items"])
    if "properties" in schema and isinstance(schema["properties"], dict):
        compacted["properties"] = {
            name: _compact_schema(value)
            for name, value in schema["properties"].items()
            if isinstance(value, dict)
        }
    return compacted


def _compact_tool_declarations(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove verbose MCP prose while preserving descriptions and callable argument schemas."""
    compacted: list[dict[str, Any]] = []
    for declaration in declarations:
        item: dict[str, Any] = {
            "name": declaration["name"],
            "description": declaration.get("description", ""),
        }
        if isinstance(declaration.get("parameters"), dict):
            item["parameters"] = _compact_schema(declaration["parameters"])
        compacted.append(item)
    return compacted


def _select_tool_declarations(
    declarations: list[dict[str, Any]], user_message: str
) -> list[dict[str, Any]]:
    """Keep only tools relevant to the detected trip type."""
    tour_type = _detect_tour_type(user_message)
    if tour_type == "bike":
        prefixes = (
            "mcp_brouter_",
            "mcp_open_meteo_",
            "mcp_overpass_",
            "mcp_waymarkedtrails_",
            "mcp_wikivoyage_",
            "mcp_tavily_",
            "mcp_travel_content_",
        )
    elif tour_type == "road":
        prefixes = (
            "mcp_osrm_",
            "mcp_openrouteservice_geocode",
            "mcp_open_meteo_",
            "mcp_overpass_",
            "mcp_wikivoyage_",
            "mcp_tavily_",
            "mcp_serpapi_flights_",
        )
    else:
        return declarations

    selected = [
        declaration
        for declaration in declarations
        if any(declaration["name"].startswith(prefix) for prefix in prefixes)
    ]
    return selected or declarations
