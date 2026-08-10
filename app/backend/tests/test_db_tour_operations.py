"""Tests for db.py tour operations.

Covers delete_tour_by_slug and generate_slug functions.
"""

import pytest


@pytest.fixture
def temp_db_path(tmp_path):
    """Use a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return db_path


@pytest.fixture
def mock_db_path(temp_db_path, monkeypatch):
    """Patch DB_PATH to use temporary database."""
    import storage.db as db

    monkeypatch.setattr(db, "DB_PATH", temp_db_path)
    monkeypatch.setattr(db, "DB_DIR", temp_db_path.parent)
    return temp_db_path


class TestDeleteTourBySlug:
    """Tests for delete_tour_by_slug function."""

    @pytest.mark.asyncio
    async def test_delete_existing_tour_by_slug(self, mock_db_path):
        """Deleting an existing tour by slug should return True."""
        import storage.db as db

        await db.init_db()

        # Create a tour first
        await db.create_tour(
            tour_id="test-123",
            title="Test Tour",
            tour_type="bike",
            slug="test-tour",
            summary="A test tour.",
        )

        # Verify it exists
        existing = await db.get_tour_by_slug("test-tour")
        assert existing is not None

        # Delete by slug
        result = await db.delete_tour_by_slug("test-tour")
        assert result is True

        # Verify it's gone
        deleted = await db.get_tour_by_slug("test-tour")
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_slug_returns_false(self, mock_db_path):
        """Deleting a non-existent slug should return False."""
        import storage.db as db

        await db.init_db()

        result = await db.delete_tour_by_slug("nonexistent-slug")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_by_slug_only_deletes_matching(self, mock_db_path):
        """delete_tour_by_slug should only delete the matching tour."""
        import storage.db as db

        await db.init_db()

        # Create multiple tours
        await db.create_tour(tour_id="tour-1", title="Tour One", tour_type="bike", slug="tour-one")
        await db.create_tour(tour_id="tour-2", title="Tour Two", tour_type="road", slug="tour-two")

        # Delete one
        await db.delete_tour_by_slug("tour-one")

        # Verify only one is deleted
        assert await db.get_tour_by_slug("tour-one") is None
        assert await db.get_tour_by_slug("tour-two") is not None


class TestGenerateSlug:
    """Tests for generate_slug function."""

    def test_basic_slug_generation(self):
        """Basic title should become lowercase hyphenated slug."""
        from storage.db import generate_slug

        assert generate_slug("My Great Tour") == "my-great-tour"

    def test_german_umlauts_replaced(self):
        """German umlauts should be replaced with ASCII equivalents."""
        from storage.db import generate_slug

        assert generate_slug("Berliner Überlandradweg") == "berliner-ueberlandradweg"
        assert generate_slug("Köln nach München") == "koeln-nach-muenchen"
        assert generate_slug("Große Äpfel") == "grosse-aepfel"

    def test_eszett_replaced(self):
        """ß should be replaced with ss."""
        from storage.db import generate_slug

        assert generate_slug("Große Straße") == "grosse-strasse"

    def test_special_characters_removed(self):
        """Special characters become hyphens."""
        from storage.db import generate_slug

        assert generate_slug("Tour: Berlin → Potsdam!") == "tour-berlin-potsdam"

    def test_consecutive_hyphens_collapsed(self):
        """Multiple special chars become single hyphen."""
        from storage.db import generate_slug

        assert generate_slug("A   B   C") == "a-b-c"
        assert generate_slug("X---Y---Z") == "x-y-z"

    def test_leading_trailing_hyphens_removed(self):
        """No leading or trailing hyphens."""
        from storage.db import generate_slug

        assert generate_slug("  Spaces Around  ") == "spaces-around"
        assert generate_slug("---dashes---") == "dashes"

    def test_empty_title_returns_untitled(self):
        """Empty or special-only title returns 'untitled'."""
        from storage.db import generate_slug

        assert generate_slug("") == "untitled"
        assert generate_slug("---") == "untitled"
        assert generate_slug("!!!") == "untitled"

    def test_unicode_normalization(self):
        """Accented characters should be normalized."""
        from storage.db import generate_slug

        # é can be represented as e + combining accent
        assert generate_slug("Café Tour") == "cafe-tour"
        assert generate_slug("naïve résumé") == "naive-resume"
