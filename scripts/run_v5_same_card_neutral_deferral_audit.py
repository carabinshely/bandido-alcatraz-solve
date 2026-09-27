from __future__ import annotations

import hashlib
import json
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import VisibleRepairReserveV5Policy
from bandido_alcatraz.strategy import (
    is_unsafe_capacity_kill_without_visible_repair_reserve,
    move_features,
    score_features,
    standalone_exit_legal_move_count,
)


ROOT = Path(__file__).parents[1]
SEEDS = (
    2001, 2004, 2005, 2020, 2024, 2034, 2084, 2098, 2104, 2110,
    2129, 2130, 2138, 2168, 2171, 2212, 2238, 2282, 2286, 2314,
    2334, 2371, 2372,
)
TARGET = "2238:a21:s20"

# Derived once from the exact canonical Worker #13 raw artifact declared in
# Issue #2 preregistration. Hash input is the compact JSON list of
# {"transition_id": ..., "move": ...} for action events only, sorted keys.
EXPECTED = {
    2001: (69, "157aad283feb3e0436bf670c13efe469cbdab431ac83afa9e065d6cafe9873ce"),
    2004: (38, "85e89bccff61352caabe673acfaed130837bdf59d5d7d81636cade71725ab2c7"),
    2005: (31, "e2894cdbcdbc28c374a078135ac7b72cf5eb7fbdcc7e860c68f2b59355719ffd"),
    2020: (69, "e03fcc538f2a17c3c4f0047686a7fafce90e528d6332aa1f1ef125e2f16e332f"),
    2024: (69, "f7aa96a218007ca6068b7eb1634d97e1c1c396feaea16c5e0725836c9f596718"),
    2034: (69, "62b2b173e537eaf611004f8f06456819ae063556edb1468fc6f4760f4e0b5655"),
    2084: (69, "09d58f7dfbae5aee2a668275f345cbbeb6d6a842ab379d4e95289f1647400b8a"),
    2098: (69, "be3a74dab76c56880d1a5c778b817b2f8c83eee8d82aa1af28d8053e6d15c000"),
    2104: (69, "6f3673a26b0f1e35a993bb2c46f67ed25c45e41b720ec013fe8a2fb50d4a0e2a"),
    2110: (69, "cf454b19fc3e4b3883785921028e457368ec8464d58f92bfc4687cc9da6f3994"),
    2129: (69, "67fecf539a482566ba82f969ca9ad1624cb8c53603b8b69ac7498979bd85248d"),
    2130: (69, "3136fe2c9baf0217e6caab25a3a009cf00018a96dc87b845bb80e8e5e932bea6"),
    2138: (38, "75e96574c9b72b3ed77ddc895af4dc7c5b8f5acffc403f482b5ae14afff531be"),
    2168: (69, "24a79ac4e1e8b4f4c9040155c4bda3c9b1c0ac9c51aa6130a040497a3391627d"),
    2171: (69, "c5615e018bb20315ba64ee3f7a7fe25f0728189fbcc82fc79a6cb7355b811aed"),
    2212: (61, "c0984ac7290e4a97d0d86bb305750b79e744860666c872e4b2b0a7e27c0653d0"),
    2238: (69, "633473071020194cfd39da2bfad4409b142c64242937c2ba716c2be352b533ee"),
    2282: (69, "d09be28b870a351a73ac963a773166c312168bbed48855b55cec85f54f9dd8aa"),
    2286: (16, "331802be665bfe00c3d2ee068e12ab11c733a356466f707ef7217a00e97f002c"),
    2314: (69, "3a2ae8e7c0dca10a8bb3912a40e8c4f6c55da02bd199a480c52273834720ed89"),
    2334: (69, "4f837ced262e25a699fed5ebfa3fe19fc09e71786689cadbc586f68ca10b3675"),
    2371: (24, "0543539aa987a7208925d388ad3bf7d4dab435584662cddef424b1fa5f2432c4"),
    2372: (69, "3d3bad238dadb87817f86e5c8425e9600ebe95e71caf6bb423f0d52e064a2aaa"),
}


def move_record(state: GameState, move: Move) -> dict[str, object]:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
    }


