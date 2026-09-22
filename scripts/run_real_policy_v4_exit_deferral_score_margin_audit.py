import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from random import Random
from statistics import mean

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import MoveFeatures, move_features, score_features


ROOT = Path(__file__).parents[1]
CANONICAL_RECEIPT = (
    ROOT
    / "experiments"
    / "real-deck-policy-v4"
    / "canonical-mechanism-replay-2026-09-22.json"
)
SETUP_WEIGHT = 250
WINNER_SEEDS = [2005, 2137, 2174, 2238, 2267, 2282, 2286, 2294, 2340, 2345, 2383]
FAMILY_FIELDS = {
    "terminal": ("wins", "closes_last_without_win"),
    "equipment_collection": ("collect_needed", "collect_excess", "collect_degree_one"),
    "topology": ("delta_open_tunnels",),
    "water_cover": ("delta_visible_water",),
    "water_space_safety": ("delta_water_obstruction", "new_trapped_water"),
    "merge": ("delta_merge_opportunities", "bounded_merge_setup_gain"),
    "exit_timing": ("places_exit_ready", "places_exit_early"),
}


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
    total = sum(weighted.values())
    assert total == sum(families.values())
    assert total == score_features(features, weights)
    return {
        "raw_features": raw,
        "weighted_contributions": weighted,
        "family_contributions": families,
        "score": total,
    }


def sign_summary(values):
    if all(value > 0 for value in values):
        return "positive"
    if all(value < 0 for value in values):
        return "negative"
    if all(value == 0 for value in values):
        return "zero"
    if all(value >= 0 for value in values):
        return "nonnegative_mixed"
    if all(value <= 0 for value in values):
        return "nonpositive_mixed"
    return "mixed"


def terminal_exit_state(state, ever_seen):
    visible = any(card.is_exit for card in state.hand)
    if state.exit_placed:
        return "already_placed"
    if visible:
        return "visible_unplayable"
    if ever_seen:
        return "seen_not_currently_visible"
    return "not_seen"


