from collections import Counter
import json
from math import comb
from pathlib import Path
from statistics import mean

from bandido_alcatraz.evaluate import wilson_interval_95
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, WaterSpaceV3Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


ROOT = Path(__file__).parents[1]
SEEDS = range(2000, 2400)


def exact_two_sided_paired_binomial(v4_only: int, control_only: int):
    discordant = v4_only + control_only
    if discordant == 0:
        return None
    tail = sum(
        comb(discordant, k)
        for k in range(min(v4_only, control_only) + 1)
    ) / (2 ** discordant)
    return min(1.0, 2 * tail)


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
    per_seed = {}
    for seed, result in zip(SEEDS, results, strict=True):
        equipment_ready = is_equipment_ready(result.raincoats, result.ropes)
        per_seed[str(seed)] = {
            "won": result.won,
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
            "reason": result.reason,
        }
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
            sorted(Counter(
                result.reason
                for result in results
                if not result.won
            ).items())
        ),
        "step_limit_count": sum(
            result.reason == "step_limit" for result in results
        ),
        "per_seed": per_seed,
    }


def paired(v4, control):
    v4_only_seeds = []
    control_only_seeds = []
    both_win_seeds = []
    both_lose_seeds = []
    for seed in SEEDS:
        v4_won = v4["per_seed"][str(seed)]["won"]
        control_won = control["per_seed"][str(seed)]["won"]
        if v4_won and control_won:
            both_win_seeds.append(seed)
        elif v4_won:
            v4_only_seeds.append(seed)
        elif control_won:
            control_only_seeds.append(seed)
        else:
            both_lose_seeds.append(seed)

    v4_only = len(v4_only_seeds)
    control_only = len(control_only_seeds)
    p_value = exact_two_sided_paired_binomial(v4_only, control_only)
    return {
        "v4_only_wins": v4_only,
        "water_space_v3_only_wins": control_only,
        "both_win": len(both_win_seeds),
        "both_lose": len(both_lose_seeds),
        "discordant_seeds": v4_only + control_only,
        "v4_only_seed_ids": v4_only_seeds,
        "water_space_v3_only_seed_ids": control_only_seeds,
        "both_win_seed_ids": both_win_seeds,
        "both_lose_seed_ids": both_lose_seeds,
        "test": {
            "method": "exact two-sided paired binomial / McNemar on discordant outcomes",
            "null_discordant_probability": 0.5,
            "p_value": p_value,
            "informative": p_value is not None,
        },
    }


def classify(v4_wins, control_wins, p_value):
    if v4_wins <= control_wins:
        return "signal weakened"
    if p_value is not None and p_value <= 0.05:
        return "stability confirmed on this holdout"
    return "directionally positive but inconclusive"


def main():
    from bandido_alcatraz.rules import RULESET_ID
    if RULESET_ID != 'v0-threshold-equipment':
        raise SystemExit('Historical experiment: use its pinned historical source; current canonical rules differ. No simulation was run.')
    # Sanity-check the exact test against the pre-registered prior result.
    assert exact_two_sided_paired_binomial(5, 1) == 0.21875
    assert exact_two_sided_paired_binomial(0, 0) is None

    deck = load_real_deck(ROOT / "data")
    v4 = evaluate(BoundedMergeV4Policy(setup_weight=250), deck)
    control = evaluate(WaterSpaceV3Policy(), deck)
    paired_result = paired(v4, control)
    p_value = paired_result["test"]["p_value"]

    result = {
        "experiment": "real-deck-policy-v4-stability-holdout",
        "date": "2026-09-21",
        "pre_registration": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5766792984"
        ),
        "rules_variant": "v0-threshold-equipment",
        "photographed_deck": True,
        "deck_file": "data/deck-v1.json",
        "start_side": "easy-5-exit",
        "hand_size": 3,
        "equipment_thresholds": {
            "raincoats_min": 3,
            "ropes_min": 2,
        },
        "seed_range": [2000, 2399],
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
        "metrics": {
            "bounded_merge_v4_250": v4,
            "water_space_v3": control,
        },
        "paired": paired_result,
        "pre_declared_classification": classify(
            v4["wins"], control["wins"], p_value
        ),
    }
    print("STABILITY_RESULT_JSON=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
