import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from random import Random
from statistics import mean, median

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, WaterSpaceV3Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import move_features, score_features


ROOT = Path(__file__).parents[1]
SEEDS = range(2000, 2400)


class DiagnosticGreedyPolicy:
    """Behavior-identical weighted-greedy chooser that exposes chosen features."""

    def __init__(self, policy):
        self.weights = policy.weights
        self.last = None

    def choose(self, state, rng):
        moves = state.legal_moves()
        if not moves:
            self.last = {
                "legal_exit_available": False,
                "chosen_features": None,
            }
            return None

        scored = []
        legal_exit_available = False
        for move in moves:
            card = state.hand[move.hand_index]
            if move.action is Action.PLACE and card.is_exit:
                legal_exit_available = True
            features = move_features(state, move)
            scored.append(
                (score_features(features, self.weights), move, features)
            )
        best = max(score for score, _, _ in scored)
        candidates = [
            (move, features)
            for score, move, features in scored
            if score == best
        ]
        move, features = rng.choice(candidates)
        self.last = {
            "legal_exit_available": legal_exit_available,
            "chosen_features": features,
        }
        return move


def final_record_from_state(state, reason):
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
    card = state.hand[move.hand_index].rotated(move.quarter_turns)
    target_counts = state.board.open_tunnel_target_counts
    total = 0
    for cell in card.cells:
        coord = (move.origin[0] + cell.x, move.origin[1] + cell.y)
        total += target_counts.get(coord, 0)
    return total


