from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
from statistics import mean
import time

from bandido_alcatraz.evaluate import wilson_interval_95
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    BoundedMergeV4Policy,
    VisibleHandTwoActionV6Policy,
)
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


ROOT = Path(__file__).parents[1]
SEEDS = tuple(range(1000, 1100))
WORKER22_RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v6"
    / "spent-development-1000-1099-2026-09-28.json"
)
OUTPUT = (
    ROOT
    / "artifacts"
    / "worker23-v6-current-model-spent-development-1000-1099.json"
)
PREREGISTRATION_URL = (
    "https://github.com/carabinshely/bandido-alcatraz-solve/"
    "issues/2#issuecomment-5864856150"
)
STARTING_MAIN = "9e337f23e46746240c81ae211e81b46f7b9ef335"
WATER_FIX_COMMIT = "87b8d3eeff3aaf53c5e887679360652a3f9e8d04"
V6_WORKERS = 4

PER_SEED_FIELDS = (
    "seed",
    "won",
    "reason",
    "turns",
    "final_open_tunnels",
    "visible_water",
    "raincoats",
    "ropes",
    "equipment_ready",
    "exit_placed",
    "exit_equipment_water_ready",
)


def final_record(seed: int, result) -> dict[str, object]:
    equipment_ready = is_equipment_ready(result.raincoats, result.ropes)
    return {
        "seed": seed,
        "won": result.won,
        "reason": result.reason,
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


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    wins = sum(bool(record["won"]) for record in records)
    interval = wilson_interval_95(wins, len(records))
    failure_counter = Counter(
        str(record["reason"])
        for record in records
        if not bool(record["won"])
    )
    failure_reasons = {
        key: failure_counter.get(key, 0)
        for key in (
            "closed_tunnels_conditions_failed",
            "deck_exhausted",
            "no_legal_move",
            "step_limit",
        )
    }
    return {
        "games": len(records),
        "wins": wins,
        "win_rate": wins / len(records),
        "wilson_95": {
            "low": interval.low,
            "high": interval.high,
        },
        "winning_seeds": [
            int(record["seed"]) for record in records if bool(record["won"])
        ],
        "mean_final_open_tunnels": mean(
            int(record["final_open_tunnels"]) for record in records
        ),
        "open_tunnels_le_5": sum(
            int(record["final_open_tunnels"]) <= 5 for record in records
        ),
        "water_clear": sum(
            int(record["visible_water"]) == 0 for record in records
        ),
        "mean_visible_water": mean(
            int(record["visible_water"]) for record in records
        ),
        "equipment_ready": sum(
            bool(record["equipment_ready"]) for record in records
        ),
        "exit_placed": sum(bool(record["exit_placed"]) for record in records),
        "exit_equipment_water_ready": sum(
            bool(record["exit_equipment_water_ready"]) for record in records
        ),
        "failure_reasons": failure_reasons,
        "step_limit": failure_reasons["step_limit"],
        "total_turns": sum(int(record["turns"]) for record in records),
        "mean_turns": mean(int(record["turns"]) for record in records),
    }


def evaluate_v4(deck) -> tuple[list[dict[str, object]], float]:
    started = time.perf_counter()
    records = [
        final_record(
            seed,
            play_game(
                start_card=deck.start_easy,
                deck=deck.draw_deck(),
                hand_size=3,
                policy=BoundedMergeV4Policy(setup_weight=250),
                seed=seed,
            ),
        )
        for seed in SEEDS
    ]
    return records, time.perf_counter() - started


def evaluate_v6_seed(seed: int) -> dict[str, object]:
    deck = load_real_deck(ROOT / "data")
    result = play_game(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        policy=VisibleHandTwoActionV6Policy(),
        seed=seed,
    )
    return final_record(seed, result)


def evaluate_v6() -> tuple[list[dict[str, object]], float]:
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=V6_WORKERS) as executor:
        records = list(executor.map(evaluate_v6_seed, SEEDS, chunksize=1))
    return records, time.perf_counter() - started


