import json
from collections import Counter, defaultdict
from pathlib import Path
from random import Random
from statistics import mean, median

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import move_features, score_features


ROOT = Path(__file__).parents[1]
SEEDS = range(2000, 2400)
SOURCE_RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v4"
    / "canonical-mechanism-replay-2026-09-22.json"
)
POLICY_NAME = "bounded_merge_v4_250"
SETUP_WEIGHT = 250
PHASES = ("pre_seen", "seen_unplaced", "post_placed")


def move_signature(state, move):
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def final_record(state, reason):
    equipment_ready = is_equipment_ready(state.raincoats, state.ropes)
    return {
        "won": state.won,
        "failure_reason": reason,
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


def attachment_count(state, move):
    if move.action is not Action.PLACE or move.origin is None:
        return 0
    rotated = state.hand[move.hand_index].rotated(move.quarter_turns)
    targets = state.board.open_tunnel_target_counts
    total = 0
    for cell in rotated.cells:
        coord = (move.origin[0] + cell.x, move.origin[1] + cell.y)
        total += targets.get(coord, 0)
    return total


def empty_phase():
    return {
        "entered": False,
        "actions": 0,
        "positive_setup_events": 0,
        "total_bounded_setup_gain": 0,
        "total_setup_score_contribution": 0,
        "branching_events": 0,
        "branching_open_growth": 0,
        "consolidation_events": 0,
        "consolidation_open_reduction": 0,
        "flat_events": 0,
        "net_open_delta": 0,
        "multi_attachment_count": 0,
        "max_frontier_state": None,
        "legal_exit_deferral_count": 0,
        "refresh_count": 0,
        "visible_to_not_visible_refresh_transitions": 0,
        "not_visible_to_visible_refresh_transitions": 0,
        "setup_positive_branch_count": 0,
        "setup_positive_branch_growth": 0,
        "setup_zero_branch_count": 0,
        "setup_zero_branch_growth": 0,
        "audited_decisions": 0,
        "gate_sensitive_decisions": 0,
        "best_set_changed_decisions": 0,
        "gate_sensitive_branching_decisions": 0,
        "gate_sensitive_consolidation_decisions": 0,
        "gate_sensitive_legal_exit_deferral_decisions": 0,
        "first_gate_sensitive_action_turn": None,
    }


def classify_phase(state, ever_seen):
    visible = any(card.is_exit for card in state.hand)
    if state.exit_placed:
        return "post_placed", None, visible
    if ever_seen or visible:
        return (
            "seen_unplaced",
            "currently_visible" if visible else "seen_not_currently_visible",
            visible,
        )
    return "pre_seen", None, visible


def trace_seed(seed, deck):
    policy = BoundedMergeV4Policy(setup_weight=SETUP_WEIGHT)
    assert policy.weights.bounded_merge_setup_gain == SETUP_WEIGHT

    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )

    ever_seen = False
    first_exit_seen_state_turn = None
    exit_placement_action_turn = None
    first_frontier_gt10_state_turn = None
    terminal_exit_state = None
    phase = {name: empty_phase() for name in PHASES}
    action_records = []
    sensitivity_records = []

    for _ in range(1000):
        current_visible = any(card.is_exit for card in state.hand)
        if current_visible and not ever_seen:
            ever_seen = True
            first_exit_seen_state_turn = state.turns

        lifecycle, visibility_substate, current_visible = classify_phase(
            state, ever_seen
        )
        p = phase[lifecycle]
        p["entered"] = True
        frontier = state.board.open_tunnels
        p["max_frontier_state"] = (
            frontier
            if p["max_frontier_state"] is None
            else max(p["max_frontier_state"], frontier)
        )
        if frontier > 10 and first_frontier_gt10_state_turn is None:
            first_frontier_gt10_state_turn = state.turns

        if state.won:
            result = final_record(state, "win")
            break
        if frontier == 0:
            result = final_record(
                state, "closed_tunnels_conditions_failed"
            )
            break
        if not state.hand and not state.draw_pile:
            result = final_record(state, "deck_exhausted")
            break

        moves = state.legal_moves()
        if not moves:
            before_visible = current_visible
            before_phase = lifecycle
            if state.refresh_unplayable_hand():
                phase[before_phase]["refresh_count"] += 1
                after_visible = any(card.is_exit for card in state.hand)
                if before_phase == "seen_unplaced":
                    if before_visible and not after_visible:
                        phase[before_phase][
                            "visible_to_not_visible_refresh_transitions"
                        ] += 1
                    elif not before_visible and after_visible:
                        phase[before_phase][
                            "not_visible_to_visible_refresh_transitions"
                        ] += 1
                if after_visible and not ever_seen:
                    ever_seen = True
                    first_exit_seen_state_turn = state.turns
                continue

            if state.exit_placed:
                terminal_exit_state = "already_placed"
            elif current_visible:
                terminal_exit_state = "visible_unplayable"
            elif ever_seen:
                terminal_exit_state = "seen_not_currently_visible"
            else:
                terminal_exit_state = "not_seen"
            result = final_record(state, "no_legal_move")
            break

        scored = []
        legal_exit_available = False
        for move in moves:
            card = state.hand[move.hand_index]
            if move.action is Action.PLACE and card.is_exit:
                legal_exit_available = True
            features = move_features(state, move)
            actual_score = score_features(features, policy.weights)
            hypothetical_score = (
                actual_score
                - features.bounded_merge_setup_gain * SETUP_WEIGHT
            )
            scored.append(
                (move, features, actual_score, hypothetical_score)
            )

        actual_max = max(row[2] for row in scored)
        hypothetical_max = max(row[3] for row in scored)
        actual_best = [row for row in scored if row[2] == actual_max]
        hypothetical_best = [
            row for row in scored if row[3] == hypothetical_max
        ]
        move, features, actual_score, hypothetical_score = rng.choice(
            actual_best
        )
        actual_best_moves = {row[0] for row in actual_best}
        hypothetical_best_moves = {row[0] for row in hypothetical_best}
        chosen_in_hypothetical = move in hypothetical_best_moves
        best_set_changed = actual_best_moves != hypothetical_best_moves
        gate_sensitive = not chosen_in_hypothetical

        card = state.hand[move.hand_index]
        chosen_exit = move.action is Action.PLACE and card.is_exit
        defers_legal_exit = legal_exit_available and not chosen_exit

        before_open = state.board.open_tunnels
        before_merge = state.board.merge_opportunities
        attachments = attachment_count(state, move)
        action_turn = state.turns + 1

        state.apply(move)

        after_open = state.board.open_tunnels
        after_merge = state.board.merge_opportunities
        open_delta = after_open - before_open
        merge_delta = after_merge - before_merge
        topology_event = (
            "branching"
            if open_delta > 0
            else "consolidation"
            if open_delta < 0
            else "flat"
        )

        p["actions"] += 1
        p["total_bounded_setup_gain"] += features.bounded_merge_setup_gain
        p["total_setup_score_contribution"] += (
            features.bounded_merge_setup_gain * SETUP_WEIGHT
        )
        if features.bounded_merge_setup_gain > 0:
            p["positive_setup_events"] += 1

        if topology_event == "branching":
            p["branching_events"] += 1
            p["branching_open_growth"] += open_delta
            if features.bounded_merge_setup_gain > 0:
                p["setup_positive_branch_count"] += 1
                p["setup_positive_branch_growth"] += open_delta
            else:
                p["setup_zero_branch_count"] += 1
                p["setup_zero_branch_growth"] += open_delta
        elif topology_event == "consolidation":
            p["consolidation_events"] += 1
            p["consolidation_open_reduction"] += -open_delta
        else:
            p["flat_events"] += 1

        p["net_open_delta"] += open_delta
        if attachments >= 2:
            p["multi_attachment_count"] += 1
        if defers_legal_exit:
            p["legal_exit_deferral_count"] += 1

        if lifecycle in ("seen_unplaced", "post_placed"):
            p["audited_decisions"] += 1
            if gate_sensitive:
                p["gate_sensitive_decisions"] += 1
                if p["first_gate_sensitive_action_turn"] is None:
                    p["first_gate_sensitive_action_turn"] = action_turn
                if topology_event == "branching":
                    p["gate_sensitive_branching_decisions"] += 1
                elif topology_event == "consolidation":
                    p["gate_sensitive_consolidation_decisions"] += 1
                if defers_legal_exit:
                    p[
                        "gate_sensitive_legal_exit_deferral_decisions"
                    ] += 1
            if best_set_changed:
                p["best_set_changed_decisions"] += 1

        event = {
            "action_turn": action_turn,
            "phase": lifecycle,
            "seen_unplaced_visibility_substate": visibility_substate,
            "action": move.action.value,
            "card_id": card.card_id,
            "before_open_tunnels": before_open,
            "after_open_tunnels": after_open,
            "open_delta": open_delta,
            "before_merge_opportunities": before_merge,
            "after_merge_opportunities": after_merge,
            "merge_opportunity_delta": merge_delta,
            "bounded_merge_setup_gain": features.bounded_merge_setup_gain,
            "bounded_setup_score_contribution": (
                features.bounded_merge_setup_gain * SETUP_WEIGHT
            ),
            "attachment_count": attachments,
            "exit_currently_visible": current_visible,
            "legal_exit_placement_exists": legal_exit_available,
            "chosen_move_is_exit": chosen_exit,
            "defers_available_legal_exit": defers_legal_exit,
            "topology_event": topology_event,
        }
        if lifecycle in ("seen_unplaced", "post_placed"):
            audit = {
                "actual_chosen_score": actual_score,
                "hypothetical_chosen_score": hypothetical_score,
                "actual_max_score": actual_max,
                "hypothetical_max_score": hypothetical_max,
                "actual_best_candidate_set_size": len(actual_best),
                "hypothetical_best_candidate_set_size": len(
                    hypothetical_best
                ),
                "chosen_remains_in_hypothetical_best_set": (
                    chosen_in_hypothetical
                ),
                "best_candidate_set_changed": best_set_changed,
                "gate_sensitive": gate_sensitive,
            }
            event["score_audit"] = audit
            if gate_sensitive or best_set_changed:
                sensitivity_records.append({
                    **event,
                    "chosen_move": move_signature(
                        GameState(
                            board=state.board.clone(),
                            draw_pile=[],
                            hand=[card],
                        ),
                        Action.PLACE if False else move,
                    )
                    if False
                    else {
                        "action": move.action.value,
                        "card_id": card.card_id,
                        "origin": (
                            list(move.origin)
                            if move.origin is not None
                            else None
                        ),
                        "quarter_turns": move.quarter_turns,
                    },
                })

        action_records.append(event)
        p["max_frontier_state"] = max(
            p["max_frontier_state"], after_open
        )

        if chosen_exit:
            exit_placement_action_turn = action_turn

    else:
        result = final_record(state, "step_limit")

    first_sensitive_turn = None
    for record in sensitivity_records:
        if record["score_audit"]["gate_sensitive"]:
            turn = record["action_turn"]
            first_sensitive_turn = (
                turn
                if first_sensitive_turn is None
                else min(first_sensitive_turn, turn)
            )

    first_sensitive_relative = None
    if first_sensitive_turn is not None:
        first_sensitive_relative = {
            "action_turn": first_sensitive_turn,
            "relative_to_first_exit_seen_state_turn": (
                None
                if first_exit_seen_state_turn is None
                else first_sensitive_turn - first_exit_seen_state_turn
            ),
            "relative_to_exit_placement_action_turn": (
                None
                if exit_placement_action_turn is None
                else first_sensitive_turn - exit_placement_action_turn
            ),
            "relative_to_first_frontier_gt10_state_turn": (
                None
                if first_frontier_gt10_state_turn is None
                else (
                    first_sensitive_turn
                    - first_frontier_gt10_state_turn
                )
            ),
        }

    return {
        "final": result,
        "terminal_no_legal_move_exit_state": terminal_exit_state,
        "first_exit_seen_state_turn": first_exit_seen_state_turn,
        "exit_placement_action_turn": exit_placement_action_turn,
        "first_frontier_gt10_state_turn": first_frontier_gt10_state_turn,
        "phases": phase,
        "first_gate_sensitive_relative": first_sensitive_relative,
        "sensitivity_records": sensitivity_records,
        "_action_records": action_records,
    }


