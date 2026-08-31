"""Pure HTTP client logic for web scraping with browser-like headers."""

import httpx
from bs4 import BeautifulSoup

# Realistic browser headers to avoid blocks
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


async def fetch_page(url: str, timeout: float = 30.0) -> dict:
    """Fetch a web page with browser-like headers.

    Returns raw HTML content or {"error": "..."} on failure.
    """
    if not url.startswith(("http://", "https://")):
        return {"error": "URL must start with http:// or https://"}

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        ) as client:
            response = await client.get(url)

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.reason_phrase}"}

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return {"error": f"Unexpected content type: {content_type}"}

        return {
            "html": response.text,
            "url": str(response.url),  # Final URL after redirects
            "status": response.status_code,
        }

    except httpx.TimeoutException:
        return {"error": f"Timeout after {timeout}s"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {e}"}


async def extract_text(url: str, selector: str | None = None) -> dict:
    """Fetch page and extract text content.

    Args:
        url: Page URL to fetch
        selector: Optional CSS selector to extract specific content.
                  If None, extracts main content heuristically.

    Returns dict with "text" key or {"error": "..."} on failure.
    """
    result = await fetch_page(url)
    if "error" in result:
        return result

    html = result["html"]
    soup = BeautifulSoup(html, "lxml")

    # Remove script, style, nav, footer elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    if selector:
        # Extract specific element
        elements = soup.select(selector)
        if not elements:
            return {"error": f"No elements found for selector: {selector}"}
        text = "\n\n".join(el.get_text(separator="\n", strip=True) for el in elements)
    else:
        # Heuristic: find main content area
        main = soup.find("main") or soup.find("article") or soup.find(id="content")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            # Fallback: body content
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else soup.get_text()

    # Clean up excessive whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    return {
        "text": text,
        "url": result["url"],
        "length": len(text),
    }


async def extract_links(url: str, selector: str | None = None) -> dict:
    """Fetch page and extract all links.

    Args:
        url: Page URL to fetch
        selector: Optional CSS selector to limit link extraction scope

    Returns dict with "links" list or {"error": "..."} on failure.
    """
    result = await fetch_page(url)
    if "error" in result:
        return result

    html = result["html"]
    soup = BeautifulSoup(html, "lxml")

    if selector:
        container = soup.select_one(selector)
        if not container:
            return {"error": f"No element found for selector: {selector}"}
    else:
        container = soup

    links = []
    for a in container.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        # Skip empty or anchor-only links
        if not href or href.startswith("#"):
            continue

        # Make relative URLs absolute
        if href.startswith("/"):
            from urllib.parse import urljoin

            href = urljoin(result["url"], href)

        links.append({"href": href, "text": text})

    return {
        "links": links,
        "url": result["url"],
        "count": len(links),
    }