def eligible_moves(
    state: GameState,
    policy: VisibleRepairReserveV5Policy,
) -> tuple[list[Move], str]:
    moves = state.legal_moves()
    if not moves:
        return [], "none"
    if state.exit_placed or state.exit_seen:
        return moves, "all_phase_inactive"
    if standalone_exit_legal_move_count(state.board, policy.exit_card) <= 0:
        return moves, "all_no_capacity"
    normal = [
        move
        for move in moves
        if not is_unsafe_capacity_kill_without_visible_repair_reserve(
            state, move, policy.exit_card
        )
    ]
    if not normal:
        return moves, "all_unsafe_fallback"
    return normal, "normal_filtered"


def nonzero_weight_vector(
    state: GameState,
    move: Move,
    policy: VisibleRepairReserveV5Policy,
) -> dict[str, dict[str, int]]:
    features = move_features(state, move)
    result: dict[str, dict[str, int]] = {}
    for field in features.__dataclass_fields__:
        weight = getattr(policy.weights, field)
        if weight == 0:
            continue
        value = getattr(features, field)
        result[field] = {
            "feature": value,
            "weight": weight,
            "contribution": value * weight,
        }
    return result


def decision_footprint(
    state: GameState,
    policy: VisibleRepairReserveV5Policy,
    transition_id: str,
) -> dict[str, object] | None:
    eligible, eligibility_path = eligible_moves(state, policy)
    if not eligible:
        return None

    scored = [
        (score_features(move_features(state, move), policy.weights), move)
        for move in eligible
    ]
    max_score = max(score for score, _ in scored)
    max_tier = [move for score, move in scored if score == max_score]
    collect_indexes = {
        move.hand_index for move in max_tier if move.action is Action.COLLECT
    }

    deferable: list[dict[str, object]] = []
    for move in max_tier:
        if move.action is not Action.PLACE or move.hand_index not in collect_indexes:
            continue
        vector = nonzero_weight_vector(state, move, policy)
        if any(item["contribution"] != 0 for item in vector.values()):
            continue
        deferable.append(
            {
                "move": move_record(state, move),
                "weighted_feature_vector": vector,
            }
        )

    if not deferable:
        return None

    same_card_collects = [
        move_record(state, move)
        for move in max_tier
        if move.action is Action.COLLECT
        and any(
            item["move"]["hand_index"] == move.hand_index
            for item in deferable
        )
    ]
    return {
        "transition_id": transition_id,
        "eligibility_path": eligibility_path,
        "max_score": max_score,
        "max_tier_size": len(max_tier),
        "same_card_collects": same_card_collects,
        "deferable_placements": deferable,
        "max_tier": [move_record(state, move) for move in max_tier],
    }


