"""Verify the frozen Worker27 raw bundle and summarize all 400 pairs, never a subset."""
from __future__ import annotations
import argparse
from hashlib import sha256
import io
import json
from math import sqrt
from pathlib import Path
import zipfile

HEAD = "f99f1808de7133c31ddba53dba4a66d73f386dc8"
BASE = "9324d15aec6e17f4b29c947fb0d846fe948b7fa1"
RUN = "36740756141"
SEEDS = list(range(1000000,1000400))
ARCHIVES = {
 "baseline": "f2ef3154a831a945e1b5cfe4a5de8bdaf3a8571e334167b4376d291fe28d05f3",
 "shard-0": "9aff9b380028f61cf9a5ef63b884d882b60053fcde1f011c964931079527ec16",
 "shard-1": "851ac14710cfc2a343e7e66938c5c929d089aba9ded4a65db7ee675fb20749f6",
 "shard-2": "46014fc71898e6ebfa873aafbbc232e693975b2dc00f51882bd84cf9ee669b2b",
 "shard-3": "9cfe2c6b7e7a11cb2dcf1a4a29fb0ef6c00a89f49b411b0dd36f9be53e496c1e",
}

def require(value, message):
    if not value: raise ValueError(message)

def validate_record(record, seed):
    require(type(record.get("seed")) is int and record["seed"] == seed, "record seed")
    for key in ("won","exit_placed","equipment_ready","exit_equipment_water_ready"):
        require(type(record.get(key)) is bool, "boolean field: " + key)
    for key in ("turns","final_open_tunnels","visible_water","raincoats","ropes"):
        require(type(record.get(key)) is int and record[key] >= 0, "nonnegative integer: " + key)
    require(record["reason"] in ("win","deck_exhausted","no_legal_move","closed_tunnels_conditions_failed"), "terminal reason")
    ready = record["raincoats"] >= 3 and record["ropes"] >= 2
    require(record["equipment_ready"] == ready, "equipment consistency")
    exit_ready = record["exit_placed"] and ready and record["visible_water"] == 0
    require(record["exit_equipment_water_ready"] == exit_ready, "exit readiness")
    require(record["won"] == (record["reason"] == "win") == (exit_ready and record["final_open_tunnels"] == 0), "victory consistency")

def summarize(pairs):
    require(len(pairs) == 400, "incomplete400population")
    rows = sorted(pairs, key=lambda p:p["seed"])
    require([p["seed"] for p in rows] == SEEDS, "wrong/duplicate seed population")
    for row in rows:
        require(row["status"] == "complete" and row["research_interpretation_performed"] is False, "pair status")
        for policy in ("v4","v7"): validate_record(row[policy],row["seed"])
    a={p["seed"] for p in rows if p["v4"]["won"]};b={p["seed"] for p in rows if p["v7"]["won"]}
    def interval(wins):
        n=400;p=wins/n;z=1.959963984540054;den=1+z*z/n
        center=(p+z*z/(2*n))/den;half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/den
        return {"wins":wins,"games":n,"rate":p,"wilson95":[center-half,center+half],"interpretation":"development only; non-confirmatory"}
    advance=len(b)-len(a)>=8
    return {"schema":"worker27-aggregate-v1","evaluated_commit":HEAD,"seed_range_inclusive":[1000000,1000399],
        "paired_games":400,"v4":interval(len(a)),"v7":interval(len(b)),"gained":sorted(b-a),"lost":sorted(a-b),
        "both_win":sorted(a&b),"both_lose":400-len(a|b),"net_wins":len(b)-len(a),"advancement_threshold_net_wins":8,
        "advance":advance,"classification":"v7_fresh_development_signal" if advance else "v7_fresh_development_no_advancement",
        "interpretation":"Fixed development gate only; no pooled or confirmatory inference"}

def verify_bundle(path, reference_path):
    reference_bytes=Path(reference_path).read_bytes();reference=json.loads(reference_bytes)
    pairs=[];provenance=None
    with zipfile.ZipFile(path) as bundle:
        for label,digest in ARCHIVES.items():
            raw=bundle.read("artifacts/"+label+".zip")
            require(sha256(raw).hexdigest()==digest,"archive hash: "+label)
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                receipt=json.loads(z.read("receipt.json"))
                require(receipt["schema"]=="bandido-worker27-v1" and receipt["status"]=="complete","receipt status/schema")
                require(receipt["head"]==HEAD and receipt["starting_main"]==BASE and receipt["run_id"]==RUN and receipt["run_attempt"]=="1","execution identity")
                require(receipt["runner"]=="bandido-alcatraz-ci" and receipt["classification"] is None and receipt["research_interpretation_performed"] is False,"uninterpreted successful run")
                if provenance is None: provenance=receipt["provenance"]
                require(receipt["provenance"]==provenance,"cross-shard source mismatch")
                require(sha256(reference_bytes).hexdigest()==provenance["reference_sha256"],"reference hash")
                if label=="baseline":
                    require(receipt["mode"]=="baseline" and receipt["seeds"]==list(range(1000,1100)),"baseline scope")
                    require(receipt["baseline"]==reference["v4_per_seed"] and receipt["baseline_gate"]=="100/100 exact","baseline replay")
                    continue
                shard=int(label[-1]);seeds=list(range(1000000+100*shard,1000100+100*shard))
                require(receipt["mode"]=="fresh_development_shard" and receipt["shard"]==shard,"shard identity")
                require(receipt["seeds"]==receipt["submitted_seeds"]==receipt["submission_attempted_seeds"]==seeds,"submitted population")
                require(not receipt.get("failures"),"shard failures")
                rows=receipt["pairs"];require([p["seed"] for p in rows]==seeds,"complete shard")
                journal=[json.loads(line) for line in z.read("completed.jsonl").decode().splitlines()]
                require(len(journal)==100 and sorted(journal,key=lambda p:p["seed"])==rows,"journal matches")
                for row in rows: require(json.loads(z.read(f"pairs/{row['seed']}.json"))==row,"pair sidecar matches")
                pairs.extend(rows)
    return summarize(pairs)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("bundle",type=Path);ap.add_argument("--reference",type=Path,default=Path(__file__).resolve().parents[1]/"experiments/real-deck-policy-v6/current-model-spent-development-1000-1099-2026-09-28.json");ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    result=verify_bundle(args.bundle,args.reference)
    tmp=args.output.with_suffix(args.output.suffix+".tmp");tmp.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n");tmp.replace(args.output)

if __name__=="__main__":main()
