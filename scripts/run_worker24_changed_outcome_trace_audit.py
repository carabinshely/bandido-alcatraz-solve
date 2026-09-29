from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
from random import Random
from statistics import mean, median
import traceback

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import (
    BoundedMergeV4Policy,
    VisibleHandTwoActionV6Policy,
)
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import (
    MoveFeatures,
    _bounded_merge_bank,
    move_features,
    move_features_no_draw,
    preview_move_without_draw,
    score_features,
    two_action_sequence_score,
)


ROOT = Path(__file__).parents[1]
WORKER23_RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v6"
    / "current-model-spent-development-1000-1099-2026-09-28.json"
)
RAW_OUTPUT = ROOT / "artifacts" / "worker24-changed-outcome-trace-audit.json"
SUMMARY_OUTPUT = ROOT / "artifacts" / "worker24-changed-outcome-trace-summary.json"

PREREGISTRATION_URL = (
    "https://github.com/carabinshely/bandido-alcatraz-solve/"
    "issues/2#issuecomment-5897161086"
)
STARTING_MAIN = "89559d71d8b59e5c794510ea7481331c63803a8e"
WATER_FIX_COMMIT = "87b8d3eeff3aaf53c5e887679360652a3f9e8d04"
MAX_STEPS = 1000
TRACE_WORKERS = 4

SEEDS = (
    1001,
    1009,
    1012,
    1013,
    1014,
    1015,
    1018,
    1021,
    1023,
    1024,
    1030,
    1039,
    1040,
    1045,
    1046,
    1047,
    1049,
    1050,
    1055,
    1066,
    1068,
    1071,
    1072,
    1075,
    1080,
    1081,
    1083,
    1084,
    1087,
    1091,
    1092,
    1098,
)

V4_WIN_TO_V6_LOSS = (1012, 1087)
V6_ONLY_WINS = (1024, 1083)
DECK_TO_NO_LEGAL = (
    1001,
    1015,
    1023,
    1039,
    1040,
    1045,
    1046,
    1047,
    1055,
    1071,
    1080,
    1084,
    1091,
    1098,
)
NO_LEGAL_TO_DECK = (
    1009,
    1013,
    1030,
    1049,
    1066,
    1068,
    1072,
    1075,
    1081,
    1092,
)
OTHER_FAILURE_SWITCH = (1014, 1018, 1021, 1050)

EXPECTED_TRANSITIONS = {
    1001: ("deck_exhausted", "no_legal_move"),
    1009: ("no_legal_move", "deck_exhausted"),
    1012: ("win", "deck_exhausted"),
    1013: ("no_legal_move", "deck_exhausted"),
    1014: ("closed_tunnels_conditions_failed", "no_legal_move"),
    1015: ("deck_exhausted", "no_legal_move"),
    1018: ("closed_tunnels_conditions_failed", "deck_exhausted"),
    1021: ("no_legal_move", "closed_tunnels_conditions_failed"),
    1023: ("deck_exhausted", "no_legal_move"),
    1024: ("deck_exhausted", "win"),
    1030: ("no_legal_move", "deck_exhausted"),
    1039: ("deck_exhausted", "no_legal_move"),
    1040: ("deck_exhausted", "no_legal_move"),
    1045: ("deck_exhausted", "no_legal_move"),
    1046: ("deck_exhausted", "no_legal_move"),
    1047: ("deck_exhausted", "no_legal_move"),
    1049: ("no_legal_move", "deck_exhausted"),
    1050: ("deck_exhausted", "closed_tunnels_conditions_failed"),
    1055: ("deck_exhausted", "no_legal_move"),
    1066: ("no_legal_move", "deck_exhausted"),
    1068: ("no_legal_move", "deck_exhausted"),
    1071: ("deck_exhausted", "no_legal_move"),
    1072: ("no_legal_move", "deck_exhausted"),
    1075: ("no_legal_move", "deck_exhausted"),
    1080: ("deck_exhausted", "no_legal_move"),
    1081: ("no_legal_move", "deck_exhausted"),
    1083: ("no_legal_move", "win"),
    1084: ("deck_exhausted", "no_legal_move"),
    1087: ("win", "deck_exhausted"),
    1091: ("deck_exhausted", "no_legal_move"),
    1092: ("no_legal_move", "deck_exhausted"),
    1098: ("deck_exhausted", "no_legal_move"),
}