def aggregate_phase(seed_ids, traces, phase_name):
    rows = [traces[str(seed)] for seed in seed_ids]
    phase_rows = [row["phases"][phase_name] for row in rows]
    entered = [p for p in phase_rows if p["entered"]]
    maxima = [
        p["max_frontier_state"]
        for p in entered
        if p["max_frontier_state"] is not None
    ]

    setup_positive_branches = sum(
        p["setup_positive_branch_count"] for p in phase_rows
    )
    setup_zero_branches = sum(
        p["setup_zero_branch_count"] for p in phase_rows
    )
    setup_positive_growth = sum(
        p["setup_positive_branch_growth"] for p in phase_rows
    )
    setup_zero_growth = sum(
        p["setup_zero_branch_growth"] for p in phase_rows
    )
    branch_count = setup_positive_branches + setup_zero_branches
    branch_growth = setup_positive_growth + setup_zero_growth

    return {
        "seeds_in_group": len(seed_ids),
        "seeds_entering_phase": len(entered),
        "seeds_with_positive_setup": sum(
            p["positive_setup_events"] > 0 for p in phase_rows
        ),
        "positive_setup_event_count": sum(
            p["positive_setup_events"] for p in phase_rows
        ),
        "total_bounded_setup_gain": sum(
            p["total_bounded_setup_gain"] for p in phase_rows
        ),
        "total_setup_score_contribution": sum(
            p["total_setup_score_contribution"] for p in phase_rows
        ),
        "branching_event_count": sum(
            p["branching_events"] for p in phase_rows
        ),
        "total_positive_open_growth": sum(
            p["branching_open_growth"] for p in phase_rows
        ),
        "consolidation_event_count": sum(
            p["consolidation_events"] for p in phase_rows
        ),
        "total_open_reduction": sum(
            p["consolidation_open_reduction"] for p in phase_rows
        ),
        "flat_event_count": sum(p["flat_events"] for p in phase_rows),
        "net_chosen_move_open_delta": sum(
            p["net_open_delta"] for p in phase_rows
        ),
        "multi_attachment_count": sum(
            p["multi_attachment_count"] for p in phase_rows
        ),
        "maximum_frontier_reached": max(maxima) if maxima else None,
        "mean_per_seed_maximum_frontier": (
            mean(maxima) if maxima else None
        ),
        "median_per_seed_maximum_frontier": (
            median(maxima) if maxima else None
        ),
        "legal_exit_deferral_count": sum(
            p["legal_exit_deferral_count"] for p in phase_rows
        ),
        "refresh_count": sum(
            p["refresh_count"] for p in phase_rows
        ),
        "visible_to_not_visible_refresh_transitions": sum(
            p["visible_to_not_visible_refresh_transitions"]
            for p in phase_rows
        ),
        "not_visible_to_visible_refresh_transitions": sum(
            p["not_visible_to_visible_refresh_transitions"]
            for p in phase_rows
        ),
        "setup_vs_branching": {
            "setup_positive_branch_count": setup_positive_branches,
            "setup_positive_branch_growth": setup_positive_growth,
            "setup_zero_branch_count": setup_zero_branches,
            "setup_zero_branch_growth": setup_zero_growth,
            "fraction_branching_events_setup_positive": (
                setup_positive_branches / branch_count
                if branch_count
                else None
            ),
            "fraction_open_growth_setup_positive": (
                setup_positive_growth / branch_growth
                if branch_growth
                else None
            ),
        },
        "gate_sensitivity": {
            "decisions_audited": sum(
                p["audited_decisions"] for p in phase_rows
            ),
            "gate_sensitive_decisions": sum(
                p["gate_sensitive_decisions"] for p in phase_rows
            ),
            "seeds_with_gate_sensitive_decision": sum(
                p["gate_sensitive_decisions"] > 0 for p in phase_rows
            ),
            "best_set_changed_decisions": sum(
                p["best_set_changed_decisions"] for p in phase_rows
            ),
            "gate_sensitive_branching_decisions": sum(
                p["gate_sensitive_branching_decisions"]
                for p in phase_rows
            ),
            "gate_sensitive_consolidation_decisions": sum(
                p["gate_sensitive_consolidation_decisions"]
                for p in phase_rows
            ),
            "gate_sensitive_legal_exit_deferral_decisions": sum(
                p["gate_sensitive_legal_exit_deferral_decisions"]
                for p in phase_rows
            ),
        },
    }