def audit_deferral(
    *,
    seed,
    cohort,
    state,
    action_turn,
    moves,
    scored_rows,
    chosen_row,
    weights,
    first_exit_seen_turn,
    prior_refreshes,
    exit_reappeared_after_cycle,
):
    chosen_move, chosen_features, chosen_payload = chosen_row
    global_max = max(row[2]["score"] for row in scored_rows)
    assert chosen_payload["score"] == global_max

    exit_rows = [
        row
        for row in scored_rows
        if row[0].action is Action.PLACE and state.hand[row[0].hand_index].is_exit
    ]
    assert exit_rows
    best_exit_score = max(row[2]["score"] for row in exit_rows)
    best_exit_rows = [row for row in exit_rows if row[2]["score"] == best_exit_score]
    tied = best_exit_score == global_max
    classification = "exit_tied_global_best" if tied else "strict_non_exit_preference"

    single_family = {}
    for family in FAMILY_FIELDS:
        hypothetical = [
            (row[2]["score"] - row[2]["family_contributions"][family], row)
            for row in scored_rows
        ]
        hypothetical_max = max(score for score, _ in hypothetical)
        best_rows = [row for score, row in hypothetical if score == hypothetical_max]
        single_family[family] = {
            "any_legal_exit_in_hypothetical_global_best_set": any(
                row[0].action is Action.PLACE
                and state.hand[row[0].hand_index].is_exit
                for row in best_rows
            ),
            "historical_chosen_remains_in_hypothetical_best_set": any(
                row[0] == chosen_move for row in best_rows
            ),
            "hypothetical_best_set_size": len(best_rows),
        }

    setup_hypothetical = [
        (
            row[2]["score"]
            - row[2]["weighted_contributions"]["bounded_merge_setup_gain"],
            row,
        )
        for row in scored_rows
    ]
    setup_max = max(score for score, _ in setup_hypothetical)
    setup_best = [row for score, row in setup_hypothetical if score == setup_max]
    worker5_setup_gate_sensitive = not any(
        row[0] == chosen_move for row in setup_best
    )

    best_exit_candidates = []
    for move, features, payload in best_exit_rows:
        best_exit_candidates.append({
            "move": move_signature(state, move),
            **payload,
        })

    result = {
        "seed": seed,
        "cohort": cohort,
        "action_turn": action_turn,
        "state_turn": state.turns,
        "equipment_ready": is_equipment_ready(state.raincoats, state.ropes),
        "visible_water": state.board.visible_water_cells,
        "water_clear": state.board.visible_water_cells == 0,
        "open_tunnels": state.board.open_tunnels,
        "open_tunnels_le_5": state.board.open_tunnels <= 5,
        "exit_first_seen_state_turn": first_exit_seen_turn,
        "prior_refreshes": prior_refreshes,
        "exit_previously_disappeared_and_reappeared": exit_reappeared_after_cycle,
        "worker5_setup_gate_sensitive": worker5_setup_gate_sensitive,
        "legal_move_count": len(moves),
        "legal_exit_move_count": len(exit_rows),
        "global_max_score": global_max,
        "best_legal_exit_score": best_exit_score,
        "classification": classification,
        "historical_chosen": {
            "move": move_signature(state, chosen_move),
            **chosen_payload,
        },
        "best_legal_exit_candidates": best_exit_candidates,
        "single_family_sensitivity": single_family,
    }

    if tied:
        result["total_margin"] = 0
        result["family_margin_summary"] = None
        result["dominant_driver"] = None
        return result

    total_margin = chosen_payload["score"] - best_exit_score
    assert total_margin > 0
    family_candidate_margins = []
    for _, _, exit_payload in best_exit_rows:
        margins = {
            family: (
                chosen_payload["family_contributions"][family]
                - exit_payload["family_contributions"][family]
            )
            for family in FAMILY_FIELDS
        }
        assert sum(margins.values()) == total_margin
        positive = sorted(
            ((family, value) for family, value in margins.items() if value > 0),
            key=lambda item: (-item[1], item[0]),
        )
        first_value = positive[0][1]
        first_families = [family for family, value in positive if value == first_value]
        second_value = next(
            (value for _, value in positive if value < first_value),
            None,
        )
        second_families = (
            [family for family, value in positive if value == second_value]
            if second_value is not None
            else []
        )
        family_candidate_margins.append({
            "margins": margins,
            "largest_positive_families": first_families,
            "largest_positive_value": first_value,
            "second_largest_positive_families": second_families,
            "second_largest_positive_value": second_value,
        })

    family_summary = {}
    for family in FAMILY_FIELDS:
        values = [row["margins"][family] for row in family_candidate_margins]
        family_summary[family] = {
            "minimum_margin": min(values),
            "maximum_margin": max(values),
            "mean_margin": mean(values),
            "sign": sign_summary(values),
            "positive_driver_for_every_best_exit": all(value > 0 for value in values),
        }

    largest_sets = [
        tuple(row["largest_positive_families"])
        for row in family_candidate_margins
    ]
    stable_largest = (
        len(set(largest_sets)) == 1 and len(largest_sets[0]) == 1
    )
    if stable_largest:
        dominant = largest_sets[0][0]
        fractions = [
            row["margins"][dominant] / total_margin
            for row in family_candidate_margins
        ]
        dominant_driver = {
            "family": dominant,
            "stable_across_best_exit_placements": True,
            "fraction_of_total_margin_min": min(fractions),
            "fraction_of_total_margin_max": max(fractions),
            "fraction_of_total_margin_mean": mean(fractions),
            "second_largest_positive_families_by_exit": [
                row["second_largest_positive_families"]
                for row in family_candidate_margins
            ],
        }
    else:
        dominant_driver = {
            "family": "attribution_ambiguous_across_exit_placements",
            "stable_across_best_exit_placements": False,
            "largest_positive_families_by_exit": [
                row["largest_positive_families"]
                for row in family_candidate_margins
            ],
        }

    result["total_margin"] = total_margin
    result["family_margin_summary"] = family_summary
    result["dominant_driver"] = dominant_driver
    return result


