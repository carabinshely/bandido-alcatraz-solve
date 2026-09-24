from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, VisibleRepairReserveV5Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import (
    _bounded_merge_bank,
    is_unsafe_capacity_kill_without_visible_repair_reserve,
    move_features,
    score_features,
    standalone_exit_legal_move_count,
)

ROOT = Path(__file__).parents[1]
STARTING_MAIN = "6e0e1262c0a94e24ab62ca559fb5b5c1b22c2ac8"
DECISION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5815715639"
WORKER13_MANIFEST = ROOT / "experiments/real-deck-policy-v5/visible-repair-reserve-development-evaluation-2026-09-24.manifest.json"

SEEDS = [
    2001, 2004, 2005, 2020, 2024, 2034, 2084, 2098, 2104, 2110, 2129,
    2130, 2138, 2168, 2171, 2212, 2238, 2282, 2286, 2314, 2334, 2371, 2372,
]
CLASS_A_SEEDS = {
    2001, 2004, 2020, 2024, 2034, 2084, 2098, 2104, 2110, 2129, 2130,
    2138, 2168, 2171, 2212, 2314, 2334, 2372,
}
REGRESSION_SEEDS = {2238, 2282}

PERSISTENT = {
    "2001:a25:s24", "2004:a8:s7", "2020:a22:s21", "2034:a18:s17",
    "2098:a17:s16", "2104:a6:s5", "2110:a15:s14", "2129:a21:s20",
    "2138:a12:s11", "2171:a23:s22", "2212:a34:s33", "2314:a22:s21",
    "2334:a13:s12",
}
KNOWN_FALSE_POSITIVE = {
    "2024:a14:s13", "2130:a19:s18", "2168:a26:s25", "2282:a6:s5",
    "2372:a13:s12",
}
OTHER = {
    "2004:a9:s8", "2004:a12:s11", "2004:a17:s16", "2020:a24:s23",
    "2084:a10:s9", "2098:a19:s18", "2104:a7:s6", "2104:a11:s10",
    "2104:a12:s11", "2104:a14:s13", "2130:a29:s28", "2138:a13:s12",
    "2138:a16:s15", "2138:a19:s18", "2138:a20:s19", "2238:a20:s19",
    "2372:a22:s21",
}
AUDIT_IDS = PERSISTENT | KNOWN_FALSE_POSITIVE | OTHER
NORMAL_V4_EXCEPTION = "2084:a10:s9"

