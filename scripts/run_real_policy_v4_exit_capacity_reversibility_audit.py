import json
from dataclasses import asdict
from pathlib import Path
from random import Random
from statistics import mean, median

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, legal_moves
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import (
    MoveFeatures,
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
WORKER7_RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v4"
    / "exit-placement-capacity-audit-2026-09-22.json"
)
POLICY_NAME = "bounded_merge_v4_250"
SETUP_WEIGHT = 250

CLASS_A = [
    2001, 2004, 2020, 2024, 2034, 2084, 2098, 2104, 2110,
    2129, 2130, 2138, 2168, 2171, 2212, 2314, 2334, 2372,
]
WIN_ZERO = [2005, 2238, 2282, 2286, 2371]
WIN_ALWAYS_POSITIVE = [
    2085, 2137, 2174, 2267, 2294, 2322, 2340, 2345, 2383,
]
AUDIT_SEEDS = sorted(CLASS_A + WIN_ZERO + WIN_ALWAYS_POSITIVE)

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
        return "class_a_failure"
    if seed in WIN_ZERO:
        return "winning_zero_capacity_control"
    if seed in WIN_ALWAYS_POSITIVE:
        return "winning_always_positive_control"
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


def geometry_clone(state):
    return GameState(
        board=state.board.clone(),
        draw_pile=[],
        hand=list(state.hand),
        raincoats=state.raincoats,
        ropes=state.ropes,
        exit_placed=state.exit_placed,
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
    )


def move_signature(state, move):
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
        "material": (
            card.material.value if card.material is not None else None
        ),
        "is_exit": card.is_exit,
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
    deltas = {
        "N": (0, -1),
        "E": (1, 0),
        "S": (0, 1),
        "W": (-1, 0),
    }
    external = {}
    for coord, cell in cells.items():
        edges = []
        for edge in cell.tunnel_edges:
            dx, dy = deltas[edge.value]
            if (coord[0] + dx, coord[1] + dy) not in cells:
                edges.append(edge.value)
        external[coord] = sorted(edges)
    connectable = [coord for coord, edges in external.items() if edges]
    terminal = [coord for coord, edges in external.items() if not edges]
    assert sum(len(edges) for edges in external.values()) == 1
    assert len(connectable) == 1
    assert len(terminal) == 1
    return rotated, connectable[0], terminal[0]


def move_target(board, exit_card, move):
    _, connectable, _ = cell_roles(exit_card, move.quarter_turns)
    assert move.origin is not None
    target = (
        move.origin[0] + connectable[0],
        move.origin[1] + connectable[1],
    )
    return target if target in board.open_tunnel_target_counts else None


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
    }


def fingerprint(card):
    return tuple(
        (
            cell.x,
            cell.y,
            tuple(sorted(edge.value for edge in cell.tunnel_edges)),
            cell.water,
        )
        for cell in card.cells
    )


def occupied_terminal_block_candidate_count(board, exit_card):
    frontier = set(board.open_tunnel_target_counts)
    board_cells = board.cells
    seen = set()
    count = 0
    examined = 0
    for quarter_turns in range(4):
        rotated, connectable, terminal = cell_roles(
            exit_card, quarter_turns
        )
        fp = fingerprint(rotated)
        for origin in sorted(board.candidate_origins(rotated)):
            key = (fp, origin)
            if key in seen:
                continue
            seen.add(key)
            connectable_global = (
                origin[0] + connectable[0],
                origin[1] + connectable[1],
            )
            if connectable_global not in frontier:
                continue
            examined += 1
            terminal_global = (
                origin[0] + terminal[0],
                origin[1] + terminal[1],
            )
            if (
                connectable_global not in board_cells
                and terminal_global in board_cells
                and not board_cells[terminal_global].water
            ):
                count += 1
    return {
        "open_frontier_target_count": len(frontier),
        "frontier_exit_candidates_examined": examined,
        "occupied_terminal_block_candidate_count": count,
    }


