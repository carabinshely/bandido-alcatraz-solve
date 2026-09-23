from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, legal_moves
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready

ROOT = Path(__file__).parents[1]
HISTORICAL_COMMIT = "5682d7b4979790d62df6b9155307021fb4177348"
HISTORICAL_PATH = "experiments/real-deck-policy-v4/exit-placement-capacity-audit-2026-09-22.json"
OVERLAP_ERROR = "only a visible water cell may be covered"
ADJACENCY_ERRORS = {
    "tunnel/earth mismatch with adjacent card",
    "water cover must preserve the covered tunnel/earth pattern",
}

PERSISTENT = [
    "2001:a25:s24", "2004:a8:s7", "2020:a22:s21", "2024:a20:s19",
    "2034:a18:s17", "2084:a18:s17", "2098:a17:s16", "2104:a6:s5",
    "2110:a15:s14", "2129:a21:s20", "2130:a26:s25", "2138:a12:s11",
    "2168:a35:s34", "2171:a23:s22", "2212:a34:s33", "2314:a22:s21",
    "2334:a13:s12", "2372:a17:s16",
]
EARLIER_RECOVERED = [
    "2001:a16:s15", "2004:a5:s4", "2024:a14:s13", "2034:a9:s8",
    "2034:a15:s14", "2110:a12:s11", "2129:a17:s16", "2130:a19:s18",
    "2168:a26:s25", "2168:a30:s29", "2314:a20:s19", "2372:a13:s12",
]
WINNING_RECOVERED = [
    "2005:a7:s6", "2238:a23:s22", "2282:a6:s5", "2286:a10:s9",
    "2371:a11:s10",
]
EXPECTED_IDS = set(PERSISTENT + EARLIER_RECOVERED + WINNING_RECOVERED)
EXPECTED_SEEDS = sorted({int(x.split(":", 1)[0]) for x in EXPECTED_IDS})

EXPECTED_FINALS = {
  "2001": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 2, "raincoats": 8, "ropes": 6, "turns": 34, "visible_water": 0, "won": False},
  "2004": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 3, "raincoats": 12, "ropes": 8, "turns": 29, "visible_water": 0, "won": False},
  "2005": {"equipment_ready": True, "exit_equipment_water_ready": True, "exit_placed": True, "failure_reason": "win", "final_open_tunnels": 0, "raincoats": 4, "ropes": 2, "turns": 31, "visible_water": 0, "won": True},
  "2020": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 3, "raincoats": 12, "ropes": 7, "turns": 35, "visible_water": 0, "won": False},
  "2024": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 2, "raincoats": 9, "ropes": 6, "turns": 32, "visible_water": 0, "won": False},
  "2034": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 1, "raincoats": 11, "ropes": 7, "turns": 31, "visible_water": 0, "won": False},
  "2084": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 1, "raincoats": 11, "ropes": 8, "turns": 33, "visible_water": 0, "won": False},
  "2098": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 4, "raincoats": 11, "ropes": 6, "turns": 30, "visible_water": 0, "won": False},
  "2104": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 3, "raincoats": 12, "ropes": 8, "turns": 26, "visible_water": 0, "won": False},
  "2110": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 2, "raincoats": 11, "ropes": 8, "turns": 31, "visible_water": 0, "won": False},
  "2129": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 1, "raincoats": 12, "ropes": 6, "turns": 34, "visible_water": 0, "won": False},
  "2130": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 4, "raincoats": 10, "ropes": 7, "turns": 35, "visible_water": 0, "won": False},
  "2138": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 3, "raincoats": 10, "ropes": 7, "turns": 27, "visible_water": 0, "won": False},
  "2168": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 2, "raincoats": 6, "ropes": 6, "turns": 41, "visible_water": 0, "won": False},
  "2171": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 3, "raincoats": 11, "ropes": 7, "turns": 36, "visible_water": 0, "won": False},
  "2212": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 5, "raincoats": 9, "ropes": 6, "turns": 44, "visible_water": 0, "won": False},
  "2238": {"equipment_ready": True, "exit_equipment_water_ready": True, "exit_placed": True, "failure_reason": "win", "final_open_tunnels": 0, "raincoats": 4, "ropes": 3, "turns": 32, "visible_water": 0, "won": True},
  "2282": {"equipment_ready": True, "exit_equipment_water_ready": True, "exit_placed": True, "failure_reason": "win", "final_open_tunnels": 0, "raincoats": 3, "ropes": 4, "turns": 20, "visible_water": 0, "won": True},
  "2286": {"equipment_ready": True, "exit_equipment_water_ready": True, "exit_placed": True, "failure_reason": "win", "final_open_tunnels": 0, "raincoats": 3, "ropes": 3, "turns": 16, "visible_water": 0, "won": True},
  "2314": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 2, "raincoats": 11, "ropes": 7, "turns": 33, "visible_water": 0, "won": False},
  "2334": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 4, "raincoats": 12, "ropes": 6, "turns": 28, "visible_water": 0, "won": False},
  "2371": {"equipment_ready": True, "exit_equipment_water_ready": True, "exit_placed": True, "failure_reason": "win", "final_open_tunnels": 0, "raincoats": 7, "ropes": 4, "turns": 24, "visible_water": 0, "won": True},
  "2372": {"equipment_ready": True, "exit_equipment_water_ready": False, "exit_placed": False, "failure_reason": "no_legal_move", "final_open_tunnels": 3, "raincoats": 8, "ropes": 8, "turns": 29, "visible_water": 0, "won": False},
}

