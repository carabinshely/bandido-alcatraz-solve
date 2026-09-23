import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from random import Random
from statistics import mean

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, legal_moves
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import (
    MoveFeatures,
    clone_state,
    move_features,
    score_features,
)


ROOT = Path(__file__).parents[1]
CANONICAL_RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v4"
    / "canonical-mechanism-replay-2026-09-22.json"
)
POLICY_NAME = "bounded_merge_v4_250"
SETUP_WEIGHT = 250

CLASS_A = [
    2001, 2004, 2020, 2024, 2034, 2084, 2098, 2104, 2110,
    2129, 2130, 2138, 2168, 2171, 2212, 2314, 2334, 2372,
]
CLASS_C = [2231, 2356, 2363]
V4_WINS = [
    2005, 2085, 2137, 2174, 2238, 2267, 2282, 2286, 2294,
    2322, 2340, 2345, 2371, 2383,
]
AUDIT_SEEDS = sorted(set(CLASS_A + CLASS_C + V4_WINS))

FAMILY_FIELDS = {
    "terminal": ("wins", "closes_last_without_win"),
    "equipment_collection": (
        "collect_needed",
        "collect_excess",
        "collect_degree_one",
    ),
    "topology": ("delta_open_tunnels",),
    "water_cover": ("delta_visible_water",),
    "water_space_safety": (
        "delta_water_obstruction",
        "new_trapped_water",
    ),
    "merge": (
        "delta_merge_opportunities",
        "bounded_merge_setup_gain",
    ),
    "exit_timing": ("places_exit_ready", "places_exit_early"),
}


def cohort_for(seed):
    if seed in CLASS_A:
        return "class_a_never_legally_placeable"
    if seed in CLASS_C:
        return "class_c_immediate_exit_then_dead_end"
    if seed in V4_WINS:
        return "canonical_v4_win"
    raise ValueError(seed)


def final_record(state, reason):
    ready = is_equipment_ready(state.raincoats, state.ropes)
    return {
        "won": state.won,
        "failure_reason": reason,
        "turns": state.turns,
        "final_open_tunnels": state.board.open_tunnels,
        "visible_water": state.board.visible_water_cells,
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "equipment_ready": ready,
        "exit_placed": state.exit_placed,
        "exit_equipment_water_ready": (
            state.exit_placed
            and state.board.visible_water_cells == 0
            and ready
        ),
    }


def move_signature(state, move):
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
        "is_exit": card.is_exit,
        "material": (
            card.material.value if card.material is not None else None
        ),
    }


def card_geometry(card):
    return {
        "card_id": card.card_id,
        "is_exit": card.is_exit,
        "external_tunnel_count": card.external_tunnel_count,
        "cells": [
            {
                "x": cell.x,
                "y": cell.y,
                "tunnel_edges": sorted(
                    edge.value for edge in cell.tunnel_edges
                ),
                "water": cell.water,
            }
            for cell in card.cells
        ],
    }


def score_payload(features, weights):
    raw = asdict(features)
    weighted = {
        field: raw[field] * getattr(weights, field)
        for field in MoveFeatures.__dataclass_fields__
    }
    families = {
        family: sum(weighted[field] for field in fields)
        for family, fields in FAMILY_FIELDS.items()
    }
    score = sum(weighted.values())
    assert score == score_features(features, weights)
    assert score == sum(families.values())
    return {
        "raw_features": raw,
        "weighted_contributions": weighted,
        "family_contributions": families,
        "score": score,
    }


def cell_roles(card, quarter_turns):
    rotated = card.rotated(quarter_turns)
    cells = {(cell.x, cell.y): cell for cell in rotated.cells}
    delta = {
        "N": (0, -1),
        "E": (1, 0),
        "S": (0, 1),
        "W": (-1, 0),
    }
    external = {}
    for coord, cell in cells.items():
        edges = []
        for edge in cell.tunnel_edges:
            dx, dy = delta[edge.value]
            if (coord[0] + dx, coord[1] + dy) not in cells:
                edges.append(edge.value)
        external[coord] = sorted(edges)

    connectable = [coord for coord, edges in external.items() if edges]
    terminal = [coord for coord, edges in external.items() if not edges]
    assert sum(len(edges) for edges in external.values()) == 1
    assert len(connectable) == 1
    assert len(terminal) == 1
    return rotated, connectable[0], terminal[0], external


def move_target(board, exit_card, move):
    _, connectable, _, _ = cell_roles(
        exit_card, move.quarter_turns
    )
    assert move.origin is not None
    target = (
        move.origin[0] + connectable[0],
        move.origin[1] + connectable[1],
    )
    return (
        target
        if target in board.open_tunnel_target_counts
        else None
    )


