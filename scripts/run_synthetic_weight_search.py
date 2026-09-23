from dataclasses import asdict
import json

from bandido_alcatraz.fixtures import synthetic_deck, synthetic_start
from bandido_alcatraz.optimize import search_weights, weight_grid
from bandido_alcatraz.strategy import PolicyWeights


def main() -> None:
    candidates = weight_grid(
        base=PolicyWeights(),
        values={
            "collect_needed": [1_000, 10_000],
            "delta_open_tunnels": [25, 100, 400],
            "places_exit_early": [-1_000, -5_000],
        },
    )
    result = search_weights(
        start_card=synthetic_start(),
        deck=synthetic_deck(),
        hand_size=3,
        candidates=candidates,
        training_seeds=range(0, 40),
        evaluation_seeds=range(10_000, 10_040),
    )
    payload = {
        "warning": "synthetic fixture only; not a Bandido Alcatraz strategy estimate",
        "training_seed_range": [0, 39],
        "evaluation_seed_range": [10_000, 10_039],
        **asdict(result),
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
