# 🗺️ Tour Pilot — AI-Powered Travel Planning

AI-powered tour planning with 14 custom MCP servers for routing, weather, POIs, public transit, and travel content. Plan complete bike tours and multi-day roadtrips through natural language prompts.

| Tour Type | Description                                         | Status |
| --------- | --------------------------------------------------- | ------ |
| Biking    | Day trips in Berlin/Brandenburg via regional trains | Active |
| Roadtrips | Multi-day car rental trips across Europe            | Active |

**→ [Biking Tours](trips/bike/README.md)** · **→ [Roadtrips](trips/road/README.md)**

---

## What It Does

Type a prompt like:

- _"Plan a 60 km bike tour through the Spreewald with swimming stops"_
- _"Plan a 10-day road trip along the northern Spanish coast"_

Get a complete tour plan:

- ✅ Route with GPX track, rendered map & synchronized elevation profile
- ✅ Accommodation recommendations (ratings, prices, booking links)
- ✅ POI photos with figure captions and responsive YouTube/Vimeo video embeds
- ✅ Hiking trails with ratings from AllTrails/Komoot
- ✅ Swimming spots, restaurants, museums, art galleries
- ✅ Weather forecast for travel dates
- ✅ Public transit connections (bike tours) or driving times (roadtrips)
- ✅ Dynamic LLM session title summarization (3–5 key words per prompt)
- ✅ Command Palette (`Cmd/Ctrl + K`) for instant search across tours & sessions
- ✅ Toast notifications & 1-click Markdown copy to clipboard
- ✅ Monokai Light & Dark themes (warm pergament & high-contrast dark mode)
- ✅ Markdown document ready to commit

The web app also keeps a session ID in the browser and restores the last viewed tour after reopening, so the user lands on the previously selected trip automatically.

All saved in `trips/bike/` or `trips/road/` with GPX files and map images.

---

## How It Works

Type a tour request → MCP servers fetch data (routing, weather, POIs, transit) → LLM plans & writes → Results saved as Markdown + GPX.

For the web UI, run `just dev` from the project root, then open http://localhost:5173. For the app-specific setup and feature list, see [app/README.md](app/README.md).

## Quickstart

### Prerequisites

