from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, Move, legal_moves
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, VisibleRepairReserveV5Policy
from bandido_alcatraz.strategy import (
    clone_state,
    is_unsafe_capacity_kill_without_visible_repair_reserve,
    standalone_exit_legal_move_count,
)

ROOT = Path(__file__).parents[1]
STARTING_MAIN = "f9f3484a38e9e129fcf2cbcb70a9b517a20a1e29"
DECISION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5830566808"
WORKER14_MANIFEST = ROOT / "experiments/real-deck-policy-v5/choice-change-geometry-debt-audit-2026-09-24.manifest.json"

PRIMARY_IDS = [
    "2024:a14:s13",
    "2098:a17:s16",
    "2168:a26:s25",
    "2238:a20:s19",
    "2372:a13:s12",
    "2372:a22:s21",
]
CONTROL_ID = "2084:a10:s9"
ALL_IDS = set(PRIMARY_IDS + [CONTROL_ID])
PRIMARY_SEEDS = sorted({int(tid.split(":", 1)[0]) for tid in PRIMARY_IDS})
REPLAY_SEEDS = sorted({int(tid.split(":", 1)[0]) for tid in ALL_IDS})
EXPECTED = json.loads(r'''{
  "2024:a14:s13": {
    "fingerprint_sha256": "f04724a6f4335fb0bccee6c730cf384139df7d3caf501b46e7855349c3cca023",
    "hand": [
      "photo-2-r4-c2",
      "photo-1-r4-c2",
      "photo-3-r2-c4"
    ],
    "raincoats": 2,
    "ropes": 2,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 13,
    "v4": {
      "action": "place",
      "card_id": "photo-3-r2-c4",
      "hand_index": 2,
      "origin": [
        -1,
        -4
      ],
      "quarter_turns": 1
    },
    "v5": {
      "action": "place",
      "card_id": "photo-3-r2-c4",
      "hand_index": 2,
      "origin": [
        0,
        -4
      ],
      "quarter_turns": 0
    },
    "capacity": 1,
    "normal": 4,
    "unsafe": 1,
    "v4_unsafe": true,
    "w14_class": "primary_geometry_equal",
    "replacement_draw": "photo-3-r1-c2",
    "successor_hand": [
      "photo-2-r4-c2",
      "photo-1-r4-c2",
      "photo-3-r1-c2"
    ],
    "outcome": "unchanged_nonwin"
  },
  "2098:a17:s16": {
    "fingerprint_sha256": "cdab5702ca0062f14c03343a4fbaab58954725210f519f3967cbbdb0a03aa969",
    "hand": [
      "photo-1-r2-c5",
      "photo-4-r2-c4",
      "photo-3-r1-c3"
    ],
    "raincoats": 3,
    "ropes": 2,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 16,
    "v4": {
      "action": "place",
      "card_id": "photo-3-r1-c3",
      "hand_index": 2,
      "origin": [
        -2,
        3
      ],
      "quarter_turns": 2
    },
    "v5": {
      "action": "place",
      "card_id": "photo-3-r1-c3",
      "hand_index": 2,
      "origin": [
        -3,
        3
      ],
      "quarter_turns": 1
    },
    "capacity": 1,
    "normal": 6,
    "unsafe": 1,
    "v4_unsafe": true,
    "w14_class": "primary_geometry_equal",
    "replacement_draw": "photo-4-r1-c5",
    "successor_hand": [
      "photo-1-r2-c5",
      "photo-4-r2-c4",
      "photo-4-r1-c5"
    ],
    "outcome": "unchanged_nonwin"
  },
  "2168:a26:s25": {
    "fingerprint_sha256": "e25750f9672c58dc8b1dbc293ef78b6aa10abe11a00d618e34d9dbbdaaa3e635",
    "hand": [
      "photo-2-r3-c5",
      "photo-1-r2-c5",
      "photo-2-r2-c2"
    ],
    "raincoats": 3,
    "ropes": 2,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 25,
    "v4": {
      "action": "place",
      "card_id": "photo-2-r2-c2",
      "hand_index": 2,
      "origin": [
        -7,
        -2
      ],
      "quarter_turns": 3
    },
    "v5": {
      "action": "place",
      "card_id": "photo-2-r2-c2",
      "hand_index": 2,
      "origin": [
        -4,
        -1
      ],
      "quarter_turns": 3
    },
    "capacity": 1,
    "normal": 9,
    "unsafe": 1,
    "v4_unsafe": true,
    "w14_class": "primary_geometry_improvement",
    "replacement_draw": "photo-4-r1-c2",
    "successor_hand": [
      "photo-2-r3-c5",
      "photo-1-r2-c5",
      "photo-4-r1-c2"
    ],
    "outcome": "unchanged_nonwin"
  },
  "2238:a20:s19": {
    "fingerprint_sha256": "8c96ad9df4548b316af8dfde0c15ac7a4c898bfc82acd7d3bdff1418c93509ef",
    "hand": [
      "photo-2-r3-c5",
      "photo-2-r4-c2",
      "photo-3-r3-c5"
    ],
    "raincoats": 4,
    "ropes": 2,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 19,
    "v4": {
      "action": "place",
      "card_id": "photo-3-r3-c5",
      "hand_index": 2,
      "origin": [
        -4,
        0
      ],
      "quarter_turns": 2
    },
    "v5": {
      "action": "place",
      "card_id": "photo-3-r3-c5",
      "hand_index": 2,
      "origin": [
        0,
        2
      ],
      "quarter_turns": 0
    },
    "capacity": 1,
    "normal": 8,
    "unsafe": 1,
    "v4_unsafe": true,
    "w14_class": "primary_geometry_equal",
    "replacement_draw": "photo-3-r2-c2",
    "successor_hand": [
      "photo-2-r3-c5",
      "photo-2-r4-c2",
      "photo-3-r2-c2"
    ],
    "outcome": "regression"
  },
  "2372:a13:s12": {
    "fingerprint_sha256": "e3e4366df42442ca5610bf5f1852ece223d2cec7be5c8607c2ce01e934c92b45",
    "hand": [
      "photo-1-r2-c5",
      "photo-2-r4-c3",
      "photo-1-r4-c3"
    ],
    "raincoats": 3,
    "ropes": 1,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 12,
    "v4": {
      "action": "place",
      "card_id": "photo-1-r4-c3",
      "hand_index": 2,
      "origin": [
        3,
        2
      ],
      "quarter_turns": 1
    },
    "v5": {
      "action": "place",
      "card_id": "photo-1-r4-c3",
      "hand_index": 2,
      "origin": [
        3,
        1
      ],
      "quarter_turns": 1
    },
    "capacity": 2,
    "normal": 8,
    "unsafe": 2,
    "v4_unsafe": true,
    "w14_class": "primary_geometry_equal",
    "replacement_draw": "photo-2-r2-c2",
    "successor_hand": [
      "photo-1-r2-c5",
      "photo-2-r4-c3",
      "photo-2-r2-c2"
    ],
    "outcome": "unchanged_nonwin"
  },
  "2372:a22:s21": {
    "fingerprint_sha256": "8b6b947aa7f5b3628c524465caff213654f7525ba1ab261b1c886992d7c8828e",
    "hand": [
      "photo-1-r2-c5",
      "photo-2-r3-c1",
      "photo-2-r2-c3"
    ],
    "raincoats": 3,
    "ropes": 1,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 21,
    "v4": {
      "action": "place",
      "card_id": "photo-2-r2-c3",
      "hand_index": 2,
      "origin": [
        4,
        3
      ],
      "quarter_turns": 0
    },
    "v5": {
      "action": "place",
      "card_id": "photo-2-r2-c3",
      "hand_index": 2,
      "origin": [
        5,
        3
      ],
      "quarter_turns": 0
    },
    "capacity": 1,
    "normal": 2,
    "unsafe": 1,
    "v4_unsafe": true,
    "w14_class": "primary_geometry_improvement",
    "replacement_draw": null,
    "successor_hand": null,
    "outcome": "unchanged_nonwin"
  },
  "2084:a10:s9": {
    "fingerprint_sha256": "1e9d0664006850b15ff7c648eae974f8f84f307fd86ef324f5fb5a08d7a6ee46",
    "hand": [
      "photo-3-r3-c3",
      "photo-1-r3-c3",
      "photo-4-r3-c1"
    ],
    "raincoats": 1,
    "ropes": 1,
    "exit_seen": false,
    "exit_placed": false,
    "turns": 9,
    "v4": {
      "action": "place",
      "card_id": "photo-3-r3-c3",
      "hand_index": 0,
      "origin": [
        2,
        1
      ],
      "quarter_turns": 3
    },
    "v5": {
      "action": "place",
      "card_id": "photo-1-r3-c3",
      "hand_index": 1,
      "origin": [
        2,
        1
      ],
      "quarter_turns": 1
    },
    "capacity": 1,
    "normal": 5,
    "unsafe": 1,
    "v4_unsafe": false,
    "w14_class": "primary_geometry_equal",
    "replacement_draw": "photo-2-r3-c4",
    "successor_hand": [
      "photo-3-r3-c3",
      "photo-4-r3-c1",
      "photo-2-r3-c4"
    ],
    "outcome": "unchanged_nonwin"
  }
}''')


