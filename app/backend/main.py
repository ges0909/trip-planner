"""FastAPI backend for the Trip Planner web app.

Application entry point with lifespan management and router registration.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import logfire
from app.routes import chat, health, sessions, tours, trash
from core.config import FRONTEND_DIST, PROJECT_ROOT
from core.mcp_manager import MCPManager, build_server_configs
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from storage.db import init_db
from storage.tour_storage import sync_filesystem_to_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
# Priority: Project .env > Home ~/.env (project overrides home)
load_dotenv(Path.home() / ".env")  # Personal API keys (not in git)
load_dotenv(PROJECT_ROOT / ".env", override=True)  # Project-specific overrides

# Configure Logfire (send_to_logfire='if-token-present' logs locally to console
# and sends to Cloud only if LOGFIRE_TOKEN is set)
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_httpx()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and MCP manager."""
    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Sync existing tours from filesystem to DB
    synced = await sync_filesystem_to_db()
    if synced:
        logger.info("Synced %d tours from filesystem to database", synced)

    # Initialize MCP manager on app state
    configs = build_server_configs()
    mcp_manager = MCPManager(configs)
    app.state.mcp_manager = mcp_manager
    logger.info("MCP manager initialized; tool servers start on demand")

    yield

    # Shutdown
    if getattr(app.state, "mcp_manager", None):
        await app.state.mcp_manager.shutdown()
        app.state.mcp_manager = None
    logger.info("MCP manager shut down")


# Create FastAPI app
app = FastAPI(title="Tour Pilot API", lifespan=lifespan)
logfire.instrument_fastapi(app)

# CORS middleware for dev servers and local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(tours.router)
app.include_router(trash.router)
app.include_router(health.router)

# Serve frontend static files (production)
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving frontend from %s", FRONTEND_DIST)
