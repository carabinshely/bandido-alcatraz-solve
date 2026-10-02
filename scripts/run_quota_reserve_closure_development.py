"""Frozen Worker35 quota-reserve-closure spent-development experiment; raw output is external to Git.

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
import shutil
import sys
import tempfile
import copy
import inspect
import random
import resource
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worker35_resources as bounded

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_MAIN = "87ddc894668ec60e7a8419e65308cadb0ced6ed9"
ACCEPTED_TREE = "3e0c450ed82ecd47fdd1e239da47d97567d584a6"
REPOSITORY = "carabinshely/bandido-alcatraz-solve"
RULESET = "v2-exact-equipment-quota-limited-collect-full-hand-refresh"
SETUP_ID = "p1-easy-5-exit-hand6-first0-full-hand-refresh"
SETUP = {"player_count": 1, "start_side": "easy-5-exit", "hand_size": 6, "starting_player": 0}
SEEDS = tuple(range(1000000, 1000400))
PASSES = (1, 2, 3)
PHASES = {1: "v4_control", 2: "candidate", 3: "candidate_replay"}
CANDIDATE_PATH = "src/bandido_alcatraz/quota_reserve_closure.py"
SCIENTIFIC_FILE_COUNT = 26
CONTROL_ARRAY_SHA256 = "a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021"
CONTROL_WINS = 45
MIN_NET_WINS = 8
CLASSIFICATION = "quota_reserve_closure_development_no_advancement"
ADVANCED_CLASSIFICATION = "quota_reserve_closure_development_advanced"
HARNESS_PATH = "scripts/run_quota_reserve_closure_development.py"
PREREGISTRATION_URL = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5947200127"
AUDIT_CLARIFICATION_URL = PREREGISTRATION_URL
MAX_STEPS = 1000
BASELINE_COMMIT = "c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853"
REFERENCE_PATH = "src/bandido_alcatraz/quota_reserve_closure_reference.py"
FREEZE_PATH = "experiments/quota-reserve-closure-development/execution-freeze.json"
BRANCH = "research/worker35-quota-reserve-closure"
MARKER = "WORKER35_EXECUTION_GO_JSON"
END_MARKER = "END_WORKER35_EXECUTION_GO_JSON"
BUDGET = None
FREEZE = None
FREEZE_SHA256 = None
EXECUTION_ACTIVE = False


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
        expected = workspace.resolve().parent / "bandido-quota-closure-development" / run_id / attempt
        configured = workspace / ".." / "bandido-quota-closure-development" / run_id / attempt
        require(path.absolute() in (expected, configured) and resolved == expected and expected.resolve() == expected,
                "output must be the nonsymlinked bounded checkout-sibling attempt path")
    return resolved


def write_json(path, value):
    """Atomic, fsynced receipt replacement; raw records use an append-only journal."""
    if BUDGET is not None:
        BUDGET.check(path, len(encoded(value).encode()), replace=True)
    elif FREEZE is not None and (path.name == 'receipt.json' or path.name.startswith('recovery-receipt-')):
        if len(encoded(value).encode()) > FREEZE['resources']['receipt_bytes']:
            raise bounded.ResourceExceeded('receipt exceeds frozen byte reserve')
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
    path = output / 'receipt.json'
    require(not path.is_symlink(), 'symlinked receipt forbidden')
    if FREEZE is not None and path.stat().st_size > FREEZE['resources']['receipt_bytes']:
        raise bounded.ResourceExceeded('receipt exceeds frozen byte bound')
    return bounded.strict_json(path.read_bytes())


def identity(expected_head, preregistration_url):
    return {
        "expected_head": expected_head, "preregistration_url": preregistration_url,
        "audit_clarification_url": AUDIT_CLARIFICATION_URL,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "freeze_sha256": FREEZE_SHA256,
    }


def initialize(output, expected_head, preregistration_url):
    # Never overwrite or silently archive/reuse another attempt's output.
    output = safe_output_path(output)
    output.mkdir(parents=True, exist_ok=False)
    require(FREEZE is not None, "mandatory freeze is missing")
    receipt = {
        "schema": "bandido-quota-reserve-closure-development-v1", **identity(expected_head, preregistration_url),
        "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
        "worker": 35, "freeze": FREEZE,
        "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "max_steps": MAX_STEPS,
        "seed_start": SEEDS[0], "seed_end": SEEDS[-1], "population": len(SEEDS),
        "passes": list(PASSES), "phases": {str(k): v for k, v in PHASES.items()},
        "candidate": {"class": "QuotaReserveClosurePolicy", "module": CANDIDATE_PATH},
        "control_array_sha256": CONTROL_ARRAY_SHA256, "min_net_wins": MIN_NET_WINS, "fresh_seeds_used": False,
        "status": "initialized", "classification": None,
        "research_interpretation_performed": False, "attempted": [],
        "current": None, "completed_records": 0, "errors": [],
    }
    write_json(output / "receipt.json", receipt)
    return receipt


def check_identity(receipt, expected_head, preregistration_url):
    expected = {**identity(expected_head, preregistration_url), "worker": 35,
                "accepted_main": ACCEPTED_MAIN, "accepted_tree": ACCEPTED_TREE,
                "ruleset_id": RULESET, "setup_id": SETUP_ID, "setup": SETUP,
                "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
                "max_steps": MAX_STEPS, "seed_start": SEEDS[0], "seed_end": SEEDS[-1],
                "population": len(SEEDS), "passes": list(PASSES), "phases": {str(k): v for k, v in PHASES.items()},
        "candidate": {"class": "QuotaReserveClosurePolicy", "module": CANDIDATE_PATH},
        "control_array_sha256": CONTROL_ARRAY_SHA256, "min_net_wins": MIN_NET_WINS, "fresh_seeds_used": False}
    require(exact_json(receipt.get("freeze"), FREEZE), "receipt frozen configuration mismatch")
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


def source_inputs(commit):
    result = {}
    for entry in git("ls-tree", "-r", "-z", commit).stdout.split("\0"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        if path == FREEZE_PATH:
            continue
        if not (path.startswith(("src/", "data/", "scripts/", "tests/", ".github/")) or
                path in ("pyproject.toml", "experiments/quota-reserve-closure-development/PROTOCOL.md",
                         "experiments/quota-reserve-closure-development/AUDIT-CONTRACT.md")):
            continue
        mode, kind, blob = metadata.split()
        require(mode == "100644" and kind == "blob", "unsupported execution input: " + path)
        result[path] = blob
    return result


def verify_source(expected_head):
    verify_bytecode_configuration()
    require(FREEZE is not None, "mandatory frozen configuration is unavailable")
    head = git("rev-parse", "HEAD").stdout.strip()
    require(head == expected_head, "checkout differs from exact admitted head")
    git("cat-file", "-e", f"{ACCEPTED_MAIN}^{{commit}}")
    require(git("rev-parse", f"{ACCEPTED_MAIN}^{{tree}}").stdout.strip() == ACCEPTED_TREE,
            "accepted source tree mismatch")
    require(git("merge-base", "--is-ancestor", ACCEPTED_MAIN, head, allowed=(0, 1)).returncode == 0,
            "accepted main is not an ancestor of execution head")
    expected = tree_blobs(BASELINE_COMMIT)
    require(len(expected) == SCIENTIFIC_FILE_COUNT and expected == FREEZE['baseline_source_blobs'],
            "frozen26 canonical model/data comparator mismatch")
    execution = source_inputs(head)
    require(set(execution) == set(FREEZE['execution_source_sha256']), "execution input population mismatch")
    require(CANDIDATE_PATH in execution and REFERENCE_PATH in execution and HARNESS_PATH in execution,
            "candidate/reference/harness missing from frozen source map")
    digests = {}
    for path, blob in execution.items():
        require(blob_hash(ROOT / path) == blob, "source differs from exact execution head: " + path)
        digests[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    require(digests == FREEZE['execution_source_sha256'], "execution sources differ from frozen SHA256 map")
    require(all(execution.get(p) == b for p, b in expected.items()), "canonical baseline/model blobs changed")
    require(not git("ls-files", "--others", "--", "src", "data", "scripts").stdout,
            "untracked executable/model inputs including bytecode are forbidden")
    return {"head": head, "tree": git("rev-parse", "HEAD^{tree}").stdout.strip(),
            "baseline_commit": BASELINE_COMMIT, "source_blobs": expected,
            "execution_blobs": execution, "execution_sha256": digests,
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "executable_sha256": bounded.file_hash(Path(sys.executable).resolve())['sha256']}

def observed_source_snapshot():
    """Forensic hashes even when authoritative source verification fails."""
    snapshot = {}
    paths = {ROOT / HARNESS_PATH, ROOT / CANDIDATE_PATH, ROOT / REFERENCE_PATH, ROOT / "scripts/worker35_resources.py"}
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
    return all(exact_json(first.get(key), second.get(key)) for key in
               ("head", "tree", "baseline_commit", "source_blobs", "execution_blobs", "execution_sha256"))

def admission(event, expected_head, freeze_sha):
    """Only a root-authored absent-to-present body-marker edit admits research."""
    require(type(event) is dict and event.get('action') == 'edited', 'research requires edited PR event')
    pr = event.get('pull_request', {})
    require(pr.get('draft') is True and pr.get('state') == 'open', 'research requires an open draft PR')
    require(pr.get('user', {}).get('login') == 'carabinshely' and
            event.get('sender', {}).get('login') == 'carabinshely', 'unauthorized research author/actor')
    require(pr.get('head', {}).get('repo', {}).get('full_name') == REPOSITORY and
            pr.get('base', {}).get('repo', {}).get('full_name') == REPOSITORY and
            event.get('repository', {}).get('full_name') == REPOSITORY, 'foreign PR repository')
    require(pr.get('head', {}).get('ref') == BRANCH and pr.get('head', {}).get('sha') == expected_head,
            'wrong research branch/head')
    old = event.get('changes', {}).get('body', {}).get('from')
    body = pr.get('body')
    require(type(old) is str and type(body) is str and MARKER not in old,
            'admission must be first absent-to-present marker transition')
    require(body.count(MARKER) == 2 and body.count(END_MARKER) == 1,
            'exactly one bounded execution marker required')
    lines = body.splitlines()
    require(lines.count(MARKER) == 1 and lines.count(END_MARKER) == 1, 'marker lines must be exact')
    start, end = lines.index(MARKER), lines.index(END_MARKER)
    require(end == start + 2, 'execution marker must contain one JSON line')
    go = bounded.strict_json(lines[start + 1])
    schema_object(go, {'head', 'tree', 'freeze_sha256', 'execution_go_url'}, 'execution-go marker')
    require(go['head'] == expected_head and go['freeze_sha256'] == freeze_sha, 'go head/freeze mismatch')
    require(type(go['tree']) is str and re.fullmatch('[0-9a-f]{40}', go['tree']), 'go tree invalid')
    require(type(go['execution_go_url']) is str and re.fullmatch(
        r'https://github\.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-[0-9]+',
        go['execution_go_url']), 'execution-go Issue2 provenance required')
    require(go['execution_go_url'] != PREREGISTRATION_URL, 'separate execution-go required')
    return go


def preflight(expected_head, preregistration_url):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), "expected head must be a full SHA")
    require(preregistration_url == PREREGISTRATION_URL, "Worker35 preregistration mismatch")
    for name in ("GITHUB_ACTIONS", "RUNNER_NAME", "GITHUB_REPOSITORY", "EXPECTED_HEAD",
                 "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_EVENT_PATH", "PYTHONHASHSEED"):
        if not os.environ.get(name):
            raise InfrastructureError(f"missing Actions context: {name}")
    require(os.environ['GITHUB_ACTIONS'] == 'true', 'research requires GitHub Actions')
    require(os.environ['RUNNER_NAME'] == 'bandido-alcatraz-ci', 'unauthorized research runner')
    require(os.environ['GITHUB_REPOSITORY'] == REPOSITORY, 'wrong repository')
    require(os.environ['GITHUB_RUN_ATTEMPT'] == '1', 'rerun attempts forbidden')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request', 'wrong event type')
    require(os.environ['EXPECTED_HEAD'] == expected_head, 'expected-head environment mismatch')
    go = admission(bounded.strict_json(Path(os.environ['GITHUB_EVENT_PATH']).read_bytes()), expected_head, FREEZE_SHA256)
    require(os.environ['PYTHONHASHSEED'] == '0', 'PYTHONHASHSEED must be0')
    actual_runtime = {'implementation': platform.python_implementation(), 'version': platform.python_version(),
                      'executable_sha256': bounded.file_hash(Path(sys.executable).resolve())['sha256']}
    require(actual_runtime == FREEZE['runtime'], 'exact frozen runtime mismatch')
    source = verify_source(expected_head)
    require(source['tree'] == go['tree'], 'execution tree differs from go')
    return source

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
    if BUDGET is not None:
        BUDGET.check(path, len(encoded(value).encode()))
    with path.open("a", encoding="utf-8") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def trace_path(output, pass_number, seed):
    return output / "decision-traces" / f"pass-{pass_number}" / f"{seed}.jsonl"


def state_witness(state, catalog):
    """Harness-only physical conservation; hidden zones never reach a policy.

    Persist only a full-state digest at decision boundaries. The final sorted
    zone inventory is separate end-state evidence, never a decision input.
    """
    from bandido_alcatraz.game import GameState
    require(type(state) is GameState, 'trusted runner GameState witness unavailable')
    zones = {'placed': [p.card_id for p in state.board.placements[1:]],
             'collected': [e.card_id for e in state.collected_equipment],
             'hand': [c.card_id for hand in state.private_hands for c in hand],
             'draw': [c.card_id for c in state.draw_pile],
             'set_aside': [c.card_id for c in state.face_down_set_aside]}
    ids = [item for zone in zones.values() for item in zone]
    expected = {c.card_id: _card_record(c) for c in catalog}
    require(len(ids) == len(set(ids)) == 69 and set(ids) == set(expected),
            'physical69-card conservation failure')
    for c in [*state.hand, *state.draw_pile, *state.face_down_set_aside,
              *(e.card for e in state.collected_equipment)]:
        require(exact_json(_card_record(c), expected[c.card_id]), 'physical card definition mutation')
    require(state.set_aside_unplayable == len(state.face_down_set_aside), 'set-aside count mismatch')
    public = public_observation_record(state.observation())
    private = {'public': public,
               'draw': [_card_record(c) for c in state.draw_pile],
               'hands': [[_card_record(c) for c in hand] for hand in state.private_hands],
               'aside': [_card_record(c) for c in state.face_down_set_aside]}
    return digest(private), {'inventory_count': len(ids), 'inventory_sha256': digest(sorted(ids)),
                             'zones': {name: sorted(items) for name, items in zones.items()}}


def append_metrics(path, value):
    original = sys.exc_info()[1]
    try:
        append_jsonl(path, value)
    except Exception as write_error:
        if original is not None:
            raise original from write_error
        raise


def decision_runtime(output, pass_number, seed, ordinal, scope, invoke, rng, caps, persist_return):
    """Always persist scope metrics; actual outputs are saved before checking."""
    start, cpu = time.monotonic(), time.process_time()
    meter = bounded.Meter(call_caps=caps, rng=rng, capture_control=scope == 'control')
    status, cost = 'failed', None
    previous = sys.getprofile()
    require(previous is None or callable(previous), 'native profile hook cannot safely be forwarded')
    wall_guard = bounded.deadline(caps['wall_seconds'], scope + ' decision')
    cpu_guard = bounded.cpu_deadline(caps['cpu_seconds'], scope)
    try:
        meter.__enter__()
        with wall_guard, cpu_guard:
            result = invoke()
            roots = meter.control_roots if scope == 'control' else result[1]['roots']
            require(type(roots) is list, 'missing actual canonical roots')
            cost = {**meter.counts, 'roots': len(roots)}
            # Durable actual output precedes post-return CPU/root checks and the
            # metrics finally block. A returned science object is never lost
            # because a later resource gate or metrics write rejects the call.
            persist_return(result, cost, meter)
        if len(roots) > caps['roots']:
            raise bounded.ResourceExceeded(scope + ': root ceiling exceeded')
        if time.process_time() - cpu > caps['cpu_seconds']:
            raise bounded.ResourceExceeded(scope + ': CPU ceiling exceeded')
        status = 'returned'
        return result, cost, meter
    finally:
        # Explicit caller finally also catches a profiling exception on the
        # return of ANY context manager's __enter__ while our hook is active.
        try:
            # A retained __enter__ exception may retain a yielded timer
            # generator. Close it now rather than depend on later collection.
            cpu_guard.gen.close()
            wall_guard.gen.close()
        finally:
            sys.setprofile(previous)
        append_metrics(output / 'resource-metrics.jsonl', {'kind': 'decision', 'pass': pass_number,
            'seed': seed, 'ordinal': ordinal, 'scope': scope, 'wall_seconds': time.monotonic() - start,
            'cpu_seconds': time.process_time() - cpu,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'cost': cost if cost is not None else {**meter.counts, 'roots': None}, 'status': status})


class AuditPolicy:
    """Trusted boundary: public-only independent checking, never another game.

    Canonical play_game owns terminal checks, refresh, shuffle and real apply.
    Its caller frame is inspected only by the harness for immutable-state hashes;
    no engine/private reference is passed to either policy implementation.
    """
    def __init__(self, policy, *, reference=None, catalog, output, pass_number, seed, limits,
                 candidate_limits=None, reference_limits=None, state_provider=None):
        self.policy, self.reference, self.catalog = policy, reference, catalog
        self.output, self.pass_number, self.seed, self.limits = output, pass_number, seed, limits
        self.candidate_limits, self.reference_limits = candidate_limits, reference_limits
        self.state_provider = state_provider
        self.path = trace_path(output, pass_number, seed)
        self.calls_path = output / 'call-results' / f'pass-{pass_number}' / f'{seed}.jsonl'
        for path in (self.path, self.calls_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8') as stream:
                stream.flush()
                os.fsync(stream.fileno())
        self.ordinal = self.non_null_choices = 0

    def trace_counts(self):
        return {'decision_count': self.ordinal, 'non_null_choices': self.non_null_choices}

    def persist_return(self, scope, returned, observed_cost, meter, expected_science=None):
        if scope == 'control':
            roots = meter.control_roots
            best = max((r['score'] for r in roots), default=None)
            result = {'chosen': move_record(returned), 'roots': roots,
                      'final': [i for i, r in enumerate(roots) if r['score'] == best], 'cost': observed_cost}
        else:
            chosen, science, cost = returned
            result = {'chosen': move_record(chosen), 'cost': cost}
            if scope == 'candidate':
                result['scientific'] = science
            else:
                result['scientific_sha256'] = digest(science)
                if not exact_json(expected_science, science):
                    result['scientific'] = science
        append_jsonl(self.calls_path, {'ordinal': self.ordinal, 'scope': scope, 'result': result})

    def choose(self, observation, rng):
        from bandido_alcatraz.simulate import play_game
        # Direct trusted canonical runner only in production. Invented unit
        # fixtures provide a synthetic state witness; they never load real data.
        frame = inspect.currentframe().f_back
        if self.state_provider is None:
            require(frame.f_code is play_game.__code__, 'policy called outside canonical game runner')
            state = frame.f_locals['state']
        else:
            state = self.state_provider()
        engine_before, unused = state_witness(state, self.catalog)
        public = public_observation_record(observation)
        self.ordinal += 1
        before_state = rng.getstate()
        before = digest(before_state)
        append_jsonl(self.path, {'event': 'decision_started', 'ordinal': self.ordinal,
                               'observation': public, 'rng_before_sha256': before})
        copied = copy.deepcopy(observation)
        reference_rng = random.Random()
        reference_rng.setstate(before_state)
        if self.pass_number == 1:
            chosen, cost, meter = decision_runtime(self.output, self.pass_number, self.seed, self.ordinal,
                'control', lambda: self.policy.choose(observation, rng), rng, self.limits['control'],
                lambda result, cost, meter: self.persist_return('control', result, cost, meter))
            roots = meter.control_roots
            best = max((r['score'] for r in roots), default=None)
            final = [i for i, r in enumerate(roots) if r['score'] == best]
            audit = {'public_observation_sha256': digest(public), 'chosen_move': move_record(chosen),
                     'rng_before_sha256': before, 'rng_after_sha256': digest(rng.getstate()),
                     'roots': roots, 'final': final, 'cost': cost}
            expected_tier = [roots[i]['move'] for i in final]
            expected_choice = reference_rng.choice(expected_tier) if expected_tier else None
            require(exact_json(move_record(chosen), expected_choice) and rng.getstate() == reference_rng.getstate(),
                    'control actual choice/RNG differs from canonical final tier')
            reference_meter = None
        else:
            returned, observed_cost, meter = decision_runtime(self.output, self.pass_number, self.seed, self.ordinal,
                'candidate', lambda: self.policy.evaluate(observation, rng, limits=self.candidate_limits), rng,
                self.limits['candidate'],
                lambda result, cost, meter: self.persist_return('candidate', result, cost, meter))
            chosen, science, cost = returned
            require(exact_json(cost, observed_cost), 'candidate physical operation audit disagrees with harness')
            checked, observed_reference_cost, reference_meter = decision_runtime(self.output, self.pass_number,
                self.seed, self.ordinal, 'reference',
                lambda: self.reference.evaluate(copied, reference_rng, limits=self.reference_limits),
                reference_rng, self.limits['reference'],
                lambda result, cost, meter: self.persist_return('reference', result, cost, meter, science))
            other, reference_science, reference_cost = checked
            require(exact_json(reference_cost, observed_reference_cost), 'reference physical operation audit mismatch')
            require(exact_json(science, reference_science), 'candidate/reference scientific audit disagreement')
            require(exact_json(move_record(chosen), move_record(other)) and rng.getstate() == reference_rng.getstate(),
                    'candidate/reference selected move or actual RNG disagreement')
            require(science['input_before'] == digest(public) == science['input_after']
                    and science['rng_before'] == before and science['rng_after'] == digest(rng.getstate())
                    and exact_json(science['chosen'], move_record(chosen)), 'science boundary/RNG mismatch')
            require(exact_json(public_observation_record(copied), public), 'reference mutated public input')
            expected_tier = [science['roots'][i]['move'] for i in science['tiers']['final']]
            audit = {'scientific_sha256': digest(science), 'reference_scientific_sha256': digest(reference_science),
                     'candidate_cost': cost, 'reference_cost': reference_cost}
        expected_calls = [expected_tier] if expected_tier else []
        require(exact_json(meter.choice_tiers, expected_calls), 'policy choice call count or tier mismatch')
        if reference_meter is not None:
            require(exact_json(reference_meter.choice_tiers, expected_calls), 'reference choice call count/tier mismatch')
        engine_after, unused = state_witness(state, self.catalog)
        after_public = public_observation_record(observation)
        boundary = {'public_before': digest(public), 'public_after': digest(after_public),
            'engine_before': engine_before, 'engine_after': engine_after,
            'choice_calls': len(meter.choice_tiers), 'choice_tier': expected_tier,
            'reference_choice_calls': None if reference_meter is None else len(reference_meter.choice_tiers),
            'reference_choice_tier': None if reference_meter is None else expected_tier}
        audit['boundary'] = boundary
        # Preserve completed outputs before boundary/schema gates can reject.
        append_jsonl(self.path, {'event': 'decision_completed', 'ordinal': self.ordinal, 'audit': audit})
        require(exact_json(public, after_public), 'policy mutated detached public observation')
        require(engine_before == engine_after, 'decision mutated real game state')
        if chosen is not None:
            self.non_null_choices += 1
        return chosen


def iter_jsonl(path):
    limits = FREEZE['resources']
    if path.stat().st_size > bounded.jsonl_limit(path, limits):
        raise bounded.ResourceExceeded('JSONL artifact exceeds its frozen class byte bound')
    total = 0
    with path.open('rb') as stream:
        while True:
            line = stream.readline(limits['line_bytes'] + 1)
            if not line:
                break
            total += len(line)
            if total > bounded.jsonl_limit(path, limits):
                raise bounded.ResourceExceeded('JSONL artifact exceeds its frozen class byte bound')
            if len(line) > limits['line_bytes']:
                raise bounded.ResourceExceeded('JSONL line exceeds frozen byte bound')
            if not line.endswith(b'\n'):
                raise InfrastructureError('interrupted trace write; original prefix preserved')
            yield bounded.strict_json(line)


def read_trace(path):
    return list(iter_jsonl(path))


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


def validate_cost(cost, scope, root_count):
    schema_object(cost, {*bounded.OPS, 'roots'}, 'physical cost')
    for key in bounded.OPS:
        integer(cost[key], key, 0, FREEZE['resources']['per_call'][scope][key])
    integer(cost['roots'], 'roots', 0, FREEZE['resources']['per_call'][scope]['roots'])
    require(cost['roots'] == root_count, 'root count/cost mismatch')


def validate_trace(events, record, pass_number, science_by_ordinal=None):
    require(len(events) >= 2 and exact_json(events[-2], {'event': 'game_returned', 'result': record['result']}),
            'trace result/normalized record disagreement or partial final decision')
    completion = events[-1]
    schema_object(completion, {'event', 'record_sha256', 'trace_counts'}, 'trace completion')
    require(completion['event'] == 'game_completed' and completion['record_sha256'] == digest(record),
            'trace completion record digest mismatch')
    trace_counts_schema(completion['trace_counts'])
    decisions = events[:-2]
    require(len(decisions) % 2 == 0 and len(decisions) // 2 == completion['trace_counts']['decision_count'],
            'partial/count-mismatched decision trace')
    actions, flags = 0, Counter()
    for ordinal in range(1, len(decisions) // 2 + 1):
        started, completed = decisions[2 * ordinal - 2:2 * ordinal]
        schema_object(started, {'event', 'ordinal', 'observation', 'rng_before_sha256'}, 'decision start')
        schema_object(completed, {'event', 'ordinal', 'audit'}, 'decision completion')
        require(started['event'] == 'decision_started' and completed['event'] == 'decision_completed'
                and started['ordinal'] == completed['ordinal'] == ordinal, 'decision event/order mismatch')
        public = started['observation']
        observation_schema(public)
        require(public['turns'] == actions, 'observation turns differ from preceding choices')
        audit = completed['audit']
        if pass_number == 1:
            schema_object(audit, {'public_observation_sha256', 'chosen_move', 'rng_before_sha256',
                'rng_after_sha256', 'roots', 'final', 'cost', 'boundary'}, 'control audit')
            chosen, roots, final = audit['chosen_move'], audit['roots'], audit['final']
            before, after, input_hash = audit['rng_before_sha256'], audit['rng_after_sha256'], audit['public_observation_sha256']
            validate_cost(audit['cost'], 'control', len(roots))
            best = max((r['score'] for r in roots), default=None)
            require(final == [i for i, r in enumerate(roots) if r['score'] == best], 'control maximal tier mismatch')
        else:
            schema_object(audit, {'scientific_sha256', 'reference_scientific_sha256', 'candidate_cost', 'reference_cost', 'boundary'},
                          'candidate audit')
            require(science_by_ordinal is not None, 'candidate science raw bytes required')
            science = science_by_ordinal[ordinal]
            require(audit['scientific_sha256'] == audit['reference_scientific_sha256'] == digest(science),
                    'persisted independent science mismatch')
            schema_object(science, {'schema', 'input_before', 'input_after', 'roots', 'supply', 'tiers', 'guards',
                'flags', 'chosen_index', 'chosen', 'rng_before', 'rng_after'}, 'science')
            require(science['schema'] == 'worker35-scientific-v1', 'science schema')
            chosen, roots, final = science['chosen'], science['roots'], science['tiers']['final']
            before, after, input_hash = science['rng_before'], science['rng_after'], science['input_before']
            require(science['input_after'] == input_hash, 'science mutated public input')
            validate_cost(audit['candidate_cost'], 'candidate', len(roots))
            validate_cost(audit['reference_cost'], 'reference', len(roots))
            for name, value in science['flags'].items():
                require(type(value) is bool, 'nonboolean mechanism flag')
                flags[name] += value
            require(science['chosen_index'] is None if chosen is None else
                    type(science['chosen_index']) is int and science['chosen_index'] in final and
                    exact_json(roots[science['chosen_index']]['move'], chosen), 'chosen root/index mismatch')
        require(input_hash == digest(public) and before == started['rng_before_sha256'], 'trace public/RNG hash mismatch')
        for root in roots:
            schema_object(root, {'move', 'score'}, 'root')
            require(type(root['score']) is int, 'root score must be integer')
            move_schema(root['move'], public['hand'])
        require(type(final) is list and all(type(i) is int and 0 <= i < len(roots) for i in final)
                and final == sorted(set(final)), 'final tier malformed/reordered')
        expected_tier = [roots[i]['move'] for i in final]
        require(any(exact_json(chosen, m) for m in expected_tier) if expected_tier else chosen is None,
                'selected move outside final tier')
        require(bool(roots) == bool(expected_tier), 'empty final tier hid legal roots')
        if chosen is None:
            require(before == after, 'empty decision consumed RNG')
        boundary = audit['boundary']
        schema_object(boundary, {'public_before', 'public_after', 'engine_before', 'engine_after', 'choice_calls',
                                'choice_tier', 'reference_choice_calls', 'reference_choice_tier'}, 'decision boundary')
        require(boundary['public_before'] == boundary['public_after'] == input_hash
                and boundary['engine_before'] == boundary['engine_after'], 'boundary immutability failure')
        require(boundary['choice_calls'] == int(bool(final)) and exact_json(boundary['choice_tier'], expected_tier),
                'actual choice call/tier mismatch')
        require(boundary['reference_choice_calls'] == (None if pass_number == 1 else int(bool(final))) and
                exact_json(boundary['reference_choice_tier'], None if pass_number == 1 else expected_tier),
                'reference actual choice call/tier mismatch')
        actions += chosen is not None
    require(actions == record['result']['turns'] == completion['trace_counts']['non_null_choices'],
            'trace action/result mismatch')
    return dict(flags)


def equal_files(first, second):
    with first.open('rb') as a, second.open('rb') as b:
        while True:
            x, y = a.read(1024 * 1024), b.read(1024 * 1024)
            require(x == y, 'candidate/replay exact trace bytes differ')
            if not x:
                return


def verify_traces(output, rows):
    expected = {trace_path(output, row['pass'], row['record']['seed']) for row in rows}
    require({p for p in (output / 'decision-traces').rglob('*') if p.is_file()} == expected,
            'unexpected/incomplete trace population')
    expected_calls = {output / 'call-results' / f"pass-{row['pass']}" / f"{row['record']['seed']}.jsonl" for row in rows}
    require({p for p in (output / 'call-results').rglob('*') if p.is_file()} == expected_calls,
            'unexpected/incomplete call-output population')
    flags, comparable, different = Counter(), 0, 0
    for row in rows:
        p, seed = row['pass'], row['record']['seed']
        events = read_trace(trace_path(output, p, seed))
        raw_calls = read_trace(output / 'call-results' / f'pass-{p}' / f'{seed}.jsonl')
        sciences = {call['ordinal']: call['result']['scientific'] for call in raw_calls if call['scope'] == 'candidate'}
        observed = validate_trace(events, row['record'], p, sciences)
        calls = iter(raw_calls)
        for completed in events[:-2][1::2]:
            audit = completed['audit']
            for scope in (('control',) if p == 1 else ('candidate', 'reference')):
                if scope == 'control':
                    result = {'chosen': audit['chosen_move'], 'roots': audit['roots'],
                              'final': audit['final'], 'cost': audit['cost']}
                else:
                    science = sciences[completed['ordinal']]
                    result = {'chosen': science['chosen'], 'cost': audit[scope + '_cost']}
                    result.update({'scientific': science} if scope == 'candidate' else {'scientific_sha256': digest(science)})
                require(exact_json(next(calls, None), {'ordinal': completed['ordinal'], 'scope': scope, 'result': result}),
                        'raw returned decision disagrees with completed audit')
        require(next(calls, None) is None, 'extra raw returned call')
        raw = bounded.strict_json((output / 'raw-results' / f'pass-{p}' / f'{seed}.json').read_bytes())
        require(exact_json(events[-1]['trace_counts'], raw['trace_counts']), 'trace/sidecar counts differ')
        if p != 2:
            continue
        flags.update(observed)
        equal_files(trace_path(output, p, seed), trace_path(output, 3, seed))
        equal_files(output / 'call-results' / 'pass-2' / f'{seed}.jsonl', output / 'call-results' / 'pass-3' / f'{seed}.jsonl')
        control = read_trace(trace_path(output, 1, seed))
        for c, d in zip(control[:-2][1::2], events[:-2][1::2]):
            a, b = c['audit'], sciences[d['ordinal']]
            if (a['public_observation_sha256'], a['rng_before_sha256']) == (b['input_before'], b['rng_before']):
                comparable += 1
                different += not exact_json(a['chosen_move'], b['chosen'])
    return {'mechanism_counts': dict(sorted(flags.items())), 'matched_observation_rng_decisions': comparable,
            'selected_action_differences_in_matched_contexts': different,
            'candidate_replay_trace_matches': len(SEEDS),
            'action_difference_scope': 'same seed and ordinal with identical public observation and pre-choice RNG hashes'}


def one_game(seed, *, output, pass_number):
    require(EXECUTION_ACTIVE, "game compute requires the admitted bounded run scope")
    require(type(seed) is int and seed in SEEDS, 'out-of-scope seed')
    require(type(pass_number) is int and pass_number in PASSES, 'out-of-scope pass')
    raw_path = output / 'raw-results' / f'pass-{pass_number}' / f'{seed}.json'
    require(not raw_path.exists(), 'raw result exists; attempt reuse forbidden')
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    verify_bytecode_configuration()
    source_path = str(ROOT / 'src')
    if sys.path[0] != source_path:
        sys.path.insert(0, source_path)
    from bandido_alcatraz.physical_deck import load_real_deck
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    from bandido_alcatraz.rules import RULESET_ID
    from bandido_alcatraz.setup import GameSetup
    from bandido_alcatraz.simulate import play_game
    require(RULESET_ID == RULESET, 'imported ruleset mismatch')
    setup = GameSetup()
    require(setup.setup_id == SETUP_ID, 'imported setup mismatch')
    deck = load_real_deck(ROOT / 'data')
    catalog, start = tuple(deck.draw_deck()), deck.start_for_setup(setup)
    options = {}
    if pass_number == 1:
        policy = BoundedMergeV4Policy(setup_weight=250)
    else:
        from bandido_alcatraz import quota_reserve_closure as candidate
        from bandido_alcatraz import quota_reserve_closure_reference as checker
        inputs = {'catalog': catalog, 'start_card': start, 'exit_card': deck.exit_card}
        policy = candidate.QuotaReserveClosurePolicy(**inputs)
        options = {'reference': checker.QuotaReserveClosureReference(**inputs),
            'candidate_limits': candidate.OperationLimits(**{k: FREEZE['resources']['per_call']['candidate'][k] for k in bounded.OPS}),
            'reference_limits': checker.OperationLimits(**{k: FREEZE['resources']['per_call']['reference'][k] for k in bounded.OPS})}
    for name, module in tuple(sys.modules.items()):
        if name == 'bandido_alcatraz' or name.startswith('bandido_alcatraz.'):
            require(Path(module.__file__).resolve().is_relative_to(ROOT / 'src'), 'import outside pinned source: ' + name)
    policy = AuditPolicy(policy, output=output, pass_number=pass_number, seed=seed, catalog=catalog,
                         limits=FREEZE['resources']['per_call'], **options)
    observations, endstate = [], {}
    def capture(observation):
        frame = inspect.currentframe().f_back
        require(frame.f_globals.get('__name__') == 'bandido_alcatraz.simulate'
                and frame.f_code.co_name == 'finish', 'unexpected final observation caller')
        observations.append(observation)
        unused, endstate['conservation'] = state_witness(frame.f_locals['state'], catalog)
    policy.on_game_finished = capture
    result = play_game(start_card=start, deck=deck.draw_deck(), hand_size=setup.hand_size,
                       policy=policy, seed=seed, setup=setup, max_steps=MAX_STEPS)
    raw = {'pass': pass_number, 'seed': seed, 'result': asdict(result),
           'public_capture_count': len(observations), 'public_captures': [], 'trace_counts': policy.trace_counts(),
           'final_public_observation': None, 'conservation': endstate.get('conservation')}
    write_json(raw_path, raw)
    append_jsonl(policy.path, {'event': 'game_returned', 'result': asdict(result)})
    normalized = []
    for observation in observations:
        record = {}
        raw['public_captures'].append(record)
        try:
            raw['final_public_observation'] = public_observation_record(observation)
            normalized.append(final_record(seed, result, observation, capture=record))
        except Exception as error:
            raw['capture_error'] = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            write_json(raw_path, raw)
    require(len(observations) == 1, 'missing/repeated final public observation')
    append_jsonl(policy.path, {'event': 'game_completed', 'record_sha256': digest(normalized[0]),
                             'trace_counts': policy.trace_counts()})
    return normalized[0]


def append_record(output, pass_number, record):
    append_jsonl(output / "completed.jsonl", {"pass": pass_number, "record": record})

def read_records(output):
    return list(iter_jsonl(output / 'completed.jsonl'))


def final_record_from_wire(seed, result, public):
    return {'seed': seed, 'result': result, 'setup': public['setup'],
        'board': {'placements': public['board']['placements'], 'visible_cells': public['board']['cells']},
        'collected_equipment': [{'order': i, 'card_id': e['card']['card_id'], 'material': e['card']['material'],
            'turn': e['turn'], 'player_index': e['player_index'], 'cells': e['card']['cells']}
            for i, e in enumerate(public['collected_equipment'], 1)]}


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
                        "public_capture_count": 1, "public_captures": [row["record"]], "trace_counts": raw["trace_counts"],
                        "final_public_observation": raw['final_public_observation'], "conservation": raw['conservation']}),
                f"raw sidecar disagrees with normalized record: pass {pass_number}, seed {seed}")
        final = raw['final_public_observation']
        observation_schema(final)
        require(exact_json(final_record_from_wire(seed, raw['result'], final), row['record']),
                'final public observation/record mismatch')
        proof = raw['conservation']
        schema_object(proof, {'inventory_count', 'inventory_sha256', 'zones'}, 'conservation')
        schema_object(proof['zones'], {'placed', 'collected', 'hand', 'draw', 'set_aside'}, 'conservation zones')
        ids = [c for zone in proof['zones'].values() for c in zone]
        require(len(ids) == len(set(ids)) == proof['inventory_count'] == 69
                and proof['inventory_sha256'] == digest(sorted(ids)), 'terminal physical inventory mismatch')
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
            "normalized_candidate_sha256": digest(candidate),
            "equipment_ready": {"control": sum((r['result']['raincoats'], r['result']['ropes']) == (3, 2) for r in control),
                                "candidate": sum((r['result']['raincoats'], r['result']['ropes']) == (3, 2) for r in candidate)},
            "terminal_components": {phase: {
                'visible_water_remaining': sum(r['result']['visible_water_cells'] > 0 for r in records),
                'exit_unplaced': sum(not r['result']['exit_placed'] for r in records),
                'closed_tunnels_conditions_failed': sum(r['result']['reason'] == 'closed_tunnels_conditions_failed' for r in records)
            } for phase, records in (('control', control), ('candidate', candidate))}}


def integrity_error(error):
    return isinstance(error, (ValueError, AssertionError, TypeError, KeyError, IndexError, AttributeError)) or \
        type(error).__name__ in ('IntegrityError', 'ReferenceIntegrityError', 'ReferenceInputError')


def fail(receipt, error, phase):
    invalid = integrity_error(error) or receipt.get('status') == 'integrity_invalid'
    limited = isinstance(error, (bounded.ResourceExceeded, MemoryError, TimeoutError)) or \
        type(error).__name__ == 'ResourceExceeded' or receipt.get('status') == 'resource_incomplete'
    receipt.update(status='integrity_invalid' if invalid else 'resource_incomplete' if limited else 'execution_blocked',
                   classification=None, research_interpretation_performed=False)
    receipt.pop('summary', None)
    receipt['errors'].append({'phase': phase, 'type': type(error).__name__, 'message': str(error)})


def require_disk_capacity(output, limits):
    """Read-only admission: full raw + compressed transport +2GiB headroom."""
    required = limits['evidence_bytes'] + limits['archive_bytes'] + 2 * 1024 ** 3
    available = shutil.disk_usage(output).free
    if available < required:
        raise bounded.ResourceExceeded(
            f'insufficient free disk before any seed: need {required} bytes, available {available}')


def run(output, expected_head, preregistration_url):
    global BUDGET, EXECUTION_ACTIVE
    receipt = read_receipt(output)
    check_identity(receipt, expected_head, preregistration_url)
    require(receipt['status'] == 'initialized' and not receipt['attempted']
            and not (output / 'completed.jsonl').exists(), 'attempt already used; resume/mixing forbidden')
    started = time.monotonic()
    meter = None
    BUDGET = bounded.EvidenceBudget(output, FREEZE['resources'])
    try:
        receipt['source_before'] = preflight(expected_head, preregistration_url)
        require(same_source_bytes(receipt['source_before'], receipt['source_at_initialization']),
                'source changed after initialization')
        require_disk_capacity(output, FREEZE['resources'])
        receipt['memory_limit'] = bounded.enforce_memory(FREEZE['resources']['address_space_bytes'])
        receipt['status'] = 'running'
        write_json(output / 'receipt.json', receipt)
        sys.path.insert(0, str(ROOT / 'src'))
        import worker31_geometry as geometry
        cards = geometry.load_cards(ROOT / 'data', receipt['source_before']['source_blobs'])
        meter = bounded.Meter(total_caps=FREEZE['resources']['total_operations'])
        EXECUTION_ACTIVE = True
        previous = sys.getprofile()
        require(previous is None or callable(previous), 'native profile hook cannot safely be forwarded')
        wall_guard = bounded.deadline(max(.000001, FREEZE['resources']['cohort_wall_seconds'] - (time.monotonic() - started)), 'whole cohort')
        try:
            meter.__enter__()
            with wall_guard:
                for pass_number in PASSES:
                    for seed in SEEDS:
                        receipt['current'] = {'pass': pass_number, 'seed': seed}
                        receipt['attempted'].append(dict(receipt['current']))
                        write_json(output / 'receipt.json', receipt)
                        game_start, game_cpu, status = time.monotonic(), time.process_time(), 'failed'
                        game_operations = dict(meter.counts)
                        try:
                            record = one_game(seed, output=output, pass_number=pass_number)
                            append_record(output, pass_number, record)
                            receipt['completed_records'] += 1
                            write_json(output / 'receipt.json', receipt)
                            validate_record(record, seed)
                            geometry.validate_record(record, seed, cards)
                            status = 'complete'
                        finally:
                            append_metrics(output / 'resource-metrics.jsonl', {'kind': 'game', 'pass': pass_number,
                                'seed': seed, 'wall_seconds': time.monotonic() - game_start,
                                'cpu_seconds': time.process_time() - game_cpu,
                                'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'status': status,
                                'operations': {k: meter.counts[k] - game_operations[k] for k in bounded.OPS}})
                    if pass_number == 1:
                        control = [row['record'] for row in read_records(output)]
                        require(digest(control) == CONTROL_ARRAY_SHA256, 'complete control differs from accepted Worker30')
                        require(sum(row['result']['won'] for row in control) == CONTROL_WINS, 'control45-win mismatch')
                receipt['source_after'] = verify_source(expected_head)
                require(exact_json(receipt['source_after'], receipt['source_before']), 'source changed during execution')
        finally:
            try:
                wall_guard.gen.close()
            finally:
                sys.setprofile(previous)
        EXECUTION_ACTIVE = False
        receipt['total_operations'] = dict(meter.counts)
        receipt['cohort_elapsed_seconds'] = time.monotonic() - started
        require(receipt['cohort_elapsed_seconds'] <= FREEZE['resources']['cohort_wall_seconds'], 'cohort elapsed exceeds freeze')
        receipt.update(status='awaiting_finalization', current=None)
        write_json(output / 'receipt.json', receipt)
        print('QUOTA_CLOSURE_DEVELOPMENT_COHORT_COMPLETE=1200; awaiting finalization', flush=True)
        return 0
    except Exception as error:
        EXECUTION_ACTIVE = False
        receipt['cohort_elapsed_seconds'] = time.monotonic() - started
        receipt['total_operations'] = None if meter is None else dict(meter.counts)
        fail(receipt, error, 'cohort')
        receipt['observed_source_after_failure'] = observed_source_snapshot()
        if 'source_before' in receipt and 'source_after' not in receipt:
            try:
                receipt['source_after'] = verify_source(expected_head)
                require(exact_json(receipt['source_after'], receipt['source_before']), 'source changed during failed execution')
            except Exception as source_error:
                fail(receipt, source_error, 'source_after')
        write_json(output / 'receipt.json', receipt)
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
        "schema": "bandido-quota-reserve-closure-development-recovery-v1", **identity(expected_head, preregistration_url),
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


def _finalize(output, expected_head, preregistration_url, test_outcome, cohort_outcome):
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
        verify_resource_metrics(output, rows, receipt)
        receipt.update(status="complete", classification=summary["classification"],
                       research_interpretation_performed=True, summary=summary, current=None)
        write_json(output / "receipt.json", receipt)
        print("QUOTA_CLOSURE_DEVELOPMENT_SUMMARY=" + encoded(summary).strip(), flush=True)
        return 0
    except Exception as error:
        if receipt["observed_journal_records"] is None or receipt["observed_journal_records"] < durable_count:
            receipt["execution_extent"] = "unknown; preserve last durable count because the journal is unavailable or contradictory"
        fail(receipt, error, "finalize")
        write_json(output / "receipt.json", receipt)
        return 1


def verify_resource_metrics(output, rows, receipt):
    metrics = iter_jsonl(output / 'resource-metrics.jsonl')
    decisions = {k: 0 for k in bounded.OPS}
    games = {k: 0 for k in bounded.OPS}
    for row in rows:
        p, seed = row['pass'], row['record']['seed']
        calls = read_trace(output / 'call-results' / f'pass-{p}' / f'{seed}.jsonl')
        game_decisions = {k: 0 for k in bounded.OPS}
        for call in calls:
            metric = next(metrics, None)
            schema_object(metric, {'kind', 'pass', 'seed', 'ordinal', 'scope', 'wall_seconds', 'cpu_seconds',
                                  'peak_rss_kib', 'cost', 'status'}, 'decision metrics')
            require((metric['kind'], metric['pass'], metric['seed'], metric['ordinal'], metric['scope'], metric['status']) ==
                    ('decision', p, seed, call['ordinal'], call['scope'], 'returned'), 'decision metric order/status')
            require(exact_json(metric['cost'], call['result']['cost']), 'metric/returned physical cost disagreement')
            caps = FREEZE['resources']['per_call'][call['scope']]
            for key in ('wall_seconds', 'cpu_seconds'):
                require(type(metric[key]) in (int, float) and 0 <= metric[key] <= caps[key], 'decision time ceiling violation')
            for key in bounded.OPS:
                decisions[key] += metric['cost'][key]
                game_decisions[key] += metric['cost'][key]
            integer(metric['peak_rss_kib'], 'peak RSS', 0, FREEZE['resources']['address_space_bytes'] // 1024)
        metric = next(metrics, None)
        schema_object(metric, {'kind', 'pass', 'seed', 'wall_seconds', 'cpu_seconds', 'peak_rss_kib', 'status', 'operations'}, 'game metrics')
        require((metric['kind'], metric['pass'], metric['seed'], metric['status']) == ('game', p, seed, 'complete'),
                'game metric order/status')
        schema_object(metric['operations'], set(bounded.OPS), 'game physical operations')
        for key in bounded.OPS:
            integer(metric['operations'][key], 'game.' + key, game_decisions[key])
            games[key] += metric['operations'][key]
        for key in ('wall_seconds', 'cpu_seconds'):
            require(type(metric[key]) in (int, float) and metric[key] >= 0, 'invalid game elapsed')
        integer(metric['peak_rss_kib'], 'peak RSS', 0, FREEZE['resources']['address_space_bytes'] // 1024)
    require(next(metrics, None) is None, 'extra resource metric rows')
    schema_object(receipt['total_operations'], set(bounded.OPS), 'total physical operations')
    require(exact_json(games, receipt['total_operations']), 'game/whole physical operation mismatch')
    for key in bounded.OPS:
        integer(receipt['total_operations'][key], 'total.' + key, decisions[key], FREEZE['resources']['total_operations'][key])
    require(type(receipt['cohort_elapsed_seconds']) in (int, float)
            and 0 <= receipt['cohort_elapsed_seconds'] <= FREEZE['resources']['cohort_wall_seconds'], 'cohort elapsed limit')


def finalize(output, expected_head, preregistration_url, test_outcome, cohort_outcome):
    global BUDGET
    started = time.monotonic()
    BUDGET = bounded.EvidenceBudget(output, FREEZE['resources'])
    try:
        bounded.enforce_memory(FREEZE['resources']['address_space_bytes'])
        with bounded.deadline(FREEZE['resources']['verification_wall_seconds'], 'evidence reconciliation'):
            result = _finalize(output, expected_head, preregistration_url, test_outcome, cohort_outcome)
        receipt = read_receipt(output)
        receipt['verification_elapsed_seconds'] = time.monotonic() - started
        if receipt['verification_elapsed_seconds'] > FREEZE['resources']['verification_wall_seconds']:
            raise bounded.ResourceExceeded('verification elapsed exceeds freeze')
        write_json(output / 'receipt.json', receipt)
        return result
    except Exception as error:
        try:
            receipt = read_receipt(output)
            receipt['verification_elapsed_seconds'] = time.monotonic() - started
            fail(receipt, error, 'verification_supervision')
            write_json(output / 'receipt.json', receipt)
        except Exception as receipt_error:
            recovery_receipt(output, expected_head, preregistration_url, test_outcome, cohort_outcome, receipt_error)
        return 1


def claim_admission(output, expected_head, go):
    """One durable first attempt per exact head inside the repository's area."""
    root = output.parent.parent / '.admitted-heads'
    root.mkdir(parents=True, exist_ok=True)
    guard = root / expected_head
    require(not root.is_symlink(), 'symlinked admission area')
    guard.mkdir(exist_ok=False)
    value = {'schema': 'worker35-exclusive-admission-v1', **identity(expected_head, PREREGISTRATION_URL), 'execution_go': go}
    write_json(guard / 'admission.json', value)
    return value


