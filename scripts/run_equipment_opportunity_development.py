"""Frozen Worker31 equipment-opportunity spent-development experiment; raw output is external to Git.

Only ``run`` may simulate, and only on the named Actions runner. ``initialize``
creates an exclusive attempt receipt before setup/tests; ``finalize`` reconciles
all step outcomes. There is deliberately no resume, seed, policy, or setup CLI.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_MAIN = "7be68ee6eac1337663b960791812c8092c7d53e4"
ACCEPTED_TREE = "7ed3b7f1f5a8d09991542f5d22f102e0b83fe612"
REPOSITORY = "carabinshely/bandido-alcatraz-solve"
RULESET = "v2-exact-equipment-quota-limited-collect-full-hand-refresh"
SETUP_ID = "p1-easy-5-exit-hand6-first0-full-hand-refresh"
SETUP = {"player_count": 1, "start_side": "easy-5-exit", "hand_size": 6, "starting_player": 0}
SEEDS = tuple(range(1000000, 1000400))
PASSES = (1, 2, 3)
PHASES = {1: "v4_control", 2: "candidate", 3: "candidate_replay"}
CANDIDATE_PATH = "src/bandido_alcatraz/equipment_opportunity.py"
SCIENTIFIC_FILE_COUNT = 26
CONTROL_ARRAY_SHA256 = "a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021"
CONTROL_WINS = 45
MIN_NET_WINS = 8
CLASSIFICATION = "equipment_opportunity_tie_development_no_advancement"
ADVANCED_CLASSIFICATION = "equipment_opportunity_tie_development_advanced"
HARNESS_PATH = "scripts/run_equipment_opportunity_development.py"
PREREGISTRATION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5928556762"
AUDIT_CLARIFICATION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5928626235"
MAX_STEPS = 1000


class IntegrityError(ValueError):
    """Present evidence contradicts the frozen protocol."""


class InfrastructureError(RuntimeError):
    """Required evidence or execution infrastructure is unavailable."""


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def exact_json(first, second):
    """JSON byte equality preserves bool/int and int/float distinctions."""
    return encoded(first).encode("utf-8") == encoded(second).encode("utf-8")


def safe_output_path(value, *, actions=False):
    require(isinstance(value, (str, Path)) and bool(str(value).strip()), "output path must be nonempty")
    path = Path(value)
    require(path.is_absolute(), "output path must be absolute")
    resolved, checkout = path.resolve(), ROOT.resolve()
    require(resolved != Path(resolved.anchor) and not resolved.is_relative_to(checkout)
            and not checkout.is_relative_to(resolved), "output cannot be root, checkout or a checkout ancestor")
    if actions:
        workspace = Path(os.environ["GITHUB_WORKSPACE"])
        require(workspace.is_absolute() and workspace.resolve() != Path(workspace.anchor), "invalid checkout root")
        run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
        require(bool(re.fullmatch(r"[1-9][0-9]*", run_id)) and bool(re.fullmatch(r"[1-9][0-9]*", attempt)),
                "invalid run/attempt output identity")
        expected = workspace.resolve().parent / "bandido-equipment-development" / run_id / attempt
        configured = workspace / ".." / "bandido-equipment-development" / run_id / attempt
        require(path.absolute() in (expected, configured) and resolved == expected and expected.resolve() == expected,
                "output must be the nonsymlinked bounded checkout-sibling attempt path")
    return resolved


def write_json(path, value):
    """Atomic, fsynced receipt replacement; raw records use an append-only journal."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def read_receipt(output):
    return json.loads((output / "receipt.json").read_text(encoding="utf-8"))


def identity(expected_head, preregistration_url):
    return {
        "expected_head": expected_head, "preregistration_url": preregistration_url,
        "audit_clarification_url": AUDIT_CLARIFICATION_URL,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    }


def initialize(output, expected_head, preregistration_url):
    # Never overwrite or silently archive/reuse another attempt's output.
    output = safe_output_path(output)
    output.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema": "bandido-equipment-opportunity-development-v1", **identity(expected_head, preregistration_url),
        "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
        "worker": 31,
        "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "max_steps": MAX_STEPS,
        "seed_start": SEEDS[0], "seed_end": SEEDS[-1], "population": len(SEEDS),
        "passes": list(PASSES), "phases": {str(k): v for k, v in PHASES.items()},
        "candidate": {"class": "EquipmentOpportunityTiePolicy", "module": CANDIDATE_PATH},
        "control_array_sha256": CONTROL_ARRAY_SHA256, "min_net_wins": MIN_NET_WINS, "fresh_seeds_used": False,
        "status": "initialized", "classification": None,
        "research_interpretation_performed": False, "attempted": [],
        "current": None, "completed_records": 0, "errors": [],
    }
    write_json(output / "receipt.json", receipt)
    return receipt


def check_identity(receipt, expected_head, preregistration_url):
    expected = {**identity(expected_head, preregistration_url), "worker": 31,
                "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
                "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
                "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
                "max_steps": MAX_STEPS, "seed_start": SEEDS[0], "seed_end": SEEDS[-1],
                "population": len(SEEDS), "passes": list(PASSES), "phases": {str(k): v for k, v in PHASES.items()},
        "candidate": {"class": "EquipmentOpportunityTiePolicy", "module": CANDIDATE_PATH},
        "control_array_sha256": CONTROL_ARRAY_SHA256, "min_net_wins": MIN_NET_WINS, "fresh_seeds_used": False}
    for key, value in expected.items():
        require(exact_json(receipt.get(key), value), f"attempt identity mismatch: {key}")


def git(*arguments, allowed=(0,)):
    process = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True)
    if process.returncode not in allowed:
        raise InfrastructureError(
            f"git {' '.join(arguments)} exited {process.returncode}: {process.stderr.strip()}")
    return process