def trace_seed(seed, cohort, deck, canonical_final):
    policy = BoundedMergeV4Policy(setup_weight=SETUP_WEIGHT)
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )

    ever_seen = False
    first_exit_seen_turn = None
    refresh_count = 0
    exit_cycled_out = False
    exit_reappeared_after_cycle = False
    deferrals = []

    for _ in range(1000):
        visible = any(card.is_exit for card in state.hand)
        if visible and not ever_seen:
            ever_seen = True
            first_exit_seen_turn = state.turns
        if visible and exit_cycled_out:
            exit_reappeared_after_cycle = True

        if state.won:
            final = final_record(state, "win")
            break
        if state.board.open_tunnels == 0:
            final = final_record(state, "closed_tunnels_conditions_failed")
            break
        if not state.hand and not state.draw_pile:
            final = final_record(state, "deck_exhausted")
            break

        moves = state.legal_moves()
        if not moves:
            before_visible = visible
            if state.refresh_unplayable_hand():
                refresh_count += 1
                after_visible = any(card.is_exit for card in state.hand)
                if before_visible and not after_visible:
                    exit_cycled_out = True
                if after_visible and exit_cycled_out:
                    exit_reappeared_after_cycle = True
                continue
            final = final_record(state, "no_legal_move")
            break

        scored_rows = []
        for move in moves:
            features = move_features(state, move)
            payload = score_payload(features, policy.weights)
            scored_rows.append((move, features, payload))

        global_max = max(row[2]["score"] for row in scored_rows)
        actual_best = [row for row in scored_rows if row[2]["score"] == global_max]
        chosen_row = rng.choice(actual_best)
        chosen_move = chosen_row[0]
        chosen_card = state.hand[chosen_move.hand_index]

        legal_exit_exists = any(
            move.action is Action.PLACE and state.hand[move.hand_index].is_exit
            for move in moves
        )
        chosen_is_exit = (
            chosen_move.action is Action.PLACE and chosen_card.is_exit
        )
        if legal_exit_exists and not chosen_is_exit:
            deferrals.append(
                audit_deferral(
                    seed=seed,
                    cohort=cohort,
                    state=state,
                    action_turn=state.turns + 1,
                    moves=moves,
                    scored_rows=scored_rows,
                    chosen_row=chosen_row,
                    weights=policy.weights,
                    first_exit_seen_turn=first_exit_seen_turn,
                    prior_refreshes=refresh_count,
                    exit_reappeared_after_cycle=exit_reappeared_after_cycle,
                )
            )

        state.apply(chosen_move)
    else:
        final = final_record(state, "step_limit")

    if final != canonical_final:
        return {
            "seed": seed,
            "cohort": cohort,
            "canonical_final": canonical_final,
            "instrumented_final": final,
            "match": False,
            "deferrals": [],
        }

    terminal = terminal_exit_state(state, ever_seen)
    for row in deferrals:
        row["terminal_exit_state"] = terminal

    return {
        "seed": seed,
        "cohort": cohort,
        "canonical_final": canonical_final,
        "instrumented_final": final,
        "match": True,
        "terminal_exit_state": terminal,
        "deferrals": deferrals,
    }


def per_seed_summary(row):
    deferrals = row["deferrals"]
    strict = [d for d in deferrals if d["classification"] == "strict_non_exit_preference"]
    tied = [d for d in deferrals if d["classification"] == "exit_tied_global_best"]
    dominant = Counter(
        d["dominant_driver"]["family"]
        for d in strict
        if d["dominant_driver"] is not None
    )
    sensitivity = {
        family: sum(
            d["single_family_sensitivity"][family][
                "any_legal_exit_in_hypothetical_global_best_set"
            ]
            for d in strict
        )
        for family in FAMILY_FIELDS
    }
    return {
        "seed": row["seed"],
        "cohort": row["cohort"],
        "legal_exit_deferral_count": len(deferrals),
        "tied_count": len(tied),
        "strict_count": len(strict),
        "pre_ready_count": sum(not d["equipment_ready"] for d in deferrals),
        "post_ready_count": sum(d["equipment_ready"] for d in deferrals),
        "dominant_family_counts": dict(sorted(dominant.items())),
        "single_family_sensitivity_counts": sensitivity,
    }


