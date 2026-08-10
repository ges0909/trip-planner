"""Tests for tour_storage module — filesystem + SQLite operations.

Covers:
- Trash operations (move, restore, list, delete)
- GPX file combination
- Slug collision handling
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# We need to set up test paths before importing tour_storage
TEST_TRIPS_DIR = Path(tempfile.mkdtemp()) / "trips"
TEST_TRASH_DIR = TEST_TRIPS_DIR / ".trash"


@pytest.fixture(autouse=True)
def setup_test_dirs():
    """Create and clean up test directories for each test."""
    TEST_TRIPS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup after test
    if TEST_TRIPS_DIR.exists():
        shutil.rmtree(TEST_TRIPS_DIR)


@pytest.fixture
def mock_paths(monkeypatch):
    """Patch TRIPS_DIR and TRASH_DIR to use test directories."""
    import storage.tour_storage as tour_storage

    monkeypatch.setattr(tour_storage, "TRIPS_DIR", TEST_TRIPS_DIR)
    monkeypatch.setattr(tour_storage, "TRASH_DIR", TEST_TRASH_DIR)
    return TEST_TRIPS_DIR, TEST_TRASH_DIR


def create_test_tour(trips_dir: Path, tour_type: str, slug: str) -> Path:
    """Helper to create a test tour directory with index.md."""
    tour_dir = trips_dir / tour_type / slug
    tour_dir.mkdir(parents=True, exist_ok=True)
    (tour_dir / "index.md").write_text(f"# Test Tour: {slug}\n\nA test tour.", encoding="utf-8")
    (tour_dir / "gpx").mkdir(exist_ok=True)
    (tour_dir / "gpx" / "route.gpx").write_text("<gpx></gpx>", encoding="utf-8")
    return tour_dir


class TestMoveToTrash:
    """Tests for move_to_trash function."""

    @pytest.mark.asyncio
    async def test_move_existing_tour_to_trash(self, mock_paths):
        """Moving an existing tour should relocate it to .trash/ with timestamp."""
        trips_dir, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        # Create a tour
        create_test_tour(trips_dir, "bike", "test-tour")

        # Mock the database deletion
        with patch.object(
            tour_storage, "delete_tour_by_slug", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = True
            result = await tour_storage.move_to_trash("bike", "test-tour")

        assert result is True
        # Original location should be gone
        assert not (trips_dir / "bike" / "test-tour").exists()
        # Should be in trash
        trash_items = list((trash_dir / "bike").iterdir())
        assert len(trash_items) == 1
        assert trash_items[0].name.startswith("test-tour_")
        # Content should be preserved
        assert (trash_items[0] / "index.md").exists()

    @pytest.mark.asyncio
    async def test_move_nonexistent_tour_returns_false(self, mock_paths):
        """Moving a tour that doesn't exist should return False."""
        import storage.tour_storage as tour_storage

        result = await tour_storage.move_to_trash("bike", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_trash_name_includes_timestamp(self, mock_paths):
        """Trash folder name should include YYYYMMDD-HHMMSS timestamp."""
        trips_dir, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        create_test_tour(trips_dir, "road", "my-trip")

        with patch.object(tour_storage, "delete_tour_by_slug", new_callable=AsyncMock):
            await tour_storage.move_to_trash("road", "my-trip")

        trash_items = list((trash_dir / "road").iterdir())
        trash_name = trash_items[0].name
        # Format: slug_YYYYMMDD-HHMMSS
        parts = trash_name.split("_")
        assert parts[0] == "my-trip"
        assert len(parts[1]) == 15  # YYYYMMDD-HHMMSS


class TestListTrash:
    """Tests for list_trash function."""

    def test_empty_trash_returns_empty_list(self, mock_paths):
        """When trash is empty, list_trash returns []."""
        import storage.tour_storage as tour_storage

        result = tour_storage.list_trash()
        assert result == []

    def test_list_trash_with_items(self, mock_paths):
        """list_trash should return items with correct metadata."""
        trips_dir, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        # Create trash items manually
        (trash_dir / "bike" / "tour-a_20240809-120000").mkdir(parents=True)
        (trash_dir / "bike" / "tour-a_20240809-120000" / "index.md").write_text(
            "# Tour A\n\nDescription.", encoding="utf-8"
        )
        (trash_dir / "road" / "tour-b_20240810-150000").mkdir(parents=True)
        (trash_dir / "road" / "tour-b_20240810-150000" / "index.md").write_text(
            "# Tour B\n\nDescription.", encoding="utf-8"
        )

        result = tour_storage.list_trash()

        assert len(result) == 2
        # Should be sorted by deleted_at descending
        assert result[0]["original_slug"] == "tour-b"
        assert result[1]["original_slug"] == "tour-a"
        # Check metadata
        assert result[0]["tour_type"] == "road"
        assert result[0]["title"] == "Tour B"
        assert result[0]["deleted_at"] == "2024-08-10T15:00:00"


class TestRestoreFromTrash:
    """Tests for restore_from_trash function."""

    @pytest.mark.asyncio
    async def test_restore_tour_from_trash(self, mock_paths):
        """Restoring a tour should move it back and re-index in DB."""
        trips_dir, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        # Create a trash item
        trash_item = trash_dir / "bike" / "my-tour_20240809-120000"
        trash_item.mkdir(parents=True)
        (trash_item / "index.md").write_text("# My Tour\n\nDescription.", encoding="utf-8")

        # Mock DB functions
        with (
            patch.object(tour_storage, "get_tour_by_slug", new_callable=AsyncMock) as mock_get,
            patch.object(tour_storage, "create_tour", new_callable=AsyncMock) as mock_create,
        ):
            mock_get.return_value = None  # Slug not taken
            mock_create.return_value = tour_storage.Tour(
                id="test-id",
                session_id=None,
                title="My Tour",
                tour_type="bike",
                slug="my-tour",
                summary="Description.",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            result = await tour_storage.restore_from_trash("bike", "my-tour_20240809-120000")

        assert result is not None
        assert result.slug == "my-tour"
        # Trash item should be gone
        assert not trash_item.exists()
        # Should be restored to original location
        assert (trips_dir / "bike" / "my-tour" / "index.md").exists()

    @pytest.mark.asyncio
    async def test_restore_with_slug_collision_gets_new_slug(self, mock_paths):
        """If original slug is taken, restored tour gets a numbered suffix."""
        trips_dir, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        # Create existing tour with same slug
        create_test_tour(trips_dir, "bike", "my-tour")

        # Create trash item
        trash_item = trash_dir / "bike" / "my-tour_20240809-120000"
        trash_item.mkdir(parents=True)
        (trash_item / "index.md").write_text("# My Tour\n\nOld version.", encoding="utf-8")

        # Mock DB: first call returns existing, second returns None (slug-2 available)
        with (
            patch.object(tour_storage, "get_tour_by_slug", new_callable=AsyncMock) as mock_get,
            patch.object(tour_storage, "create_tour", new_callable=AsyncMock) as mock_create,
        ):
            # Simulate: my-tour exists, my-tour-2 doesn't
            mock_get.side_effect = [
                tour_storage.Tour(
                    id="existing",
                    session_id=None,
                    title="Existing",
                    tour_type="bike",
                    slug="my-tour",
                    summary=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ),
                None,  # my-tour-2 is available
            ]
            mock_create.return_value = tour_storage.Tour(
                id="new-id",
                session_id=None,
                title="My Tour",
                tour_type="bike",
                slug="my-tour-2",
                summary="Old version.",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            result = await tour_storage.restore_from_trash("bike", "my-tour_20240809-120000")

        assert result is not None
        assert result.slug == "my-tour-2"
        # Should be at new location
        assert (trips_dir / "bike" / "my-tour-2" / "index.md").exists()

    @pytest.mark.asyncio
    async def test_restore_nonexistent_returns_none(self, mock_paths):
        """Restoring a non-existent trash item returns None."""
        import storage.tour_storage as tour_storage

        result = await tour_storage.restore_from_trash("bike", "nonexistent_20240809-120000")
        assert result is None


class TestDeleteFromTrash:
    """Tests for permanent deletion from trash."""

    @pytest.mark.asyncio
    async def test_delete_single_item_from_trash(self, mock_paths):
        """delete_from_trash should permanently remove a single item."""
        _, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        # Create trash item
        trash_item = trash_dir / "bike" / "to-delete_20240809-120000"
        trash_item.mkdir(parents=True)
        (trash_item / "index.md").write_text("# Delete Me", encoding="utf-8")

        result = await tour_storage.delete_from_trash("bike", "to-delete_20240809-120000")

        assert result is True
        assert not trash_item.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_from_trash_returns_false(self, mock_paths):
        """Deleting non-existent item returns False."""
        import storage.tour_storage as tour_storage

        result = await tour_storage.delete_from_trash("bike", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_trash_deletes_all(self, mock_paths):
        """empty_trash should permanently delete all items in trash."""
        _, trash_dir = mock_paths
        import storage.tour_storage as tour_storage

        # Create multiple trash items
        for i in range(3):
            item = trash_dir / "bike" / f"tour-{i}_20240809-12000{i}"
            item.mkdir(parents=True)
            (item / "index.md").write_text(f"# Tour {i}", encoding="utf-8")

        count = await tour_storage.empty_trash()

        assert count == 3
        # No tour directories should remain (type dirs may remain empty)
        remaining_items = [
            p for p in trash_dir.rglob("*") if p.is_dir() and p.name not in ("bike", "road")
        ]
        assert remaining_items == []


class TestExtractTitle:
    """Tests for _extract_title_from_markdown."""

    def test_extracts_h1_title(self):
        """Should extract title from # heading."""
        from storage.tour_storage import _extract_title_from_markdown

        result = _extract_title_from_markdown("# My Great Tour\n\nSome content.")
        assert result == "My Great Tour"

    def test_extracts_h2_title(self):
        """Should extract title from ## heading if no h1."""
        from storage.tour_storage import _extract_title_from_markdown

        result = _extract_title_from_markdown("## Another Tour\n\nContent.")
        assert result == "Another Tour"

    def test_returns_untitled_if_no_heading(self):
        """Returns 'Untitled Tour' if no heading found."""
        from storage.tour_storage import _extract_title_from_markdown

        result = _extract_title_from_markdown("Just some text without heading.")
        assert result == "Untitled Tour"


class TestExtractSummary:
    """Tests for _extract_summary_from_markdown."""

    def test_extracts_first_paragraph(self):
        """Should extract first paragraph after title."""
        from storage.tour_storage import _extract_summary_from_markdown

        md = "# Title\n\nThis is the summary paragraph.\n\n## Next section"
        result = _extract_summary_from_markdown(md)
        assert result == "This is the summary paragraph."

    def test_truncates_long_summary(self):
        """Summary should be truncated to 500 chars."""
        from storage.tour_storage import _extract_summary_from_markdown

        long_text = "x" * 600
        md = f"# Title\n\n{long_text}\n\n## Next"
        result = _extract_summary_from_markdown(md)
        assert len(result) == 500
        assert result.endswith("...")

    def test_returns_none_for_no_summary(self):
        """Returns None if no paragraph after title."""
        from storage.tour_storage import _extract_summary_from_markdown

        result = _extract_summary_from_markdown("# Just a title")
        assert result is None