def group_table(seed_ids, traces):
    return {
        phase_name: aggregate_phase(seed_ids, traces, phase_name)
        for phase_name in PHASES
    }


def post_exit_frontier_analysis(trace):
    events = trace["_action_records"]
    placement = next(
        (event for event in events if event["chosen_move_is_exit"]),
        None,
    )
    if placement is None:
        return {
            "exit_placement_action_turn": None,
            "open_immediately_after_exit_placement": None,
            "first_post_placement_state_turn_frontier_gt10": None,
            "post_placement_branching_before_first_gt10": 0,
            "post_placement_setup_positive_branching_before_first_gt10": 0,
            "post_placement_branching_after_first_gt10": 0,
            "post_placement_growth_after_first_gt10": 0,
            "post_placement_branching_with_before_open_gt10": 0,
            "post_placement_growth_with_before_open_gt10": 0,
            "post_placement_setup_positive_branching": 0,
            "post_placement_setup_zero_branching": 0,
            "post_placement_setup_positive_growth": 0,
            "post_placement_setup_zero_growth": 0,
            "harmful_growth_when_setup_structurally_zero": False,
        }

    exit_turn = placement["action_turn"]
    after_exit_open = placement["after_open_tunnels"]

    post = [
        event
        for event in events
        if event["phase"] == "post_placed"
    ]

    first_gt10 = exit_turn if after_exit_open > 10 else None
    if first_gt10 is None:
        for event in post:
            if event["before_open_tunnels"] > 10:
                first_gt10 = event["action_turn"] - 1
                break
            if event["after_open_tunnels"] > 10:
                first_gt10 = event["action_turn"]
                break

    branching = [
        event for event in post if event["topology_event"] == "branching"
    ]
    before_first = [
        event
        for event in branching
        if first_gt10 is None or event["action_turn"] <= first_gt10
    ]
    after_first = [
        event
        for event in branching
        if first_gt10 is not None and event["action_turn"] > first_gt10
    ]
    before_gt10_state = [
        event
        for event in branching
        if event["before_open_tunnels"] > 10
    ]

    setup_positive = [
        event
        for event in branching
        if event["bounded_merge_setup_gain"] > 0
    ]
    setup_zero = [
        event
        for event in branching
        if event["bounded_merge_setup_gain"] == 0
    ]

    return {
        "exit_placement_action_turn": exit_turn,
        "open_immediately_after_exit_placement": after_exit_open,
        "first_post_placement_state_turn_frontier_gt10": first_gt10,
        "post_placement_branching_before_first_gt10": len(before_first),
        "post_placement_setup_positive_branching_before_first_gt10": sum(
            event["bounded_merge_setup_gain"] > 0
            for event in before_first
        ),
        "post_placement_branching_after_first_gt10": len(after_first),
        "post_placement_growth_after_first_gt10": sum(
            event["open_delta"] for event in after_first
        ),
        "post_placement_branching_with_before_open_gt10": len(
            before_gt10_state
        ),
        "post_placement_growth_with_before_open_gt10": sum(
            event["open_delta"] for event in before_gt10_state
        ),
        "post_placement_setup_positive_branching": len(setup_positive),
        "post_placement_setup_zero_branching": len(setup_zero),
        "post_placement_setup_positive_growth": sum(
            event["open_delta"] for event in setup_positive
        ),
        "post_placement_setup_zero_growth": sum(
            event["open_delta"] for event in setup_zero
        ),
        "harmful_growth_when_setup_structurally_zero": bool(
            setup_zero
        ),
    }