FINAL_RECORD_FIELDS = (
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

FEATURE_FIELDS = tuple(MoveFeatures.__dataclass_fields__)
MILESTONE_FIELDS = (
    "first_equipment_ready_turn",
    "first_water_clear_turn_including_initial",
    "first_water_clear_after_visible_turn",
    "first_open_tunnels_le_10_turn_including_initial",
    "first_open_tunnels_le_5_turn_including_initial",
    "first_return_open_tunnels_le_10_after_above_turn",
    "first_return_open_tunnels_le_5_after_above_turn",
    "first_exit_seen_turn",
    "first_legal_exit_placement_turn",
    "exit_placed_turn",
    "refresh_count",
    "terminal_turn",
)


class TraceIntegrityError(RuntimeError):
    pass


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def board_cells_record(state: GameState) -> list[dict[str, object]]:
    return [
        {
            "x": x,
            "y": y,
            "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
            "water": cell.water,
        }
        for (x, y), cell in sorted(state.board.cells.items())
    ]


def visible_state_record(state: GameState) -> dict[str, object]:
    cells = board_cells_record(state)
    return {
        "board_fingerprint_sha256": sha256_text(canonical_json(cells)),
        "board_cells": cells,
        "visible_hand_card_ids": [card.card_id for card in state.hand],
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "exit_placed": state.exit_placed,
        "exit_seen": state.exit_seen,
        "turns": state.turns,
        "set_aside_unplayable": state.set_aside_unplayable,
        "open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "merge_opportunities": state.board.merge_opportunities,
        "bounded_merge_bank": _bounded_merge_bank(state.board),
        "water_obstruction": state.board.water_obstruction,
        "trapped_water": state.board.trapped_water_cells,
    }


def visible_state_digest(state: GameState) -> str:
    return sha256_text(canonical_json(visible_state_record(state)))


def rng_digest(rng: Random) -> str:
    return sha256_text(repr(rng.getstate()))


def move_record(state: GameState, move: Move) -> dict[str, object]:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "hand_index": move.hand_index,
        "card_id": card.card_id,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def move_key(state: GameState, move: Move) -> tuple[object, ...]:
    item = move_record(state, move)
    origin = tuple(item["origin"]) if item["origin"] is not None else None
    return (
        item["action"],
        item["hand_index"],
        item["card_id"],
        origin,
        item["quarter_turns"],
    )


def features_record(features: MoveFeatures, weights) -> dict[str, object]:
    raw = asdict(features)
    weighted = {
        field: raw[field] * getattr(weights, field)
        for field in FEATURE_FIELDS
    }
    return {
        "features": raw,
        "weighted_contributions": weighted,
        "score": sum(weighted.values()),
    }


def first_step_result_record(state: GameState) -> dict[str, object]:
    return {
        "visible_hand_card_ids": [card.card_id for card in state.hand],
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "equipment_ready": is_equipment_ready(state.raincoats, state.ropes),
        "exit_placed": state.exit_placed,
        "exit_seen": state.exit_seen,
        "open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "merge_opportunities": state.board.merge_opportunities,
        "bounded_merge_bank": _bounded_merge_bank(state.board),
        "water_obstruction": state.board.water_obstruction,
        "trapped_water": state.board.trapped_water_cells,
        "won": state.won,
    }


def analyze_first_move(
    state: GameState,
    move: Move,
    weights,
) -> dict[str, object]:
    immediate_features = move_features_no_draw(state, move)
    immediate = features_record(immediate_features, weights)
    preview = preview_move_without_draw(state, move)
    successor = preview.successor

    terminal_after_first = None
    if successor.won:
        terminal_after_first = "win"
    elif successor.board.open_tunnels == 0:
        terminal_after_first = "closed_tunnels_conditions_failed"

    second_rows: list[dict[str, object]] = []
    best_second_score = 0
    if terminal_after_first is None:
        for second_move in successor.legal_moves():
            second_features = move_features_no_draw(successor, second_move)
            second_feature_record = features_record(second_features, weights)
            second_rows.append(
                {
                    "move": move_record(successor, second_move),
                    "features": second_feature_record["features"],
                    "weighted_contributions": second_feature_record[
                        "weighted_contributions"
                    ],
                    "score": second_feature_record["score"],
                }
            )
        if second_rows:
            best_second_score = max(row["score"] for row in second_rows)

    best_second_moves = [
        row for row in second_rows if row["score"] == best_second_score
    ] if second_rows else []

    return {
        "move": move_record(state, move),
        "immediate_features": immediate["features"],
        "immediate_weighted_contributions": immediate["weighted_contributions"],
        "score1": immediate["score"],
        "terminal_after_first": terminal_after_first,
        "first_step_result": first_step_result_record(successor),
        "best_score2": best_second_score,
        "best_second_moves": best_second_moves,
        "sequence_score": immediate["score"] + best_second_score,
    }


def deterministic_tiers(
    state: GameState,
    weights,
    audit: dict[str, int],
) -> dict[str, object]:
    legal = state.legal_moves()
    if not legal:
        raise TraceIntegrityError("tier analysis requires legal moves")

    rows = []
    for move in legal:
        production_features = move_features(state, move)
        no_draw_features = move_features_no_draw(state, move)
        audit["v4_no_draw_feature_equivalence_checks"] += 1
        if production_features != no_draw_features:
            audit["v4_no_draw_feature_equivalence_failures"] += 1
            raise TraceIntegrityError(
                "V4 production/no-draw feature mismatch at visible shared state"
            )

        immediate_score = score_features(production_features, weights)
        sequence_score = two_action_sequence_score(state, move, weights)
        rows.append(
            {
                "move_object": move,
                "move": move_record(state, move),
                "key": move_key(state, move),
                "immediate_v4_score": immediate_score,
                "v6_sequence_score": sequence_score,
                "second_step_component": sequence_score - immediate_score,
            }
        )

    v4_max = max(row["immediate_v4_score"] for row in rows)
    v6_max = max(row["v6_sequence_score"] for row in rows)
    v4_tier_rows = [
        row for row in rows if row["immediate_v4_score"] == v4_max
    ]
    v6_tier_rows = [
        row for row in rows if row["v6_sequence_score"] == v6_max
    ]

    return {
        "rows": rows,
        "v4_max": v4_max,
        "v6_max": v6_max,
        "v4_tier_rows": v4_tier_rows,
        "v6_tier_rows": v6_tier_rows,
    }


def tier_rows_public(tiers: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "move": row["move"],
            "immediate_v4_score": row["immediate_v4_score"],
            "v6_sequence_score": row["v6_sequence_score"],
            "second_step_component": row["second_step_component"],
        }
        for row in tiers["rows"]
    ]


def tier_move_records(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row["move"] for row in rows]


def tier_keys(rows: list[dict[str, object]]) -> tuple[tuple[object, ...], ...]:
    return tuple(row["key"] for row in rows)


def tier_label(tiers: dict[str, object]) -> str:
    v4 = set(tier_keys(tiers["v4_tier_rows"]))
    v6 = set(tier_keys(tiers["v6_tier_rows"]))
    if v4 == v6:
        raise TraceIntegrityError("tier_label called for equal tiers")

    outside = v6 - v4
    retained = v6 & v4

    if outside and retained:
        return "tier_expansion"

    if not outside and v6:
        return "lookahead_tiebreak"

    if outside and not retained:
        row_map = {row["key"]: row for row in tiers["rows"]}
        if all(
            row_map[key]["immediate_v4_score"] < tiers["v4_max"]
            and row_map[key]["v6_sequence_score"] == tiers["v6_max"]
            for key in outside
        ):
            return "lookahead_override"

    return "other_semantic_difference"


def target_decompositions(
    state: GameState,
    tiers: dict[str, object],
    selected_v4: Move,
    weights,
) -> list[dict[str, object]]:
    selected_key = move_key(state, selected_v4)
    v6_keys = set(tier_keys(tiers["v6_tier_rows"]))
    targets = {selected_key, *v6_keys}

    out: list[dict[str, object]] = []
    for row in tiers["rows"]:
        if row["key"] not in targets:
            continue
        roles: list[str] = []
        if row["key"] == selected_key:
            roles.append("v4_selected")
        if row["key"] in v6_keys:
            roles.append("v6_preferred")
        analysis = analyze_first_move(state, row["move_object"], weights)
        if analysis["score1"] != row["immediate_v4_score"]:
            raise TraceIntegrityError("first-step score decomposition mismatch")
        if analysis["sequence_score"] != row["v6_sequence_score"]:
            raise TraceIntegrityError("two-action score decomposition mismatch")
        analysis["roles"] = roles
        out.append(analysis)
    return out


def selected_immediate_comparison(
    state: GameState,
    selected_v4: Move,
    selected_v6: Move,
) -> dict[str, object]:
    v4_next = preview_move_without_draw(state, selected_v4).successor
    v6_next = preview_move_without_draw(state, selected_v6).successor
    v4 = first_step_result_record(v4_next)
    v6 = first_step_result_record(v6_next)
    return {
        "v4": v4,
        "v6": v6,
        "v6_minus_v4": {
            "open_tunnels": v6["open_tunnels"] - v4["open_tunnels"],
            "visible_water": v6["visible_water"] - v4["visible_water"],
            "water_obstruction": (
                v6["water_obstruction"] - v4["water_obstruction"]
            ),
            "trapped_water": v6["trapped_water"] - v4["trapped_water"],
            "bounded_merge_bank": (
                v6["bounded_merge_bank"] - v4["bounded_merge_bank"]
            ),
            "raincoats": v6["raincoats"] - v4["raincoats"],
            "ropes": v6["ropes"] - v4["ropes"],
        },
    }


