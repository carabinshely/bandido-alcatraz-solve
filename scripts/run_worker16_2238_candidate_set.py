from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, VisibleRepairReserveV5Policy
from bandido_alcatraz.strategy import (
    clone_state,
    move_features,
    score_features,
    standalone_exit_legal_move_count,
)

ROOT = Path(__file__).parents[1]
STARTING_MAIN = "fb5e4674ebc2de276cb77c3a2e5a8c7aa2217395"
DECISION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5855733500"
WORKER15_MANIFEST = ROOT / "experiments/real-deck-policy-v5/mixed-case-next-hand-closure-reserve-audit-2026-09-25.manifest.json"

TARGET = "2238:a20:s19"
CONTROLS = ["2024:a14:s13", "2098:a17:s16", "2372:a22:s21"]
AUDIT_IDS = [TARGET, *CONTROLS]

PRE_ACTION = {
    "2238:a20:s19": {
        "seed": 2238,
        "fingerprint_sha256": "8c96ad9df4548b316af8dfde0c15ac7a4c898bfc82acd7d3bdff1418c93509ef",
        "replacement_draw": "photo-3-r2-c2",
        "v4": {"action":"place","card_id":"photo-3-r3-c5","hand_index":2,"origin":[-4,0],"quarter_turns":2},
        "v5": {"action":"place","card_id":"photo-3-r3-c5","hand_index":2,"origin":[0,2],"quarter_turns":0},
    },
    "2024:a14:s13": {
        "seed": 2024,
        "fingerprint_sha256": "f04724a6f4335fb0bccee6c730cf384139df7d3caf501b46e7855349c3cca023",
        "replacement_draw": "photo-3-r1-c2",
        "v4": {"action":"place","card_id":"photo-3-r2-c4","hand_index":2,"origin":[-1,-4],"quarter_turns":1},
        "v5": {"action":"place","card_id":"photo-3-r2-c4","hand_index":2,"origin":[0,-4],"quarter_turns":0},
    },
    "2098:a17:s16": {
        "seed": 2098,
        "fingerprint_sha256": "cdab5702ca0062f14c03343a4fbaab58954725210f519f3967cbbdb0a03aa969",
        "replacement_draw": "photo-4-r1-c5",
        "v4": {"action":"place","card_id":"photo-3-r1-c3","hand_index":2,"origin":[-2,3],"quarter_turns":2},
        "v5": {"action":"place","card_id":"photo-3-r1-c3","hand_index":2,"origin":[-3,3],"quarter_turns":1},
    },
    "2372:a22:s21": {
        "seed": 2372,
        "fingerprint_sha256": "8b6b947aa7f5b3628c524465caff213654f7525ba1ab261b1c886992d7c8828e",
        "replacement_draw": "photo-4-r1-c4",
        "v4": {"action":"place","card_id":"photo-2-r2-c3","hand_index":2,"origin":[4,3],"quarter_turns":0},
        "v5": {"action":"place","card_id":"photo-2-r2-c3","hand_index":2,"origin":[5,3],"quarter_turns":0},
    },
}

# Accepted Worker #13 raw provenance only. These events are not executed here.
HISTORICAL_NEXT = {
    "2238:a20:s19": {
        "event": "action",
        "transition_id": "2238:a21:s20",
        "move": {"action":"place","card_id":"photo-3-r2-c2","hand_index":2,"origin":[-4,1],"quarter_turns":0},
    },
    "2024:a14:s13": {
        "event": "action",
        "transition_id": "2024:a15:s14",
        "move": {"action":"collect","card_id":"photo-3-r1-c2","hand_index":2,"origin":None,"quarter_turns":0},
    },
    "2098:a17:s16": {
        "event": "action",
        "transition_id": "2098:a18:s17",
        "move": {"action":"collect","card_id":"photo-4-r1-c5","hand_index":2,"origin":None,"quarter_turns":0},
    },
    "2372:a22:s21": {
        "event": "refresh",
        "state_turn": 22,
    },
}


