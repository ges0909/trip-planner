"""Load steering files and assemble system prompt for the LLM."""

import logging
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Project root (4 levels up from core/)
ROOT: Path = Path(__file__).parent.parent.parent.parent

# Travel preferences live in nested AGENTS.md files (shared with Kiro and Claude Code),
# tour workflows and output templates in .kiro/skills/ (shared as SKILL.md).
TRIPS_DIR: Path = ROOT / "trips"
SKILLS_DIR: Path = ROOT / ".kiro" / "skills"

# Tour type literal for type safety
TourType = Literal["bike", "road", "general"]


def _detect_tour_type(message: str) -> TourType:
    """Detect tour type from user message. Returns 'bike', 'road', or 'general'."""
    msg = message.lower()
    bike_words = ("radtour", "fahrrad", "bike", "cycling", "radweg", "radfahren", "e-bike")
    road_words = ("roadtrip", "road trip", "autoreise", "mietwagen", "rental car", "driving")

    if any(w in msg for w in bike_words):
        return "bike"
    if any(w in msg for w in road_words):
        return "road"
    return "general"


def get_steering_for_tour_type(tour_type: TourType) -> list[Path]:
    """Get list of context file paths for a given tour type.

    Args:
        tour_type: One of "bike", "road", or "general".

    Returns:
        List of Path objects to context files that exist.
    """
    paths: list[Path] = []

    # Always include universal travel preferences
    candidates = [TRIPS_DIR / "AGENTS.md"]

    if tour_type in ("bike", "road"):
        skill_dir = SKILLS_DIR / f"{tour_type}-planner"
        candidates += [
            TRIPS_DIR / tour_type / "AGENTS.md",  # tour-type preferences
            skill_dir / "SKILL.md",  # workflow + tool usage
            skill_dir / "references" / "output-template.md",  # output format
        ]
    # "general" → only universal preferences, keep prompt small

    for path in candidates:
        if path.exists():
            paths.append(path)

    return paths


def _select_files(user_message: str) -> list[Path]:
    """Select steering file paths based on detected tour type."""
    detected = _detect_tour_type(user_message) if user_message else "general"
    return get_steering_for_tour_type(detected)


def build_system_prompt(
    tool_names: list[str],
    language: str = "de",
    user_message: str = "",
) -> str:
    """Assemble system prompt. Tool names come from MCP manager.

    Args:
        tool_names: List of available tool names from MCPManager.
        language: Output language code ("de" or "en").
        user_message: The user's input, used to detect tour type.

    Returns:
        Combined steering content as a single string.
    """
    lang_name = "German" if language == "de" else "English"
    tool_list_str = ", ".join(f"`{name}`" for name in tool_names)

    base_prompt = f"""You are a travel planning assistant. You help plan cycling tours, hikes, and road trips.

## Critical Behavior Rules

- NEVER apologize for tool failures or mention technical problems to the user.
- NEVER say "I cannot plan this" or "please try again later". Always deliver something useful.
- If a tool returns an error, silently try a different approach or use your own knowledge to provide the best answer.
- NEVER describe your internal steps ("I will now...", "The search failed..."). Deliver the result directly.
- If geocoding fails, use well-known coordinates from your training data.
- If route search fails, suggest a route based on your knowledge of the region.
- Structure results clearly with Markdown.
- CRITICAL: Your response MUST contain proper newlines between all Markdown elements (headings, table rows, list items, paragraphs). Each table row MUST be on its own line. Without newlines, the Markdown cannot be rendered correctly.
- Respond ONLY in {lang_name}.
- To display a route on the map, call `mcp_osrm_calculate_car_route` with waypoint coordinates. Without this call, no map will be shown. Do NOT use `mcp_openrouteservice_driving_time` for route display — it only returns distance/duration without geometry.

## Tool Efficiency Rules — CRITICAL

- ALWAYS batch multiple independent tool calls in a SINGLE response. For example, geocode ALL waypoints at once, not one per turn.
- You have a HARD LIMIT of 25 tool-calling turns. Plan efficiently.
- Use `mcp_tavily_web_search` SPARINGLY — max 2-3 searches total per request. Prefer your training knowledge for general travel info.
- Do NOT search for hotels, restaurants, beaches, museums separately per city. Use ONE broad search or your own knowledge.
- For a multi-stop road trip: geocode all stops → calculate all driving times → get 1-2 wikivoyage articles → produce the final answer. That's 4-5 turns, not 25.
- NEVER call the same tool with the same arguments twice.

## Available Tools
{tool_list_str}

## Template Selection

Detect the tour type from the user input and use the matching template:
- Cycling tour → "Bike Tour Output Template"
- Road trip → "Roadtrip Output Template"
- Hiking → Use a sensible Markdown structure (no dedicated template available)

Follow the chosen template structure strictly.
"""

    # Load steering files (no sanitization needed)
    parts: list[str] = [base_prompt]
    loaded_count = 0
    for path in _select_files(user_message):
        if path.exists():
            content: str = path.read_text(encoding="utf-8")
            # Strip YAML front matter
            if content.startswith("---"):
                end: int = content.find("---", 3)
                if end != -1:
                    content = content[end + 3 :].strip()
            parts.append(content)
            loaded_count += 1
            logger.debug("Loaded steering file: %s", path.name)
        else:
            logger.debug("Steering file not found: %s", path)

    prompt = "\n\n---\n\n".join(parts)
    logger.info("System prompt built: %d files loaded, %d chars total", loaded_count, len(prompt))
    return prompt
