"""Unit tests for GPX file combining, ordering, and filesystem-to-DB syncing."""

import asyncio

import pytest
import storage.db as db
import storage.tour_storage as tour_storage


@pytest.fixture
def temp_sync_env(tmp_path, monkeypatch):
    """Provide a temporary environment for filesystem-to-DB syncing."""
    test_db = tmp_path / "sync.db"
    trips = tmp_path / "trips"
    trash = trips / ".trash"

    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(tour_storage, "TRIPS_DIR", trips)
    monkeypatch.setattr(tour_storage, "TRASH_DIR", trash)

    trips.mkdir(parents=True, exist_ok=True)
    asyncio.run(db.init_db())
    return trips


def test_combine_and_order_gpx_files(temp_sync_env):
    """Test combining multiple day GPX files in markdown section order."""
    day1_gpx = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk><name>Tag 1</name><trkseg><trkpt lat="52.5" lon="13.4"></trkpt></trkseg></trk>
</gpx>"""
    day2_gpx = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk><name>Tag 2</name><trkseg><trkpt lat="52.4" lon="13.3"></trkpt></trkseg></trk>
</gpx>"""

    gpx1_path = temp_sync_env / "day1.gpx"
    gpx2_path = temp_sync_env / "day2.gpx"
    gpx1_path.write_text(day1_gpx, encoding="utf-8")
    gpx2_path.write_text(day2_gpx, encoding="utf-8")

    combined = tour_storage._combine_gpx_files([gpx1_path, gpx2_path])
    assert "<gpx" in combined

    # Test ordering by markdown index
    index_md = temp_sync_env / "index.md"
    index_md.write_text(
        "# Multi Day Tour\n\n- [Tag 2](day2.gpx)\n- [Tag 1](day1.gpx)", encoding="utf-8"
    )

    ordered = tour_storage._order_gpx_by_markdown([gpx1_path, gpx2_path], index_md)
    assert len(ordered) == 2
    assert ordered[0] == gpx1_path
    assert ordered[1] == gpx2_path


@pytest.mark.asyncio
async def test_sync_filesystem_to_db(temp_sync_env):
    """Test discovering tour folders on disk and syncing into SQLite DB."""
    tour_dir = temp_sync_env / "bike" / "ostsee-radweg"
    tour_dir.mkdir(parents=True, exist_ok=True)
    (tour_dir / "index.md").write_text(
        "# Ostsee Radweg\n\nTraumhafte Tour am Meer.", encoding="utf-8"
    )

    synced_count = await tour_storage.sync_filesystem_to_db()
    assert synced_count >= 1

    tours = await db.list_tours(tour_type="bike")
    assert any(t.slug == "ostsee-radweg" for t in tours)