def aggregate_cohort(rows):
    deferrals = [d for row in rows for d in row["deferrals"]]
    strict = [d for d in deferrals if d["classification"] == "strict_non_exit_preference"]
    tied = [d for d in deferrals if d["classification"] == "exit_tied_global_best"]

    dominant = {}
    positive_driver_every_exit = {}
    sensitivity = {}
    for family in FAMILY_FIELDS:
        dominant_events = [
            d for d in strict
            if d["dominant_driver"] is not None
            and d["dominant_driver"]["family"] == family
        ]
        dominant[family] = {
            "events": len(dominant_events),
            "affected_seeds": sorted({d["seed"] for d in dominant_events}),
        }
        positive_events = [
            d for d in strict
            if d["family_margin_summary"][family][
                "positive_driver_for_every_best_exit"
            ]
        ]
        positive_driver_every_exit[family] = {
            "events": len(positive_events),
            "affected_seeds": sorted({d["seed"] for d in positive_events}),
        }
        sensitive_events = [
            d for d in strict
            if d["single_family_sensitivity"][family][
                "any_legal_exit_in_hypothetical_global_best_set"
            ]
        ]
        sensitivity[family] = {
            "events": len(sensitive_events),
            "affected_seeds": sorted({d["seed"] for d in sensitive_events}),
        }

    readiness = {}
    for label, ready in (("equipment_not_ready", False), ("equipment_ready", True)):
        ds = [d for d in deferrals if d["equipment_ready"] is ready]
        readiness[label] = {
            "deferrals": len(ds),
            "strict": sum(
                d["classification"] == "strict_non_exit_preference" for d in ds
            ),
            "tied": sum(
                d["classification"] == "exit_tied_global_best" for d in ds
            ),
            "affected_seeds": sorted({d["seed"] for d in ds}),
            "stable_dominant_driver_counts": dict(sorted(Counter(
                d["dominant_driver"]["family"]
                for d in ds
                if d["classification"] == "strict_non_exit_preference"
                and d["dominant_driver"] is not None
            ).items())),
        }

    return {
        "seed_count": len(rows),
        "seeds_with_any_deferral": len({d["seed"] for d in deferrals}),
        "deferrals": len(deferrals),
        "strict_deferrals": len(strict),
        "tied_deferrals": len(tied),
        "worker5_setup_gate_sensitive_deferrals": sum(
            d["worker5_setup_gate_sensitive"] for d in deferrals
        ),
        "equipment_readiness": readiness,
        "stable_dominant_driver": dominant,
        "positive_driver_for_every_best_exit": positive_driver_every_exit,
        "single_family_removal_puts_exit_in_best_set": sensitivity,
    }


