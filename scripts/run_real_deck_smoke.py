from dataclasses import asdict
import json
from pathlib import Path

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    GeometryAwareV1Policy,
    GreedyV0Policy,
    MinOpenTunnelsPolicy,
    RandomLegalPolicy,
)
from bandido_alcatraz.simulate import run_many
from bandido_alcatraz.rules import RULESET_ID
from bandido_alcatraz.setup import SOLO_EASY


ROOT = Path(__file__).parents[1]


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    seeds = range(20)

    common = {
        "start_card": deck.start_for_setup(SOLO_EASY),
        "deck": deck.draw_deck(),
        "hand_size": SOLO_EASY.hand_size,
        "seeds": seeds,
        "setup": SOLO_EASY,
    }
    result = {
        "rules_variant": RULESET_ID,
        "setup_id": SOLO_EASY.setup_id,
        "warning": "Routine spent-seed smoke, not performance evidence or confirmation",
        "start_side": "easy-5-exit",
        "hand_size": SOLO_EASY.hand_size,
        "seed_range": [0, 19],
        "random_legal": asdict(
            run_many(policy=RandomLegalPolicy(), **common)
        ),
        "min_open_tunnels": asdict(
            run_many(policy=MinOpenTunnelsPolicy(), **common)
        ),
        "greedy_v0": asdict(
            run_many(policy=GreedyV0Policy(), **common)
        ),
        "geometry_aware_v1": asdict(
            run_many(policy=GeometryAwareV1Policy(), **common)
        ),
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
