from dataclasses import asdict
import json

from bandido_alcatraz.fixtures import synthetic_deck, synthetic_start
from bandido_alcatraz.policies import (
    GreedyV0Policy,
    MinOpenTunnelsPolicy,
    RandomLegalPolicy,
)
from bandido_alcatraz.simulate import run_many


def main() -> None:
    seeds = range(200)
    common = {
        "start_card": synthetic_start(),
        "deck": synthetic_deck(),
        "hand_size": 3,
        "seeds": seeds,
    }
    result = {
        "warning": "synthetic fixture only; not a Bandido Alcatraz win-rate estimate",
        "seed_range": [0, 199],
        "random_legal": asdict(run_many(policy=RandomLegalPolicy(), **common)),
        "min_open_tunnels": asdict(
            run_many(policy=MinOpenTunnelsPolicy(), **common)
        ),
        "greedy_v0": asdict(run_many(policy=GreedyV0Policy(), **common)),
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
