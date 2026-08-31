"""Tavily API client used by the MCP server.

No FastMCP dependency — importable independently for testing.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import AsyncTavilyClient

# Load .env: Home first, then project (project overrides)
load_dotenv(Path.home() / ".env")
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
_client = AsyncTavilyClient(api_key=TAVILY_API_KEY or None)


async def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> dict:
    """Search the web via Tavily.

    Returns raw API response as dict, or {"error": "..."} on failure.
    """
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not configured"}

    if not query or len(query.strip()) < 3:
        return {"error": "query must be at least 3 characters"}

    query = query.strip()[:400]
    max_results = max(1, min(10, max_results))

    try:
        return await _client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
            include_raw_content=False,
        )
    except Exception as error:
        return {"error": f"Tavily request failed: {error}"}


async def web_extract(url: str) -> dict:
    """Extract main content from a URL via Tavily.

    Returns raw API response as dict, or {"error": "..."} on failure.
    """
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not configured"}

    if not url or not url.startswith(("http://", "https://")):
        return {"error": "url must start with http:// or https://"}

    try:
        return await _client.extract(urls=[url])
    except Exception as error:
        return {"error": f"Tavily request failed: {error}"}
