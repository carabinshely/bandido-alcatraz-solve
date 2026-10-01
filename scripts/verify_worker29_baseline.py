"""Offline, read-only Worker29 evidence gate; never import or execute the engine.

Usage: python scripts/verify_worker29_baseline.py ARTIFACT.zip \
  --inventory inventory.json --metadata metadata.json \
  --source-manifest accepted-source-blobs.json --data-dir accepted/data

Inventory schema (all hashes lowercase SHA256; all sizes integer bytes):
  {"schema":"worker29-artifact-inventory-v1", "artifact_id":123,
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
state consistency, not the hidden deck, policy decisions, or a legal replay.
Authority/authenticity of the separately supplied inventory and GitHub metadata
must be established by the caller; offline JSON alone cannot authenticate GitHub.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import stat
import sys
import zipfile

REPOSITORY = "carabinshely/bandido-alcatraz-solve"
RUN_ID = 36826613482
HEAD = "bf7b1273f8f87b7bc50ccf1ce61acc0f97e9a7f9"
ACCEPTED_MAIN = "45a17097c814e327439cb67404b75c4b4f7dd9b5"
ACCEPTED_TREE = "6fc68dfd1bded75b3cc09b81ee76add495b63928"
SOURCE_MAP_SHA256 = "54156930984b646b6431b325dba6ed39e13f89c165c0d4124dab436c913f975a"
HARNESS_BLOB = "4ac40f10960b71f7a14c7455f08e3b486d9b54a0"
HARNESS_SHA256 = "b174027c2c0b6fbcc651e4390fe345853986564c2d4d735d012f6ca0105f407e"
PREREGISTRATION = f"https://github.com/{REPOSITORY}/issues/2#issuecomment-5925924722"
RULESET = "v1-exact-equipment-full-hand-refresh"
SETUP_ID = "p1-easy-5-exit-hand6-first0-full-hand-refresh"
SETUP = {"player_count": 1, "start_side": "easy-5-exit", "hand_size": 6, "starting_player": 0}
CLASSIFICATION = "canonical_exact_solo_baseline_reproduced"
SEEDS = range(1000000, 1000400)
EXPECTED = [(p, s) for p in (1, 2) for s in SEEDS]
DELTAS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
MAX_BYTES = 512 * 1024 * 1024


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


def digest(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def check_digest(data, expected, label):
    keys(expected, "sha256 size_bytes", label)
    integer(expected["size_bytes"], 1, MAX_BYTES, label)
    same(digest(data), expected, f"{label}: SHA256/size mismatch")


def read_json(path):
    require(path.stat().st_size <= MAX_BYTES, "JSON input exceeds safety bound")
    return strict_json(path.read_bytes())


def load_cards(data_dir, source):
    same(hashlib.sha256(canonical(source)).hexdigest(), SOURCE_MAP_SHA256,
         "source manifest is not the independently pinned accepted tree map")
    data = {}
    for name in ("deck-v1.json", "deck-observations-v0.json"):
        raw = (data_dir / name).read_bytes()
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
    same(run.get("head_branch"), "research/worker29-canonical-baseline", "head branch")
    for key in ("repository", "head_repository"):
        same(run.get(key, {}).get("full_name"), REPOSITORY, f"run {key}")
    same(job.get("run_id"), RUN_ID, "job run ID")
    integer(job.get("id"), 1, 10**15, "job ID")
    same(job.get("name"), "baseline", "job name")
    same(job.get("runner_name"), "bandido-alcatraz-ci", "execution runner")
    labels = job.get("labels")
    require(type(labels) is list and all(type(x) is str for x in labels), "runner labels")
    require({"self-hosted", "Linux", "X64", "bandido-alcatraz-ci"} <= set(labels), "runner labels")
    if "run_attempt" in job:
        same(job["run_attempt"], 1, "job attempt")
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
    same(artifact.get("name"), f"worker29-canonical-baseline-{RUN_ID}-1", "artifact name")
    same(artifact.get("expired"), False, "artifact expired")
    same(artifact.get("size_in_bytes"), inventory["archive"]["size_bytes"], "artifact size")
    same(artifact.get("digest"), "sha256:" + inventory["archive"]["sha256"], "artifact digest")
    artifact_run = artifact.get("workflow_run")
    require(type(artifact_run) is dict, "artifact workflow identity missing")
    same(artifact_run.get("id"), RUN_ID, "artifact run ID")
    same(artifact_run.get("head_sha"), HEAD, "artifact head")


def read_archive(path, inventory):
    keys(inventory, "schema artifact_id archive receipt journal", "inventory")
    same(inventory["schema"], "worker29-artifact-inventory-v1", "inventory schema")
    integer(inventory["artifact_id"], 1, 10**15, "artifact ID")
    keys(inventory["archive"], "sha256 size_bytes", "archive inventory")
    integer(inventory["archive"]["size_bytes"], 1, MAX_BYTES, "archive size")
    same(path.stat().st_size, inventory["archive"]["size_bytes"], "archive size")
    raw = path.read_bytes()
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
    expected = {
        "schema": "bandido-canonical-baseline-v1", "expected_head": HEAD,
        "preregistration_url": PREREGISTRATION, "run_id": str(RUN_ID), "run_attempt": "1",
        "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
        "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "seed_start": SEEDS.start, "seed_end": SEEDS.stop - 1, "population": 400,
        "passes": [1, 2], "fresh_seeds_used": False, "status": "complete",
        "classification": CLASSIFICATION, "research_interpretation_performed": True,
        "attempted": [{"pass": p, "seed": s} for p, s in EXPECTED], "current": None,
        "completed_records": 800, "errors": [],
        "source_before": {"head": HEAD, "harness_blob": HARNESS_BLOB, "source_blobs": source},
        "source_after": {"head": HEAD, "harness_blob": HARNESS_BLOB, "source_blobs": source},
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
                       ("raincoats", 12), ("ropes", 8)):
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
    occupied, last_owner = set(), {}
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
        require(len(footprint) == 2, "physical two-cell footprint")
        require(sum(abs(a - b) for a, b in zip(*footprint)) == 1, "disconnected card footprint")
        same(list(origin), [min(p[0] for p in footprint), min(p[1] for p in footprint)], "footprint origin")
        overlaps = coordinates(placement["overlaps"])
        require(overlaps == sorted(set(footprint) & occupied) and len(overlaps) <= 1, "overlap history")
        same(placement["covered_placement_index"], last_owner[overlaps[0]] if overlaps else None, "covered placement")
        occupied.update(footprint)
        last_owner.update({point: index for point in footprint})
        used.add(card_id)
    same(result["exit_placed"], "exit" in used, "EXIT placement count")
    observed = validate_cells(board["visible_cells"])
    require(list(observed) == sorted(occupied), "visible board coordinates vs placement history")
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
            "win_rate": len(wins) / 400, "winning_seed_ids": wins,
            "failure_reasons": dict(sorted(Counter(record["result"]["reason"] for record in first
                                                    if not record["result"]["won"]).items())),
            "interpretation": "Corrected-model baseline only; spent seeds; no improvement or confirmation claim",
            "normalized_pass_sha256": hashlib.sha256(canonical(first, newline=True)).hexdigest()}


def verify(path, inventory, metadata, source, data_dir):
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
