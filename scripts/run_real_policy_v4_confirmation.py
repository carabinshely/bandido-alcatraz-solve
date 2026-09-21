from collections import Counter
import json
from pathlib import Path
from statistics import mean

from bandido_alcatraz.evaluate import wilson_interval_95
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    BoundedMergeV4Policy,
    CombinedV2Policy,
    WaterSpaceV3Policy,
)
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


ROOT = Path(__file__).parents[1]
SEEDS = range(1000, 1100)


def evaluate(policy, deck):
    results = [
        play_game(
            start_card=deck.start_easy,
            deck=deck.draw_deck(),
            hand_size=3,
            policy=policy,
            seed=seed,
        )
        for seed in SEEDS
    ]
    wins = sum(result.won for result in results)
    interval = wilson_interval_95(wins, len(results))
    return {
        "games": len(results),
        "wins": wins,
        "win_rate": wins / len(results),
        "wilson_95": {
            "low": interval.low,
            "high": interval.high,
        },
        "winning_seeds": [
            seed
            for seed, result in zip(SEEDS, results, strict=True)
            if result.won
        ],
        "mean_final_open_tunnels": mean(
            result.open_tunnels for result in results
        ),
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
            sorted(
                Counter(
                    result.reason
                    for result in results
                    if not result.won
                ).items()
            )
        ),
        "_wins_by_seed": {
            str(seed): result.won
            for seed, result in zip(SEEDS, results, strict=True)
        },
    }


def paired(candidate, control):
    candidate_wins = candidate["_wins_by_seed"]
    control_wins = control["_wins_by_seed"]
    counts = {
        "v4_only_wins": 0,
        "control_only_wins": 0,
        "both_win": 0,
        "both_lose": 0,
    }
    for seed in SEEDS:
        v4_won = candidate_wins[str(seed)]
        control_won = control_wins[str(seed)]
        if v4_won and control_won:
            counts["both_win"] += 1
        elif v4_won:
            counts["v4_only_wins"] += 1
        elif control_won:
            counts["control_only_wins"] += 1
        else:
            counts["both_lose"] += 1
    return counts


def strip_internal(summary):
    return {
        key: value
        for key, value in summary.items()
        if not key.startswith("_")
    }


def main():
    deck = load_real_deck(ROOT / "data")
    policy_objects = {
        "bounded_merge_v4_250": BoundedMergeV4Policy(setup_weight=250),
        "water_space_v3": WaterSpaceV3Policy(),
        "combined_v2": CombinedV2Policy(),
    }
    raw = {
        name: evaluate(policy, deck)
        for name, policy in policy_objects.items()
    }

    result = {
        "experiment": "real-deck-policy-v4-confirmation",
        "rules_variant": "v0-threshold-equipment",
        "photographed_deck": True,
        "deck_file": "data/deck-v1.json",
        "start_side": "easy-5-exit",
        "hand_size": 3,
        "equipment_thresholds": {
            "raincoats_min": 3,
            "ropes_min": 2,
        },
        "seed_range": [1000, 1099],
        "policies": {
            "bounded_merge_v4_250": {
                "class": "BoundedMergeV4Policy",
                "parameters": {"setup_weight": 250},
            },
            "water_space_v3": {
                "class": "WaterSpaceV3Policy",
                "parameters": {},
            },
            "combined_v2": {
                "class": "CombinedV2Policy",
                "parameters": {},
            },
        },
        "metrics": {
            name: strip_internal(summary)
            for name, summary in raw.items()
        },
        "paired": {
            "v4_vs_water_space_v3": paired(
                raw["bounded_merge_v4_250"],
                raw["water_space_v3"],
            ),
            "v4_vs_combined_v2": paired(
                raw["bounded_merge_v4_250"],
                raw["combined_v2"],
            ),
        },
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