def cohort_for(transition_id: str) -> str:
    if transition_id in PERSISTENT:
        return "persistent"
    if transition_id in EARLIER_RECOVERED:
        return "earlier_recovered"
    if transition_id in WINNING_RECOVERED:
        return "winning_recovered"
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
        "exit_equipment_water_ready": state.exit_placed and state.board.visible_water_cells == 0 and ready,
    }

def move_signature(state: GameState, move) -> dict:
    card = state.hand[move.hand_index]
    return {
        "action": move.action.value,
        "card_id": card.card_id,
        "hand_index": move.hand_index,
        "origin": list(move.origin) if move.origin is not None else None,
        "quarter_turns": move.quarter_turns,
        "is_exit": card.is_exit,
        "material": card.material.value if card.material is not None else None,
    }

def exit_cell_roles(exit_card, quarter_turns: int):
    rotated = exit_card.rotated(quarter_turns)
    cells = {(cell.x, cell.y): cell for cell in rotated.cells}
    delta = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
    external = {}
    for coord, cell in cells.items():
        edges = []
        for edge in cell.tunnel_edges:
            dx, dy = delta[edge.value]
            if (coord[0] + dx, coord[1] + dy) not in cells:
                edges.append(edge.value)
        external[coord] = edges
    connectable = [coord for coord, edges in external.items() if edges]
    terminal = [coord for coord, edges in external.items() if not edges]
    if len(connectable) != 1 or len(terminal) != 1 or sum(map(len, external.values())) != 1:
        raise AssertionError("unexpected EXIT geometry")
    return connectable[0], terminal[0]

def exit_capacity(board, exit_card) -> dict:
    moves = legal_moves(board, (exit_card,))
    placements = []
    targets = set()
    for move in moves:
        if move.action is not Action.PLACE or move.origin is None:
            raise AssertionError("EXIT capacity contains non-placement move")
        connectable, terminal = exit_cell_roles(exit_card, move.quarter_turns)
        target = (move.origin[0] + connectable[0], move.origin[1] + connectable[1])
        terminal_global = (move.origin[0] + terminal[0], move.origin[1] + terminal[1])
        if target not in board.open_tunnel_target_counts:
            raise AssertionError("legal EXIT move is not attached at open frontier")
        targets.add(target)
        placements.append({
            "origin": list(move.origin),
            "quarter_turns": move.quarter_turns,
            "frontier_target": list(target),
            "terminal_cell": list(terminal_global),
        })
    return {
        "exit_legal_move_count": len(moves),
        "exit_compatible_frontier_target_count": len(targets),
        "frontier_targets": [list(x) for x in sorted(targets)],
        "placements": placements,
    }

