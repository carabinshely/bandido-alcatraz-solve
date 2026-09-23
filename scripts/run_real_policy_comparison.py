from dataclasses import asdict
import json
from pathlib import Path

from bandido_alcatraz.evaluate import evaluate_policies
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import GeometryAwareV1Policy, GreedyV0Policy


ROOT = Path(__file__).parents[1]


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    seeds = range(100)

    suite = evaluate_policies(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        policies={
            "greedy_v0": GreedyV0Policy(),
            "geometry_aware_v1": GeometryAwareV1Policy(),
        },
        seeds=seeds,
    )
    payload = {
        "rules_variant": "v0-threshold-equipment",
        "warning": (
            "Real photographed deck. Equipment uses project-v0 thresholds "
            "raincoats>=3 and ropes>=2."
        ),
        "start_side": "easy-5-exit",
        "hand_size": 3,
        "seed_range": [0, 99],
        **asdict(suite),
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
