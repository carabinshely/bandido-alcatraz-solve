"""Fixed fresh-development shards. No shard-level performance interpretation."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from scripts import run_worker26 as common

ROOT = Path(__file__).resolve().parents[1]
STARTING_MAIN = "9324d15aec6e17f4b29c947fb0d846fe948b7fa1"
PREREGISTRATION = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5914705341"
FIRST = 1_000_000
COUNT = 400
SHARD_SIZE = 100

def shard_seeds(shard):
    common.require(type(shard) is int and 0 <= shard < 4, "invalid frozen shard")
    return list(range(FIRST + shard * SHARD_SIZE, FIRST + (shard + 1) * SHARD_SIZE))

def preflight():
    head = common.git("rev-parse", "HEAD")
    common.require(head == os.environ.get("EVALUATED_COMMIT"), "execution head mismatch")
    common.require(os.environ.get("RUNNER_NAME") == "bandido-alcatraz-ci", "unauthorized research executor")
    check_ancestry()
    manifest = json.loads(common.git("show", STARTING_MAIN + ":experiments/real-deck-policy-v7/immediate-tie-development-2026-09-30.manifest.json"))
    source_blobs = manifest["fixed_configuration"]["canonical_source_blobs"]
    for path, blob in source_blobs.items():
        common.require(common.git("hash-object", path) == blob, "canonical source mismatch: " + path)
    for path in ("scripts/run_worker26.py", "scripts/run_worker27.py", "experiments/seed-ledger.json"):
        common.require(common.git("hash-object", path) == common.git("rev-parse", "HEAD:" + path), "dirty input: " + path)
    candidate_blob = common.git("hash-object", "scripts/run_worker26.py")
    common.require(candidate_blob == common.git("rev-parse", STARTING_MAIN + ":scripts/run_worker26.py"), "candidate changed from accepted Worker26")
    ledger = json.loads((ROOT / "experiments/seed-ledger.json").read_text())
    allocations = [a for a in ledger["allocations"] if a["research_step"] == 27]
    common.require(len(allocations) == 1 and allocations[0]["range_inclusive"] == [FIRST, FIRST + COUNT - 1], "ledger allocation")
    common.require(allocations[0]["role"] == "fresh development; never confirmation" and allocations[0]["confirmation_eligible"] is False, "ledger role")
    raw_reference = (ROOT / common.REFERENCE).read_bytes()
    reference = json.loads(raw_reference)
    common.require(reference["seed_range"] == [1000,1099], "baseline reference range")
    rows = reference["v4_per_seed"]
    common.require([r["seed"] for r in rows] == list(common.SEEDS), "baseline reference ordered population")
    return rows, {"head": head, "canonical_source_blobs": source_blobs,
        "reference_sha256": hashlib.sha256(raw_reference).hexdigest(), "candidate_blob": candidate_blob,
        "worker27_harness_blob": common.git("hash-object", "scripts/run_worker27.py"),
        "worker27_harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ledger_blob": common.git("hash-object", "experiments/seed-ledger.json")}

def check_ancestry():
    result = subprocess.run(["git", "merge-base", "--is-ancestor", STARTING_MAIN, "HEAD"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode not in (0,1):
        raise common.InfrastructureError(f"Git ancestry check unavailable: code={result.returncode}; {result.stderr}")
    common.require(result.returncode == 0, "Worker27 base is not an ancestor")

def pair(task):
    seed, folder = task
    common.require(type(seed) is int and FIRST <= seed < FIRST + COUNT, "out-of-scope fresh seed")
    path = Path(folder) / f"{seed}.json"
    result = {"seed": seed, "status": "running", "v4": None, "v7": None,
              "research_interpretation_performed": False}
    common.write_json(path, result)
    try:
        for name in ("v4", "v7"):
            deck = common.load_real_deck(ROOT / "data")
            policy = common.BoundedMergeV4Policy(setup_weight=250) if name == "v4" else common.ImmediateTieV7Policy()
            played = common.play_game(start_card=deck.start_easy, deck=deck.draw_deck(), hand_size=3, policy=policy, seed=seed)
            result[name] = common.final_record(seed, played)
            common.write_json(path, result)
            common.require(played.reason != "step_limit", f"step limit {name}/{seed}")
        result["status"] = "complete"
    except OSError as exc:
        result.update(status="execution_blocked", error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:
        result.update(status="diagnostic_invalid", error=f"{type(exc).__name__}: {exc}")
    common.write_json(path, result)
    return result

def run_shard(seeds, output, receipt, save):
    pairs = output / "pairs"
    pairs.mkdir(exist_ok=False)
    with (output / "completed.jsonl").open("x") as journal:
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures, failures = {}, []
            for seed in seeds:
                receipt["submission_attempted_seeds"].append(seed); save()
                try:
                    future = pool.submit(pair, (seed, str(pairs)))
                except Exception as exc:
                    failures.append({"seed": seed, "kind": "infrastructure", "error": f"{type(exc).__name__}: {exc}"})
                    break
                futures[future] = seed
                receipt["submitted_seeds"].append(seed); save()
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception as exc:
                    failures.append({"seed": futures[future], "kind": "infrastructure" if isinstance(exc, (OSError, BrokenProcessPool)) else "integrity", "error": f"{type(exc).__name__}: {exc}"})
                else:
                    common.require(row["seed"] == futures[future], "worker returned wrong seed")
                    receipt["pairs"].append(row)
                    journal.write(json.dumps(row, sort_keys=True) + "\n"); journal.flush(); os.fsync(journal.fileno())
                    if row["status"] != "complete":
                        failures.append({"seed": row["seed"], "kind": "infrastructure" if row["status"] == "execution_blocked" else "integrity", "error": row.get("error")})
                receipt["failures"] = failures; save()
            if failures:
                if any(f["kind"] == "integrity" for f in failures): raise common.IntegrityError("shard integrity failure; no interpretation")
                raise common.InfrastructureError("shard infrastructure failure; no interpretation")
    receipt["pairs"].sort(key=lambda row: row["seed"])
    common.require([p["seed"] for p in receipt["pairs"]] == seeds, "incomplete/wrong shard population")

def finalize(output, cohort_outcome, tests_outcome):
    output.mkdir(parents=True, exist_ok=True)
    path = output / "receipt.json"
    r = json.loads(path.read_text()) if path.exists() else {"schema": "bandido-worker27-v1", "pairs": [], "baseline": [], "submission_attempted_seeds": [], "submitted_seeds": [], "preregistration_url": PREREGISTRATION}
    if r.get("status") == "complete" and cohort_outcome == tests_outcome == "success": return
    invalid = tests_outcome == "failure" or r.get("status") == "diagnostic_invalid"
    r.update(status="diagnostic_invalid" if invalid else "execution_blocked", classification="worker27_invalid" if invalid else None,
        research_interpretation_performed=False, finalizer_outcomes={"cohort": cohort_outcome, "tests": tests_outcome},
        partial_evidence_note="Inspect pair sidecars and submission lists; unfinished submitted work may have executed")
    r.pop("summary", None)
    common.write_json(path, r)

def main():
    ap = argparse.ArgumentParser()
    modes = ap.add_mutually_exclusive_group(required=True)
    modes.add_argument("--baseline", action="store_true")
    modes.add_argument("--shard", type=int, choices=range(4))
    modes.add_argument("--finalize", action="store_true")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--cohort-outcome", default="unknown")
    ap.add_argument("--tests-outcome", default="unknown")
    args = ap.parse_args()
    if args.finalize:
        finalize(args.output, args.cohort_outcome, args.tests_outcome); return 0
    args.output.mkdir(parents=True, exist_ok=True)
    previous = common.preserve_previous_attempt(args.output)
    if (args.output / "pairs").exists():
        common.require(previous is not None, "orphan pair directory; preserve/reconcile before retry")
        (args.output / "pairs").rename(args.output / previous / "pairs")
    seeds = list(common.SEEDS) if args.baseline else shard_seeds(args.shard)
    r = {"schema": "bandido-worker27-v1", "preregistration_url": PREREGISTRATION,
         "starting_main": STARTING_MAIN, "head": os.environ.get("EVALUATED_COMMIT"),
         "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
         "runner": os.environ.get("RUNNER_NAME"), "python": os.sys.version,
         "mode": "baseline" if args.baseline else "fresh_development_shard", "shard": args.shard,
         "seeds": seeds, "status": "preflight", "classification": None,
         "research_interpretation_performed": False, "pairs": [], "baseline": [],
         "submission_attempted_seeds": [], "submitted_seeds": [], "preserved_previous_attempt": previous}
    started = time.monotonic()
    def save():
        r["elapsed_seconds"] = time.monotonic() - started
        common.write_json(args.output / "receipt.json", r)
    save()
    try:
        expected, provenance = preflight(); r["provenance"] = provenance; r["status"] = "running"; save()
        if args.baseline:
            for seed, accepted in zip(common.SEEDS, expected):
                r["submission_attempted_seeds"].append(seed); save()
                row = common.one_game(("v4", seed)); r["baseline"].append(row); save()
                common.require(row == accepted, f"baseline replay mismatch {seed}")
            common.require(len(r["baseline"]) == 100, "incomplete baseline")
            r["baseline_gate"] = "100/100 exact"
        else:
            run_shard(seeds, args.output, r, save)
        _, after = preflight(); common.require(after == provenance, "source changed during execution")
        r["status"] = "complete"; save(); return 0
    except (OSError, subprocess.CalledProcessError, common.InfrastructureError) as exc:
        r.update(status="execution_blocked", error=f"{type(exc).__name__}: {exc}", classification=None)
    except Exception as exc:
        r.update(status="diagnostic_invalid", error=f"{type(exc).__name__}: {exc}", classification="worker27_invalid")
    r["research_interpretation_performed"] = False; save(); return 1

if __name__ == "__main__": raise SystemExit(main())
