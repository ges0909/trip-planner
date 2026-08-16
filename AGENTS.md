# Gerrit on Tour — AI Context

Universal guidelines for all AI assistants in this repository.

## Repository Overview

**Gerrit on Tour** is an AI-powered travel planning tool serving two purposes:

1. **Personal Travel Planning** — Planning and documenting bike adn car tours
2. **Platform Development** — Developing a web app, MCP servers, and infrastructure

**Important:** This repository separates both contexts consistently:

- When working in `trips/**` → Travel planning context active (user perspective)
- When working in `app/**`, `mcp/**` → Development context active (developer perspective)

Context-specific rules live in `context/` and `skills/`, loaded automatically based on the files you work on and the task you are doing.

---

# Commit Messages

All git commits in this project use [Conventional Commits](https://www.conventionalcommits.org/) format. Language is always **English**, regardless of the conversation language.

## Format

```
<type>(<optional-scope>): <short summary>

<optional body>
```

## Subject Line Rules

- Imperative mood ("add feature", not "added feature")
- All lowercase, no trailing period
- Maximum 70 characters
- Must start with one of the allowed types
- Scope is optional but recommended for larger changes

## Allowed Types

| Type       | Use for                                     |
| ---------- | ------------------------------------------- |
| `feat`     | New functionality, new tours, new MCP tools |
| `fix`      | Bug fixes, corrected data, broken routes    |
| `docs`     | Documentation, READMEs, tour descriptions   |
| `refactor` | Code restructuring without behavior change  |
| `chore`    | Dependency updates, config changes, cleanup |
| `style`    | Formatting, whitespace, linting (no logic)  |
| `test`     | Adding or updating tests                    |
| `ci`       | CI/CD pipeline changes                      |

## Scopes

Optional, use when helpful for clarity. Common scopes:

| Scope      | Use for                          |
| ---------- | -------------------------------- |
| `mcp`      | MCP server changes (any server)  |
| `frontend` | Vue 3 frontend changes           |
| `backend`  | FastAPI backend changes          |
| `trip`     | Tour/trip content updates        |
| `docs`     | Documentation (concepts, guides) |
| `ci`       | CI/CD configuration              |

Examples: `feat(mcp): add elevation profile tool`, `docs(trip): update sardinia itinerary`

## Body

- Optional but encouraged for multi-file changes
- Bullet list, each line starting with `-`
- Keep lines under 80 characters
- Reference tour names, file names, or MCP server names when relevant

## Examples

```
feat(mcp): add elevation profile rendering to brouter

- implement render_elevation_profile tool
- add matplotlib dependency
- include property-based tests for chart output
```

```
docs(trip): update sardinia roadtrip with restaurant picks
```

```
fix: correct GPX coordinate ordering in bike routes
```

## Auto-Commit Behavior

When the user types **"commit"** (or equivalent like "committen", "einchecken"):

1. Generate a commit message following the rules above based on `git diff --staged` or working tree changes
2. Run `git add -A`
3. Run `git commit -m "<generated message>"` (with body via `-m` flag if needed)
4. Do **not** ask for confirmation — execute immediately
5. Do **not** push unless explicitly asked

---

## Context-Specific Rules

Context is split by *kind*, and all AI assistants (Kiro, Claude Code, Antigravity, Cursor) read the same files natively without symbolical links (symlinks):

All content lives in two vendor-neutral top-level directories, `steering/` and `skills/`.
No tool-specific duplicates or symlinks exist — `.mcp.json` and `.vscode/settings.json` point tools to the single source of truth.

**Preferences and conventions** — facts that apply whenever you work in a directory tree.
Root `AGENTS.md` defines global rules. Subfolder `AGENTS.md` files use native `@steering/...` imports:

| Content file (edit this) | Discovered as | Content |
| --- | --- | --- |
| `steering/travel/user-preferences.md` | `trips/AGENTS.md` | Universal travel preferences, home base, content integrity |
| `steering/travel/road/road-preferences.md` | `trips/road/AGENTS.md` | Roadtrip preferences (flights, interests, food) |
| `steering/travel/bike/bike-preferences.md` | `trips/bike/AGENTS.md` | Bike tour preferences (distance, terrain, Einkehr) |
| `steering/dev/app.md` | `app/AGENTS.md` | Web app architecture + coding guidelines (Vue 3 + FastAPI) |
| `steering/dev/mcp.md` | `mcp/AGENTS.md` | MCP server development guidelines |

**Workflows** — procedures loaded on demand when you actually plan a tour, not on every
file touch. Skills in the vendor-neutral top-level `skills/<name>/`, each with `SKILL.md`
plus `references/output-template.md`:

| Skill | Content |
| --- | --- |
| `skills/road-planner/` | Roadtrip workflow (ORS/OSRM, flights) + output template |
| `skills/bike-planner/` | Bike tour workflow (BRouter/VBB, Overpass) + output template |

Tools discover skills natively via `.vscode/settings.json` (`"chat.agentSkillsLocations": ["skills"]`) and standard root scanning.

A third consumer, `app/backend/core/steering.py`, assembles the same files into the web app's
system prompt, resolving the canonical `steering/` and `skills/` paths directly.

---

## Python Environment

This project uses a virtual environment at `.venv/`. When executing Python scripts:

```bash
# Correct — use venv interpreter directly
.venv/bin/python scripts/render_roadtrip_map.py ...

# Wrong — system Python may lack dependencies
python3 scripts/render_roadtrip_map.py ...
```

**Rule:** Always use `.venv/bin/python` for any Python script execution in this repository.