def core_capacity(capacity: dict) -> dict:
    return {
        "exit_legal_move_count": capacity["exit_legal_move_count"],
        "exit_compatible_frontier_target_count": capacity["exit_compatible_frontier_target_count"],
        "frontier_targets": capacity["frontier_targets"],
    }

def chosen_global_cells(card, move) -> set[tuple[int, int]]:
    if move.origin is None:
        return set()
    rotated = card.rotated(move.quarter_turns)
    return {
        (move.origin[0] + cell.x, move.origin[1] + cell.y)
        for cell in rotated.cells
    }

def classify_false(rows: list[dict]) -> str:
    frontier_removed = any(not row["remained_open_frontier"] for row in rows)
    adjacency = any(row["engine_rejection"] in ADJACENCY_ERRORS for row in rows)
    terminal_overlap = any(
        row["remained_open_frontier"]
        and row["terminal_cell_occupied_by_chosen_card"]
        and row["engine_rejection"] == OVERLAP_ERROR
        for row in rows
    )
    other = any(
        row["remained_open_frontier"]
        and row["engine_rejection"] not in ADJACENCY_ERRORS
        and row["engine_rejection"] != OVERLAP_ERROR
        for row in rows
    )
    flags = sum(bool(x) for x in (frontier_removed, adjacency, terminal_overlap, other))
    if frontier_removed and flags == 1:
        return "frontier_removed_or_closed"
    if adjacency and flags == 1:
        return "adjacency_changed"
    if flags > 1:
        return "mixed"
    return "other"

def audit_transition(state: GameState, move, exit_card, historical_row: dict) -> dict:
    before = exit_capacity(state.board, exit_card)
    card = state.hand[move.hand_index]
    if move.action is not Action.PLACE or card.is_exit or move.origin is None:
        raise AssertionError("target transition is not an ordinary placement")

    after_board = state.board.clone()
    after_board.place(card, move.origin, move.quarter_turns)
    after = exit_capacity(after_board, exit_card)
    chosen_cells = chosen_global_cells(card, move)
    after_frontier = set(after_board.open_tunnel_target_counts)

    placement_rows = []
    for placement in before["placements"]:
        target = tuple(placement["frontier_target"])
        terminal = tuple(placement["terminal_cell"])
        error = None
        try:
            after_board.clone()._prepare_placement(
                exit_card,
                tuple(placement["origin"]),
                placement["quarter_turns"],
            )
        except ValueError as exc:
            error = str(exc)
        placement_rows.append({
            "frontier_target": placement["frontier_target"],
            "remained_open_frontier": target in after_frontier,
            "terminal_cell": placement["terminal_cell"],
            "terminal_cell_occupied_by_chosen_card": terminal in chosen_cells,
            "engine_rejection": error,
        })

    direct = (
        before["exit_legal_move_count"] > 0
        and after["exit_legal_move_count"] == 0
        and bool(placement_rows)
        and all(row["remained_open_frontier"] for row in placement_rows)
        and all(row["terminal_cell_occupied_by_chosen_card"] for row in placement_rows)
        and all(row["engine_rejection"] == OVERLAP_ERROR for row in placement_rows)
    )
    affected = {}
    for row in placement_rows:
        key = tuple(row["frontier_target"])
        entry = affected.setdefault(key, {"target": list(key), "remained_open_frontier": True})
        entry["remained_open_frontier"] = entry["remained_open_frontier"] and row["remained_open_frontier"]

    transition_id = f"{historical_row['seed']}:a{historical_row['action_turn']}:s{historical_row['state_turn_before_action']}"
    return {
        "transition_id": transition_id,
        "cohort": cohort_for(transition_id),
        "chosen_action": move_signature(state, move),
        "before_exit_legal_capacity": core_capacity(before),
        "after_exit_legal_capacity": core_capacity(after),
        "affected_compatible_frontier_targets": [affected[k] for k in sorted(affected)],
        "remained_open_frontier": all(row["remained_open_frontier"] for row in placement_rows),
        "terminal_cell_coordinates": sorted({tuple(row["terminal_cell"]) for row in placement_rows}),
        "occupied_by_chosen_card": all(row["terminal_cell_occupied_by_chosen_card"] for row in placement_rows),
        "engine_rejections": [row["engine_rejection"] for row in placement_rows],
        "placement_evidence": placement_rows,
        "direct_terminal_half_kill": direct,
        "false_classification": None if direct else classify_false(placement_rows),
    }

