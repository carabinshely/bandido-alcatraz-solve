from collections import Counter
from pathlib import Path

from bandido_alcatraz.board import Board
from bandido_alcatraz.model import Material
from bandido_alcatraz.physical_deck import load_real_deck


ROOT = Path(__file__).parents[1]


def test_real_deck_loads_all_physical_cards() -> None:
    deck = load_real_deck(ROOT / "data")

    assert len(deck.ordinary_cards) == 68
    assert len(deck.draw_deck()) == 69
    assert deck.exit_card.is_exit


def test_real_deck_special_counts_match_physical_inventory() -> None:
    deck = load_real_deck(ROOT / "data")

    materials = Counter(card.material for card in deck.ordinary_cards)
    assert materials[Material.RAINCOAT] == 12
    assert materials[Material.ROPE] == 8
    assert sum(card.has_water for card in deck.ordinary_cards) == 4


def test_real_start_and_exit_open_tunnel_counts() -> None:
    deck = load_real_deck(ROOT / "data")

    easy = Board()
    easy.seed(deck.start_easy)
    assert easy.open_tunnels == 5

    normal = Board()
    normal.seed(deck.start_normal)
    assert normal.open_tunnels == 6

    exit_board = Board()
    exit_board.seed(deck.exit_card)
    assert exit_board.open_tunnels == 1


def test_real_geometry_family_multiplicities_cover_all_cards() -> None:
    import json

    raw = json.loads((ROOT / "data" / "deck-v1.json").read_text())
    families = raw["families"]

    assert len(families) == 30
    assert sum(family["multiplicity"] for family in families) == 68
    assert sorted(
        (family["multiplicity"] for family in families),
        reverse=True,
    ) == [
        4, 4, 4,
        3, 3, 3, 3, 3, 3, 3, 3,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        1, 1, 1, 1, 1, 1,
    ]
