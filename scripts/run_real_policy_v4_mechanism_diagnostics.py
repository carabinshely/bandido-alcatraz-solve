from collections import Counter, defaultdict
import json
from pathlib import Path
from random import Random
from statistics import mean

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, WaterSpaceV3Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import move_features, score_features


ROOT = Path(__file__).parents[1]
SEEDS = range(2000, 2400)
RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v4"
    / "stability-holdout-2026-09-21.json"
)


class DiagnosticGreedyPolicy:
    """Behavior-identical weighted-greedy chooser with selected-move diagnostics."""

    def __init__(self, policy):
        self.weights = policy.weights
        self.last = None

    def choose(self, state, rng):
        moves = state.legal_moves()
        legal_exit = any(
            move.action is Action.PLACE
            and state.hand[move.hand_index].is_exit
            for move in moves
        )
        if not moves:
            self.last = {
                "legal_exit_available": False,
                "features": None,
                "move": None,
            }
            return None

        scored = []
        for move in moves:
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
            "legal_exit_available": legal_exit,
            "features": features,
            "move": move,
        }
        return move


def final_record(state, won, reason):
    equipment_ready = is_equipment_ready(state.raincoats, state.ropes)
    return {
        "won": won,
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
        "reason": reason,
    }


def trace(policy, seed, deck):
    rng = Random(seed)
    diagnostic_policy = DiagnosticGreedyPolicy(policy)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )

    d = {
        "exit_first_enters_hand_state_turn": None,
        "first_legal_exit_placement_action_turn": None,
        "exit_placed_action_turn": None,
        "first_equipment_ready_state_turn": None,
        "first_water_clear_state_turn": None,
        "first_post_move_open_le_10_turn": None,
        "first_post_move_open_le_5_turn": None,
        "first_return_open_le_10_after_exceeding_turn": None,
        "first_return_open_le_5_after_exceeding_turn": None,
        "min_open_before_exit_placement": None,
        "min_open_after_exit_seen_before_placement": None,
        "refresh_count": 0,
        "max_merge_opportunities": 0,
        "positive_bounded_merge_setup_chosen_moves": 0,
        "first_positive_bounded_merge_setup_action_turn": None,
        "consolidation_moves_negative_delta_open": 0,
        "first_consolidation_action_turn": None,
        "first_consolidation_after_setup_action_turn": None,
        "exit_visible_unplayable_state_count": 0,
        "terminal_no_legal_move_exit_state": None,
    }
    exceeded_10 = False
    exceeded_5 = False

    def observe_state():
        nonlocal exceeded_10, exceeded_5
        turn = state.turns
        exit_visible = any(card.is_exit for card in state.hand)
        if exit_visible and d["exit_first_enters_hand_state_turn"] is None:
            d["exit_first_enters_hand_state_turn"] = turn

        if (
            d["first_equipment_ready_state_turn"] is None
            and is_equipment_ready(state.raincoats, state.ropes)
        ):
            d["first_equipment_ready_state_turn"] = turn
        if (
            d["first_water_clear_state_turn"] is None
            and state.board.visible_water_cells == 0
        ):
            d["first_water_clear_state_turn"] = turn

        open_tunnels = state.board.open_tunnels
        if turn > 0:
            if (
                d["first_post_move_open_le_10_turn"] is None
                and open_tunnels <= 10
            ):
                d["first_post_move_open_le_10_turn"] = turn
            if (
                d["first_post_move_open_le_5_turn"] is None
                and open_tunnels <= 5
            ):
                d["first_post_move_open_le_5_turn"] = turn

        if open_tunnels > 10:
            exceeded_10 = True
        elif (
            exceeded_10
            and d["first_return_open_le_10_after_exceeding_turn"] is None
        ):
            d["first_return_open_le_10_after_exceeding_turn"] = turn

        if open_tunnels > 5:
            exceeded_5 = True
        elif (
            exceeded_5
            and d["first_return_open_le_5_after_exceeding_turn"] is None
        ):
            d["first_return_open_le_5_after_exceeding_turn"] = turn

        d["max_merge_opportunities"] = max(
            d["max_merge_opportunities"],
            state.board.merge_opportunities,
        )

        if not state.exit_placed:
            current = d["min_open_before_exit_placement"]
            d["min_open_before_exit_placement"] = (
                open_tunnels if current is None else min(current, open_tunnels)
            )
            if d["exit_first_enters_hand_state_turn"] is not None:
                current_seen = d["min_open_after_exit_seen_before_placement"]
                d["min_open_after_exit_seen_before_placement"] = (
                    open_tunnels
                    if current_seen is None
                    else min(current_seen, open_tunnels)
                )

    for _ in range(1000):
        observe_state()

        if state.won:
            return {
                "final": final_record(state, True, "win"),
                "diagnostics": d,
            }

        if state.board.open_tunnels == 0:
            return {
                "final": final_record(
                    state, False, "closed_tunnels_conditions_failed"
                ),
                "diagnostics": d,
            }

        if not state.hand and not state.draw_pile:
            return {
                "final": final_record(state, False, "deck_exhausted"),
                "diagnostics": d,
            }

        move = diagnostic_policy.choose(state, rng)
        last = diagnostic_policy.last
        if (
            last["legal_exit_available"]
            and d["first_legal_exit_placement_action_turn"] is None
        ):
            d["first_legal_exit_placement_action_turn"] = state.turns + 1

        exit_visible = any(card.is_exit for card in state.hand)
        if exit_visible and not last["legal_exit_available"] and not state.exit_placed:
            d["exit_visible_unplayable_state_count"] += 1

        if move is None:
            if state.refresh_unplayable_hand():
                d["refresh_count"] += 1
                continue

            if state.exit_placed:
                exit_state = "already_placed"
            elif exit_visible:
                exit_state = "visible_but_unplayable"
            elif d["exit_first_enters_hand_state_turn"] is None:
                exit_state = "never_seen"
            else:
                exit_state = "seen_not_currently_visible"
            d["terminal_no_legal_move_exit_state"] = exit_state
            return {
                "final": final_record(state, False, "no_legal_move"),
                "diagnostics": d,
            }

        action_turn = state.turns + 1
        card = state.hand[move.hand_index]
        features = last["features"]
        if features.bounded_merge_setup_gain > 0:
            d["positive_bounded_merge_setup_chosen_moves"] += 1
            if d["first_positive_bounded_merge_setup_action_turn"] is None:
                d["first_positive_bounded_merge_setup_action_turn"] = action_turn

        before_open = state.board.open_tunnels
        if card.is_exit and move.action is Action.PLACE:
            d["exit_placed_action_turn"] = action_turn

        state.apply(move)
        after_open = state.board.open_tunnels

        if after_open < before_open:
            d["consolidation_moves_negative_delta_open"] += 1
            if d["first_consolidation_action_turn"] is None:
                d["first_consolidation_action_turn"] = action_turn
            if (
                d["first_positive_bounded_merge_setup_action_turn"] is not None
                and action_turn
                > d["first_positive_bounded_merge_setup_action_turn"]
                and d["first_consolidation_after_setup_action_turn"] is None
            ):
                d["first_consolidation_after_setup_action_turn"] = action_turn

    observe_state()
    return {
        "final": final_record(state, state.won, "step_limit"),
        "diagnostics": d,
    }