def load_historical_rows() -> dict[str, dict]:
    raw = subprocess.run(
        ["git", "show", f"{HISTORICAL_COMMIT}:{HISTORICAL_PATH}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    payload = json.loads(raw)
    rows = payload["all_last_slot_killing_decisions"]
    by_id = {
        f"{row['seed']}:a{row['action_turn']}:s{row['state_turn_before_action']}": row
        for row in rows
    }
    if set(by_id) != EXPECTED_IDS:
        raise AssertionError({
            "historical_ids_missing": sorted(EXPECTED_IDS - set(by_id)),
            "historical_ids_extra": sorted(set(by_id) - EXPECTED_IDS),
        })
    return by_id

def replay_seed(seed: int, deck, historical_rows: dict[str, dict]):
    rng = Random(seed)
    policy = BoundedMergeV4Policy(setup_weight=250)
    state = GameState.new(start_card=deck.start_easy, deck=deck.draw_deck(), hand_size=3, rng=rng)
    transition_records = []
    transition_mismatches = []

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
        if transition_id in historical_rows:
            historical = historical_rows[transition_id]
            signature = move_signature(state, move)
            expected_signature = historical["chosen_action"]
            before = core_capacity(exit_capacity(state.board, deck.exit_card))
            expected_before = historical["local_preventability_audit"]["before_capacity"]

            card = state.hand[move.hand_index]
            post_board = state.board.clone()
            if move.action is Action.PLACE:
                post_board.place(card, move.origin, move.quarter_turns)
            after = core_capacity(exit_capacity(post_board, deck.exit_card))
            expected_after = historical["local_preventability_audit"]["after_capacity"]

            mismatch = {}
            if signature != expected_signature:
                mismatch["chosen_action"] = {"expected": expected_signature, "actual": signature}
            if before != expected_before:
                mismatch["before_capacity"] = {"expected": expected_before, "actual": before}
            if after != expected_after:
                mismatch["after_capacity"] = {"expected": expected_after, "actual": after}
            if mismatch:
                transition_mismatches.append({"transition_id": transition_id, **mismatch})
            transition_records.append(audit_transition(state, move, deck.exit_card, historical))

        state.apply(move)
    else:
        reason = "step_limit"

    actual_final = final_record(state, reason)
    expected_final = EXPECTED_FINALS[str(seed)]
    final_mismatch = None if actual_final == expected_final else {
        "seed": seed,
        "expected": expected_final,
        "actual": actual_final,
    }
    return transition_records, transition_mismatches, final_mismatch, actual_final

def summarize(records: list[dict], ids: list[str]) -> dict:
    selected = [row for row in records if row["transition_id"] in ids]
    true_ids = [row["transition_id"] for row in selected if row["direct_terminal_half_kill"]]
    false_rows = [row for row in selected if not row["direct_terminal_half_kill"]]
    counts = Counter(row["false_classification"] for row in false_rows)
    return {
        "total": len(selected),
        "true": len(true_ids),
        "true_fraction": len(true_ids) / len(selected) if selected else 0.0,
        "false": len(false_rows),
        "true_transition_ids": true_ids,
        "false_transition_ids": [row["transition_id"] for row in false_rows],
        "false_mechanism_counts": {name: counts.get(name, 0) for name in [
            "frontier_removed_or_closed", "adjacency_changed", "mixed", "other"
        ]},
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    historical_rows = load_historical_rows()
    deck = load_real_deck(ROOT / "data")
    all_records = []
    transition_mismatches = []
    final_mismatches = []
    finals = {}

    for seed in EXPECTED_SEEDS:
        records, tm, fm, final = replay_seed(seed, deck, historical_rows)
        all_records.extend(records)
        transition_mismatches.extend(tm)
        if fm is not None:
            final_mismatches.append(fm)
        finals[str(seed)] = final

    observed_ids = {row["transition_id"] for row in all_records}
    missing_ids = sorted(EXPECTED_IDS - observed_ids)
    extra_ids = sorted(observed_ids - EXPECTED_IDS)
    if missing_ids or extra_ids:
        transition_mismatches.append({"missing_ids": missing_ids, "extra_ids": extra_ids})

    integrity = {
        "seed_scope": {
            "expected_distinct_seeds": 23,
            "replayed_distinct_seeds": len(EXPECTED_SEEDS),
            "fresh_seeds_used": False,
            "passed": len(EXPECTED_SEEDS) == 23,
        },
        "final_records": {
            "records_compared": 23,
            "exact_matches": 23 - len(final_mismatches),
            "mismatches": final_mismatches,
            "passed": not final_mismatches,
        },
        "transition_identities": {
            "records_compared": 35,
            "exact_matches": 35 - len(transition_mismatches),
            "mismatches": transition_mismatches,
            "passed": not transition_mismatches,
        },
    }
    integrity_passed = all(section["passed"] for section in integrity.values())

    payload = {
        "schema": "bandido-alcatraz-preloss-direct-terminal-half-kill-audit",
        "schema_version": 1,
        "experiment_id": "worker-9-direct-terminal-half-kill",
        "dataset_status": "already-spent / diagnostic / non-confirmatory",
        "date": "2026-09-23",
        "starting_main": "87b8d3eeff3aaf53c5e887679360652a3f9e8d04",
        "evaluated_commit": os.environ.get("EVALUATED_COMMIT") or os.environ.get("GITHUB_SHA"),
        "workflow_run": {
            "run_id": int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None,
            "url": f"https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/{os.environ.get('GITHUB_RUN_ID')}" if os.environ.get("GITHUB_RUN_ID") else None,
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
        "transition_ids": {
            "persistent": PERSISTENT,
            "earlier_recovered": EARLIER_RECOVERED,
            "winning_recovered": WINNING_RECOVERED,
        },
        "replay_integrity": integrity,
        "integrity_passed": integrity_passed,
        "transition_records": all_records,
        "final_records": finals,
    }

    if integrity_passed:
        persistent = summarize(all_records, PERSISTENT)
        earlier = summarize(all_records, EARLIER_RECOVERED)
        winning = summarize(all_records, WINNING_RECOVERED)
        reversible_ids = EARLIER_RECOVERED + WINNING_RECOVERED
        reversible = summarize(all_records, reversible_ids)
        persistent_true = persistent["true"]
        reversible_true = reversible["true"]
        if persistent_true >= 16 and reversible_true <= 2:
            classification = "direct_terminal_half_kill_discriminator_supported_for_v5_design"
        elif persistent_true <= 13 or reversible_true >= 6:
            classification = "direct_terminal_half_kill_discriminator_not_supported"
        else:
            classification = "direct_terminal_half_kill_discriminator_ambiguous"
        global_false = Counter(
            row["false_classification"] for row in all_records if not row["direct_terminal_half_kill"]
        )
        payload.update({
            "cohort_results": {
                "persistent": persistent,
                "earlier_recovered": earlier,
                "winning_recovered": winning,
                "reversible_combined": reversible,
            },
            "persistent_false_negatives": persistent["false_transition_ids"],
            "reversible_false_positives": reversible["true_transition_ids"],
            "false_case_mechanism_distribution": {
                name: global_false.get(name, 0)
                for name in ["frontier_removed_or_closed", "adjacency_changed", "mixed", "other"]
            },
            "final_classification": classification,
        })

    out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("WORKER9_INTEGRITY=" + json.dumps(integrity, sort_keys=True))
    if integrity_passed:
        print("WORKER9_RESULT=" + json.dumps({
            "cohort_results": payload["cohort_results"],
            "classification": payload["final_classification"],
            "false_case_mechanism_distribution": payload["false_case_mechanism_distribution"],
        }, sort_keys=True))
    else:
        raise SystemExit("replay integrity gate failed; discriminator not interpreted")

if __name__ == "__main__":
    main()