# tuple shape:
# (current_capacity, normal_count, unsafe_count, v4_unsafe,
#  v4_action, v4_card, v4_hand_index, v4_origin, v4_rotation,
#  v5_action, v5_card, v5_hand_index, v5_origin, v5_rotation)
EXPECTED = {
    "2001:a25:s24": (1,4,1,True,"place","photo-2-r2-c4",1,(-5,3),1,"place","photo-4-r3-c1",2,(-5,3),2),
    "2004:a8:s7": (1,4,1,True,"place","photo-1-r3-c2",1,(2,3),3,"place","photo-3-r4-c5",0,(2,3),0),
    "2020:a22:s21": (1,6,1,True,"place","photo-4-r2-c2",2,(-5,3),3,"collect","photo-4-r2-c2",2,None,0),
    "2034:a18:s17": (1,3,1,True,"place","photo-2-r3-c4",1,(-2,1),0,"collect","photo-2-r3-c4",1,None,0),
    "2098:a17:s16": (1,6,1,True,"place","photo-3-r1-c3",2,(-2,3),2,"place","photo-3-r1-c3",2,(-3,3),1),
    "2104:a6:s5": (1,4,1,True,"place","photo-2-r2-c4",0,(-2,-1),2,"place","photo-2-r4-c3",1,(-2,-1),2),
    "2110:a15:s14": (1,3,1,True,"place","photo-2-r2-c4",2,(-1,5),2,"place","photo-3-r4-c2",0,(-1,5),0),
    "2129:a21:s20": (2,1,3,True,"place","photo-1-r2-c4",2,(-3,-1),0,"place","photo-1-r2-c4",2,(-4,0),3),
    "2138:a12:s11": (1,3,1,True,"place","photo-3-r3-c4",2,(-3,-2),2,"place","photo-1-r3-c4",0,(-3,-2),0),
    "2171:a23:s22": (1,6,1,True,"place","photo-2-r3-c4",2,(3,-2),3,"collect","photo-2-r3-c4",2,None,0),
    "2212:a34:s33": (1,4,1,True,"place","photo-2-r2-c4",2,(-2,7),2,"place","photo-4-r2-c3",0,(-3,7),3),
    "2314:a22:s21": (1,6,1,True,"place","photo-1-r1-c4",1,(6,4),3,"collect","photo-1-r1-c4",1,None,0),
    "2334:a13:s12": (1,8,1,True,"place","photo-3-r3-c5",2,(-3,0),2,"collect","photo-3-r3-c5",2,None,0),

    "2024:a14:s13": (1,4,1,True,"place","photo-3-r2-c4",2,(-1,-4),1,"place","photo-3-r2-c4",2,(0,-4),0),
    "2130:a19:s18": (1,5,1,True,"place","photo-1-r2-c3",2,(-1,-5),2,"place","photo-4-r1-c1",1,(-1,-4),0),
    "2168:a26:s25": (1,9,1,True,"place","photo-2-r2-c2",2,(-7,-2),3,"place","photo-2-r2-c2",2,(-4,-1),3),
    "2282:a6:s5": (1,2,3,True,"place","photo-1-r1-c4",2,(2,-1),3,"collect","photo-1-r1-c4",2,None,0),
    "2372:a13:s12": (2,8,2,True,"place","photo-1-r4-c3",2,(3,2),1,"place","photo-1-r4-c3",2,(3,1),1),

    "2004:a9:s8": (1,4,1,True,"place","photo-1-r3-c2",0,(2,5),3,"place","photo-2-r4-c1",2,(1,5),1),
    "2004:a12:s11": (1,3,2,True,"place","photo-3-r3-c4",2,(1,6),1,"place","photo-1-r2-c5",1,(0,6),1),
    "2004:a17:s16": (1,2,2,True,"place","photo-3-r3-c4",1,(-2,5),3,"place","photo-4-r1-c4",2,(-2,5),3),
    "2020:a24:s23": (1,6,1,True,"place","photo-2-r3-c4",2,(-5,3),0,"collect","photo-2-r3-c4",2,None,0),
    "2084:a10:s9": (1,5,1,False,"place","photo-3-r3-c3",0,(2,1),3,"place","photo-1-r3-c3",1,(2,1),1),
    "2098:a19:s18": (1,6,1,True,"place","photo-3-r3-c5",2,(-4,2),2,"collect","photo-3-r3-c5",2,None,0),
    "2104:a7:s6": (1,4,1,True,"place","photo-2-r2-c4",0,(-3,-1),2,"place","photo-4-r2-c4",1,(-3,-2),0),
    "2104:a11:s10": (1,3,1,True,"place","photo-1-r3-c2",2,(-6,-2),1,"place","photo-2-r2-c5",1,(-6,-2),3),
    "2104:a12:s11": (1,4,1,True,"place","photo-1-r3-c2",1,(-7,-2),0,"place","photo-2-r1-c5",2,(-8,-2),1),
    "2104:a14:s13": (1,4,1,True,"place","photo-1-r3-c2",1,(-9,-3),1,"place","photo-2-r1-c2",2,(-9,-3),1),
    "2130:a29:s28": (1,6,1,True,"place","photo-2-r2-c4",2,(-3,-8),0,"place","photo-4-r3-c1",1,(-3,-8),2),
    "2138:a13:s12": (1,5,1,True,"place","photo-3-r3-c4",1,(-4,-1),2,"place","photo-4-r1-c4",0,(-4,-1),0),
    "2138:a16:s15": (1,5,1,True,"place","photo-3-r3-c4",0,(-5,0),2,"place","photo-1-r1-c2",2,(-3,0),0),
    "2138:a19:s18": (1,5,1,True,"place","photo-2-r3-c4",2,(-6,0),1,"place","photo-3-r2-c3",1,(-6,0),3),
    "2138:a20:s19": (1,2,1,True,"place","photo-2-r3-c4",1,(-5,-2),2,"collect","photo-2-r3-c4",1,None,0),
    "2238:a20:s19": (1,8,1,True,"place","photo-3-r3-c5",2,(-4,0),2,"place","photo-3-r3-c5",2,(0,2),0),
    "2372:a22:s21": (1,2,1,True,"place","photo-2-r2-c3",2,(4,3),0,"place","photo-2-r2-c3",2,(5,3),0),
}

