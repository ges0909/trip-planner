"""Central paths and configuration settings for the backend application."""

from pathlib import Path

# Base directories
BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent
PROJECT_ROOT: Path = BACKEND_ROOT.parent.parent

# Storage and Database paths
DB_DIR: Path = BACKEND_ROOT / "storage" / "data"
DB_PATH: Path = DB_DIR / "app.db"

# Trips and Content paths
TRIPS_DIR: Path = PROJECT_ROOT / "trips"
TRASH_DIR: Path = TRIPS_DIR / ".trash"
CONTEXT_DIR: Path = PROJECT_ROOT / "context" / "travel"
SKILLS_DIR: Path = PROJECT_ROOT / "skills"

# Frontend distribution (for production static serving)
FRONTEND_DIST: Path = PROJECT_ROOT / "app" / "frontend" / "dist"