def load_configuration(path):
    global FREEZE, FREEZE_SHA256
    FREEZE, FREEZE_SHA256 = bounded.read_freeze(path)
    require(FREEZE['preregistration_url'] == PREREGISTRATION_URL and FREEZE['baseline_commit'] == BASELINE_COMMIT,
            'freeze changed preregistration or canonical comparator')


def quarantine_receipt(output, expected_head, preregistration_url, go, error, phase):
    """Add a failure sidecar; never repair, parse again or overwrite bad bytes."""
    output.mkdir(parents=True, exist_ok=True)
    original = output / 'receipt.json'
    identity_bytes = None
    if original.is_file() and not original.is_symlink():
        identity_bytes = bounded.file_hash(original)
    limited = isinstance(error, (bounded.ResourceExceeded, MemoryError, TimeoutError))
    value = {'schema': 'worker35-quarantined-recovery-v1', **identity(expected_head, preregistration_url),
        'execution_go': go, 'quarantined': True,
        'status': 'resource_incomplete' if limited else 'integrity_invalid' if integrity_error(error) else 'execution_blocked',
        'classification': None, 'research_interpretation_performed': False,
        'original_receipt': identity_bytes,
        'errors': [{'phase': phase, 'type': type(error).__name__, 'message': str(error)}]}
    descriptor, name = tempfile.mkstemp(prefix='recovery-receipt-quarantined-', suffix='.json', dir=output)
    os.close(descriptor)
    write_json(Path(name), value)