def first_tier_event_record(
    *,
    seed: int,
    decision_index: int,
    loop_iteration: int,
    state: GameState,
    tiers: dict[str, object],
    selected_v4: Move,
    selected_v6: Move,
    weights,
    rng_before_v4: str,
    rng_before_v6: str,
    rng_after_v4: str,
    rng_after_v6: str,
) -> dict[str, object]:
    return {
        "seed": seed,
        "decision_index": decision_index,
        "loop_iteration": loop_iteration,
        "turn_index": state.turns,
        "state": visible_state_record(state),
        "v4_max_score": tiers["v4_max"],
        "v6_max_sequence_score": tiers["v6_max"],
        "v4_max_tier": tier_move_records(tiers["v4_tier_rows"]),
        "v6_best_first_tier": tier_move_records(tiers["v6_tier_rows"]),
        "all_legal_first_move_scores": tier_rows_public(tiers),
        "label": tier_label(tiers),
        "v4_selected_move": move_record(state, selected_v4),
        "v6_selected_move_at_this_state": move_record(state, selected_v6),
        "target_decompositions": target_decompositions(
            state,
            tiers,
            selected_v4,
            weights,
        ),
        "rng_state_digest_before": {
            "v4": rng_before_v4,
            "v6": rng_before_v6,
            "equal": rng_before_v4 == rng_before_v6,
        },
        "rng_state_digest_after": {
            "v4": rng_after_v4,
            "v6": rng_after_v6,
            "equal": rng_after_v4 == rng_after_v6,
        },
    }


def selected_divergence_event_record(
    *,
    seed: int,
    decision_index: int,
    loop_iteration: int,
    state: GameState,
    tiers: dict[str, object],
    selected_v4: Move,
    selected_v6: Move,
    first_tier_decision_index: int | None,
    rng_before_v4: str,
    rng_before_v6: str,
    rng_after_v4: str,
    rng_after_v6: str,
) -> dict[str, object]:
    tier_equal = (
        tier_keys(tiers["v4_tier_rows"]) == tier_keys(tiers["v6_tier_rows"])
    )
    return {
        "seed": seed,
        "decision_index": decision_index,
        "loop_iteration": loop_iteration,
        "turn_index": state.turns,
        "state": visible_state_record(state),
        "selected_move_v4": move_record(state, selected_v4),
        "selected_move_v6": move_record(state, selected_v6),
        "tier_sets_differ_here": not tier_equal,
        "v4_max_tier": tier_move_records(tiers["v4_tier_rows"]),
        "v6_best_first_tier": tier_move_records(tiers["v6_tier_rows"]),
        "v4_max_score": tiers["v4_max"],
        "v6_max_sequence_score": tiers["v6_max"],
        "earlier_first_tier_divergence_decision_index": first_tier_decision_index,
        "selected_divergence_at_first_tier_divergence": (
            first_tier_decision_index == decision_index
        ),
        "rng_state_digest_before": {
            "v4": rng_before_v4,
            "v6": rng_before_v6,
            "equal": rng_before_v4 == rng_before_v6,
        },
        "rng_state_digest_after": {
            "v4": rng_after_v4,
            "v6": rng_after_v6,
            "equal": rng_after_v4 == rng_after_v6,
        },
        "immediate_no_draw_post_action_comparison": selected_immediate_comparison(
            state,
            selected_v4,
            selected_v6,
        ),
    }


def new_milestones() -> dict[str, object]:
    return {
        "first_equipment_ready_turn": None,
        "first_water_clear_turn_including_initial": None,
        "first_visible_water_turn": None,
        "first_water_clear_after_visible_turn": None,
        "first_open_tunnels_le_10_turn_including_initial": None,
        "first_open_tunnels_le_5_turn_including_initial": None,
        "first_open_tunnels_above_10_turn": None,
        "first_open_tunnels_above_5_turn": None,
        "first_return_open_tunnels_le_10_after_above_turn": None,
        "first_return_open_tunnels_le_5_after_above_turn": None,
        "first_exit_seen_turn": None,
        "first_legal_exit_placement_turn": None,
        "exit_placed_turn": None,
        "refresh_count": 0,
        "terminal_turn": None,
        "terminal_outcome": None,
        "_water_seen": False,
        "_open_above_10_seen": False,
        "_open_above_5_seen": False,
    }


def observe_milestones(state: GameState, milestones: dict[str, object]) -> None:
    turn = state.turns

    if (
        milestones["first_equipment_ready_turn"] is None
        and is_equipment_ready(state.raincoats, state.ropes)
    ):
        milestones["first_equipment_ready_turn"] = turn

    if state.board.visible_water_cells == 0:
        if milestones["first_water_clear_turn_including_initial"] is None:
            milestones["first_water_clear_turn_including_initial"] = turn
        if (
            milestones["_water_seen"]
            and milestones["first_water_clear_after_visible_turn"] is None
        ):
            milestones["first_water_clear_after_visible_turn"] = turn
    else:
        milestones["_water_seen"] = True
        if milestones["first_visible_water_turn"] is None:
            milestones["first_visible_water_turn"] = turn

    open_tunnels = state.board.open_tunnels
    if (
        open_tunnels <= 10
        and milestones["first_open_tunnels_le_10_turn_including_initial"] is None
    ):
        milestones["first_open_tunnels_le_10_turn_including_initial"] = turn
    if (
        open_tunnels <= 5
        and milestones["first_open_tunnels_le_5_turn_including_initial"] is None
    ):
        milestones["first_open_tunnels_le_5_turn_including_initial"] = turn

    if open_tunnels > 10:
        milestones["_open_above_10_seen"] = True
        if milestones["first_open_tunnels_above_10_turn"] is None:
            milestones["first_open_tunnels_above_10_turn"] = turn
    elif (
        milestones["_open_above_10_seen"]
        and milestones["first_return_open_tunnels_le_10_after_above_turn"] is None
    ):
        milestones["first_return_open_tunnels_le_10_after_above_turn"] = turn

    if open_tunnels > 5:
        milestones["_open_above_5_seen"] = True
        if milestones["first_open_tunnels_above_5_turn"] is None:
            milestones["first_open_tunnels_above_5_turn"] = turn
    elif (
        milestones["_open_above_5_seen"]
        and milestones["first_return_open_tunnels_le_5_after_above_turn"] is None
    ):
        milestones["first_return_open_tunnels_le_5_after_above_turn"] = turn

    if state.exit_seen and milestones["first_exit_seen_turn"] is None:
        milestones["first_exit_seen_turn"] = turn

    if state.exit_placed and milestones["exit_placed_turn"] is None:
        milestones["exit_placed_turn"] = turn

    if (
        milestones["first_legal_exit_placement_turn"] is None
        and any(card.is_exit for card in state.hand)
    ):
        if any(
            move.action is Action.PLACE
            and state.hand[move.hand_index].is_exit
            for move in state.legal_moves()
        ):
            milestones["first_legal_exit_placement_turn"] = turn


