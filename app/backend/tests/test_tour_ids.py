"""Tests for stable tour identifiers."""


def test_tour_id_is_deterministic():
    """The same tour location always produces the same identifier."""
    from storage.tour_storage import _generate_tour_id

    first = _generate_tour_id("road", "nordspanien")
    second = _generate_tour_id("road", "nordspanien")

    assert first == second


def test_tour_id_includes_tour_type_and_slug():
    """Different tour locations do not share identifiers."""
    from storage.tour_storage import _generate_tour_id

    assert _generate_tour_id("bike", "same-slug") != _generate_tour_id("road", "same-slug")
    assert _generate_tour_id("road", "first") != _generate_tour_id("road", "second")
