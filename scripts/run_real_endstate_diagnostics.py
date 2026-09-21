from collections import Counter
import json
from pathlib import Path

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import GreedyV0Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


ROOT = Path(__file__).parents[1]


def main() -> None:
    deck = load_real_deck(ROOT / "data")
    results = [
        play_game(
            start_card=deck.start_easy,
            deck=deck.draw_deck(),
            hand_size=3,
            policy=GreedyV0Policy(),
            seed=seed,
        )
        for seed in range(100)
    ]

    top_states = Counter(
        (
            result.open_tunnels,
            result.visible_water_cells,
            result.raincoats,
            result.ropes,
            result.exit_placed,
            result.reason,
        )
        for result in results
    )

    payload = {
        "rules_variant": "v0-threshold-equipment",
        "policy": "greedy_v0",
        "seed_range": [0, 99],
        "games": len(results),
        "wins": sum(result.won for result in results),
        "exit_placed": sum(result.exit_placed for result in results),
        "equipment_ready": sum(
            is_equipment_ready(result.raincoats, result.ropes)
            for result in results
        ),
        "water_clear": sum(
            result.visible_water_cells == 0 for result in results
        ),
        "exit_equipment_water_ready": sum(
            result.exit_placed
            and is_equipment_ready(result.raincoats, result.ropes)
            and result.visible_water_cells == 0
            for result in results
        ),
        "open_tunnels_histogram": dict(
            sorted(Counter(result.open_tunnels for result in results).items())
        ),
        "water_histogram": dict(
            sorted(
                Counter(
                    result.visible_water_cells for result in results
                ).items()
            )
        ),
        "raincoat_histogram": dict(
            sorted(Counter(result.raincoats for result in results).items())
        ),
        "rope_histogram": dict(
            sorted(Counter(result.ropes for result in results).items())
        ),
        "failure_reasons": dict(Counter(result.reason for result in results)),
        "top_final_states": [
            {
                "open_tunnels": state[0],
                "visible_water": state[1],
                "raincoats": state[2],
                "ropes": state[3],
                "exit_placed": state[4],
                "reason": state[5],
                "count": count,
            }
            for state, count in top_states.most_common(10)
        ],
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