def exit_capacity(board, exit_card):
    moves = legal_moves(board, (exit_card,))
    targets = {
        target
        for move in moves
        for target in [move_target(board, exit_card, move)]
        if target is not None
    }
    return {
        "exit_legal_move_count": len(moves),
        "exit_compatible_frontier_target_count": len(targets),
        "frontier_targets": [list(coord) for coord in sorted(targets)],
    }


def fingerprint(card):
    return tuple(
        (
            cell.x,
            cell.y,
            tuple(sorted(
                edge.value for edge in cell.tunnel_edges
            )),
            cell.water,
        )
        for cell in card.cells
    )


def placement_rejection_audit(board, exit_card):
    rows = []
    seen = set()
    board_cells = board.cells
    frontier_targets = set(board.open_tunnel_target_counts)

    for quarter_turns in range(4):
        rotated, connectable, terminal, external = cell_roles(
            exit_card, quarter_turns
        )
        fp = fingerprint(rotated)
        for origin in sorted(board.candidate_origins(rotated)):
            key = (fp, origin)
            if key in seen:
                continue
            seen.add(key)

            coords = {
                (origin[0] + cell.x, origin[1] + cell.y)
                for cell in rotated.cells
            }
            connectable_global = (
                origin[0] + connectable[0],
                origin[1] + connectable[1],
            )
            terminal_global = (
                origin[0] + terminal[0],
                origin[1] + terminal[1],
            )
            overlaps = sorted(coords.intersection(board_cells))
            error = None
            try:
                board.clone()._prepare_placement(
                    exit_card, origin, quarter_turns
                )
                legal = True
            except ValueError as exc:
                legal = False
                error = str(exc)

            rows.append({
                "quarter_turns": quarter_turns,
                "origin": list(origin),
                "connectable_cell": list(connectable_global),
                "terminal_cell": list(terminal_global),
                "connectable_external_edges": external[connectable],
                "connectable_is_frontier_target": (
                    connectable_global in frontier_targets
                ),
                "overlap_count": len(overlaps),
                "overlaps": [list(coord) for coord in overlaps],
                "terminal_cell_occupied": (
                    terminal_global in board_cells
                ),
                "connectable_cell_occupied": (
                    connectable_global in board_cells
                ),
                "legal": legal,
                "engine_error_text": error,
            })

    legal_rows = [row for row in rows if row["legal"]]
    rejected = [row for row in rows if not row["legal"]]
    reasons = Counter(
        row["engine_error_text"] for row in rejected
    )
    overlap_reasons = {
        "a placement may cover only one existing water cell",
        "only a visible water cell may be covered",
    }
    pattern_reasons = {
        "tunnel/earth mismatch with adjacent card",
        "water cover must preserve the covered tunnel/earth pattern",
    }
    has_terminal_space = any(
        row["terminal_cell_occupied"]
        and row["engine_error_text"] in overlap_reasons
        for row in rejected
    )
    has_pattern = any(
        row["engine_error_text"] in pattern_reasons
        for row in rejected
    )

    if not rows:
        geometry_class = "no_attachable_frontier"
        geometry_basis = (
            "Board.candidate_origins generated zero candidates."
        )
    elif legal_rows:
        geometry_class = None
        geometry_basis = "At least one candidate is legal."
    elif rejected and all(
        row["terminal_cell_occupied"]
        and row["engine_error_text"] in overlap_reasons
        for row in rejected
    ):
        geometry_class = "terminal_cell_space_blocked"
        geometry_basis = (
            "Every candidate is rejected by an overlap rule and "
            "its EXIT terminal cell is occupied."
        )
    elif rejected and all(
        row["engine_error_text"] in pattern_reasons
        for row in rejected
    ):
        geometry_class = "adjacency_pattern_blocked"
        geometry_basis = (
            "Every candidate is rejected by an adjacency or "
            "water-cover tunnel/earth pattern rule."
        )
    elif has_terminal_space and has_pattern:
        geometry_class = "mixed_geometry_block"
        geometry_basis = (
            "Candidates include both terminal-cell overlap failures "
            "and tunnel/earth-pattern failures."
        )
    else:
        geometry_class = None
        geometry_basis = (
            "Raw engine evidence does not map cleanly to one "
            "requested derived geometry class."
        )

    return {
        "plausible_candidate_count": len(rows),
        "legal_count": len(legal_rows),
        "engine_rejection_reason_counts": dict(sorted(reasons.items())),
        "one_failure_reason_blocks_every_candidate": (
            bool(rejected)
            and len(reasons) == 1
            and sum(reasons.values()) == len(rows)
        ),
        "frontier_targets_examined": len(frontier_targets),
        "derived_geometry_class": geometry_class,
        "derived_geometry_basis": geometry_basis,
        "candidate_records": rows,
    }


def topology_type(before_open, after_open):
    if after_open > before_open:
        return "branches"
    if after_open < before_open:
        return "consolidates"
    return "flat"


