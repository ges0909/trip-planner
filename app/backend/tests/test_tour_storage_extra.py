import pytest
import storage.db as db
import storage.tour_storage as tour_storage


@pytest.fixture
def temp_trips_dir(tmp_path, monkeypatch):
    """Provide temporary trips and trash directories."""
    test_db = tmp_path / "test_storage.db"
    trips = tmp_path / "trips"
    trash = trips / ".trash"

    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(tour_storage, "TRIPS_DIR", trips)
    monkeypatch.setattr(tour_storage, "TRASH_DIR", trash)

    import asyncio

    asyncio.run(db.init_db())
    return trips


@pytest.mark.asyncio
async def test_save_and_delete_tour_storage(temp_trips_dir):
    """Test saving a tour, listing detail, moving to trash, and permanently deleting."""
    markdown = "# Oder-Neiße Radweg\n\nSchöne Radtour an der Oder."
    gpx = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk><trkseg>
    <trkpt lat="52.5" lon="14.3"></trkpt>
    <trkpt lat="52.6" lon="14.4"></trkpt>
  </trkseg></trk>
</gpx>"""

    # 1. Save tour
    tour = await tour_storage.save_tour(
        markdown=markdown,
        tour_type="bike",
        gpx_content=gpx,
    )
    assert tour.title == "Oder-Neiße Radweg"
    assert tour.slug.startswith("oder-neisse-radweg")

    # 2. Get detail
    detail = await tour_storage.get_tour_detail("bike", tour.slug)
    assert detail is not None
    assert detail["title"] == "Oder-Neiße Radweg"
    assert detail["has_gpx"] is True

    # 3. Get GPX & GeoJSON
    gpx_out = tour_storage.get_tour_gpx("bike", tour.slug)
    assert gpx_out is not None
    assert "<gpx" in gpx_out

    geojson = tour_storage.get_tour_geojson("bike", tour.slug)
    assert geojson is not None
    assert geojson["type"] == "FeatureCollection"

    # 4. Move to trash
    deleted = await tour_storage.move_to_trash("bike", tour.slug)
    assert deleted is True

    # 5. List trash items
    trash_items = tour_storage.list_trash()
    assert len(trash_items) == 1
    assert trash_items[0]["title"] == "Oder-Neiße Radweg"
    trash_name = trash_items[0]["trash_name"]

    # 6. Restore from trash
    restored = await tour_storage.restore_from_trash("bike", trash_name)
    assert restored is not None

    # Tour is restored
    restored_detail = await tour_storage.get_tour_detail("bike", tour.slug)
    assert restored_detail is not None

    # 7. Delete again and permanently remove
    await tour_storage.move_to_trash("bike", tour.slug)
    trash_items = tour_storage.list_trash()
    perm_deleted = await tour_storage.delete_from_trash("bike", trash_items[0]["trash_name"])
    assert perm_deleted is True

    # 8. Empty trash
    empty_count = await tour_storage.empty_trash()
    assert empty_count >= 0


def test_slug_and_filename_validation():
    """Test is_valid_slug and is_valid_map_filename validation functions."""
    assert tour_storage.is_valid_slug("berlin-potsdam-radtour") is True
    assert tour_storage.is_valid_slug("invalid/slug/path") is False
    assert tour_storage.is_valid_slug("../etc/passwd") is False

    assert tour_storage.is_valid_map_filename("route.png") is True
    assert tour_storage.is_valid_map_filename("../secret.png") is False


@pytest.mark.asyncio
async def test_rename_tour_storage(temp_trips_dir):
    """Test renaming a tour."""
    # 1. Save original tour
    tour = await tour_storage.save_tour(
        markdown="# Originale Tour\n\nStart in Hamburg.",
        tour_type="bike",
    )
    assert tour.title == "Originale Tour"

    # 2. Rename tour
    renamed = await tour_storage.rename_tour("bike", tour.slug, "Neuer Tourname")
    assert renamed is not None
    assert renamed.title == "Neuer Tourname"

    # Verify updated index.md
    md_content = tour_storage.get_tour_markdown("bike", tour.slug)
    assert md_content.startswith("# Neuer Tourname")