def trace(policy, seed, deck):
    rng = Random(seed)
    wrapped = DiagnosticGreedyPolicy(policy)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )

    d = {
        "exit_first_enters_hand_state_turn": None,
        "exit_ever_seen": False,
        "first_legal_exit_placement_action_turn": None,
        "exit_placed_action_turn": None,
        "exit_visible_turn_count_before_placement": 0,
        "exit_legal_but_deferred_move_count": 0,
        "first_equipment_ready_state_turn": None,
        "first_water_clear_state_turn": None,
        "first_water_clear_after_water_seen_state_turn": None,
        "first_open_le_10_state_turn": None,
        "first_open_le_5_state_turn": None,
        "first_return_open_le_10_after_exceeding_state_turn": None,
        "first_return_open_le_5_after_exceeding_state_turn": None,
        "min_open_before_exit_first_seen": None,
        "min_open_before_exit_placement": None,
        "max_open_tunnels": 0,
        "max_merge_opportunities": 0,
        "positive_merge_opportunity_delta_move_count": 0,
        "positive_bounded_merge_setup_gain_chosen_move_count": 0,
        "first_positive_bounded_merge_setup_action_turn": None,
        "negative_delta_open_move_count": 0,
        "largest_single_negative_delta_open": 0,
        "consolidation_move_count": 0,
        "multi_attachment_move_count": 0,
        "first_consolidation_action_turn": None,
        "first_consolidation_after_setup_action_turn": None,
        "trapped_water_occurred": False,
        "refresh_count": 0,
        "terminal_no_legal_move_exit_state": None,
        "water_ever_visible": False,
    }

    exit_visible_state_turns = set()
    exceeded_10 = False
    exceeded_5 = False

    def observe_state():
        nonlocal exceeded_10, exceeded_5
        turn = state.turns
        open_tunnels = state.board.open_tunnels
        visible_water = state.board.visible_water_cells
        exit_visible = any(card.is_exit for card in state.hand)

        if not d["exit_ever_seen"]:
            current = d["min_open_before_exit_first_seen"]
            d["min_open_before_exit_first_seen"] = (
                open_tunnels if current is None else min(current, open_tunnels)
            )

        if exit_visible:
            if not d["exit_ever_seen"]:
                d["exit_ever_seen"] = True
                d["exit_first_enters_hand_state_turn"] = turn
            if not state.exit_placed:
                exit_visible_state_turns.add(turn)

        if not state.exit_placed:
            current = d["min_open_before_exit_placement"]
            d["min_open_before_exit_placement"] = (
                open_tunnels if current is None else min(current, open_tunnels)
            )

        if (
            d["first_equipment_ready_state_turn"] is None
            and is_equipment_ready(state.raincoats, state.ropes)
        ):
            d["first_equipment_ready_state_turn"] = turn

        if visible_water > 0:
            d["water_ever_visible"] = True
        if d["first_water_clear_state_turn"] is None and visible_water == 0:
            d["first_water_clear_state_turn"] = turn
        if (
            d["water_ever_visible"]
            and visible_water == 0
            and d["first_water_clear_after_water_seen_state_turn"] is None
        ):
            d["first_water_clear_after_water_seen_state_turn"] = turn

        if d["first_open_le_10_state_turn"] is None and open_tunnels <= 10:
            d["first_open_le_10_state_turn"] = turn
        if d["first_open_le_5_state_turn"] is None and open_tunnels <= 5:
            d["first_open_le_5_state_turn"] = turn

        if open_tunnels > 10:
            exceeded_10 = True
        elif (
            exceeded_10
            and d["first_return_open_le_10_after_exceeding_state_turn"] is None
        ):
            d["first_return_open_le_10_after_exceeding_state_turn"] = turn

        if open_tunnels > 5:
            exceeded_5 = True
        elif (
            exceeded_5
            and d["first_return_open_le_5_after_exceeding_state_turn"] is None
        ):
            d["first_return_open_le_5_after_exceeding_state_turn"] = turn

        d["max_open_tunnels"] = max(d["max_open_tunnels"], open_tunnels)
        d["max_merge_opportunities"] = max(
            d["max_merge_opportunities"],
            state.board.merge_opportunities,
        )
        d["trapped_water_occurred"] = (
            d["trapped_water_occurred"]
            or state.board.trapped_water_cells > 0
        )

    for _ in range(1000):
        observe_state()

        if state.won:
            d["exit_visible_turn_count_before_placement"] = len(
                exit_visible_state_turns
            )
            return {
                "final": final_record_from_state(state, "win"),
                "diagnostics": d,
            }
        if state.board.open_tunnels == 0:
            d["exit_visible_turn_count_before_placement"] = len(
                exit_visible_state_turns
            )
            return {
                "final": final_record_from_state(
                    state, "closed_tunnels_conditions_failed"
                ),
                "diagnostics": d,
            }
        if not state.hand and not state.draw_pile:
            d["exit_visible_turn_count_before_placement"] = len(
                exit_visible_state_turns
            )
            return {
                "final": final_record_from_state(state, "deck_exhausted"),
                "diagnostics": d,
            }

        move = wrapped.choose(state, rng)
        last = wrapped.last
        exit_visible = any(card.is_exit for card in state.hand)

        if (
            last["legal_exit_available"]
            and d["first_legal_exit_placement_action_turn"] is None
        ):
            d["first_legal_exit_placement_action_turn"] = state.turns + 1

        if move is None:
            if state.refresh_unplayable_hand():
                d["refresh_count"] += 1
                continue

            if state.exit_placed:
                exit_state = "already_placed"
            elif exit_visible:
                exit_state = "visible_unplayable"
            elif not d["exit_ever_seen"]:
                exit_state = "not_seen"
            else:
                exit_state = "seen_not_currently_visible"
            d["terminal_no_legal_move_exit_state"] = exit_state
            d["exit_visible_turn_count_before_placement"] = len(
                exit_visible_state_turns
            )
            return {
                "final": final_record_from_state(state, "no_legal_move"),
                "diagnostics": d,
            }

        action_turn = state.turns + 1
        card = state.hand[move.hand_index]
        chosen_exit = move.action is Action.PLACE and card.is_exit
        if last["legal_exit_available"] and not chosen_exit:
            d["exit_legal_but_deferred_move_count"] += 1

        features = last["chosen_features"]
        if features.delta_merge_opportunities > 0:
            d["positive_merge_opportunity_delta_move_count"] += 1
        if features.bounded_merge_setup_gain > 0:
            d["positive_bounded_merge_setup_gain_chosen_move_count"] += 1
            if d["first_positive_bounded_merge_setup_action_turn"] is None:
                d["first_positive_bounded_merge_setup_action_turn"] = action_turn

        attachments = attachment_count(state, move)
        before_open = state.board.open_tunnels

        if chosen_exit:
            d["exit_placed_action_turn"] = action_turn

        state.apply(move)
        after_open = state.board.open_tunnels
        delta_open = after_open - before_open

        if delta_open < 0:
            d["negative_delta_open_move_count"] += 1
            d["largest_single_negative_delta_open"] = min(
                d["largest_single_negative_delta_open"], delta_open
            )
            if move.action is Action.PLACE:
                d["consolidation_move_count"] += 1
                if d["first_consolidation_action_turn"] is None:
                    d["first_consolidation_action_turn"] = action_turn
                if (
                    d["first_positive_bounded_merge_setup_action_turn"] is not None
                    and action_turn
                    > d["first_positive_bounded_merge_setup_action_turn"]
                    and d["first_consolidation_after_setup_action_turn"] is None
                ):
                    d["first_consolidation_after_setup_action_turn"] = action_turn

        if move.action is Action.PLACE and attachments >= 2:
            d["multi_attachment_move_count"] += 1

    observe_state()
    d["exit_visible_turn_count_before_placement"] = len(exit_visible_state_turns)
    return {
        "final": final_record_from_state(state, "step_limit"),
        "diagnostics": d,
    }