- **Python:** 3.12+ (managed by [uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js:** 20+ (for frontend)
- **[just](https://github.com/casey/just):** 1.20+ (command runner with module support)
- **API Keys:** Loaded from two locations (in order):
  1. `~/.env` — Personal keys (shared across projects, not in git)
  2. `project/.env` — Project-specific overrides (gitignored)

  Project values override home if both define the same key.

```bash
# Option 1: Personal keys in home directory (recommended)
echo "OPENROUTER_API_KEY=your-key" >> ~/.env     # Required: https://openrouter.ai/keys
echo "ORS_API_KEY=your-key" >> ~/.env            # Free: https://openrouteservice.org/dev/#/signup
echo "TAVILY_API_KEY=your-key" >> ~/.env         # Free (1000 req/month): https://tavily.com
echo "SERPAPI_API_KEY=your-key" >> ~/.env        # Optional: https://serpapi.com (flight search)

# Option 2: Project-specific overrides
cp .env.example .env
# Edit .env with project-specific values
```

All other MCP servers use free/public APIs without keys.

### Use with Kiro

1. Install [Kiro](https://kiro.dev)
2. Open this project folder
3. Type your tour request in chat (e.g., _"Plan a bike tour from Berlin to Potsdam"_)
4. Results are saved in `trips/bike/` or `trips/road/`

MCP servers are auto-configured via `.mcp.json`.

---

## MCP Servers (14 Custom Tools)

Self-contained Python servers providing tour planning capabilities via [Model Context Protocol](https://modelcontextprotocol.io/):

| Server                                    | Purpose                                 | API / Data Source          | Key Required |
| ----------------------------------------- | --------------------------------------- | -------------------------- | ------------ |
| [`brouter`](mcp/brouter/)                 | Bike routing, map rendering, elevation  | BRouter + Nominatim        | No           |
| [`ors`](mcp/ors/)                         | Car/foot routing, isochrones, matrix    | OpenRouteService           | Yes          |
| [`osrm`](mcp/osrm/)                       | Car routing + GPX export                | OSRM (public)              | No           |
| [`open-meteo`](mcp/open-meteo/)           | Weather forecast + geocoding            | Open-Meteo                 | No           |
| [`vbb`](mcp/vbb/)                         | Public transit (Berlin/Brandenburg)     | VBB REST API               | No           |
| [`overpass`](mcp/overpass/)               | POI search along GPX routes             | OpenStreetMap Overpass API | No           |
| [`waymarkedtrails`](mcp/waymarkedtrails/) | Marked cycling routes                   | Waymarked Trails           | No           |
| [`wikivoyage`](mcp/wikivoyage/)           | Travel guides, destination search       | Wikivoyage                 | No           |
| [`tavily`](mcp/tavily/)                   | Web search (hotels, restaurants, etc.)  | Tavily Search API          | Yes          |
| [`serpapi-flights`](mcp/serpapi-flights/) | Flight search via Google Flights        | SerpAPI                    | Yes          |
| [`travel-content`](mcp/travel-content/)   | Travel article search + route tips      | Tavily (quality press)     | Yes          |
| [`travel-videos`](mcp/travel-videos/)     | Public broadcaster videos + transcripts | YouTube (ÖR channels)      | No           |
| [`web-scraper`](mcp/web-scraper/)         | General web page scraping               | HTTP requests              | No           |
| [`podcasts`](mcp/podcasts/)               | Travel podcast search + transcripts     | iTunes Search API          | No           |

**Architecture:** FastMCP + httpx, spawned as subprocesses via stdio JSON-RPC. Each server is self-contained with its own `pyproject.toml`.

---

## Project Structure

```
├── app/                      Web app (FastAPI backend + Vue 3 frontend)
├── mcp/                      14 MCP servers (14 Python packages)
├── context/                  Preferences (travel/, dev/) — Single Source of Truth
├── skills/                   Tour planning workflows (bike-planner/, road-planner/)
├── trips/                    Tour documents (bike/, road/ with AGENTS.md)
├── AGENTS.md                 Core AI rules
├── CLAUDE.md                 Claude Code instructions
├── .mcp.json                 MCP server registry
├── .env.example              API keys template
└── ruff.toml                 Linter config
```

---

## Development

```bash
just dev            # Start frontend (5173) and backend (8000) concurrently
just backend dev    # Start only the FastAPI backend
just frontend dev   # Start only the Vite frontend
just check          # Run full checks (linter, types, all tests)
just test           # Run backend and frontend test suites
just coverage       # Run backend tests with coverage report
just audit          # Run security audit on frontend dependencies
just audit-fix      # Automatically fix security vulnerabilities
just format         # Format Python and TypeScript files
```

For the web UI, run `just dev` and open http://localhost:5173. For the complete app documentation, see [app/README.md](app/README.md).

---

## Context Management

The project uses a **three-layer context system**, shared by Claude Code and the web app:

1. **`AGENTS.md`** (repo root) — Universal rules for all AI assistants (Conventional Commits, project overview)
2. **`context/`** (top level) — Preferences and conventions, loaded by path; surfaced to Claude Code as `AGENTS.md` symlinks in `trips/`, `trips/road/`, `trips/bike/`, `app/`, `mcp/`
3. **`skills/*/SKILL.md`** — Tour planning workflows, loaded on demand by task

Every file exists exactly once; edit the target, not symlink copies.

### AI Context Reference Map

Full hierarchy of AGENTS.md, SKILL.md files and their references:

```
trip-planner/
│
├── AGENTS.md (ROOT — Universal rules)
│   └── Defines: Conventional Commits, project overview
│
├── CLAUDE.md (Claude Code alias)
│   └── Imports: @AGENTS.md
│
├── trips/
│   ├── AGENTS.md (Travel Planning base)
│   │   └── Imports: @context/travel/user-preferences.md
│   │
│   ├── bike/
│   │   └── AGENTS.md (Bike tour context)
│   │       └── Imports: @context/travel/bike/bike-preferences.md
│   │
│   └── road/
│       └── AGENTS.md (Roadtrip context)
│           └── Imports: @context/travel/road/road-preferences.md
│
├── app/
│   └── AGENTS.md (Web app development)
│       └── Imports: @context/dev/app.md
│
├── mcp/
│   └── AGENTS.md (MCP server development)
│       └── Imports: @context/dev/mcp.md
│
├── skills/
│   ├── bike-planner/
│   │   └── SKILL.md
│   │       ├── YAML header: name=bike-planner, triggers on "bike tour", trips/bike/**
│   │       └── References: Bike tour workflow + output template
│   │
│   └── road-planner/
│       └── SKILL.md
│           ├── YAML header: name=road-planner, triggers on "roadtrip", trips/road/**
│           └── References: Roadtrip workflow + output template + scripts
│
└── context/ (Preferences — Single Source of Truth)
    ├── travel/
    │   ├── user-preferences.md (Home base, interests, content integrity)
    │   ├── bike/
    │   │   └── bike-preferences.md (Distance, terrain, food rules)
    │   └── road/
    │       └── road-preferences.md (Flights, hotels, hiking rules)
    │
    └── dev/
        ├── app.md (Vue 3 + FastAPI architecture)
        └── mcp.md (MCP server guidelines)
```

**Load mechanism:** Claude Code reads preferences via `AGENTS.md` symlinks in directory roots. The web app
assembles the same context in `app/backend/core/context.py`.
