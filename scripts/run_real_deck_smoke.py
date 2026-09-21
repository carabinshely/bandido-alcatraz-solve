from dataclasses import asdict
import json
from pathlib import Path

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    GreedyV0Policy,
    MinOpenTunnelsPolicy,
    RandomLegalPolicy,
)
from bandido_alcatraz.simulate import run_many


ROOT = Path(__file__).parents[1]


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    seeds = range(20)

    common = {
        "start_card": deck.start_easy,
        "deck": deck.draw_deck(),
        "hand_size": 3,
        "seeds": seeds,
    }
    result = {
        "rules_variant": "v0-threshold-equipment",
        "warning": (
            "Real photographed deck, but project v0 intentionally treats "
            "equipment as raincoats>=3 and ropes>=2."
        ),
        "start_side": "easy-5-exit",
        "hand_size": 3,
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
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
