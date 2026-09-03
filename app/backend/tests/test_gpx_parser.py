"""Unit tests for GPX parser and combination functions."""

from pathlib import Path

from storage.gpx_parser import combine_gpx_files, order_gpx_by_markdown


def test_order_gpx_by_markdown_no_index_md(tmp_path: Path):
    """Fallback to alphabetical sort when index.md does not exist."""
    gpx1 = tmp_path / "b-route.gpx"
    gpx2 = tmp_path / "a-route.gpx"
    gpx1.touch()
    gpx2.touch()

    ordered = order_gpx_by_markdown([gpx1, gpx2], tmp_path / "non_existent.md")
    assert ordered == [gpx2, gpx1]


def test_order_gpx_by_markdown_with_map_references(tmp_path: Path):
    """Order GPX files according to map image order in markdown."""
    gpx_tag2 = tmp_path / "bakio-guernica.gpx"
    gpx_tag1 = tmp_path / "bilbao-bakio.gpx"
    gpx_tag2.touch()
    gpx_tag1.touch()

    index_md = tmp_path / "index.md"
    index_md.write_text(
        "# Nordspanien Tour\n"
        "![Tag 1: Bilbao → Bakio](maps/tag-01-bilbao-bakio.png)\n"
        "![Tag 2: Bakio → Guernica](maps/tag-02-bakio-guernica.png)\n",
        encoding="utf-8",
    )

    ordered = order_gpx_by_markdown([gpx_tag2, gpx_tag1], index_md)
    assert ordered == [gpx_tag1, gpx_tag2]


def test_combine_gpx_files_empty():
    """Empty file list returns empty string."""
    assert combine_gpx_files([]) == ""


def test_combine_gpx_files_multiple(tmp_path: Path):
    """Combine multiple single-track GPX files into one valid multi-track GPX."""
    tour_dir = tmp_path / "trips" / "bike" / "test-tour"
    gpx_dir = tour_dir / "gpx"
    gpx_dir.mkdir(parents=True)

    gpx1 = gpx_dir / "stage-1.gpx"
    gpx1.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">\n'
        '  <trk><name>Stage 1</name><trkseg><trkpt lat="52.5" lon="13.4"></trkpt></trkseg></trk>\n'
        "</gpx>",
        encoding="utf-8",
    )

    gpx2 = gpx_dir / "stage-2.gpx"
    gpx2.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">\n'
        '  <trk><name>Stage 2</name><trkseg><trkpt lat="52.6" lon="13.5"></trkpt></trkseg></trk>\n'
        "</gpx>",
        encoding="utf-8",
    )

    combined = combine_gpx_files([gpx1, gpx2])
    assert "<gpx" in combined
    assert "Stage 1" in combined
    assert "Stage 2" in combined