def move_taxonomy(before_state, after_state, move, features):
    labels = []
    if move.action is Action.COLLECT:
        labels.append("equipment_collection")
    else:
        labels.append("ordinary_placement")
        if features.delta_visible_water > 0:
            labels.append("water_cover_placement")
        before_open = before_state.board.open_tunnels
        after_open = after_state.board.open_tunnels
        if after_open < before_open:
            labels.append("consolidation")
        elif after_open > before_open:
            labels.append("branching")
        else:
            labels.append("flat_topology_placement")
    return labels


def audit_zero_state(
    *,
    seed,
    cohort,
    interval_id,
    state,
    exit_card,
    policy,
    moves,
    scored_rows,
    chosen_row,
    visible_state_index,
    hand_generation_index,
    refresh_count,
    ever_seen,
    current_visible,
):
    assert not state.exit_placed
    capacity = exit_capacity(state.board, exit_card)
    assert capacity["exit_legal_move_count"] == 0
    assert capacity["exit_compatible_frontier_target_count"] == 0

    global_best_score = (
        max(row[2] for row in scored_rows)
        if scored_rows else None
    )
    chosen_move = chosen_row[0] if chosen_row is not None else None

    restoring = []
    for move, features, score in scored_rows:
        clone = geometry_clone(state)
        before_open = clone.board.open_tunnels
        before_merge = clone.board.merge_opportunities
        clone.apply(move, validate=False)
        if clone.exit_placed:
            continue
        result_capacity = exit_capacity(clone.board, exit_card)
        if result_capacity["exit_legal_move_count"] <= 0:
            continue
        payload = score_payload(features, policy.weights)
        restoring.append({
            "move": move_signature(state, move),
            **payload,
            "resulting_exit_legal_move_count": (
                result_capacity["exit_legal_move_count"]
            ),
            "resulting_exit_compatible_frontier_target_count": (
                result_capacity[
                    "exit_compatible_frontier_target_count"
                ]
            ),
            "before_open_tunnels": before_open,
            "after_open_tunnels": clone.board.open_tunnels,
            "before_merge_opportunities": before_merge,
            "after_merge_opportunities": (
                clone.board.merge_opportunities
            ),
            "move_type_labels": move_taxonomy(
                state, clone, move, features
            ),
        })

    if restoring:
        best_score = max(row["score"] for row in restoring)
        best_restoring = [
            row for row in restoring if row["score"] == best_score
        ]
        score_gap = global_best_score - best_score
        assert score_gap >= 0
        any_global_best = best_score == global_best_score
        tied_global_best_count = sum(
            row["score"] == global_best_score
            for row in restoring
        )
        best_exit_capacity = max(
            row["resulting_exit_legal_move_count"]
            for row in restoring
        )
        best_frontier_capacity = max(
            row["resulting_exit_compatible_frontier_target_count"]
            for row in restoring
        )
    else:
        best_score = None
        best_restoring = []
        score_gap = None
        any_global_best = False
        tied_global_best_count = 0
        best_exit_capacity = 0
        best_frontier_capacity = 0

    canonical_chosen_restoring = (
        chosen_move is not None
        and any(
            row["move"] == move_signature(state, chosen_move)
            for row in restoring
        )
    )
    recovery_deferral = bool(
        restoring
        and chosen_move is not None
        and not canonical_chosen_restoring
    )

    state_id = (
        f"{seed}:t{state.turns}:h{hand_generation_index}:"
        f"v{visible_state_index}"
    )
    return {
        "state_id": state_id,
        "seed": seed,
        "cohort": cohort,
        "zero_interval_id": interval_id,
        "state_turn": state.turns,
        "refresh_index": refresh_count,
        "hand_generation_index": hand_generation_index,
        "visible_state_index": visible_state_index,
        "exit_ever_seen": ever_seen,
        "exit_currently_visible": current_visible,
        "exit_placed": False,
        "current_hand_card_ids": [
            card.card_id for card in state.hand
        ],
        "draw_pile_size": len(state.draw_pile),
        "open_tunnels": state.board.open_tunnels,
        "merge_opportunities": state.board.merge_opportunities,
        "visible_water": state.board.visible_water_cells,
        "equipment_ready": is_equipment_ready(
            state.raincoats, state.ropes
        ),
        "refresh_count_so_far": refresh_count,
        "legal_move_count": len(moves),
        **capacity,
        **occupied_terminal_block_candidate_count(
            state.board, exit_card
        ),
        "capacity_restoring_move_count": len(restoring),
        "one_step_exit_capacity_recoverable": bool(restoring),
        "best_resulting_exit_legal_move_count": best_exit_capacity,
        "best_resulting_frontier_target_count": (
            best_frontier_capacity
        ),
        "best_restoring_v4_score": best_score,
        "canonical_global_best_score": global_best_score,
        "restoring_score_gap": score_gap,
        "any_restoring_move_in_actual_global_best_set": (
            any_global_best
        ),
        "canonical_chosen_move_is_restoring": (
            canonical_chosen_restoring
        ),
        "restoring_moves_tied_global_best_count": (
            tied_global_best_count
        ),
        "canonical_chosen_move": (
            None
            if chosen_move is None
            else move_signature(state, chosen_move)
        ),
        "recovery_deferral": recovery_deferral,
        "best_restoring_moves": best_restoring,
        "all_capacity_restoring_moves": restoring,
    }


