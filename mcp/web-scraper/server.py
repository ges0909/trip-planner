"""MCP server for fetching web pages that block standard tools.

Uses browser-like headers to bypass simple bot detection.
Extracts clean text content from HTML pages.

Usage:
    python server.py
"""

from fastmcp import FastMCP
from scraper import extract_links as _extract_links
from scraper import extract_text as _extract_text
from scraper import fetch_page as _fetch_page

mcp = FastMCP("Web Scraper")


@mcp.tool()
async def fetch_page(url: str) -> str:
    """Fetch a web page with browser-like headers.

    Use this for pages that block standard fetch tools (header overflow,
    bot detection, etc.). Returns raw HTML content.

    Args:
        url: Full URL to fetch (must start with http:// or https://)
    """
    if not url:
        return "Error: URL is required"

    data = await _fetch_page(url)

    if "error" in data:
        return f"Error: {data['error']}"

    html = data["html"]
    final_url = data["url"]

    # Truncate very long HTML
    max_chars = 50000
    truncated = ""
    if len(html) > max_chars:
        html = html[:max_chars]
        truncated = "\n\n[... HTML gekürzt, verwende extract_text für sauberen Text]"

    result = f"# Raw HTML von {final_url}\n\nLänge: {len(html)} Zeichen\n\n```html\n{html}\n```{truncated}"
    return result


@mcp.tool()
async def extract_text(url: str, selector: str | None = None) -> str:
    """Fetch a web page and extract clean text content.

    Removes scripts, styles, navigation, and other non-content elements.
    Best for reading article content, travel guides, etc.

    Args:
        url: Full URL to fetch (must start with http:// or https://)
        selector: Optional CSS selector to extract specific content.
                  Examples: "article", ".content", "#main", ".highlight-box"
                  If omitted, extracts main content heuristically.
    """
    if not url:
        return "Error: URL is required"

    data = await _extract_text(url, selector)

    if "error" in data:
        return f"Error: {data['error']}"

    text = data["text"]
    final_url = data["url"]
    length = data["length"]

    # Truncate very long content
    max_chars = 30000
    truncated = ""
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = "\n\n[... Inhalt gekürzt]"

    selector_info = f" (Selector: `{selector}`)" if selector else ""
    return f"# Inhalt von {final_url}{selector_info}\n\n**Länge:** {length} Zeichen\n\n---\n\n{text}{truncated}"


@mcp.tool()
async def extract_links(url: str, selector: str | None = None) -> str:
    """Fetch a web page and extract all links.

    Useful for finding subpages, navigation structure, or related content.

    Args:
        url: Full URL to fetch (must start with http:// or https://)
        selector: Optional CSS selector to limit link extraction scope.
                  Examples: "nav", ".menu", "#sidebar"
    """
    if not url:
        return "Error: URL is required"

    data = await _extract_links(url, selector)

    if "error" in data:
        return f"Error: {data['error']}"

    links = data["links"]
    final_url = data["url"]
    count = data["count"]

    if not links:
        return f"Keine Links gefunden auf {final_url}"

    lines = [f"# Links auf {final_url}", f"**Anzahl:** {count}", ""]

    for link in links[:100]:  # Limit to 100 links
        href = link["href"]
        text = link["text"][:80] if link["text"] else "(kein Text)"
        lines.append(f"- [{text}]({href})")

    if count > 100:
        lines.append(f"\n... und {count - 100} weitere Links")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