def stable_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def state_fingerprint(state: GameState) -> dict:
    cells = [
        (
            [x, y],
            sorted(edge.value for edge in cell.tunnel_edges),
            cell.water,
        )
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
        "set_aside": state.set_aside_unplayable,
    }


def draw_pile_ids(state: GameState) -> list[str]:
    return [card.card_id for card in state.draw_pile]


def move_record(state: GameState, move: Move) -> dict:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def expected_move_to_tuple(move: dict) -> tuple:
    return (
        move["action"],
        move["card_id"],
        move["hand_index"],
        tuple(move["origin"]) if move["origin"] is not None else None,
        move["quarter_turns"],
    )


def move_to_tuple(state: GameState, move: Move) -> tuple:
    record = move_record(state, move)
    return expected_move_to_tuple(record)


def find_exact_move(state: GameState, expected_move: dict) -> Move:
    wanted = expected_move_to_tuple(expected_move)
    for move in state.legal_moves():
        if move_to_tuple(state, move) == wanted:
            return move
    raise AssertionError(f"expected move not legal: {wanted}")


def primary_class(debts: dict) -> str:
    vals = [
        debts["max_gain_debt"],
        debts["improving_move_count_debt"],
        debts["capable_card_count_debt"],
    ]
    if all(value >= 0 for value in vals) and any(value > 0 for value in vals):
        return "strict_next_hand_closure_reserve_debt"
    if any(value > 0 for value in vals) and any(value < 0 for value in vals):
        return "next_hand_closure_reserve_tradeoff"
    if all(value == 0 for value in vals):
        return "next_hand_closure_reserve_equal"
    if all(value <= 0 for value in vals) and any(value < 0 for value in vals):
        return "next_hand_closure_reserve_improvement"
    raise AssertionError(vals)


