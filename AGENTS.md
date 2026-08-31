# Tour Pilot — AI Context

## Scope

- `trips/**` = travel-planning content
- `app/**` and `mcp/**` = product and development context

## Planning modes

- The primary travel-planning workflow is the chat; evaluate it directly against the relevant `AGENTS.md`, `SKILL.md`, context files, and MCP capabilities.
- `app/**` is a separate proprietary spin-off that derives its workflow from these files. App-specific agent filters and implementation limits do not restrict the primary chat workflow.

## Context imports

Keep subfolder AGENTS files short and import the relevant context file:

- `trips/AGENTS.md` → `@context/travel/user-preferences.md`
- `trips/bike/AGENTS.md` → `@context/travel/bike/bike-preferences.md`
- `trips/road/AGENTS.md` → `@context/travel/road/road-preferences.md`
- `app/AGENTS.md` → `@context/dev/app.md`
- `mcp/AGENTS.md` → `@context/dev/mcp.md`

## Commit rules

Use Conventional Commits in English:

- format: `<type>(<scope>): <short summary>`
- types: `feat`, `fix`, `docs`, `refactor`, `chore`, `style`, `test`, `ci`
- lowercase, imperative mood, max 70 chars, no trailing period

When the user says “commit”, run `git add -A` and commit immediately.

## Python

Use the project virtual environment for Python commands:

```bash
.venv/bin/python ...
```

Do not use system Python for repo scripts.