def visibility_stratum(row):
    if not row["exit_ever_seen"]:
        return "pre_seen"
    if row["exit_currently_visible"]:
        return "seen_visible"
    return "seen_not_currently_visible"


def distribution(values):
    values = sorted(values)
    if not values:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "mean": None,
            "maximum": None,
            "values": [],
        }
    return {
        "count": len(values),
        "minimum": values[0],
        "median": median(values),
        "mean": mean(values),
        "maximum": values[-1],
        "values": values,
    }


def summarize_interval(interval, state_records):
    rows = [
        state_records[index]
        for index in interval["state_record_indices"]
    ]
    assert rows
    recoverable = [
        row for row in rows
        if row["one_step_exit_capacity_recoverable"]
    ]
    gaps = [
        row["restoring_score_gap"]
        for row in recoverable
        if row["restoring_score_gap"] is not None
    ]
    strata = {}
    for label in ("pre_seen", "seen_visible", "seen_not_currently_visible"):
        subset = [
            row for row in rows
            if visibility_stratum(row) == label
        ]
        strata[label] = {
            "states": len(subset),
            "one_step_recoverable_states": sum(
                row["one_step_exit_capacity_recoverable"]
                for row in subset
            ),
        }

    first_recoverable = recoverable[0] if recoverable else None
    return {
        "zero_interval_id": interval["zero_interval_id"],
        "seed": interval["seed"],
        "cohort": interval["cohort"],
        "interval_class": interval["interval_class"],
        "start_state_turn": rows[0]["state_turn"],
        "end_state_turn": rows[-1]["state_turn"],
        "audited_visible_hand_states": len(rows),
        "canonical_recovered": interval["canonical_recovered"],
        "recovery_phase": interval["recovery_phase"],
        "recovered_at_action_turn": interval[
            "recovered_at_action_turn"
        ],
        "exit_seen_at_interval_start": rows[0]["exit_ever_seen"],
        "exit_seen_at_interval_end": rows[-1]["exit_ever_seen"],
        "exit_visible_at_interval_start": rows[0][
            "exit_currently_visible"
        ],
        "exit_visible_at_interval_end": rows[-1][
            "exit_currently_visible"
        ],
        "states_one_step_recoverable": len(recoverable),
        "fraction_states_one_step_recoverable": (
            len(recoverable) / len(rows)
        ),
        "first_one_step_recoverable_state": (
            None
            if first_recoverable is None
            else {
                "state_id": first_recoverable["state_id"],
                "state_turn": first_recoverable["state_turn"],
                "refresh_index": first_recoverable[
                    "refresh_index"
                ],
                "restoring_score_gap": first_recoverable[
                    "restoring_score_gap"
                ],
            }
        ),
        "restoring_score_gap_distribution": distribution(gaps),
        "states_where_restoring_move_is_global_best": sum(
            row["any_restoring_move_in_actual_global_best_set"]
            for row in rows
        ),
        "canonical_restoring_move_selection_count": sum(
            row["canonical_chosen_move_is_restoring"]
            for row in rows
        ),
        "recovery_deferral_count": sum(
            row["recovery_deferral"] for row in rows
        ),
        "visibility_strata": strata,
        "interval_termination": interval["interval_termination"],
        "canonical_recovery_move": interval[
            "canonical_recovery_move"
        ],
        "state_ids": [row["state_id"] for row in rows],
    }


