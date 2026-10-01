"""Frozen Worker30 quota-corrected v2 baseline; raw output is external to Git.

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
ACCEPTED_MAIN = "d357a01bed0cccb34bae3c440cc7201ef39a2a84"
ACCEPTED_TREE = "8f694dfff0999ba57015a6fdb2bcfc05793cf063"
REPOSITORY = "carabinshely/bandido-alcatraz-solve"
RULESET = "v2-exact-equipment-quota-limited-collect-full-hand-refresh"
SETUP_ID = "p1-easy-5-exit-hand6-first0-full-hand-refresh"
SETUP = {"player_count": 1, "start_side": "easy-5-exit", "hand_size": 6, "starting_player": 0}
SEEDS = tuple(range(1000000, 1000400))
PASSES = (1, 2)
CLASSIFICATION = "canonical_quota_limited_solo_baseline_reproduced"
HARNESS_PATH = "scripts/run_canonical_baseline.py"
PREREGISTRATION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5927438161"
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
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    }


def initialize(output, expected_head, preregistration_url):
    # Never overwrite or silently archive/reuse another attempt's output.
    output.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema": "bandido-canonical-baseline-v1", **identity(expected_head, preregistration_url),
        "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
        "worker": 30,
        "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "max_steps": MAX_STEPS,
        "seed_start": SEEDS[0], "seed_end": SEEDS[-1], "population": len(SEEDS),
        "passes": list(PASSES), "fresh_seeds_used": False,
        "status": "initialized", "classification": None,
        "research_interpretation_performed": False, "attempted": [],
        "current": None, "completed_records": 0, "errors": [],
    }
    write_json(output / "receipt.json", receipt)
    return receipt


def check_identity(receipt, expected_head, preregistration_url):
    expected = {**identity(expected_head, preregistration_url), "worker": 30,
                "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
                "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
                "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
                "max_steps": MAX_STEPS, "seed_start": SEEDS[0], "seed_end": SEEDS[-1],
                "population": len(SEEDS), "passes": list(PASSES), "fresh_seeds_used": False}
    for key, value in expected.items():
        require(receipt.get(key) == value, f"attempt identity mismatch: {key}")


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
    require(tree_blobs(head) == expected, "source/data trees differ from accepted main")
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
            "source_blobs": expected, "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version()}


def preflight(expected_head, preregistration_url):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), "expected head must be a full SHA")
    require(bool(re.fullmatch(r"https://github\.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-[0-9]+",
                              preregistration_url)), "a frozen Issue2 preregistration URL is required")
    require(preregistration_url == PREREGISTRATION_URL, "Worker30 preregistration mismatch")
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
    require((result.raincoats, result.ropes, result.exit_placed, result.turns, result.won) ==
            (observation.raincoats, observation.ropes, observation.exit_placed,
             observation.turns, observation.won), "GameResult disagrees with final public state")
    require((result.open_tunnels, result.visible_water_cells) ==
            (observation.board.open_tunnels, observation.board.visible_water_cells),
            "GameResult disagrees with public board geometry")
    return json.loads(encoded(record))  # Uniform JSON types, no tuple/list differences.


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
    policy = BoundedMergeV4Policy(setup_weight=250)
    observations = []
    # The existing final-observation hook is observational and does not alter choose/RNG.
    policy.on_game_finished = observations.append
    result = play_game(start_card=deck.start_for_setup(setup), deck=deck.draw_deck(),
                       hand_size=setup.hand_size, policy=policy, seed=seed, setup=setup,
                       max_steps=MAX_STEPS)
    # Save the returned GameResult before any callback-count or public-capture checks.
    raw = {"pass": pass_number, "seed": seed, "result": asdict(result),
           "public_capture_count": len(observations), "public_captures": []}
    write_json(raw_path, raw)
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
        require(raw == {"pass": pass_number, "seed": seed, "result": row["record"]["result"],
                        "public_capture_count": 1, "public_captures": [row["record"]]},
                f"raw sidecar disagrees with normalized record: pass {pass_number}, seed {seed}")
    actual = {p for p in (output / "raw-results").rglob("*") if p.is_file()}
    require(actual == expected, "unexpected or incomplete raw sidecar population")


def validate_record(record, seed):
    require(set(record) == {"seed", "result", "setup", "collected_equipment", "board"},
            "missing or unexpected normalized record fields")
    require(record["setup"] == SETUP, "record setup dimensions mismatch")
    require(set(record["result"]) == {"won", "turns", "open_tunnels", "visible_water_cells",
            "raincoats", "ropes", "exit_placed", "reason", "ruleset_id", "setup_id"},
            "incomplete normalized GameResult")
    require(set(record["board"]) == {"placements", "visible_cells"}
            and record["board"]["placements"] and record["board"]["visible_cells"],
            "missing public final board geometry")
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
    first = [r["record"] for r in rows[:len(SEEDS)]]
    second = [r["record"] for r in rows[len(SEEDS):]]
    require(first == second, "normalized final records differ across the two passes")
    wins = [r["seed"] for r in first if r["result"]["won"]]
    return {"games_per_pass": len(SEEDS), "matching_records": len(SEEDS),
            "quota_overshoots": 0,
            "wins": len(wins), "win_rate": len(wins) / len(SEEDS), "winning_seed_ids": wins,
            "failure_reasons": dict(sorted(Counter(r["result"]["reason"] for r in first
                                                    if not r["result"]["won"]).items())),
            "interpretation": "Quota-corrected v2 baseline only; spent seeds; no improvement or confirmation claim",
            "normalized_pass_sha256": hashlib.sha256(encoded(first).encode()).hexdigest()}


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
        receipt["source_after"] = verify_source(expected_head)
        require(receipt["source_after"] == receipt["source_before"], "source changed during execution")
        rows = read_records(output)
        compare_passes(rows)
        verify_raw_sidecars(output, rows)
        receipt.update(status="awaiting_finalization", current=None)
        write_json(output / "receipt.json", receipt)
        print("CANONICAL_BASELINE_COHORT_COMPLETE=800; awaiting successful workflow finalization", flush=True)
        return 0
    except Exception as error:
        fail(receipt, error, "cohort")
        if "source_before" in receipt and "source_after" not in receipt:
            try:
                receipt["source_after"] = verify_source(expected_head)
                require(receipt["source_after"] == receipt["source_before"], "source changed during failed execution")
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
        "schema": "bandido-canonical-baseline-recovery-v1", **identity(expected_head, preregistration_url),
        "status": "integrity_invalid" if integrity_error(error) else "execution_blocked",
        "classification": None, "research_interpretation_performed": False,
        "attempted": None, "current": None, "completed_records": None,
        "execution_extent": "unknown because the original attempt receipt could not be loaded or validated",
        "original_receipt_sha256": original_hash,
        "step_outcomes": {"tests": test_outcome, "cohort": cohort_outcome},
        "errors": [{"phase": "finalize_receipt", "type": type(error).__name__, "message": str(error)}],
    }
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
        for key in ("source_before", "source_after"):
            if key in receipt:
                require(after == receipt[key], f"source changed before finalization: {key}")
    except Exception as error:
        fail(receipt, error, "source_at_finalization")
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
        require(after == receipt["source_before"] == receipt["source_after"], "source changed before finalization")
        summary = compare_passes(rows)
        require(receipt["attempted"] == [{"pass": p, "seed": s} for p in PASSES for s in SEEDS],
                "attempt provenance does not cover the complete ordered population")
        verify_raw_sidecars(output, rows)
        receipt.update(status="complete", classification=CLASSIFICATION,
                       research_interpretation_performed=True, summary=summary, current=None)
        write_json(output / "receipt.json", receipt)
        print("CANONICAL_BASELINE_SUMMARY=" + encoded(summary).strip(), flush=True)
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--preregistration-url", required=True)
    parser.add_argument("--test-outcome", default="unknown")
    parser.add_argument("--cohort-outcome", default="unknown")
    args = parser.parse_args(argv)
    try:
        if args.mode == "initialize":
            initialize(args.output_dir, args.expected_head, args.preregistration_url)
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