def paired_groups(records):
    v4 = records["bounded_merge_v4_250"]
    control = records["water_space_v3"]
    groups = {
        "v4_only_win": [],
        "water_space_v3_only_win": [],
        "both_win": [],
        "both_lose": [],
    }
    for seed in SEEDS:
        key = str(seed)
        a = v4[key]["won"]
        b = control[key]["won"]
        if a and b:
            groups["both_win"].append(seed)
        elif a:
            groups["v4_only_win"].append(seed)
        elif b:
            groups["water_space_v3_only_win"].append(seed)
        else:
            groups["both_lose"].append(seed)
    return groups


def historical_record(row):
    return {
        "won": row["won"],
        "failure_reason": row["reason"],
        "turns": row["turns"],
        "final_open_tunnels": row["final_open_tunnels"],
        "visible_water": row["visible_water"],
        "raincoats": row["raincoats"],
        "ropes": row["ropes"],
        "equipment_ready": row["equipment_ready"],
        "exit_placed": row["exit_placed"],
        "exit_equipment_water_ready": row["exit_equipment_water_ready"],
    }


def historical_delta(canonical, historical):
    final_differences = 0
    won_differences = 0
    by_policy = {}
    for policy_name in ("bounded_merge_v4_250", "water_space_v3"):
        canonical_wins = set()
        historical_wins = set()
        exact_diff = 0
        won_diff = 0
        for seed in SEEDS:
            key = str(seed)
            c = canonical[policy_name][key]
            h = historical_record(
                historical["metrics"][policy_name]["per_seed"][key]
            )
            if c != h:
                exact_diff += 1
                final_differences += 1
            if c["won"] != h["won"]:
                won_diff += 1
                won_differences += 1
            if c["won"]:
                canonical_wins.add(seed)
            if h["won"]:
                historical_wins.add(seed)
        by_policy[policy_name] = {
            "historical_wins": len(historical_wins),
            "canonical_wins": len(canonical_wins),
            "winning_seed_overlap_count": len(
                historical_wins & canonical_wins
            ),
            "historical_winning_seed_ids": sorted(historical_wins),
            "canonical_winning_seed_ids": sorted(canonical_wins),
            "exact_final_record_differences": exact_diff,
            "won_value_differences": won_diff,
        }

    canonical_groups = paired_groups(canonical)
    historical_paired = historical["paired"]
    historical_v4_only = set(historical_paired["v4_only_seed_ids"])
    historical_control_only = set(
        historical_paired["water_space_v3_only_seed_ids"]
    )
    return {
        "final_record_differences_out_of_800": final_differences,
        "won_value_differences_out_of_800": won_differences,
        "by_policy": by_policy,
        "historical_v4_only_remaining_v4_only": sorted(
            historical_v4_only
            & set(canonical_groups["v4_only_win"])
        ),
        "historical_water_space_v3_only_remaining_water_space_v3_only": sorted(
            historical_control_only
            & set(canonical_groups["water_space_v3_only_win"])
        ),
    }