def tree_blobs(commit):
    result = {}
    for entry in git("ls-tree", "-r", "-z", commit, "--", "src", "data").stdout.split("\0"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        mode, kind, blob = metadata.split()
        require(kind == "blob" and mode == "100644", f"unsupported source entry: {path}")
        result[path] = blob
    if not result:
        raise InfrastructureError("source/data tree is unavailable")
    return result


def blob_hash(path):
    content = path.read_bytes()  # Missing/inaccessible file is infrastructure, not an observed mismatch.
    require(not path.is_symlink(), f"symlinked source: {path}")
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def verify_bytecode_configuration():
    require(sys.pycache_prefix is None and not os.environ.get("PYTHONPYCACHEPREFIX"),
            "external Python bytecode cache is forbidden")
    require(sys.dont_write_bytecode, "Python bytecode writes must be disabled")


def verify_source(expected_head):
    verify_bytecode_configuration()
    head = git("rev-parse", "HEAD").stdout.strip()
    require(head == expected_head, "checkout differs from exact expected head")
    # Missing accepted commit objects are infrastructure errors, not non-ancestry.
    git("cat-file", "-e", f"{ACCEPTED_MAIN}^{{commit}}")
    require(git("rev-parse", f"{ACCEPTED_MAIN}^{{tree}}").stdout.strip() == ACCEPTED_TREE,
            "accepted source tree mismatch")
    ancestry = git("merge-base", "--is-ancestor", ACCEPTED_MAIN, head, allowed=(0, 1))
    require(ancestry.returncode == 0, "accepted main is not an ancestor of execution head")
    expected = tree_blobs(ACCEPTED_MAIN)
    require(len(expected) == SCIENTIFIC_FILE_COUNT and CANDIDATE_PATH not in expected,
            "accepted scientific file population mismatch")
    execution = tree_blobs(head)
    require(set(execution) == set(expected) | {CANDIDATE_PATH},
            "only the isolated candidate may be added to scientific source/data")
    require({p: b for p, b in execution.items() if p != CANDIDATE_PATH} == expected,
            "source/data trees differ from accepted main")
    require(blob_hash(ROOT / CANDIDATE_PATH) == execution[CANDIDATE_PATH],
            "candidate differs from exact execution head")
    for path, blob in expected.items():
        require(blob_hash(ROOT / path) == blob, f"source/data hash mismatch: {path}")
    # Ignored bytecode can execute instead of matching source. Reject it too.
    require(not git("ls-files", "--others", "--", "src", "data").stdout,
            "untracked source/data input")
    harness = blob_hash(ROOT / HARNESS_PATH)
    require(harness == git("rev-parse", f"HEAD:{HARNESS_PATH}").stdout.strip(),
            "harness differs from exact execution head")
    return {"head": head, "harness_blob": harness,
            "harness_sha256": hashlib.sha256((ROOT / HARNESS_PATH).read_bytes()).hexdigest(),
            "source_blobs": expected, "candidate_blob": execution[CANDIDATE_PATH],
            "candidate_sha256": hashlib.sha256((ROOT / CANDIDATE_PATH).read_bytes()).hexdigest(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version()}


def observed_source_snapshot():
    """Forensic hashes even when authoritative source verification fails."""
    snapshot = {}
    paths = {ROOT / HARNESS_PATH, ROOT / CANDIDATE_PATH}
    for directory in (ROOT / "src", ROOT / "data"):
        paths.update(path for path in directory.rglob("*") if path.is_file() or path.is_symlink())
    for path in sorted(paths):
        key = str(path.relative_to(ROOT))
        try:
            if path.is_symlink():
                snapshot[key] = {"error": "symlink rejected"}
            else:
                content = path.read_bytes()
                snapshot[key] = {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        except Exception as error:
            snapshot[key] = {"error": type(error).__name__, "message": str(error)}
    return snapshot


def same_source_bytes(first, second):
    # initialize may precede setup-python; freeze bytes independently of runtime.
    return all(exact_json(first.get(key), second.get(key)) for key in
               ("head", "harness_blob", "harness_sha256", "source_blobs", "candidate_blob", "candidate_sha256"))


def preflight(expected_head, preregistration_url):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), "expected head must be a full SHA")
    require(bool(re.fullmatch(r"https://github\.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-[0-9]+",
                              preregistration_url)), "a frozen Issue2 preregistration URL is required")
    require(preregistration_url == PREREGISTRATION_URL, "Worker31 preregistration mismatch")
    for name in ("GITHUB_ACTIONS", "RUNNER_NAME", "GITHUB_REPOSITORY", "EXPECTED_HEAD",
                 "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_EVENT_PATH", "PYTHONHASHSEED"):
        if not os.environ.get(name):
            raise InfrastructureError(f"missing Actions context: {name}")
    require(os.environ.get("GITHUB_ACTIONS") == "true", "research requires GitHub Actions")
    require(os.environ.get("RUNNER_NAME") == "bandido-alcatraz-ci", "unauthorized research runner")
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "wrong repository")
    require(os.environ.get("EXPECTED_HEAD") == expected_head, "expected-head environment mismatch")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    event_head = event.get("pull_request", {}).get("head", {}).get("sha")
    require(event_head == expected_head, "expected head is not the PR event head")
    require(os.environ.get("PYTHONHASHSEED") == "0", "PYTHONHASHSEED must be fixed to 0")
    require(platform.python_implementation() == "CPython" and sys.version_info[:2] == (3, 11),
            "frozen runtime requires CPython 3.11")
    return verify_source(expected_head)


def final_record(seed, result, observation, *, capture=None):
    """Serialize public state incrementally so a failed capture retains its prefix."""
    record = capture if capture is not None else {}
    record.update(seed=seed, result=asdict(result), setup=asdict(observation.setup))
    record["board"] = {"placements": [asdict(item) for item in observation.board.placements],
                       "visible_cells": []}
    for (x, y), cell in sorted(observation.board.cells.items()):
        record["board"]["visible_cells"].append({
            "x": x, "y": y, "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
            "water": cell.water})
    record["collected_equipment"] = []
    for order, item in enumerate(observation.collected_equipment, 1):
        record["collected_equipment"].append({
            "order": order, "card_id": item.card_id, "material": item.material.value,
            "turn": item.turn, "player_index": item.player_index,
            "cells": [{"x": cell.x, "y": cell.y,
                       "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
                       "water": cell.water} for cell in item.card.cells],
        })
    # Use the existing public state/board API; full physical-card replay belongs
    # to the independent acceptance verifier. The raw returned result is already
    # durable, and the caller preserves this capture even when a check fails.
    require(exact_json((result.raincoats, result.ropes, result.exit_placed, result.turns, result.won),
            (observation.raincoats, observation.ropes, observation.exit_placed,
             observation.turns, observation.won)), "GameResult disagrees with final public state")
    require(exact_json((result.open_tunnels, result.visible_water_cells),
            (observation.board.open_tunnels, observation.board.visible_water_cells)),
            "GameResult disagrees with public board geometry")
    return json.loads(encoded(record))  # Uniform JSON types, no tuple/list differences.