def preserving_alternative_audit(
    state,
    exit_card,
    policy,
    scored,
    chosen_row,
    before_capacity,
    after_capacity,
    exit_seen_before_action,
):
    chosen_move, chosen_features, chosen_score = chosen_row
    chosen_payload = score_payload(
        chosen_features, policy.weights
    )
    global_max = max(score for _, _, score in scored)
    assert chosen_score == global_max

    alternatives = []
    before_open = state.board.open_tunnels
    for move, features, score in scored:
        clone = clone_state(state)
        card = clone.hand[move.hand_index]
        clone.apply(move, validate=False)

        if clone.exit_placed:
            continue
        cap = exit_capacity(clone.board, exit_card)
        if cap["exit_legal_move_count"] <= 0:
            continue

        payload = score_payload(features, policy.weights)
        alternatives.append({
            "move": move_signature(state, move),
            "resulting_capacity": cap,
            **payload,
            "topology_effect": topology_type(
                before_open, clone.board.open_tunnels
            ),
            "collects_equipment": move.action is Action.COLLECT,
            "covers_water": features.delta_visible_water > 0,
            "places_ordinary_card": (
                move.action is Action.PLACE and not card.is_exit
            ),
        })

    if not alternatives:
        return {
            "exit_seen_before_action": exit_seen_before_action,
            "before_capacity": before_capacity,
            "after_capacity": after_capacity,
            "preserving_alternative_exists": False,
            "preserving_alternative_in_actual_global_best_set": False,
            "historical_chosen_score": chosen_score,
            "best_preserving_score": None,
            "score_gap": None,
            "preventability_classification": "locally_unavoidable",
            "historical_chosen": {
                "move": move_signature(state, chosen_move),
                **chosen_payload,
            },
            "best_preserving_alternatives": [],
            "family_gap_ranges": None,
        }

    best_score = max(row["score"] for row in alternatives)
    best = [
        row for row in alternatives
        if row["score"] == best_score
    ]
    gap = chosen_score - best_score
    assert gap >= 0
    classification = (
        "avoidable_tied_best"
        if gap == 0
        else "avoidable_scored_lower"
    )

    gap_ranges = {}
    for family in FAMILY_FIELDS:
        values = [
            (
                chosen_payload["family_contributions"][family]
                - row["family_contributions"][family]
            )
            for row in best
        ]
        gap_ranges[family] = {
            "minimum": min(values),
            "maximum": max(values),
            "mean": mean(values),
        }
    for row in best:
        assert sum(
            chosen_payload["family_contributions"][family]
            - row["family_contributions"][family]
            for family in FAMILY_FIELDS
        ) == gap

    return {
        "exit_seen_before_action": exit_seen_before_action,
        "before_capacity": before_capacity,
        "after_capacity": after_capacity,
        "preserving_alternative_exists": True,
        "preserving_alternative_in_actual_global_best_set": (
            best_score == global_max
        ),
        "historical_chosen_score": chosen_score,
        "best_preserving_score": best_score,
        "score_gap": gap,
        "preventability_classification": classification,
        "historical_chosen": {
            "move": move_signature(state, chosen_move),
            **chosen_payload,
        },
        "best_preserving_alternatives": best,
        "family_gap_ranges": gap_ranges,
    }


def zero_intervals(points):
    intervals = []
    current = None
    for point in points:
        is_zero = point["exit_legal_move_count"] == 0
        if is_zero and current is None:
            current = {
                "start_state_turn": point["state_turn"],
                "end_state_turn": point["state_turn"],
                "state_turn_count": 1,
            }
        elif is_zero:
            current["end_state_turn"] = point["state_turn"]
            current["state_turn_count"] += 1
        elif current is not None:
            current["recovered_at_state_turn"] = point["state_turn"]
            current["recovered"] = True
            intervals.append(current)
            current = None
    if current is not None:
        current["recovered_at_state_turn"] = None
        current["recovered"] = False
        intervals.append(current)
    return intervals