def finish_milestones(
    milestones: dict[str, object],
    state: GameState,
    reason: str,
) -> dict[str, object]:
    milestones["terminal_turn"] = state.turns
    milestones["terminal_outcome"] = reason
    return {
        key: value
        for key, value in milestones.items()
        if not key.startswith("_")
    }


def final_record(state: GameState, reason: str) -> dict[str, object]:
    equipment_ready = is_equipment_ready(state.raincoats, state.ropes)
    return {
        "won": state.won,
        "reason": reason,
        "turns": state.turns,
        "final_open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "equipment_ready": equipment_ready,
        "exit_placed": state.exit_placed,
        "exit_equipment_water_ready": (
            state.exit_placed
            and state.board.visible_water_cells == 0
            and equipment_ready
        ),
    }


def pre_choice_terminal_reason(state: GameState) -> str | None:
    if state.won:
        return "win"
    if state.board.open_tunnels == 0:
        return "closed_tunnels_conditions_failed"
    if not state.hand and not state.draw_pile:
        return "deck_exhausted"
    return None


def finish_game(
    *,
    state: GameState,
    rng: Random,
    policy,
    milestones: dict[str, object],
    iterations_used: int,
) -> tuple[dict[str, object], dict[str, object]]:
    for _ in range(iterations_used, MAX_STEPS):
        reason = pre_choice_terminal_reason(state)
        if reason is not None:
            return final_record(state, reason), finish_milestones(
                milestones, state, reason
            )

        move = policy.choose(state, rng)
        if move is None:
            if state.refresh_unplayable_hand():
                milestones["refresh_count"] += 1
                observe_milestones(state, milestones)
                continue
            reason = "deck_exhausted" if state.exhausted else "no_legal_move"
            return final_record(state, reason), finish_milestones(
                milestones, state, reason
            )

        state.apply(move)
        observe_milestones(state, milestones)

    return final_record(state, "step_limit"), finish_milestones(
        milestones, state, "step_limit"
    )


def transition_category(record: dict[str, object]) -> str:
    return "win" if record["won"] else str(record["reason"])


