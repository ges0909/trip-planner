"""Tests for session persistence and the last-viewed tour reference."""

import aiosqlite
import pytest


@pytest.fixture
def mock_db_path(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    import storage.db as db

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    return db_path


@pytest.mark.asyncio
async def test_last_viewed_tour_roundtrip(mock_db_path):
    """A session can save and restore its last viewed tour."""
    import storage.db as db

    await db.init_db()
    await db.create_session("session-1")
    await db.create_tour(
        tour_id="tour-1",
        title="Test Tour",
        tour_type="bike",
        slug="test-tour",
    )

    assert await db.update_last_viewed_tour("session-1", "tour-1") is True

    tour = await db.get_last_viewed_tour("session-1")

    assert tour is not None
    assert tour.id == "tour-1"
    assert tour.slug == "test-tour"


@pytest.mark.asyncio
async def test_last_viewed_tour_returns_none_for_missing_reference(mock_db_path):
    """A session without a valid last-viewed tour returns None."""
    import storage.db as db

    await db.init_db()
    await db.create_session("session-1")

    assert await db.get_last_viewed_tour("session-1") is None
    assert await db.update_last_viewed_tour("missing-session", "tour-1") is False


@pytest.mark.asyncio
async def test_last_viewed_routes_create_and_restore_session(mock_db_path):
    """The API creates a missing session and returns its saved tour."""
    import storage.db as db
    from app.routes.sessions import (
        get_last_viewed_tour_endpoint,
        set_last_viewed_tour_endpoint,
    )
    from app.schemas import LastViewedTourRequest

    await db.init_db()
    await db.create_tour(
        tour_id="tour-1",
        title="Test Tour",
        tour_type="road",
        slug="test-tour",
    )

    save_response = await set_last_viewed_tour_endpoint(
        "new-session", LastViewedTourRequest(tour_id="tour-1")
    )
    restore_response = await get_last_viewed_tour_endpoint("new-session")

    assert save_response == {"status": "ok"}
    assert restore_response["tour"]["slug"] == "test-tour"


@pytest.mark.asyncio
async def test_init_db_migrates_existing_sessions_table(mock_db_path):
    """Initialization adds the last-viewed column to an older database."""
    import storage.db as db

    async with aiosqlite.connect(mock_db_path) as connection:
        await connection.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                language TEXT NOT NULL,
                tour_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await connection.commit()

    await db.init_db()

    async with (
        aiosqlite.connect(mock_db_path) as connection,
        connection.execute("PRAGMA table_info(sessions)") as cursor,
    ):
        columns = {row[1] for row in await cursor.fetchall()}

    assert "last_viewed_tour_id" in columns


@pytest.mark.asyncio
async def test_delete_session_cascades_messages_and_artifacts(mock_db_path):
    """Deleting a session cascades to its messages and artifacts."""
    import storage.db as db

    await db.init_db()
    await db.create_session("sess-to-delete", title="Temp Session", language="de")
    await db.add_message("sess-to-delete", "user", "Hallo TourPilot")
    await db.save_session_artifacts("sess-to-delete", "<gpx></gpx>", {}, [])

    assert await db.get_session("sess-to-delete") is not None
    assert len(await db.get_chat_history("sess-to-delete")) == 1
    artifacts = await db.get_session_artifacts("sess-to-delete")
    assert artifacts is not None
    assert artifacts["gpx"] == "<gpx></gpx>"

    # Delete session
    assert await db.delete_session("sess-to-delete") is True
    assert await db.get_session("sess-to-delete") is None
    assert len(await db.get_chat_history("sess-to-delete")) == 0
    assert await db.get_session_artifacts("sess-to-delete") is None


@pytest.mark.asyncio
async def test_delete_all_sessions_clears_owner_sessions(mock_db_path):
    """delete_all_sessions removes all sessions."""
    import storage.db as db

    await db.init_db()
    await db.create_session("sess-1", title="Tour 1", language="de")
    await db.create_session("sess-2", title="Tour 2", language="de")

    assert len(await db.list_sessions()) == 2
    deleted = await db.delete_all_sessions()
    assert deleted == 2
    assert len(await db.list_sessions()) == 0
