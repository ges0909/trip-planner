"""HTTP Integration tests for FastAPI router endpoints."""

import asyncio
from unittest.mock import AsyncMock

import pytest
import storage.db as db
import storage.tour_storage as tour_storage
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide a TestClient with a fresh temporary SQLite DB and trips directory."""
    test_db = tmp_path / "test_api.db"
    test_trips = tmp_path / "trips"
    test_trash = test_trips / ".trash"

    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(tour_storage, "TRIPS_DIR", test_trips)
    monkeypatch.setattr(tour_storage, "TRASH_DIR", test_trash)

    # Initialize DB synchronously
    asyncio.run(db.init_db())

    # Provide a mock MCP manager on app.state
    mock_mcp = AsyncMock()
    mock_mcp.get_tool_declarations.return_value = []
    mock_mcp.call_tool.return_value = {}
    app.state.mcp_manager = mock_mcp

    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Health endpoint returns ok status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sessions_crud_and_last_viewed(client):
    """Full lifecycle of sessions via API."""
    # 1. Create a session via DB helper
    session_id = "test-session-123"
    asyncio.run(
        db.create_session(
            session_id=session_id,
            title="Alpen Tour",
            language="de",
            tour_type="bike",
        )
    )

    # 2. Get the session detail
    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    assert res.json()["id"] == session_id
    assert res.json()["title"] == "Alpen Tour"

    # 3. List sessions
    res = client.get("/api/sessions")
    assert res.status_code == 200
    sessions = res.json()
    assert any(s["id"] == session_id for s in sessions)

    # 4. Create a tour and link as last-viewed via PUT endpoint
    asyncio.run(
        db.create_tour(
            tour_id="tour-123",
            title="Alpen Pass",
            tour_type="bike",
            slug="alpen-pass",
            session_id=session_id,
        )
    )

    res = client.put(f"/api/sessions/{session_id}/last-viewed", json={"tour_id": "tour-123"})
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    res = client.get(f"/api/sessions/{session_id}/last-viewed")
    assert res.status_code == 200
    assert res.json()["tour"]["id"] == "tour-123"

    # 5. Delete single session via DELETE /api/sessions/{session_id}
    res = client.delete(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Nonexistent session detail returns 404
    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 404

    # 6. Create multiple sessions and clear all via DELETE /api/sessions
    asyncio.run(db.create_session(session_id="s1", title="Tour 1", language="de"))
    asyncio.run(db.create_session(session_id="s2", title="Tour 2", language="de"))

    res = client.delete("/api/sessions")
    assert res.status_code == 200
    assert res.json()["deleted_count"] >= 2

    res = client.get("/api/sessions")
    assert len(res.json()) == 0


def test_tours_endpoints_and_validation(client):
    """Tour listing, saving, viewing, and validation rejection."""
    # 1. Invalid tour_type / slug validation rejection
    res = client.get("/api/tours/invalid_type/berlin-tour")
    assert res.status_code == 400

    res = client.get("/api/tours/bike/invalid_slug_with_special!chars")
    assert res.status_code == 400

    # 2. Save a new tour via POST /api/tours
    save_payload = {
        "title": "Müggelsee Rundfahrt",
        "tour_type": "bike",
        "markdown": "# Müggelsee Tour\n\nSchöne Radtour um den Müggelsee.",
        "gpx": "<gpx></gpx>",
    }
    res = client.post("/api/tours", json=save_payload)
    assert res.status_code == 200
    saved_tour = res.json()
    slug = saved_tour["slug"]
    assert slug == "mueggelsee-tour"

    # 3. Get tour detail
    res = client.get(f"/api/tours/bike/{slug}")
    assert res.status_code == 200
    assert res.json()["title"] == "Müggelsee Tour"

    # 4. Get GPX file
    res = client.get(f"/api/tours/bike/{slug}/gpx")
    assert res.status_code == 200
    assert "<gpx>" in res.text

    # 5. Get GeoJSON representation
    res = client.get(f"/api/tours/bike/{slug}/geojson")
    assert res.status_code == 200
    geojson = res.json()
    assert geojson["type"] == "FeatureCollection"

    # 6. List tours
    res = client.get("/api/tours?tour_type=bike")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 7. Map image serving & 404 checks
    res = client.get(f"/api/tours/bike/{slug}/maps/route.png")
    assert res.status_code in (404, 200)

    res = client.get("/api/tours/bike/nonexistent-tour-slug")
    assert res.status_code == 404

    res = client.get("/api/tours/bike/nonexistent-tour-slug/gpx")
    assert res.status_code == 404

    res = client.get("/api/tours/bike/nonexistent-tour-slug/geojson")
    assert res.status_code == 404

    res = client.get("/api/tours/bike/nonexistent-tour-slug/maps/invalid_map!.png")
    assert res.status_code == 400


def test_trash_endpoints(client):
    """Trash listing, restore, and permanent deletion."""
    # 1. Save tour
    res = client.post(
        "/api/tours",
        json={
            "tour_type": "bike",
            "markdown": "# Wannsee Tour\n\nWunderschöne Wannsee Runde.",
        },
    )
    assert res.status_code == 200
    slug = res.json()["slug"]

    # 2. Move to trash
    del_res = client.delete(f"/api/tours/bike/{slug}")
    assert del_res.status_code == 200

    # 3. List trash
    res = client.get("/api/trash")
    assert res.status_code == 200
    trash_items = res.json()
    assert len(trash_items) >= 1
    trash_name = trash_items[0]["trash_name"]

    # 4. Restore from trash
    res = client.post(f"/api/trash/bike/{trash_name}/restore")
    assert res.status_code == 200
    assert res.json()["status"] == "restored"

    # Tour is back in tours
    res = client.get(f"/api/tours/bike/{slug}")
    assert res.status_code == 200

    # 5. Delete again and permanently remove from trash
    client.delete(f"/api/tours/bike/{slug}")
    trash_items = client.get("/api/trash").json()
    new_trash_name = trash_items[0]["trash_name"]

    res = client.delete(f"/api/trash/bike/{new_trash_name}")
    assert res.status_code == 200
    assert res.json() == {"status": "permanently_deleted"}

    # 6. Empty trash
    res = client.delete("/api/trash")
    assert res.status_code == 200
    assert res.json()["status"] == "emptied"


def test_tour_rename_endpoint(client):
    """Test POST /api/tours/{tour_type}/{slug}/rename endpoint."""
    # 1. Create a tour
    res = client.post(
        "/api/tours",
        json={
            "tour_type": "bike",
            "markdown": "# Spree Tour\n\nSchöne Radtour an der Spree.",
        },
    )
    assert res.status_code == 200
    slug = res.json()["slug"]

    # 2. Rename tour
    rename_res = client.post(
        f"/api/tours/bike/{slug}/rename",
        json={"title": "Spree Tour 2026"},
    )
    assert rename_res.status_code == 200
    assert rename_res.json()["status"] == "renamed"
    assert rename_res.json()["title"] == "Spree Tour 2026"

    # Verify tour detail has updated title
    detail_res = client.get(f"/api/tours/bike/{slug}")
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Spree Tour 2026"
