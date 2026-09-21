import json
from pathlib import Path
from random import Random

from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import CombinedV2Policy, CombinedV3Policy


ROOT = Path(__file__).parents[1]


def trace(policy_name, policy, seed):
    deck = load_real_deck(ROOT / "data")
    rng = Random(seed)
    state = GameState.new(
        start_card=deck.start_easy,
        deck=deck.draw_deck(),
        hand_size=3,
        rng=rng,
    )
    rows = []

    for step in range(1000):
        if state.won:
            return {
                "policy": policy_name,
                "won": True,
                "reason": "win",
                "turns": state.turns,
                "rows": rows,
                "final": final_state(state),
            }

        if state.board.open_tunnels == 0:
            return {
                "policy": policy_name,
                "won": False,
                "reason": "closed_tunnels_conditions_failed",
                "turns": state.turns,
                "rows": rows,
                "final": final_state(state),
            }

        if not state.hand and not state.draw_pile:
            return {
                "policy": policy_name,
                "won": False,
                "reason": "deck_exhausted",
                "turns": state.turns,
                "rows": rows,
                "final": final_state(state),
            }

        move = policy.choose(state, rng)
        if move is None:
            before_hand = [card.card_id for card in state.hand]
            if state.refresh_unplayable_hand():
                rows.append(
                    {
                        "turn": state.turns,
                        "event": "refresh",
                        "hand_before": before_hand,
                        "open": state.board.open_tunnels,
                        "water": state.board.visible_water_cells,
                        "merge": state.board.merge_opportunities,
                    }
                )
                continue
            return {
                "policy": policy_name,
                "won": False,
                "reason": "no_legal_move",
                "turns": state.turns,
                "rows": rows,
                "final": final_state(state),
            }

        card = state.hand[move.hand_index]
        before = final_state(state)
        row = {
            "turn": state.turns + 1,
            "event": move.action.value,
            "card": card.card_id,
            "card_degree": card.external_tunnel_count,
            "material": card.material.value if card.material else None,
            "is_exit": card.is_exit,
            "origin": list(move.origin) if move.origin is not None else None,
            "quarter_turns": move.quarter_turns,
            "before": before,
        }

        state.apply(move)
        after = final_state(state)
        row["after"] = after
        row["delta_open"] = after["open"] - before["open"]
        row["delta_water"] = after["water"] - before["water"]
        row["delta_merge"] = after["merge"] - before["merge"]
        row["delta_water_obstruction"] = (
            after["water_obstruction"] - before["water_obstruction"]
        )
        rows.append(row)

    return {
        "policy": policy_name,
        "won": state.won,
        "reason": "step_limit",
        "turns": state.turns,
        "rows": rows,
        "final": final_state(state),
    }


def final_state(state):
    return {
        "open": state.board.open_tunnels,
        "water": state.board.visible_water_cells,
        "merge": state.board.merge_opportunities,
        "water_obstruction": state.board.water_obstruction,
        "trapped_water": state.board.trapped_water_cells,
        "raincoats": state.raincoats,
        "ropes": state.ropes,
        "exit_placed": state.exit_placed,
        "draw_remaining": len(state.draw_pile),
        "hand_size": len(state.hand),
    }


def compact(trace_data):
    rows = trace_data["rows"]
    interesting = []
    previous = None
    for row in rows:
        if row["event"] == "refresh":
            interesting.append(row)
            continue
        before = row["before"]
        after = row["after"]
        important = (
            row["event"] == Action.COLLECT.value
            or row["is_exit"]
            or row["delta_water"] != 0
            or row["delta_open"] < 0
            or row["delta_merge"] != 0
            or after["trapped_water"] != before["trapped_water"]
        )
        if important:
            interesting.append(row)
        previous = row
    return {
        "policy": trace_data["policy"],
        "won": trace_data["won"],
        "reason": trace_data["reason"],
        "turns": trace_data["turns"],
        "final": trace_data["final"],
        "interesting_rows": interesting,
    }


def main():
    seed = 24
    traces = [
        trace("combined_v2", CombinedV2Policy(), seed),
        trace("combined_v3", CombinedV3Policy(), seed),
    ]
    print(
        json.dumps(
            {
                "seed": seed,
                "rules_variant": "v0-threshold-equipment",
                "traces": [compact(item) for item in traces],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