def trace_seed(seed: int) -> dict[str, object]:
    deck = load_real_deck(ROOT / "data")
    v4_policy = BoundedMergeV4Policy(setup_weight=250)
    v6_policy = VisibleHandTwoActionV6Policy()
    weights = v4_policy.weights

    rng_v4 = Random(seed)
    rng_v6 = Random(seed)
    state_v4 = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng_v4,
    )
    state_v6 = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng_v6,
    )

    milestones_v4 = new_milestones()
    milestones_v6 = new_milestones()
    observe_milestones(state_v4, milestones_v4)
    observe_milestones(state_v6, milestones_v6)

    audit = {
        "v4_no_draw_feature_equivalence_checks": 0,
        "v4_no_draw_feature_equivalence_failures": 0,
    }
    prefix_records: list[dict[str, object]] = []
    first_tier_divergence = None
    first_selected_divergence = None
    decision_index = 0
    final_v4 = final_v6 = None
    final_milestones_v4 = final_milestones_v6 = None

    for loop_iteration in range(MAX_STEPS):
        digest_v4 = visible_state_digest(state_v4)
        digest_v6 = visible_state_digest(state_v6)
        if digest_v4 != digest_v6:
            raise TraceIntegrityError(
                f"visible states diverged before selected move at seed {seed}"
            )

        reason_v4 = pre_choice_terminal_reason(state_v4)
        reason_v6 = pre_choice_terminal_reason(state_v6)
        if reason_v4 is not None or reason_v6 is not None:
            if reason_v4 != reason_v6:
                raise TraceIntegrityError(
                    "shared visible state produced different terminal reasons"
                )
            reason = reason_v4
            assert reason is not None
            final_v4 = final_record(state_v4, reason)
            final_v6 = final_record(state_v6, reason)
            final_milestones_v4 = finish_milestones(
                milestones_v4, state_v4, reason
            )
            final_milestones_v6 = finish_milestones(
                milestones_v6, state_v6, reason
            )
            break

        legal_v4 = state_v4.legal_moves()
        legal_v6 = state_v6.legal_moves()
        if bool(legal_v4) != bool(legal_v6):
            raise TraceIntegrityError("shared visible state legal-move mismatch")

        if not legal_v4:
            refreshed_v4 = state_v4.refresh_unplayable_hand()
            refreshed_v6 = state_v6.refresh_unplayable_hand()
            if refreshed_v4 != refreshed_v6:
                raise TraceIntegrityError("shared refresh result mismatch")
            if refreshed_v4:
                milestones_v4["refresh_count"] += 1
                milestones_v6["refresh_count"] += 1
                observe_milestones(state_v4, milestones_v4)
                observe_milestones(state_v6, milestones_v6)
                continue

            reason_v4 = (
                "deck_exhausted" if state_v4.exhausted else "no_legal_move"
            )
            reason_v6 = (
                "deck_exhausted" if state_v6.exhausted else "no_legal_move"
            )
            if reason_v4 != reason_v6:
                raise TraceIntegrityError("shared no-move terminal mismatch")
            final_v4 = final_record(state_v4, reason_v4)
            final_v6 = final_record(state_v6, reason_v6)
            final_milestones_v4 = finish_milestones(
                milestones_v4, state_v4, reason_v4
            )
            final_milestones_v6 = finish_milestones(
                milestones_v6, state_v6, reason_v6
            )
            break

        tiers = None
        if first_tier_divergence is None:
            tiers = deterministic_tiers(state_v4, weights, audit)

        rng_before_v4 = rng_digest(rng_v4)
        rng_before_v6 = rng_digest(rng_v6)
        selected_v4 = v4_policy.choose(state_v4, rng_v4)
        selected_v6 = v6_policy.choose(state_v6, rng_v6)
        if selected_v4 is None or selected_v6 is None:
            raise TraceIntegrityError("policy returned None with legal moves")
        rng_after_v4 = rng_digest(rng_v4)
        rng_after_v6 = rng_digest(rng_v6)

        selected_equal = move_key(state_v4, selected_v4) == move_key(
            state_v6, selected_v6
        )

        if tiers is not None:
            v4_tier_keys = set(tier_keys(tiers["v4_tier_rows"]))
            v6_tier_keys = set(tier_keys(tiers["v6_tier_rows"]))
            if move_key(state_v4, selected_v4) not in v4_tier_keys:
                raise TraceIntegrityError("actual V4 selected outside V4 tier")
            if move_key(state_v6, selected_v6) not in v6_tier_keys:
                raise TraceIntegrityError("actual V6 selected outside V6 tier")
            tier_equal = v4_tier_keys == v6_tier_keys
        else:
            tier_equal = None

        prefix_row = {
            "decision_index": decision_index,
            "loop_iteration": loop_iteration,
            "turn_index": state_v4.turns,
            "visible_state_digest": digest_v4,
            "tier_analysis_performed": tiers is not None,
            "tier_equal": tier_equal,
            "selected_move_v4": move_record(state_v4, selected_v4),
            "selected_move_v6": move_record(state_v6, selected_v6),
            "selected_equal": selected_equal,
            "rng_before_equal": rng_before_v4 == rng_before_v6,
            "rng_after_equal": rng_after_v4 == rng_after_v6,
        }
        if tiers is not None:
            prefix_row["v4_max_tier"] = tier_move_records(
                tiers["v4_tier_rows"]
            )
            prefix_row["v6_best_first_tier"] = tier_move_records(
                tiers["v6_tier_rows"]
            )
        prefix_records.append(prefix_row)

        if (
            tiers is not None
            and not tier_equal
            and first_tier_divergence is None
        ):
            first_tier_divergence = first_tier_event_record(
                seed=seed,
                decision_index=decision_index,
                loop_iteration=loop_iteration,
                state=state_v4,
                tiers=tiers,
                selected_v4=selected_v4,
                selected_v6=selected_v6,
                weights=weights,
                rng_before_v4=rng_before_v4,
                rng_before_v6=rng_before_v6,
                rng_after_v4=rng_after_v4,
                rng_after_v6=rng_after_v6,
            )

        if not selected_equal:
            if tiers is None:
                tiers = deterministic_tiers(state_v4, weights, audit)
                v4_tier_keys = set(tier_keys(tiers["v4_tier_rows"]))
                v6_tier_keys = set(tier_keys(tiers["v6_tier_rows"]))
                if move_key(state_v4, selected_v4) not in v4_tier_keys:
                    raise TraceIntegrityError(
                        "selected-divergence V4 outside tier"
                    )
                if move_key(state_v6, selected_v6) not in v6_tier_keys:
                    raise TraceIntegrityError(
                        "selected-divergence V6 outside tier"
                    )
                tier_equal = v4_tier_keys == v6_tier_keys
                prefix_records[-1]["tier_analysis_performed"] = True
                prefix_records[-1]["tier_equal"] = tier_equal
                prefix_records[-1]["v4_max_tier"] = tier_move_records(
                    tiers["v4_tier_rows"]
                )
                prefix_records[-1]["v6_best_first_tier"] = tier_move_records(
                    tiers["v6_tier_rows"]
                )

            if first_tier_divergence is None and not tier_equal:
                first_tier_divergence = first_tier_event_record(
                    seed=seed,
                    decision_index=decision_index,
                    loop_iteration=loop_iteration,
                    state=state_v4,
                    tiers=tiers,
                    selected_v4=selected_v4,
                    selected_v6=selected_v6,
                    weights=weights,
                    rng_before_v4=rng_before_v4,
                    rng_before_v6=rng_before_v6,
                    rng_after_v4=rng_after_v4,
                    rng_after_v6=rng_after_v6,
                )

            first_selected_divergence = selected_divergence_event_record(
                seed=seed,
                decision_index=decision_index,
                loop_iteration=loop_iteration,
                state=state_v4,
                tiers=tiers,
                selected_v4=selected_v4,
                selected_v6=selected_v6,
                first_tier_decision_index=(
                    first_tier_divergence["decision_index"]
                    if first_tier_divergence is not None
                    else None
                ),
                rng_before_v4=rng_before_v4,
                rng_before_v6=rng_before_v6,
                rng_after_v4=rng_after_v4,
                rng_after_v6=rng_after_v6,
            )

            state_v4.apply(selected_v4)
            state_v6.apply(selected_v6)
            observe_milestones(state_v4, milestones_v4)
            observe_milestones(state_v6, milestones_v6)

            iterations_used = loop_iteration + 1
            final_v4, final_milestones_v4 = finish_game(
                state=state_v4,
                rng=rng_v4,
                policy=v4_policy,
                milestones=milestones_v4,
                iterations_used=iterations_used,
            )
            final_v6, final_milestones_v6 = finish_game(
                state=state_v6,
                rng=rng_v6,
                policy=v6_policy,
                milestones=milestones_v6,
                iterations_used=iterations_used,
            )
            break

        state_v4.apply(selected_v4)
        state_v6.apply(selected_v6)
        observe_milestones(state_v4, milestones_v4)
        observe_milestones(state_v6, milestones_v6)
        decision_index += 1
    else:
        final_v4 = final_record(state_v4, "step_limit")
        final_v6 = final_record(state_v6, "step_limit")
        final_milestones_v4 = finish_milestones(
            milestones_v4, state_v4, "step_limit"
        )
        final_milestones_v6 = finish_milestones(
            milestones_v6, state_v6, "step_limit"
        )

    assert final_v4 is not None
    assert final_v6 is not None
    assert final_milestones_v4 is not None
    assert final_milestones_v6 is not None

    actual_transition = (
        transition_category(final_v4),
        transition_category(final_v6),
    )

    return {
        "seed": seed,
        "error": None,
        "actual_transition": list(actual_transition),
        "expected_transition": list(EXPECTED_TRANSITIONS[seed]),
        "transition_matches_expected": (
            actual_transition == EXPECTED_TRANSITIONS[seed]
        ),
        "final_records": {
            "v4": final_v4,
            "v6": final_v6,
        },
        "milestones": {
            "v4": final_milestones_v4,
            "v6": final_milestones_v6,
        },
        "first_tier_divergence": first_tier_divergence,
        "first_selected_divergence": first_selected_divergence,
        "selected_divergence_relation": (
            "same_tier_divergence_state"
            if (
                first_tier_divergence is not None
                and first_selected_divergence is not None
                and first_tier_divergence["decision_index"]
                == first_selected_divergence["decision_index"]
            )
            else "later"
            if first_tier_divergence is not None
            and first_selected_divergence is not None
            else None
        ),
        "shared_prefix_records": prefix_records,
        "audit": audit,
    }


def safe_trace_seed(seed: int) -> dict[str, object]:
    try:
        return trace_seed(seed)
    except Exception as exc:
        return {
            "seed": seed,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }


def exact_record_view(record: dict[str, object]) -> dict[str, object]:
    return {field: record[field] for field in FINAL_RECORD_FIELDS}


