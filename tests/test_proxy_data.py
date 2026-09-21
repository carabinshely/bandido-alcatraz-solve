import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_covid_proxy_slot_inventory_matches_published_distribution() -> None:
    data = json.loads(
        (ROOT / "data" / "proxy-bandido-covid-v0.json").read_text()
    )
    slots = data["slots"]

    assert len(slots) == 32
    assert len({slot["id"] for slot in slots}) == 32
    assert sum(slot["kind"] == "basic" for slot in slots) == 22
    assert sum(slot["kind"] == "end" for slot in slots) == 10
    assert data["expected_counts"] == {
        "tunnel_cards": 32,
        "basic_slots": 22,
        "end_slots": 10,
    }


def test_covid_proxy_geometry_is_explicitly_incomplete() -> None:
    data = json.loads(
        (ROOT / "data" / "proxy-bandido-covid-v0.json").read_text()
    )

    assert data["complete_geometry"] is False
    assert all(slot["geometry"] is None for slot in data["slots"])
    assert data["must_not_be_used_as"] == "Bandido Alcatraz deck definition"