def package_attempt(output, expected_head, preregistration_url, go):
    """Transport is evidence preservation, never an acceptance/receipt gate.

    Caller has already validated frozen caps, exact event admission and bounded
    attempt path. A damaged receipt is quarantined but cannot hide its raw tree.
    """
    receipt, quarantined = None, False
    try:
        receipt = read_receipt(output)
        check_identity(receipt, expected_head, preregistration_url)
    except Exception as error:
        quarantined = True
        try:
            quarantine_receipt(output, expected_head, preregistration_url, go, error, 'receipt_before_packaging')
        except Exception as recovery_error:
            # Even an unavailable/full recovery reserve cannot hide already
            # existing raw bytes. The package and workflow still fail closed.
            print('QUARANTINED: recovery sidecar unavailable: ' + str(recovery_error), file=sys.stderr)
    try:
        with bounded.deadline(FREEZE['resources']['verification_wall_seconds'], 'evidence packaging'):
            bounded.package_evidence(output, output.with_name(output.name + '-transport'), FREEZE['resources'])
        return 1 if quarantined else 0
    except Exception as error:
        if quarantined:
            try:
                quarantine_receipt(output, expected_head, preregistration_url, go, error, 'quarantined_packaging')
            except Exception as recovery_error:
                print('QUARANTINED: packaging/recovery failure: ' + str(recovery_error), file=sys.stderr)
        else:
            fail(receipt, error, 'packaging')
            write_json(output / 'receipt.json', receipt)
        return 1
    finally:
        transport = output.with_name(output.name + '-transport')
        parts = [p.name for p in sorted(transport.glob('evidence.part-*'))]
        require(len(parts) <= 256, 'transport shard population exceeds256')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                stream.write('parts=' + json.dumps(parts, separators=(',', ':')) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('admit', 'initialize', 'run', 'finalize', 'package'))
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--preregistration-url', required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--test-outcome', default='unknown')
    parser.add_argument('--cohort-outcome', default='unknown')
    args = parser.parse_args(argv)
    try:
        # Ordinary PR edits do not need a freeze, receipt or admission directory.
        event = bounded.strict_json(Path(os.environ['GITHUB_EVENT_PATH']).read_bytes())
        if args.mode == 'admit':
            body = event.get('pull_request', {}).get('body') or ''
            old = event.get('changes', {}).get('body', {}).get('from')
            if event.get('action') != 'edited' or MARKER not in body or type(old) is not str or MARKER in old:
                with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                    output.write('admitted=false\n')
                return 0
        load_configuration(args.freeze)
        args.output_dir = safe_output_path(args.output_dir, actions=True)
        go = admission(event, args.expected_head, FREEZE_SHA256)
        require(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('RUNNER_NAME') == 'bandido-alcatraz-ci'
                and os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_RUN_ATTEMPT') == '1'
                and os.environ.get('GITHUB_EVENT_NAME') == 'pull_request', 'unauthorized Actions execution context')
        require(args.preregistration_url == PREREGISTRATION_URL, 'wrong preregistration')
        if args.mode == 'admit':
            # Source verification follows the initial durable receipt so even a
            # rejected source gate leaves an explicit pre-compute failure record.
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('admitted=true\n')
            return 0
        if args.mode == 'initialize':
            admitted = claim_admission(args.output_dir, args.expected_head, go)
            receipt = initialize(args.output_dir, args.expected_head, args.preregistration_url)
            receipt['admission'] = admitted
            receipt['execution_go'] = go
            try:
                receipt['source_at_initialization'] = verify_source(args.expected_head)
                require(receipt['source_at_initialization']['tree'] == go['tree'], 'execution tree mismatch')
            except Exception as error:
                fail(receipt, error, 'source_at_initialization')
                receipt['observed_source_at_failed_initialization'] = observed_source_snapshot()
                write_json(args.output_dir / 'receipt.json', receipt)
                return 1
            write_json(args.output_dir / 'receipt.json', receipt)
            return 0
        if args.mode == 'run':
            return run(args.output_dir, args.expected_head, args.preregistration_url)
        if args.mode == 'finalize':
            return finalize(args.output_dir, args.expected_head, args.preregistration_url,
                            args.test_outcome, args.cohort_outcome)
        return package_attempt(args.output_dir, args.expected_head, args.preregistration_url, go)
    except Exception as error:
        # Gate/reuse failures must never overwrite the original attempt receipt.
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