def summarize_seed(trace):
    points = trace["board_capacity_points"]
    timeline = trace["capacity_timeline"]
    first_seen = trace["first_exit_seen_state_turn"]
    placement = trace["exit_placement_action_turn"]
    intervals = zero_intervals(points)
    zero_points = [
        point for point in points
        if point["exit_legal_move_count"] == 0
    ]
    transitions = trace["last_slot_killing_decisions"]

    at_first_seen = next(
        (
            row for row in timeline
            if row["state_turn"] == first_seen
            and row["exit_currently_visible"]
        ),
        None,
    )
    after_first_seen = [
        row for row in timeline
        if first_seen is not None
        and row["state_turn"] >= first_seen
        and (
            placement is None
            or row["state_turn"] <= placement - 1
        )
    ]
    visible_rows = [
        row for row in timeline
        if row["exit_currently_visible"]
    ]

    recoveries = [
        interval for interval in intervals
        if interval["recovered"]
    ]
    recovers_before_sighting = any(
        interval["recovered_at_state_turn"] is not None
        and first_seen is not None
        and interval["recovered_at_state_turn"] <= first_seen
        for interval in intervals
    )
    recovers_while_visible = any(
        interval["recovered_at_state_turn"] is not None
        and any(
            row["state_turn"]
            == interval["recovered_at_state_turn"]
            and row["exit_currently_visible"]
            for row in timeline
        )
        for interval in intervals
    )

    if visible_rows:
        visible_caps = [
            row["exit_legal_move_count"]
            for row in visible_rows
        ]
        if all(value == 0 for value in visible_caps):
            visible_pattern = "continuously_zero"
        elif visible_caps[0] > 0 and 0 in visible_caps:
            visible_pattern = "temporarily_positive_then_lost"
        else:
            visible_pattern = "another_observed_pattern"
    else:
        visible_pattern = "exit_never_visible"

    before_sighting_points = [
        point for point in points
        if first_seen is None
        or point["state_turn"] <= first_seen
    ]
    return {
        "seed": trace["seed"],
        "cohort": trace["cohort"],
        "initial_exit_legal_move_count": points[0][
            "exit_legal_move_count"
        ],
        "initial_exit_compatible_frontier_target_count": points[0][
            "exit_compatible_frontier_target_count"
        ],
        "capacity_immediately_before_exit_first_appearance": trace[
            "capacity_immediately_before_exit_first_appearance"
        ],
        "capacity_at_exit_first_sighting": (
            None if at_first_seen is None else {
                "state_turn": at_first_seen["state_turn"],
                "exit_legal_move_count": at_first_seen[
                    "exit_legal_move_count"
                ],
                "exit_compatible_frontier_target_count": (
                    at_first_seen[
                        "exit_compatible_frontier_target_count"
                    ]
                ),
            }
        ),
        "first_zero_capacity_state_turn": (
            zero_points[0]["state_turn"]
            if zero_points else None
        ),
        "first_positive_to_zero_action_turn": (
            transitions[0]["action_turn"]
            if transitions else None
        ),
        "zero_capacity_intervals": intervals,
        "zero_capacity_interval_count": len(intervals),
        "longest_zero_capacity_interval_state_turns": max(
            (
                interval["state_turn_count"]
                for interval in intervals
            ),
            default=0,
        ),
        "capacity_ever_recovers_after_zero": bool(recoveries),
        "recovers_before_exit_first_sighting": (
            recovers_before_sighting
        ),
        "recovers_while_exit_visible": recovers_while_visible,
        "minimum_exit_legal_move_count_before_sighting": (
            min(
                point["exit_legal_move_count"]
                for point in before_sighting_points
            )
            if before_sighting_points else None
        ),
        "maximum_exit_legal_move_count_before_placement": max(
            point["exit_legal_move_count"] for point in points
        ),
        "capacity_immediately_before_actual_exit_placement": trace[
            "capacity_immediately_before_actual_exit_placement"
        ],
        "exit_first_seen_state_turn": first_seen,
        "exit_placement_action_turn": placement,
        "exit_visible_capacity_pattern": visible_pattern,
        "capacity_positive_continuously_from_first_sighting_to_placement": (
            None
            if first_seen is None or placement is None
            else all(
                row["exit_legal_move_count"] > 0
                for row in after_first_seen
            )
        ),
        "last_slot_killing_decision_count": len(transitions),
        "last_slot_killing_then_later_recovered": (
            bool(transitions) and bool(recoveries)
        ),
    }


