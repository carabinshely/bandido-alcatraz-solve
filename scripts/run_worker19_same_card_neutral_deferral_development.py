from __future__ import annotations

import hashlib
import inspect
import json
import os
from collections import Counter
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, VisibleRepairReserveV5Policy
from bandido_alcatraz.strategy import (
    PolicyWeights,
    move_features,
    score_features,
    standalone_exit_legal_move_count,
    is_unsafe_capacity_kill_without_visible_repair_reserve,
)

ROOT = Path(__file__).parents[1]
SEEDS = (
    2001, 2004, 2005, 2020, 2024, 2034, 2084, 2098, 2104, 2110,
    2129, 2130, 2138, 2168, 2171, 2212, 2238, 2282, 2286, 2314,
    2334, 2371, 2372,
)
EXPECTED_V5 = {
    2001: (69, "157aad283feb3e0436bf670c13efe469cbdab431ac83afa9e065d6cafe9873ce"),
    2004: (38, "85e89bccff61352caabe673acfaed130837bdf59d5d7d81636cade71725ab2c7"),
    2005: (31, "e2894cdbcdbc28c374a078135ac7b72cf5eb7fbdcc7e860c68f2b59355719ffd"),
    2020: (69, "e03fcc538f2a17c3c4f0047686a7fafce90e528d6332aa1f1ef125e2f16e332f"),
    2024: (69, "f7aa96a218007ca6068b7eb1634d97e1c1c396feaea16c5e0725836c9f596718"),
    2034: (69, "62b2b173e537eaf611004f8f06456819ae063556edb1468fc6f4760f4e0b5655"),
    2084: (69, "09d58f7dfbae5aee2a668275f345cbbeb6d6a842ab379d4e95289f1647400b8a"),
    2098: (69, "be3a74dab76c56880d1a5c778b817b2f8c83eee8d82aa1af28d8053e6d15c000"),
    2104: (69, "6f3673a26b0f1e35a993bb2c46f67ed25c45e41b720ec013fe8a2fb50d4a0e2a"),
    2110: (69, "cf454b19fc3e4b3883785921028e457368ec8464d58f92bfc4687cc9da6f3994"),
    2129: (69, "67fecf539a482566ba82f969ca9ad1624cb8c53603b8b69ac7498979bd85248d"),
    2130: (69, "3136fe2c9baf0217e6caab25a3a009cf00018a96dc87b845bb80e8e5e932bea6"),
    2138: (38, "75e96574c9b72b3ed77ddc895af4dc7c5b8f5acffc403f482b5ae14afff531be"),
    2168: (69, "24a79ac4e1e8b4f4c9040155c4bda3c9b1c0ac9c51aa6130a040497a3391627d"),
    2171: (69, "c5615e018bb20315ba64ee3f7a7fe25f0728189fbcc82fc79a6cb7355b811aed"),
    2212: (61, "c0984ac7290e4a97d0d86bb305750b79e744860666c872e4b2b0a7e27c0653d0"),
    2238: (69, "633473071020194cfd39da2bfad4409b142c64242937c2ba716c2be352b533ee"),
    2282: (69, "d09be28b870a351a73ac963a773166c312168bbed48855b55cec85f54f9dd8aa"),
    2286: (16, "331802be665bfe00c3d2ee068e12ab11c733a356466f707ef7217a00e97f002c"),
    2314: (69, "3a2ae8e7c0dca10a8bb3912a40e8c4f6c55da02bd199a480c52273834720ed89"),
    2334: (69, "4f837ced262e25a699fed5ebfa3fe19fc09e71786689cadbc586f68ca10b3675"),
    2371: (24, "0543539aa987a7208925d388ad3bf7d4dab435584662cddef424b1fa5f2432c4"),
    2372: (69, "3d3bad238dadb87817f86e5c8425e9600ebe95e71caf6bb423f0d52e064a2aaa"),
}
EXPECTED_V5_WINS = {2005, 2286, 2371}
KNOWN_REGRESSIONS = {2238, 2282}
PREREGISTRATION_URL = (
    "https://github.com/carabinshely/bandido-alcatraz-solve/"
    "issues/2#issuecomment-5858632097"
)
SLICE18_MANIFEST = (
    "experiments/real-deck-policy-v5/"
    "same-card-neutral-deferral-footprint-2026-09-27.manifest.json"
)


def sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def move_record(state: GameState, move: Move) -> dict[str, object]:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def visible_state_record(state: GameState) -> dict[str, object]:
    cells = [
        {
            "coord": [x, y],
            "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
            "water": cell.water,
        }
        for (x, y), cell in sorted(state.board.cells.items())
    ]
    return {
        "turns": state.turns,
        "cells": cells,
        "hand": [card.card_id for card in state.hand],
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "exit_placed": state.exit_placed,
        "exit_seen": state.exit_seen,
        "set_aside_unplayable": state.set_aside_unplayable,
    }


def final_record(state: GameState, reason: str) -> dict[str, object]:
    return {
        "won": state.won,
        "reason": reason,
        "turns": state.turns,
        "final_open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "exit_placed": state.exit_placed,
    }


def v5_eligible_moves(
    state: GameState,
    policy: VisibleRepairReserveV5Policy,
) -> tuple[list[Move], str]:
    moves = state.legal_moves()
    if not moves:
        return [], "none"
    if state.exit_placed or state.exit_seen:
        return moves, "all_phase_inactive"
    if standalone_exit_legal_move_count(state.board, policy.exit_card) <= 0:
        return moves, "all_no_capacity"
    normal_moves = [
        move
        for move in moves
        if not is_unsafe_capacity_kill_without_visible_repair_reserve(
            state, move, policy.exit_card
        )
    ]
    if not normal_moves:
        return moves, "all_unsafe_fallback"
    return normal_moves, "normal_filtered"


def weighted_nonzero_vector(
    state: GameState,
    move: Move,
    weights: PolicyWeights,
) -> dict[str, dict[str, int]]:
    features = move_features(state, move)
    result: dict[str, dict[str, int]] = {}
    for field in features.__dataclass_fields__:
        weight = getattr(weights, field)
        if weight == 0:
            continue
        value = getattr(features, field)
        result[field] = {
            "feature": value,
            "weight": weight,
            "contribution": value * weight,
        }
    return result


def candidate_choose(
    state: GameState,
    rng: Random,
    policy: VisibleRepairReserveV5Policy,
    weights: PolicyWeights,
) -> tuple[Move | None, dict[str, object] | None]:
    eligible, eligibility_path = v5_eligible_moves(state, policy)
    if not eligible:
        return None, None

    scored = [
        (score_features(move_features(state, move), weights), move)
        for move in eligible
    ]
    max_score = max(score for score, _ in scored)
    max_tier = [move for score, move in scored if score == max_score]
    collect_indexes = {
        move.hand_index for move in max_tier if move.action is Action.COLLECT
    }

    deferable: list[Move] = []
    vectors: dict[Move, dict[str, dict[str, int]]] = {}
    for move in max_tier:
        if move.action is not Action.PLACE or move.hand_index not in collect_indexes:
            continue
        vector = weighted_nonzero_vector(state, move, weights)
        if any(item["contribution"] != 0 for item in vector.values()):
            continue
        deferable.append(move)
        vectors[move] = vector

    remaining = [move for move in max_tier if move not in deferable]
    if not remaining:
        raise AssertionError("candidate removed entire max-score tier")

    selected = rng.choice(remaining)
    if not deferable:
        return selected, None

    return selected, {
        "eligibility_path": eligibility_path,
        "max_score": max_score,
        "max_tier_size_before": len(max_tier),
        "max_tier_size_after": len(remaining),
        "deferable_placements": [
            {
                "move": move_record(state, move),
                "weighted_nonzero_vector": vectors[move],
            }
            for move in deferable
        ],
        "same_card_collects": [
            move_record(state, move)
            for move in max_tier
            if move.action is Action.COLLECT and move.hand_index in collect_indexes
        ],
        "selected_move": move_record(state, selected),
    }