def integrity_report(
    traces: list[dict[str, object]],
    worker23: dict[str, object],
) -> dict[str, object]:
    expected_v4 = {
        record["seed"]: record for record in worker23["v4_per_seed"]
    }
    expected_v6 = {
        record["seed"]: record for record in worker23["v6_per_seed"]
    }

    mismatches: list[dict[str, object]] = []
    matches = 0
    transition_matches = 0

    for trace in traces:
        seed = trace["seed"]
        if trace.get("error") is not None:
            mismatches.append(
                {
                    "seed": seed,
                    "kind": "trace_error",
                    "error": trace["error"],
                }
            )
            continue

        for policy_name, expected_map in (
            ("v4", expected_v4),
            ("v6", expected_v6),
        ):
            actual = exact_record_view(trace["final_records"][policy_name])
            expected = exact_record_view(expected_map[seed])
            if actual == expected:
                matches += 1
            else:
                mismatches.append(
                    {
                        "seed": seed,
                        "kind": "final_record",
                        "policy": policy_name,
                        "expected": expected,
                        "actual": actual,
                    }
                )

        if trace["transition_matches_expected"]:
            transition_matches += 1
        else:
            mismatches.append(
                {
                    "seed": seed,
                    "kind": "transition_label",
                    "expected": trace["expected_transition"],
                    "actual": trace["actual_transition"],
                }
            )

    return {
        "final_record_exact_matches": matches,
        "final_record_expected": 64,
        "transition_label_exact_matches": transition_matches,
        "transition_label_expected": 32,
        "mismatches": mismatches,
        "passed": matches == 64 and transition_matches == 32 and not mismatches,
    }


def milestone_diff_summary(
    traces: list[dict[str, object]],
    field: str,
) -> dict[str, object]:
    both = []
    v4_only = 0
    v6_only = 0
    neither = 0
    earlier = same = later = 0
    for trace in traces:
        v4 = trace["milestones"]["v4"].get(field)
        v6 = trace["milestones"]["v6"].get(field)
        if v4 is None and v6 is None:
            neither += 1
        elif v4 is None:
            v6_only += 1
        elif v6 is None:
            v4_only += 1
        else:
            delta = v6 - v4
            both.append(delta)
            if delta < 0:
                earlier += 1
            elif delta > 0:
                later += 1
            else:
                same += 1
    return {
        "both_present": len(both),
        "v4_only_present": v4_only,
        "v6_only_present": v6_only,
        "neither_present": neither,
        "v6_earlier": earlier,
        "same_turn": same,
        "v6_later": later,
        "mean_v6_minus_v4_when_both": mean(both) if both else None,
        "deltas_when_both": both,
    }


def numeric_distribution(values: list[int]) -> dict[str, object]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": mean(values) if values else None,
        "median": median(values) if values else None,
        "histogram": dict(sorted(Counter(values).items())),
    }


def contribution_aggregate(
    traces: list[dict[str, object]],
) -> dict[str, object]:
    totals = Counter({field: 0 for field in FEATURE_FIELDS})
    nonzero = Counter({field: 0 for field in FEATURE_FIELDS})
    positive = Counter({field: 0 for field in FEATURE_FIELDS})
    negative = Counter({field: 0 for field in FEATURE_FIELDS})
    option_count = 0

    for trace in traces:
        event = trace["first_tier_divergence"]
        for analysis in event["target_decompositions"]:
            if "v6_preferred" not in analysis["roles"]:
                continue
            for second in analysis["best_second_moves"]:
                option_count += 1
                for field, value in second[
                    "weighted_contributions"
                ].items():
                    totals[field] += value
                    if value != 0:
                        nonzero[field] += 1
                    if value > 0:
                        positive[field] += 1
                    elif value < 0:
                        negative[field] += 1

    ranked = sorted(
        FEATURE_FIELDS,
        key=lambda field: (
            positive[field],
            nonzero[field],
            abs(totals[field]),
            field,
        ),
        reverse=True,
    )
    return {
        "aggregation_definition": (
            "tie-inclusive sum across every V6-preferred first move and every "
            "tied-best visible second move at each seed's first tier divergence"
        ),
        "best_second_option_count": option_count,
        "weighted_totals_by_feature": dict(totals),
        "nonzero_option_occurrences_by_feature": dict(nonzero),
        "positive_option_occurrences_by_feature": dict(positive),
        "negative_option_occurrences_by_feature": dict(negative),
        "ranked_positive_features": ranked,
    }


def immediate_effect_summary(
    traces: list[dict[str, object]],
) -> dict[str, object]:
    keys = (
        "open_tunnels",
        "visible_water",
        "water_obstruction",
        "trapped_water",
        "bounded_merge_bank",
    )
    out = {}
    for key in keys:
        less = same = greater = 0
        deltas = []
        for trace in traces:
            delta = trace["first_selected_divergence"][
                "immediate_no_draw_post_action_comparison"
            ]["v6_minus_v4"][key]
            deltas.append(delta)
            if delta < 0:
                less += 1
            elif delta > 0:
                greater += 1
            else:
                same += 1
        out[key] = {
            "v6_lower": less,
            "same": same,
            "v6_higher": greater,
            "mean_delta": mean(deltas) if deltas else None,
            "deltas": deltas,
        }
    return out


def tier_preference_effect_summary(
    traces: list[dict[str, object]],
) -> dict[str, object]:
    keys = (
        "open_tunnels",
        "visible_water",
        "water_obstruction",
        "trapped_water",
        "bounded_merge_bank",
    )
    out = {
        key: {"v6_preferred_lower": 0, "same": 0, "v6_preferred_higher": 0}
        for key in keys
    }
    comparisons = 0

    for trace in traces:
        event = trace["first_tier_divergence"]
        v4_selected = next(
            item
            for item in event["target_decompositions"]
            if "v4_selected" in item["roles"]
        )
        v4_result = v4_selected["first_step_result"]
        for item in event["target_decompositions"]:
            if "v6_preferred" not in item["roles"]:
                continue
            comparisons += 1
            v6_result = item["first_step_result"]
            for key in keys:
                delta = v6_result[key] - v4_result[key]
                if delta < 0:
                    out[key]["v6_preferred_lower"] += 1
                elif delta > 0:
                    out[key]["v6_preferred_higher"] += 1
                else:
                    out[key]["same"] += 1
    return {
        "comparison_definition": (
            "tie-inclusive comparison of every V6-preferred first move's "
            "no-draw first-step visible result against the actual V4-selected "
            "first move at the first deterministic tier divergence"
        ),
        "comparisons": comparisons,
        "metrics": out,
    }