def trace_seed(seed, deck, canonical_final):
    policy = BoundedMergeV4Policy(setup_weight=SETUP_WEIGHT)
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )

    ever_seen = False
    first_seen_turn = None
    capacity_before_first_appearance = None
    capacity_before_actual_placement = None
    exit_placement_action_turn = None
    refresh_count = 0
    timeline = []
    board_points = []
    last_slot = []
    rejection_states = []
    class_c_post_placement = []
    observation_index = 0

    board_points.append({
        "state_turn": state.turns,
        **exit_capacity(state.board, deck.exit_card),
    })

    for _ in range(1000):
        visible = any(card.is_exit for card in state.hand)
        if visible and not ever_seen:
            ever_seen = True
            first_seen_turn = state.turns
            if capacity_before_first_appearance is None:
                capacity_before_first_appearance = exit_capacity(
                    state.board, deck.exit_card
                )

        capacity = (
            None
            if state.exit_placed
            else exit_capacity(state.board, deck.exit_card)
        )

        if state.won:
            result = final_record(state, "win")
            break
        if state.board.open_tunnels == 0:
            result = final_record(
                state, "closed_tunnels_conditions_failed"
            )
            break
        if not state.hand and not state.draw_pile:
            result = final_record(state, "deck_exhausted")
            break

        moves = state.legal_moves()
        if not state.exit_placed:
            observation_index += 1
            timeline.append({
                "observation_index": observation_index,
                "state_turn": state.turns,
                "action_turn_about_to_occur": state.turns + 1,
                "exit_already_seen": ever_seen,
                "exit_currently_visible": visible,
                "exit_placed": False,
                "open_tunnels": state.board.open_tunnels,
                "merge_opportunities": state.board.merge_opportunities,
                "visible_water": state.board.visible_water_cells,
                "equipment_ready": is_equipment_ready(
                    state.raincoats, state.ropes
                ),
                "refresh_count_so_far": refresh_count,
                "legal_canonical_move_exists": bool(moves),
                **capacity,
            })

            if (
                seed in CLASS_A
                and visible
                and capacity["exit_legal_move_count"] == 0
            ):
                rejection_states.append({
                    "observation_index": observation_index,
                    "state_turn": state.turns,
                    "refresh_count_so_far": refresh_count,
                    **placement_rejection_audit(
                        state.board, deck.exit_card
                    ),
                })

        if not moves:
            before_seen = ever_seen
            before_capacity = capacity
            before_visible = visible
            if state.refresh_unplayable_hand():
                refresh_count += 1
                after_visible = any(
                    card.is_exit for card in state.hand
                )
                if after_visible and not before_seen:
                    ever_seen = True
                    first_seen_turn = state.turns
                    capacity_before_first_appearance = before_capacity
                if seed in CLASS_C and state.exit_placed:
                    class_c_post_placement.append({
                        "event": "refresh",
                        "state_turn": state.turns,
                        "refresh_count": refresh_count,
                        "before_exit_visible": before_visible,
                        "after_exit_visible": after_visible,
                        "open_tunnels": state.board.open_tunnels,
                        "visible_water": state.board.visible_water_cells,
                    })
                continue
            result = final_record(state, "no_legal_move")
            break

        scored = []
        for move in moves:
            features = move_features(state, move)
            score = score_features(features, policy.weights)
            scored.append((move, features, score))
        best_score = max(score for _, _, score in scored)
        best_rows = [
            row for row in scored if row[2] == best_score
        ]
        chosen_move, chosen_features, chosen_score = rng.choice(
            best_rows
        )
        chosen_card = state.hand[chosen_move.hand_index]

        before_open = state.board.open_tunnels
        before_merge = state.board.merge_opportunities
        before_water = state.board.visible_water_cells
        before_capacity = capacity
        action_turn = state.turns + 1

        chosen_clone = clone_state(state)
        chosen_clone.apply(chosen_move, validate=False)
        chosen_after_capacity = (
            None
            if chosen_clone.exit_placed
            else exit_capacity(chosen_clone.board, deck.exit_card)
        )

        if (
            before_capacity is not None
            and before_capacity["exit_legal_move_count"] > 0
            and chosen_after_capacity is not None
            and chosen_after_capacity["exit_legal_move_count"] == 0
        ):
            audit = preserving_alternative_audit(
                state,
                deck.exit_card,
                policy,
                scored,
                (chosen_move, chosen_features, chosen_score),
                before_capacity,
                chosen_after_capacity,
                ever_seen,
            )
            last_slot.append({
                "seed": seed,
                "cohort": cohort_for(seed),
                "action_turn": action_turn,
                "state_turn_before_action": state.turns,
                "exit_had_already_been_seen": ever_seen,
                "chosen_action": move_signature(
                    state, chosen_move
                ),
                "before_open_tunnels": before_open,
                "after_open_tunnels": (
                    chosen_clone.board.open_tunnels
                ),
                "before_merge_opportunities": before_merge,
                "after_merge_opportunities": (
                    chosen_clone.board.merge_opportunities
                ),
                "actual_move_features": asdict(chosen_features),
                "actual_weighted_score": chosen_score,
                "local_preventability_audit": audit,
            })

        was_seen = ever_seen
        was_visible = visible
        move_sig = move_signature(state, chosen_move)
        state.apply(chosen_move)

        if (
            not was_seen
            and any(card.is_exit for card in state.hand)
        ):
            ever_seen = True
            first_seen_turn = state.turns
            capacity_before_first_appearance = before_capacity

        if (
            chosen_card.is_exit
            and chosen_move.action is Action.PLACE
        ):
            exit_placement_action_turn = action_turn
            capacity_before_actual_placement = before_capacity
        elif not state.exit_placed:
            board_points.append({
                "state_turn": state.turns,
                **exit_capacity(state.board, deck.exit_card),
            })

        if seed in CLASS_C and state.exit_placed:
            class_c_post_placement.append({
                "event": (
                    "exit_placement"
                    if chosen_card.is_exit
                    else "action"
                ),
                "action_turn": action_turn,
                "move": move_sig,
                "before_open_tunnels": before_open,
                "after_open_tunnels": state.board.open_tunnels,
                "before_merge_opportunities": before_merge,
                "after_merge_opportunities": (
                    state.board.merge_opportunities
                ),
                "before_visible_water": before_water,
                "after_visible_water": (
                    state.board.visible_water_cells
                ),
                "exit_was_visible_before_action": was_visible,
            })

    else:
        result = final_record(state, "step_limit")

    if result != canonical_final:
        return {
            "seed": seed,
            "cohort": cohort_for(seed),
            "match": False,
            "canonical_final": canonical_final,
            "instrumented_final": result,
        }

    trace = {
        "seed": seed,
        "cohort": cohort_for(seed),
        "match": True,
        "final": result,
        "first_exit_seen_state_turn": first_seen_turn,
        "exit_placement_action_turn": exit_placement_action_turn,
        "capacity_immediately_before_exit_first_appearance": (
            capacity_before_first_appearance
        ),
        "capacity_immediately_before_actual_exit_placement": (
            capacity_before_actual_placement
        ),
        "refresh_count": refresh_count,
        "capacity_timeline": timeline,
        "board_capacity_points": board_points,
        "last_slot_killing_decisions": last_slot,
        "class_a_exit_visible_rejection_audits": (
            rejection_states
        ),
        "class_c_post_placement_trajectory": (
            class_c_post_placement
        ),
    }
    trace["capacity_summary"] = summarize_seed(trace)
    return trace


