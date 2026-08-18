# Trip Planner App

AI-powered travel planning app with a FastAPI backend and a Vue 3 frontend for tour planning, session persistence, and itinerary browsing.

## Features

- AI chat flow for tour planning via SSE streaming
- Tour library and tour detail views for bike and road trips
- GPX download and route map rendering
- Soft-deletion and restore flow for tours
- Session persistence across browser restarts via a stored session ID and last-viewed tour tracking
- Tour metadata stored in SQLite; markdown and GPX content stored in the filesystem

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20+ with npm
- OpenRouter API key from [openrouter.ai](https://openrouter.ai/keys)
- ORS API key from [openrouteservice.org](https://openrouteservice.org/dev/#/signup) for geocoding and routing features

## Setup

```bash
# Backend
cd app/backend
uv sync

# Frontend
cd app/frontend
npm install
```

## Environment Variables

API keys are loaded from two locations, in priority order:

1. `~/.env` — personal credentials, not committed
2. `project/.env` — project-specific overrides

Project values override home values when both exist.

### Required Variables

| Variable             | Used by | Description        |
| -------------------- | ------- | ------------------ |
| `OPENROUTER_API_KEY` | Backend | OpenRouter API key |

### Optional Variables

| Variable          | Used by   | Description                            |
| ----------------- | --------- | -------------------------------------- |
| `LLM_MODEL`       | Backend   | Override model ID                      |
| `ORS_API_KEY`     | MCP (ORS) | OpenRouteService geocoding and routing |
| `TAVILY_API_KEY`  | MCP       | Web search support                     |
| `SERPAPI_API_KEY` | MCP       | Flight search support                  |

Example:

```bash
# personal setup
echo "OPENROUTER_API_KEY=sk-or-v1-..." >> ~/.env

# project override example
cp app/backend/.env.example .env
# edit .env with project-specific values
```

## Development

Run the backend and frontend in separate terminals:

```bash
# Backend (port 8000)
cd app/backend
uv run python -m uvicorn main:app --reload
```

```bash
# Frontend (port 5173, proxies /api to backend)
cd app/frontend
npm run dev
```

Open http://localhost:5173

## Production

```bash
# Frontend build
cd app/frontend
npm run build

# Backend production start
cd app/backend
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Docker is also supported from the root app directory:

```bash
cd app
docker build -t trip-planner .
docker run -p 8000:8000 -e OPENROUTER_API_KEY=your-key trip-planner
```

## App Structure

```text
app/
├── backend/
│   ├── main.py                # FastAPI app and startup/shutdown lifecycle
│   ├── i18n.py                # UI translations
│   ├── app/routes/
│   │   ├── chat.py            # POST /api/chat with SSE streaming
│   │   ├── sessions.py        # Session management + last viewed tour persistence
│   │   ├── tours.py           # Tour CRUD + GPX endpoints
│   │   ├── trash.py           # Soft delete/restore workflow
│   │   └── health.py          # Health check
│   ├── core/
│   │   ├── agent.py           # LLM agent orchestration
│   │   ├── mcp_manager.py     # MCP server lifecycle and tool routing
│   │   ├── model_gateway.py   # OpenRouter configuration
│   │   └── context.py         # Tour context and prompt assembly
│   ├── storage/
│   │   ├── db.py              # SQLite session/tour metadata
│   │   └── tour_storage.py    # Filesystem tour storage and DB sync
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.vue            # Main app shell and session restore logic
│   │   ├── api.ts             # API client helpers
│   │   ├── i18n.ts            # de/en translations
│   │   ├── composables/
│   │   │   └── useChat.ts     # Chat state and loading logic
│   │   └── components/
│   │       ├── ChatInput.vue
│   │       ├── TourContent.vue
│   │       ├── TourLibrary.vue
│   │       └── TourMap.vue
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── Dockerfile
└── README.md
```

## API overview

| Method | Path                             | Description                         |
| ------ | -------------------------------- | ----------------------------------- |
| POST   | `/api/chat`                      | Send prompt and receive SSE stream  |
| GET    | `/api/sessions`                  | List sessions                       |
| GET    | `/api/sessions/{id}`             | Get session details                 |
| GET    | `/api/sessions/{id}/last-viewed` | Load last viewed tour for a session |
| PUT    | `/api/sessions/{id}/last-viewed` | Save last viewed tour for a session |
| GET    | `/api/tours`                     | List saved tours                    |
| GET    | `/api/tours/{type}/{slug}`       | Fetch tour detail markdown          |
| GET    | `/api/tours/{type}/{slug}/gpx`   | Download GPX                        |
| DELETE | `/api/tours/{type}/{slug}`       | Move tour to trash                  |
| GET    | `/api/trash`                     | List trashed tours                  |
| GET    | `/api/health`                    | Health check                        |

## Architecture notes

The backend uses pydantic-ai with OpenRouter for LLM orchestration and MCP-based tool access. The app loads context files depending on detected tour type:

- Bike trips use bike-specific travel preferences and planning workflow
- Road trips use road-specific travel preferences and planning workflow
- General instructions remain in the common user preferences

Tours are persisted in SQLite for metadata and in the filesystem for markdown, GPX, and generated map assets.

Frontend features include Markdown rendering, route map display, and a sidebar-based tour library. Session IDs are kept in localStorage so the last selected trip can be restored after reopening the browser.

## Key dependencies

### Backend

- FastAPI
- pydantic-ai
- aiosqlite
- uvicorn

### Frontend

- Vue 3
- Vite
- Tailwind CSS
- Leaflet