# Worker #13 exact final V5 records, from canonical raw artifact.
EXPECTED_FINALS = {
    2001:(False,"deck_exhausted",69,21,3,6,3,True,True,False,True),
    2004:(False,"no_legal_move",38,3,0,12,8,True,False,False,True),
    2005:(True,"win",31,0,0,4,2,True,True,True,True),
    2020:(False,"deck_exhausted",69,20,2,8,4,True,True,False,True),
    2024:(False,"deck_exhausted",69,20,3,7,4,True,True,False,True),
    2034:(False,"deck_exhausted",69,13,2,6,5,True,True,False,True),
    2084:(False,"deck_exhausted",69,20,2,6,2,True,True,False,True),
    2098:(False,"deck_exhausted",69,17,2,7,4,True,True,False,True),
    2104:(False,"deck_exhausted",69,21,2,7,3,True,True,False,True),
    2110:(False,"deck_exhausted",69,25,2,9,3,True,True,False,True),
    2129:(False,"deck_exhausted",69,18,3,9,3,True,True,False,True),
    2130:(False,"deck_exhausted",69,23,2,7,4,True,True,False,True),
    2138:(False,"no_legal_move",38,3,0,11,7,True,True,True,True),
    2168:(False,"deck_exhausted",69,17,1,5,5,True,True,False,True),
    2171:(False,"deck_exhausted",69,18,2,8,4,True,True,False,True),
    2212:(False,"no_legal_move",61,6,1,6,4,True,True,False,True),
    2238:(False,"deck_exhausted",69,18,3,6,5,True,True,False,True),
    2282:(False,"deck_exhausted",69,17,2,5,6,True,True,False,True),
    2286:(True,"win",16,0,0,3,3,True,True,True,True),
    2314:(False,"deck_exhausted",69,20,2,6,4,True,True,False,True),
    2334:(False,"deck_exhausted",69,21,2,5,4,True,True,False,True),
    2371:(True,"win",24,0,0,7,4,True,True,True,True),
    2372:(False,"deck_exhausted",69,16,2,6,5,True,True,False,True),
}


def move_signature(state: GameState, move) -> tuple:
    card = state.hand[move.hand_index]
    return (
        move.action.value,
        card.card_id,
        move.hand_index,
        tuple(move.origin) if move.origin is not None else None,
        move.quarter_turns,
    )


def expected_move_pair(value: tuple) -> tuple[tuple, tuple]:
    return (
        (value[4], value[5], value[6], value[7], value[8]),
        (value[9], value[10], value[11], value[12], value[13]),
    )


def final_tuple(state: GameState, reason: str) -> tuple:
    ready = is_equipment_ready(state.raincoats, state.ropes)
    return (
        state.won,
        reason,
        state.turns,
        state.board.open_tunnels,
        state.board.visible_water_cells,
        state.raincoats,
        state.ropes,
        ready,
        state.exit_placed,
        state.exit_placed and state.board.visible_water_cells == 0 and ready,
        state.exit_seen,
    )


def board_metrics(board) -> dict:
    return {
        "open_tunnels": board.open_tunnels,
        "visible_water_cells": board.visible_water_cells,
        "water_obstruction": board.water_obstruction,
        "trapped_water_cells": board.trapped_water_cells,
        "merge_opportunities": board.merge_opportunities,
        "bounded_merge_bank": _bounded_merge_bank(board),
    }


def immediate_board_after(state: GameState, move):
    board = state.board.clone()
    if move.action is Action.PLACE:
        card = state.hand[move.hand_index]
        assert move.origin is not None
        board.place(card, move.origin, move.quarter_turns)
    return board


def no_draw_features(state: GameState, move):
    # Canonical move_features(), but with an intentionally empty draw pile so
    # the secondary local audit does not consume or inspect a replacement draw.
    shadow = GameState(
        board=state.board.clone(),
        draw_pile=[],
        hand=list(state.hand),
        raincoats=state.raincoats,
        ropes=state.ropes,
        exit_placed=state.exit_placed,
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
        exit_seen=state.exit_seen,
    )
    return move_features(shadow, move)


def primary_class(open_debt: int, water_debt: int) -> str:
    if open_debt >= 0 and water_debt >= 0 and (open_debt > 0 or water_debt > 0):
        return "strict_primary_geometry_debt"
    if (open_debt > 0 and water_debt < 0) or (open_debt < 0 and water_debt > 0):
        return "primary_geometry_tradeoff"
    if open_debt == 0 and water_debt == 0:
        return "primary_geometry_equal"
    if open_debt <= 0 and water_debt <= 0 and (open_debt < 0 or water_debt < 0):
        return "primary_geometry_improvement"
    raise AssertionError((open_debt, water_debt))