def replay_seed(seed: int, deck) -> tuple[list[dict[str, object]], list[dict[str, object]], int]:
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    policy = VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
    action_records: list[dict[str, object]] = []
    triggers: list[dict[str, object]] = []
    refreshes = 0

    for _ in range(1000):
        if state.won or state.board.open_tunnels == 0:
            break
        if not state.hand and not state.draw_pile:
            break

        transition_id = f"{seed}:a{state.turns + 1}:s{state.turns}"
        footprint = decision_footprint(state, policy, transition_id)

        selected = policy.choose(state, rng)
        if selected is None:
            if state.refresh_unplayable_hand():
                refreshes += 1
                continue
            break

        selected_record = move_record(state, selected)
        action_records.append(
            {"transition_id": transition_id, "move": selected_record}
        )
        if footprint is not None:
            deferable_moves = [
                item["move"] for item in footprint["deferable_placements"]
            ]
            footprint["historical_v5_selected_move"] = selected_record
            footprint["historical_selected_deferable"] = (
                selected_record in deferable_moves
            )
            triggers.append(footprint)

        # Apply only the historical frozen V5 choice. The diagnostic filter is
        # never used for selection and never changes trajectory.
        state.apply(selected)
    else:
        raise AssertionError(f"step limit reached for seed {seed}")

    return action_records, triggers, refreshes


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    all_triggers: list[dict[str, object]] = []
    integrity: dict[str, object] = {
        "expected_seed_count": len(SEEDS),
        "exact_sequence_matches": 0,
        "mismatches": [],
    }
    total_actions = 0
    total_refreshes = 0

    for seed in SEEDS:
        records, triggers, refreshes = replay_seed(seed, deck)
        encoded = json.dumps(
            records, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        expected_count, expected_hash = EXPECTED[seed]
        match = len(records) == expected_count and digest == expected_hash
        if match:
            integrity["exact_sequence_matches"] += 1
        else:
            integrity["mismatches"].append(
                {
                    "seed": seed,
                    "expected_count": expected_count,
                    "actual_count": len(records),
                    "expected_sha256": expected_hash,
                    "actual_sha256": digest,
                }
            )
        total_actions += len(records)
        total_refreshes += refreshes
        for trigger in triggers:
            trigger["seed"] = seed
        all_triggers.extend(triggers)

    target = next(
        (item for item in all_triggers if item["transition_id"] == TARGET),
        None,
    )
    target_expected_collect = {
        "action": "collect",
        "card_id": "photo-3-r2-c2",
        "hand_index": 2,
        "origin": None,
        "quarter_turns": 0,
    }
    target_expected_place = {
        "action": "place",
        "card_id": "photo-3-r2-c2",
        "hand_index": 2,
        "origin": [-4, 1],
        "quarter_turns": 0,
    }
    target_fact_ok = bool(
        target
        and target["max_score"] == 0
        and target["max_tier_size"] == 2
        and target_expected_collect in target["same_card_collects"]
        and any(
            item["move"] == target_expected_place
            for item in target["deferable_placements"]
        )
        and target["historical_v5_selected_move"] == target_expected_place
        and target["historical_selected_deferable"] is True
    )

    trigger_seeds = sorted({item["seed"] for item in all_triggers})
    selected_deferable = [
        item["transition_id"]
        for item in all_triggers
        if item["historical_selected_deferable"]
    ]
    regression = {2238, 2282}
    unchanged_win = {2005, 2286, 2371}
    unchanged_nonwin = set(SEEDS) - regression - unchanged_win

    total_deferable = sum(
        len(item["deferable_placements"]) for item in all_triggers
    )
    all_contract_rows_valid = all(
        item["same_card_collects"]
        and all(
            all(
                component["contribution"] == 0
                for component in placement["weighted_feature_vector"].values()
            )
            for placement in item["deferable_placements"]
        )
        for item in all_triggers
    )

    integrity_passed = (
        integrity["exact_sequence_matches"] == len(SEEDS)
        and not integrity["mismatches"]
        and total_actions == 1381
        and target_fact_ok
    )
    if not integrity_passed:
        classification = "same_card_neutral_deferral_diagnostic_invalid"
    elif not target:
        classification = "same_card_neutral_deferral_target_not_captured"
    elif not all_contract_rows_valid:
        classification = "same_card_neutral_deferral_contract_invalid"
    else:
        classification = "same_card_neutral_deferral_semantically_bounded"

    result = {
        "schema": "bandido-alcatraz-v5-same-card-neutral-deferral-footprint",
        "schema_version": 1,
        "dataset_status": "already-spent / selected / development / diagnostic / non-confirmatory",
        "seed_scope": list(SEEDS),
        "integrity": {
            **integrity,
            "total_action_decisions": total_actions,
            "total_refreshes_replayed": total_refreshes,
            "target_worker16_fact_reconstructed": target_fact_ok,
            "passed": integrity_passed,
        },
        "metrics": {
            "total_action_decisions_audited": total_actions,
            "trigger_decisions": len(all_triggers),
            "trigger_seed_count": len(trigger_seeds),
            "trigger_seeds": trigger_seeds,
            "total_deferable_placements": total_deferable,
            "historical_selected_deferable_count": len(selected_deferable),
            "historical_selected_deferable_transition_ids": selected_deferable,
            "trigger_transition_ids": [
                item["transition_id"] for item in all_triggers
            ],
            "target_triggers": target is not None,
            "target_historical_selected_is_deferable": bool(
                target and target["historical_selected_deferable"]
            ),
        },
        "descriptive_overlap": {
            "regression_trigger_seeds": sorted(set(trigger_seeds) & regression),
            "unchanged_win_trigger_seeds": sorted(
                set(trigger_seeds) & unchanged_win
            ),
            "unchanged_nonwin_trigger_seeds": sorted(
                set(trigger_seeds) & unchanged_nonwin
            ),
            "note": "Descriptive spent-data overlap only; not an acceptance gate.",
        },
        "triggers": all_triggers,
        "classification": classification,
        "candidate_executed": False,
        "modified_policy_replayed": False,
        "fresh_seeds_used": False,
        "holdout_used": False,
    }
    artifact_dir = ROOT / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    artifact_path = artifact_dir / "slice18-same-card-neutral-deferral-footprint.json"
    artifact_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("WORKER18_RESULT=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
