from collections import Counter
import json
from pathlib import Path
from statistics import mean

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    BoundedMergeV4Policy,
    CombinedV2Policy,
    CombinedV3Policy,
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


def evaluate(policy, seeds, deck):
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
    return summarize(results), [
        seed
        for seed, result in zip(seeds, results, strict=True)
        if result.won
    ]


def selection_key(summary):
    return (
        summary["wins"],
        summary["open_tunnels_le_5"],
        -summary["mean_open_tunnels"],
        summary["exit_equipment_water_ready"],
        summary["water_clear"],
        -summary["mean_visible_water"],
    )


def main():
    from bandido_alcatraz.rules import RULESET_ID
    if RULESET_ID != 'v0-threshold-equipment':
        raise SystemExit('Historical experiment: use its pinned historical source; current canonical rules differ. No simulation was run.')
    deck = load_real_deck(ROOT / "data")
    training_seeds = range(30)
    held_out_seeds = range(100, 130)

    candidate_weights = [250, 500, 1000]
    training = {}
    for weight in candidate_weights:
        summary, wins = evaluate(
            BoundedMergeV4Policy(setup_weight=weight),
            training_seeds,
            deck,
        )
        training[str(weight)] = {
            "summary": summary,
            "winning_seeds": wins,
        }

    context_training = {}
    for name, policy in {
        "water_space_v3": WaterSpaceV3Policy(),
        "combined_v3": CombinedV3Policy(),
    }.items():
        summary, wins = evaluate(policy, training_seeds, deck)
        context_training[name] = {
            "summary": summary,
            "winning_seeds": wins,
        }

    best_weight = max(
        candidate_weights,
        key=lambda weight: selection_key(
            training[str(weight)]["summary"]
        ),
    )

    held_out = {}
    held_policies = {
        f"bounded_merge_v4_{best_weight}": BoundedMergeV4Policy(
            setup_weight=best_weight
        ),
        "water_space_v3": WaterSpaceV3Policy(),
        "combined_v3": CombinedV3Policy(),
        "combined_v2": CombinedV2Policy(),
    }
    for name, policy in held_policies.items():
        summary, wins = evaluate(policy, held_out_seeds, deck)
        held_out[name] = {
            "summary": summary,
            "winning_seeds": wins,
        }

    print(
        json.dumps(
            {
                "rules_variant": "v0-threshold-equipment",
                "start_side": "easy-5-exit",
                "hand_size": 3,
                "training_seed_range": [0, 29],
                "held_out_seed_range": [100, 129],
                "candidate_weights": candidate_weights,
                "training": training,
                "context_training": context_training,
                "selected_weight": best_weight,
                "held_out": held_out,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