def aggregate_rejections(traces):
    reasons = Counter()
    classes = Counter()
    visible_states = 0
    candidates = 0
    for trace in traces:
        for state in trace[
            "class_a_exit_visible_rejection_audits"
        ]:
            visible_states += 1
            candidates += state["plausible_candidate_count"]
            reasons.update(
                state["engine_rejection_reason_counts"]
            )
            classes[state["derived_geometry_class"]] += 1
    return {
        "visible_zero_capacity_state_observations": visible_states,
        "plausible_candidates_examined": candidates,
        "engine_rejection_reason_counts": dict(
            sorted(reasons.items())
        ),
        "derived_geometry_class_counts": {
            str(key): value
            for key, value in sorted(
                classes.items(),
                key=lambda item: str(item[0]),
            )
        },
    }


def emit_chunks(payload):
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    )
    size = 16000
    chunks = [
        encoded[index:index + size]
        for index in range(0, len(encoded), size)
    ]
    print(
        f"EXIT_CAPACITY_RECEIPT_CHUNK_COUNT={len(chunks)}"
    )
    for index, chunk in enumerate(chunks):
        print(
            f"EXIT_CAPACITY_RECEIPT_CHUNK_{index:04d}={chunk}"
        )


def main():
    source = json.loads(
        CANONICAL_RECEIPT.read_text(encoding="utf-8")
    )
    canonical = source[
        "canonical_per_seed_final_records"
    ][POLICY_NAME]
    canonical_wins = sorted(
        int(seed)
        for seed, row in canonical.items()
        if row["won"]
    )
    assert canonical_wins == V4_WINS

    deck = load_real_deck(ROOT / "data")
    assert deck.exit_card.is_exit
    assert deck.exit_card.card_id == "exit"
    assert deck.exit_card.external_tunnel_count == 1

    traces = []
    mismatches = []
    for seed in AUDIT_SEEDS:
        trace = trace_seed(
            seed, deck, canonical[str(seed)]
        )
        traces.append(trace)
        if not trace["match"]:
            mismatches.append(trace)

    if mismatches:
        payload = {
            "experiment": "v4-exit-placement-capacity-audit",
            "date": "2026-09-22",
            "dataset_status": (
                "already-spent / development / diagnostic / "
                "non-confirmatory"
            ),
            "replay_integrity": {
                "records_compared": len(AUDIT_SEEDS),
                "exact_matches": (
                    len(AUDIT_SEEDS) - len(mismatches)
                ),
                "mismatches": len(mismatches),
                "passed": False,
            },
            "mismatch_records": mismatches,
        }
        emit_chunks(payload)
        raise SystemExit("replay integrity gate failed")

    class_a = [
        trace for trace in traces
        if trace["seed"] in CLASS_A
    ]
    class_c = [
        trace for trace in traces
        if trace["seed"] in CLASS_C
    ]
    wins = [
        trace for trace in traces
        if trace["seed"] in V4_WINS
    ]
    first_losses_a = [
        trace["last_slot_killing_decisions"][0]
        for trace in class_a
        if trace["last_slot_killing_decisions"]
    ]
    all_last_slot = [
        row
        for trace in traces
        for row in trace["last_slot_killing_decisions"]
    ]

    class_a_table = []
    for trace in class_a:
        summary = trace["capacity_summary"]
        first_loss = (
            trace["last_slot_killing_decisions"][0]
            if trace["last_slot_killing_decisions"]
            else None
        )
        class_a_table.append({
            **summary,
            "final": trace["final"],
            "first_last_slot_loss": first_loss,
            "last_slot_loss_before_first_sighting": (
                first_loss is not None
                and trace["first_exit_seen_state_turn"]
                is not None
                and first_loss["action_turn"]
                <= trace["first_exit_seen_state_turn"]
            ),
            "turns_from_first_last_slot_loss_to_sighting": (
                None
                if first_loss is None
                or trace["first_exit_seen_state_turn"]
                is None
                else (
                    trace["first_exit_seen_state_turn"]
                    - first_loss["action_turn"]
                )
            ),
            "terminal_refresh_exposes_earlier_geometric_loss": (
                first_loss is not None
                and trace["first_exit_seen_state_turn"]
                is not None
                and first_loss["action_turn"]
                <= trace["first_exit_seen_state_turn"]
                and not summary[
                    "recovers_before_exit_first_sighting"
                ]
                and trace["final"]["failure_reason"]
                == "no_legal_move"
            ),
        })

    payload = {
        "experiment": "v4-exit-placement-capacity-audit",
        "date": "2026-09-22",
        "branch": "bootstrap/model-foundation",
        "dataset_status": (
            "already-spent / development / diagnostic / "
            "non-confirmatory"
        ),
        "fresh_seeds_used": False,
        "orchestrator_decision": (
            "https://github.com/carabinshely/"
            "bandido-alcatraz-solve/issues/2"
            "#issuecomment-5779006521"
        ),
        "canonical_source_receipts": [
            "experiments/real-deck-policy-v4/"
            "canonical-mechanism-replay-2026-09-22.json",
            "experiments/real-deck-policy-v4/"
            "exit-phase-diagnostics-2026-09-22.json",
            "experiments/real-deck-policy-v4/"
            "exit-deferral-score-margin-audit-2026-09-22.json",
        ],
        "fixed_model": {
            "deck_file": "data/deck-v1.json",
            "exit_geometry_source": (
                "data/deck-observations-v0.json"
            ),
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
            "policy": (
                "BoundedMergeV4Policy(setup_weight=250)"
            ),
        },
        "exit_geometry": card_geometry(deck.exit_card),
        "capacity_metric_semantics": {
            "exit_legal_move_count": (
                "len(legal_moves(board, "
                "(canonical_exit_card,))); uses canonical "
                "move generation and Board.can_place."
            ),
            "exit_compatible_frontier_target_count": (
                "Across legal EXIT moves, count distinct "
                "board open_tunnel_target_counts coordinates "
                "occupied by the rotated EXIT cell carrying "
                "its sole external tunnel edge. Equivalent "
                "moves attaching at the same frontier cell "
                "count once."
            ),
            "capacity_is_diagnostic_only": (
                "EXIT is never inserted into the canonical "
                "hand; capacity uses only the visible board "
                "and public EXIT geometry."
            ),
            "zero_interval": (
                "Consecutive distinct action-state turns "
                "with exit_legal_move_count == 0 before EXIT "
                "placement. Refreshes do not change board "
                "state or create a new action-state turn."
            ),
        },
        "audited_cohorts": {
            "class_a_never_legally_placeable": CLASS_A,
            "class_c_immediate_exit_then_dead_end": CLASS_C,
            "canonical_v4_wins": V4_WINS,
        },
        "replay_integrity": {
            "records_compared": len(AUDIT_SEEDS),
            "exact_matches": len(AUDIT_SEEDS),
            "mismatches": 0,
            "passed": True,
            "fields": [
                "won",
                "failure_reason",
                "turns",
                "final_open_tunnels",
                "visible_water",
                "raincoats",
                "ropes",
                "equipment_ready",
                "exit_placed",
                "exit_equipment_water_ready",
            ],
        },
        "per_seed_capacity_summaries": [
            trace["capacity_summary"]
            for trace in traces
        ],
        "class_a_per_seed_table": class_a_table,
        "all_last_slot_killing_decisions": all_last_slot,
        "first_class_a_last_slot_losses": first_losses_a,
        "class_a_visible_placement_rejection_audits": [
            {
                "seed": trace["seed"],
                "states": trace[
                    "class_a_exit_visible_rejection_audits"
                ],
            }
            for trace in class_a
        ],
        "placement_rejection_aggregate": (
            aggregate_rejections(class_a)
        ),
        "canonical_v4_win_controls": [
            {
                "seed": trace["seed"],
                "final": trace["final"],
                **trace["capacity_summary"],
                "last_slot_killing_decisions": trace[
                    "last_slot_killing_decisions"
                ],
            }
            for trace in wins
        ],
        "class_c_controls": [
            {
                "seed": trace["seed"],
                "final": trace["final"],
                **trace["capacity_summary"],
                "first_legal_exit_action_turn": next(
                    (
                        row["state_turn"] + 1
                        for row in trace["capacity_timeline"]
                        if row["exit_currently_visible"]
                        and row["exit_legal_move_count"] > 0
                    ),
                    None,
                ),
                "placement_consumes_only_remaining_compatible_target": (
                    trace[
                        "capacity_immediately_before_actual_exit_placement"
                    ] is not None
                    and trace[
                        "capacity_immediately_before_actual_exit_placement"
                    ][
                        "exit_compatible_frontier_target_count"
                    ]
                    == 1
                ),
                "post_placement_trajectory": trace[
                    "class_c_post_placement_trajectory"
                ],
            }
            for trace in class_c
        ],
        "per_seed_capacity_timelines": {
            str(trace["seed"]): trace["capacity_timeline"]
            for trace in traces
        },
        "answers": {
            "q1": {"pending_interpretation": True},
            "q2": {"pending_interpretation": True},
            "q3": {"pending_interpretation": True},
            "q4": {"pending_interpretation": True},
            "q5": {"pending_interpretation": True},
            "q6": {"pending_interpretation": True},
        },
        "final_classification": "pending_interpretation",
        "recommended_next_step": None,
        "evaluated_commit": None,
        "workflow_run": None,
        "runner": None,
        "tests": None,
        "bugs_or_invalidated_runs": [],
        "unresolved_risks": [],
    }

    summary = {
        "replay_integrity": payload["replay_integrity"],
        "class_a": [
            {
                "seed": row["seed"],
                "first_seen": row[
                    "exit_first_seen_state_turn"
                ],
                "initial_capacity": row[
                    "initial_exit_legal_move_count"
                ],
                "capacity_at_sighting": (
                    None
                    if row[
                        "capacity_at_exit_first_sighting"
                    ] is None
                    else row[
                        "capacity_at_exit_first_sighting"
                    ]["exit_legal_move_count"]
                ),
                "first_kill_action": row[
                    "first_positive_to_zero_action_turn"
                ],
                "recovers_before_sighting": row[
                    "recovers_before_exit_first_sighting"
                ],
                "visible_pattern": row[
                    "exit_visible_capacity_pattern"
                ],
            }
            for row in class_a_table
        ],
        "class_a_first_losses": len(first_losses_a),
        "class_a_locally_unavoidable": sum(
            row["local_preventability_audit"][
                "preventability_classification"
            ] == "locally_unavoidable"
            for row in first_losses_a
        ),
        "class_a_with_preserving_alternative": sum(
            row["local_preventability_audit"][
                "preserving_alternative_exists"
            ]
            for row in first_losses_a
        ),
        "class_a_score_gaps": [
            row["local_preventability_audit"][
                "score_gap"
            ]
            for row in first_losses_a
            if row["local_preventability_audit"][
                "score_gap"
            ] is not None
        ],
        "rejections": payload[
            "placement_rejection_aggregate"
        ],
        "wins": [
            {
                "seed": row["seed"],
                "ever_zero": (
                    row["zero_capacity_interval_count"] > 0
                ),
                "recovers": row[
                    "capacity_ever_recovers_after_zero"
                ],
                "positive_at_first_sighting": (
                    row[
                        "capacity_at_exit_first_sighting"
                    ] is not None
                    and row[
                        "capacity_at_exit_first_sighting"
                    ]["exit_legal_move_count"] > 0
                ),
                "continuous_positive": row[
                    "capacity_positive_continuously_from_first_sighting_to_placement"
                ],
                "kill_then_recovered": row[
                    "last_slot_killing_then_later_recovered"
                ],
            }
            for row in payload["canonical_v4_win_controls"]
        ],
        "class_c": [
            {
                "seed": row["seed"],
                "capacity_at_sighting": row[
                    "capacity_at_exit_first_sighting"
                ],
                "first_legal_exit_action_turn": row[
                    "first_legal_exit_action_turn"
                ],
                "exit_placement_action_turn": row[
                    "exit_placement_action_turn"
                ],
                "consumes_only_target": row[
                    "placement_consumes_only_remaining_compatible_target"
                ],
                "final": row["final"],
            }
            for row in payload["class_c_controls"]
        ],
    }
    print(
        "EXIT_CAPACITY_AUDIT_SUMMARY="
        + json.dumps(summary, sort_keys=True)
    )
    emit_chunks(payload)


if __name__ == "__main__":
    main()
