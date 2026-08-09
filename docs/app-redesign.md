# App Redesign — Agentic Backend & Modern Frontend

- **System:** Gerrit on Tour — AI Trip Planner
- **Document Version:** 3.0.0
- **Date:** August 2026
- **Status:** Implemented
- **Author:** Kiro (Claude Opus 4.5)

---

## 1. Objective

Transform the app into a **provider-agnostic architecture** with **LLM flexibility via pydantic-ai**, **SQLite persistence**, and an **improved frontend with Tour Library**.

### Core Features (Implemented)

| Feature                  | Description                                         | Status |
| ------------------------ | --------------------------------------------------- | ------ |
| **LLM Agnostic**         | pydantic-ai + LiteLLM for provider switching        | Done   |
| **SQLite Persistence**   | Sessions, Messages, Tours — no data loss on restart | Done   |
| **Tour Library**         | Sidebar with saved tours from `trips/`              | Done   |
| **Frontend Composables** | Clean separation of concerns with `useChat()`       | Done   |
| **Zero Adaptation**      | Same steering files and MCP servers as Kiro         | Done   |

---

## 2. Architecture Overview

### 2.1 Single-Agent Architecture (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Endpoints                        │
│   /api/chat  /api/sessions  /api/tours  /api/health         │
├─────────────────────────────────────────────────────────────┤
│                    Agent (pydantic-ai)                      │
│            (SSE streaming, tool calling, synthesis)         │
│                                                             │
│  Uses MCPManager for tool execution                         │
│  Uses steering.py for tour-type-specific prompts            │
├─────────────────────────────────────────────────────────────┤
│                    Model Gateway                            │
│         pydantic-ai infer_model() → provider:model          │
│         google:gemini-2.5-flash │ openai:gpt-4o-mini │ ...  │
├─────────────────────────────────────────────────────────────┤
│                    SQLite (data/app.db)                     │
│         sessions │ messages │ tours                         │
├─────────────────────────────────────────────────────────────┤
│                    MCPManager                               │
│         13 MCP servers via JSON-RPC subprocess              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Overview

| Component         | File               | Description                             |
| ----------------- | ------------------ | --------------------------------------- |
| **Model Gateway** | `model_gateway.py` | Provider-agnostic model creation        |
| **Agent**         | `agent.py`         | pydantic-ai agent with manual tool loop |
| **Steering**      | `steering.py`      | Load tour-type-specific prompts         |
| **Database**      | `db.py`            | SQLite schema and async CRUD operations |
| **Tour Storage**  | `tour_storage.py`  | Filesystem + SQLite hybrid tour storage |
| **MCP Manager**   | `mcp_manager.py`   | MCP server subprocess management        |
| **API**           | `main.py`          | FastAPI endpoints and SSE streaming     |

---

## 3. LLM Provider Configuration

### 3.1 Environment Variables

```bash
# .env configuration
LLM_PROVIDER=google          # google, openai, anthropic
LLM_MODEL=gemini-2.5-flash   # Model name (provider-specific)

# API Keys (set the one matching your provider)
GEMINI_API_KEY=...           # For google provider
OPENAI_API_KEY=...           # For openai provider
ANTHROPIC_API_KEY=...        # For anthropic provider
```

### 3.2 Model Gateway

```python
# model_gateway.py
from pydantic_ai import infer_model

PROVIDER_MODELS = {
    "google": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",
}

def get_model():
    provider = os.getenv("LLM_PROVIDER", "google")
    model = os.getenv("LLM_MODEL") or PROVIDER_MODELS.get(provider)
    model_string = f"{provider}:{model}"
    return infer_model(model_string)
```

### 3.3 Supported Providers

| Provider      | Model String Format    | Example                      |
| ------------- | ---------------------- | ---------------------------- |
| **Google**    | `google:model-name`    | `google:gemini-2.5-flash`    |
| **OpenAI**    | `openai:model-name`    | `openai:gpt-4o-mini`         |
| **Anthropic** | `anthropic:model-name` | `anthropic:claude-haiku-4-5` |

---

## 4. SQLite Schema

