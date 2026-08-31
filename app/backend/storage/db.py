"""SQLite database layer for session, message, and tour persistence.

Uses raw aiosqlite for simplicity. Database is stored at data/app.db.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiosqlite
from core.config import DB_DIR as DEFAULT_DB_DIR
from core.config import DB_PATH as DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

# Database path (relative to backend directory)
DB_DIR = DEFAULT_DB_DIR
DB_PATH = DEFAULT_DB_PATH


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class Session:
    """A chat session."""

    id: str
    title: str | None
    language: str
    tour_type: str | None  # "bike", "road", or None
    created_at: datetime
    updated_at: datetime
    last_viewed_tour_id: str | None = None  # Track most recently viewed tour
    owner_token: str = "legacy"

    @classmethod
    def from_row(cls, row: aiosqlite.Row | dict[str, Any]) -> Session:
        """Construct a Session instance from a database row."""
        row_dict = dict(row)
        return cls(
            id=row_dict["id"],
            title=row_dict.get("resolved_title") or row_dict.get("title"),
            language=row_dict["language"],
            tour_type=row_dict["tour_type"],
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=datetime.fromisoformat(row_dict["updated_at"]),
            last_viewed_tour_id=row_dict.get("last_viewed_tour_id"),
            owner_token=row_dict.get("owner_token") or "legacy",
        )


@dataclass
class Message:
    """A message in a chat session."""

    id: int
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row | dict[str, Any]) -> Message:
        """Construct a Message instance from a database row."""
        row_dict = dict(row)
        return cls(
            id=row_dict["id"],
            session_id=row_dict["session_id"],
            role=row_dict["role"],
            content=row_dict["content"],
            created_at=datetime.fromisoformat(row_dict["created_at"]),
        )


@dataclass
class Tour:
    """A saved tour with reference to filesystem storage."""

    id: str
    session_id: str | None
    title: str
    tour_type: str  # "bike" or "road"
    slug: str  # URL-safe name, e.g., "berlin-potsdam-radtour"
    summary: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row | dict[str, Any]) -> Tour:
        """Construct a Tour instance from a database row."""
        row_dict = dict(row)
        return cls(
            id=row_dict["id"],
            session_id=row_dict["session_id"],
            title=row_dict["title"],
            tour_type=row_dict["tour_type"],
            slug=row_dict["slug"],
            summary=row_dict["summary"],
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=datetime.fromisoformat(row_dict["updated_at"]),
        )


# ============================================================================
# Schema
# ============================================================================

SCHEMA = """
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    language TEXT NOT NULL DEFAULT 'de',
    tour_type TEXT,
    last_viewed_tour_id TEXT,
    owner_token TEXT NOT NULL DEFAULT 'legacy',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Index for fast message lookup by session
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

-- Tours table (metadata only, content lives in trips/)
CREATE TABLE IF NOT EXISTS tours (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    title TEXT NOT NULL,
    tour_type TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

-- Index for tour listing by type
CREATE INDEX IF NOT EXISTS idx_tours_type ON tours(tour_type);
CREATE INDEX IF NOT EXISTS idx_tours_slug ON tours(slug);

CREATE TABLE IF NOT EXISTS session_artifacts (
    session_id TEXT PRIMARY KEY,
    gpx_content TEXT,
    map_data TEXT NOT NULL DEFAULT '{}',
    elevation_data TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""


# ============================================================================
# Database Connection
# ============================================================================


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection]:
    """Get a configured aiosqlite connection with pragmas and Row factory applied."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA busy_timeout = 5000;")
        yield db


async def init_db() -> None:
    """Initialize database schema. Creates tables if they don't exist and runs migrations."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA busy_timeout = 5000;")
        await db.executescript(SCHEMA)

        # Run migrations for existing databases
        with suppress(Exception):
            # Add last_viewed_tour_id column if it doesn't exist
            await db.execute("ALTER TABLE sessions ADD COLUMN last_viewed_tour_id TEXT")
            logger.info("Added last_viewed_tour_id column to sessions table")

        with suppress(Exception):
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN owner_token TEXT NOT NULL DEFAULT 'legacy'"
            )
        await db.execute("UPDATE sessions SET owner_token = 'legacy' WHERE owner_token IS NULL")

        await db.commit()

    logger.info("Database initialized at %s (WAL mode enabled)", DB_PATH)