def opportunity_metrics(state: GameState, exit_card) -> dict:
    successor_open = state.board.open_tunnels
    successor_water = state.board.visible_water_cells
    successor_merge = state.board.merge_opportunities
    placements = [
        move
        for move in legal_moves(state.board, tuple(state.hand))
        if move.action is Action.PLACE
    ]

    closure_gains = []
    water_gains = []
    merge_gains = []
    closure_capable = set()
    water_capable = set()
    placement_rows = []

    for move in placements:
        card = state.hand[move.hand_index]
        board = state.board.clone()
        assert move.origin is not None
        board.place(card, move.origin, move.quarter_turns)
        closure_gain = successor_open - board.open_tunnels
        water_gain = successor_water - board.visible_water_cells
        merge_gain = board.merge_opportunities - successor_merge
        closure_gains.append(closure_gain)
        water_gains.append(water_gain)
        merge_gains.append(merge_gain)
        if closure_gain > 0:
            closure_capable.add(move.hand_index)
        if water_gain > 0:
            water_capable.add(move.hand_index)
        placement_rows.append(
            {
                "move": move_record(state, move),
                "closure_gain": closure_gain,
                "visible_water_reduction": water_gain,
                "merge_opportunity_gain": merge_gain,
            }
        )

    return {
        "successor_open_tunnels": successor_open,
        "successor_visible_water": successor_water,
        "successor_exit_capacity": standalone_exit_legal_move_count(
            state.board,
            exit_card,
        ),
        "total_legal_ordinary_placement_count": len(placements),
        "max_one_step_closure_gain": max([g for g in closure_gains if g > 0], default=0),
        "closure_improving_placement_count": sum(g > 0 for g in closure_gains),
        "closure_capable_card_count": len(closure_capable),
        "max_one_step_visible_water_reduction": max([g for g in water_gains if g > 0], default=0),
        "visible_water_improving_placement_count": sum(g > 0 for g in water_gains),
        "visible_water_capable_card_count": len(water_capable),
        "max_one_step_merge_opportunity_gain": max([g for g in merge_gains if g > 0], default=0),
        "merge_opportunity_increasing_placement_count": sum(g > 0 for g in merge_gains),
        "placement_opportunities": placement_rows,
    }


