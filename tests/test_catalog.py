from bandido_alcatraz.catalog import validate_complete_catalog


def test_empty_catalog_is_reported_incomplete() -> None:
    errors = validate_complete_catalog([])
    assert "expected 68 cards, got 0" in errors
    assert "expected 4 water cards, got 0" in errors
    assert "expected 8 rope cards, got 0" in errors
    assert "expected 12 raincoat cards, got 0" in errors