def run_seed(
    *,
    seed: int,
    deck,
    mode: str,
    baseline_actions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    policy = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
    v4_weights = BoundedMergeV4Policy(setup_weight=250).weights
    if policy.weights != v4_weights:
        raise AssertionError("frozen V5 weights differ from V4-250 weights")
    actions: list[dict[str, object]] = []
    activations: list[dict[str, object]] = []
    refreshes = 0
    first_divergence: dict[str, object] | None = None

    for _ in range(1000):
        if state.won:
            reason = "win"
            break
        if state.board.open_tunnels == 0:
            reason = "closed_tunnels_conditions_failed"
            break
        if not state.hand and not state.draw_pile:
            reason = "deck_exhausted"
            break

        transition_id = f"{seed}:a{state.turns + 1}:s{state.turns}"
        state_hash = sha256_json(visible_state_record(state))

        if mode == "v5":
            selected = policy.choose(state, rng)
            activation = None
        elif mode == "candidate":
            selected, activation = candidate_choose(state, rng, policy, v4_weights)
        else:
            raise ValueError(f"unknown mode: {mode}")

        if selected is None:
            if state.refresh_unplayable_hand():
                refreshes += 1
                continue
            reason = "deck_exhausted" if state.exhausted else "no_legal_move"
            break

        selected_record = move_record(state, selected)
        action = {
            "transition_id": transition_id,
            "pre_visible_state_sha256": state_hash,
            "move": selected_record,
        }
        actions.append(action)

        if activation is not None:
            activations.append(
                {
                    "transition_id": transition_id,
                    "pre_visible_state_sha256": state_hash,
                    **activation,
                }
            )

        if (
            mode == "candidate"
            and first_divergence is None
            and baseline_actions is not None
        ):
            index = len(actions) - 1
            if index >= len(baseline_actions):
                first_divergence = {
                    "candidate_action_index": index,
                    "candidate_transition_id": transition_id,
                    "baseline_record_missing": True,
                    "candidate_move": selected_record,
                }
            else:
                baseline = baseline_actions[index]
                if (
                    selected_record != baseline["move"]
                    or transition_id != baseline["transition_id"]
                ):
                    first_divergence = {
                        "candidate_action_index": index,
                        "candidate_transition_id": transition_id,
                        "baseline_transition_id": baseline["transition_id"],
                        "states_still_identical": (
                            state_hash == baseline["pre_visible_state_sha256"]
                        ),
                        "pre_visible_state_sha256": state_hash,
                        "frozen_v5_move": baseline["move"],
                        "candidate_move": selected_record,
                    }

        state.apply(selected)
    else:
        reason = "step_limit"

    canonical_action_records = [
        {"transition_id": item["transition_id"], "move": item["move"]}
        for item in actions
    ]
    return {
        "seed": seed,
        "mode": mode,
        "action_count": len(actions),
        "action_sequence_sha256": sha256_json(canonical_action_records),
        "refreshes": refreshes,
        "final": final_record(state, reason),
        "filter_activation_count": len(activations),
        "filter_activations": activations,
        "first_divergence_from_v5": first_divergence,
        "actions": actions,
    }


def summarize(runs: dict[int, dict[str, object]]) -> dict[str, object]:
    wins = sorted(seed for seed, run in runs.items() if run["final"]["won"])
    failures = Counter(
        run["final"]["reason"]
        for run in runs.values()
        if not run["final"]["won"]
    )
    return {
        "wins": len(wins),
        "winning_seeds": wins,
        "failure_reason_counts": dict(sorted(failures.items())),
    }


def write_payload(payload: dict[str, object]) -> None:
    artifact_dir = ROOT / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    path = artifact_dir / "worker19-same-card-neutral-deferral-development.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("WORKER19_RESULT=" + json.dumps({
        "classification": payload["classification"],
        "integrity_passed": payload["integrity"]["passed"],
        "paired": payload.get("paired"),
        "candidate_summary": payload.get("candidate_summary"),
    }, sort_keys=True))


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    evaluated_commit = os.environ.get("EVALUATED_COMMIT", "")
    policy_path = ROOT / "src" / "bandido_alcatraz" / "policies.py"
    strategy_path = ROOT / "src" / "bandido_alcatraz" / "strategy.py"
    deck_path = ROOT / "data" / "deck-v1.json"
    observations_path = ROOT / "data" / "deck-observations-v0.json"
    script_path = Path(__file__)

    candidate_source = inspect.getsource(candidate_choose)
    candidate_rng_choice_count = candidate_source.count("rng.choice(")

    v5_runs: dict[int, dict[str, object]] = {}
    replay_mismatches: list[dict[str, object]] = []
    total_actions = 0
    total_refreshes = 0

    for seed in SEEDS:
        run = run_seed(seed=seed, deck=deck, mode="v5")
        v5_runs[seed] = run
        total_actions += run["action_count"]
        total_refreshes += run["refreshes"]
        expected_count, expected_hash = EXPECTED_V5[seed]
        if (
            run["action_count"] != expected_count
            or run["action_sequence_sha256"] != expected_hash
        ):
            replay_mismatches.append({
                "seed": seed,
                "expected_action_count": expected_count,
                "actual_action_count": run["action_count"],
                "expected_sha256": expected_hash,
                "actual_sha256": run["action_sequence_sha256"],
            })

    v5_summary = summarize(v5_runs)
    structural = {
        "candidate_and_v5_fixed_model_parameters_identical": True,
        "v5_weights_equal_v4_250": VisibleRepairReserveV5Policy(
            exit_card=deck.exit_card
        ).weights == BoundedMergeV4Policy(setup_weight=250).weights,
        "candidate_inputs": ["visible GameState", "Random", "frozen V5 policy weights/exit_card"],
        "inspects_seed_id": False,
        "inspects_final_outcome": False,
        "inspects_hidden_future_draws": False,
        "reconstructs_v4_comparator_state": False,
        "mutable_cross_policy_memory": False,
        "extra_policy_rng_calls_before_final_selection": False,
        "candidate_rng_choice_calls_in_source": candidate_rng_choice_count,
        "single_final_rng_choice_source_check": candidate_rng_choice_count == 1,
    }
    integrity_passed = (
        len(replay_mismatches) == 0
        and total_actions == 1381
        and total_refreshes == 42
        and v5_summary["wins"] == 3
        and set(v5_summary["winning_seeds"]) == EXPECTED_V5_WINS
        and candidate_rng_choice_count == 1
        and structural["v5_weights_equal_v4_250"]
    )

    base_payload: dict[str, object] = {
        "schema": "bandido-alcatraz-worker19-same-card-neutral-deferral-development",
        "schema_version": 1,
        "dataset_status": "already-spent / selected / development / counterfactual / non-confirmatory",
        "preregistration_url": PREREGISTRATION_URL,
        "source_slice18_manifest": SLICE18_MANIFEST,
        "evaluated_commit": evaluated_commit,
        "seed_scope": list(SEEDS),
        "fresh_seeds_used": False,
        "holdout_used": False,
        "fixed_model": {
            "v5": "merged VisibleRepairReserveV5Policy",
            "scoring": "BoundedMergeV4Policy(setup_weight=250).weights",
            "deck_file": "data/deck-v1.json",
            "deck_sha256": sha256_file(deck_path),
            "exit_geometry_source": "data/deck-observations-v0.json",
            "deck_observations_sha256": sha256_file(observations_path),
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
            "deterministic_legal_move_ordering": "unchanged",
            "exit_seen_semantics": "unchanged",
            "policies_source_sha256": sha256_file(policy_path),
            "strategy_source_sha256": sha256_file(strategy_path),
        },
        "candidate_contract": {
            "name": "same-card neutral-placement deferral",
            "version": "slice18-fixed-v1",
            "scope": "existing frozen-V5 eligible max-score tier only",
            "rule": [
                "construct exact existing V5 eligible move set",
                "score eligible moves with unchanged V4-250 weights",
                "form max-score tier M",
                "defer max-tier PLACE only when same hand_index has max-tier COLLECT and every non-zero-weight feature contribution is zero",
                "remove only deferable placements from M",
                "perform exactly one final rng.choice over remaining max-tier candidates",
            ],
            "script_sha256": sha256_file(script_path),
            "candidate_choose_source_sha256": hashlib.sha256(
                candidate_source.encode("utf-8")
            ).hexdigest(),
            "candidate_choose_source": candidate_source,
        },
        "integrity": {
            "expected_seed_count": len(SEEDS),
            "exact_sequence_matches": len(SEEDS) - len(replay_mismatches),
            "replay_mismatches": replay_mismatches,
            "total_action_decisions": total_actions,
            "total_refreshes": total_refreshes,
            "frozen_v5_summary": v5_summary,
            "structural_candidate_checks": structural,
            "passed": integrity_passed,
        },
        "frozen_v5_runs": {str(seed): run for seed, run in v5_runs.items()},
    }

    if not integrity_passed:
        base_payload["classification"] = (
            "same_card_neutral_deferral_development_diagnostic_invalid"
        )
        base_payload["candidate_interpreted"] = False
        write_payload(base_payload)
        return

    candidate_runs: dict[int, dict[str, object]] = {}
    for seed in SEEDS:
        candidate_runs[seed] = run_seed(
            seed=seed,
            deck=deck,
            mode="candidate",
            baseline_actions=v5_runs[seed]["actions"],
        )

    candidate_summary = summarize(candidate_runs)
    gained = sorted(
        seed
        for seed in SEEDS
        if not v5_runs[seed]["final"]["won"] and candidate_runs[seed]["final"]["won"]
    )
    lost = sorted(
        seed
        for seed in SEEDS
        if v5_runs[seed]["final"]["won"] and not candidate_runs[seed]["final"]["won"]
    )
    unchanged_win = sorted(
        seed
        for seed in SEEDS
        if v5_runs[seed]["final"]["won"] and candidate_runs[seed]["final"]["won"]
    )
    unchanged_nonwin = sorted(
        seed
        for seed in SEEDS
        if not v5_runs[seed]["final"]["won"] and not candidate_runs[seed]["final"]["won"]
    )
    paired = {
        "gained_win_seeds": gained,
        "lost_win_seeds": lost,
        "unchanged_win_seeds": unchanged_win,
        "unchanged_nonwin_seeds": unchanged_nonwin,
        "net_paired_win_count_change": candidate_summary["wins"] - v5_summary["wins"],
        "rescued_regression_seeds": sorted(set(gained) & KNOWN_REGRESSIONS),
        "rescued_regression_count": len(set(gained) & KNOWN_REGRESSIONS),
    }

    if lost or candidate_summary["wins"] < 3:
        classification = "same_card_neutral_deferral_development_harm_detected"
    elif (
        candidate_summary["wins"] >= 4
        and not lost
        and bool(set(candidate_summary["winning_seeds"]) & KNOWN_REGRESSIONS)
    ):
        classification = "same_card_neutral_deferral_development_supported"
    else:
        classification = "same_card_neutral_deferral_development_not_supported"

    activation_counts = {
        str(seed): candidate_runs[seed]["filter_activation_count"] for seed in SEEDS
    }
    special_seeds = {
        str(seed): {
            "frozen_v5": v5_runs[seed]["final"],
            "candidate": candidate_runs[seed]["final"],
            "candidate_filter_activation_count": candidate_runs[seed][
                "filter_activation_count"
            ],
            "first_divergence": candidate_runs[seed]["first_divergence_from_v5"],
        }
        for seed in (2238, 2282, 2005, 2286, 2371)
    }

    base_payload.update({
        "candidate_interpreted": True,
        "candidate_runs": {str(seed): run for seed, run in candidate_runs.items()},
        "candidate_summary": candidate_summary,
        "paired": paired,
        "special_seeds": special_seeds,
        "candidate_filter_activations": {
            "total": sum(activation_counts.values()),
            "per_seed": activation_counts,
        },
        "classification": classification,
        "classification_gates": {
            "A_candidate_wins_gte_4": candidate_summary["wins"] >= 4,
            "A_zero_frozen_v5_wins_lost": len(lost) == 0,
            "A_rescues_2238_or_2282": bool(
                set(candidate_summary["winning_seeds"]) & KNOWN_REGRESSIONS
            ),
            "B_any_frozen_v5_win_lost": bool(lost),
            "B_candidate_wins_lt_3": candidate_summary["wins"] < 3,
        },
        "production_source_modified_by_candidate": False,
        "interpretation_limit": (
            "Selected already-spent development cohort only; descriptive, "
            "counterfactual and non-confirmatory."
        ),
    })
    write_payload(base_payload)


if __name__ == "__main__":
    main()