def aggregate_final(records):
    rows = list(records.values())
    wins = [int(seed) for seed, row in records.items() if row["won"]]
    failures = Counter(
        row["failure_reason"] for row in rows if not row["won"]
    )
    return {
        "games": len(rows),
        "wins": len(wins),
        "win_rate": len(wins) / len(rows),
        "winning_seed_ids": wins,
        "failure_reason_counts": dict(sorted(failures.items())),
        "mean_final_open_tunnels": mean(
            row["final_open_tunnels"] for row in rows
        ),
        "median_final_open_tunnels": median(
            row["final_open_tunnels"] for row in rows
        ),
        "final_open_tunnels_le_5": sum(
            row["final_open_tunnels"] <= 5 for row in rows
        ),
        "water_clear": sum(row["visible_water"] == 0 for row in rows),
        "mean_visible_water": mean(row["visible_water"] for row in rows),
        "equipment_ready": sum(row["equipment_ready"] for row in rows),
        "exit_placed": sum(row["exit_placed"] for row in rows),
        "exit_equipment_water_ready": sum(
            row["exit_equipment_water_ready"] for row in rows
        ),
        "step_limit": failures.get("step_limit", 0),
        "mean_turns": mean(row["turns"] for row in rows),
    }


def mean_or_none(values):
    values = [value for value in values if value is not None]
    return mean(values) if values else None


def mechanism_summary(seed_ids, traces, policy_name):
    rows = [traces[policy_name][str(seed)] for seed in seed_ids]
    finals = [row["final"] for row in rows]
    diagnostics = [row["diagnostics"] for row in rows]
    fields = [
        "exit_first_enters_hand_state_turn",
        "first_legal_exit_placement_action_turn",
        "exit_placed_action_turn",
        "exit_visible_turn_count_before_placement",
        "exit_legal_but_deferred_move_count",
        "first_equipment_ready_state_turn",
        "first_water_clear_after_water_seen_state_turn",
        "first_return_open_le_10_after_exceeding_state_turn",
        "first_return_open_le_5_after_exceeding_state_turn",
        "min_open_before_exit_first_seen",
        "min_open_before_exit_placement",
        "max_open_tunnels",
        "max_merge_opportunities",
        "positive_merge_opportunity_delta_move_count",
        "positive_bounded_merge_setup_gain_chosen_move_count",
        "negative_delta_open_move_count",
        "largest_single_negative_delta_open",
        "consolidation_move_count",
        "multi_attachment_move_count",
        "refresh_count",
    ]
    result = {
        "seeds": len(seed_ids),
        "wins": sum(row["won"] for row in finals),
        "exit_ever_seen": sum(d["exit_ever_seen"] for d in diagnostics),
        "exit_legal_ever": sum(
            d["first_legal_exit_placement_action_turn"] is not None
            for d in diagnostics
        ),
        "exit_placed": sum(row["exit_placed"] for row in finals),
        "water_clear_final": sum(row["visible_water"] == 0 for row in finals),
        "equipment_ready_final": sum(
            row["equipment_ready"] for row in finals
        ),
        "compact_final_le_5": sum(
            row["final_open_tunnels"] <= 5 for row in finals
        ),
        "positive_setup_any": sum(
            d["positive_bounded_merge_setup_gain_chosen_move_count"] > 0
            for d in diagnostics
        ),
        "consolidation_any": sum(
            d["consolidation_move_count"] > 0 for d in diagnostics
        ),
        "setup_then_later_consolidation": sum(
            d["first_consolidation_after_setup_action_turn"] is not None
            for d in diagnostics
        ),
        "trapped_water_occurred": sum(
            d["trapped_water_occurred"] for d in diagnostics
        ),
    }
    for field in fields:
        result[f"mean_{field}"] = mean_or_none(
            [d[field] for d in diagnostics]
        )
    return result


