# Trip Planner App

AI-powered tour planner — FastAPI backend with OpenRouter LLM + Vue 3 frontend.

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20+ with npm
- OpenRouter API key from [openrouter.ai](https://openrouter.ai/keys)
- ORS API key from [openrouteservice.org](https://openrouteservice.org/dev/#/signup) (for geocoding)

## Setup

```bash
# Backend
cd app/backend
cp .env.example .env
# Edit .env with your API keys
uv sync

# Frontend
cd app/frontend && npm install
```

## Environment Variables

API keys are loaded from **two locations** (in order):

1. **`~/.env`** — Personal API keys (not in git, shared across projects)
2. **`project/.env`** — Project-specific overrides (gitignored)

Project `.env` values **override** home `~/.env` if both define the same key.

### Required Variables

| Variable             | Used by | Description        |
| -------------------- | ------- | ------------------ |
| `OPENROUTER_API_KEY` | Backend | OpenRouter API key |

### Optional Variables

| Variable          | Used by                 | Description                                             |
| ----------------- | ----------------------- | ------------------------------------------------------- |
| `LLM_MODEL`       | Backend                 | Model ID (default: `meta-llama/llama-3.3-70b-instruct`) |
| `ORS_API_KEY`     | MCP (ors)               | OpenRouteService geocoding                              |
| `TAVILY_API_KEY`  | MCP (tavily, travel-\*) | Web search                                              |
| `SERPAPI_API_KEY` | MCP (serpapi-flights)   | Google Flights search                                   |

### Setup

```bash
# Option 1: Personal keys in home directory (recommended)
echo "OPENROUTER_API_KEY=sk-or-v1-..." >> ~/.env
echo "TAVILY_API_KEY=tvly-..." >> ~/.env

# Option 2: Project-specific overrides
cp app/backend/.env.example .env
# Edit .env with project-specific values
```

## Development

Run in separate terminals:

```bash
# Backend (port 8000)
cd app/backend && uv run python -m uvicorn main:app --reload
```

```bash
# Frontend (port 5173, proxies /api → backend)
cd app/frontend && npm run dev
```

Open http://localhost:5173.

## Production

```bash
# Docker
cd app && docker build -t trip-planner .
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=your-key \
  -e ORS_API_KEY=your-key \
  trip-planner

# Without Docker
cd app/frontend && npm run build
cd app/backend && uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Configuration

See **Environment Variables** section above for full details.

## Structure

```
app/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, router includes
│   ├── i18n.py              # UI translations
│   ├── app/routes/          # API endpoints
│   │   ├── chat.py          # POST /api/chat (SSE streaming)
│   │   ├── sessions.py      # Session management
│   │   ├── tours.py         # Tour CRUD + GPX
│   │   ├── trash.py         # Soft delete / restore
│   │   └── health.py        # Health check
│   ├── core/                # Business logic
│   │   ├── agent.py         # pydantic-ai agent with tool calling
│   │   ├── mcp_manager.py   # MCP subprocess management
│   │   ├── model_gateway.py # OpenRouter LLM configuration
│   │   └── steering.py      # Tour-type detection + prompts
│   ├── storage/             # Data layer
│   │   ├── db.py            # SQLite schema and operations
│   │   └── tour_storage.py  # Filesystem + trash
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.vue              # Main layout
│   │   ├── api.ts               # API client
│   │   ├── i18n.ts              # UI translations (de/en)
│   │   ├── composables/
│   │   │   └── useChat.ts       # Chat state management
│   │   └── components/
│   │       ├── ChatInput.vue    # Message input
│   │       ├── TourContent.vue  # Markdown rendering
│   │       ├── TourLibrary.vue  # Sidebar with tour list
│   │       └── TourMap.vue      # Leaflet map
│   ├── vite.config.ts    # Dev proxy to backend
│   └── package.json
└── Dockerfile            # Multi-stage: node build → python serve
```

## API

| Method | Path                           | Description                |
| ------ | ------------------------------ | -------------------------- |
| POST   | `/api/chat`                    | Send prompt, receive SSE   |
| GET    | `/api/sessions`                | List chat sessions         |
| GET    | `/api/tours`                   | List saved tours           |
| GET    | `/api/tours/{type}/{slug}`     | Get tour detail (markdown) |
| GET    | `/api/tours/{type}/{slug}/gpx` | Download GPX file          |
| GET    | `/api/health`                  | Health check               |

## Architecture

The backend uses pydantic-ai with OpenRouter for LLM access (supporting 100+ models including Llama, Claude, Gemini). The agent loop iterates: prompt → tool calls → results → final markdown response, streamed via SSE.

Steering files from `.kiro/steering/` are loaded based on detected tour type:

- **Bike** keywords → `user-preferences.md` + `bike-planning.md` + `bike-template.md`
- **Road** keywords → `user-preferences.md` + `road-planning.md` + `road-template.md`

Tours are persisted in SQLite (metadata) + filesystem (markdown, GPX, maps).

The frontend renders Markdown using [marked](https://github.com/markedjs/marked) + [DOMPurify](https://github.com/cure53/DOMPurify). Routes are displayed on a Leaflet map. The Tour Library sidebar shows saved tours from `trips/`.

## Key Dependencies

### Backend

- **pydantic-ai** — Agent framework with tool calling
- **FastAPI** — Async web framework with SSE
- **aiosqlite** — Async SQLite access

### Frontend

- **Vue 3** — Reactive UI (Composition API)
- **marked** — Markdown → HTML
- **Leaflet** — Interactive maps
- **Tailwind CSS** — Utility-first styling
