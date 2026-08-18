"""Tests for agent context compaction."""

from core.agent import _compact_messages
from pydantic_ai.messages import ModelRequest, SystemPromptPart, ToolReturnPart

MODEL_ID = "meta-llama/llama-3.3-70b-instruct"


def test_compacts_large_tool_result() -> None:
    messages = [
        ModelRequest(parts=[SystemPromptPart(content="system")]),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="search",
                    content="result " * 20000,
                    tool_call_id="call-1",
                )
            ]
        ),
    ]

    compacted = _compact_messages(messages, MODEL_ID)

    assert len(compacted[1].parts[0].content) < 200
    assert compacted[1].parts[0].tool_call_id == "call-1"


def test_keeps_small_tool_result_unchanged() -> None:
    result = "small result"
    messages = [
        ModelRequest(parts=[SystemPromptPart(content="system")]),
        ModelRequest(
            parts=[ToolReturnPart(tool_name="search", content=result, tool_call_id="call-1")]
        ),
    ]

    compacted = _compact_messages(messages, MODEL_ID)

    assert compacted[1].parts[0].content == result