def branch_once(pre_state: GameState, move: Move, exit_card) -> dict:
    branch = clone_state(pre_state)
    pre_draw_ids = draw_pile_ids(branch)
    pre_hand = [card.card_id for card in branch.hand]
    pre_turns = branch.turns
    pre_draw_count = len(branch.draw_pile)
    consumed_card_id = branch.hand[move.hand_index].card_id

    branch.apply(move, validate=False)

    post_draw_ids = draw_pile_ids(branch)
    successor_hand = [card.card_id for card in branch.hand]
    drawn_card_id = successor_hand[-1] if pre_draw_count > 0 else None

    return {
        "consumed_card_id": consumed_card_id,
        "consumed_hand_index": move.hand_index,
        "pre_hand": pre_hand,
        "pre_draw_pile_count": pre_draw_count,
        "pre_draw_pile_sha256": stable_hash(pre_draw_ids),
        "pre_draw_top_card_id": pre_draw_ids[-1] if pre_draw_ids else None,
        "post_draw_pile_count": len(branch.draw_pile),
        "post_draw_pile_sha256": stable_hash(post_draw_ids),
        "drawn_card_id": drawn_card_id,
        "successor_hand": successor_hand,
        "successor_exit_seen": branch.exit_seen,
        "successor_exit_placed": branch.exit_placed,
        "successor_turns": branch.turns,
        "exactly_one_card_consumed": len(pre_hand) - 1 + (1 if pre_draw_count > 0 else 0) == len(successor_hand),
        "exactly_one_draw_consumed": pre_draw_count - len(branch.draw_pile) == (1 if pre_draw_count > 0 else 0),
        "exactly_one_action": branch.turns == pre_turns + 1,
        "opportunity_metrics": opportunity_metrics(branch, exit_card),
    }