def digest(value):
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def move_record(move: Move | None) -> dict | None:
    if move is None:
        return None
    return {
        "action": move.action.value,
        "hand_index": move.hand_index,
        "origin": None if move.origin is None else list(move.origin),
        "quarter_turns": move.quarter_turns,
    }


def _card_record(card: CardDefinition) -> dict:
    return {
        "card_id": card.card_id,
        "material": None if card.material is None else card.material.value,
        "is_exit": card.is_exit,
        "cells": [
            {
                "x": cell.x,
                "y": cell.y,
                "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
                "water": cell.water,
            }
            for cell in card.cells
        ],
    }


def public_observation_record(observation: PlayerObservation) -> dict:
    """Serialize only the detached, public observation, without enumeration."""
    from bandido_alcatraz.game import PlayerObservation
    if type(observation) is not PlayerObservation:
        raise TypeError("expected a detached PlayerObservation")
    return {
        "board": {
            "cells": [
                {
                    "x": coord[0],
                    "y": coord[1],
                    "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
                    "water": cell.water,
                }
                for coord, cell in sorted(observation.board.cells.items())
            ],
            "placements": [asdict(item) for item in observation.board.placements],
        },
        "hand": [_card_record(card) for card in observation.hand],
        "raincoats": observation.raincoats,
        "ropes": observation.ropes,
        "exit_placed": observation.exit_placed,
        "exit_seen": observation.exit_seen,
        "turns": observation.turns,
        "set_aside_unplayable": observation.set_aside_unplayable,
        "collected_equipment": [
            {
                "card": _card_record(item.card),
                "turn": item.turn,
                "player_index": item.player_index,
            }
            for item in observation.collected_equipment
        ],
        "setup": asdict(observation.setup),
        "player_index": observation.player_index,
    }



def append_jsonl(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def trace_path(output, pass_number, seed):
    return output / "decision-traces" / f"pass-{pass_number}" / f"{seed}.jsonl"


class AuditPolicy:
    """Passive boundary wrapper; no legal enumeration, scoring or extra choice."""
    def __init__(self, policy, *, output, pass_number, seed):
        self.policy = policy
        self.pass_number = pass_number
        self.path = trace_path(output, pass_number, seed)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x", encoding="utf-8") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        self.ordinal = 0
        self.non_null_choices = 0

    def trace_counts(self):
        return {"decision_count": self.ordinal, "non_null_choices": self.non_null_choices}

    def choose(self, observation, rng):
        # Reject GameState rather than serialize private deck/set-aside zones.
        public = public_observation_record(observation)
        self.ordinal += 1
        before = digest(rng.getstate())
        append_jsonl(self.path, {"event": "decision_started", "ordinal": self.ordinal,
                               "observation": public, "rng_before_sha256": before})
        move = self.policy.choose(observation, rng)
        common = {"public_observation_sha256": digest(public), "chosen_move": move_record(move),
                  "rng_before_sha256": before, "rng_after_sha256": digest(rng.getstate())}
        if self.pass_number == 1:
            audit = common
        else:
            # Detach immediately; never consult diagnostic fields to choose.
            audit = json.loads(encoded(self.policy.last_audit))
        if move is not None:
            self.non_null_choices += 1
        # Preserve the actual returned audit before validation can reject it.
        append_jsonl(self.path, {"event": "decision_completed", "ordinal": self.ordinal, "audit": audit})
        require(all(exact_json(audit.get(k), value) for k, value in common.items()),
                "candidate audit disagrees with actual observation/choice/RNG")
        require(exact_json(public_observation_record(observation), public),
                "policy mutated its detached public observation")
        return move


def read_trace(path):
    data = path.read_text(encoding="utf-8")
    if data and not data.endswith("\n"):
        raise InfrastructureError("interrupted decision trace write; original bytes preserved")
    return [json.loads(line) for line in data.splitlines()]


def schema_object(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), f"unexpected {label} schema")


def integer(value, label, minimum=None, maximum=None):
    require(type(value) is int and (minimum is None or value >= minimum)
            and (maximum is None or value <= maximum), f"invalid {label} integer")


def text_value(value, label):
    require(type(value) is str and bool(value), f"invalid {label} string")


def coordinate(value, label):
    require(type(value) is list and len(value) == 2, f"invalid {label} coordinate")
    for component in value:
        integer(component, label)


def cell_schema(cell):
    schema_object(cell, {"x", "y", "tunnel_edges", "water"}, "public cell")
    integer(cell["x"], "cell x")
    integer(cell["y"], "cell y")
    edges = cell["tunnel_edges"]
    require(type(edges) is list and all(type(edge) is str and edge in ("N", "E", "S", "W") for edge in edges)
            and edges == sorted(set(edges)), "invalid public tunnel edges")
    require(type(cell["water"]) is bool, "invalid public water flag")


def card_schema(card):
    schema_object(card, {"card_id", "material", "is_exit", "cells"}, "public card")
    text_value(card["card_id"], "card ID")
    require(card["material"] is None or type(card["material"]) is str
            and card["material"] in ("raincoat", "rope"), "invalid public material")
    require(type(card["is_exit"]) is bool, "invalid public EXIT flag")
    require(type(card["cells"]) is list and card["cells"], "invalid public card cells")
    for cell in card["cells"]:
        cell_schema(cell)


