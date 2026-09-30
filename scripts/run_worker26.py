"""Frozen spent-development comparison; research runs only on bandido-alcatraz-ci."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import asdict
import hashlib
import json
from math import sqrt
import os
from pathlib import Path
import subprocess
import time

from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.simulate import play_game
from bandido_alcatraz.strategy import best_two_action_first_moves, score_move_no_draw

ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(1000, 1100))
STARTING_MAIN = "c0a45313dba3b4076a529cce13a94a0e19aeb209"
PREREGISTRATION = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5912894282"
REFERENCE = "experiments/real-deck-policy-v6/current-model-spent-development-1000-1099-2026-09-28.json"
MANIFEST25 = "experiments/real-deck-policy-v6/full-spent-tier-footprint-2026-09-30.manifest.json"

class IntegrityError(ValueError):
    pass

class InfrastructureError(RuntimeError):
    pass

class ImmediateTieV7Policy(BoundedMergeV4Policy):
    """Keep V6's maximum sequence utility; break ties by immediate V4 reward."""
    def __init__(self):
        super().__init__(setup_weight=250)

    def choose(self, state, rng):
        candidates = best_two_action_first_moves(state, self.weights)
        if not candidates:
            return None
        scored = [(score_move_no_draw(state, move, self.weights), move) for move in candidates]
        best = max(score for score, _ in scored)
        return rng.choice([move for score, move in scored if score == best])

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def require(condition, message):
    if not condition:
        raise IntegrityError(message)

def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temp.replace(path)

def preserve_previous_attempt(output):
    previous = [output / name for name in ("receipt.json", "receipt.json.tmp", "completed.jsonl")
                if (output / name).exists()]
    if not previous:
        return None
    destination = output / "previous-attempts" / str(time.time_ns())
    destination.mkdir(parents=True, exist_ok=False)
    for path in previous:
        path.rename(destination / path.name)
    return str(destination.relative_to(output))

def verify_harness_binding():
    path = str(Path(__file__).resolve().relative_to(ROOT))
    actual = git("hash-object", path)
    require(actual == git("rev-parse", f"HEAD:{path}"), "harness differs from evaluated commit")
    return actual

def finalize(output, outcome, tests_outcome):
    """Persist an explicit terminal blocker when timeout interrupted the producer."""
    output.mkdir(parents=True, exist_ok=True)
    path = output / "receipt.json"
    receipt = json.loads(path.read_text()) if path.exists() else {
        "schema": "bandido-worker26-v1", "preregistration_url": PREREGISTRATION,
        "starting_main": STARTING_MAIN, "claimed_execution_head": os.environ.get("EVALUATED_COMMIT"),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "completed_policy_seed_records": 0, "submitted_candidate_seeds": [],
        "submission_attempted_seeds": [], "v4": [], "v7": []}
    if receipt.get("status") in ("complete", "diagnostic_invalid", "execution_blocked"):
        return
    invalid = tests_outcome == "failure"
    receipt.update(status="diagnostic_invalid" if invalid else "execution_blocked",
                   classification="worker26_invalid" if invalid else None,
                   research_interpretation_performed=False,
                   error=f"No complete terminal receipt; cohort step={outcome}; synthetic tests={tests_outcome}",
                   executed_count_note="Completed records only; interrupted/submitted work may have started")
    write_json(path, receipt)