def close_interval(
    interval,
    *,
    recovered,
    recovery_phase,
    recovered_at_action_turn,
    interval_termination,
    canonical_recovery_move,
):
    interval["canonical_recovered"] = recovered
    interval["recovery_phase"] = recovery_phase
    interval["recovered_at_action_turn"] = recovered_at_action_turn
    interval["interval_termination"] = interval_termination
    interval["canonical_recovery_move"] = canonical_recovery_move


def trace_seed(seed, deck, canonical_final):
    policy = BoundedMergeV4Policy(setup_weight=SETUP_WEIGHT)
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )

    cohort = cohort_for(seed)
    ever_seen = False
    refresh_count = 0
    hand_generation_index = 0
    visible_state_index = 0
    interval_serial = 0
    active_interval = None
    intervals = []
    zero_state_records = []

    for _ in range(1000):
        current_visible = any(card.is_exit for card in state.hand)
        if current_visible:
            ever_seen = True

        if state.won:
            if active_interval is not None:
                close_interval(
                    active_interval,
                    recovered=False,
                    recovery_phase="never",
                    recovered_at_action_turn=None,
                    interval_termination="win_without_capacity_recovery",
                    canonical_recovery_move=None,
                )
                active_interval = None
            result = final_record(state, "win")
            break
        if state.board.open_tunnels == 0:
            if active_interval is not None:
                close_interval(
                    active_interval,
                    recovered=False,
                    recovery_phase="never",
                    recovered_at_action_turn=None,
                    interval_termination=(
                        "closed_tunnels_conditions_failed"
                    ),
                    canonical_recovery_move=None,
                )
                active_interval = None
            result = final_record(
                state, "closed_tunnels_conditions_failed"
            )
            break
        if not state.hand and not state.draw_pile:
            if active_interval is not None:
                close_interval(
                    active_interval,
                    recovered=False,
                    recovery_phase="never",
                    recovered_at_action_turn=None,
                    interval_termination="deck_exhausted",
                    canonical_recovery_move=None,
                )
                active_interval = None
            result = final_record(state, "deck_exhausted")
            break

        moves = state.legal_moves()
        scored_rows = []
        chosen_row = None
        if moves:
            for move in moves:
                features = move_features(state, move)
                score = score_features(features, policy.weights)
                scored_rows.append((move, features, score))
            best_score = max(row[2] for row in scored_rows)
            best_rows = [
                row for row in scored_rows
                if row[2] == best_score
            ]
            chosen_row = rng.choice(best_rows)

        capacity = (
            None
            if state.exit_placed
            else exit_capacity(state.board, deck.exit_card)
        )

        if (
            capacity is not None
            and capacity["exit_legal_move_count"] == 0
        ):
            if active_interval is None:
                interval_serial += 1
                active_interval = {
                    "zero_interval_id": (
                        f"{seed}:zero:{interval_serial}"
                    ),
                    "seed": seed,
                    "cohort": cohort,
                    "state_record_indices": [],
                    "canonical_recovered": None,
                    "recovery_phase": None,
                    "recovered_at_action_turn": None,
                    "interval_termination": None,
                    "canonical_recovery_move": None,
                    "interval_class": None,
                }
                intervals.append(active_interval)

            visible_state_index += 1
            record = audit_zero_state(
                seed=seed,
                cohort=cohort,
                interval_id=active_interval[
                    "zero_interval_id"
                ],
                state=state,
                exit_card=deck.exit_card,
                policy=policy,
                moves=moves,
                scored_rows=scored_rows,
                chosen_row=chosen_row,
                visible_state_index=visible_state_index,
                hand_generation_index=hand_generation_index,
                refresh_count=refresh_count,
                ever_seen=ever_seen,
                current_visible=current_visible,
            )
            active_interval["state_record_indices"].append(
                len(zero_state_records)
            )
            zero_state_records.append(record)
        else:
            assert active_interval is None

        if not moves:
            if state.refresh_unplayable_hand():
                refresh_count += 1
                hand_generation_index += 1
                if any(card.is_exit for card in state.hand):
                    ever_seen = True
                continue
            if active_interval is not None:
                close_interval(
                    active_interval,
                    recovered=False,
                    recovery_phase="never",
                    recovered_at_action_turn=None,
                    interval_termination="terminal_no_legal_move",
                    canonical_recovery_move=None,
                )
                active_interval = None
            result = final_record(state, "no_legal_move")
            break

        chosen_move, _, _ = chosen_row
        action_turn = state.turns + 1
        before_zero = (
            capacity is not None
            and capacity["exit_legal_move_count"] == 0
        )
        chosen_sig = move_signature(state, chosen_move)
        visible_before = current_visible
        seen_before = ever_seen

        state.apply(chosen_move)
        hand_generation_index += 1
        if any(card.is_exit for card in state.hand):
            ever_seen = True

        if (
            before_zero
            and not state.exit_placed
            and exit_capacity(
                state.board, deck.exit_card
            )["exit_legal_move_count"] > 0
        ):
            assert active_interval is not None
            recovery_phase = (
                "before_exit_sighting"
                if not seen_before
                else (
                    "while_exit_visible"
                    if visible_before
                    else "after_seen_not_visible"
                )
            )
            close_interval(
                active_interval,
                recovered=True,
                recovery_phase=recovery_phase,
                recovered_at_action_turn=action_turn,
                interval_termination="canonical_recovery_move",
                canonical_recovery_move=chosen_sig,
            )
            active_interval = None

    else:
        result = final_record(state, "step_limit")

    if result != canonical_final:
        return {
            "seed": seed,
            "cohort": cohort,
            "match": False,
            "canonical_final": canonical_final,
            "instrumented_final": result,
        }

    assert active_interval is None
    for interval in intervals:
        assert interval["canonical_recovered"] is not None

    if seed in CLASS_A:
        unrecovered = [
            interval for interval in intervals
            if not interval["canonical_recovered"]
        ]
        assert len(unrecovered) == 1
        assert intervals[-1] is unrecovered[0]
        for interval in intervals[:-1]:
            assert interval["canonical_recovered"]
            interval["interval_class"] = (
                "earlier_recovered_class_a"
            )
        intervals[-1]["interval_class"] = (
            "persistent_class_a"
        )
    elif seed in WIN_ZERO:
        assert intervals
        assert all(
            interval["canonical_recovered"]
            for interval in intervals
        )
        for interval in intervals:
            interval["interval_class"] = "winning_recovered"
    else:
        assert seed in WIN_ALWAYS_POSITIVE
        assert intervals == []

    interval_summaries = [
        summarize_interval(interval, zero_state_records)
        for interval in intervals
    ]
    interval_recovery_by_id = {
        row["zero_interval_id"]: row["canonical_recovered"]
        for row in interval_summaries
    }
    for row in zero_state_records:
        row["zero_interval_canonical_recovered"] = (
            interval_recovery_by_id[row["zero_interval_id"]]
        )

    return {
        "seed": seed,
        "cohort": cohort,
        "match": True,
        "final": result,
        "refresh_count": refresh_count,
        "zero_state_records": zero_state_records,
        "interval_summaries": interval_summaries,
    }


