"""Pure schema/physical-geometry helpers extracted unchanged from the accepted
Worker30 offline verifier SHA256 f4157246c5a403be63f5aabc23df17b1e59be85180eba96d410b072e0b8cd12b.
No Worker30 run acceptance logic, archive loader, engine, or policy is included.
"""
from collections import Counter
import hashlib
import json
import math

SOURCE_MAP_SHA256 = "27b4a000202d5e22b3e37ea128571cd7a5b8a4ef1a882514616c361cf2da0aed"

RULESET = "v2-exact-equipment-quota-limited-collect-full-hand-refresh"

SETUP_ID = "p1-easy-5-exit-hand6-first0-full-hand-refresh"

SETUP = {"player_count": 1, "start_side": "easy-5-exit", "hand_size": 6, "starting_player": 0}

DELTAS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}

OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}

MAX_MODEL_DATA_BYTES = 1024 * 1024

class Rejected(ValueError):
    """Evidence cannot establish the complete frozen baseline."""

def require(condition, message):
    if not condition:
        raise Rejected(message)

def canonical(value, newline=False):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + ("\n" if newline else "")).encode("utf-8")

def same(actual, expected, message):
    # JSON serialization also distinguishes True/1 and 1/1.0, unlike Python ==.
    require(canonical(actual) == canonical(expected), message)

def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected.split()), f"{label}: fields")

def integer(value, lower, upper, label):
    require(type(value) is int and lower <= value <= upper, f"{label}: integer/range")

def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def number(value):
        result = float(value)
        require(math.isfinite(result), "non-finite JSON number")
        return result

    def constant(value):
        raise Rejected(f"non-JSON number: {value}")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=constant)

def load_cards(data_dir, source):
    same(hashlib.sha256(canonical(source)).hexdigest(), SOURCE_MAP_SHA256,
         "source manifest is not the independently pinned accepted tree map")
    data = {}
    for name in ("deck-v1.json", "deck-observations-v0.json"):
        path = data_dir / name
        require(path.stat().st_size <= MAX_MODEL_DATA_BYTES, "accepted model data exceeds safety bound")
        with path.open("rb") as stream:
            raw = stream.read(MAX_MODEL_DATA_BYTES + 1)
        require(len(raw) <= MAX_MODEL_DATA_BYTES, "accepted model data exceeds safety bound")
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        same(blob, source[f"data/{name}"], f"accepted data changed: {name}")
        data[name] = strict_json(raw)
    cards = {}
    for item in data["deck-v1.json"]["instances"]:
        edges = [set(), set()]
        for port, half, direction in (("T", 0, "N"), ("B", 1, "S"), ("LU", 0, "W"),
                                      ("RU", 0, "E"), ("LL", 1, "W"), ("RL", 1, "E")):
            if port in item["external_ports"]:
                edges[half].add(direction)
        if item["internal_bridge"]:
            edges[0].add("S")
            edges[1].add("N")
        cells = [{"x": 0, "y": i, "tunnel_edges": sorted(edges[i]),
                  "water": item["water_half"] == half} for i, half in enumerate(("top", "bottom"))]
        cards[item["card_id"]] = {"material": item["material"], "cells": cells}
    for name in ("start_easy", "exit"):
        cells = data["deck-observations-v0.json"]["special_geometry"][name]["cells"]
        cards[name] = {"material": None, "cells": [dict(c, tunnel_edges=sorted(c["tunnel_edges"]))
                                                  for c in cells]}
    require(len(cards) == 70, "accepted physical card inventory")
    return cards

def coordinate(value):
    require(type(value) is list and len(value) == 2, "coordinate shape")
    for axis in value:
        integer(axis, -140, 140, "coordinate")
    return tuple(value)

def coordinates(value):
    require(type(value) is list, "coordinate list")
    result = [coordinate(item) for item in value]
    require(result == sorted(set(result)), "coordinates must be sorted and unique")
    return result

def validate_cells(cells):
    require(type(cells) is list and cells, "missing cell geometry")
    result = {}
    for cell in cells:
        keys(cell, "x y tunnel_edges water", "cell")
        point = coordinate([cell["x"], cell["y"]])
        require(point not in result, "duplicate visible coordinate")
        edges = cell["tunnel_edges"]
        require(type(edges) is list and all(type(e) is str and e in DELTAS for e in edges), "cell edges")
        require(edges == sorted(set(edges)), "cell edges must be sorted and unique")
        require(type(cell["water"]) is bool, "cell water must be boolean")
        result[point] = cell
    return result

def physical_placement(card, quarter_turns, origin):
    """Rotate pinned cells, normalize their footprint, then translate to the board.

    This reconstructs public geometry only; it does not decide move legality.
    """
    rotated = []
    directions = "NESW"
    for cell in card["cells"]:
        x, y = cell["x"], cell["y"]
        for _ in range(quarter_turns):
            x, y = -y, x
        edges = sorted(directions[(directions.index(edge) + quarter_turns) % 4]
                       for edge in cell["tunnel_edges"])
        rotated.append(dict(cell, x=x, y=y, tunnel_edges=edges))
    min_x = min(cell["x"] for cell in rotated)
    min_y = min(cell["y"] for cell in rotated)
    return {(cell["x"] - min_x + origin[0], cell["y"] - min_y + origin[1]):
            dict(cell, x=cell["x"] - min_x + origin[0], y=cell["y"] - min_y + origin[1])
            for cell in rotated}