def no_legal_move_split(v4_traces):
    rows = [
        v4_traces[str(seed)]
        for seed in SEEDS
        if v4_traces[str(seed)]["final"]["failure_reason"]
        == "no_legal_move"
    ]
    by_exit = defaultdict(list)
    for row in rows:
        by_exit[
            row["diagnostics"]["terminal_no_legal_move_exit_state"]
        ].append(row)

    result = {}
    for exit_state, items in sorted(by_exit.items()):
        cross = defaultdict(int)
        delayed_legal = 0
        for row in items:
            final = row["final"]
            d = row["diagnostics"]
            water = final["visible_water"] == 0
            equipment = final["equipment_ready"]
            compact = final["final_open_tunnels"] <= 5
            cross[
                f"water_{str(water).lower()}__equipment_{str(equipment).lower()}__compact_{str(compact).lower()}"
            ] += 1
            if d["exit_legal_but_deferred_move_count"] > 0:
                delayed_legal += 1
        result[exit_state] = {
            "count": len(items),
            "water_clear": sum(
                row["final"]["visible_water"] == 0 for row in items
            ),
            "equipment_ready": sum(
                row["final"]["equipment_ready"] for row in items
            ),
            "compact_le_5": sum(
                row["final"]["final_open_tunnels"] <= 5 for row in items
            ),
            "water_and_equipment_ready": sum(
                row["final"]["visible_water"] == 0
                and row["final"]["equipment_ready"]
                for row in items
            ),
            "water_equipment_and_compact": sum(
                row["final"]["visible_water"] == 0
                and row["final"]["equipment_ready"]
                and row["final"]["final_open_tunnels"] <= 5
                for row in items
            ),
            "legal_exit_deferred_earlier": delayed_legal,
            "cross_classification": dict(sorted(cross.items())),
            "mean_final_open_tunnels": mean(
                row["final"]["final_open_tunnels"] for row in items
            ),
            "mean_refresh_count": mean(
                row["diagnostics"]["refresh_count"] for row in items
            ),
        }
    return {
        "total": len(rows),
        "by_terminal_exit_state": result,
    }


def classify_exit_never_placed(row):
    d = row["diagnostics"]
    if not d["exit_ever_seen"]:
        return "terminated_before_exit_appeared"
    if d["first_legal_exit_placement_action_turn"] is None:
        return "exit_appeared_but_never_legally_placeable"
    if d["exit_legal_but_deferred_move_count"] > 0:
        return "exit_became_legally_placeable_but_policy_selected_something_else"
    return "another_evidenced_exit_not_placed_path"


def classify_water_space_only_v4_loss(row):
    final = row["final"]
    d = row["diagnostics"]
    if not final["exit_placed"]:
        return classify_exit_never_placed(row)
    if final["failure_reason"] == "no_legal_move":
        return "post_exit_no_legal_move_topology_dead_end"
    if final["failure_reason"] == "closed_tunnels_conditions_failed":
        return "post_exit_closed_tunnels_conditions_failed"
    if final["failure_reason"] == "deck_exhausted":
        if final["visible_water"] > 0:
            return "post_exit_deck_exhausted_with_water_unresolved"
        if not final["equipment_ready"]:
            return "post_exit_deck_exhausted_equipment_unready"
        if final["final_open_tunnels"] > 0:
            return "post_exit_deck_exhausted_open_tunnels_remaining"
    return "another_evidenced_post_exit_failure"