def summarize_classes(records: list[dict]) -> dict:
    counts = Counter(record["primary_geometry_class"] for record in records)
    return {
        "total": len(records),
        "strict_primary_geometry_debt": counts["strict_primary_geometry_debt"],
        "primary_geometry_tradeoff": counts["primary_geometry_tradeoff"],
        "primary_geometry_equal": counts["primary_geometry_equal"],
        "primary_geometry_improvement": counts["primary_geometry_improvement"],
    }


def provenance_for(tid: str) -> str:
    if tid in PERSISTENT:
        return "persistent"
    if tid in KNOWN_FALSE_POSITIVE:
        return "known_false_positive"
    if tid in OTHER:
        return "other"
    raise KeyError(tid)


def replay_seed(seed: int, deck, weights) -> tuple[dict, list[dict], dict]:
    rng = Random(seed)
    v4 = BoundedMergeV4Policy(setup_weight=250)
    v5 = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    records: list[dict] = []
    first_choice_change_id = None
    first_exit_seen = None

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

        moves = state.legal_moves()
        if not moves:
            before_seen = state.exit_seen
            if state.refresh_unplayable_hand():
                if not before_seen and state.exit_seen and first_exit_seen is None:
                    first_exit_seen = {
                        "kind": "refresh",
                        "state_turn": state.turns,
                    }
                continue
            reason = "deck_exhausted" if state.exhausted else "no_legal_move"
            break

        transition_id = f"{seed}:a{state.turns + 1}:s{state.turns}"
        current_capacity = standalone_exit_legal_move_count(
            state.board,
            deck.exit_card,
        )
        phase_active = (
            not state.exit_placed
            and not state.exit_seen
            and current_capacity > 0
        )
        if phase_active:
            unsafe_flags = [
                is_unsafe_capacity_kill_without_visible_repair_reserve(
                    state,
                    move,
                    deck.exit_card,
                )
                for move in moves
            ]
        else:
            unsafe_flags = [False] * len(moves)
        unsafe_count = sum(unsafe_flags)
        normal_count = len(moves) - unsafe_count

        probe_rng = Random()
        probe_rng.setstate(rng.getstate())
        v4_move = v4.choose(state, probe_rng)
        v5_move = v5.choose(state, rng)
        assert v4_move is not None and v5_move is not None

        if v4_move != v5_move:
            if first_choice_change_id is None:
                first_choice_change_id = transition_id

            v4_unsafe = (
                is_unsafe_capacity_kill_without_visible_repair_reserve(
                    state,
                    v4_move,
                    deck.exit_card,
                )
                if phase_active
                else False
            )

            pre = board_metrics(state.board)
            post_v4_board = immediate_board_after(state, v4_move)
            post_v5_board = immediate_board_after(state, v5_move)
            post_v4 = board_metrics(post_v4_board)
            post_v5 = board_metrics(post_v5_board)

            open_debt = post_v5["open_tunnels"] - post_v4["open_tunnels"]
            water_debt = (
                post_v5["visible_water_cells"]
                - post_v4["visible_water_cells"]
            )

            v4_features = no_draw_features(state, v4_move)
            v5_features = no_draw_features(state, v5_move)
            v4_score = score_features(v4_features, weights)
            v5_score = score_features(v5_features, weights)

            records.append(
                {
                    "transition_id": transition_id,
                    "seed": seed,
                    "action_turn": state.turns + 1,
                    "state_turn_before_action": state.turns,
                    "exit_seen": state.exit_seen,
                    "exit_placed": state.exit_placed,
                    "current_exit_capacity": current_capacity,
                    "normal_move_count": normal_count,
                    "unsafe_move_count": unsafe_count,
                    "v4_unsafe": v4_unsafe,
                    "v4_probe": {
                        "action": move_signature(state, v4_move)[0],
                        "card_id": move_signature(state, v4_move)[1],
                        "hand_index": v4_move.hand_index,
                        "origin": list(v4_move.origin) if v4_move.origin is not None else None,
                        "quarter_turns": v4_move.quarter_turns,
                    },
                    "v5_selected": {
                        "action": move_signature(state, v5_move)[0],
                        "card_id": move_signature(state, v5_move)[1],
                        "hand_index": v5_move.hand_index,
                        "origin": list(v5_move.origin) if v5_move.origin is not None else None,
                        "quarter_turns": v5_move.quarter_turns,
                    },
                    "action_pair": f"{v4_move.action.value}->{v5_move.action.value}",
                    "is_first_divergence_for_seed": transition_id == first_choice_change_id,
                    "provenance": provenance_for(transition_id) if transition_id in AUDIT_IDS else "unexpected",
                    "worker13_final_outcome_category": (
                        "regression"
                        if seed in REGRESSION_SEEDS
                        else "unchanged_nonwin"
                    ),
                    "pre_action_board": pre,
                    "post_v4_board": post_v4,
                    "post_v5_board": post_v5,
                    "open_tunnel_debt": open_debt,
                    "visible_water_debt": water_debt,
                    "primary_geometry_class": primary_class(
                        open_debt,
                        water_debt,
                    ),
                    "v4_move_features": asdict(v4_features),
                    "v5_move_features": asdict(v5_features),
                    "v4_score": v4_score,
                    "v5_score": v5_score,
                    "v4_score_gap_v4_minus_v5": v4_score - v5_score,
                    "local_counterfactual_replacement_draw_used": False,
                    "local_counterfactual_refresh_used": False,
                    "local_counterfactual_second_action_used": False,
                    "local_counterfactual_trajectory_continued": False,
                }
            )

        before_seen = state.exit_seen
        selected_card_is_exit = state.hand[v5_move.hand_index].is_exit
        action_turn = state.turns + 1
        state.apply(v5_move)
        if not before_seen and state.exit_seen and first_exit_seen is None:
            first_exit_seen = {
                "kind": (
                    "exit_placement"
                    if selected_card_is_exit
                    else "normal_draw"
                ),
                "action_turn": action_turn,
                "state_turn": state.turns,
            }
    else:
        reason = "step_limit"

    return (
        {
            "seed": seed,
            "final": final_tuple(state, reason),
            "first_choice_change_id": first_choice_change_id,
            "first_exit_seen_transition": first_exit_seen,
        },
        records,
        {
            "reason": reason,
            "state": state,
        },
    )