async def get_db() -> aiosqlite.Connection:
    """Get a database connection. Caller must close it."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    await db.execute("PRAGMA busy_timeout = 5000;")
    return db


# ============================================================================
# Session Operations
# ============================================================================


async def create_session(
    session_id: str,
    language: str = "de",
    title: str | None = None,
    tour_type: str | None = None,
    owner_token: str = "legacy",
) -> Session:
    """Create a new session."""
    now = datetime.now(UTC).isoformat()

    async with get_connection() as db:
        await db.execute(
            """
            INSERT INTO sessions (id, title, language, tour_type, owner_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, title, language, tour_type, owner_token, now, now),
        )
        await db.commit()

    return Session(
        id=session_id,
        title=title,
        language=language,
        tour_type=tour_type,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
        last_viewed_tour_id=None,
        owner_token=owner_token,
    )


async def get_session(session_id: str, owner_token: str | None = None) -> Session | None:
    """Get a session by ID."""
    if owner_token:
        query = (
            "SELECT * FROM sessions WHERE id = ? AND (owner_token = ? OR owner_token = 'legacy')"
        )
        params = (session_id, owner_token)
    else:
        query = "SELECT * FROM sessions WHERE id = ?"
        params = (session_id,)

    async with (
        get_connection() as db,
        db.execute(query, params) as cursor,
    ):
        row = await cursor.fetchone()
        return Session.from_row(row) if row else None


async def update_session(
    session_id: str,
    title: str | None = None,
    tour_type: str | None = None,
) -> bool:
    """Update session metadata. Returns True if session existed."""
    now = datetime.now(UTC).isoformat()

    updates = ["updated_at = ?"]
    params: list[Any] = [now]

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if tour_type is not None:
        updates.append("tour_type = ?")
        params.append(tour_type)

    params.append(session_id)

    async with get_connection() as db:
        cursor = await db.execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_session(session_id: str, owner_token: str | None = None) -> bool:
    """Delete a session and all its messages. Returns True if session existed."""
    async with get_connection() as db:
        if owner_token and owner_token != "legacy":
            cursor = await db.execute(
                "DELETE FROM sessions WHERE id = ? AND (owner_token = ? OR owner_token = 'legacy')",
                (session_id, owner_token),
            )
        else:
            cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_all_sessions(owner_token: str = "legacy") -> int:
    """Delete all sessions for an owner. Returns count of deleted sessions."""
    async with get_connection() as db:
        if owner_token != "legacy":
            cursor = await db.execute(
                "DELETE FROM sessions WHERE owner_token = ? OR owner_token = 'legacy'",
                (owner_token,),
            )
        else:
            cursor = await db.execute("DELETE FROM sessions")
        await db.commit()
        return cursor.rowcount