def v4_only_pattern(seed_ids, v4_traces):
    rows = [v4_traces[str(seed)] for seed in seed_ids]
    sequence = 0
    setup_any = 0
    setup_consolidation = 0
    no_setup = 0
    details = []
    for seed, row in zip(seed_ids, rows, strict=True):
        d = row["diagnostics"]
        setup = d["first_positive_bounded_merge_setup_action_turn"]
        consolidation = d["first_consolidation_after_setup_action_turn"]
        exit_turn = d["exit_placed_action_turn"]
        if setup is not None:
            setup_any += 1
        else:
            no_setup += 1
        if setup is not None and consolidation is not None:
            setup_consolidation += 1
        matches = (
            setup is not None
            and consolidation is not None
            and exit_turn is not None
            and setup < consolidation <= exit_turn
        )
        if matches:
            sequence += 1
        details.append({
            "seed": seed,
            "setup_turn": setup,
            "first_consolidation_after_setup_turn": consolidation,
            "exit_placed_turn": exit_turn,
            "sequence_setup_consolidation_exit_win": matches,
            "positive_setup_moves": d[
                "positive_bounded_merge_setup_gain_chosen_move_count"
            ],
            "consolidation_moves": d["consolidation_move_count"],
            "multi_attachment_moves": d["multi_attachment_move_count"],
            "max_open_tunnels": d["max_open_tunnels"],
            "max_merge_opportunities": d["max_merge_opportunities"],
        })
    return {
        "count": len(rows),
        "positive_setup_any": setup_any,
        "no_positive_setup": no_setup,
        "setup_then_later_consolidation": setup_consolidation,
        "setup_consolidation_exit_win_sequence": sequence,
        "per_seed": details,
    }


def compact_side(row):
    final = row["final"]
    d = row["diagnostics"]
    return {
        "won": final["won"],
        "failure_reason": final["failure_reason"],
        "turns": final["turns"],
        "final_open_tunnels": final["final_open_tunnels"],
        "visible_water": final["visible_water"],
        "equipment_ready": final["equipment_ready"],
        "exit_placed": final["exit_placed"],
        "refresh_count": d["refresh_count"],
        "early_topology": {
            "max_open_tunnels": d["max_open_tunnels"],
            "min_open_before_exit_first_seen": d[
                "min_open_before_exit_first_seen"
            ],
            "max_merge_opportunities": d["max_merge_opportunities"],
        },
        "merge_setup": {
            "positive_merge_delta_moves": d[
                "positive_merge_opportunity_delta_move_count"
            ],
            "positive_bounded_setup_moves": d[
                "positive_bounded_merge_setup_gain_chosen_move_count"
            ],
            "first_bounded_setup_turn": d[
                "first_positive_bounded_merge_setup_action_turn"
            ],
        },
        "compaction": {
            "negative_delta_open_moves": d["negative_delta_open_move_count"],
            "largest_single_negative_delta_open": d[
                "largest_single_negative_delta_open"
            ],
            "consolidation_moves": d["consolidation_move_count"],
            "multi_attachment_moves": d["multi_attachment_move_count"],
            "first_consolidation_after_setup_turn": d[
                "first_consolidation_after_setup_action_turn"
            ],
        },
        "water_equipment": {
            "first_water_clear_after_seen_turn": d[
                "first_water_clear_after_water_seen_state_turn"
            ],
            "first_equipment_ready_turn": d[
                "first_equipment_ready_state_turn"
            ],
        },
        "exit": {
            "first_seen_turn": d["exit_first_enters_hand_state_turn"],
            "first_legal_turn": d[
                "first_legal_exit_placement_action_turn"
            ],
            "placed_turn": d["exit_placed_action_turn"],
            "visible_turn_count_before_placement": d[
                "exit_visible_turn_count_before_placement"
            ],
            "legal_but_deferred_moves": d[
                "exit_legal_but_deferred_move_count"
            ],
            "terminal_no_legal_move_state": d[
                "terminal_no_legal_move_exit_state"
            ],
        },
    }


