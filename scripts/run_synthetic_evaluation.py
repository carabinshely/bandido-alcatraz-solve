from dataclasses import asdict
import json

from bandido_alcatraz.evaluate import evaluate_policies
from bandido_alcatraz.fixtures import synthetic_deck, synthetic_start
from bandido_alcatraz.policies import (
    GreedyV0Policy,
    MinOpenTunnelsPolicy,
    RandomLegalPolicy,
)


def main() -> None:
    suite = evaluate_policies(
        start_card=synthetic_start(),
        deck=synthetic_deck(),
        hand_size=3,
        policies={
            "random_legal": RandomLegalPolicy(),
            "min_open_tunnels": MinOpenTunnelsPolicy(),
            "greedy_v0": GreedyV0Policy(),
        },
        seeds=range(500),
    )
    payload = {
        "warning": "synthetic fixture only; not a Bandido Alcatraz estimate",
        "seed_range": [0, 499],
        **asdict(suite),
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
