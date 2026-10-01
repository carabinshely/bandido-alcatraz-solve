"""Offline, read-only Worker30 evidence gate; never import or execute the engine.

Usage: python scripts/verify_worker30_baseline.py ARTIFACT.zip \
  --inventory inventory.json --metadata metadata.json \
  --source-manifest accepted-source-blobs.json --data-dir accepted/data

Inventory schema (all hashes lowercase SHA256; all sizes integer bytes):
  {"schema":"worker30-artifact-inventory-v1", "artifact_id":123,
   "archive":{"sha256":"...", "size_bytes":123},
   "receipt":{"sha256":"...", "size_bytes":123},
   "journal":{"sha256":"...", "size_bytes":123}}
Metadata: {"run":<saved GitHub REST run>, "job":<saved REST baseline job>,
           "artifact":<saved REST artifact>}. Supply independently obtained,
terminal metadata and a frozen inventory, never values copied from the receipt.
The source manifest is the exact path-to-Git-blob map from the accepted tree;
its independent fingerprint is pinned below. Only two hash-checked data files
are read from data-dir. No checkout, Git, network, harness, or engine is needed.

Exit 0 prints an independently recomputed, compact acceptance report. Exit 1
rejects the evidence without changing/extracting any input or reporting a
partial-cohort result. Failed/recovery artifacts are evidence, not valid
negative baselines. Preserve them separately. This gate checks public final
state consistency, including pinned card rotation and final visible geometry,
not the hidden deck, policy decisions, or a legal replay.
Authority/authenticity of the separately supplied inventory and GitHub metadata
must be established by the caller; offline JSON alone cannot authenticate GitHub.

Execution pins were supplied independently from the pre-outcome Worker30 freeze.
All entry through verify()/the CLI fails closed if a pin is missing or malformed;
there is no command-line or receipt-driven override. Synthetic tests explicitly
substitute synthetic pins. Never use those test substitutions for real evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import re
import stat
import sys
import zipfile

REPOSITORY = "carabinshely/bandido-alcatraz-solve"
RUN_ID = 36837736898
HEAD = "7daeaba0dba2a73db21e3075199eabab6303b241"
ACCEPTED_MAIN = "d357a01bed0cccb34bae3c440cc7201ef39a2a84"
ACCEPTED_TREE = "8f694dfff0999ba57015a6fdb2bcfc05793cf063"
SOURCE_MAP_SHA256 = "27b4a000202d5e22b3e37ea128571cd7a5b8a4ef1a882514616c361cf2da0aed"
HARNESS_BLOB = "bc54bdcc5cbc158ae096562ad7ec7b8ac025bb40"
HARNESS_SHA256 = "d15a2d74c55973863937d6f9b883ef8b59f99cd0fc5342d8d839b80400ba2110"
PREREGISTRATION = f"https://github.com/{REPOSITORY}/issues/2#issuecomment-5927438161"
EXECUTION_FREEZE = f"https://github.com/{REPOSITORY}/issues/2#issuecomment-5927853920"
RULESET = "v2-exact-equipment-quota-limited-collect-full-hand-refresh"
SETUP_ID = "p1-easy-5-exit-hand6-first0-full-hand-refresh"
SETUP = {"player_count": 1, "start_side": "easy-5-exit", "hand_size": 6, "starting_player": 0}
CLASSIFICATION = "canonical_quota_limited_solo_baseline_reproduced"
SEEDS = range(1000000, 1000400)
EXPECTED = [(p, s) for p in (1, 2) for s in SEEDS]
DELTAS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
MAX_BYTES = 512 * 1024 * 1024
MAX_MODEL_DATA_BYTES = 1024 * 1024
MAX_STEPS = 1000


class Rejected(ValueError):
    """Evidence cannot establish the complete frozen baseline."""


def require(condition, message):
    if not condition:
        raise Rejected(message)


def validate_execution_freeze():
    """Reject missing/malformed placeholders before reading any candidate archive."""
    require(type(RUN_ID) is int and 1 <= RUN_ID <= 10**15,
            "execution freeze missing or invalid: RUN_ID")
    for name, value, size in (("HEAD", HEAD, 40), ("HARNESS_BLOB", HARNESS_BLOB, 40),
                              ("HARNESS_SHA256", HARNESS_SHA256, 64)):
        require(type(value) is str and re.fullmatch(r"[0-9a-f]{" + str(size) + r"}", value)
                and value != "0" * size,
                f"execution freeze missing or invalid: {name}")


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


def digest(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def check_digest(data, expected, label):
    keys(expected, "sha256 size_bytes", label)
    integer(expected["size_bytes"], 1, MAX_BYTES, label)
    same(digest(data), expected, f"{label}: SHA256/size mismatch")


def read_json(path):
    require(path.stat().st_size <= MAX_BYTES, "JSON input exceeds safety bound")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "JSON input exceeds safety bound")
    return strict_json(raw)


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


def validate_metadata(metadata, inventory):
    keys(metadata, "run job artifact", "metadata")
    run, job, artifact = (metadata[key] for key in ("run", "job", "artifact"))
    require(all(type(value) is dict for value in (run, job, artifact)), "metadata objects")
    for value, label in ((run, "run"), (job, "job")):
        for key, expected in (("status", "completed"), ("conclusion", "success"), ("head_sha", HEAD)):
            same(value.get(key), expected, f"authoritative {label} {key}")
    same(run.get("id"), RUN_ID, "authoritative run ID")
    same(run.get("run_attempt"), 1, "only the frozen first run attempt is authorized")
    same(run.get("event"), "pull_request", "run event")
    same(run.get("path"), ".github/workflows/canonical-baseline.yml", "workflow path")
    same(run.get("head_branch"), "research/worker30-canonical-baseline", "head branch")
    for key in ("repository", "head_repository"):
        same(run.get(key, {}).get("full_name"), REPOSITORY, f"run {key}")
    same(job.get("run_id"), RUN_ID, "job run ID")
    integer(job.get("id"), 1, 10**15, "job ID")
    same(job.get("name"), "baseline", "job name")
    same(job.get("runner_name"), "bandido-alcatraz-ci", "execution runner")
    labels = job.get("labels")
    require(type(labels) is list and all(type(x) is str for x in labels), "runner labels")
    require({"self-hosted", "Linux", "X64", "bandido-alcatraz-ci"} <= set(labels), "runner labels")
    same(job.get("run_attempt"), 1, "job attempt must be present and exactly 1")
    steps = job.get("steps")
    require(type(steps) is list and steps, "missing job steps")
    names = []
    for step in steps:
        require(type(step) is dict and type(step.get("name")) is str, "malformed job step")
        same(step.get("status"), "completed", "unfinished job step")
        same(step.get("conclusion"), "success", "unsuccessful job step")
        names.append(step["name"])
    required = ["Initialize evidence before dependencies and tests", "Routine and synthetic tests",
                "Two complete fixed baseline passes", "Reconcile final status", "Run actions/upload-artifact@v4"]
    require(all(names.count(name) == 1 for name in required), "missing/duplicate required job steps")
    require([names.index(name) for name in required] == sorted(names.index(name) for name in required),
            "job steps out of order")
    same(artifact.get("id"), inventory["artifact_id"], "artifact ID")
    same(artifact.get("name"), f"worker30-canonical-baseline-{RUN_ID}-1", "artifact name")
    same(artifact.get("expired"), False, "artifact expired")
    same(artifact.get("size_in_bytes"), inventory["archive"]["size_bytes"], "artifact size")
    same(artifact.get("digest"), "sha256:" + inventory["archive"]["sha256"], "artifact digest")
    artifact_run = artifact.get("workflow_run")
    require(type(artifact_run) is dict, "artifact workflow identity missing")
    same(artifact_run.get("id"), RUN_ID, "artifact run ID")
    same(artifact_run.get("head_sha"), HEAD, "artifact head")


def read_archive(path, inventory):
    keys(inventory, "schema artifact_id archive receipt journal", "inventory")
    same(inventory["schema"], "worker30-artifact-inventory-v1", "inventory schema")
    integer(inventory["artifact_id"], 1, 10**15, "artifact ID")
    keys(inventory["archive"], "sha256 size_bytes", "archive inventory")
    integer(inventory["archive"]["size_bytes"], 1, MAX_BYTES, "archive size")
    expected_size = inventory["archive"]["size_bytes"]
    same(path.stat().st_size, expected_size, "archive size")
    with path.open("rb") as stream:
        raw = stream.read(expected_size + 1)
    same(len(raw), expected_size, "archive size after read")
    check_digest(raw, inventory["archive"], "archive")
    files = {"receipt.json", "completed.jsonl"} | {
        f"raw-results/pass-{p}/{s}.json" for p, s in EXPECTED}
    directories = {"raw-results/", "raw-results/pass-1/", "raw-results/pass-2/"}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "duplicate ZIP members")
        require(sum(info.file_size for info in infos) <= MAX_BYTES, "ZIP expansion exceeds safety bound")
        for info in infos:
            require(info.orig_filename == info.filename, "ambiguous ZIP member name")
            mode = stat.S_IFMT(info.external_attr >> 16)
            require(mode in (0, stat.S_IFREG, stat.S_IFDIR), "non-regular ZIP member")
            require(not info.flag_bits & 1, "encrypted ZIP member")
            require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "ZIP compression")
            if info.is_dir():
                require(info.filename in directories and info.file_size == 0, "unexpected ZIP directory")
            else:
                require(info.filename in files and mode != stat.S_IFDIR, "unexpected ZIP member")
        require({info.filename for info in infos if not info.is_dir()} == files,
                "incomplete ZIP member population")
        result = {name: archive.read(name) for name in files}  # CRC checked; never extract to disk.
    check_digest(result["receipt.json"], inventory["receipt"], "receipt")
    check_digest(result["completed.jsonl"], inventory["journal"], "journal")
    return result


def validate_receipt(receipt, source):
    # Runtime patch version is recorded rather than selected after outcomes. The
    # preregistration freezes CPython 3.11; all three snapshots must match exactly.
    require(type(receipt) is dict, "receipt: fields")
    before = receipt.get("source_before")
    require(type(before) is dict, "receipt source_before: fields")
    version = before.get("python_version")
    require(type(version) is str and re.fullmatch(r"3\.11\.(0|[1-9][0-9]*)", version),
            "receipt runtime requires an exact CPython 3.11 patch version")
    source_snapshot = {"head": HEAD, "harness_blob": HARNESS_BLOB, "harness_sha256": HARNESS_SHA256,
                       "source_blobs": source, "python_implementation": "CPython", "python_version": version}
    expected = {
        "schema": "bandido-canonical-baseline-v1", "expected_head": HEAD,
        "preregistration_url": PREREGISTRATION, "run_id": str(RUN_ID), "run_attempt": "1",
        "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE, "worker": 30,
        "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "max_steps": MAX_STEPS,
        "seed_start": SEEDS.start, "seed_end": SEEDS.stop - 1, "population": 400,
        "passes": [1, 2], "fresh_seeds_used": False, "status": "complete",
        "classification": CLASSIFICATION, "research_interpretation_performed": True,
        "attempted": [{"pass": p, "seed": s} for p, s in EXPECTED], "current": None,
        "completed_records": 800, "errors": [],
        "source_before": source_snapshot, "source_after": source_snapshot,
        "source_at_finalization": source_snapshot,
        "last_durable_completed_records": 800, "observed_journal_records": 800,
        "step_outcomes": {"tests": "success", "cohort": "success"},
    }
    keys(receipt, " ".join(expected) + " summary", "receipt")
    for key, value in expected.items():
        same(receipt[key], value, f"receipt {key}")


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


def summarize(first):
    wins = [record["seed"] for record in first if record["result"]["won"]]
    return {"games_per_pass": 400, "matching_records": 400, "wins": len(wins),
            "quota_overshoots": sum(record["result"]["raincoats"] > 3 or record["result"]["ropes"] > 2
                                    for record in first),
            "win_rate": len(wins) / 400, "winning_seed_ids": wins,
            "failure_reasons": dict(sorted(Counter(record["result"]["reason"] for record in first
                                                    if not record["result"]["won"]).items())),
            "interpretation": "Quota-corrected v2 baseline only; spent seeds; no improvement or confirmation claim",
            "normalized_pass_sha256": hashlib.sha256(canonical(first, newline=True)).hexdigest()}


def verify(path, inventory, metadata, source, data_dir):
    validate_execution_freeze()
    files = read_archive(path, inventory)
    validate_metadata(metadata, inventory)
    cards = load_cards(data_dir, source)
    receipt = strict_json(files["receipt.json"])
    validate_receipt(receipt, source)
    journal = files["completed.jsonl"]
    require(journal.endswith(b"\n"), "incomplete journal final line")
    lines = journal.splitlines()
    require(len(lines) == 800, "journal population must be exactly 800")
    records = []
    for line, (pass_number, seed) in zip(lines, EXPECTED):
        row = strict_json(line)
        keys(row, "pass record", "journal envelope")
        same(row["pass"], pass_number, "journal pass order")
        record = row["record"]
        validate_record(record, seed, cards)
        raw = strict_json(files[f"raw-results/pass-{pass_number}/{seed}.json"])
        keys(raw, "pass seed result public_capture_count public_captures", "raw sidecar")
        same(raw, {"pass": pass_number, "seed": seed, "result": record["result"],
                   "public_capture_count": 1, "public_captures": [record]}, "sidecar/journal discrepancy")
        records.append(record)
    same(records[:400], records[400:], "normalized full records differ between passes")
    summary = summarize(records[:400])
    same(receipt["summary"], summary, "producer summary disagrees with independent recomputation")
    return {"verified": True, "classification": CLASSIFICATION, "run_id": RUN_ID, "run_attempt": 1,
            "head": HEAD, "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
            "source_map_sha256": SOURCE_MAP_SHA256, "harness_blob": HARNESS_BLOB,
            "runtime": {"python_implementation": receipt["source_before"]["python_implementation"],
                        "python_version": receipt["source_before"]["python_version"]},
            "preregistration_url": PREREGISTRATION, "ruleset_id": RULESET, "setup_id": SETUP_ID,
            "execution_freeze_url": EXECUTION_FREEZE,
            "worker": 30, "max_steps": MAX_STEPS,
            "harness_sha256": HARNESS_SHA256, "artifact_id": inventory["artifact_id"],
            "archive": inventory["archive"], "receipt": inventory["receipt"], "journal": inventory["journal"],
            "verified_records": 800, "verified_sidecars": 800, "summary": summary}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    for name in ("inventory", "metadata", "source-manifest", "data-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify(args.archive, read_json(args.inventory), read_json(args.metadata),
                        read_json(args.source_manifest), args.data_dir)
    except (ValueError, TypeError, KeyError, AttributeError, OSError, zipfile.BadZipFile, RuntimeError,
            OverflowError, RecursionError) as error:
        print(f"REJECTED: {type(error).__name__}: {error}; inputs preserved; no baseline accepted", file=sys.stderr)
        return 1
    print(canonical(report).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