def emit_chunks(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    size = 18000
    chunks = [encoded[i : i + size] for i in range(0, len(encoded), size)]
    print(f"CANONICAL_RECEIPT_CHUNK_COUNT={len(chunks)}")
    for index, chunk in enumerate(chunks):
        print(f"CANONICAL_RECEIPT_CHUNK_{index:04d}={chunk}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-zero", required=True)
    parser.add_argument("--baseline-one", required=True)
    parser.add_argument("--historical-receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    baseline0 = json.loads(Path(args.baseline_zero).read_text())
    baseline1 = json.loads(Path(args.baseline_one).read_text())
    historical = json.loads(Path(args.historical_receipt).read_text())

    records0 = baseline0["records"]
    records1 = baseline1["records"]
    mismatches = []
    for policy_name in ("bounded_merge_v4_250", "water_space_v3"):
        for seed in SEEDS:
            key = str(seed)
            if records0[policy_name][key] != records1[policy_name][key]:
                mismatches.append({
                    "policy": policy_name,
                    "seed": seed,
                    "hash0": records0[policy_name][key],
                    "hash1": records1[policy_name][key],
                })
    if mismatches:
        print("DETERMINISM_GATE_FAILURE=" + json.dumps({
            "mismatch_count": len(mismatches),
            "first_20": mismatches[:20],
        }, sort_keys=True))
        raise SystemExit("post-fix determinism gate failed")

    canonical = records0
    deck = load_real_deck(ROOT / "data")
    policy_objects = {
        "bounded_merge_v4_250": BoundedMergeV4Policy(setup_weight=250),
        "water_space_v3": WaterSpaceV3Policy(),
    }
    traces = {
        "bounded_merge_v4_250": {},
        "water_space_v3": {},
    }
    trace_mismatches = []
    for policy_name, policy in policy_objects.items():
        for seed in SEEDS:
            row = trace(policy, seed, deck)
            traces[policy_name][str(seed)] = row
            if row["final"] != canonical[policy_name][str(seed)]:
                trace_mismatches.append({
                    "policy": policy_name,
                    "seed": seed,
                    "canonical": canonical[policy_name][str(seed)],
                    "instrumented": row["final"],
                })
    if trace_mismatches:
        print("INSTRUMENTATION_GATE_FAILURE=" + json.dumps({
            "mismatch_count": len(trace_mismatches),
            "first_20": trace_mismatches[:20],
        }, sort_keys=True))
        raise SystemExit("instrumented replay diverged from canonical baseline")

    groups = paired_groups(canonical)
    all_seeds = list(SEEDS)
    strata = {
        "all_400": all_seeds,
        "v4_only_win": groups["v4_only_win"],
        "water_space_v3_only_win": groups["water_space_v3_only_win"],
        "both_win": groups["both_win"],
        "both_lose": groups["both_lose"],
    }

    mechanism_strata = {}
    for stratum_name, seed_ids in strata.items():
        mechanism_strata[stratum_name] = {
            policy_name: mechanism_summary(
                seed_ids, traces, policy_name
            )
            for policy_name in (
                "bounded_merge_v4_250",
                "water_space_v3",
            )
        }

    v4_no_legal = no_legal_move_split(traces["bounded_merge_v4_250"])

    v4_exit_never_placed = defaultdict(list)
    for seed in SEEDS:
        row = traces["bounded_merge_v4_250"][str(seed)]
        if not row["final"]["exit_placed"]:
            v4_exit_never_placed[classify_exit_never_placed(row)].append(seed)

    water_only_classifications = []
    for seed in groups["water_space_v3_only_win"]:
        v4_row = traces["bounded_merge_v4_250"][str(seed)]
        water_only_classifications.append({
            "seed": seed,
            "classification": classify_water_space_only_v4_loss(v4_row),
            "v4": compact_side(v4_row),
            "water_space_v3": compact_side(
                traces["water_space_v3"][str(seed)]
            ),
        })

    discordant = []
    for category in ("v4_only_win", "water_space_v3_only_win"):
        for seed in groups[category]:
            discordant.append({
                "seed": seed,
                "category": category,
                "bounded_merge_v4_250": compact_side(
                    traces["bounded_merge_v4_250"][str(seed)]
                ),
                "water_space_v3": compact_side(
                    traces["water_space_v3"][str(seed)]
                ),
            })
    discordant.sort(key=lambda row: row["seed"])

    v4_only_analysis = v4_only_pattern(
        groups["v4_only_win"],
        traces["bounded_merge_v4_250"],
    )

    q1 = {
        "canonical_v4_no_legal_move_losses": v4_no_legal,
        "cases_where_exit_was_legally_playable_earlier_but_deferred": sum(
            row["diagnostics"]["exit_legal_but_deferred_move_count"] > 0
            for row in traces["bounded_merge_v4_250"].values()
            if row["final"]["failure_reason"] == "no_legal_move"
        ),
    }
    q2 = {
        "near_win_state_counts": v4_no_legal,
        "interpretation_pending": True,
    }
    q3 = {
        "canonical_v4_only_wins": v4_only_analysis,
        "interpretation_pending": True,
    }
    q4 = {
        "canonical_water_space_v3_only_wins": water_only_classifications,
        "classification_counts": dict(sorted(Counter(
            row["classification"] for row in water_only_classifications
        ).items())),
        "interpretation_pending": True,
    }

    payload = {
        "experiment": "canonical-post-fix-v4-mechanism-replay",
        "date": "2026-09-22",
        "branch": "bootstrap/model-foundation",
        "orchestrator_decision": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5773389961"
        ),
        "dataset_status": "non-confirmatory / already-spent diagnostic seeds",
        "seed_range": [2000, 2399],
        "fresh_seeds_used": False,
        "rules_variant": "v0-threshold-equipment",
        "deck_file": "data/deck-v1.json",
        "start_side": "easy-5-exit",
        "hand_size": 3,
        "policies": baseline0["policies"],
        "determinism_gate": {
            "hash_seeds": [
                baseline0["hash_seed"],
                baseline1["hash_seed"],
            ],
            "records_compared": 800,
            "exact_matches": 800,
            "mismatches": 0,
            "passed": True,
        },
        "instrumentation_gate": {
            "records_compared": 800,
            "exact_matches": 800,
            "mismatches": 0,
            "passed": True,
        },
        "canonical_per_seed_final_records": canonical,
        "canonical_baseline": {
            policy_name: aggregate_final(records)
            for policy_name, records in canonical.items()
        },
        "canonical_paired_groups": {
            name: {
                "count": len(seed_ids),
                "seed_ids": seed_ids,
            }
            for name, seed_ids in groups.items()
        },
        "historical_delta": historical_delta(canonical, historical),
        "metric_semantics": {
            "state_turn": "number of completed actions; initial state is turn 0",
            "action_turn": "1-based action number",
            "exit_visible_turn_count_before_placement": (
                "count of distinct completed-action state turns in which EXIT "
                "was visible before placement"
            ),
            "first_water_clear_after_water_seen_state_turn": (
                "first zero-visible-water state after water had previously "
                "become visible; avoids the trivial initial water-clear state"
            ),
            "first_return_open_threshold": (
                "first state at/below threshold after previously exceeding it; "
                "avoids the trivial START state"
            ),
            "delta_open": "after_open_tunnels - before_open_tunnels",
            "consolidation_move": (
                "placement move with negative actual delta_open"
            ),
            "multi_attachment_move": (
                "placement whose occupied coordinates consume at least two "
                "pre-existing open-tunnel targets"
            ),
        },
        "per_seed_mechanism_summaries": traces,
        "mechanism_strata": mechanism_strata,
        "v4_no_legal_move_exit_split": v4_no_legal,
        "v4_exit_never_placed_classification": {
            key: {
                "count": len(seed_ids),
                "seed_ids": seed_ids,
            }
            for key, seed_ids in sorted(v4_exit_never_placed.items())
        },
        "canonical_discordant_comparison": discordant,
        "answers": {
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "q4": q4,
            "q5": {
                "interpretation_pending": True,
                "recommended_next": None,
            },
        },
    }

    Path(args.output).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "determinism_gate": payload["determinism_gate"],
        "canonical_baseline": payload["canonical_baseline"],
        "canonical_paired_groups": payload["canonical_paired_groups"],
        "historical_delta": payload["historical_delta"],
        "v4_no_legal_move_exit_split": payload[
            "v4_no_legal_move_exit_split"
        ],
        "v4_exit_never_placed_classification": payload[
            "v4_exit_never_placed_classification"
        ],
        "v4_only_analysis": v4_only_analysis,
        "water_space_only_classification_counts": q4[
            "classification_counts"
        ],
        "water_space_only_classifications": water_only_classifications,
    }
    print("CANONICAL_MECHANISM_SUMMARY=" + json.dumps(summary, sort_keys=True))
    emit_chunks(payload)


if __name__ == "__main__":
    main()