def aggregate_intervals(intervals, state_records):
    ids = {row["zero_interval_id"] for row in intervals}
    states = [
        row for row in state_records
        if row["zero_interval_id"] in ids
    ]
    recoverable_states = [
        row for row in states
        if row["one_step_exit_capacity_recoverable"]
    ]
    interval_min_gaps = [
        row["restoring_score_gap_distribution"]["minimum"]
        for row in intervals
        if row["restoring_score_gap_distribution"]["minimum"]
        is not None
    ]
    state_gaps = [
        row["restoring_score_gap"]
        for row in recoverable_states
        if row["restoring_score_gap"] is not None
    ]

    strata = {}
    for label in ("pre_seen", "seen_visible", "seen_not_currently_visible"):
        subset = [
            row for row in states
            if visibility_stratum(row) == label
        ]
        strata[label] = {
            "states": len(subset),
            "one_step_recoverable_states": sum(
                row["one_step_exit_capacity_recoverable"]
                for row in subset
            ),
            "recovery_deferrals": sum(
                row["recovery_deferral"] for row in subset
            ),
        }

    return {
        "interval_count": len(intervals),
        "state_count": len(states),
        "intervals_with_any_one_step_restoring_move": sum(
            row["states_one_step_recoverable"] > 0
            for row in intervals
        ),
        "one_step_recoverable_state_count": len(
            recoverable_states
        ),
        "fraction_states_one_step_recoverable": (
            len(recoverable_states) / len(states)
            if states else None
        ),
        "intervals_where_restoring_move_is_ever_global_best": sum(
            row["states_where_restoring_move_is_global_best"] > 0
            for row in intervals
        ),
        "interval_minimum_restoring_gap_distribution": (
            distribution(interval_min_gaps)
        ),
        "recoverable_state_score_gap_distribution": (
            distribution(state_gaps)
        ),
        "recovery_deferral_count": sum(
            row["recovery_deferral"] for row in states
        ),
        "canonical_recovery_selection_count": sum(
            row["canonical_restoring_move_selection_count"]
            for row in intervals
        ),
        "visibility_strata": strata,
    }


