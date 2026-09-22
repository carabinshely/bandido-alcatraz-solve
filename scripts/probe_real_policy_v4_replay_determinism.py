import json
import os
from pathlib import Path
from random import Random
import subprocess
import sys

from bandido_alcatraz.game import GameState
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, WaterSpaceV3Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game
from bandido_alcatraz.strategy import move_features, score_features


ROOT = Path(__file__).parents[1]
RECEIPT = ROOT / "experiments" / "real-deck-policy-v4" / "stability-holdout-2026-09-21.json"
CASES = {
    "bounded_merge_v4_250": [2066, 2103, 2218, 2292, 2309, 2320, 2385],
    "water_space_v3": [2062, 2071, 2096, 2099, 2105, 2109, 2114, 2129, 2136, 2141, 2143, 2155, 2156],
}


def final_record(result):
    equipment_ready = is_equipment_ready(result.raincoats, result.ropes)
    return {
        "won": result.won,
        "turns": result.turns,
        "final_open_tunnels": result.open_tunnels,
        "visible_water": result.visible_water_cells,
        "raincoats": result.raincoats,
        "ropes": result.ropes,
        "equipment_ready": equipment_ready,
        "exit_placed": result.exit_placed,
        "exit_equipment_water_ready": (
            result.exit_placed
            and result.visible_water_cells == 0
            and equipment_ready
        ),
        "reason": result.reason,
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


def child_trace(seed):
    deck = load_real_deck(ROOT / "data")
    policy = BoundedMergeV4Policy(setup_weight=250)
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    rows = []
    for _ in range(1000):
        if state.won or state.board.open_tunnels == 0 or (
            not state.hand and not state.draw_pile
        ):
            break

        moves = state.legal_moves()
        if moves:
            scored = [
                (
                    score_features(move_features(state, move), policy.weights),
                    move,
                )
                for move in moves
            ]
            best = max(score for score, _ in scored)
            best_candidates = [
                move_signature(state, move)
                for score, move in scored
                if score == best
            ]
        else:
            best_candidates = []

        move = policy.choose(state, rng)
        if move is None:
            rows.append({
                "state_turn": state.turns,
                "event": "refresh_or_stop",
                "best_candidates": best_candidates,
                "chosen": None,
            })
            if state.refresh_unplayable_hand():
                continue
            break

        chosen = move_signature(state, move)
        rows.append({
            "state_turn": state.turns,
            "event": "move",
            "best_candidates": best_candidates,
            "chosen": chosen,
        })
        state.apply(move)

    result = {
        "hash_seed": os.environ.get("PYTHONHASHSEED"),
        "seed": seed,
        "rows": rows,
        "final": {
            "won": state.won,
            "turns": state.turns,
            "open_tunnels": state.board.open_tunnels,
            "visible_water": state.board.visible_water_cells,
            "raincoats": state.raincoats,
            "ropes": state.ropes,
            "exit_placed": state.exit_placed,
        },
    }
    print("HASH_CHILD_JSON=" + json.dumps(result, sort_keys=True))


def hash_probe():
    traces = {}
    for hash_seed in ("0", "1", "2", "3"):
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = hash_seed
        proc = subprocess.run(
            [sys.executable, __file__, "--hash-child", "2066"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        line = next(
            line
            for line in proc.stdout.splitlines()
            if line.startswith("HASH_CHILD_JSON=")
        )
        traces[hash_seed] = json.loads(line.split("=", 1)[1])

    first_divergence = None
    max_rows = max(len(trace["rows"]) for trace in traces.values())
    for index in range(max_rows):
        snapshots = {}
        for hash_seed, trace in traces.items():
            row = trace["rows"][index] if index < len(trace["rows"]) else None
            snapshots[hash_seed] = row
        serialized = {
            json.dumps(row, sort_keys=True)
            for row in snapshots.values()
        }
        if len(serialized) > 1:
            first_divergence = {
                "row_index": index,
                "by_hash_seed": snapshots,
            }
            break

    return {
        "seed": 2066,
        "policy": "bounded_merge_v4_250",
        "hash_seeds": list(traces),
        "final_by_hash_seed": {
            key: value["final"] for key, value in traces.items()
        },
        "first_divergence": first_divergence,
    }


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--hash-child":
        child_trace(int(sys.argv[2]))
        return

    receipt = json.loads(RECEIPT.read_text())
    deck = load_real_deck(ROOT / "data")
    policies = {
        "bounded_merge_v4_250": BoundedMergeV4Policy(setup_weight=250),
        "water_space_v3": WaterSpaceV3Policy(),
    }
    rows = []
    for name, seeds in CASES.items():
        for seed in seeds:
            result = play_game(
                start_card=deck.start_easy,
                deck=deck.draw_deck(),
                hand_size=3,
                policy=policies[name],
                seed=seed,
            )
            actual = final_record(result)
            expected = receipt["metrics"][name]["per_seed"][str(seed)]
            rows.append({
                "policy": name,
                "seed": seed,
                "matches_receipt": actual == expected,
                "actual": actual,
                "expected": expected,
            })

    print("DETERMINISM_PROBE_JSON=" + json.dumps({
        "cases": len(rows),
        "matches": sum(row["matches_receipt"] for row in rows),
        "rows": rows,
        "hash_probe": hash_probe(),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