def compare_v4_replay(
    actual_records: list[dict[str, object]],
    actual_metrics: dict[str, object],
    authority: dict[str, object],
) -> dict[str, object]:
    expected_records = authority["v4_per_seed"]
    expected_metrics = authority["v4_metrics"]

    if len(expected_records) != 100:
        return {
            "passed": False,
            "per_seed_exact_matches": 0,
            "aggregate_match": False,
            "mismatches": [
                {
                    "kind": "authority_record_count",
                    "expected": 100,
                    "actual": len(expected_records),
                }
            ],
        }

    mismatches: list[dict[str, object]] = []
    exact_count = 0
    for expected, actual in zip(expected_records, actual_records, strict=True):
        expected_view = {field: expected[field] for field in PER_SEED_FIELDS}
        actual_view = {field: actual[field] for field in PER_SEED_FIELDS}
        if expected_view == actual_view:
            exact_count += 1
        else:
            mismatches.append(
                {
                    "kind": "per_seed",
                    "seed": actual["seed"],
                    "expected": expected_view,
                    "actual": actual_view,
                }
            )

    aggregate_match = actual_metrics == expected_metrics
    if not aggregate_match:
        mismatches.append(
            {
                "kind": "aggregate",
                "expected": expected_metrics,
                "actual": actual_metrics,
            }
        )

    return {
        "passed": exact_count == 100 and aggregate_match,
        "per_seed_exact_matches": exact_count,
        "aggregate_match": aggregate_match,
        "mismatches": mismatches,
    }


def paired(v4_records, v6_records) -> dict[str, object]:
    v4 = {int(record["seed"]): bool(record["won"]) for record in v4_records}
    v6 = {int(record["seed"]): bool(record["won"]) for record in v6_records}
    v6_only = [seed for seed in SEEDS if v6[seed] and not v4[seed]]
    v4_only = [seed for seed in SEEDS if v4[seed] and not v6[seed]]
    both = [seed for seed in SEEDS if v4[seed] and v6[seed]]
    neither = [seed for seed in SEEDS if not v4[seed] and not v6[seed]]
    return {
        "v6_only_wins": len(v6_only),
        "v4_only_wins": len(v4_only),
        "both_win": len(both),
        "both_lose": len(neither),
        "v6_only_seed_ids": v6_only,
        "v4_only_seed_ids": v4_only,
        "both_win_seed_ids": both,
        "both_lose_seed_ids": neither,
        "discordant_seed_ids": sorted(v6_only + v4_only),
        "net_paired_win_count_change": len(v6_only) - len(v4_only),
    }


def write_payload(payload: dict[str, object]) -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "WORKER23_RESULT="
        + json.dumps(
            {
                "classification": payload["classification"],
                "v4_integrity_passed": payload["v4_replay_integrity"]["passed"],
                "v4_wins": payload["v4_metrics"]["wins"],
                "v6_wins": (
                    payload.get("v6_metrics", {}).get("wins")
                    if isinstance(payload.get("v6_metrics"), dict)
                    else None
                ),
                "paired": payload.get("paired"),
                "runtime_seconds": payload["runtime_seconds"],
            },
            sort_keys=True,
        )
    )