def mean_or_none(values):
    values = [value for value in values if value is not None]
    return mean(values) if values else None


def aggregate(seed_ids, traces):
    result = {"seeds": len(seed_ids), "policies": {}}
    diagnostic_fields = [
        "exit_first_enters_hand_state_turn",
        "first_legal_exit_placement_action_turn",
        "exit_placed_action_turn",
        "first_equipment_ready_state_turn",
        "first_water_clear_state_turn",
        "first_post_move_open_le_10_turn",
        "first_post_move_open_le_5_turn",
        "first_return_open_le_10_after_exceeding_turn",
        "first_return_open_le_5_after_exceeding_turn",
        "min_open_before_exit_placement",
        "min_open_after_exit_seen_before_placement",
        "refresh_count",
        "max_merge_opportunities",
        "positive_bounded_merge_setup_chosen_moves",
        "consolidation_moves_negative_delta_open",
        "exit_visible_unplayable_state_count",
    ]
    for policy_name in ("bounded_merge_v4_250", "water_space_v3"):
        rows = [traces[policy_name][str(seed)] for seed in seed_ids]
        finals = [row["final"] for row in rows]
        diagnostics = [row["diagnostics"] for row in rows]
        policy_result = {
            "wins": sum(final["won"] for final in finals),
            "failure_reasons": dict(
                sorted(Counter(
                    final["reason"] for final in finals if not final["won"]
                ).items())
            ),
            "exit_seen_count": sum(
                d["exit_first_enters_hand_state_turn"] is not None
                for d in diagnostics
            ),
            "exit_legal_ever_count": sum(
                d["first_legal_exit_placement_action_turn"] is not None
                for d in diagnostics
            ),
            "exit_placed_count": sum(final["exit_placed"] for final in finals),
            "equipment_ready_ever_count": sum(
                d["first_equipment_ready_state_turn"] is not None
                for d in diagnostics
            ),
            "water_clear_ever_count": sum(
                d["first_water_clear_state_turn"] is not None
                for d in diagnostics
            ),
            "positive_setup_any_count": sum(
                d["positive_bounded_merge_setup_chosen_moves"] > 0
                for d in diagnostics
            ),
            "consolidation_any_count": sum(
                d["consolidation_moves_negative_delta_open"] > 0
                for d in diagnostics
            ),
            "setup_then_later_consolidation_count": sum(
                d["first_consolidation_after_setup_action_turn"] is not None
                for d in diagnostics
            ),
        }
        for field in diagnostic_fields:
            values = [d[field] for d in diagnostics]
            policy_result[f"mean_{field}"] = mean_or_none(values)
        result["policies"][policy_name] = policy_result
    return result