def restoring_move_type_summary(state_records):
    labels = {}
    best_move_records = []
    for row in state_records:
        for move in row["best_restoring_moves"]:
            best_move_records.append({
                "state_id": row["state_id"],
                "seed": row["seed"],
                "zero_interval_id": row["zero_interval_id"],
                **move,
            })
            for label in move["move_type_labels"]:
                labels[label] = labels.get(label, 0) + 1
    return {
        "best_restoring_move_record_count": len(
            best_move_records
        ),
        "label_counts": dict(sorted(labels.items())),
        "best_restoring_move_records": best_move_records,
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
        f"EXIT_REVERSIBILITY_RECEIPT_CHUNK_COUNT={len(chunks)}"
    )
    for index, chunk in enumerate(chunks):
        print(
            f"EXIT_REVERSIBILITY_RECEIPT_CHUNK_{index:04d}={chunk}"
        )


def main():
    canonical_source = json.loads(
        CANONICAL_RECEIPT.read_text(encoding="utf-8")
    )
    worker7 = json.loads(
        WORKER7_RECEIPT.read_text(encoding="utf-8")
    )
    canonical = canonical_source[
        "canonical_per_seed_final_records"
    ][POLICY_NAME]

    assert worker7[
        "audited_cohorts"
    ]["class_a_never_legally_placeable"] == CLASS_A
    assert worker7[
        "winner_control_summary"
    ]["zero_capacity_before_placement_seeds"] == WIN_ZERO
    assert sorted(
        set(
            worker7["audited_cohorts"]["canonical_v4_wins"]
        ) - set(WIN_ZERO)
    ) == WIN_ALWAYS_POSITIVE

    deck = load_real_deck(ROOT / "data")
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
            "experiment": "v4-exit-capacity-reversibility-audit",
            "date": "2026-09-23",
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

    zero_states = [
        state
        for trace in traces
        for state in trace["zero_state_records"]
    ]
    intervals = [
        interval
        for trace in traces
        for interval in trace["interval_summaries"]
    ]

    persistent = [
        row for row in intervals
        if row["interval_class"] == "persistent_class_a"
    ]
    earlier = [
        row for row in intervals
        if row["interval_class"]
        == "earlier_recovered_class_a"
    ]
    winning = [
        row for row in intervals
        if row["interval_class"] == "winning_recovered"
    ]
    assert len(persistent) == 18
    assert len(earlier) == 12
    assert len(winning) == 5

    persistent_cmp = aggregate_intervals(
        persistent, zero_states
    )
    earlier_cmp = aggregate_intervals(earlier, zero_states)
    winning_cmp = aggregate_intervals(winning, zero_states)

    always_positive = [
        {
            "seed": trace["seed"],
            "final": trace["final"],
            "zero_interval_count": len(
                trace["interval_summaries"]
            ),
        }
        for trace in traces
        if trace["seed"] in WIN_ALWAYS_POSITIVE
    ]
    assert all(
        row["zero_interval_count"] == 0
        for row in always_positive
    )

    payload = {
        "experiment": "v4-exit-capacity-reversibility-audit",
        "date": "2026-09-23",
        "branch": "bootstrap/model-foundation",
        "dataset_status": (
            "already-spent / development / diagnostic / "
            "non-confirmatory"
        ),
        "fresh_seeds_used": False,
        "orchestrator_decision": (
            "https://github.com/carabinshely/"
            "bandido-alcatraz-solve/issues/2"
            "#issuecomment-5789888769"
        ),
        "source_receipts": [
            "experiments/real-deck-policy-v4/"
            "canonical-mechanism-replay-2026-09-22.json",
            "experiments/real-deck-policy-v4/"
            "exit-placement-capacity-audit-2026-09-22.json",
        ],
        "fixed_model": {
            "policy": (
                "BoundedMergeV4Policy(setup_weight=250)"
            ),
            "deck_file": "data/deck-v1.json",
            "exit_geometry_source": (
                "data/deck-observations-v0.json"
            ),
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
        },
        "cohort_definitions": {
            "class_a_failures": CLASS_A,
            "winning_zero_capacity_controls": WIN_ZERO,
            "winning_always_positive_controls": (
                WIN_ALWAYS_POSITIVE
            ),
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
        "state_semantics": {
            "one_step_exit_capacity_recoverable": (
                "At least one currently legal move from the "
                "current visible hand, applied once to a "
                "geometry-only clone with no future draw "
                "contents inspected, results in positive "
                "EXIT legal-move capacity."
            ),
            "refresh_visibility_rule": (
                "A refresh that keeps the board/state turn "
                "unchanged but changes the visible hand is "
                "recorded as a new auditable visible state."
            ),
            "no_multi_step_search": True,
        },
        "per_state_zero_capacity_audit": zero_states,
        "per_interval_summaries": intervals,
        "cohort_comparison": {
            "persistent_class_a": persistent_cmp,
            "earlier_recovered_class_a": earlier_cmp,
            "winning_recovered": winning_cmp,
        },
        "always_positive_winner_controls": always_positive,
        "restoring_move_type_summary": (
            restoring_move_type_summary(zero_states)
        ),
        "per_seed_compact": [
            {
                "seed": trace["seed"],
                "cohort": trace["cohort"],
                "final": trace["final"],
                "refresh_count": trace["refresh_count"],
                "zero_interval_count": len(
                    trace["interval_summaries"]
                ),
                "zero_state_count": len(
                    trace["zero_state_records"]
                ),
            }
            for trace in traces
        ],
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
        "persistent": persistent_cmp,
        "earlier_recovered": earlier_cmp,
        "winning_recovered": winning_cmp,
        "always_positive_winners": always_positive,
        "interval_counts": {
            "persistent_class_a": len(persistent),
            "earlier_recovered_class_a": len(earlier),
            "winning_recovered": len(winning),
        },
        "zero_state_count": len(zero_states),
    }
    print(
        "EXIT_REVERSIBILITY_AUDIT_SUMMARY="
        + json.dumps(summary, sort_keys=True)
    )
    emit_chunks(payload)


if __name__ == "__main__":
    main()