### 4.1 Tables

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    language TEXT NOT NULL DEFAULT 'de',
    tour_type TEXT,  -- 'bike', 'road', or NULL
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Tours table (metadata only, content in filesystem)
CREATE TABLE tours (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    title TEXT NOT NULL,
    tour_type TEXT NOT NULL,  -- 'bike' or 'road'
    slug TEXT NOT NULL UNIQUE,
    summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);
```

### 4.2 Tour Storage Strategy

Tours are stored as a **hybrid** of SQLite (metadata) and filesystem (content):

```
trips/
├── bike/{slug}/
│   ├── index.md      # Tour description
│   ├── gpx/route.gpx # GPX track
│   └── maps/         # Map images
└── road/{slug}/
    ├── index.md
    ├── gpx/*.gpx
    └── maps/
```

**Benefits:**

- Zero Adaptation with Kiro workflow
- GPX files directly usable with bike computers
- Fast listing via SQLite index
- Auto-sync of existing tours on startup

---

## 5. API Endpoints

### 5.1 Chat

```
POST /api/chat
Content-Type: application/json

{
  "message": "Plan a bike tour to Potsdam",
  "session_id": "optional-uuid",  // Auto-generated if omitted
  "language": "de"                // "de" or "en"
}

Response: SSE stream with events:
  - session: {session_id}
  - status: {message}
  - map: {waypoints, route, pois}
  - elevation: {profile}
  - gpx: {gpx content}
  - tour: {markdown}
  - error: {error message}
  - done: {iterations}
```

### 5.2 Sessions

```
GET /api/sessions?limit=50
→ [{id, title, language, tour_type, created_at, updated_at}, ...]

GET /api/sessions/{session_id}
→ {id, title, language, tour_type, created_at, updated_at, messages: [...]}
```

### 5.3 Tour Library

```
GET /api/tours?tour_type=bike
→ [{id, title, tour_type, slug, summary, created_at, updated_at}, ...]

GET /api/tours/{tour_type}/{slug}
→ {id, title, tour_type, slug, summary, markdown, has_gpx, ...}

GET /api/tours/{tour_type}/{slug}/gpx
→ GPX file (application/gpx+xml)

POST /api/tours
Content-Type: application/json
{
  "markdown": "# Tour Title\n...",
  "tour_type": "bike",
  "gpx": "<?xml ...",
  "session_id": "optional"
}
→ {id, title, tour_type, slug, created_at}
```

### 5.4 Health

```
GET /api/health
→ {
    "status": "ok",
    "providers": {
      "google": true,
      "openai": false,
      "anthropic": false
    }
  }
```

---

## 6. Frontend Structure

### 6.1 Components

```
app/frontend/src/
├── App.vue                    # Main layout with sidebar
├── api.ts                     # API client functions
├── i18n.ts                    # Internationalization
├── composables/
│   └── useChat.ts             # Chat state management
└── components/
    ├── ChatInput.vue          # Message input
    ├── TourContent.vue        # Markdown + GPX download
    ├── TourLibrary.vue        # Sidebar with tour list
    └── TourMap.vue            # Leaflet map + elevation
```

### 6.2 useChat Composable

```typescript
export function useChat(): ChatState {
  const tourMarkdown = ref("");
  const gpxContent = ref("");
  const isLoading = ref(false);
  const errorMessage = ref("");
  const statusMessages = ref<string[]>([]);
  const mapData = ref<MapData>({ waypoints: [], routes: [], pois: [], elevation: [] });
  const sessionId = ref<string | null>(null);

  async function sendMessage(message: string, language: Lang): Promise<void>;
  async function loadTour(tour: Tour): Promise<void>;
  function clearError(): void;
  function reset(): void;

  return { tourMarkdown, gpxContent, isLoading, ..., sendMessage, loadTour, ... };
}
```

### 6.3 TourLibrary Sidebar

- Collapsible sidebar with filter tabs (All / Bike / Road)
- Auto-loads tours from API on mount
- Click to load tour into main view
- Refresh button to reload tour list

---

## 7. Development Workflow

### 7.1 Running Locally

```bash
# Backend
cd app/backend
uv sync  # Install dependencies
uv run uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd app/frontend
npm install
npm run dev  # Vite on :5173, proxies /api → :8000
```

### 7.2 Environment Setup

```bash
# Copy example and configure
cp app/backend/.env.example app/backend/.env

# Edit .env with your API key
LLM_PROVIDER=google
GEMINI_API_KEY=your-key-here
```

### 7.3 Database Location

```
app/backend/data/app.db  # SQLite database (git-ignored)
```

---

## 8. Migration from Previous Version

### 8.1 Removed Dependencies

```diff
- "google-genai>=1.0.0"        # Gemini-specific SDK
```

### 8.2 Added Dependencies

```diff
+ "pydantic-ai>=0.2.0"         # Agent framework
+ "litellm>=1.75.0"            # Provider abstraction
+ "aiosqlite>=0.20.0"          # Async SQLite
```

### 8.3 File Changes

| Action  | File                | Description                             |
| ------- | ------------------- | --------------------------------------- |
| New     | `model_gateway.py`  | Provider-agnostic model access          |
| New     | `db.py`             | SQLite schema and operations            |
| New     | `tour_storage.py`   | Filesystem + SQLite storage             |
| Rewrite | `agent.py`          | pydantic-ai based agent                 |
| Update  | `steering.py`       | Fixed paths to `.kiro/steering/travel/` |
| Update  | `main.py`           | Session persistence, tour API           |
| New     | `api.ts` (frontend) | API client                              |
| New     | `TourLibrary.vue`   | Sidebar component                       |
| New     | `useChat.ts`        | Chat composable                         |

---

## 9. Future Extensions

### 9.1 Multi-Agent Architecture

The current single-agent approach works well for most use cases. For complex multi-day trips or when specialized reasoning is needed, a multi-agent architecture could be beneficial.

**Proposed Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    OrchestratorAgent                            │
│            (Request analysis, delegation, synthesis)            │
│  ┌─────────────────────────┬─────────────────────────────────┐ │
│  │      RouteAgent         │      EnrichmentAgent            │ │
│  │  • geocode              │  • search_pois                  │ │
│  │  • calculate_route      │  • get_weather                  │ │
│  │  • render_map           │  • search_transit               │ │
│  │                         │  • get_travel_guide             │ │
│  └─────────────────────────┴─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Agent Roles:**

| Agent               | Responsibility                         | Tools       |
| ------------------- | -------------------------------------- | ----------- |
| **Orchestrator**    | Parse request, coordinate, synthesize  | None        |
| **RouteAgent**      | Geocoding, routing, maps, elevation    | 4 MCP tools |
| **EnrichmentAgent** | POIs, weather, transit, travel content | 9 MCP tools |

**Benefits:**

- Focused context per agent (fewer tools = better tool selection)
- Parallel execution of independent tasks
- Specialized prompts per agent role

**Implementation Steps:**

1. Create `agents/` directory with orchestrator, route, enrichment modules
2. Define structured output types with Pydantic models
3. Implement agent handoff via pydantic-ai's multi-agent support
4. Add SSE events for agent status visualization

**Estimated Effort:** 2-3 days

### 9.2 Additional Providers

pydantic-ai supports many providers through `infer_model()`:

```python
# Add to PROVIDER_MODELS in model_gateway.py
"bedrock": "anthropic.claude-v2",
"azure": "azure/gpt-4-turbo",
"groq": "groq/llama-3-70b",
```

### 9.3 Multi-User Support

The database schema is prepared for multi-user extension:

```sql
-- Add user_id to sessions and tours
ALTER TABLE sessions ADD COLUMN user_id TEXT;
ALTER TABLE tours ADD COLUMN user_id TEXT;

-- Add users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TEXT NOT NULL
);
```

### 9.4 Tour Collaboration

- Share tours with other users
- Collaborative editing
- Tour reviews and ratings

---

## 10. Changelog

### v3.0.0 (August 2026)

**Breaking Changes:**

- Removed `google-genai` dependency
- New agent.py implementation (not compatible with previous version)

**New Features:**

- LLM provider switching via environment variables
- SQLite persistence for sessions, messages, and tours
- Tour Library sidebar in frontend
- Auto-sync of existing tours from `trips/` directory

**Improvements:**

- Frontend refactored with `useChat()` composable
- Cleaner API with dedicated tour endpoints
- Better error handling and SSE event structure

**Fixes:**

- Steering file paths now correctly point to `.kiro/steering/travel/`