def stable_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def board_fingerprint(board) -> list:
    return [
        ([x, y], sorted(edge.value for edge in cell.tunnel_edges), cell.water)
        for (x, y), cell in sorted(board.cells.items())
    ]


def state_fingerprint(state: GameState) -> dict:
    return {
        "turns": state.turns,
        "cells": board_fingerprint(state.board),
        "hand": [card.card_id for card in state.hand],
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "exit_placed": state.exit_placed,
        "exit_seen": state.exit_seen,
        "set_aside": state.set_aside_unplayable,
    }


def move_signature(state: GameState, move: Move) -> dict:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def signature_key(sig: dict) -> tuple:
    return (
        sig["action"],
        sig["card_id"],
        sig["hand_index"],
        tuple(sig["origin"]) if sig["origin"] is not None else None,
        sig["quarter_turns"],
    )


def find_move(state: GameState, sig: dict) -> Move:
    wanted = signature_key(sig)
    for move in state.legal_moves():
        if signature_key(move_signature(state, move)) == wanted:
            return move
    raise AssertionError(f"expected move is not legal: {wanted}")


def replay_to_pre_action(seed: int, target_id: str, deck) -> GameState:
    rng = Random(seed)
    policy = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    for _ in range(1000):
        if state.won or state.board.open_tunnels == 0 or (
            not state.hand and not state.draw_pile
        ):
            raise AssertionError(f"terminated before target {target_id}")

        moves = state.legal_moves()
        if not moves:
            if state.refresh_unplayable_hand():
                continue
            raise AssertionError(f"no legal move before target {target_id}")

        tid = f"{seed}:a{state.turns + 1}:s{state.turns}"
        if tid == target_id:
            return state

        move = policy.choose(state, rng)
        if move is None:
            raise AssertionError(f"policy returned None before target {target_id}")
        state.apply(move)

    raise AssertionError(f"target not reached: {target_id}")


def reserve_metrics(state: GameState, exit_card) -> dict:
    base_open = state.board.open_tunnels
    base_water = state.board.visible_water_cells
    base_merge = state.board.merge_opportunities
    placements = [m for m in state.legal_moves() if m.action is Action.PLACE]
    closure_gains = []
    water_gains = []
    merge_gains = []
    closure_cards = set()
    for move in placements:
        board = state.board.clone()
        card = state.hand[move.hand_index]
        assert move.origin is not None
        board.place(card, move.origin, move.quarter_turns)
        cg = base_open - board.open_tunnels
        wg = base_water - board.visible_water_cells
        mg = board.merge_opportunities - base_merge
        closure_gains.append(cg)
        water_gains.append(wg)
        merge_gains.append(mg)
        if cg > 0:
            closure_cards.add(move.hand_index)
    return {
        "max_one_step_closure_gain": max([x for x in closure_gains if x > 0], default=0),
        "closure_improving_placement_count": sum(x > 0 for x in closure_gains),
        "closure_capable_card_count": len(closure_cards),
        "total_legal_ordinary_placement_count": len(placements),
        "successor_exit_capacity": standalone_exit_legal_move_count(state.board, exit_card),
        "successor_open_tunnels": state.board.open_tunnels,
        "successor_visible_water": state.board.visible_water_cells,
    }


def branch_once(pre: GameState, sig: dict, exit_card) -> tuple[GameState, dict]:
    state = clone_state(pre)
    move = find_move(state, sig)
    consumed = state.hand[move.hand_index].card_id
    expected_draw = state.draw_pile[-1].card_id if state.draw_pile else None
    before_draw_count = len(state.draw_pile)
    before_turns = state.turns

    direct_board = state.board.clone()
    if move.action is Action.PLACE:
        card = state.hand[move.hand_index]
        assert move.origin is not None
        direct_board.place(card, move.origin, move.quarter_turns)

    state.apply(move, validate=False)

    actual_draw = state.hand[-1].card_id if before_draw_count else None
    apply_board_sha = stable_hash(board_fingerprint(state.board))
    direct_board_sha = stable_hash(board_fingerprint(direct_board))
    return state, {
        "consumed_card_id": consumed,
        "replacement_draw_card_id": actual_draw,
        "expected_draw_from_pre_action_top": expected_draw,
        "successor_hand": [card.card_id for card in state.hand],
        "successor_board_fingerprint_sha256": apply_board_sha,
        "board_apply_equivalence": apply_board_sha == direct_board_sha,
        "exactly_one_draw": before_draw_count - len(state.draw_pile) == 1,
        "exactly_one_action": state.turns == before_turns + 1,
        "reserve_metrics": reserve_metrics(state, exit_card),
    }