def no_legal_move_exit_split(v4_traces):
    split = {}
    groups = defaultdict(list)
    for seed in SEEDS:
        row = v4_traces[str(seed)]
        if row["final"]["reason"] != "no_legal_move":
            continue
        groups[
            row["diagnostics"]["terminal_no_legal_move_exit_state"]
        ].append(row)

    for state_name, rows in sorted(groups.items()):
        split[state_name] = {
            "count": len(rows),
            "equipment_ready_at_failure": sum(
                row["final"]["equipment_ready"] for row in rows
            ),
            "water_clear_at_failure": sum(
                row["final"]["visible_water"] == 0 for row in rows
            ),
            "final_open_le_10": sum(
                row["final"]["final_open_tunnels"] <= 10 for row in rows
            ),
            "final_open_le_5": sum(
                row["final"]["final_open_tunnels"] <= 5 for row in rows
            ),
            "mean_final_open_tunnels": mean(
                row["final"]["final_open_tunnels"] for row in rows
            ),
            "mean_visible_water": mean(
                row["final"]["visible_water"] for row in rows
            ),
            "mean_refresh_count": mean(
                row["diagnostics"]["refresh_count"] for row in rows
            ),
            "mean_positive_setup_moves": mean(
                row["diagnostics"][
                    "positive_bounded_merge_setup_chosen_moves"
                ]
                for row in rows
            ),
            "mean_consolidation_moves": mean(
                row["diagnostics"][
                    "consolidation_moves_negative_delta_open"
                ]
                for row in rows
            ),
        }
    return split


def discordant_table(seed_ids, traces, category_by_seed):
    fields = [
        "exit_first_enters_hand_state_turn",
        "first_legal_exit_placement_action_turn",
        "exit_placed_action_turn",
        "first_equipment_ready_state_turn",
        "first_water_clear_state_turn",
        "first_return_open_le_10_after_exceeding_turn",
        "first_return_open_le_5_after_exceeding_turn",
        "min_open_before_exit_placement",
        "min_open_after_exit_seen_before_placement",
        "refresh_count",
        "max_merge_opportunities",
        "positive_bounded_merge_setup_chosen_moves",
        "consolidation_moves_negative_delta_open",
        "first_positive_bounded_merge_setup_action_turn",
        "first_consolidation_after_setup_action_turn",
        "exit_visible_unplayable_state_count",
        "terminal_no_legal_move_exit_state",
    ]
    rows = []
    for seed in seed_ids:
        row = {
            "seed": seed,
            "category": category_by_seed[seed],
        }
        for policy_name in ("bounded_merge_v4_250", "water_space_v3"):
            trace_row = traces[policy_name][str(seed)]
            compact = dict(trace_row["final"])
            compact.update({
                field: trace_row["diagnostics"][field]
                for field in fields
            })
            row[policy_name] = compact
        rows.append(row)
    return rows