def per_seed_gate_summary(seed, trace):
    phases = trace["phases"]
    return {
        "seed": seed,
        "final": trace["final"],
        "terminal_no_legal_move_exit_state": (
            trace["terminal_no_legal_move_exit_state"]
        ),
        "first_exit_seen_state_turn": trace[
            "first_exit_seen_state_turn"
        ],
        "exit_placement_action_turn": trace[
            "exit_placement_action_turn"
        ],
        "first_frontier_gt10_state_turn": trace[
            "first_frontier_gt10_state_turn"
        ],
        "seen_unplaced": phases["seen_unplaced"],
        "post_placed": phases["post_placed"],
        "post_sighting_gate_sensitive_decisions": (
            phases["seen_unplaced"]["gate_sensitive_decisions"]
            + phases["post_placed"]["gate_sensitive_decisions"]
        ),
        "post_sighting_best_set_changed_decisions": (
            phases["seen_unplaced"]["best_set_changed_decisions"]
            + phases["post_placed"]["best_set_changed_decisions"]
        ),
        "first_gate_sensitive_relative": trace[
            "first_gate_sensitive_relative"
        ],
        "post_exit_frontier": post_exit_frontier_analysis(trace),
        "sensitivity_records": trace["sensitivity_records"],
    }


def near_win(row):
    final = row["final"]
    return (
        final["equipment_ready"]
        and final["visible_water"] == 0
        and final["final_open_tunnels"] <= 5
    )


