from __future__ import annotations

from collections import Counter
import json
import math
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
OUTPUT = ROOT / "artifacts" / "worker22-v6-spent-development-1000-1099.json"

PREREGISTRATION_URL = (
    "https://github.com/carabinshely/bandido-alcatraz-solve/"
    "issues/2#issuecomment-5859965905"
)
HISTORICAL_REFERENCE = {
    "commit": "27b3ba30b9454ca2ce7a8e891793699e7136fcfe",
    "path": "experiments/real-deck-policy-v4/confirmation-2026-09-21.json",
}
HISTORICAL_V4 = {
    "games": 100,
    "wins": 5,
    "winning_seeds": [1008, 1049, 1056, 1087, 1097],
    "mean_final_open_tunnels": 14.77,
    "open_tunnels_le_5": 21,
    "water_clear": 55,
    "mean_visible_water": 0.73,
    "equipment_ready": 99,
    "exit_placed": 89,
    "exit_equipment_water_ready": 45,
    "failure_reasons": {
        "closed_tunnels_conditions_failed": 2,
        "deck_exhausted": 76,
        "no_legal_move": 17,
        "step_limit": 0,
    },
}


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


def evaluate(policy, deck) -> tuple[list[dict[str, object]], float]:
    started = time.perf_counter()
    records = [
        final_record(
            seed,
            play_game(
                start_card=deck.start_easy,
                deck=deck.draw_deck(),
                hand_size=3,
                policy=policy,
                seed=seed,
            ),
        )
        for seed in SEEDS
    ]
    return records, time.perf_counter() - started


def compare_v4_replay(actual: dict[str, object]) -> dict[str, object]:
    checks: dict[str, object] = {}
    exact_fields = (
        "games",
        "wins",
        "winning_seeds",
        "open_tunnels_le_5",
        "water_clear",
        "equipment_ready",
        "exit_placed",
        "exit_equipment_water_ready",
        "failure_reasons",
    )
    for field in exact_fields:
        checks[field] = {
            "expected": HISTORICAL_V4[field],
            "actual": actual[field],
            "matched": actual[field] == HISTORICAL_V4[field],
        }

    for field in ("mean_final_open_tunnels", "mean_visible_water"):
        expected = float(HISTORICAL_V4[field])
        observed = float(actual[field])
        checks[field] = {
            "expected": expected,
            "actual": observed,
            "matched": math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-12),
        }

    checks["step_limit_zero"] = {
        "expected": 0,
        "actual": int(actual["step_limit"]),
        "matched": int(actual["step_limit"]) == 0,
    }
    passed = all(bool(item["matched"]) for item in checks.values())
    return {"passed": passed, "checks": checks}


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
        "net_paired_win_count_difference": len(v6_only) - len(v4_only),
    }


def write_payload(payload: dict[str, object]) -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "WORKER22_RESULT="
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
                "runtime_seconds": payload.get("runtime_seconds"),
            },
            sort_keys=True,
        )
    )


def main() -> None:
    overall_started = time.perf_counter()
    deck = load_real_deck(ROOT / "data")
    evaluated_commit = os.environ.get("EVALUATED_COMMIT", "")
    workflow_run_id = os.environ.get("WORKFLOW_RUN_ID", "")

    v4_records, v4_seconds = evaluate(
        BoundedMergeV4Policy(setup_weight=250),
        deck,
    )
    v4_metrics = summarize(v4_records)
    v4_integrity = compare_v4_replay(v4_metrics)

    payload: dict[str, object] = {
        "schema": "bandido-alcatraz-v6-spent-development-evaluation",
        "schema_version": 1,
        "date": "2026-09-28",
        "dataset_status": "already-spent / development / non-confirmatory",
        "preregistration_url": PREREGISTRATION_URL,
        "starting_main": "37173f57910f6e67e01c2bcf662e2ab5b640d6fc",
        "evaluated_commit": evaluated_commit,
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
            "photographed_deck": True,
            "rules_variant": "v0-threshold-equipment",
            "equipment_thresholds": {"raincoats_min": 3, "ropes_min": 2},
            "start_side": "easy-5-exit",
            "hand_size": 3,
            "legal_move_ordering": "canonical current implementation",
            "v4_setup_weight": 250,
            "v6_source": "merged canonical main; unmodified by Worker #22",
        },
        "seed_range": [1000, 1099],
        "seed_count_per_policy": 100,
        "fresh_seeds_used": False,
        "holdout_used": False,
        "historical_v4_reference": HISTORICAL_REFERENCE,
        "v4_replay_integrity": v4_integrity,
        "v4_metrics": v4_metrics,
        "v4_per_seed": v4_records,
        "runtime_seconds": {
            "v4": v4_seconds,
            "v6": None,
            "overall": None,
        },
        "ci_provenance": {
            "workflow_run_id": workflow_run_id,
            "evaluated_commit": evaluated_commit,
            "runner_requirement": "[self-hosted, Linux, X64, bandido-alcatraz-ci]",
        },
        "interpretation_limits": [
            "Seeds 1000-1099 are already-spent historical development data.",
            "This evaluation is non-confirmatory and not an unbiased or final win-rate estimate.",
            "No seed outside the preregistered range is evaluated.",
        ],
    }

    if not v4_integrity["passed"]:
        payload["v6_metrics"] = None
        payload["v6_per_seed"] = None
        payload["paired"] = None
        payload["historical_v4_win_preservation"] = None
        payload["v6_gained_win_seeds"] = None
        payload["classification"] = "v6_spent_development_diagnostic_invalid"
        payload["runtime_seconds"]["overall"] = time.perf_counter() - overall_started
        write_payload(payload)
        return

    v6_records, v6_seconds = evaluate(VisibleHandTwoActionV6Policy(), deck)
    v6_metrics = summarize(v6_records)
    paired_result = paired(v4_records, v6_records)

    historical_wins = HISTORICAL_V4["winning_seeds"]
    v6_winning_set = set(v6_metrics["winning_seeds"])
    preservation = {
        str(seed): {
            "v4_won": True,
            "v6_won": seed in v6_winning_set,
            "status": "preserved" if seed in v6_winning_set else "lost",
        }
        for seed in historical_wins
    }

    if v6_metrics["wins"] > v4_metrics["wins"]:
        classification = "v6_spent_development_directionally_supported"
    elif v6_metrics["wins"] < v4_metrics["wins"]:
        classification = "v6_spent_development_harm_detected"
    else:
        classification = "v6_spent_development_no_win_signal"

    payload.update(
        {
            "v6_metrics": v6_metrics,
            "v6_per_seed": v6_records,
            "paired": paired_result,
            "historical_v4_win_preservation": preservation,
            "v6_gained_win_seeds": paired_result["v6_only_seed_ids"],
            "classification": classification,
        }
    )
    payload["runtime_seconds"]["v6"] = v6_seconds
    payload["runtime_seconds"]["overall"] = time.perf_counter() - overall_started
    write_payload(payload)


if __name__ == "__main__":
    main()