def validate_record(record, seed, cards):
    keys(record, "seed result setup collected_equipment board", "record")
    same(record["seed"], seed, "record seed")
    same(record["setup"], SETUP, "record setup")
    result = record["result"]
    keys(result, "won turns open_tunnels visible_water_cells raincoats ropes exit_placed reason ruleset_id setup_id",
         "GameResult")
    for key in ("won", "exit_placed"):
        require(type(result[key]) is bool, f"{key}: boolean")
    for key, upper in (("turns", 69), ("open_tunnels", 560), ("visible_water_cells", 4),
                       ("raincoats", 3), ("ropes", 2)):
        integer(result[key], 0, upper, key)
    same(result["ruleset_id"], RULESET, "result ruleset")
    same(result["setup_id"], SETUP_ID, "result setup")
    require(result["reason"] in ("win", "closed_tunnels_conditions_failed", "deck_exhausted", "no_legal_move"),
            "unknown/step_limit result")
    victory = (result["exit_placed"] and result["open_tunnels"] == 0 and result["visible_water_cells"] == 0
               and result["raincoats"] == 3 and result["ropes"] == 2)
    same(result["won"], victory, "exact victory consistency")
    same(result["reason"] == "win", victory, "win reason consistency")
    same(result["reason"] == "closed_tunnels_conditions_failed",
         not victory and result["open_tunnels"] == 0, "closed-tunnel reason consistency")
    collected = record["collected_equipment"]
    require(type(collected) is list, "collected equipment list")
    used, materials, last_turn = set(), Counter(), 0
    for order, item in enumerate(collected, 1):
        keys(item, "order card_id material turn player_index cells", "collected equipment")
        same(item["order"], order, "collected order")
        same(item["player_index"], 0, "collected solo player")
        integer(item["turn"], last_turn + 1, result["turns"], "collected turn order")
        last_turn = item["turn"]
        card_id = item["card_id"]
        require(type(card_id) is str and card_id in cards and card_id not in used, "collected card ID")
        card = cards[card_id]
        require(card["material"] in ("raincoat", "rope"), "non-equipment collection")
        same(item["material"], card["material"], "collected material")
        same(item["cells"], card["cells"], "collected physical geometry")
        used.add(card_id)
        materials[item["material"]] += 1
    same([result["raincoats"], result["ropes"]], [materials["raincoat"], materials["rope"]], "collected counts")
    board = record["board"]
    keys(board, "placements visible_cells", "board")
    placements = board["placements"]
    require(type(placements) is list and placements, "missing placement history")
    same(result["turns"], len(placements) - 1 + len(collected), "action/placement/collection count")
    visible, last_owner = {}, {}
    for index, placement in enumerate(placements):
        keys(placement, "card_id origin quarter_turns placement_index kind cells overlaps covered_placement_index",
             "placement")
        same(placement["placement_index"], index, "placement order")
        card_id = placement["card_id"]
        require(type(card_id) is str and card_id in cards and card_id not in used, "placed card ID")
        require((index == 0) == (card_id == "start_easy"), "START identity/order")
        same(placement["kind"], "start" if index == 0 else "exit" if card_id == "exit" else "ordinary", "placement kind")
        origin = coordinate(placement["origin"])
        integer(placement["quarter_turns"], 0, 3, "rotation")
        if index == 0:
            same([placement["origin"], placement["quarter_turns"]], [[0, 0], 0], "START origin/rotation")
        footprint = coordinates(placement["cells"])
        geometry = physical_placement(cards[card_id], placement["quarter_turns"], origin)
        require(footprint == sorted(geometry), "placement footprint vs pinned physical rotation")
        overlaps = coordinates(placement["overlaps"])
        require(overlaps == sorted(set(footprint) & set(visible)) and len(overlaps) <= 1, "overlap history")
        same(placement["covered_placement_index"], last_owner[overlaps[0]] if overlaps else None, "covered placement")
        visible.update(geometry)
        last_owner.update({point: index for point in footprint})
        used.add(card_id)
    same(result["exit_placed"], "exit" in used, "EXIT placement count")
    observed = validate_cells(board["visible_cells"])
    same(board["visible_cells"], [visible[point] for point in sorted(visible)],
         "visible board vs pinned physical placement geometry")
    open_tunnels = 0
    for (x, y), cell in observed.items():
        for edge, (dx, dy) in DELTAS.items():
            neighbor = observed.get((x + dx, y + dy))
            if neighbor is None:
                open_tunnels += edge in cell["tunnel_edges"]
            else:
                require((edge in cell["tunnel_edges"]) == (OPPOSITE[edge] in neighbor["tunnel_edges"]),
                        "visible board tunnel/earth mismatch")
    same(result["open_tunnels"], open_tunnels, "visible open-tunnel count")
    same(result["visible_water_cells"], sum(cell["water"] for cell in observed.values()), "visible water count")
