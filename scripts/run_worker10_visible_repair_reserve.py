from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, legal_moves
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready

ROOT = Path(__file__).parents[1]
STARTING_MAIN = "ed406095f99704bd3b5a4206b34dde3345e2f542"
MANIFEST_PATH = ROOT / "experiments/real-deck-policy-v4/preloss-direct-terminal-half-kill-audit-2026-09-23.manifest.json"
PROVENANCE_PATH = ROOT / "scripts/worker10_provenance_fixture.json"


def load_scope() -> tuple[dict[str, list[str]], set[str], list[int]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    transition_ids = manifest["transition_ids"]
    expected_keys = {"persistent", "earlier_recovered", "winning_recovered"}
    if set(transition_ids) != expected_keys:
        raise AssertionError(f"unexpected Worker #9 cohort keys: {sorted(transition_ids)}")
    all_ids = (
        transition_ids["persistent"]
        + transition_ids["earlier_recovered"]
        + transition_ids["winning_recovered"]
    )
    if len(all_ids) != 35 or len(set(all_ids)) != 35:
        raise AssertionError("Worker #9 manifest must contain exactly 35 distinct transitions")
    seeds = sorted({int(value.split(":", 1)[0]) for value in all_ids})
    if len(seeds) != 23:
        raise AssertionError("Worker #10 scope must contain exactly 23 distinct seeds")
    return transition_ids, set(all_ids), seeds


def cohort_for(transition_id: str, transition_ids: dict[str, list[str]]) -> str:
    for cohort in ("persistent", "earlier_recovered", "winning_recovered"):
        if transition_id in transition_ids[cohort]:
            return cohort
    raise KeyError(transition_id)


def final_record(state: GameState, reason: str) -> dict:
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


def move_signature(state: GameState, move) -> dict:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def exit_legal_move_count(board, exit_card) -> int:
    moves = legal_moves(board, (exit_card,))
    if any(move.action is not Action.PLACE for move in moves):
        raise AssertionError("standalone EXIT capacity contains a non-placement move")
    return len(moves)


def audit_transition(
    state: GameState,
    move,
    exit_card,
    transition_id: str,
    cohort: str,
    expected: dict,
    worker8_first_zero_recoverable: bool,
) -> tuple[dict, dict, dict, bool]:
    actual_signature = move_signature(state, move)
    pre_hand = list(state.hand)
    pre_hand_ids = [card.card_id for card in pre_hand]

    identity_mismatch: dict = {}
    for field in ("action", "card_id", "hand_index", "origin", "quarter_turns"):
        if actual_signature[field] != expected[field]:
            identity_mismatch[field] = {
                "expected": expected[field],
                "actual": actual_signature[field],
            }

    pre_capacity = exit_legal_move_count(state.board, exit_card)
    if pre_capacity != expected["pre_exit_legal_move_count"]:
        identity_mismatch["pre_exit_legal_move_count"] = {
            "expected": expected["pre_exit_legal_move_count"],
            "actual": pre_capacity,
        }

    hand_mismatch: dict = {}
    if len(pre_hand) != 3:
        hand_mismatch["pre_action_hand_size"] = {"expected": 3, "actual": len(pre_hand)}

    expected_index = expected["hand_index"]
    if not (0 <= expected_index < len(pre_hand)):
        hand_mismatch["historical_chosen_hand_index"] = {
            "expected_valid_index": expected_index,
            "actual_hand_size": len(pre_hand),
        }
    elif pre_hand[expected_index].card_id != expected["card_id"]:
        hand_mismatch["historical_chosen_card_at_index"] = {
            "expected": expected["card_id"],
            "actual": pre_hand[expected_index].card_id,
        }

    if move.action is not Action.PLACE:
        return {}, identity_mismatch, hand_mismatch, False
    if move.origin is None:
        raise AssertionError("ordinary placement has no origin")

    chosen_card = pre_hand[move.hand_index]
    if chosen_card.is_exit:
        hand_mismatch["historical_chosen_card_is_exit"] = True

    retained = [
        (index, card)
        for index, card in enumerate(pre_hand)
        if index != move.hand_index
    ]
    if len(retained) != 2:
        hand_mismatch["retained_card_count"] = {
            "expected": 2,
            "actual": len(retained),
        }

    # Authorized first action clone: historical chosen placement only.
    # Critically, this does not call GameState.apply(), so it does not draw.
    post_board = state.board.clone()
    post_board.place(chosen_card, move.origin, move.quarter_turns)
    post_capacity = exit_legal_move_count(post_board, exit_card)
    if post_capacity != expected["post_exit_legal_move_count"]:
        identity_mismatch["post_exit_legal_move_count"] = {
            "expected": expected["post_exit_legal_move_count"],
            "actual": post_capacity,
        }

    legal_retained_placements = 0
    restoring: list[dict] = []
    maximum_restored_capacity = 0

    for original_hand_index, card in retained:
        # EXIT is never injected into this hand. If it happened to be one of
        # the two naturally retained visible cards, it is not an ordinary card
        # and therefore contributes no repair-placement candidates.
        if card.is_exit:
            continue
        for repair_move in legal_moves(post_board, (card,)):
            if repair_move.action is not Action.PLACE:
                continue
            if repair_move.origin is None:
                raise AssertionError("retained-card placement has no origin")
            legal_retained_placements += 1

            # Authorized second action clone: exactly one placement by a card
            # visible in the pre-action hand. No draw, refresh, or continuation.
            repair_board = post_board.clone()
            repair_board.place(
                card,
                repair_move.origin,
                repair_move.quarter_turns,
            )
            restored_capacity = exit_legal_move_count(repair_board, exit_card)
            maximum_restored_capacity = max(
                maximum_restored_capacity,
                restored_capacity,
            )
            if restored_capacity > 0:
                restoring.append(
                    {
                        "card_id": card.card_id,
                        "original_pre_action_hand_index": original_hand_index,
                        "origin": list(repair_move.origin),
                        "quarter_turns": repair_move.quarter_turns,
                        "restored_exit_legal_move_count": restored_capacity,
                    }
                )

    reserve = bool(restoring)
    kill_without_reserve = not reserve
    if reserve:
        provenance_class = "repair_already_visible_pre_action"
    elif worker8_first_zero_recoverable:
        provenance_class = "repair_appears_only_after_draw_or_visible_hand_change"
    else:
        provenance_class = "no_immediate_repair_in_either_view"

    record = {
        "transition_id": transition_id,
        "cohort": cohort,
        "seed": int(transition_id.split(":", 1)[0]),
        "action_turn": state.turns + 1,
        "state_turn_before_action": state.turns,
        "pre_action_hand_card_ids": pre_hand_ids,
        "historical_chosen_hand_index": move.hand_index,
        "historical_chosen_card_id": chosen_card.card_id,
        "historical_chosen_origin": list(move.origin),
        "historical_chosen_rotation": move.quarter_turns,
        "retained_pre_action_cards": [
            {
                "original_pre_action_hand_index": index,
                "card_id": card.card_id,
            }
            for index, card in retained
        ],
        "pre_action_exit_legal_move_count": pre_capacity,
        "immediate_post_historical_action_exit_legal_move_count": post_capacity,
        "legal_retained_card_ordinary_placement_count": legal_retained_placements,
        "capacity_restoring_retained_card_placement_count": len(restoring),
        "pre_action_visible_repair_reserve": reserve,
        "capacity_kill_without_visible_repair_reserve": kill_without_reserve,
        "maximum_restored_exit_legal_move_count": maximum_restored_capacity,
        "restoring_placements": restoring,
        "worker8_first_zero_one_step_exit_capacity_recoverable": (
            worker8_first_zero_recoverable
        ),
        "worker8_provenance_class": provenance_class,
        "replacement_draw_used_in_repair_audit": False,
        "refresh_used_in_repair_audit": False,
        "artificial_exit_injected_into_visible_hand": False,
    }
    return record, identity_mismatch, hand_mismatch, True


def replay_seed(
    seed: int,
    deck,
    target_ids: set[str],
    transition_ids: dict[str, list[str]],
    provenance: dict,
):
    rng = Random(seed)
    policy = BoundedMergeV4Policy(setup_weight=250)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    records: list[dict] = []
    identity_mismatches: list[dict] = []
    hand_mismatches: list[dict] = []
    non_place_ids: list[str] = []

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

        move = policy.choose(state, rng)
        if move is None:
            if state.refresh_unplayable_hand():
                continue
            reason = "deck_exhausted" if state.exhausted else "no_legal_move"
            break

        transition_id = f"{seed}:a{state.turns + 1}:s{state.turns}"
        if transition_id in target_ids:
            cohort = cohort_for(transition_id, transition_ids)
            expected = provenance["worker9_transition_expected"][transition_id]
            record, identity_mismatch, hand_mismatch, is_place = audit_transition(
                state,
                move,
                deck.exit_card,
                transition_id,
                cohort,
                expected,
                provenance["worker8_first_zero_one_step_recoverable"][
                    transition_id
                ],
            )
            if identity_mismatch:
                identity_mismatches.append(
                    {"transition_id": transition_id, **identity_mismatch}
                )
            if hand_mismatch:
                hand_mismatches.append(
                    {"transition_id": transition_id, **hand_mismatch}
                )
            if not is_place:
                non_place_ids.append(transition_id)
            else:
                records.append(record)

        # Canonical replay continues only to reach later preregistered
        # transitions/final records. The diagnostic repair audit above never
        # reads or uses the replacement draw produced here.
        state.apply(move)
    else:
        reason = "step_limit"

    final = final_record(state, reason)
    expected_final = provenance["worker8_final_expected"][str(seed)]
    final_mismatch = None
    if final != expected_final:
        final_mismatch = {
            "seed": seed,
            "expected": expected_final,
            "actual": final,
        }

    return (
        records,
        identity_mismatches,
        hand_mismatches,
        non_place_ids,
        final_mismatch,
        final,
    )


def summarize(records: list[dict], ids: list[str]) -> dict:
    selected = [record for record in records if record["transition_id"] in ids]
    true_ids = [
        record["transition_id"]
        for record in selected
        if record["capacity_kill_without_visible_repair_reserve"]
    ]
    false_ids = [
        record["transition_id"]
        for record in selected
        if not record["capacity_kill_without_visible_repair_reserve"]
    ]
    return {
        "total": len(selected),
        "true": len(true_ids),
        "true_fraction": (
            len(true_ids) / len(selected) if selected else 0.0
        ),
        "false": len(false_ids),
        "true_transition_ids": true_ids,
        "false_transition_ids": false_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    transition_ids, target_ids, seeds = load_scope()
    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))

    if set(provenance["worker9_transition_expected"]) != target_ids:
        raise AssertionError("Worker #9 provenance scope does not match merged manifest")
    if set(provenance["worker8_first_zero_one_step_recoverable"]) != target_ids:
        raise AssertionError("Worker #8 first-zero provenance scope mismatch")
    if set(provenance["worker8_final_expected"]) != {str(seed) for seed in seeds}:
        raise AssertionError("Worker #8 final-record seed scope mismatch")

    deck = load_real_deck(ROOT / "data")
    all_records: list[dict] = []
    identity_mismatches: list[dict] = []
    hand_mismatches: list[dict] = []
    non_place_ids: list[str] = []
    final_mismatches: list[dict] = []
    finals: dict[str, dict] = {}

    for seed in seeds:
        (
            records,
            identity,
            hands,
            non_place,
            final_mismatch,
            final,
        ) = replay_seed(
            seed,
            deck,
            target_ids,
            transition_ids,
            provenance,
        )
        all_records.extend(records)
        identity_mismatches.extend(identity)
        hand_mismatches.extend(hands)
        non_place_ids.extend(non_place)
        if final_mismatch is not None:
            final_mismatches.append(final_mismatch)
        finals[str(seed)] = final

    observed_ids = {record["transition_id"] for record in all_records}
    missing_ids = sorted(target_ids - observed_ids - set(non_place_ids))
    extra_ids = sorted(observed_ids - target_ids)
    if missing_ids or extra_ids:
        identity_mismatches.append(
            {"missing_transition_ids": missing_ids, "extra_transition_ids": extra_ids}
        )

    seed_scope_passed = len(seeds) == 23
    final_records_passed = not final_mismatches
    transition_identity_passed = (
        not identity_mismatches and len(observed_ids | set(non_place_ids)) == 35
    )
    hand_integrity_passed = not hand_mismatches and len(observed_ids) == 35
    action_type_passed = not non_place_ids and len(observed_ids) == 35

    integrity = {
        "starting_repository": {
            "starting_main": STARTING_MAIN,
            "passed": True,
        },
        "seed_scope": {
            "expected_distinct_seeds": 23,
            "replayed_distinct_seeds": len(seeds),
            "fresh_seeds_used": False,
            "passed": seed_scope_passed,
        },
        "final_records": {
            "records_compared": 23,
            "exact_matches": 23 - len(final_mismatches),
            "mismatches": final_mismatches,
            "passed": final_records_passed,
        },
        "transition_identities": {
            "records_compared": 35,
            "exact_matches": 35 - len(identity_mismatches),
            "mismatches": identity_mismatches,
            "passed": transition_identity_passed,
        },
        "pre_action_hands": {
            "records_reconstructed": 35,
            "exact_reconstructions": 35 - len(hand_mismatches),
            "mismatches": hand_mismatches,
            "replacement_draw_used_in_repair_audit": False,
            "refresh_used_in_repair_audit": False,
            "artificial_exit_injected": False,
            "passed": hand_integrity_passed,
        },
        "historical_action_type": {
            "expected_place_count": 35,
            "actual_place_count": 35 - len(non_place_ids),
            "non_place_transition_ids": non_place_ids,
            "passed": action_type_passed,
        },
    }
    integrity_passed = all(section["passed"] for section in integrity.values())

    payload = {
        "schema": "bandido-alcatraz-preaction-visible-repair-reserve-audit",
        "schema_version": 1,
        "experiment_id": "worker-10-visible-repair-reserve",
        "dataset_status": "already-spent / development / diagnostic / non-confirmatory",
        "date": "2026-09-23",
        "authoritative_orchestrator_decision_url": (
            "https://github.com/carabinshely/bandido-alcatraz-solve/"
            "issues/2#issuecomment-5794154223"
        ),
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
                "https://github.com/carabinshely/bandido-alcatraz-solve/"
                f"actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
                if os.environ.get("GITHUB_RUN_ID")
                else None
            ),
        },
        "runner": os.environ.get("RUNNER_NAME"),
        "policy": "BoundedMergeV4Policy(setup_weight=250)",
        "model": {
            "deck_file": "data/deck-v1.json",
            "exit_geometry_source": "data/deck-observations-v0.json",
            "rules_variant": "v0-threshold-equipment",
            "raincoats_min": 3,
            "ropes_min": 2,
            "start_side": "easy-5-exit",
            "hand_size": 3,
        },
        "transition_ids": transition_ids,
        "seed_scope": seeds,
        "replay_integrity": integrity,
        "integrity_passed": integrity_passed,
        "transition_records": all_records,
        "final_records": finals,
    }

    if integrity_passed:
        persistent = summarize(all_records, transition_ids["persistent"])
        earlier = summarize(all_records, transition_ids["earlier_recovered"])
        winning = summarize(all_records, transition_ids["winning_recovered"])
        reversible_ids = (
            transition_ids["earlier_recovered"]
            + transition_ids["winning_recovered"]
        )
        reversible = summarize(all_records, reversible_ids)

        persistent_true = persistent["true"]
        earlier_true = earlier["true"]
        winning_true = winning["true"]
        reversible_true = reversible["true"]

        if (
            persistent_true >= 16
            and earlier_true <= 5
            and winning_true <= 1
            and reversible_true <= 6
        ):
            classification = (
                "capacity_kill_without_visible_repair_reserve_"
                "supported_for_v5_design"
            )
        elif (
            persistent_true <= 12
            or earlier_true >= 8
            or winning_true >= 3
        ):
            classification = (
                "capacity_kill_without_visible_repair_reserve_not_supported"
            )
        else:
            classification = (
                "capacity_kill_without_visible_repair_reserve_ambiguous"
            )

        provenance_counts = Counter(
            record["worker8_provenance_class"] for record in all_records
        )
        provenance_cross_tab = {
            name: provenance_counts.get(name, 0)
            for name in (
                "repair_already_visible_pre_action",
                "repair_appears_only_after_draw_or_visible_hand_change",
                "no_immediate_repair_in_either_view",
            )
        }

        payload.update(
            {
                "cohort_results": {
                    "persistent": persistent,
                    "earlier_recovered": earlier,
                    "winning_recovered": winning,
                    "reversible_combined": reversible,
                },
                "persistent_false_negatives": persistent["false_transition_ids"],
                "reversible_false_positives": reversible["true_transition_ids"],
                "winning_false_positives": winning["true_transition_ids"],
                "worker8_provenance_cross_tab": provenance_cross_tab,
                "final_classification": classification,
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print("WORKER10_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
    if not integrity_passed:
        raise SystemExit(
            "Worker #10 integrity gate failed; discriminator not interpreted"
        )

    print(
        "WORKER10_RESULT="
        + json.dumps(
            {
                "cohort_results": payload["cohort_results"],
                "worker8_provenance_cross_tab": payload[
                    "worker8_provenance_cross_tab"
                ],
                "classification": payload["final_classification"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
