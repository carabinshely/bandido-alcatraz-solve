import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]


_ROTATE_180 = {
    "W": "E",
    "E": "W",
    "NW": "SE",
    "NE": "SW",
    "SW": "NE",
    "SE": "NW",
}


def _canonical_ports(ports: list[str]) -> tuple[str, ...]:
    original = tuple(sorted(ports))
    rotated = tuple(sorted(_ROTATE_180[port] for port in ports))
    return min(original, rotated)


def _data() -> dict:
    return json.loads(
        (ROOT / "data" / "proxy-bandido-covid-v0.json").read_text()
    )


def test_covid_proxy_slot_inventory_matches_published_distribution() -> None:
    data = _data()
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
    data = _data()

    assert data["complete_geometry"] is False
    assert sum(slot["geometry"] is not None for slot in data["slots"]) == 10
    assert data["must_not_be_used_as"] == "Bandido Alcatraz deck definition"


def test_transcribed_end_cards_match_published_family_multiplicities() -> None:
    data = _data()
    end_slots = [slot for slot in data["slots"] if slot["kind"] == "end"]

    assert all(slot["geometry"] is not None for slot in end_slots)

    families = Counter(
        _canonical_ports(slot["geometry"]["external_ports"])
        for slot in end_slots
    )

    assert len(families) == 6
    assert sorted(families.values()) == [1, 1, 2, 2, 2, 2]


def test_proxy_ports_use_declared_notation() -> None:
    data = _data()
    allowed = set(data["port_notation"])

    for slot in data["slots"]:
        geometry = slot["geometry"]
        if geometry is None:
            continue
        ports = geometry["external_ports"]
        assert len(ports) == len(set(ports))
        assert set(ports) <= allowed
        assert geometry["confidence"] == "proxy"
