"""FastAPI backend for the Trip Planner web app.

Application entry point with lifespan management and router registration.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from app.routes import chat, health, sessions, tours, trash
from core.mcp_manager import MCPManager, build_server_configs
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from storage.db import init_db
from storage.tour_storage import sync_filesystem_to_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
# Priority: Project .env > Home ~/.env (project overrides home)
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(Path.home() / ".env")  # Personal API keys (not in git)
load_dotenv(PROJECT_ROOT / ".env", override=True)  # Project-specific overrides

# Module-level MCP manager instance
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    """Get the MCP manager instance. Raises if not initialized."""
    if _mcp_manager is None:
        raise RuntimeError("MCPManager not initialized")
    return _mcp_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and MCP manager."""
    global _mcp_manager

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Sync existing tours from filesystem to DB
    synced = await sync_filesystem_to_db()
    if synced:
        logger.info("Synced %d tours from filesystem to database", synced)

    # Initialize MCP manager
    configs = build_server_configs()
    _mcp_manager = MCPManager(configs)
    await _mcp_manager.discover_all_tools()
    logger.info(
        "MCP manager initialized with %d tool declarations",
        len(await _mcp_manager.get_tool_declarations()),
    )

    yield

    # Shutdown
    await _mcp_manager.shutdown()
    _mcp_manager = None
    logger.info("MCP manager shut down")


# Create FastAPI app
app = FastAPI(title="Gerrit on Tour API", lifespan=lifespan)

# Wire up MCP manager getter for chat route
chat.set_mcp_manager_getter(get_mcp_manager)

# Register routers
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(tours.router)
app.include_router(trash.router)
app.include_router(health.router)

# Serve frontend static files (production)
FRONTEND_DIST: Path = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving frontend from %s", FRONTEND_DIST)