def main():
    receipt = json.loads(RECEIPT.read_text())
    expected = receipt["metrics"]
    deck = load_real_deck(ROOT / "data")

    traces = {
        "bounded_merge_v4_250": {},
        "water_space_v3": {},
    }
    policies = {
        "bounded_merge_v4_250": BoundedMergeV4Policy(setup_weight=250),
        "water_space_v3": WaterSpaceV3Policy(),
    }

    mismatches = []
    for policy_name, policy in policies.items():
        for seed in SEEDS:
            row = trace(policy, seed, deck)
            traces[policy_name][str(seed)] = row
            expected_final = expected[policy_name]["per_seed"][str(seed)]
            if row["final"] != expected_final:
                mismatches.append({
                    "policy": policy_name,
                    "seed": seed,
                    "expected": expected_final,
                    "actual": row["final"],
                })

    if mismatches:
        print(
            "REPLAY_MISMATCH_JSON="
            + json.dumps(
                {
                    "count": len(mismatches),
                    "first_20": mismatches[:20],
                },
                sort_keys=True,
            )
        )
        raise SystemExit(
            "diagnostic replay does not reproduce Worker #2 receipt"
        )

    paired = receipt["paired"]
    groups = {
        "all_400": list(SEEDS),
        "v4_only_wins": paired["v4_only_seed_ids"],
        "water_space_v3_only_wins": paired[
            "water_space_v3_only_seed_ids"
        ],
        "both_win": paired["both_win_seed_ids"],
        "both_lose": paired["both_lose_seed_ids"],
    }
    aggregates = {
        name: aggregate(seed_ids, traces)
        for name, seed_ids in groups.items()
    }

    category_by_seed = {}
    for seed in paired["v4_only_seed_ids"]:
        category_by_seed[seed] = "v4_only_win"
    for seed in paired["water_space_v3_only_seed_ids"]:
        category_by_seed[seed] = "water_space_v3_only_win"

    discordant_ids = sorted(
        paired["v4_only_seed_ids"]
        + paired["water_space_v3_only_seed_ids"]
    )

    result = {
        "experiment": "real-deck-policy-v4-mechanism-diagnostics",
        "date": "2026-09-22",
        "source_receipt": str(RECEIPT.relative_to(ROOT)),
        "source_worker_2_comment": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5772073757"
        ),
        "orchestrator_decision": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5772513909"
        ),
        "rules_variant": "v0-threshold-equipment",
        "deck_file": "data/deck-v1.json",
        "seed_range": [2000, 2399],
        "diagnostic_replay": True,
        "fresh_seeds_used": False,
        "policies": {
            "bounded_merge_v4_250": {
                "class": "BoundedMergeV4Policy",
                "parameters": {"setup_weight": 250},
            },
            "water_space_v3": {
                "class": "WaterSpaceV3Policy",
                "parameters": {},
            },
        },
        "metric_semantics": {
            "state_turn": (
                "number of completed actions; 0 denotes the initial hand/state"
            ),
            "action_turn": "1-based turn number of the action about to be taken",
            "first_return_threshold": (
                "first state turn at or below threshold after previously "
                "having exceeded it"
            ),
            "consolidation_move": (
                "chosen move whose actual final open-tunnel count is lower "
                "than immediately before the move"
            ),
            "positive_bounded_merge_setup_move": (
                "chosen move with move_features.bounded_merge_setup_gain > 0"
            ),
        },
        "deterministic_replay_check": {
            "games_compared": 800,
            "mismatch_count": 0,
            "exact_final_records_match_worker_2_receipt": True,
        },
        "aggregates": aggregates,
        "v4_no_legal_move_exit_state_split": no_legal_move_exit_split(
            traces["bounded_merge_v4_250"]
        ),
        "discordant_seed_table": discordant_table(
            discordant_ids, traces, category_by_seed
        ),
        "per_seed": traces,
    }
    print("MECHANISM_DIAGNOSTICS_JSON=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
