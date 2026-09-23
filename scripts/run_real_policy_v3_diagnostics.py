from collections import Counter
import json
from pathlib import Path
from statistics import mean

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    CombinedV2Policy,
    CombinedV3Policy,
    MergeAwareV3Policy,
    WaterSpaceV3Policy,
)
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


ROOT = Path(__file__).parents[1]


def summarize(results):
    return {
        "games": len(results),
        "wins": sum(result.won for result in results),
        "mean_open_tunnels": mean(result.open_tunnels for result in results),
        "open_tunnels_le_5": sum(
            result.open_tunnels <= 5 for result in results
        ),
        "water_clear": sum(
            result.visible_water_cells == 0 for result in results
        ),
        "mean_visible_water": mean(
            result.visible_water_cells for result in results
        ),
        "equipment_ready": sum(
            is_equipment_ready(result.raincoats, result.ropes)
            for result in results
        ),
        "exit_placed": sum(result.exit_placed for result in results),
        "exit_equipment_water_ready": sum(
            result.exit_placed
            and result.visible_water_cells == 0
            and is_equipment_ready(result.raincoats, result.ropes)
            for result in results
        ),
        "failure_reasons": dict(
            Counter(result.reason for result in results)
        ),
    }


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    seeds = range(50)
    policies = {
        "combined_v2": CombinedV2Policy(),
        "merge_aware_v3": MergeAwareV3Policy(),
        "water_space_v3": WaterSpaceV3Policy(),
        "combined_v3": CombinedV3Policy(),
    }

    summaries = {}
    winning_seeds = {}
    for name, policy in policies.items():
        results = [
            play_game(
                start_card=deck.start_easy,
                deck=deck.draw_deck(),
                hand_size=3,
                policy=policy,
                seed=seed,
            )
            for seed in seeds
        ]
        summaries[name] = summarize(results)
        winning_seeds[name] = [
            seed
            for seed, result in zip(seeds, results, strict=True)
            if result.won
        ]

    print(
        json.dumps(
            {
                "rules_variant": "v0-threshold-equipment",
                "start_side": "easy-5-exit",
                "hand_size": 3,
                "seed_range": [0, 49],
                "policies": summaries,
                "winning_seeds": winning_seeds,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