def emit_chunks(payload):
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    )
    size = 18000
    chunks = [
        encoded[index : index + size]
        for index in range(0, len(encoded), size)
    ]
    print(f"EXIT_PHASE_RECEIPT_CHUNK_COUNT={len(chunks)}")
    for index, chunk in enumerate(chunks):
        print(f"EXIT_PHASE_RECEIPT_CHUNK_{index:04d}={chunk}")


def main():
    source = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    canonical = source["canonical_per_seed_final_records"][POLICY_NAME]
    v4_only = source["canonical_paired_groups"]["v4_only_win"]["seed_ids"]
    water_only = source["canonical_paired_groups"][
        "water_space_v3_only_win"
    ]["seed_ids"]
    no_legal = [
        int(seed)
        for seed, row in source["per_seed_mechanism_summaries"][
            POLICY_NAME
        ].items()
        if row["final"]["failure_reason"] == "no_legal_move"
    ]

    deck = load_real_deck(ROOT / "data")
    traces = {}
    mismatches = []
    for seed in SEEDS:
        row = trace_seed(seed, deck)
        traces[str(seed)] = row
        if row["final"] != canonical[str(seed)]:
            mismatches.append({
                "seed": seed,
                "canonical": canonical[str(seed)],
                "instrumented": row["final"],
            })

    if mismatches:
        print(
            "EXIT_PHASE_INTEGRITY_FAILURE="
            + json.dumps(
                {
                    "mismatch_count": len(mismatches),
                    "first_20": mismatches[:20],
                },
                sort_keys=True,
            )
        )
        raise SystemExit(
            "exit-phase instrumentation diverged from canonical V4 finals"
        )

    groups = {
        "v4_only_wins": v4_only,
        "v4_no_legal_move_losses": no_legal,
        "water_space_v3_only_seeds_v4_trajectories": water_only,
    }
    phase_tables = {
        name: group_table(seed_ids, traces)
        for name, seed_ids in groups.items()
    }

    terminal_split = defaultdict(list)
    for seed in no_legal:
        terminal_split[
            traces[str(seed)]["terminal_no_legal_move_exit_state"]
        ].append(seed)
    terminal_phase_tables = {
        terminal: {
            "seed_ids": seed_ids,
            "phase_table": group_table(seed_ids, traces),
        }
        for terminal, seed_ids in sorted(terminal_split.items())
    }

    winner_per_seed = [
        per_seed_gate_summary(seed, traces[str(seed)])
        for seed in v4_only
    ]
    no_legal_per_seed = [
        per_seed_gate_summary(seed, traces[str(seed)])
        for seed in no_legal
    ]
    water_only_per_seed = [
        per_seed_gate_summary(seed, traces[str(seed)])
        for seed in water_only
    ]

    winner_sensitive = [
        row
        for row in winner_per_seed
        if row["post_sighting_gate_sensitive_decisions"] > 0
    ]
    no_legal_sensitive = [
        row
        for row in no_legal_per_seed
        if row["post_sighting_gate_sensitive_decisions"] > 0
    ]
    water_sensitive = [
        row
        for row in water_only_per_seed
        if row["post_sighting_gate_sensitive_decisions"] > 0
    ]

    no_legal_near = [
        seed for seed in no_legal if near_win(traces[str(seed)])
    ]
    no_legal_near_table = group_table(no_legal_near, traces)

    selected_action_records = {
        str(seed): traces[str(seed)]["_action_records"]
        for seed in sorted(set(v4_only + water_only))
    }

    per_seed_phase_summaries = {
        str(seed): {
            "final": traces[str(seed)]["final"],
            "terminal_no_legal_move_exit_state": traces[str(seed)][
                "terminal_no_legal_move_exit_state"
            ],
            "first_exit_seen_state_turn": traces[str(seed)][
                "first_exit_seen_state_turn"
            ],
            "exit_placement_action_turn": traces[str(seed)][
                "exit_placement_action_turn"
            ],
            "first_frontier_gt10_state_turn": traces[str(seed)][
                "first_frontier_gt10_state_turn"
            ],
            "phases": traces[str(seed)]["phases"],
            "first_gate_sensitive_relative": traces[str(seed)][
                "first_gate_sensitive_relative"
            ],
        }
        for seed in SEEDS
    }

    all_sensitivity_records = []
    for seed in SEEDS:
        for record in traces[str(seed)]["sensitivity_records"]:
            all_sensitivity_records.append({
                "seed": seed,
                **record,
            })

    summary = {
        "integrity_gate": {
            "records_compared": 400,
            "exact_matches": 400,
            "mismatches": 0,
            "passed": True,
        },
        "group_seed_ids": groups,
        "phase_tables": phase_tables,
        "terminal_exit_split": {
            key: {
                "count": len(seed_ids),
                "seed_ids": seed_ids,
            }
            for key, seed_ids in sorted(terminal_split.items())
        },
        "terminal_exit_split_phase_tables": terminal_phase_tables,
        "no_legal_near_win_seed_ids": no_legal_near,
        "no_legal_near_win_phase_table": no_legal_near_table,
        "winner_gate_sensitivity": {
            "per_seed": winner_per_seed,
            "seeds_with_post_sighting_gate_sensitive_decision": [
                row["seed"] for row in winner_sensitive
            ],
            "count": len(winner_sensitive),
        },
        "no_legal_gate_sensitivity": {
            "seeds_with_post_sighting_gate_sensitive_decision": [
                row["seed"] for row in no_legal_sensitive
            ],
            "count": len(no_legal_sensitive),
        },
        "water_only_gate_sensitivity": {
            "per_seed": water_only_per_seed,
            "seeds_with_post_sighting_gate_sensitive_decision": [
                row["seed"] for row in water_sensitive
            ],
            "count": len(water_sensitive),
        },
    }
    print(
        "EXIT_PHASE_DIAGNOSTIC_SUMMARY="
        + json.dumps(summary, sort_keys=True)
    )

    payload = {
        "experiment": "v4-exit-phase-diagnostics",
        "date": "2026-09-22",
        "branch": "bootstrap/model-foundation",
        "orchestrator_decision": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5775096836"
        ),
        "dataset_status": (
            "already-spent / development / diagnostic / non-confirmatory"
        ),
        "seed_range": [2000, 2399],
        "fresh_seeds_used": False,
        "canonical_source_receipt": str(
            SOURCE_RECEIPT.relative_to(ROOT)
        ),
        "policy": {
            "class": "BoundedMergeV4Policy",
            "parameters": {"setup_weight": SETUP_WEIGHT},
        },
        "fixed_model": {
            "deck_file": "data/deck-v1.json",
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
        },
        "integrity_gate": summary["integrity_gate"],
        "lifecycle_phase_definitions": {
            "pre_seen": "EXIT has never entered the hand",
            "seen_unplaced": (
                "EXIT has entered the hand at least once and has not been "
                "placed; substate tracks current visibility"
            ),
            "post_placed": "EXIT has already been placed",
            "placement_move_rule": (
                "EXIT placement itself is classified by its pre-action state, "
                "normally seen_unplaced/currently_visible"
            ),
        },
        "event_semantics": {
            "open_delta": "after_open - before_open",
            "branching": "open_delta > 0",
            "consolidation": "open_delta < 0",
            "flat": "open_delta == 0",
            "bounded_setup_score_contribution": (
                "bounded_merge_setup_gain * 250"
            ),
            "gate_sensitive": (
                "historical chosen move is absent from the hypothetical "
                "maximum-score set after removing only bounded setup "
                "contribution for that decision"
            ),
            "best_set_changed": (
                "actual maximum-score move set differs from the hypothetical "
                "maximum-score move set"
            ),
        },
        "group_seed_ids": groups,
        "phase_tables": phase_tables,
        "terminal_exit_split": summary["terminal_exit_split"],
        "terminal_exit_split_phase_tables": terminal_phase_tables,
        "no_legal_near_win_seed_ids": no_legal_near,
        "no_legal_near_win_phase_table": no_legal_near_table,
        "per_seed_phase_summaries": per_seed_phase_summaries,
        "local_score_sensitivity_records": all_sensitivity_records,
        "group_gate_sensitivity_summary": {
            "v4_only_wins": summary["winner_gate_sensitivity"],
            "v4_no_legal_move_losses": summary["no_legal_gate_sensitivity"],
            "water_space_v3_only_seeds_v4_trajectories": summary[
                "water_only_gate_sensitivity"
            ],
        },
        "v4_only_winner_results": winner_per_seed,
        "v4_no_legal_move_results": no_legal_per_seed,
        "water_space_v3_only_seed_v4_results": water_only_per_seed,
        "selected_group_action_records": selected_action_records,
        "answers": {
            "q1": {"pending_interpretation": True},
            "q2": {"pending_interpretation": True},
            "q3": {"pending_interpretation": True},
            "q4": {"pending_interpretation": True},
            "q5": {"pending_interpretation": True},
        },
        "gate_classification": "pending_interpretation",
        "recommended_next_step": None,
    }
    emit_chunks(payload)


if __name__ == "__main__":
    main()