def main() -> None:
    overall_started = time.perf_counter()
    deck = load_real_deck(ROOT / "data")
    authority = json.loads(WORKER22_RECEIPT.read_text(encoding="utf-8"))
    evaluated_commit = os.environ.get("EVALUATED_COMMIT", "")
    workflow_run_id = os.environ.get("WORKFLOW_RUN_ID", "")

    v4_records, v4_seconds = evaluate_v4(deck)
    v4_metrics = summarize(v4_records)
    v4_integrity = compare_v4_replay(v4_records, v4_metrics, authority)

    payload: dict[str, object] = {
        "schema": "bandido-alcatraz-v6-current-model-spent-development-evaluation",
        "schema_version": 1,
        "date": "2026-09-28",
        "dataset_status": "already-spent / development / non-confirmatory",
        "preregistration_url": PREREGISTRATION_URL,
        "starting_main": STARTING_MAIN,
        "evaluated_commit": evaluated_commit,
        "current_model_baseline_authority": {
            "commit": STARTING_MAIN,
            "path": (
                "experiments/real-deck-policy-v6/"
                "spent-development-1000-1099-2026-09-28.json"
            ),
            "worker22_classification": authority["classification"],
        },
        "corrected_model_provenance": {
            "water_over_water_fix_commit": WATER_FIX_COMMIT,
            "water_over_water_semantics": (
                "Board.place preserves replacement cell.water on overlap"
            ),
        },
        "policies": {
            "v4": {
                "class": "BoundedMergeV4Policy",
                "parameters": {"setup_weight": 250},
            },
            "v6": {
                "class": "VisibleHandTwoActionV6Policy",
                "parameters": {},
            },
        },
        "fixed_model": {
            "deck_file": "data/deck-v1.json",
            "exit_geometry_source": "data/deck-observations-v0.json",
            "rules_variant": "v0-threshold-equipment",
            "equipment_thresholds": {"raincoats_min": 3, "ropes_min": 2},
            "start_side": "easy-5-exit",
            "hand_size": 3,
            "legal_move_ordering": "canonical current implementation",
            "board_semantics": "current corrected canonical",
            "v4_setup_weight": 250,
            "v6_source": "merged current main; unmodified by Worker #23",
        },
        "seed_range": [1000, 1099],
        "seed_count_per_policy": 100,
        "fresh_seeds_used": False,
        "holdout_used": False,
        "v4_replay_integrity": v4_integrity,
        "v4_metrics": v4_metrics,
        "v4_per_seed": v4_records,
        "runtime_seconds": {
            "v4": v4_seconds,
            "v6": None,
            "overall": None,
        },
        "execution": {
            "v6_parallel_workers": V6_WORKERS,
            "parallelization": (
                "mechanical fixed execution over seeds 1000-1099; "
                "executor.map preserves seed order and executes each seed once"
            ),
        },
        "ci_provenance": {
            "workflow_run_id": workflow_run_id,
            "evaluated_commit": evaluated_commit,
            "runner_requirement": "[self-hosted, Linux, X64, bandido-alcatraz-ci]",
        },
        "interpretation_limits": [
            "Seeds 1000-1099 are already-spent development data.",
            "This is non-confirmatory and not an unbiased or final win-rate estimate.",
            "No fresh or held-out seed is used.",
        ],
    }

    if not v4_integrity["passed"]:
        payload.update(
            {
                "v6_metrics": None,
                "v6_per_seed": None,
                "paired": None,
                "current_v4_win_preservation": None,
                "v6_gained_win_seeds": None,
                "classification": (
                    "v6_current_model_spent_development_diagnostic_invalid"
                ),
            }
        )
        payload["runtime_seconds"]["overall"] = time.perf_counter() - overall_started
        write_payload(payload)
        return

    v6_records, v6_seconds = evaluate_v6()
    if [record["seed"] for record in v6_records] != list(SEEDS):
        raise AssertionError("V6 seed population/order mismatch")

    v6_metrics = summarize(v6_records)
    paired_result = paired(v4_records, v6_records)

    current_v4_wins = v4_metrics["winning_seeds"]
    v6_winning_set = set(v6_metrics["winning_seeds"])
    preservation = {
        str(seed): {
            "v4_won": True,
            "v6_won": seed in v6_winning_set,
            "status": "preserved" if seed in v6_winning_set else "lost",
        }
        for seed in current_v4_wins
    }

    if v6_metrics["wins"] > v4_metrics["wins"]:
        classification = (
            "v6_current_model_spent_development_directionally_supported"
        )
    elif v6_metrics["wins"] < v4_metrics["wins"]:
        classification = "v6_current_model_spent_development_harm_detected"
    else:
        classification = "v6_current_model_spent_development_no_win_signal"

    payload.update(
        {
            "v6_metrics": v6_metrics,
            "v6_per_seed": v6_records,
            "paired": paired_result,
            "current_v4_win_preservation": preservation,
            "v6_gained_win_seeds": paired_result["v6_only_seed_ids"],
            "classification": classification,
        }
    )
    payload["runtime_seconds"]["v6"] = v6_seconds
    payload["runtime_seconds"]["overall"] = time.perf_counter() - overall_started
    write_payload(payload)


if __name__ == "__main__":
    main()