def preflight():
    head = git("rev-parse", "HEAD")
    require(head == os.environ.get("EVALUATED_COMMIT"), "checkout differs from frozen execution head")
    require(os.environ.get("RUNNER_NAME") == "bandido-alcatraz-ci", "unauthorized research executor")
    harness_blob = verify_harness_binding()
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", STARTING_MAIN, head], cwd=ROOT)
    require(ancestry.returncode == 0, "frozen starting main is not an ancestor")
    # Read the authority from the pinned base, not an editable branch manifest.
    base_manifest = json.loads(git("show", f"{STARTING_MAIN}:{MANIFEST25}"))
    expected = base_manifest["source_integrity"]["source_blobs"]
    for path, blob in expected.items():
        require(git("hash-object", path) == blob, f"source/data hash mismatch: {path}")
    reference_bytes = (ROOT / REFERENCE).read_bytes()
    reference = json.loads(reference_bytes)
    require(reference["seed_range"] == [1000, 1099], "reference population range")
    rows = reference["v4_per_seed"]
    require([r["seed"] for r in rows] == list(SEEDS), "reference exact ordered population")
    require(len({r["seed"] for r in rows}) == 100, "reference duplicate seeds")
    return rows, {"head": head, "starting_main": STARTING_MAIN,
                  "harness_blob": harness_blob,
                  "source_blobs": expected,
                  "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
                  "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

def final_record(seed, result):
    ready = is_equipment_ready(result.raincoats, result.ropes)
    return {"seed": seed, "won": result.won, "reason": result.reason,
            "turns": result.turns, "final_open_tunnels": result.open_tunnels,
            "visible_water": result.visible_water_cells, "raincoats": result.raincoats,
            "ropes": result.ropes, "exit_placed": result.exit_placed,
            "equipment_ready": ready,
            "exit_equipment_water_ready": result.exit_placed and ready and result.visible_water_cells == 0}

def one_game(task):
    policy_name, seed = task
    require(seed in SEEDS, "out-of-scope seed")
    require(policy_name in ("v4", "v7"), "unknown policy")
    deck = load_real_deck(ROOT / "data")
    policy = BoundedMergeV4Policy(setup_weight=250) if policy_name == "v4" else ImmediateTieV7Policy()
    result = play_game(start_card=deck.start_easy, deck=deck.draw_deck(), hand_size=3,
                       policy=policy, seed=seed)
    row = final_record(seed, result)
    require(row["reason"] != "step_limit", f"step limit: {policy_name}/{seed}")
    return row

def summarize(v4, v7):
    for rows in (v4, v7):
        require([r["seed"] for r in rows] == list(SEEDS), "incomplete/wrong outcome population")
    gained = [a["seed"] for a, b in zip(v4, v7) if b["won"] and not a["won"]]
    lost = [a["seed"] for a, b in zip(v4, v7) if a["won"] and not b["won"]]
    both = [a["seed"] for a, b in zip(v4, v7) if a["won"] and b["won"]]
    net = len(gained) - len(lost)
    def descriptive_interval(rows):
        n = len(rows); p = sum(r["won"] for r in rows) / n; z = 1.959963984540054
        center = (p + z*z/(2*n)) / (1 + z*z/n)
        half = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
        return {"rate": p, "wilson95": [center-half, center+half],
                "interpretation": "descriptive on spent development; not confirmatory"}
    return {"v4_wins": sum(r["won"] for r in v4), "v7_wins": sum(r["won"] for r in v7),
            "v4_descriptive_rate": descriptive_interval(v4), "v7_descriptive_rate": descriptive_interval(v7),
            "gained": gained, "lost": lost, "both_win": both, "both_lose": 100-len(gained)-len(lost)-len(both),
            "net_wins": net, "advance": net >= 2,
            "classification": "v7_immediate_tie_development_signal" if net >= 2 else "v7_immediate_tie_no_advancement"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--finalize", action="store_true")
    ap.add_argument("--step-outcome", default="unknown")
    ap.add_argument("--tests-outcome", default="unknown")
    ap.add_argument("--output", type=Path, default=ROOT / "worker26-output")
    args = ap.parse_args()
    if args.finalize:
        finalize(args.output, args.step_outcome, args.tests_outcome)
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    previous_attempt = preserve_previous_attempt(args.output)
    receipt = {"schema": "bandido-worker26-v1", "status": "preflight",
               "preserved_previous_attempt": previous_attempt,
               "preregistration_url": PREREGISTRATION,
               "fixed_configuration": {"rules": "v0-threshold-equipment", "hand_size": 3,
                   "start": "easy", "baseline": "BoundedMergeV4Policy(setup_weight=250)",
                   "candidate": "lexmax(V6_sequence_score, immediate_V4_250_score)",
                   "candidate_workers": 4, "advance_if_net_wins_at_least": 2},
               "classification": None, "research_interpretation_performed": False,
               "dataset_status": "spent development; non-confirmatory", "seeds": list(SEEDS),
               "completed_policy_seed_records": 0, "submitted_candidate_seeds": [],
               "submission_attempted_seeds": [], "v4": [], "v7": [],
               "starting_main": STARTING_MAIN, "run_id": os.environ.get("GITHUB_RUN_ID"),
               "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "runner": os.environ.get("RUNNER_NAME"), "python": os.sys.version,
               "claimed_execution_head": os.environ.get("EVALUATED_COMMIT")}
    start = time.monotonic()
    def save():
        receipt["elapsed_seconds"] = time.monotonic() - start
        write_json(args.output / "receipt.json", receipt)
    save()
    try:
        expected, provenance = preflight()
        receipt["provenance"] = provenance
        if not args.execute:
            receipt["status"] = "preflight_pass_zero_seeds"
            save()
            return 0
        receipt["status"] = "running"
        save()
        with (args.output / "completed.jsonl").open("x") as journal:
            def retain(policy, row):
                receipt[policy].append(row)
                receipt["completed_policy_seed_records"] += 1
                journal.write(json.dumps({"policy": policy, "record": row}, sort_keys=True) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
                save()
            for seed, accepted in zip(SEEDS, expected):
                row = one_game(("v4", seed))
                retain("v4", row)
                require(row == accepted, f"V4 accepted replay mismatch at seed {seed}")
            receipt["baseline_gate"] = "100/100 exact"
            save()
            with ProcessPoolExecutor(max_workers=4) as pool:
                futures = {}
                failures = []
                for seed in SEEDS:
                    receipt["submission_attempted_seeds"].append(seed)
                    save()
                    try:
                        future = pool.submit(one_game, ("v7", seed))
                    except Exception as exc:
                        failures.append({"seed": seed, "stage": "submission", "kind": "infrastructure",
                                         "error": f"{type(exc).__name__}: {exc}"})
                        receipt["candidate_failures"] = failures
                        save()
                        break
                    futures[future] = seed
                    receipt["submitted_candidate_seeds"].append(seed)
                    save()
                for future in as_completed(futures):
                    try:
                        row = future.result()
                    except Exception as exc:
                        kind = "infrastructure" if isinstance(exc, (OSError, BrokenProcessPool)) else "integrity"
                        failures.append({"seed": futures[future], "stage": "result", "kind": kind,
                                         "error": f"{type(exc).__name__}: {exc}"})
                        receipt["candidate_failures"] = failures
                        save()
                    else:
                        retain("v7", row)
                if failures:
                    if any(f["kind"] == "integrity" for f in failures):
                        raise IntegrityError("candidate integrity failures; see recorded failure categories")
                    raise InfrastructureError("candidate infrastructure failures; no subset interpretation")
            receipt["v7"].sort(key=lambda row: row["seed"])
        # Recheck source integrity after execution, before interpreting any outcomes.
        _, after = preflight()
        require(after == provenance, "source/provenance changed during execution")
        summary = summarize(receipt["v4"], receipt["v7"])
        receipt.update(status="complete", summary=summary, classification=summary["classification"],
                       research_interpretation_performed=True)
        save()
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, subprocess.CalledProcessError, InfrastructureError) as exc:
        receipt.update(status="execution_blocked", error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:
        receipt.update(status="diagnostic_invalid", classification="worker26_invalid",
                       error=f"{type(exc).__name__}: {exc}")
    save()
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
