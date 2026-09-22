import json
from pathlib import Path

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, WaterSpaceV3Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game


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


def main():
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
    }, sort_keys=True))


if __name__ == "__main__":
    main()