def summarize_cohort(
    name: str,
    seeds: tuple[int, ...],
    trace_by_seed: dict[int, dict[str, object]],
) -> dict[str, object]:
    traces = [trace_by_seed[seed] for seed in seeds]
    labels = Counter(
        trace["first_tier_divergence"]["label"] for trace in traces
    )
    relation = Counter(
        trace["selected_divergence_relation"] for trace in traces
    )
    selected_tiers_differ = Counter(
        str(
            trace["first_selected_divergence"]["tier_sets_differ_here"]
        ).lower()
        for trace in traces
    )
    selected_pairs = Counter(
        (
            trace["first_selected_divergence"]["selected_move_v4"]["action"]
            + "->"
            + trace["first_selected_divergence"]["selected_move_v6"]["action"]
        )
        for trace in traces
    )
    tier_state_selected_pairs = Counter(
        (
            trace["first_tier_divergence"]["v4_selected_move"]["action"]
            + "->"
            + trace["first_tier_divergence"][
                "v6_selected_move_at_this_state"
            ]["action"]
        )
        for trace in traces
    )
    turns = [
        trace["first_tier_divergence"]["turn_index"] for trace in traces
    ]

    milestone_diffs = {
        field: milestone_diff_summary(traces, field)
        for field in MILESTONE_FIELDS
    }

    return {
        "name": name,
        "seed_count": len(seeds),
        "seeds": list(seeds),
        "divergence_label_counts": dict(labels),
        "selected_divergence_relation_counts": dict(relation),
        "selected_divergence_tier_sets_differ_counts": dict(
            selected_tiers_differ
        ),
        "action_type_pairs_at_first_selected_divergence": dict(
            selected_pairs
        ),
        "actual_selected_action_pairs_at_first_tier_divergence": dict(
            tier_state_selected_pairs
        ),
        "first_tier_divergence_turn_distribution": numeric_distribution(turns),
        "weighted_second_step_contributions": contribution_aggregate(traces),
        "milestone_differences": milestone_diffs,
        "immediate_actual_selected_divergence_effect": immediate_effect_summary(
            traces
        ),
        "first_tier_v6_preference_effect": tier_preference_effect_summary(
            traces
        ),
    }


def mechanism_signature(trace: dict[str, object]) -> dict[str, object]:
    event = trace["first_tier_divergence"]
    selected = trace["first_selected_divergence"]
    positive_features = Counter()
    for analysis in event["target_decompositions"]:
        if "v6_preferred" not in analysis["roles"]:
            continue
        for second in analysis["best_second_moves"]:
            for field, value in second["weighted_contributions"].items():
                if value > 0:
                    positive_features[field] += 1
    return {
        "label": event["label"],
        "tier_turn": event["turn_index"],
        "tier_selected_action_pair": (
            event["v4_selected_move"]["action"]
            + "->"
            + event["v6_selected_move_at_this_state"]["action"]
        ),
        "selected_divergence_action_pair": (
            selected["selected_move_v4"]["action"]
            + "->"
            + selected["selected_move_v6"]["action"]
        ),
        "selected_divergence_relation": trace[
            "selected_divergence_relation"
        ],
        "positive_second_step_features": dict(positive_features),
    }


def diagnostic_answers(
    trace_by_seed: dict[int, dict[str, object]],
    cohort_summaries: dict[str, dict[str, object]],
) -> dict[str, object]:
    all_traceable = all(
        trace["first_tier_divergence"] is not None
        and trace["first_selected_divergence"] is not None
        and trace["first_selected_divergence"]["decision_index"]
        >= trace["first_tier_divergence"]["decision_index"]
        for trace in trace_by_seed.values()
    )

    losses = {
        seed: mechanism_signature(trace_by_seed[seed])
        for seed in V4_WIN_TO_V6_LOSS
    }
    gains = {
        seed: mechanism_signature(trace_by_seed[seed])
        for seed in V6_ONLY_WINS
    }

    loss_labels = {item["label"] for item in losses.values()}
    gain_labels = {item["label"] for item in gains.values()}

    all_contrib = cohort_summaries["all_32"][
        "weighted_second_step_contributions"
    ]

    return {
        "q1_all_32_terminal_category_changes_traceable_to_deterministic_tier_divergence": (
            all_traceable
        ),
        "q2_lost_v4_wins": {
            "seeds": list(V4_WIN_TO_V6_LOSS),
            "mechanisms": losses,
            "same_first_divergence_label": len(loss_labels) == 1,
        },
        "q3_gained_v6_wins": {
            "seeds": list(V6_ONLY_WINS),
            "mechanisms": gains,
            "same_first_divergence_label": len(gain_labels) == 1,
        },
        "q4_gain_vs_loss_first_divergence_labels": {
            "loss_labels": sorted(loss_labels),
            "gain_labels": sorted(gain_labels),
            "same_label_set": loss_labels == gain_labels,
        },
        "q5_deck_exhausted_to_no_legal_move": {
            "immediate_selected_divergence_effect": cohort_summaries[
                "deck_exhausted_to_no_legal_move"
            ]["immediate_actual_selected_divergence_effect"],
            "first_tier_preference_effect": cohort_summaries[
                "deck_exhausted_to_no_legal_move"
            ]["first_tier_v6_preference_effect"],
            "milestone_differences": cohort_summaries[
                "deck_exhausted_to_no_legal_move"
            ]["milestone_differences"],
        },
        "q6_no_legal_move_to_deck_exhausted": {
            "immediate_selected_divergence_effect": cohort_summaries[
                "no_legal_move_to_deck_exhausted"
            ]["immediate_actual_selected_divergence_effect"],
            "first_tier_preference_effect": cohort_summaries[
                "no_legal_move_to_deck_exhausted"
            ]["first_tier_v6_preference_effect"],
            "milestone_differences": cohort_summaries[
                "no_legal_move_to_deck_exhausted"
            ]["milestone_differences"],
        },
        "q7_second_step_feature_contributions_most_often_positive": {
            "ranked_positive_features": all_contrib[
                "ranked_positive_features"
            ],
            "positive_option_occurrences_by_feature": all_contrib[
                "positive_option_occurrences_by_feature"
            ],
            "weighted_totals_by_feature": all_contrib[
                "weighted_totals_by_feature"
            ],
            "note": (
                "Counts are tie-inclusive diagnostic associations, not "
                "single-feature causal ablations."
            ),
        },
    }