def distribution(values: list[int]) -> dict:
    if not values:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "mean": None,
            "maximum": None,
            "values": [],
        }
    ordered = sorted(values)
    return {
        "count": len(values),
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "maximum": max(values),
        "values": ordered,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    assert len(AUDIT_IDS) == 35
    assert len(PERSISTENT) == 13
    assert len(KNOWN_FALSE_POSITIVE) == 5
    assert len(OTHER) == 17
    assert len({int(tid.split(":", 1)[0]) for tid in AUDIT_IDS}) == 20

    manifest = json.loads(WORKER13_MANIFEST.read_text(encoding="utf-8"))
    deck = load_real_deck(ROOT / "data")
    v4 = BoundedMergeV4Policy(setup_weight=250)
    v5 = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)

    changed_files = subprocess.check_output(
        ["git", "diff", "--name-only", STARTING_MAIN, "HEAD"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden_changes = [
        path
        for path in changed_files
        if path.startswith(("src/", "data/"))
        or path
        in {
            "docs/decisions/2026-09-23-v5-visible-repair-reserve-design.md",
        }
    ]

    integrity = {
        "repository_and_implementation": {
            "worker13_manifest_present": WORKER13_MANIFEST.exists(),
            "worker13_manifest_classification": manifest.get(
                "final_preregistered_classification"
            ),
            "worker13_seed_scope_exact": manifest.get("seed_scope") == SEEDS,
            "v5_weights_equal_v4_250": v5.weights == v4.weights,
            "production_or_model_changes": forbidden_changes,
            "deterministic_legal_move_ordering_unchanged": (
                "src/bandido_alcatraz/moves.py" not in changed_files
            ),
            "changed_files": changed_files,
        },
    }

    seed_replay: dict[str, dict] = {}
    all_records: list[dict] = []
    for seed in SEEDS:
        seed_summary, records, _ = replay_seed(seed, deck, v4.weights)
        seed_replay[str(seed)] = seed_summary
        all_records.extend(records)

    final_mismatches = []
    for seed in SEEDS:
        actual = seed_replay[str(seed)]["final"]
        expected = EXPECTED_FINALS[seed]
        if actual != expected:
            final_mismatches.append(
                {
                    "seed": seed,
                    "expected": expected,
                    "actual": actual,
                }
            )

    actual_by_id = {
        record["transition_id"]: record
        for record in all_records
    }
    actual_ids = set(actual_by_id)
    unexpected_ids = sorted(actual_ids - AUDIT_IDS)
    missing_ids = sorted(AUDIT_IDS - actual_ids)

    event_mismatches = []
    for tid in sorted(AUDIT_IDS):
        record = actual_by_id.get(tid)
        if record is None:
            continue
        expected = EXPECTED[tid]
        expected_v4, expected_v5 = expected_move_pair(expected)
        actual_v4 = (
            record["v4_probe"]["action"],
            record["v4_probe"]["card_id"],
            record["v4_probe"]["hand_index"],
            tuple(record["v4_probe"]["origin"])
            if record["v4_probe"]["origin"] is not None
            else None,
            record["v4_probe"]["quarter_turns"],
        )
        actual_v5 = (
            record["v5_selected"]["action"],
            record["v5_selected"]["card_id"],
            record["v5_selected"]["hand_index"],
            tuple(record["v5_selected"]["origin"])
            if record["v5_selected"]["origin"] is not None
            else None,
            record["v5_selected"]["quarter_turns"],
        )
        mismatch = {}
        if record["current_exit_capacity"] != expected[0]:
            mismatch["current_exit_capacity"] = {
                "expected": expected[0],
                "actual": record["current_exit_capacity"],
            }
        if record["normal_move_count"] != expected[1]:
            mismatch["normal_move_count"] = {
                "expected": expected[1],
                "actual": record["normal_move_count"],
            }
        if record["unsafe_move_count"] != expected[2]:
            mismatch["unsafe_move_count"] = {
                "expected": expected[2],
                "actual": record["unsafe_move_count"],
            }
        if record["v4_unsafe"] != expected[3]:
            mismatch["v4_unsafe"] = {
                "expected": expected[3],
                "actual": record["v4_unsafe"],
            }
        if actual_v4 != expected_v4:
            mismatch["v4_probe"] = {
                "expected": expected_v4,
                "actual": actual_v4,
            }
        if actual_v5 != expected_v5:
            mismatch["v5_selected"] = {
                "expected": expected_v5,
                "actual": actual_v5,
            }
        if mismatch:
            event_mismatches.append(
                {"transition_id": tid, **mismatch}
            )

    affected_seeds = {record["seed"] for record in all_records}
    provenance_counts = Counter(record["provenance"] for record in all_records)
    unsafe_true_ids = {
        record["transition_id"]
        for record in all_records
        if record["v4_unsafe"]
    }
    unsafe_false_ids = {
        record["transition_id"]
        for record in all_records
        if not record["v4_unsafe"]
    }

    repo_section = integrity["repository_and_implementation"]
    repo_section["passed"] = (
        repo_section["worker13_manifest_present"]
        and repo_section["worker13_manifest_classification"]
        == "v5_development_signal_not_supported"
        and repo_section["worker13_seed_scope_exact"]
        and repo_section["v5_weights_equal_v4_250"]
        and not forbidden_changes
        and repo_section["deterministic_legal_move_ordering_unchanged"]
    )
    integrity["worker13_final_replay"] = {
        "records_compared": 23,
        "exact_matches": 23 - len(final_mismatches),
        "mismatches": final_mismatches,
        "passed": not final_mismatches,
    }
    integrity["choice_change_population"] = {
        "expected_count": 35,
        "actual_count": len(all_records),
        "missing_ids": missing_ids,
        "unexpected_ids": unexpected_ids,
        "distinct_affected_seeds": len(affected_seeds),
        "expected_distinct_affected_seeds": 20,
        "passed": (
            len(all_records) == 35
            and not missing_ids
            and not unexpected_ids
            and len(affected_seeds) == 20
        ),
    }
    integrity["choice_change_identity"] = {
        "records_compared": 35,
        "exact_matches": 35 - len(event_mismatches),
        "mismatches": event_mismatches,
        "passed": not event_mismatches,
    }
    integrity["provenance"] = {
        "persistent": provenance_counts["persistent"],
        "known_false_positive": provenance_counts["known_false_positive"],
        "other": provenance_counts["other"],
        "passed": (
            provenance_counts["persistent"] == 13
            and provenance_counts["known_false_positive"] == 5
            and provenance_counts["other"] == 17
        ),
    }
    integrity["v4_unsafe_fidelity"] = {
        "true_count": len(unsafe_true_ids),
        "false_count": len(unsafe_false_ids),
        "false_ids": sorted(unsafe_false_ids),
        "expected_false_ids": [NORMAL_V4_EXCEPTION],
        "passed": (
            len(unsafe_true_ids) == 34
            and unsafe_false_ids == {NORMAL_V4_EXCEPTION}
        ),
    }
    integrity["all_choice_changes_pre_exit_sighting"] = {
        "false_exit_seen_count": sum(
            not record["exit_seen"] for record in all_records
        ),
        "total": len(all_records),
        "passed": all(not record["exit_seen"] for record in all_records),
    }

    integrity_passed = all(
        section["passed"]
        for section in integrity.values()
    )

    payload = {
        "schema": "bandido-alcatraz-v5-choice-change-geometry-debt-audit",
        "schema_version": 1,
        "experiment_id": "worker-14-v5-choice-change-geometry-debt-audit",
        "date": "2026-09-24",
        "dataset_status": (
            "already-spent / selected / development / diagnostic / "
            "non-confirmatory"
        ),
        "authoritative_orchestrator_decision_url": DECISION_URL,
        "starting_main": STARTING_MAIN,
        "evaluated_commit": (
            os.environ.get("EVALUATED_COMMIT")
            or os.environ.get("GITHUB_SHA")
        ),
        "workflow_run": {
            "run_id": (
                int(os.environ["GITHUB_RUN_ID"])
                if os.environ.get("GITHUB_RUN_ID")
                else None
            ),
            "url": (
                "https://github.com/carabinshely/"
                "bandido-alcatraz-solve/actions/runs/"
                f"{os.environ.get('GITHUB_RUN_ID')}"
            ),
        },
        "runner": os.environ.get("RUNNER_NAME"),
        "worker13_source": {
            "manifest_path": str(WORKER13_MANIFEST.relative_to(ROOT)),
            "raw_drive_file_id": "1cYGQHLh2-A8b8TaeL20_fXVH-6Kg8QfL",
            "raw_archive_bytes": 403282,
            "raw_archive_sha256": (
                "bd300ce874b14b72c41c57a56a0230c0703ef63a50ae97a56856ba3a5d63c583"
            ),
            "raw_inner_bytes": 19494891,
            "raw_inner_sha256": (
                "f8b20de7d24d14cfd8fe33cd770057ce664a706531d4d8dbc09b3477ad3da9c2"
            ),
        },
        "model": {
            "deck_file": "data/deck-v1.json",
            "exit_geometry_source": "data/deck-observations-v0.json",
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
        },
        "policies": {
            "v4": "BoundedMergeV4Policy(setup_weight=250)",
            "v5": "VisibleRepairReserveV5Policy(exit_card=deck.exit_card)",
        },
        "seed_scope": SEEDS,
        "audit_transition_ids": {
            "persistent": sorted(PERSISTENT),
            "known_false_positive": sorted(KNOWN_FALSE_POSITIVE),
            "other": sorted(OTHER),
        },
        "integrity": integrity,
        "integrity_passed": integrity_passed,
        "seed_replay": seed_replay,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not integrity_passed:
        payload["transition_records"] = all_records
        output.write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print("WORKER14_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
        raise SystemExit(
            "Worker #14 integrity gate failed; mechanism not interpreted"
        )

    records_by_group = {
        "all_35": all_records,
        "unsafe_34": [
            record for record in all_records if record["v4_unsafe"]
        ],
        "persistent_13": [
            record for record in all_records
            if record["provenance"] == "persistent"
        ],
        "known_false_positive_5": [
            record for record in all_records
            if record["provenance"] == "known_false_positive"
        ],
        "other_unsafe_16": [
            record for record in all_records
            if record["provenance"] == "other" and record["v4_unsafe"]
        ],
        "rng_candidate_exception_1": [
            record for record in all_records
            if record["transition_id"] == NORMAL_V4_EXCEPTION
        ],
        "first_divergence_20": [
            record for record in all_records
            if record["is_first_divergence_for_seed"]
        ],
    }
    class_summaries = {
        key: summarize_classes(records)
        for key, records in records_by_group.items()
    }

    strict_records = [
        record
        for record in all_records
        if record["primary_geometry_class"]
        == "strict_primary_geometry_debt"
    ]
    strict_seed_ids = {
        record["seed"] for record in strict_records
    }
    affected_diverged_seed_count = len(
        affected_seeds & strict_seed_ids
    )
    affected_class_a_seed_count = len(
        CLASS_A_SEEDS & strict_seed_ids
    )

    positive_open_debts = [
        record["open_tunnel_debt"]
        for record in all_records
        if record["open_tunnel_debt"] > 0
    ]
    positive_water_debts = [
        record["visible_water_debt"]
        for record in all_records
        if record["visible_water_debt"] > 0
    ]
    score_gaps = [
        record["v4_score_gap_v4_minus_v5"]
        for record in all_records
    ]
    action_pairs = Counter(record["action_pair"] for record in all_records)

    seed_strict_coverage = {
        str(seed): {
            "has_strict_primary_geometry_debt_before_exit_sighting": (
                seed in strict_seed_ids
            ),
            "strict_transition_ids": [
                record["transition_id"]
                for record in strict_records
                if record["seed"] == seed
            ],
        }
        for seed in sorted(CLASS_A_SEEDS)
    }

    regression_cases = {}
    for seed in sorted(REGRESSION_SEEDS):
        seed_records = [
            record
            for record in all_records
            if record["seed"] == seed
        ]
        regression_cases[str(seed)] = {
            "worker13_outcome": "regression",
            "transition_count": len(seed_records),
            "transitions": [
                {
                    "transition_id": record["transition_id"],
                    "action_pair": record["action_pair"],
                    "open_tunnel_debt": record["open_tunnel_debt"],
                    "visible_water_debt": record["visible_water_debt"],
                    "primary_geometry_class": record[
                        "primary_geometry_class"
                    ],
                    "v4_score": record["v4_score"],
                    "v5_score": record["v5_score"],
                    "v4_score_gap_v4_minus_v5": record[
                        "v4_score_gap_v4_minus_v5"
                    ],
                }
                for record in seed_records
            ],
            "final": seed_replay[str(seed)]["final"],
        }

    strict_count = class_summaries["all_35"][
        "strict_primary_geometry_debt"
    ]
    if (
        strict_count >= 24
        and affected_diverged_seed_count >= 16
        and affected_class_a_seed_count >= 14
    ):
        classification = "v5_failure_geometry_debt_supported"
    elif (
        strict_count <= 17
        or affected_diverged_seed_count <= 10
        or affected_class_a_seed_count <= 9
    ):
        classification = "v5_failure_geometry_debt_not_supported"
    else:
        classification = "v5_failure_geometry_debt_ambiguous"

    payload.update(
        {
            "transition_records": all_records,
            "primary_class_summaries": class_summaries,
            "seed_level_coverage": {
                "affected_diverged_seeds_with_strict_debt": (
                    affected_diverged_seed_count
                ),
                "affected_diverged_seed_total": 20,
                "class_a_seeds_with_strict_debt": (
                    affected_class_a_seed_count
                ),
                "class_a_seed_total": 18,
                "class_a_per_seed": seed_strict_coverage,
            },
            "action_pair_counts": dict(sorted(action_pairs.items())),
            "place_to_collect_count": action_pairs["place->collect"],
            "positive_open_tunnel_debt_distribution": distribution(
                positive_open_debts
            ),
            "positive_visible_water_debt_distribution": distribution(
                positive_water_debts
            ),
            "v4_score_gap_distribution_v4_minus_v5": distribution(
                score_gaps
            ),
            "regression_cases": regression_cases,
            "rng_candidate_set_exception": next(
                record
                for record in all_records
                if record["transition_id"] == NORMAL_V4_EXCEPTION
            ),
            "final_preregistered_classification": classification,
            "interpretation_limit": (
                "Immediate local diagnostic on an intentionally selected, "
                "already-spent development cohort; no population-effect or "
                "confirmatory claim."
            ),
        }
    )

    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("WORKER14_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
    print(
        "WORKER14_RESULT="
        + json.dumps(
            {
                "primary_class_summaries": class_summaries,
                "affected_diverged_seeds_with_strict_debt": (
                    affected_diverged_seed_count
                ),
                "class_a_seeds_with_strict_debt": (
                    affected_class_a_seed_count
                ),
                "place_to_collect_count": action_pairs[
                    "place->collect"
                ],
                "positive_open_tunnel_debt_distribution": distribution(
                    positive_open_debts
                ),
                "positive_visible_water_debt_distribution": distribution(
                    positive_water_debts
                ),
                "v4_score_gap_distribution_v4_minus_v5": distribution(
                    score_gaps
                ),
                "regression_cases": regression_cases,
                "rng_exception": payload[
                    "rng_candidate_set_exception"
                ],
                "classification": classification,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