def placement_schema(placement):
    schema_object(placement, {"card_id", "origin", "quarter_turns", "placement_index", "kind", "cells",
                             "overlaps", "covered_placement_index"}, "public placement")
    text_value(placement["card_id"], "placed card ID")
    coordinate(placement["origin"], "placement origin")
    integer(placement["quarter_turns"], "placement rotation", 0, 3)
    integer(placement["placement_index"], "placement index", 0)
    require(type(placement["kind"]) is str and placement["kind"] in ("start", "ordinary", "exit"),
            "invalid placement kind")
    for key in ("cells", "overlaps"):
        require(type(placement[key]) is list and (key != "cells" or placement[key]), "invalid placement coordinates")
        for coord in placement[key]:
            coordinate(coord, key)
    if placement["covered_placement_index"] is not None:
        integer(placement["covered_placement_index"], "covered placement index", 0)


def board_schema(board, cells_key="cells"):
    schema_object(board, {cells_key, "placements"}, "public board")
    require(type(board[cells_key]) is list and bool(board[cells_key]), "invalid public board cells")
    require(type(board["placements"]) is list and bool(board["placements"]), "invalid public placements")
    for cell in board[cells_key]:
        cell_schema(cell)
    for placement in board["placements"]:
        placement_schema(placement)


def observation_schema(observation):
    schema_object(observation, {"board", "hand", "raincoats", "ropes", "exit_placed", "exit_seen", "turns",
        "set_aside_unplayable", "collected_equipment", "setup", "player_index"}, "public observation")
    board_schema(observation["board"])
    require(type(observation["hand"]) is list, "invalid public hand")
    for card in observation["hand"]:
        card_schema(card)
    integer(observation["raincoats"], "observed raincoats", 0, 3)
    integer(observation["ropes"], "observed ropes", 0, 2)
    integer(observation["turns"], "observed turns", 0)
    integer(observation["set_aside_unplayable"], "public set-aside count", 0)
    integer(observation["player_index"], "observed player index", 0, 0)
    for key in ("exit_placed", "exit_seen"):
        require(type(observation[key]) is bool, f"invalid observed {key} flag")
    require(exact_json(observation["setup"], SETUP), "observed setup schema/type mismatch")
    require(type(observation["collected_equipment"]) is list, "invalid observed collected history")
    for item in observation["collected_equipment"]:
        schema_object(item, {"card", "turn", "player_index"}, "observed collection")
        card_schema(item["card"])
        integer(item["turn"], "observed collection turn", 1, observation["turns"])
        integer(item["player_index"], "observed collection player", 0, 0)


def move_schema(move, hand):
    if move is None:
        return
    schema_object(move, {"action", "hand_index", "origin", "quarter_turns"}, "public move")
    require(type(move["action"]) is str and move["action"] in ("place", "collect"), "invalid public move action")
    integer(move["hand_index"], "move hand index", 0, len(hand) - 1)
    integer(move["quarter_turns"], "move rotation", 0, 3)
    if move["action"] == "collect":
        require(move["origin"] is None and move["quarter_turns"] == 0, "invalid collection move geometry")
    else:
        coordinate(move["origin"], "move origin")


def trace_counts_schema(counts):
    schema_object(counts, {"decision_count", "non_null_choices"}, "trace counts")
    integer(counts["decision_count"], "decision count", 0)
    integer(counts["non_null_choices"], "non-null choice count", 0, counts["decision_count"])


