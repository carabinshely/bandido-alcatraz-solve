import json
from pathlib import Path

from bandido_alcatraz.proxy import card_from_port_geometry


ROOT = Path(__file__).parents[1]


def test_transcribed_proxy_end_cards_compile_to_engine_cards() -> None:
    data = json.loads(
        (ROOT / "data" / "proxy-bandido-covid-v0.json").read_text()
    )

    transcribed = [
        slot for slot in data["slots"] if slot["geometry"] is not None
    ]
    assert len(transcribed) == 10

    for slot in transcribed:
        geometry = slot["geometry"]
        card = card_from_port_geometry(
            slot["id"],
            external_ports=geometry["external_ports"],
            internal_bridge=geometry["internal_bridge"],
        )

        assert len(card.cells) == 2


def test_internal_bridge_is_symmetric_between_half_cells() -> None:
    card = card_from_port_geometry(
        "bridge",
        external_ports=["W", "E"],
        internal_bridge=True,
    )

    left, right = card.cells
    assert "E" in {edge.value for edge in left.tunnel_edges}
    assert "W" in {edge.value for edge in right.tunnel_edges}