def empty_draw_copy(state: GameState) -> GameState:
    return GameState(
        board=state.board.clone(),
        draw_pile=[],
        hand=list(state.hand),
        raincoats=state.raincoats,
        ropes=state.ropes,
        exit_placed=state.exit_placed,
        exit_seen=state.exit_seen,
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
    )


def score_successor(state: GameState, paired_state: GameState, weights) -> tuple[dict, list]:
    legal = state.legal_moves()
    paired_keys = {signature_key(move_signature(paired_state, m)) for m in paired_state.legal_moves()}
    rows = []
    invariance_failures = []

    for index, move in enumerate(legal):
        prod_features = move_features(state, move)
        prod_score = score_features(prod_features, weights)

        shadow = empty_draw_copy(state)
        shadow_move = find_move(shadow, move_signature(state, move))
        empty_features = move_features(shadow, shadow_move)
        empty_score = score_features(empty_features, weights)

        if prod_features != empty_features or prod_score != empty_score:
            invariance_failures.append({
                "move_index": index,
                "move": move_signature(state, move),
                "production_features": asdict(prod_features),
                "empty_draw_features": asdict(empty_features),
                "production_score": prod_score,
                "empty_draw_score": empty_score,
            })

        row = {
            "canonical_index": index,
            "move": move_signature(state, move),
            "features": asdict(prod_features),
            "score": prod_score,
        }
        if move.action is Action.PLACE:
            board = state.board.clone()
            card = state.hand[move.hand_index]
            assert move.origin is not None
            before_open = state.board.open_tunnels
            before_water = state.board.visible_water_cells
            before_merge = state.board.merge_opportunities
            board.place(card, move.origin, move.quarter_turns)
            row["placement_explanation"] = {
                "closure_gain": before_open - board.open_tunnels,
                "visible_water_reduction": before_water - board.visible_water_cells,
                "merge_opportunity_gain": board.merge_opportunities - before_merge,
                "exact_move_legal_on_paired_other_board": signature_key(row["move"]) in paired_keys,
            }
        rows.append(row)

    max_score = max((row["score"] for row in rows), default=None)
    top = [row for row in rows if row["score"] == max_score] if rows else []
    summary = {
        "full_legal_move_count": len(rows),
        "place_count": sum(row["move"]["action"] == "place" for row in rows),
        "collect_count": sum(row["move"]["action"] == "collect" for row in rows),
        "no_legal_moves": not rows,
        "max_v4_250_score": max_score,
        "max_score_candidate_count": len(top),
        "max_score_place_count": sum(row["move"]["action"] == "place" for row in top),
        "max_score_collect_count": sum(row["move"]["action"] == "collect" for row in top),
        "max_score_candidates": [
            {
                "canonical_index": row["canonical_index"],
                "move": row["move"],
                "score": row["score"],
                **(
                    {"placement_explanation": row["placement_explanation"]}
                    if "placement_explanation" in row
                    else {}
                ),
            }
            for row in top
        ],
    }
    return summary, invariance_failures


def move_is_top_tier(summary: dict, sig: dict) -> bool:
    wanted = signature_key(sig)
    return any(signature_key(row["move"]) == wanted for row in summary["max_score_candidates"])


