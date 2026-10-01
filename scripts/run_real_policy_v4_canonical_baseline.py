import argparse
from collections import Counter
import json
import os
from pathlib import Path
from statistics import mean, median

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, WaterSpaceV3Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


ROOT = Path(__file__).parents[1]
SEEDS = range(2000, 2400)


def final_record(result):
    equipment_ready = is_equipment_ready(result.raincoats, result.ropes)
    return {
        "won": result.won,
        "failure_reason": result.reason,
        "turns": result.turns,
        "final_open_tunnels": result.open_tunnels,
        "visible_water": result.visible_water_cells,
        "raincoats": result.raincoats,
        "ropes": result.ropes,
        "equipment_ready": equipment_ready,
        "exit_placed": result.exit_placed,
        "exit_equipment_water_ready": (
            result.exit_placed
            and result.visible_water_cells == 0
            and equipment_ready
        ),
    }


def aggregate(records):
    rows = list(records.values())
    wins = [seed for seed, row in records.items() if row["won"]]
    failures = Counter(
        row["failure_reason"] for row in rows if not row["won"]
    )
    return {
        "games": len(rows),
        "wins": len(wins),
        "win_rate": len(wins) / len(rows),
        "winning_seed_ids": [int(seed) for seed in wins],
        "failure_reason_counts": dict(sorted(failures.items())),
        "mean_final_open_tunnels": mean(
            row["final_open_tunnels"] for row in rows
        ),
        "median_final_open_tunnels": median(
            row["final_open_tunnels"] for row in rows
        ),
        "final_open_tunnels_le_5": sum(
            row["final_open_tunnels"] <= 5 for row in rows
        ),
        "water_clear": sum(row["visible_water"] == 0 for row in rows),
        "mean_visible_water": mean(row["visible_water"] for row in rows),
        "equipment_ready": sum(row["equipment_ready"] for row in rows),
        "exit_placed": sum(row["exit_placed"] for row in rows),
        "exit_equipment_water_ready": sum(
            row["exit_equipment_water_ready"] for row in rows
        ),
        "step_limit": failures.get("step_limit", 0),
        "mean_turns": mean(row["turns"] for row in rows),
    }


def main():
    from bandido_alcatraz.rules import RULESET_ID
    if RULESET_ID != 'v0-threshold-equipment':
        raise SystemExit('Historical experiment: use its pinned historical source; current canonical rules differ. No simulation was run.')
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    deck = load_real_deck(ROOT / "data")
    policies = {
        "bounded_merge_v4_250": BoundedMergeV4Policy(setup_weight=250),
        "water_space_v3": WaterSpaceV3Policy(),
    }
    records = {}
    for policy_name, policy in policies.items():
        records[policy_name] = {}
        for seed in SEEDS:
            result = play_game(
                start_card=deck.start_easy,
                deck=deck.draw_deck(),
                hand_size=3,
                policy=policy,
                seed=seed,
            )
            records[policy_name][str(seed)] = final_record(result)

    payload = {
        "experiment": "post-fix-canonical-baseline-process",
        "hash_seed": os.environ.get("PYTHONHASHSEED"),
        "seed_range": [2000, 2399],
        "fresh_seeds_used": False,
        "rules_variant": "v0-threshold-equipment",
        "deck_file": "data/deck-v1.json",
        "start_side": "easy-5-exit",
        "hand_size": 3,
        "policies": {
            "bounded_merge_v4_250": {
                "class": "BoundedMergeV4Policy",
                "parameters": {"setup_weight": 250},
            },
            "water_space_v3": {
                "class": "WaterSpaceV3Policy",
                "parameters": {},
            },
        },
        "records": records,
        "aggregate": {
            name: aggregate(policy_records)
            for name, policy_records in records.items()
        },
    }
    Path(args.output).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "CANONICAL_BASELINE_SUMMARY="
        + json.dumps(
            {
                "hash_seed": payload["hash_seed"],
                "aggregate": payload["aggregate"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