def main() -> None:
    worker23 = json.loads(WORKER23_RECEIPT.read_text(encoding="utf-8"))
    evaluated_commit = os.environ.get("EVALUATED_COMMIT", "")
    workflow_run_id = os.environ.get("WORKFLOW_RUN_ID", "")

    with ProcessPoolExecutor(max_workers=TRACE_WORKERS) as executor:
        traces = list(executor.map(safe_trace_seed, SEEDS, chunksize=1))

    traces.sort(key=lambda item: item["seed"])
    if [item["seed"] for item in traces] != list(SEEDS):
        raise AssertionError("trace seed population/order mismatch")

    integrity = integrity_report(traces, worker23)

    errors = [
        trace for trace in traces if trace.get("error") is not None
    ]

    trace_by_seed = {
        trace["seed"]: trace
        for trace in traces
        if trace.get("error") is None
    }

    complete_trace = (
        not errors
        and len(trace_by_seed) == 32
        and all(
            trace["first_tier_divergence"] is not None
            and trace["first_selected_divergence"] is not None
            and trace["first_tier_divergence"]["target_decompositions"]
            for trace in trace_by_seed.values()
        )
    )

    downstream_linked = (
        complete_trace
        and all(
            trace["first_selected_divergence"]["decision_index"]
            >= trace["first_tier_divergence"]["decision_index"]
            and (
                trace["first_selected_divergence"]["tier_sets_differ_here"]
                or trace["first_selected_divergence"]["decision_index"]
                > trace["first_tier_divergence"]["decision_index"]
            )
            for trace in trace_by_seed.values()
        )
    )

    if not integrity["passed"] or not complete_trace:
        classification = "v6_changed_outcome_trace_diagnostic_invalid"
    elif not downstream_linked:
        classification = "v6_changed_outcome_trace_rng_or_state_confounded"
    else:
        classification = "v6_changed_outcome_trace_mechanism_resolved"

    cohort_summaries = {}
    answers = {}
    if integrity["passed"] and complete_trace:
        cohorts = {
            "all_32": SEEDS,
            "v4_win_to_v6_loss": V4_WIN_TO_V6_LOSS,
            "v6_only_wins": V6_ONLY_WINS,
            "deck_exhausted_to_no_legal_move": DECK_TO_NO_LEGAL,
            "no_legal_move_to_deck_exhausted": NO_LEGAL_TO_DECK,
            "other_failure_switches": OTHER_FAILURE_SWITCH,
        }
        cohort_summaries = {
            name: summarize_cohort(name, seeds, trace_by_seed)
            for name, seeds in cohorts.items()
        }
        answers = diagnostic_answers(trace_by_seed, cohort_summaries)

    total_feature_checks = sum(
        trace.get("audit", {}).get(
            "v4_no_draw_feature_equivalence_checks", 0
        )
        for trace in traces
    )
    total_feature_failures = sum(
        trace.get("audit", {}).get(
            "v4_no_draw_feature_equivalence_failures", 0
        )
        for trace in traces
    )

    raw = {
        "schema": "bandido-alcatraz-v6-changed-outcome-trace-audit",
        "schema_version": 1,
        "date": "2026-09-29",
        "dataset_status": (
            "already-spent / outcome-selected diagnostic / non-confirmatory"
        ),
        "preregistration_url": PREREGISTRATION_URL,
        "starting_main": STARTING_MAIN,
        "evaluated_commit": evaluated_commit,
        "worker23_authority": {
            "commit": STARTING_MAIN,
            "path": (
                "experiments/real-deck-policy-v6/"
                "current-model-spent-development-1000-1099-2026-09-28.json"
            ),
            "classification": worker23["classification"],
        },
        "fixed_model": {
            "deck_file": "data/deck-v1.json",
            "exit_geometry_source": "data/deck-observations-v0.json",
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
            "water_over_water_fix_commit": WATER_FIX_COMMIT,
            "legal_move_ordering": "canonical current implementation",
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
        "seed_scope": list(SEEDS),
        "seed_count": len(SEEDS),
        "fresh_seeds_used": False,
        "holdout_used": False,
        "hidden_draw_diagnostic_fields_logged": False,
        "v4_production_vs_no_draw_feature_equivalence": {
            "checks": total_feature_checks,
            "failures": total_feature_failures,
            "passed": total_feature_failures == 0,
        },
        "integrity": integrity,
        "classification": classification,
        "trace_completeness": {
            "seed_trace_errors": [item["seed"] for item in errors],
            "complete_trace": complete_trace,
            "downstream_linked": downstream_linked,
        },
        "traces": traces,
        "cohort_summaries": cohort_summaries,
        "diagnostic_answers": answers,
        "execution": {
            "trace_workers": TRACE_WORKERS,
            "mechanical_parallelization": True,
            "max_steps_per_policy_seed": MAX_STEPS,
            "authoritative_policy_seed_executions": 64,
            "note": (
                "Each exact policy/seed path is executed once for final-record "
                "replay; shared-prefix tier analysis adds deterministic scoring "
                "without additional policy trajectory execution."
            ),
        },
        "workflow_provenance": {
            "workflow_run_id": workflow_run_id,
            "evaluated_commit": evaluated_commit,
            "runner_requirement": (
                "[self-hosted, Linux, X64, bandido-alcatraz-ci]"
            ),
        },
        "interpretation_limits": [
            "The 32 seeds are outcome-selected from already-spent Worker #23 data.",
            "Cohort proportions do not generalize to the 100-seed development set or any population.",
            "This slice diagnoses mechanism only; it does not evaluate or support a new policy.",
            "No hidden draw identity or future outcome is used as a diagnostic mechanism feature.",
        ],
    }

    summary = {
        key: raw[key]
        for key in (
            "schema",
            "schema_version",
            "date",
            "dataset_status",
            "preregistration_url",
            "starting_main",
            "evaluated_commit",
            "worker23_authority",
            "seed_scope",
            "fresh_seeds_used",
            "holdout_used",
            "v4_production_vs_no_draw_feature_equivalence",
            "integrity",
            "classification",
            "trace_completeness",
            "cohort_summaries",
            "diagnostic_answers",
            "execution",
            "workflow_provenance",
            "interpretation_limits",
        )
    }
    summary["first_divergences"] = {
        str(trace["seed"]): {
            "first_tier": (
                {
                    "decision_index": trace["first_tier_divergence"][
                        "decision_index"
                    ],
                    "turn_index": trace["first_tier_divergence"]["turn_index"],
                    "label": trace["first_tier_divergence"]["label"],
                    "v4_selected_move": trace["first_tier_divergence"][
                        "v4_selected_move"
                    ],
                    "v6_best_first_tier": trace["first_tier_divergence"][
                        "v6_best_first_tier"
                    ],
                }
                if trace.get("first_tier_divergence") is not None
                else None
            ),
            "first_selected": (
                {
                    "decision_index": trace["first_selected_divergence"][
                        "decision_index"
                    ],
                    "turn_index": trace["first_selected_divergence"][
                        "turn_index"
                    ],
                    "v4": trace["first_selected_divergence"][
                        "selected_move_v4"
                    ],
                    "v6": trace["first_selected_divergence"][
                        "selected_move_v6"
                    ],
                    "tier_sets_differ_here": trace[
                        "first_selected_divergence"
                    ]["tier_sets_differ_here"],
                }
                if trace.get("first_selected_divergence") is not None
                else None
            ),
            "relation": trace.get("selected_divergence_relation"),
        }
        for trace in traces
    }

    RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT.write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SUMMARY_OUTPUT.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "WORKER24_RESULT="
        + json.dumps(
            {
                "classification": classification,
                "integrity_passed": integrity["passed"],
                "final_record_exact_matches": integrity[
                    "final_record_exact_matches"
                ],
                "transition_label_exact_matches": integrity[
                    "transition_label_exact_matches"
                ],
                "complete_trace": complete_trace,
                "downstream_linked": downstream_linked,
                "trace_errors": [item["seed"] for item in errors],
                "first_tier_labels": (
                    cohort_summaries.get("all_32", {}).get(
                        "divergence_label_counts"
                    )
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
