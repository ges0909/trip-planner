"""pydantic-ai based agent with MCP tool integration and SSE event streaming.

Coordinates the LLM turn loop, tool execution, and real-time frontend streaming.
"""

import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

import logfire
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

from core.agent_context import AgentContext, SSEEvent
from core.compaction import (
    MAX_CHAT_HISTORY_MESSAGES,
    MAX_RESPONSE_TOKENS,
    MAX_TOOL_RESULT_CHARS,
    _compact_messages,
    _compact_tool_declarations,
    _select_tool_declarations,
)
from core.context import _detect_tour_type, build_system_prompt
from core.geo_events import (
    GEO_POI_PATTERNS,
    GEO_POINT_PATTERNS,
    GEO_ROUTE_PATTERNS,
    _is_geocode_tool,
    _is_poi_tool,
    _is_route_tool,
    _process_tool_result,
)
from core.mcp_manager import MCPManager
from core.model_gateway import get_model, get_model_chain
from core.tool_metadata import get_status_categories

logger = logging.getLogger(__name__)

TOUR_SERVER_GROUPS = {
    "bike": [
        "brouter",
        "open-meteo",
        "vbb",
        "overpass",
        "ors",
        "waymarkedtrails",
        "tavily",
        "wikivoyage",
    ],
    "road": [
        "osrm",
        "open-meteo",
        "ors",
        "wikivoyage",
        "tavily",
        "serpapi-flights",
        "travel-content",
    ],
    "general": ["open-meteo", "ors", "wikivoyage", "tavily"],
}

# Re-exports for backwards compatibility with test fixtures
__all__ = [
    "GEO_POINT_PATTERNS",
    "GEO_POI_PATTERNS",
    "GEO_ROUTE_PATTERNS",
    "AgentContext",
    "SSEEvent",
    "_compact_messages",
    "_is_geocode_tool",
    "_is_poi_tool",
    "_is_route_tool",
    "run_agent",
]


def _build_initial_messages(
    user_message: str,
    chat_history: list[dict[str, str]],
    system_prompt: str,
) -> list[ModelMessage]:
    """Construct the initial message list from system prompt, history, and user input."""
    messages: list[ModelMessage] = [ModelRequest(parts=[SystemPromptPart(content=system_prompt)])]

    # Include recent chat history (limited to avoid huge prompts)
    recent_history = chat_history[-MAX_CHAT_HISTORY_MESSAGES:]
    for hist in recent_history:
        role = hist.get("role", "")
        content = hist.get("content", "")
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=content)]))

    # Add current user message
    messages.append(ModelRequest(parts=[UserPromptPart(content=user_message)]))
    return messages


def _gemini_decl_to_tool_def(decl: dict[str, Any]) -> ToolDefinition:
    """Convert Gemini-style FunctionDeclaration to pydantic-ai ToolDefinition."""
    params = decl.get("parameters", {})
    return ToolDefinition(
        name=decl["name"],
        description=decl.get("description", ""),
        parameters_json_schema=params if params else {"type": "object", "properties": {}},
    )


async def _execute_model_request(
    model: Any,
    messages: list[ModelMessage],
    tool_defs: list[ToolDefinition],
    model_settings: ModelSettings,
    model_id: str,
    iteration: int,
    lang: Lang,
) -> tuple[Any | None, SSEEvent | None]:
    """Execute a single model request with Logfire span tracking."""
    with logfire.span(
        "Model Request (Iteration {iteration})",
        iteration=iteration + 1,
        model_id=model_id,
    ) as req_span:
        try:
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

            # Record token usage attributes
            usage = getattr(response, "usage", None)
            if usage and getattr(usage, "total_tokens", None):
                req_span.set_attribute("input_tokens", usage.input_tokens)
                req_span.set_attribute("output_tokens", usage.output_tokens)
                req_span.set_attribute("total_tokens", usage.total_tokens)
                logger.info(
                    "Iteration %d: %d tokens (%d input, %d output)",
                    iteration + 1,
                    usage.total_tokens,
                    usage.input_tokens,
                    usage.output_tokens,
                )
            return response, None

        except Exception as e:
            logger.error("Model request failed: %s: %s", type(e).__name__, e)
            req_span.record_exception(e)
            error_str = str(e).lower()
            if any(k in error_str for k in ("402", "429", "quota", "credit", "rate")):
                return None, {
                    "event": "error",
                    "data": {"error": i18n_msg("quota_exhausted", lang)},
                }
            elif "503" in error_str or "500" in error_str:
                return None, {
                    "event": "error",
                    "data": {"error": i18n_msg("server_unavailable", lang, code="503")},
                }
            return None, {
                "event": "error",
                "data": {"error": i18n_msg("unexpected_error", lang, detail=str(e))},
            }