def validate_trace(events, record, pass_number):
    require(len(events) >= 2 and exact_json(events[-2], {"event": "game_returned", "result": record["result"]}),
            "trace result/normalized record disagreement or partial final decision")
    completion = events[-1]
    schema_object(completion, {"event", "record_sha256", "trace_counts"}, "trace completion")
    require(completion["event"] == "game_completed" and completion["record_sha256"] == digest(record),
            "trace completion record digest mismatch")
    trace_counts_schema(completion["trace_counts"])
    decisions = events[:-2]
    require(len(decisions) % 2 == 0, "incomplete decision trace")
    require(len(decisions) // 2 == completion["trace_counts"]["decision_count"],
            "trace decision count disagrees with durable wrapper count")
    non_null_choices = 0
    strict = 0
    common_keys = {"public_observation_sha256", "chosen_move", "rng_before_sha256", "rng_after_sha256"}
    candidate_keys = common_keys | {"legal_move_count", "primary_tier", "primary_tier_sha256",
        "primary_score", "eligible_collect_tier", "collection_opportunities", "opportunity_null_is_lowest",
        "narrowed_tier", "narrowed_tier_sha256", "narrowed_tier_count", "strict_narrowing"}
    for ordinal in range(1, len(decisions) // 2 + 1):
        started, completed = decisions[2 * ordinal - 2:2 * ordinal]
        require(set(started) == {"event", "ordinal", "observation", "rng_before_sha256"}
                and started["event"] == "decision_started" and type(started["ordinal"]) is int
                and started["ordinal"] == ordinal, "malformed decision start or ordinal")
        require(set(completed) == {"event", "ordinal", "audit"} and completed["event"] == "decision_completed"
                and type(completed["ordinal"]) is int and completed["ordinal"] == ordinal,
                "malformed decision completion or ordinal")
        audit = completed["audit"]
        require(set(audit) == (common_keys if pass_number == 1 else candidate_keys),
                "unexpected audit fields (including private data)")
        require(audit["public_observation_sha256"] == digest(started["observation"])
                and audit["rng_before_sha256"] == started["rng_before_sha256"],
                "trace observation or RNG digest mismatch")
        observation_schema(started["observation"])
        require(started["observation"]["turns"] == non_null_choices,
                "observation turn count disagrees with preceding non-null choices")
        move_schema(audit["chosen_move"], started["observation"]["hand"])
        non_null_choices += audit["chosen_move"] is not None
        if audit["chosen_move"] is None:
            require(audit["rng_before_sha256"] == audit["rng_after_sha256"], "no-move decision consumed RNG")
        for key in ("public_observation_sha256", "rng_before_sha256", "rng_after_sha256"):
            require(isinstance(audit[key], str) and re.fullmatch(r"[0-9a-f]{64}", audit[key]),
                    "invalid trace digest")
        if pass_number == 1:
            continue  # Accepted clarification: control uses only common passive fields.
        primary, narrowed = audit["primary_tier"], audit["narrowed_tier"]
        require(isinstance(primary, list) and isinstance(narrowed, list), "malformed audit tiers")
        require(audit["primary_tier_sha256"] == digest(primary)
                and audit["narrowed_tier_sha256"] == digest(narrowed), "audit tier digest mismatch")
        require(type(audit["legal_move_count"]) is int and audit["legal_move_count"] >= len(primary)
                and type(audit["narrowed_tier_count"]) is int
                and audit["narrowed_tier_count"] == len(narrowed), "audit tier counts mismatch")
        for move in primary + narrowed:
            require(move is not None, "null move in an audit tier")
            move_schema(move, started["observation"]["hand"])
        eligible = bool(primary) and all(m["action"] == "collect" for m in primary)
        require(type(audit["eligible_collect_tier"]) is bool and audit["eligible_collect_tier"] == eligible,
                "audit eligibility mismatch")
        require(audit["opportunity_null_is_lowest"] is True, "missing empty-opportunity ordering")
        opportunities = audit["collection_opportunities"]
        if eligible:
            require(len(opportunities) == len(primary), "missing collection opportunities")
            keys = []
            for move, item in zip(primary, opportunities):
                integer(item.get("hand_index"), "opportunity hand index", 0, len(started["observation"]["hand"]) - 1)
                text_value(item.get("card_id"), "opportunity card ID")
                require(set(item) == {"hand_index", "card_id", "opportunity_score"}
                        and item["hand_index"] == move["hand_index"]
                        and item["card_id"] == started["observation"]["hand"][move["hand_index"]]["card_id"],
                        "opportunity card identity mismatch")
                score = item["opportunity_score"]
                require(score is None or type(score) is int, "invalid opportunity value")
                keys.append((score is not None, 0 if score is None else score))
            expected = [move for move, key in zip(primary, keys) if key == min(keys)]
        else:
            require(opportunities == [], "opportunities outside eligible collection tier")
            expected = primary
        require(exact_json(narrowed, expected), "narrowing does not follow the frozen rule")
        changed = len(narrowed) < len(primary)
        require(type(audit["strict_narrowing"]) is bool and audit["strict_narrowing"] == changed,
                "strict-narrowing count mismatch")
        strict += changed
        require(any(exact_json(audit["chosen_move"], move) for move in narrowed) if narrowed else audit["chosen_move"] is None,
                "chosen move outside final tier")
        require((type(audit["primary_score"]) is int) if primary else audit["primary_score"] is None,
                "primary score mismatch")
        if not primary:
            require(audit["legal_move_count"] == 0 and audit["rng_before_sha256"] == audit["rng_after_sha256"],
                    "empty tier consumed RNG or hid legal moves")
    require(non_null_choices == record["result"]["turns"]
            and non_null_choices == completion["trace_counts"]["non_null_choices"],
            "trace non-null choices disagree with final turns/wrapper count")
    return strict


def verify_traces(output, rows):
    expected_paths = {trace_path(output, row["pass"], row["record"]["seed"]) for row in rows}
    actual = {p for p in (output / "decision-traces").rglob("*") if p.is_file()}
    require(actual == expected_paths, "unexpected or incomplete trace population")
    strict = comparable = differing = 0
    # Bound memory to a few individual games, not 1200 full decision histories.
    for row in rows:
        p, seed = row["pass"], row["record"]["seed"]
        events = read_trace(trace_path(output, p, seed))
        count = validate_trace(events, row["record"], p)
        raw = json.loads((output / "raw-results" / f"pass-{p}" / f"{seed}.json").read_text(encoding="utf-8"))
        require(exact_json(events[-1]["trace_counts"], raw["trace_counts"]),
                "trace counts disagree with raw returned-result sidecar")
        if p != 2:
            continue
        strict += count
        replay = read_trace(trace_path(output, 3, seed))
        require(exact_json(events, replay), "candidate decision traces differ across replay")
        control = read_trace(trace_path(output, 1, seed))
        for c, d in zip(control[:-2][1::2], events[:-2][1::2]):
            ca, da = c["audit"], d["audit"]
            if (ca["public_observation_sha256"], ca["rng_before_sha256"]) == (da["public_observation_sha256"], da["rng_before_sha256"]):
                comparable += 1
                differing += not exact_json(ca["chosen_move"], da["chosen_move"])
    return {"candidate_strict_tier_narrowings": strict,
            "matched_observation_rng_decisions": comparable,
            "selected_action_differences_in_matched_contexts": differing,
            "candidate_replay_trace_matches": len(SEEDS),
            "action_difference_scope": "same seed and ordinal with identical public observation and pre-choice RNG hashes"}


def one_game(seed, *, output, pass_number):
    require(type(seed) is int and seed in SEEDS, "out-of-scope seed")
    require(type(pass_number) is int and pass_number in PASSES, "out-of-scope pass")
    raw_path = output / "raw-results" / f"pass-{pass_number}" / f"{seed}.json"
    require(not raw_path.exists(), "raw returned result already exists; attempt reuse is forbidden")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    # Import only after the durable attempt receipt and source preflight exist.
    verify_bytecode_configuration()
    source_path = str(ROOT / "src")
    if sys.path[0] != source_path:
        sys.path.insert(0, source_path)
    from bandido_alcatraz.physical_deck import load_real_deck
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    from bandido_alcatraz.rules import RULESET_ID
    from bandido_alcatraz.setup import GameSetup
    from bandido_alcatraz.simulate import play_game

    require(RULESET_ID == RULESET, "imported ruleset mismatch")
    setup = GameSetup()
    require(setup.setup_id == SETUP_ID, "imported setup mismatch")
    for name, module in tuple(sys.modules.items()):
        if name == "bandido_alcatraz" or name.startswith("bandido_alcatraz."):
            require(Path(module.__file__).resolve().is_relative_to(ROOT / "src"),
                    f"import outside pinned source: {name}")
    deck = load_real_deck(ROOT / "data")
    if pass_number == 1:
        policy = BoundedMergeV4Policy(setup_weight=250)
    else:
        from bandido_alcatraz.equipment_opportunity import EquipmentOpportunityTiePolicy
        policy = EquipmentOpportunityTiePolicy()
        module = sys.modules["bandido_alcatraz.equipment_opportunity"]
        require(Path(module.__file__).resolve() == ROOT / CANDIDATE_PATH,
                "candidate imported outside pinned source")
    policy = AuditPolicy(policy, output=output, pass_number=pass_number, seed=seed)
    observations = []
    # The existing final-observation hook is observational and does not alter choose/RNG.
    policy.on_game_finished = observations.append
    result = play_game(start_card=deck.start_for_setup(setup), deck=deck.draw_deck(),
                       hand_size=setup.hand_size, policy=policy, seed=seed, setup=setup,
                       max_steps=MAX_STEPS)
    # Save the returned GameResult before any callback-count or public-capture checks.
    raw = {"pass": pass_number, "seed": seed, "result": asdict(result),
           "public_capture_count": len(observations), "public_captures": [], "trace_counts": policy.trace_counts()}
    write_json(raw_path, raw)
    append_jsonl(policy.path, {"event": "game_returned", "result": asdict(result)})
    normalized = []
    for observation in observations:
        capture = {}
        raw["public_captures"].append(capture)
        try:
            normalized.append(final_record(seed, result, observation, capture=capture))
        except Exception as error:
            raw["capture_error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            write_json(raw_path, raw)  # Preserve available public fields even on failure.
    require(len(observations) == 1, "missing or repeated final public observation")
    append_jsonl(policy.path, {"event": "game_completed", "record_sha256": digest(normalized[0]),
                              "trace_counts": policy.trace_counts()})
    return normalized[0]


def append_record(output, pass_number, record):
    with (output / "completed.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(encoded({"pass": pass_number, "record": record}))
        stream.flush()
        os.fsync(stream.fileno())


def read_records(output):
    path = output / "completed.jsonl"
    data = path.read_text(encoding="utf-8")
    if data and not data.endswith("\n"):
        raise InfrastructureError("interrupted raw journal write; original bytes preserved")
    return [json.loads(line) for line in data.splitlines()]


def verify_raw_sidecars(output, rows):
    """Every completed normalized record needs its original durable returned result."""
    expected = set()
    for row in rows:
        seed, pass_number = row["record"]["seed"], row["pass"]
        path = output / "raw-results" / f"pass-{pass_number}" / f"{seed}.json"
        expected.add(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        trace_counts_schema(raw.get("trace_counts"))
        require(exact_json(raw, {"pass": pass_number, "seed": seed, "result": row["record"]["result"],
                        "public_capture_count": 1, "public_captures": [row["record"]], "trace_counts": raw["trace_counts"]}),
                f"raw sidecar disagrees with normalized record: pass {pass_number}, seed {seed}")
    actual = {p for p in (output / "raw-results").rglob("*") if p.is_file()}
    require(actual == expected, "unexpected or incomplete raw sidecar population")


def validate_record(record, seed):
    require(set(record) == {"seed", "result", "setup", "collected_equipment", "board"},
            "missing or unexpected normalized record fields")
    require(exact_json(record["setup"], SETUP), "record setup dimensions mismatch")
    require(set(record["result"]) == {"won", "turns", "open_tunnels", "visible_water_cells",
            "raincoats", "ropes", "exit_placed", "reason", "ruleset_id", "setup_id"},
            "incomplete normalized GameResult")
    require(set(record["board"]) == {"placements", "visible_cells"}
            and record["board"]["placements"] and record["board"]["visible_cells"],
            "missing public final board geometry")
    board_schema(record["board"], cells_key="visible_cells")
    require(type(record["seed"]) is int and record["seed"] == seed, "record seed mismatch")
    require(record["result"]["ruleset_id"] == RULESET, "record ruleset mismatch")
    require(record["result"]["setup_id"] == SETUP_ID, "record setup mismatch")
    require(record["result"]["reason"] != "step_limit", f"step limit at seed {seed}")
    result = record["result"]
    require(type(result["won"]) is bool and type(result["exit_placed"]) is bool,
            "invalid result flags")
    for field in ("turns", "open_tunnels", "visible_water_cells"):
        require(type(result[field]) is int and result[field] >= 0, "invalid result counter")
    for field, quota in (("raincoats", 3), ("ropes", 2)):
        require(type(result[field]) is int and 0 <= result[field] <= quota,
                f"invalid {field} count or quota overshoot at seed {seed}")
    history = record["collected_equipment"]
    require(isinstance(history, list), "collected-equipment history must be a list")
    materials = Counter()
    identities = set()
    for order, item in enumerate(history, 1):
        require(isinstance(item, dict) and set(item) ==
                {"order", "card_id", "material", "turn", "player_index", "cells"},
                "incomplete collected-equipment history")
        require(type(item["order"]) is int and item["order"] == order,
                "collected-equipment history order mismatch")
        require(isinstance(item["card_id"], str) and item["card_id"]
                and item["card_id"] not in identities, "duplicate or missing collected card identity")
        require(item["material"] in ("raincoat", "rope"), "unknown collected equipment material")
        require(type(item["turn"]) is int and 1 <= item["turn"] <= result["turns"] and
                type(item["player_index"]) is int and item["player_index"] == 0,
                "invalid collection turn or solo player")
        require(isinstance(item["cells"], list) and item["cells"], "missing collected-card geometry")
        for cell in item["cells"]:
            cell_schema(cell)
        identities.add(item["card_id"])
        materials[item["material"]] += 1
    require(materials["raincoat"] == result["raincoats"] and materials["rope"] == result["ropes"],
            f"collected-equipment history disagrees with quota counts at seed {seed}")
    require(not result["won"] or (result["raincoats"], result["ropes"]) == (3, 2),
            f"win without exact equipment quotas at seed {seed}")
    won = ((result["raincoats"], result["ropes"]) == (3, 2) and result["exit_placed"]
           and result["open_tunnels"] == 0 and result["visible_water_cells"] == 0)
    require(result["won"] == won and (result["reason"] == "win") == won,
            "result disagrees with exact victory conditions")


def compare_passes(rows):
    expected = [(p, s) for p in PASSES for s in SEEDS]
    require(all(type(r.get("pass")) is int and isinstance(r.get("record"), dict) for r in rows),
            "malformed raw record envelope")
    require([(r["pass"], r["record"].get("seed")) for r in rows] == expected,
            "incomplete, duplicate, reordered, or out-of-scope raw population")
    for row, (_, seed) in zip(rows, expected):
        validate_record(row["record"], seed)
    control = [r["record"] for r in rows[:len(SEEDS)]]
    candidate = [r["record"] for r in rows[len(SEEDS):2 * len(SEEDS)]]
    replay = [r["record"] for r in rows[2 * len(SEEDS):]]
    require(exact_json(candidate, replay), "normalized final records differ across candidate replay")
    control_hash = digest(control)
    require(control_hash == CONTROL_ARRAY_SHA256, "complete control normalized array differs from accepted Worker30")
    control_wins = {r["seed"] for r in control if r["result"]["won"]}
    wins = {r["seed"] for r in candidate if r["result"]["won"]}
    require(len(control_wins) == CONTROL_WINS, "control does not reproduce accepted 45 wins")
    gained, lost = wins - control_wins, control_wins - wins
    shared, both_lost = wins & control_wins, set(SEEDS) - (wins | control_wins)
    net = len(wins) - len(control_wins)
    return {"games_per_pass": len(SEEDS), "matching_records": len(SEEDS),
            "quota_overshoots": 0, "control_wins": len(control_wins),
            "wins": len(wins), "win_rate": len(wins) / len(SEEDS), "winning_seed_ids": sorted(wins),
            "net_wins": net, "min_net_wins": MIN_NET_WINS,
            "classification": ADVANCED_CLASSIFICATION if net >= MIN_NET_WINS else CLASSIFICATION,
            "paired_2x2": {"both_win": len(shared), "control_only": len(lost),
                           "candidate_only": len(gained), "both_lose": len(both_lost)},
            "gained_seed_ids": sorted(gained), "lost_seed_ids": sorted(lost),
            "shared_win_seed_ids": sorted(shared), "both_loss_seed_ids": sorted(both_lost),
            "candidate_loss_seed_ids": sorted(set(SEEDS) - wins),
            "control_loss_seed_ids": sorted(set(SEEDS) - control_wins),
            "failure_reasons": dict(sorted(Counter(r["result"]["reason"] for r in candidate
                                                    if not r["result"]["won"]).items())),
            "interpretation": "Spent development screen only; next validation requires separate preregistration",
            "normalized_control_sha256": control_hash,
            "normalized_candidate_sha256": digest(candidate)}


def integrity_error(error):
    if isinstance(error, (InfrastructureError, OSError, MemoryError, ImportError,
                          subprocess.SubprocessError)):
        return False
    return isinstance(error, (ValueError, AssertionError, TypeError, KeyError,
                              IndexError, AttributeError))


def fail(receipt, error, phase):
    invalid = integrity_error(error)
    # Never downgrade an already established integrity failure to infrastructure.
    invalid = invalid or receipt.get("status") == "integrity_invalid"
    receipt.update(status="integrity_invalid" if invalid else "execution_blocked",
                   classification=None, research_interpretation_performed=False)
    receipt.pop("summary", None)
    receipt["errors"].append({"phase": phase, "type": type(error).__name__, "message": str(error)})


def run(output, expected_head, preregistration_url):
    receipt = read_receipt(output) if output.exists() else initialize(output, expected_head, preregistration_url)
    check_identity(receipt, expected_head, preregistration_url)
    require(receipt["status"] == "initialized" and not receipt["attempted"]
            and not (output / "completed.jsonl").exists(), "attempt already used; resume/mixing is forbidden")
    try:
        receipt["source_before"] = preflight(expected_head, preregistration_url)
        if "source_at_initialization" in receipt:
            require(same_source_bytes(receipt["source_before"], receipt["source_at_initialization"]),
                    "source changed after initialization")
        receipt["status"] = "running"
        write_json(output / "receipt.json", receipt)
        for pass_number in PASSES:
            for seed in SEEDS:
                receipt["current"] = {"pass": pass_number, "seed": seed}
                receipt["attempted"].append(dict(receipt["current"]))
                write_json(output / "receipt.json", receipt)  # Must precede every game.
                record = one_game(seed, output=output, pass_number=pass_number)
                append_record(output, pass_number, record)  # Must precede step_limit validation.
                receipt["completed_records"] += 1
                write_json(output / "receipt.json", receipt)
                validate_record(record, seed)
            if pass_number == 1:
                control = [row["record"] for row in read_records(output)]
                require(digest(control) == CONTROL_ARRAY_SHA256,
                        "complete control normalized array differs from accepted Worker30")
                require(sum(row["result"]["won"] for row in control) == CONTROL_WINS,
                        "control does not reproduce accepted 45 wins")
        receipt["source_after"] = verify_source(expected_head)
        require(exact_json(receipt["source_after"], receipt["source_before"]), "source changed during execution")
        rows = read_records(output)
        compare_passes(rows)
        verify_raw_sidecars(output, rows)
        verify_traces(output, rows)
        receipt.update(status="awaiting_finalization", current=None)
        write_json(output / "receipt.json", receipt)
        print("EQUIPMENT_DEVELOPMENT_COHORT_COMPLETE=1200; awaiting successful workflow finalization", flush=True)
        return 0
    except Exception as error:
        fail(receipt, error, "cohort")
        receipt["observed_source_after_failure"] = observed_source_snapshot()
        if "source_before" in receipt and "source_after" not in receipt:
            try:
                receipt["source_after"] = verify_source(expected_head)
                require(exact_json(receipt["source_after"], receipt["source_before"]), "source changed during failed execution")
            except Exception as source_error:
                fail(receipt, source_error, "source_after")
        write_json(output / "receipt.json", receipt)
        return 1


def recovery_receipt(output, expected_head, preregistration_url, test_outcome, cohort_outcome, error):
    """Record finalization failure separately; never repair/overwrite unreadable evidence."""
    output.mkdir(parents=True, exist_ok=True)
    original_hash = None
    try:
        original_hash = hashlib.sha256((output / "receipt.json").read_bytes()).hexdigest()
    except OSError:
        pass
    recovery = {
        "schema": "bandido-equipment-opportunity-development-recovery-v1", **identity(expected_head, preregistration_url),
        "status": "integrity_invalid" if integrity_error(error) or test_outcome == "failure" else "execution_blocked",
        "classification": None, "research_interpretation_performed": False,
        "attempted": None, "current": None, "completed_records": None,
        "execution_extent": "unknown because the original attempt receipt could not be loaded or validated",
        "original_receipt_sha256": original_hash,
        "observed_source_at_failed_finalization": observed_source_snapshot(),
        "step_outcomes": {"tests": test_outcome, "cohort": cohort_outcome},
        "errors": [{"phase": "finalize_receipt", "type": type(error).__name__, "message": str(error)}],
    }
    if test_outcome == "failure":
        recovery["errors"].append({"phase": "tests", "type": "IntegrityError", "message": "synthetic test step failed"})
    # A unique sidecar also preserves evidence from repeated failed finalizations.
    descriptor, name = tempfile.mkstemp(prefix="recovery-receipt-", suffix=".json", dir=output)
    os.close(descriptor)
    write_json(Path(name), recovery)


def finalize(output, expected_head, preregistration_url, test_outcome, cohort_outcome):
    # Reconcile even when a killed producer left its last receipt at 'running'.
    try:
        receipt = read_receipt(output)
        require(isinstance(receipt, dict) and isinstance(receipt.get("errors"), list)
                and isinstance(receipt.get("status"), str)
                and type(receipt.get("completed_records")) is int
                and receipt["completed_records"] >= 0, "malformed attempt receipt schema")
        check_identity(receipt, expected_head, preregistration_url)
    except Exception as error:
        recovery_receipt(output, expected_head, preregistration_url, test_outcome, cohort_outcome, error)
        return 1
    receipt["step_outcomes"] = {"tests": test_outcome, "cohort": cohort_outcome}
    # This known integrity failure must survive absent research output when the
    # cohort was skipped because tests failed.
    if test_outcome == "failure":
        fail(receipt, IntegrityError("synthetic test step failed"), "tests")
    # A killed producer cannot perform its own source-after check. Reconcile
    # accessible source before any outcome/journal failure can short-circuit it.
    try:
        after = verify_source(expected_head)
        receipt["source_at_finalization"] = after
        if "source_at_initialization" in receipt:
            require(same_source_bytes(after, receipt["source_at_initialization"]),
                    "source changed after initialization")
        for key in ("source_before", "source_after"):
            if key in receipt:
                require(exact_json(after, receipt[key]), f"source changed before finalization: {key}")
    except Exception as error:
        fail(receipt, error, "source_at_finalization")
        receipt["observed_source_at_failed_finalization"] = observed_source_snapshot()
    # The prior fsynced count is evidence even if the journal is later lost.
    durable_count = receipt["completed_records"]
    receipt["last_durable_completed_records"] = durable_count
    receipt["observed_journal_records"] = None
    receipt.pop("execution_extent", None)
    try:
        rows = read_records(output)
        receipt["observed_journal_records"] = len(rows)
        require(type(durable_count) is int and durable_count >= 0,
                "invalid durable completed-record count")
        require(len(rows) >= durable_count,
                "present journal contradicts durable completed-record count")
        receipt["completed_records"] = len(rows)
        if test_outcome != "success" or cohort_outcome != "success":
            raise InfrastructureError(f"workflow did not succeed: tests={test_outcome}, cohort={cohort_outcome}")
        if receipt["status"] in ("awaiting_finalization", "complete") and not (output / "completed.jsonl").exists():
            raise InfrastructureError("completed raw artifact is missing")
        if receipt["status"] not in ("awaiting_finalization", "complete"):
            raise InfrastructureError(f"cohort did not establish completion: {receipt['status']}")
        after = receipt["source_at_finalization"]
        require(exact_json(after, receipt["source_before"]) and exact_json(after, receipt["source_after"]), "source changed before finalization")
        summary = compare_passes(rows)
        require(exact_json(receipt["attempted"], [{"pass": p, "seed": s} for p in PASSES for s in SEEDS]),
                "attempt provenance does not cover the complete ordered population")
        verify_raw_sidecars(output, rows)
        summary["trace_summary"] = verify_traces(output, rows)
        receipt.update(status="complete", classification=summary["classification"],
                       research_interpretation_performed=True, summary=summary, current=None)
        write_json(output / "receipt.json", receipt)
        print("EQUIPMENT_DEVELOPMENT_SUMMARY=" + encoded(summary).strip(), flush=True)
        return 0
    except Exception as error:
        if receipt["observed_journal_records"] is None or receipt["observed_journal_records"] < durable_count:
            receipt["execution_extent"] = "unknown; preserve last durable count because the journal is unavailable or contradictory"
        fail(receipt, error, "finalize")
        write_json(output / "receipt.json", receipt)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("initialize", "run", "finalize"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--preregistration-url", required=True)
    parser.add_argument("--test-outcome", default="unknown")
    parser.add_argument("--cohort-outcome", default="unknown")
    args = parser.parse_args(argv)
    try:
        args.output_dir = safe_output_path(args.output_dir, actions=os.environ.get("GITHUB_ACTIONS") == "true")
        if args.mode == "initialize":
            receipt = initialize(args.output_dir, args.expected_head, args.preregistration_url)
            try:
                receipt["source_at_initialization"] = verify_source(args.expected_head)
            except Exception as error:
                fail(receipt, error, "source_at_initialization")
                receipt["observed_source_at_failed_initialization"] = observed_source_snapshot()
                write_json(args.output_dir / "receipt.json", receipt)
                return 1
            write_json(args.output_dir / "receipt.json", receipt)
            return 0
        if args.mode == "run":
            return run(args.output_dir, args.expected_head, args.preregistration_url)
        return finalize(args.output_dir, args.expected_head, args.preregistration_url,
                        args.test_outcome, args.cohort_outcome)
    except Exception as error:
        # Identity/reuse failures must not overwrite the prior attempt's receipt.
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