def top_tier_placement_added(summary: dict) -> list[dict]:
    return [
        row
        for row in summary["max_score_candidates"]
        if row["move"]["action"] == "place"
        and not row["placement_explanation"]["exact_move_legal_on_paired_other_board"]
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(WORKER15_MANIFEST.read_text(encoding="utf-8"))
    deck = load_real_deck(ROOT / "data")
    weights = BoundedMergeV4Policy(setup_weight=250).weights

    changed = subprocess.check_output(
        ["git", "diff", "--name-only", STARTING_MAIN, "HEAD"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden = [
        path for path in changed
        if path.startswith(("src/", "data/"))
        or path == "docs/decisions/2026-09-23-v5-visible-repair-reserve-design.md"
    ]

    integrity = {
        "repository": {
            "worker15_manifest_present": WORKER15_MANIFEST.exists(),
            "worker15_classification": manifest.get("final_preregistered_classification"),
            "production_or_model_changes": forbidden,
            "deterministic_legal_move_ordering_unchanged": "src/bandido_alcatraz/moves.py" not in changed,
        },
        "successor_reconstruction": {
            "exact_cases": 0,
            "total": 4,
            "mismatches": [],
        },
        "score_feature_invariance": {
            "audited_move_count": 0,
            "failure_count": 0,
            "failures": [],
        },
        "no_next_decision_execution": {
            "policy_choose_called_on_successor": False,
            "rng_consumed_on_successor": False,
            "candidate_executed": False,
            "refresh_executed": False,
            "additional_draw_executed": False,
            "passed": True,
        },
    }
    integrity["repository"]["passed"] = (
        integrity["repository"]["worker15_manifest_present"]
        and integrity["repository"]["worker15_classification"]
        == "v5_mixed_case_next_hand_closure_debt_not_supported"
        and not forbidden
        and integrity["repository"]["deterministic_legal_move_ordering_unchanged"]
    )

    case_results = {}
    all_invariance_failures = []

    for tid in AUDIT_IDS:
        exp = PRE_ACTION[tid]
        pre = replay_to_pre_action(exp["seed"], tid, deck)
        mismatch = {}

        actual_pre_hash = stable_hash(state_fingerprint(pre))
        if actual_pre_hash != exp["fingerprint_sha256"]:
            mismatch["pre_action_fingerprint_sha256"] = {
                "expected": exp["fingerprint_sha256"],
                "actual": actual_pre_hash,
            }

        if not pre.draw_pile or pre.draw_pile[-1].card_id != exp["replacement_draw"]:
            mismatch["replacement_draw"] = {
                "expected": exp["replacement_draw"],
                "actual": pre.draw_pile[-1].card_id if pre.draw_pile else None,
            }

        v4_state, v4_branch = branch_once(pre, exp["v4"], deck.exit_card)
        v5_state, v5_branch = branch_once(pre, exp["v5"], deck.exit_card)

        predecessor = manifest["primary_results"][tid]
        expected_hand = predecessor["successor_hand"]
        if v4_branch["successor_hand"] != expected_hand or v5_branch["successor_hand"] != expected_hand:
            mismatch["successor_hand"] = {
                "expected": expected_hand,
                "v4": v4_branch["successor_hand"],
                "v5": v5_branch["successor_hand"],
            }

        for label, branch in (("v4", v4_branch), ("v5", v5_branch)):
            expected_reserve = predecessor[f"{label}_reserve"]
            actual_reserve = branch["reserve_metrics"]
            for key in (
                "max_one_step_closure_gain",
                "closure_improving_placement_count",
                "closure_capable_card_count",
            ):
                if actual_reserve[key] != expected_reserve[key]:
                    mismatch[f"{label}_{key}"] = {
                        "expected": expected_reserve[key],
                        "actual": actual_reserve[key],
                    }
            secondary = predecessor["secondary"]
            expected_place = secondary[f"{label}_total_legal_placements"]
            expected_exit = secondary[f"{label}_exit_capacity"]
            expected_open = secondary[f"{label}_open_tunnels"]
            expected_water = secondary[f"{label}_visible_water"]
            if actual_reserve["total_legal_ordinary_placement_count"] != expected_place:
                mismatch[f"{label}_ordinary_placements"] = {
                    "expected": expected_place,
                    "actual": actual_reserve["total_legal_ordinary_placement_count"],
                }
            if actual_reserve["successor_exit_capacity"] != expected_exit:
                mismatch[f"{label}_exit_capacity"] = {
                    "expected": expected_exit,
                    "actual": actual_reserve["successor_exit_capacity"],
                }
            if actual_reserve["successor_open_tunnels"] != expected_open:
                mismatch[f"{label}_open_tunnels"] = {
                    "expected": expected_open,
                    "actual": actual_reserve["successor_open_tunnels"],
                }
            if actual_reserve["successor_visible_water"] != expected_water:
                mismatch[f"{label}_visible_water"] = {
                    "expected": expected_water,
                    "actual": actual_reserve["successor_visible_water"],
                }
            if not branch["board_apply_equivalence"]:
                mismatch[f"{label}_board_apply_equivalence"] = False
            if not branch["exactly_one_draw"] or not branch["exactly_one_action"]:
                mismatch[f"{label}_one_action_one_draw"] = branch

        v4_summary, v4_failures = score_successor(v4_state, v5_state, weights)
        v5_summary, v5_failures = score_successor(v5_state, v4_state, weights)
        all_invariance_failures.extend(
            [{"transition_id": tid, "branch": "v4", **f} for f in v4_failures]
        )
        all_invariance_failures.extend(
            [{"transition_id": tid, "branch": "v5", **f} for f in v5_failures]
        )
        integrity["score_feature_invariance"]["audited_move_count"] += (
            v4_summary["full_legal_move_count"] + v5_summary["full_legal_move_count"]
        )

        historical = HISTORICAL_NEXT[tid]
        hist_in_v5_top = (
            move_is_top_tier(v5_summary, historical["move"])
            if historical["event"] == "action"
            else None
        )
        hist_in_v4_top = (
            move_is_top_tier(v4_summary, historical["move"])
            if historical["event"] == "action"
            else None
        )

        case_results[tid] = {
            "transition_id": tid,
            "replacement_draw_card_id": exp["replacement_draw"],
            "successor_hand": expected_hand,
            "v4_successor_board_fingerprint_sha256": v4_branch["successor_board_fingerprint_sha256"],
            "v5_successor_board_fingerprint_sha256": v5_branch["successor_board_fingerprint_sha256"],
            "worker15_closure_reserve_class": predecessor["primary_class"],
            "v4_worker15_reserve_metrics": predecessor["v4_reserve"],
            "v5_worker15_reserve_metrics": predecessor["v5_reserve"],
            "v4_candidate_set": v4_summary,
            "v5_candidate_set": v5_summary,
            "historical_next_event": historical,
            "historical_action_in_v4_top_tier": hist_in_v4_top,
            "historical_action_in_v5_top_tier": hist_in_v5_top,
        }

        if mismatch:
            integrity["successor_reconstruction"]["mismatches"].append(
                {"transition_id": tid, **mismatch}
            )
        else:
            integrity["successor_reconstruction"]["exact_cases"] += 1

    integrity["successor_reconstruction"]["passed"] = (
        integrity["successor_reconstruction"]["exact_cases"] == 4
        and not integrity["successor_reconstruction"]["mismatches"]
    )
    integrity["score_feature_invariance"]["failure_count"] = len(all_invariance_failures)
    integrity["score_feature_invariance"]["failures"] = all_invariance_failures
    integrity["score_feature_invariance"]["passed"] = not all_invariance_failures

    integrity_passed = all(section["passed"] for section in integrity.values())

    payload = {
        "schema": "bandido-alcatraz-v5-2238-next-decision-candidate-set-audit",
        "schema_version": 1,
        "experiment_id": "worker-16-v5-2238-next-decision-candidate-set-audit",
        "date": "2026-09-27",
        "dataset_status": "already-spent / selected / development / diagnostic / non-confirmatory",
        "authoritative_orchestrator_decision_url": DECISION_URL,
        "starting_main": STARTING_MAIN,
        "evaluated_commit": os.environ.get("EVALUATED_COMMIT") or os.environ.get("GITHUB_SHA"),
        "workflow_run": {
            "run_id": int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None,
            "url": f"https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/{os.environ.get('GITHUB_RUN_ID')}",
        },
        "runner": os.environ.get("RUNNER_NAME"),
        "primary_target": TARGET,
        "controls": CONTROLS,
        "fresh_seeds_used": False,
        "holdout_used": False,
        "integrity": integrity,
        "integrity_passed": integrity_passed,
        "case_results": case_results,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not integrity_passed:
        output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        print("WORKER16_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
        raise SystemExit("Worker #16 integrity gate failed; no candidate-set interpretation")

    target = case_results[TARGET]
    v4s = target["v4_candidate_set"]
    v5s = target["v5_candidate_set"]
    added = top_tier_placement_added(v5s)

    A = v4s["max_score_collect_count"] >= 1 and v4s["max_score_place_count"] == 0
    B = v5s["max_score_collect_count"] >= 1 and v5s["max_score_place_count"] >= 1
    C = bool(added)

    historical_move = HISTORICAL_NEXT[TARGET]["move"]
    hist_key = signature_key(historical_move)
    added_keys = {signature_key(row["move"]) for row in added}
    D = (
        historical_move["action"] == "place"
        and move_is_top_tier(v5s, historical_move)
        and hist_key in added_keys
    )

    historical_candidate = next(
        (
            row for row in v5s["max_score_candidates"]
            if signature_key(row["move"]) == hist_key
        ),
        None,
    )
    E = bool(
        D
        and historical_candidate is not None
        and historical_candidate["placement_explanation"]["closure_gain"] <= 0
    )

    predicates = {
        "A_v4_top_tier_collect_only": A,
        "B_v5_top_tier_mixed_collect_place": B,
        "C_v5_added_top_tier_placement": C,
        "D_actual_next_v5_action_is_added_top_tier_placement": D,
        "E_actual_added_placement_is_nonclosing": E,
    }

    if all(predicates.values()):
        classification = "v5_2238_next_decision_tie_expansion_supported"
    elif not A or not C or not D:
        classification = "v5_2238_next_decision_tie_expansion_not_supported"
    else:
        classification = "v5_2238_next_decision_tie_expansion_ambiguous"

    control_summaries = {}
    for tid in CONTROLS:
        result = case_results[tid]
        cv4 = result["v4_candidate_set"]
        cv5 = result["v5_candidate_set"]
        cadded = top_tier_placement_added(cv5)
        control_summaries[tid] = {
            "v4_top_tier_collect_only": (
                cv4["max_score_collect_count"] >= 1
                and cv4["max_score_place_count"] == 0
            ),
            "v5_top_tier_mixed_collect_place": (
                cv5["max_score_collect_count"] >= 1
                and cv5["max_score_place_count"] >= 1
            ),
            "v5_added_top_tier_placement": bool(cadded),
            "historical_next_event": result["historical_next_event"],
            "historical_action_in_v5_top_tier": result["historical_action_in_v5_top_tier"],
            "v4_candidate_set": cv4,
            "v5_candidate_set": cv5,
        }

    payload.update({
        "target_predicates": predicates,
        "target_added_top_tier_placements": added,
        "historical_next_v5_action": HISTORICAL_NEXT[TARGET],
        "historical_next_v5_candidate": historical_candidate,
        "control_summaries": control_summaries,
        "final_preregistered_classification": classification,
        "interpretation_limit": "Target-specific candidate-set diagnosis on one already-known regression plus three selected controls; already-spent development data only. No tie-break fix, policy change, fresh seed, trajectory continuation, or win-rate claim.",
    })

    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print("WORKER16_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
    print("WORKER16_RESULT=" + json.dumps({
        "target": {
            "v4_candidate_set": v4s,
            "v5_candidate_set": v5s,
            "predicates": predicates,
            "historical_next_v5_action": HISTORICAL_NEXT[TARGET],
            "classification": classification,
        },
        "controls": control_summaries,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