def reconstruct() -> tuple[dict, list[dict]]:
    deck = load_real_deck(ROOT / "data")
    expected_manifest = json.loads(WORKER14_MANIFEST.read_text())
    assert expected_manifest["final_preregistered_classification"] == "v5_failure_geometry_debt_ambiguous"

    v4 = BoundedMergeV4Policy(setup_weight=250)
    v5 = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
    assert v4.weights == v5.weights

    observed = {}
    trace = []

    for seed in REPLAY_SEEDS:
        rng = Random(seed)
        state = GameState.new(
            start_card=deck.start_easy,
            deck=deck.draw_deck(),
            hand_size=3,
            rng=rng,
        )
        max_action = max(
            int(tid.split(":a", 1)[1].split(":", 1)[0])
            for tid in ALL_IDS
            if tid.startswith(f"{seed}:")
        )

        for _ in range(1000):
            if state.won or state.board.open_tunnels == 0 or (
                not state.hand and not state.draw_pile
            ):
                break
            moves = state.legal_moves()
            if not moves:
                if state.refresh_unplayable_hand():
                    continue
                break

            tid = f"{seed}:a{state.turns + 1}:s{state.turns}"
            current_capacity = standalone_exit_legal_move_count(
                state.board,
                deck.exit_card,
            )
            phase_active = (
                not state.exit_placed
                and not state.exit_seen
                and current_capacity > 0
            )
            unsafe_flags = (
                [
                    is_unsafe_capacity_kill_without_visible_repair_reserve(
                        state,
                        move,
                        deck.exit_card,
                    )
                    for move in moves
                ]
                if phase_active
                else [False] * len(moves)
            )
            unsafe_count = sum(unsafe_flags)
            normal_count = len(moves) - unsafe_count

            probe_rng = Random()
            probe_rng.setstate(rng.getstate())
            v4_move = v4.choose(state, probe_rng)
            v5_move = v5.choose(state, rng)
            assert v4_move is not None and v5_move is not None

            if tid in ALL_IDS:
                fp = state_fingerprint(state)
                v4_unsafe = (
                    is_unsafe_capacity_kill_without_visible_repair_reserve(
                        state,
                        v4_move,
                        deck.exit_card,
                    )
                    if phase_active
                    else False
                )
                observed[tid] = {
                    "transition_id": tid,
                    "seed": seed,
                    "action_turn": state.turns + 1,
                    "state_turn": state.turns,
                    "fingerprint_sha256": stable_hash(fp),
                    "fingerprint": fp,
                    "draw_pile_count": len(state.draw_pile),
                    "draw_pile_sha256": stable_hash(draw_pile_ids(state)),
                    "draw_pile_top_card_id": state.draw_pile[-1].card_id if state.draw_pile else None,
                    "v4_probe": move_record(state, v4_move),
                    "v5_selected": move_record(state, v5_move),
                    "current_exit_capacity": current_capacity,
                    "normal_move_count": normal_count,
                    "unsafe_move_count": unsafe_count,
                    "v4_unsafe": v4_unsafe,
                }

            state.apply(v5_move)

            if state.turns >= max_action and all(
                tid2 in observed
                for tid2 in ALL_IDS
                if tid2.startswith(f"{seed}:")
            ):
                break

    return observed, trace


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    changed_files = subprocess.check_output(
        ["git", "diff", "--name-only", STARTING_MAIN, "HEAD"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden = [
        path
        for path in changed_files
        if path.startswith(("src/", "data/"))
        or path == "docs/decisions/2026-09-23-v5-visible-repair-reserve-design.md"
    ]

    observed, _ = reconstruct()

    integrity = {
        "repository": {
            "worker14_manifest_present": WORKER14_MANIFEST.exists(),
            "forbidden_changes": forbidden,
            "deterministic_legal_move_ordering_unchanged": "src/bandido_alcatraz/moves.py" not in changed_files,
        },
        "state_reconstruction": {
            "expected_count": 7,
            "observed_count": len(observed),
            "missing_ids": sorted(ALL_IDS - set(observed)),
            "mismatches": [],
        },
        "primary_six_card_identity": {
            "same_consumed_card_id": 0,
            "same_hand_index": 0,
            "both_place": 0,
            "total": 6,
        },
        "successor_identity": {
            "same_drawn_card_id": 0,
            "same_successor_hand": 0,
            "same_post_draw_pile": 0,
            "exactly_one_draw_each": 0,
            "exactly_one_action_each": 0,
            "exit_seen_false_both": 0,
            "total": 6,
            "mismatches": [],
        },
    }

    integrity["repository"]["passed"] = (
        integrity["repository"]["worker14_manifest_present"]
        and not forbidden
        and integrity["repository"]["deterministic_legal_move_ordering_unchanged"]
    )

    for tid in sorted(ALL_IDS):
        exp = EXPECTED[tid]
        obs = observed.get(tid)
        if obs is None:
            continue
        mismatch = {}
        if obs["fingerprint_sha256"] != exp["fingerprint_sha256"]:
            mismatch["fingerprint_sha256"] = {
                "expected": exp["fingerprint_sha256"],
                "actual": obs["fingerprint_sha256"],
            }
        for key in ("hand", "raincoats", "ropes", "exit_seen", "exit_placed", "turns"):
            actual = obs["fingerprint"][key]
            if actual != exp[key]:
                mismatch[key] = {"expected": exp[key], "actual": actual}
        if obs["v4_probe"] != exp["v4"]:
            mismatch["v4_probe"] = {"expected": exp["v4"], "actual": obs["v4_probe"]}
        if obs["v5_selected"] != exp["v5"]:
            mismatch["v5_selected"] = {"expected": exp["v5"], "actual": obs["v5_selected"]}
        if obs["current_exit_capacity"] != exp["capacity"]:
            mismatch["current_exit_capacity"] = {"expected": exp["capacity"], "actual": obs["current_exit_capacity"]}
        if obs["normal_move_count"] != exp["normal"]:
            mismatch["normal_move_count"] = {"expected": exp["normal"], "actual": obs["normal_move_count"]}
        if obs["unsafe_move_count"] != exp["unsafe"]:
            mismatch["unsafe_move_count"] = {"expected": exp["unsafe"], "actual": obs["unsafe_move_count"]}
        if obs["v4_unsafe"] != exp["v4_unsafe"]:
            mismatch["v4_unsafe"] = {"expected": exp["v4_unsafe"], "actual": obs["v4_unsafe"]}
        if mismatch:
            integrity["state_reconstruction"]["mismatches"].append({"transition_id": tid, **mismatch})

    integrity["state_reconstruction"]["passed"] = (
        len(observed) == 7
        and not integrity["state_reconstruction"]["missing_ids"]
        and not integrity["state_reconstruction"]["mismatches"]
    )

    deck = load_real_deck(ROOT / "data")
    primary_results = []
    control_result = None

    for tid in PRIMARY_IDS + [CONTROL_ID]:
        obs = observed[tid]
        exp = EXPECTED[tid]

        # Reconstruct exact state again and stop at this checkpoint.
        seed = obs["seed"]
        rng = Random(seed)
        state = GameState.new(
            start_card=deck.start_easy,
            deck=deck.draw_deck(),
            hand_size=3,
            rng=rng,
        )
        v4 = BoundedMergeV4Policy(setup_weight=250)
        v5 = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)

        while True:
            moves = state.legal_moves()
            if not moves:
                if state.refresh_unplayable_hand():
                    continue
                raise AssertionError(f"target not reached: {tid}")
            current_tid = f"{seed}:a{state.turns + 1}:s{state.turns}"
            probe_rng = Random()
            probe_rng.setstate(rng.getstate())
            v4_move_live = v4.choose(state, probe_rng)
            v5_move_live = v5.choose(state, rng)
            assert v4_move_live is not None and v5_move_live is not None
            if current_tid == tid:
                break
            state.apply(v5_move_live)

        v4_move = find_exact_move(state, exp["v4"])
        v5_move = find_exact_move(state, exp["v5"])

        v4_card = state.hand[v4_move.hand_index].card_id
        v5_card = state.hand[v5_move.hand_index].card_id

        v4_branch = branch_once(state, v4_move, deck.exit_card)
        v5_branch = branch_once(state, v5_move, deck.exit_card)

        if tid in PRIMARY_IDS:
            same_card = v4_card == v5_card
            same_index = v4_move.hand_index == v5_move.hand_index
            both_place = v4_move.action is Action.PLACE and v5_move.action is Action.PLACE
            integrity["primary_six_card_identity"]["same_consumed_card_id"] += int(same_card)
            integrity["primary_six_card_identity"]["same_hand_index"] += int(same_index)
            integrity["primary_six_card_identity"]["both_place"] += int(both_place)

            successor_checks = {
                "same_drawn_card_id": v4_branch["drawn_card_id"] == v5_branch["drawn_card_id"],
                "same_successor_hand": v4_branch["successor_hand"] == v5_branch["successor_hand"],
                "same_post_draw_pile": v4_branch["post_draw_pile_sha256"] == v5_branch["post_draw_pile_sha256"],
                "exactly_one_draw_each": (
                    v4_branch["exactly_one_draw_consumed"]
                    and v5_branch["exactly_one_draw_consumed"]
                ),
                "exactly_one_action_each": (
                    v4_branch["exactly_one_action"]
                    and v5_branch["exactly_one_action"]
                ),
                "exit_seen_false_both": (
                    not v4_branch["successor_exit_seen"]
                    and not v5_branch["successor_exit_seen"]
                ),
            }
            for key, passed in successor_checks.items():
                integrity["successor_identity"][key] += int(passed)

            expected_draw = exp["replacement_draw"]
            if expected_draw is not None and v5_branch["drawn_card_id"] != expected_draw:
                integrity["successor_identity"]["mismatches"].append({
                    "transition_id": tid,
                    "replacement_draw": {
                        "expected": expected_draw,
                        "actual": v5_branch["drawn_card_id"],
                    },
                })
            expected_hand = exp["successor_hand"]
            if expected_hand is not None and v5_branch["successor_hand"] != expected_hand:
                integrity["successor_identity"]["mismatches"].append({
                    "transition_id": tid,
                    "successor_hand": {
                        "expected": expected_hand,
                        "actual": v5_branch["successor_hand"],
                    },
                })
            if v4_branch["drawn_card_id"] == "exit" or v5_branch["drawn_card_id"] == "exit":
                integrity["successor_identity"]["mismatches"].append({
                    "transition_id": tid,
                    "unexpected_exit_draw": True,
                })

            v4m = v4_branch["opportunity_metrics"]
            v5m = v5_branch["opportunity_metrics"]
            debts = {
                "max_gain_debt": v4m["max_one_step_closure_gain"] - v5m["max_one_step_closure_gain"],
                "improving_move_count_debt": v4m["closure_improving_placement_count"] - v5m["closure_improving_placement_count"],
                "capable_card_count_debt": v4m["closure_capable_card_count"] - v5m["closure_capable_card_count"],
            }
            primary_results.append({
                "transition_id": tid,
                "seed": seed,
                "worker14_immediate_primary_class": exp["w14_class"],
                "worker13_final_outcome_category": exp["outcome"],
                "pre_action_draw_pile_count": obs["draw_pile_count"],
                "pre_action_draw_pile_sha256": obs["draw_pile_sha256"],
                "pre_action_draw_top_card_id": obs["draw_pile_top_card_id"],
                "consumed_card_id": v4_card,
                "hand_index": v4_move.hand_index,
                "replacement_draw_card_id": v4_branch["drawn_card_id"],
                "successor_hand": v4_branch["successor_hand"],
                "v4_successor": v4m,
                "v5_successor": v5m,
                "debts": debts,
                "primary_class": primary_class(debts),
            })
        else:
            control_result = {
                "transition_id": tid,
                "seed": seed,
                "worker14_immediate_primary_class": exp["w14_class"],
                "v4_consumed_card": v4_card,
                "v5_consumed_card": v5_card,
                "v4_hand_index": v4_move.hand_index,
                "v5_hand_index": v5_move.hand_index,
                "replacement_draw_v4": v4_branch["drawn_card_id"],
                "replacement_draw_v5": v5_branch["drawn_card_id"],
                "v4_successor_hand": v4_branch["successor_hand"],
                "v5_successor_hand": v5_branch["successor_hand"],
                "successor_hands_identical": v4_branch["successor_hand"] == v5_branch["successor_hand"],
                "v4_closure_reserve": {
                    key: v4_branch["opportunity_metrics"][key]
                    for key in (
                        "max_one_step_closure_gain",
                        "closure_improving_placement_count",
                        "closure_capable_card_count",
                    )
                },
                "v5_closure_reserve": {
                    key: v5_branch["opportunity_metrics"][key]
                    for key in (
                        "max_one_step_closure_gain",
                        "closure_improving_placement_count",
                        "closure_capable_card_count",
                    )
                },
                "topology_isolated": False,
                "excluded_from_primary_gates": True,
            }

    integrity["primary_six_card_identity"]["passed"] = (
        integrity["primary_six_card_identity"]["same_consumed_card_id"] == 6
        and integrity["primary_six_card_identity"]["same_hand_index"] == 6
        and integrity["primary_six_card_identity"]["both_place"] == 6
    )
    integrity["successor_identity"]["passed"] = (
        integrity["successor_identity"]["same_drawn_card_id"] == 6
        and integrity["successor_identity"]["same_successor_hand"] == 6
        and integrity["successor_identity"]["same_post_draw_pile"] == 6
        and integrity["successor_identity"]["exactly_one_draw_each"] == 6
        and integrity["successor_identity"]["exactly_one_action_each"] == 6
        and integrity["successor_identity"]["exit_seen_false_both"] == 6
        and not integrity["successor_identity"]["mismatches"]
    )

    integrity_passed = all(section["passed"] for section in integrity.values())

    payload = {
        "schema": "bandido-alcatraz-v5-mixed-case-next-hand-closure-reserve-audit",
        "schema_version": 1,
        "experiment_id": "worker-15-v5-mixed-case-next-hand-closure-reserve-audit",
        "date": "2026-09-25",
        "dataset_status": "already-spent / selected / development / diagnostic / non-confirmatory",
        "authoritative_orchestrator_decision_url": DECISION_URL,
        "starting_main": STARTING_MAIN,
        "evaluated_commit": os.environ.get("EVALUATED_COMMIT") or os.environ.get("GITHUB_SHA"),
        "workflow_run": {
            "run_id": int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None,
            "url": f"https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/{os.environ.get('GITHUB_RUN_ID')}",
        },
        "runner": os.environ.get("RUNNER_NAME"),
        "seed_scope": REPLAY_SEEDS,
        "primary_transition_ids": PRIMARY_IDS,
        "control_transition_id": CONTROL_ID,
        "fresh_seeds_used": False,
        "holdout_used": False,
        "integrity": integrity,
        "integrity_passed": integrity_passed,
        "pre_action_states": observed,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not integrity_passed:
        payload["primary_results"] = primary_results
        payload["control_result"] = control_result
        output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        print("WORKER15_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
        raise SystemExit("Worker #15 integrity gate failed; no mechanism interpretation")

    counts = {
        "strict_next_hand_closure_reserve_debt": 0,
        "next_hand_closure_reserve_tradeoff": 0,
        "next_hand_closure_reserve_equal": 0,
        "next_hand_closure_reserve_improvement": 0,
    }
    for record in primary_results:
        counts[record["primary_class"]] += 1

    equal_ids = {
        "2024:a14:s13",
        "2098:a17:s16",
        "2238:a20:s19",
        "2372:a13:s12",
    }
    improvement_ids = {
        "2168:a26:s25",
        "2372:a22:s21",
    }
    equal_records = [r for r in primary_results if r["transition_id"] in equal_ids]
    improvement_records = [r for r in primary_results if r["transition_id"] in improvement_ids]
    equal_strict = sum(
        r["primary_class"] == "strict_next_hand_closure_reserve_debt"
        for r in equal_records
    )
    strict_total = counts["strict_next_hand_closure_reserve_debt"]
    case2238 = next(r for r in primary_results if r["transition_id"] == "2238:a20:s19")

    if (
        strict_total >= 4
        and equal_strict >= 3
        and case2238["primary_class"] == "strict_next_hand_closure_reserve_debt"
    ):
        classification = "v5_mixed_case_next_hand_closure_debt_supported"
    elif (
        strict_total <= 2
        or equal_strict <= 1
        or case2238["primary_class"] == "next_hand_closure_reserve_improvement"
    ):
        classification = "v5_mixed_case_next_hand_closure_debt_not_supported"
    else:
        classification = "v5_mixed_case_next_hand_closure_debt_ambiguous"

    payload.update({
        "primary_results": primary_results,
        "control_result": control_result,
        "primary_summary": {
            **counts,
            "total": 6,
            "strict_debt_among_worker14_immediate_equal": equal_strict,
            "worker14_immediate_equal_total": 4,
        },
        "worker14_immediate_equal_cases": equal_records,
        "worker14_immediate_improvement_cases": improvement_records,
        "seed_2238": case2238,
        "final_preregistered_classification": classification,
        "interpretation_limit": "Selected already-spent diagnostic data only; one-action plus one canonical replacement draw, then opportunity enumeration only. No second gameplay action or confirmatory claim.",
    })

    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print("WORKER15_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
    print("WORKER15_RESULT=" + json.dumps({
        "primary_summary": payload["primary_summary"],
        "primary_results": [
            {
                "transition_id": r["transition_id"],
                "replacement_draw_card_id": r["replacement_draw_card_id"],
                "successor_hand": r["successor_hand"],
                "v4_reserve": {
                    "max_one_step_closure_gain": r["v4_successor"]["max_one_step_closure_gain"],
                    "closure_improving_placement_count": r["v4_successor"]["closure_improving_placement_count"],
                    "closure_capable_card_count": r["v4_successor"]["closure_capable_card_count"],
                },
                "v5_reserve": {
                    "max_one_step_closure_gain": r["v5_successor"]["max_one_step_closure_gain"],
                    "closure_improving_placement_count": r["v5_successor"]["closure_improving_placement_count"],
                    "closure_capable_card_count": r["v5_successor"]["closure_capable_card_count"],
                },
                "debts": r["debts"],
                "primary_class": r["primary_class"],
            }
            for r in primary_results
        ],
        "control_result": control_result,
        "classification": classification,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
