"""SQLite database layer for session, message, and tour persistence.

Uses raw aiosqlite for simplicity. Database is stored at data/app.db.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Database path (relative to backend directory)
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "app.db"


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


@dataclass
class Message:
    """A message in a chat session."""

    id: int
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


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
"""


# ============================================================================
# Database Connection
# ============================================================================


async def init_db() -> None:
    """Initialize database schema. Creates tables if they don't exist and runs migrations."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        
        # Run migrations for existing databases
        try:
            # Add last_viewed_tour_id column if it doesn't exist
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN last_viewed_tour_id TEXT"
            )
            logger.info("Added last_viewed_tour_id column to sessions table")
        except Exception:
            # Column already exists or other error - ignore
            pass
        
        await db.commit()

    logger.info("Database initialized at %s", DB_PATH)


async def get_db() -> aiosqlite.Connection:
    """Get a database connection. Caller must close it."""
    return await aiosqlite.connect(DB_PATH)


# ============================================================================
# Session Operations
# ============================================================================


async def create_session(
    session_id: str,
    language: str = "de",
    title: str | None = None,
    tour_type: str | None = None,
) -> Session:
    """Create a new session."""
    now = datetime.now(UTC).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO sessions (id, title, language, tour_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, title, language, tour_type, now, now),
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
    )


async def get_session(session_id: str) -> Session | None:
    """Get a session by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Session(
                id=row["id"],
                title=row["title"],
                language=row["language"],
                tour_type=row["tour_type"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                last_viewed_tour_id=row.get("last_viewed_tour_id"),
            )


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

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_session(session_id: str) -> bool:
    """Delete a session and all its messages. Returns True if session existed."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
        return cursor.rowcount > 0


async def list_sessions(limit: int = 50) -> list[Session]:
    """List recent sessions, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Session(
                    id=row["id"],
                    title=row["title"],
                    language=row["language"],
                    tour_type=row["tour_type"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    last_viewed_tour_id=row.get("last_viewed_tour_id"),
                )
                for row in rows
            ]


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

    async with aiosqlite.connect(DB_PATH) as db:
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Message(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]


async def get_chat_history(session_id: str) -> list[dict[str, str]]:
    """Get messages in the format expected by the agent (role/content dicts)."""
    messages = await get_messages(session_id)
    return [{"role": msg.role, "content": msg.content} for msg in messages]


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

    async with aiosqlite.connect(DB_PATH) as db:
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tours WHERE id = ?", (tour_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Tour(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                tour_type=row["tour_type"],
                slug=row["slug"],
                summary=row["summary"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )


async def get_tour_by_slug(slug: str) -> Tour | None:
    """Get a tour by its URL slug."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tours WHERE slug = ?", (slug,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Tour(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                tour_type=row["tour_type"],
                slug=row["slug"],
                summary=row["summary"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )


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

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"UPDATE tours SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_tour(tour_id: str) -> bool:
    """Delete a tour. Returns True if tour existed."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM tours WHERE id = ?", (tour_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_tour_by_slug(slug: str) -> bool:
    """Delete a tour by its slug. Returns True if tour existed."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM tours WHERE slug = ?", (slug,))
        await db.commit()
        return cursor.rowcount > 0


async def list_tours(tour_type: str | None = None, limit: int = 100) -> list[Tour]:
    """List tours, optionally filtered by type, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if tour_type:
            query = "SELECT * FROM tours WHERE tour_type = ? ORDER BY created_at DESC LIMIT ?"
            params = (tour_type, limit)
        else:
            query = "SELECT * FROM tours ORDER BY created_at DESC LIMIT ?"
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                Tour(
                    id=row["id"],
                    session_id=row["session_id"],
                    title=row["title"],
                    tour_type=row["tour_type"],
                    slug=row["slug"],
                    summary=row["summary"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]


# ============================================================================
# Last Viewed Tour Operations
# ============================================================================


async def update_last_viewed_tour(session_id: str, tour_id: str) -> bool:
    """Update the last viewed tour for a session. Returns True if successful."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE sessions SET last_viewed_tour_id = ? WHERE id = ?",
            (tour_id, session_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_last_viewed_tour(session_id: str) -> Tour | None:
    """Get the last viewed tour for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.* FROM tours t
            WHERE t.id = (SELECT last_viewed_tour_id FROM sessions WHERE id = ?)
            """,
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Tour(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                tour_type=row["tour_type"],
                slug=row["slug"],
                summary=row["summary"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )


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