async def list_sessions(limit: int = 50, owner_token: str = "legacy") -> list[Session]:
    """List recent sessions, newest first. Hides empty unused sessions without title or messages."""
    async with (
        get_connection() as db,
        db.execute(
            """SELECT s.*,
                      COALESCE(
                          s.title,
                          (SELECT SUBSTR(content, 1, 60) FROM messages WHERE session_id = s.id AND role = 'user' ORDER BY id ASC LIMIT 1)
                      ) as resolved_title
               FROM sessions s
               WHERE (s.owner_token = ? OR s.owner_token = 'legacy')
                 AND (s.title IS NOT NULL OR EXISTS (SELECT 1 FROM messages WHERE session_id = s.id))
               ORDER BY s.updated_at DESC
               LIMIT ?""",
            (owner_token, limit),
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        return [Session.from_row(row) for row in rows]


# ============================================================================
# Message Operations
# ============================================================================


async def add_message(
    session_id: str,
    role: str,
    content: str,
) -> Message:
    """Add a message to a session."""
    now = datetime.now(UTC).isoformat()

    async with get_connection() as db:
        cursor = await db.execute(
            """
            INSERT INTO messages (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, now),
        )
        await db.commit()
        message_id = cursor.lastrowid

    return Message(
        id=message_id,
        session_id=session_id,
        role=role,
        content=content,
        created_at=datetime.fromisoformat(now),
    )


async def get_messages(session_id: str) -> list[Message]:
    """Get all messages for a session, ordered by creation time."""
    async with (
        get_connection() as db,
        db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ) as cursor,
    ):
        rows = await cursor.fetchall()
        return [Message.from_row(row) for row in rows]


async def get_chat_history(session_id: str) -> list[dict[str, str]]:
    """Get messages in the format expected by the agent (role/content dicts)."""
    messages = await get_messages(session_id)
    return [{"role": msg.role, "content": msg.content} for msg in messages]


async def save_session_artifacts(
    session_id: str, gpx_content: str | None, map_data: dict[str, Any], elevation_data: list[Any]
) -> None:
    """Store the latest generated map and GPX data for session restoration."""
    import json

    async with get_connection() as db:
        await db.execute(
            """INSERT INTO session_artifacts (session_id, gpx_content, map_data, elevation_data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET gpx_content=excluded.gpx_content,
            map_data=excluded.map_data, elevation_data=excluded.elevation_data""",
            (session_id, gpx_content, json.dumps(map_data), json.dumps(elevation_data)),
        )
        await db.commit()


async def get_session_artifacts(session_id: str) -> dict[str, Any] | None:
    """Return the persisted route artifacts for a session."""
    import json

    async with (
        get_connection() as db,
        db.execute(
            "SELECT gpx_content, map_data, elevation_data FROM session_artifacts WHERE session_id = ?",
            (session_id,),
        ) as cursor,
    ):
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "gpx": row["gpx_content"],
            "map": json.loads(row["map_data"]),
            "elevation": json.loads(row["elevation_data"]),
        }


# ============================================================================
# Tour Operations
# ============================================================================


async def create_tour(
    tour_id: str,
    title: str,
    tour_type: str,
    slug: str,
    session_id: str | None = None,
    summary: str | None = None,
) -> Tour:
    """Create a new tour entry."""
    now = datetime.now(UTC).isoformat()

    async with get_connection() as db:
        await db.execute(
            """
            INSERT INTO tours (id, session_id, title, tour_type, slug, summary, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tour_id, session_id, title, tour_type, slug, summary, now, now),
        )
        await db.commit()

    return Tour(
        id=tour_id,
        session_id=session_id,
        title=title,
        tour_type=tour_type,
        slug=slug,
        summary=summary,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


async def get_tour(tour_id: str) -> Tour | None:
    """Get a tour by ID."""
    async with (
        get_connection() as db,
        db.execute("SELECT * FROM tours WHERE id = ?", (tour_id,)) as cursor,
    ):
        row = await cursor.fetchone()
        return Tour.from_row(row) if row else None


async def get_tour_by_slug(slug: str) -> Tour | None:
    """Get a tour by its URL slug."""
    async with (
        get_connection() as db,
        db.execute("SELECT * FROM tours WHERE slug = ?", (slug,)) as cursor,
    ):
        row = await cursor.fetchone()
        return Tour.from_row(row) if row else None


async def update_tour(
    tour_id: str,
    title: str | None = None,
    summary: str | None = None,
) -> bool:
    """Update tour metadata. Returns True if tour existed."""
    now = datetime.now(UTC).isoformat()

    updates = ["updated_at = ?"]
    params: list[Any] = [now]

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)

    params.append(tour_id)

    async with get_connection() as db:
        cursor = await db.execute(
            f"UPDATE tours SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_tour(tour_id: str) -> bool:
    """Delete a tour. Returns True if tour existed."""
    async with get_connection() as db:
        cursor = await db.execute("DELETE FROM tours WHERE id = ?", (tour_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_tour_by_slug(slug: str) -> bool:
    """Delete a tour by its slug. Returns True if tour existed."""
    async with get_connection() as db:
        cursor = await db.execute("DELETE FROM tours WHERE slug = ?", (slug,))
        await db.commit()
        return cursor.rowcount > 0


async def list_tours(tour_type: str | None = None, limit: int = 100) -> list[Tour]:
    """List tours, optionally filtered by type, newest first."""
    async with get_connection() as db:
        if tour_type:
            query = "SELECT * FROM tours WHERE tour_type = ? ORDER BY created_at DESC LIMIT ?"
            params = (tour_type, limit)
        else:
            query = "SELECT * FROM tours ORDER BY created_at DESC LIMIT ?"
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [Tour.from_row(row) for row in rows]


# ============================================================================
# Last Viewed Tour Operations
# ============================================================================


async def update_last_viewed_tour(session_id: str, tour_id: str) -> bool:
    """Update the last viewed tour for a session. Returns True if successful."""
    async with get_connection() as db:
        cursor = await db.execute(
            "UPDATE sessions SET last_viewed_tour_id = ? WHERE id = ?",
            (tour_id, session_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_last_viewed_tour(session_id: str) -> Tour | None:
    """Get the last viewed tour for a session."""
    async with (
        get_connection() as db,
        db.execute(
            """
            SELECT t.* FROM tours t
            WHERE t.id = (SELECT last_viewed_tour_id FROM sessions WHERE id = ?)
            """,
            (session_id,),
        ) as cursor,
    ):
        row = await cursor.fetchone()
        return Tour.from_row(row) if row else None


# ============================================================================
# Utility Functions
# ============================================================================


def generate_slug(title: str) -> str:
    """Generate a URL-safe slug from a title.

    Handles German umlauts and special characters.
    """
    import re
    import unicodedata

    # German umlaut replacements
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
    }

    slug = title.lower()
    for char, replacement in replacements.items():
        slug = slug.replace(char, replacement)

    # Normalize unicode and remove accents
    slug = unicodedata.normalize("NFKD", slug)
    slug = slug.encode("ascii", "ignore").decode("ascii")

    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug or "untitled"
