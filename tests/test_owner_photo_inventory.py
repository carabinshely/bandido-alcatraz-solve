import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _inventory() -> dict:
    return json.loads(
        (ROOT / "data" / "owner-photo-inventory-v0.json").read_text()
    )


def test_owner_photo_slot_inventory_is_complete() -> None:
    data = _inventory()
    slots = data["slots"]

    assert len(slots) == 71
    assert len({slot["id"] for slot in slots}) == 71

    roles = Counter(slot["role"] for slot in slots)
    assert roles == {"ordinary": 68, "start": 2, "exit": 1}


def test_owner_photo_special_counts_match_published_deck() -> None:
    data = _inventory()
    ordinary = [slot for slot in data["slots"] if slot["role"] == "ordinary"]

    materials = Counter(slot["material"] for slot in ordinary)
    assert materials["raincoat"] == 12
    assert materials["rope"] == 8
    assert sum(slot["water"] for slot in ordinary) == 4


def test_owner_photo_start_is_two_faces_of_one_physical_card() -> None:
    data = _inventory()
    counts = data["counts"]

    assert counts["start_faces"] == 2
    assert counts["distinct_start_cards"] == 1
    assert counts["ordinary_cards"] + counts["exit_cards"] == 69
    assert (
        counts["ordinary_cards"]
        + counts["exit_cards"]
        + counts["distinct_start_cards"]
        == 70
    )
    assert (
        counts["ordinary_cards"]
        + counts["exit_cards"]
        + counts["start_faces"]
        == counts["photographed_faces"]
        == 71
    )


def test_owner_photo_images_are_not_persisted_in_git() -> None:
    data = _inventory()

    assert data["images_committed"] is False
    assert all(
        slot["source"] == "owner-photo-set:2026-09-21"
        for slot in data["slots"]
    )


def test_geometry_is_separate_from_visual_metadata_transcription() -> None:
    data = _inventory()

    assert all(slot["geometry"] is None for slot in data["slots"])


def test_owner_photo_start_variants_are_identified() -> None:
    data = _inventory()
    starts = {
        slot["start_variant"]: slot
        for slot in data["slots"]
        if slot["role"] == "start"
    }

    assert set(starts) == {"easy", "normal"}
    assert starts["easy"]["id"] == "photo-1-r1-c1"
    assert starts["normal"]["id"] == "photo-2-r1-c1"


def test_owner_photo_water_halves_are_two_top_two_bottom() -> None:
    data = _inventory()
    water = [
        slot for slot in data["slots"]
        if slot["role"] == "ordinary" and slot["water"]
    ]

    assert Counter(slot["water_half"] for slot in water) == {
        "top": 2,
        "bottom": 2,
    }
    assert all(
        slot["water_half"] is None
        for slot in data["slots"]
        if not slot["water"]
    )