async def _execute_tool_calls(
    tool_calls: list[ToolCallPart],
    mcp: MCPManager,
    ctx: AgentContext,
    tool_return_parts: list[ToolReturnPart],
) -> AsyncGenerator[SSEEvent]:
    """Execute all tool calls in a turn, yield progress/geo events, and populate return parts."""
    # Emit status messages for tool categories
    call_names = [tc.tool_name for tc in tool_calls]
    for category_key in get_status_categories(call_names):
        ctx.emit_status(category_key)

    for evt in ctx.drain_events():
        yield evt

    for tc in tool_calls:
        tool_name = tc.tool_name
        tool_args = tc.args if isinstance(tc.args, dict) else {}
        tool_call_id = tc.tool_call_id

        logger.info("Tool call: %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False)[:150])
        yield {"event": "tool", "data": {"name": tool_name}}

        with logfire.span(
            "Tool: {tool_name}", tool_name=tool_name, tool_args=tool_args
        ) as tool_span:
            try:
                result = await mcp.call_tool(tool_name, tool_args)
                result = _process_tool_result(tool_name, tool_args, result, ctx)

                for evt in ctx.drain_events():
                    yield evt

                result_str = json.dumps(result, ensure_ascii=False, default=str)
                if len(result_str) > MAX_TOOL_RESULT_CHARS:
                    logger.info(
                        "Truncating %s result from %d to %d chars",
                        tool_name,
                        len(result_str),
                        MAX_TOOL_RESULT_CHARS,
                    )
                    result_str = result_str[:MAX_TOOL_RESULT_CHARS] + '..."}'

            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                tool_span.record_exception(e)
                result_str = json.dumps({"error": str(e)})

        tool_return_parts.append(
            ToolReturnPart(
                tool_name=tool_name,
                content=result_str,
                tool_call_id=tool_call_id,
            )
        )


async def run_agent(
    user_message: str,
    chat_history: list[dict[str, str]],
    mcp: MCPManager,
    language: str = "de",
) -> AsyncGenerator[SSEEvent]:
    """Run the agent turn loop, streaming SSE events to the client."""
    ctx = AgentContext(language=language)
    lang = ctx.get_lang()

    # 1. Discover and prepare tools & system prompt
    declarations = await mcp.get_tool_declarations(
        TOUR_SERVER_GROUPS[_detect_tour_type(user_message)]
    )
    selected_decls = _select_tool_declarations(declarations, user_message)
    compacted_decls = _compact_tool_declarations(selected_decls)

    tool_names = [d["name"] for d in declarations]
    system_prompt = build_system_prompt(
        tool_names=tool_names,
        language=language,
        user_message=user_message,
    )

    messages = _build_initial_messages(user_message, chat_history, system_prompt)
    tool_defs = [_gemini_decl_to_tool_def(d) for d in compacted_decls]

    model_chain = get_model_chain()
    current_model_idx = 0
    model_id = model_chain[current_model_idx]
    model = get_model(model_id)
    model_settings = ModelSettings(max_tokens=MAX_RESPONSE_TOKENS, temperature=0.7)

    # 2. Main Agent Turn Loop
    max_iterations = 25
    recovery_count = 0
    max_recoveries = 2

    with logfire.span("Agent Plan: {message}", message=user_message[:60], lang=lang):
        for iteration in range(max_iterations):
            logger.info("Iteration %d: calling model %s", iteration + 1, model_id)
            messages = _compact_messages(messages, model_id)
            yield {
                "event": "model",
                "data": {"iteration": iteration + 1, "model_id": model_id},
            }

            response, error_event = await _execute_model_request(
                model=model,
                messages=messages,
                tool_defs=tool_defs,
                model_settings=model_settings,
                model_id=model_id,
                iteration=iteration,
                lang=lang,
            )
            if error_event:
                # Check if we can fallback to the next model in the chain
                if current_model_idx + 1 < len(model_chain):
                    current_model_idx += 1
                    previous_model_id = model_id
                    model_id = model_chain[current_model_idx]
                    logger.warning(
                        "Model %s failed. Falling back to alternative model %s (%d/%d)",
                        previous_model_id,
                        model_id,
                        current_model_idx + 1,
                        len(model_chain),
                    )
                    try:
                        model = get_model(model_id)
                        # Retry the current iteration with the fallback model
                        yield {
                            "event": "model",
                            "data": {"iteration": iteration + 1, "model_id": model_id},
                        }
                        response, error_event = await _execute_model_request(
                            model=model,
                            messages=messages,
                            tool_defs=tool_defs,
                            model_settings=model_settings,
                            model_id=model_id,
                            iteration=iteration,
                            lang=lang,
                        )
                    except Exception as fallback_err:
                        logger.error(
                            "Failed to initialize fallback model %s: %s", model_id, fallback_err
                        )

                if error_event:
                    yield error_event
                    return

            response_parts = response.parts if hasattr(response, "parts") else []
            tool_calls = [p for p in response_parts if isinstance(p, ToolCallPart)]
            text_parts = [p for p in response_parts if isinstance(p, TextPart)]

            # 3. Final response handling (no tool calls)
            if not tool_calls:
                final_text = "".join(p.content for p in text_parts if p.content)
                if not final_text and recovery_count < max_recoveries:
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

                heading_match = re.search(r"^#{1,3}\s+(.+)$", final_text, re.MULTILINE)
                route_name = heading_match.group(1).strip() if heading_match else "unnamed"
                logger.info("Tour generation complete: %s (%d chars)", route_name, len(final_text))

                for evt in ctx.drain_events():
                    yield evt

                yield {"event": "tour", "data": {"markdown": final_text}}
                yield {"event": "done", "data": {"iterations": iteration + 1}}
                return

            # 4. Tool calls execution
            logger.info("Iteration %d: %d tool call(s)", iteration + 1, len(tool_calls))
            messages.append(ModelResponse(parts=response_parts))

            # Run tool generator, capturing yielded SSE events and populating return parts
            tool_return_parts: list[ToolReturnPart] = []
            async for evt in _execute_tool_calls(tool_calls, mcp, ctx, tool_return_parts):
                yield evt

            messages.append(ModelRequest(parts=tool_return_parts))

        # Max iterations reached
        logger.warning("Max iterations (%d) reached", max_iterations)
        yield {"event": "error", "data": {"error": i18n_msg("max_iterations", lang)}}
