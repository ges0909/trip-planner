# Tavily MCP Server

MCP server for web search and content extraction via the [Tavily API](https://tavily.com/). Requires an API key.

The API layer uses Tavily's official [`tavily-python`](https://pypi.org/project/tavily-python/)
SDK and its asynchronous client. The MCP layer keeps the result formatting and
input validation local.

## Tools

| Tool          | Description                              |
| ------------- | ---------------------------------------- |
| `web_search`  | Search the web for current information   |
| `web_extract` | Extract main content from a specific URL |

## Setup

1. Register at [tavily.com](https://tavily.com/) and get an API key
2. Add to `.env`:

   ```
   TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
   ```

3. Install dependencies:

   ```bash
   cd mcp/tavily
   uv sync
   ```

4. Enable in `mcp/servers.json`:

   ```json
   {
     "tavily": {
       "command": "uv",
       "args": ["run", "--directory", "mcp/tavily", "python", "server.py"]
     }
   }
   ```

## Usage Examples

Web search:

```
web_search("best cycling routes Brandenburg 2025")
web_search("ferry schedule Sardinia", search_depth="advanced")
```

Extract page content:

```
web_extract("https://example.com/article")
```

## Scope

Tavily returns cleaned, LLM-oriented page content. It does not replace the
[`web-scraper`](../web-scraper/) server for use cases that require raw HTML,
arbitrary CSS selectors, or direct link extraction.

## Costs and Rate Limits

Tavily requests consume API credits. The free plan and credit costs can change;
see the current [Tavily pricing and credits documentation](https://www.tavily.com/pricing)
before enabling frequent or automated searches.