def emit_chunks(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    size = 16000
    chunks = [encoded[i:i + size] for i in range(0, len(encoded), size)]
    print(f"AUDIT_RECEIPT_CHUNK_COUNT={len(chunks)}")
    for index, chunk in enumerate(chunks):
        print(f"AUDIT_RECEIPT_CHUNK_{index:04d}={chunk}")


def main():
    canonical = json.loads(CANONICAL_RECEIPT.read_text(encoding="utf-8"))
    finals = canonical["canonical_per_seed_final_records"]["bounded_merge_v4_250"]
    near_win_seeds = sorted(
        int(seed)
        for seed, row in finals.items()
        if row["failure_reason"] == "no_legal_move"
        and row["equipment_ready"]
        and row["visible_water"] == 0
        and row["final_open_tunnels"] <= 5
    )
    assert len(near_win_seeds) == 28
    assert canonical["canonical_paired_groups"]["v4_only_win"]["seed_ids"] == WINNER_SEEDS

    deck = load_real_deck(ROOT / "data")
    rows = []
    for seed in near_win_seeds:
        rows.append(trace_seed(seed, "compact_near_win_failure", deck, finals[str(seed)]))
    for seed in WINNER_SEEDS:
        rows.append(trace_seed(seed, "v4_only_winner", deck, finals[str(seed)]))

    mismatches = [row for row in rows if not row["match"]]
    if mismatches:
        payload = {
            "experiment": "exit-deferral-score-margin-audit",
            "date": "2026-09-22",
            "dataset_status": "non-confirmatory / already-spent diagnostic seeds",
            "replay_integrity": {
                "records_compared": len(rows),
                "exact_matches": len(rows) - len(mismatches),
                "mismatches": len(mismatches),
                "passed": False,
            },
            "mismatch_records": mismatches,
        }
        emit_chunks(payload)
        raise SystemExit("replay integrity gate failed")

    near_rows = [row for row in rows if row["cohort"] == "compact_near_win_failure"]
    winner_rows = [row for row in rows if row["cohort"] == "v4_only_winner"]
    near_summary = aggregate_cohort(near_rows)
    winner_summary = aggregate_cohort(winner_rows)

    assert near_summary["worker5_setup_gate_sensitive_deferrals"] == 10
    assert winner_summary["worker5_setup_gate_sensitive_deferrals"] == 4

    weights = asdict(BoundedMergeV4Policy(setup_weight=SETUP_WEIGHT).weights)
    payload = {
        "experiment": "exit-deferral-score-margin-audit",
        "date": "2026-09-22",
        "branch": "bootstrap/model-foundation",
        "dataset_status": "non-confirmatory / already-spent diagnostic seeds",
        "fresh_seeds_used": False,
        "orchestrator_decision": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5776611260"
        ),
        "canonical_source_receipts": [
            "experiments/real-deck-policy-v4/canonical-mechanism-replay-2026-09-22.json",
            "experiments/real-deck-policy-v4/exit-phase-diagnostics-2026-09-22.json",
        ],
        "policy": "BoundedMergeV4Policy(setup_weight=250)",
        "active_weights": weights,
        "score_families": FAMILY_FIELDS,
        "seed_cohorts": {
            "compact_near_win_failures": near_win_seeds,
            "v4_only_winners": WINNER_SEEDS,
        },
        "replay_integrity": {
            "records_compared": len(rows),
            "exact_matches": len(rows),
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
        "per_deferral_records": [
            d for row in rows for d in row["deferrals"]
        ],
        "failure_vs_winner_comparator": {
            "compact_near_win_failures": near_summary,
            "v4_only_winners": winner_summary,
        },
        "per_seed_summaries": [per_seed_summary(row) for row in rows],
        "answers": {
            "q1": {
                "near_win_deferrals": near_summary["deferrals"],
                "exit_tied_global_best": near_summary["tied_deferrals"],
                "strict_non_exit_preference": near_summary["strict_deferrals"],
            },
            "q2": {
                "stable_dominant_driver": near_summary["stable_dominant_driver"],
                "positive_driver_for_every_best_exit": near_summary[
                    "positive_driver_for_every_best_exit"
                ],
            },
            "q3": {
                "single_family_sensitivity": near_summary[
                    "single_family_removal_puts_exit_in_best_set"
                ],
                "interpretation_pending": True,
            },
            "q4": {
                "failure_comparator": near_summary,
                "winner_comparator": winner_summary,
                "interpretation_pending": True,
            },
            "q5": {
                "failure_equipment_readiness": near_summary["equipment_readiness"],
                "interpretation_pending": True,
            },
            "q6": {
                "classification": "interpretation_pending",
                "interpretation_pending": True,
            },
        },
        "final_classification": "interpretation_pending",
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
        "near_win_seeds": near_win_seeds,
        "winner_seeds": WINNER_SEEDS,
        "near_win": near_summary,
        "winners": winner_summary,
        "q1": payload["answers"]["q1"],
    }
    print("AUDIT_SUMMARY=" + json.dumps(summary, sort_keys=True))
    emit_chunks(payload)


if __name__ == "__main__":
    main()
