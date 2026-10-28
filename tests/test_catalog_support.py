import hashlib
from pathlib import Path
from random import Random

from bandido_alcatraz.catalog_support import CatalogSupportPolicy
from bandido_alcatraz.game import GameState
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.setup import SOLO_EASY


def test_confirmed_catalog_support_policy_is_exact_and_legal() -> None:
    source = Path(__file__).parents[1] / "src/bandido_alcatraz/catalog_support.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "6b668193a5a763561ca0c91fd15be3e3dbbaa38b2283b9085b84365ca3718b4a"
    )

    deck = load_real_deck(Path(__file__).parents[1] / "data")
    state = GameState.new(
        start_card=deck.start_for_setup(SOLO_EASY),
        deck=deck.draw_deck(),
        hand_size=SOLO_EASY.hand_size,
        rng=Random(0),
        setup=SOLO_EASY,
    )
    policy = CatalogSupportPolicy(deck.ordinary_cards, deck.exit_card)
    observation = state.observation()
    move = policy.choose(observation, Random(1))
    assert move in observation.legal_moves()
