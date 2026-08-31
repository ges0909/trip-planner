---
inclusion: fileMatch
fileMatchPattern: ["mcp/**"]
---

# MCP Server Development Guide

Guidelines for developing MCP servers in this project.

Keep this document high-level. It should describe project rules, not lock every server into one implementation style.

## Core rules

- Use FastMCP as the default MCP framework.
- Keep each server self-contained under `mcp/<name>/`.
- Use `uv` for dependency management and local execution.
- Prefer one clear entrypoint per server (`server.py`) with `@mcp.tool()` functions.
- Keep external API calls isolated and testable when possible.
- Validate inputs early and return readable error messages.
- Keep tool descriptions specific enough for the LLM to understand the parameters.
- Prefer Markdown-formatted outputs for human-readable results.

## Project conventions

- Server directories use kebab-case, matching the service name.
- Use project-root `.env` for API keys; do not hardcode secrets.
- Do not add `"env"` blocks to `.mcp.json` for keys stored in `.env`.
- Keep server behavior predictable and easy to debug.
- Write tests for real behavior, not only mock behavior.

## Typical structure

Most servers follow this pattern, but it is a convention rather than a strict template:

```text
mcp/<name>/
├── server.py
├── <helper>.py
├── pyproject.toml
├── tests/
└── README.md   # optional, but useful for usage notes
```

A server may either:

- keep API logic in a separate module,
- keep helper code in `server.py`, or
- use a language-specific SDK when it makes the integration cleaner.

The important point is not the exact layout, but clarity and maintainability.

## Installation and run pattern

```bash
cd mcp/<name> && uv sync
cd mcp/<name> && uv run pytest
cd mcp/<name> && uv run python server.py
```

This is the project default, and it is usually safer than relying on a framework-specific CLI wrapper.

## Good default design

A good default is:

- `server.py` = MCP tool declarations, validation, user-facing formatting
- helper/client module = API calls, auth, parsing, and raw response handling
- tests = async tests for the real integration surface

That said, the repo already contains valid exceptions, and they should not be treated as violations.

## What to avoid

- Over-prescribing one exact folder structure or import style
- Treating one implementation pattern as the only correct approach
- Returning unformatted API dumps directly to the LLM
- Hardcoding secrets or environment-specific values into server code
- Putting repo-level architecture rules in a way that prevents legitimate SDK-based or helper-based implementations

## Rule of thumb

Keep the guidance broad enough to allow clean engineering, but specific enough to keep the MCP servers consistent and understandable.

If a pattern is useful and clear, document it. If it is just one valid implementation, leave it as a convention, not a requirement.
