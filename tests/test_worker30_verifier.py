"""Synthetic evidence only: no harness/engine imports and no games."""
import ast
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import stat
import zipfile

import pytest

from scripts import verify_worker30_baseline as v

SYNTHETIC_PINS = {"RUN_ID": 987654321,
                  "HEAD": hashlib.sha1(b"synthetic Worker30 execution head").hexdigest(),
                  "HARNESS_BLOB": hashlib.sha1(b"synthetic Worker30 harness blob").hexdigest(),
                  "HARNESS_SHA256": hashlib.sha256(b"synthetic Worker30 harness").hexdigest()}

# Independently pinned accepted-tree map; tests need only repository data files.
ACCEPTED_SOURCE_BLOBS = {
    "data/README.md": "2ac91d9da6769934c78a90ba865f3d558f48bbd2",
    "data/deck-observations-v0.json": "ee38d60277c79dafa7527876367e3e6450ccb53f",
    "data/deck-v1.json": "9fa2066507ff9a0fb6b922d52e84529b35acb05e",
    "data/owner-photo-inventory-v0.json": "5911fdeea4138421945d0cffd69908088cad5639",
    "data/proxy-bandido-covid-v0.json": "a9e3013f58a94216e920637461331e3c8fccdeae",
    "src/bandido_alcatraz/__init__.py": "425141547c12e61eee6ecafd5b7136322f0af6d4",
    "src/bandido_alcatraz/board.py": "e04e9255ecc9c8181ca49903dfb6501a67c8a482",
    "src/bandido_alcatraz/catalog.py": "e82ca3d70310281bf5a6c4f325e10f0083d7b0b3",
    "src/bandido_alcatraz/deck_data.py": "6e997e464736bcd0ad79f6115ff69f3967cd57f5",
    "src/bandido_alcatraz/evaluate.py": "49cc2da9e651dfc58f4911801b8b923da90c05b4",
    "src/bandido_alcatraz/export_svg.py": "ab39daf4df714cc8dfe5a1244e8345f8abafbdb2",
    "src/bandido_alcatraz/fixtures.py": "a12d395871a6a5e2d1c2011c5ac628878a2d5dde",
    "src/bandido_alcatraz/game.py": "8df56288eded0ae96c57314589a9707b4a056054",
    "src/bandido_alcatraz/model.py": "dc469a82a5fab7574aebe25a18543494494f4b11",
    "src/bandido_alcatraz/moves.py": "e605897b6c0c5539d51270b9371df9cc1dfe1a1e",
    "src/bandido_alcatraz/optimize.py": "53e9f2f0265d1e5ee542413a842caedbd67cd110",
    "src/bandido_alcatraz/photo_geometry.py": "eb40808af9616b2d77c3e6519e010021992d364a",
    "src/bandido_alcatraz/physical_deck.py": "87601a25bf16f181753f71b2c84dc3c0fa6fe418",
    "src/bandido_alcatraz/policies.py": "3218817fe43cd901e5fc3de0d62c651dc5059dd5",
    "src/bandido_alcatraz/proxy.py": "7c590565591d558e1d18d38a8471abd02bcac156",
    "src/bandido_alcatraz/proxy_data.py": "c0d63b6d0de90626600cb0d1ca5fa6917c7908f4",
    "src/bandido_alcatraz/render_svg.py": "2951661e5b12bb85de04c563078bfd405fbef924",
    "src/bandido_alcatraz/rules.py": "d0fffb7b37f531e149a0d7e17800e2ac708e9890",
    "src/bandido_alcatraz/setup.py": "b055fe799a60e499af1fbd86275d3b7e61f2b656",
    "src/bandido_alcatraz/simulate.py": "7637bed25e3d380ff0928927b8bb97abd9a2af56",
    "src/bandido_alcatraz/strategy.py": "57c7d173c9f173690d6c27cf546da2576cd35510"
}


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha_size(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def cell(x, y, edges, water=False):
    return {"x": x, "y": y, "tunnel_edges": sorted(edges), "water": water}


def placement(card_id, index=0, origin=None):
    x, y = origin or (0, 0)
    return {"card_id": card_id, "origin": [x, y], "quarter_turns": 0,
            "placement_index": index, "kind": "start" if index == 0 else "exit",
            "cells": [[x, y], [x, y + 1]], "overlaps": [], "covered_placement_index": None}


def record(seed, win=False):
    collected = []
    if win:
        for i, card_id in enumerate(("card-0", "card-1", "card-2", "card-12", "card-13"), 1):
            collected.append({"order": i, "card_id": card_id, "material": "raincoat" if i <= 3 else "rope",
                              "turn": i, "player_index": 0,
                              "cells": [cell(0, 0, "NS"), cell(0, 1, "NS")]})
    placements = [placement("start_easy")]
    cells = [cell(0, 0, "NS"), cell(0, 1, "N")]
    if win:
        placements.append(placement("exit", 1, (0, -2)))
        cells = [cell(0, -2, "S"), cell(0, -1, "NS")] + cells
    return {"seed": seed, "setup": dict(v.SETUP),
            "result": {"won": win, "turns": 6 if win else 0, "open_tunnels": 0 if win else 1,
                       "visible_water_cells": 0, "raincoats": 3 if win else 0, "ropes": 2 if win else 0,
                       "exit_placed": win, "reason": "win" if win else "no_legal_move",
                       "ruleset_id": v.RULESET, "setup_id": v.SETUP_ID},
            "board": {"placements": placements, "visible_cells": cells}, "collected_equipment": collected}


def summary(first):
    # Independent test oracle; do not call the verifier's summarize implementation.
    wins = [r["seed"] for r in first if r["result"]["won"]]
    failures = {}
    for r in first:
        if not r["result"]["won"]:
            reason = r["result"]["reason"]
            failures[reason] = failures.get(reason, 0) + 1
    return {"games_per_pass": 400, "matching_records": 400, "wins": len(wins), "win_rate": len(wins) / 400,
            "quota_overshoots": sum(r["result"]["raincoats"] > 3 or r["result"]["ropes"] > 2 for r in first),
            "winning_seed_ids": wins, "failure_reasons": dict(sorted(failures.items())),
            "interpretation": "Quota-corrected v2 baseline only; spent seeds; no improvement or confirmation claim",
            "normalized_pass_sha256": hashlib.sha256(encoded(first)).hexdigest()}


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """Pin overrides are explicit and confined to synthetic execution/data authority."""
    for name, value in SYNTHETIC_PINS.items():
        monkeypatch.setattr(v, name, value)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    deck = {"instances": [{"card_id": f"card-{i}", "material": "raincoat" if i < 12 else "rope" if i < 20 else None,
                           "external_ports": ["LU", "B"] if i == 67 else ["T", "B"], "internal_bridge": True,
                           "water_half": "top" if i == 20 else None} for i in range(68)]}
    special = {"special_geometry": {"start_easy": {"cells": [cell(0, 0, "NS"), cell(0, 1, "N")]},
                                    "exit": {"cells": [cell(0, 0, "S"), cell(0, 1, "NS")]}}}
    source = {}
    for name, value in (("deck-v1.json", deck), ("deck-observations-v0.json", special)):
        raw = encoded(value)
        (data_dir / name).write_bytes(raw)
        source[f"data/{name}"] = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    monkeypatch.setattr(v, "SOURCE_MAP_SHA256", fingerprint)
    first = [record(seed, win=seed == 1000000) for seed in v.SEEDS]
    source_receipt = {"head": v.HEAD, "harness_blob": v.HARNESS_BLOB, "harness_sha256": v.HARNESS_SHA256,
                      "source_blobs": source, "python_implementation": "CPython", "python_version": "3.11.14"}
    receipt = {
        "schema": "bandido-canonical-baseline-v1", "expected_head": v.HEAD,
        "preregistration_url": v.PREREGISTRATION, "run_id": str(v.RUN_ID), "run_attempt": "1",
        "accepted_main": v.ACCEPTED_MAIN, "accepted_tree": v.ACCEPTED_TREE, "worker": 30,
        "ruleset_id": v.RULESET, "setup_id": v.SETUP_ID, "setup": dict(v.SETUP),
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "max_steps": 1000,
        "seed_start": 1000000, "seed_end": 1000399, "population": 400, "passes": [1, 2],
        "fresh_seeds_used": False, "status": "complete", "classification": v.CLASSIFICATION,
        "research_interpretation_performed": True,
        "attempted": [{"pass": p, "seed": s} for p, s in v.EXPECTED], "current": None,
        "completed_records": 800, "errors": [], "source_before": deepcopy(source_receipt),
        "source_after": deepcopy(source_receipt), "source_at_finalization": deepcopy(source_receipt),
        "last_durable_completed_records": 800, "observed_journal_records": 800,
        "step_outcomes": {"tests": "success", "cohort": "success"},
        "summary": summary(first),
    }
    rows = [{"pass": p, "record": deepcopy(r)} for p in (1, 2) for r in first]
    names = ["Initialize evidence before dependencies and tests", "Routine and synthetic tests",
             "Two complete fixed baseline passes", "Reconcile final status", "Run actions/upload-artifact@v4"]
    metadata = {
        "run": {"id": v.RUN_ID, "run_attempt": 1, "head_sha": v.HEAD, "status": "completed",
                "conclusion": "success", "event": "pull_request", "path": ".github/workflows/canonical-baseline.yml",
                "head_branch": "research/worker30-canonical-baseline", "repository": {"full_name": v.REPOSITORY},
                "head_repository": {"full_name": v.REPOSITORY}},
        "job": {"id": 111, "run_id": v.RUN_ID, "run_attempt": 1, "head_sha": v.HEAD, "name": "baseline", "status": "completed",
                "conclusion": "success", "runner_name": "bandido-alcatraz-ci",
                "labels": ["self-hosted", "Linux", "X64", "bandido-alcatraz-ci"],
                "steps": [{"name": n, "status": "completed", "conclusion": "success"} for n in names]},
        "artifact": {"id": 222, "name": f"worker30-canonical-baseline-{v.RUN_ID}-1", "expired": False,
                     "workflow_run": {"id": v.RUN_ID, "head_sha": v.HEAD}},
    }
    return {"path": tmp_path / "synthetic.zip", "receipt": receipt, "rows": rows, "metadata": metadata,
            "source": source, "data_dir": data_dir}


def archive(e, mutate_files=None):
    files = {"receipt.json": encoded(e["receipt"]), "completed.jsonl": b"".join(encoded(r) for r in e["rows"])}
    for row in e["rows"]:
        r, p = row["record"], row["pass"]
        files[f"raw-results/pass-{p}/{r['seed']}.json"] = encoded({"pass": p, "seed": r["seed"], "result": r["result"],
                                                               "public_capture_count": 1, "public_captures": [r]})
    if mutate_files:
        mutate_files(files)
    with zipfile.ZipFile(e["path"], "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    inventory = {"schema": "worker30-artifact-inventory-v1", "artifact_id": 222,
                 "archive": sha_size(e["path"].read_bytes()), "receipt": sha_size(files["receipt.json"]),
                 "journal": sha_size(files["completed.jsonl"])}
    e["metadata"]["artifact"].update(size_in_bytes=inventory["archive"]["size_bytes"],
                                        digest="sha256:" + inventory["archive"]["sha256"])
    return inventory


def verify(e, inventory=None):
    return v.verify(e["path"], inventory or archive(e), e["metadata"], e["source"], e["data_dir"])


def edit_sidecar(files, edit):
    key = "raw-results/pass-1/1000000.json"
    value = json.loads(files[key])
    edit(value)
    files[key] = encoded(value)


def test_fixed_pins_and_no_engine_imports():
    assert v.SOURCE_MAP_SHA256 == "27b4a000202d5e22b3e37ea128571cd7a5b8a4ef1a882514616c361cf2da0aed"
    assert v.ACCEPTED_MAIN == "d357a01bed0cccb34bae3c440cc7201ef39a2a84"
    assert v.ACCEPTED_TREE == "8f694dfff0999ba57015a6fdb2bcfc05793cf063"
    assert v.RUN_ID == 36837736898
    assert v.HEAD == "7daeaba0dba2a73db21e3075199eabab6303b241"
    assert v.HARNESS_BLOB == "bc54bdcc5cbc158ae096562ad7ec7b8ac025bb40"
    assert v.HARNESS_SHA256 == "d15a2d74c55973863937d6f9b883ef8b59f99cd0fc5342d8d839b80400ba2110"
    assert v.EXECUTION_FREEZE.endswith("#issuecomment-5927853920")
    v.validate_execution_freeze()
    assert v.RULESET == "v2-exact-equipment-quota-limited-collect-full-hand-refresh"
    assert v.CLASSIFICATION == "canonical_quota_limited_solo_baseline_reproduced"
    tree = ast.parse(Path(v.__file__).read_text())
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports += [item.name for node in ast.walk(tree) if isinstance(node, ast.Import) for item in node.names]
    assert not any(name and ("bandido" in name or "canonical_baseline" in name) for name in imports)
    assert len(v.EXPECTED) == 800 and v.EXPECTED[0] == (1, 1000000) and v.EXPECTED[-1] == (2, 1000399)


@pytest.mark.parametrize("field,value", [
    ("RUN_ID", None), ("RUN_ID", True), ("RUN_ID", "987654321"), ("RUN_ID", 0), ("RUN_ID", 10**15 + 1),
    ("HEAD", None), ("HEAD", "TODO"), ("HEAD", "0" * 40), ("HEAD", "A" * 40),
    ("HARNESS_BLOB", None), ("HARNESS_BLOB", "0" * 40), ("HARNESS_BLOB", "a" * 39),
    ("HARNESS_SHA256", None), ("HARNESS_SHA256", "0" * 64), ("HARNESS_SHA256", "a" * 40),
])
def test_unfrozen_execution_fails_before_archive_read(evidence, monkeypatch, field, value):
    monkeypatch.setattr(v, field, value)

    def forbid_archive_read(*args, **kwargs):
        pytest.fail("unfrozen pins must be rejected before reading candidate evidence")

    monkeypatch.setattr(v, "read_archive", forbid_archive_read)
    with pytest.raises(v.Rejected, match="execution freeze missing or invalid: " + field):
        v.verify(evidence["path"], {}, {}, {}, evidence["data_dir"])


def test_complete_synthetic_cohort_recomputes_independent_summary(evidence):
    report = verify(evidence)
    assert report["verified"] is True
    assert report["verified_sidecars"] == 800
    assert report["summary"] == summary([r["record"] for r in evidence["rows"][:400]])
    assert report["summary"]["wins"] == 1
    assert report["summary"]["winning_seed_ids"] == [1000000]
    assert report["summary"]["quota_overshoots"] == 0
    assert report["runtime"] == {"python_implementation": "CPython", "python_version": "3.11.14"}


def test_zero_win_complete_cohort_is_accepted(evidence):
    evidence["rows"] = [{"pass": p, "record": record(seed)} for p, seed in v.EXPECTED]
    evidence["receipt"]["summary"] = summary([r["record"] for r in evidence["rows"][:400]])
    assert verify(evidence)["summary"]["wins"] == 0


def test_all_win_complete_cohort_is_accepted_without_old_outcome_requirement(evidence):
    evidence["rows"] = [{"pass": p, "record": record(seed, win=True)} for p, seed in v.EXPECTED]
    evidence["receipt"]["summary"] = summary([r["record"] for r in evidence["rows"][:400]])
    report = verify(evidence)
    assert report["summary"]["wins"] == 400
    assert report["summary"]["quota_overshoots"] == 0


@pytest.mark.parametrize("field,card_ids", [("raincoats", [0, 1, 2, 3]), ("ropes", [12, 13, 14])])
@pytest.mark.parametrize("terminal", ["no_legal_move", "closed_tunnels_conditions_failed"])
def test_coherent_overquota_loss_rejected_even_after_all_hashes_rebuilt(evidence, field, card_ids, terminal):
    # Keep physical identities, equipment history, turns, geometry, both passes,
    # raw sidecars, summary and frozen archive hashes coherent. Only the v2 quota
    # is violated, including when the final state could never count as a win.
    bad = record(1000000, win=terminal == "closed_tunnels_conditions_failed")
    if terminal == "no_legal_move":
        bad["collected_equipment"] = []
    else:
        material = "raincoat" if field == "raincoats" else "rope"
        bad["collected_equipment"] = [c for c in bad["collected_equipment"] if c["material"] != material]
    for card_id in card_ids:
        bad["collected_equipment"].append({
            "card_id": f"card-{card_id}", "material": "raincoat" if field == "raincoats" else "rope",
            "cells": [cell(0, 0, "NS"), cell(0, 1, "NS")], "player_index": 0})
    for i, item in enumerate(bad["collected_equipment"], 1):
        item.update(order=i, turn=i)
    bad["result"].update(won=False, reason=terminal,
                         turns=len(bad["collected_equipment"]) + len(bad["board"]["placements"]) - 1)
    bad["result"][field] = len(card_ids)
    for row in (evidence["rows"][0], evidence["rows"][400]):
        row["record"] = deepcopy(bad)
    evidence["receipt"]["summary"] = summary([r["record"] for r in evidence["rows"][:400]])
    assert evidence["receipt"]["summary"]["quota_overshoots"] == 1
    with pytest.raises(v.Rejected, match=field + ": integer/range"):
        verify(evidence)


@pytest.mark.parametrize("version", [None, 3.11, True, "3.11", "3.10.15", "3.12.1", "3.11.-1",
                                    "3.11.01", "3.11.14rc1", "3.11.14\n", "3.11.14.extra"])
def test_runtime_must_be_exact_stable_python311_patch(evidence, version):
    for key in ("source_before", "source_after", "source_at_finalization"):
        evidence["receipt"][key]["python_version"] = version
    with pytest.raises(v.Rejected, match="exact CPython 3.11 patch"):
        verify(evidence)


@pytest.mark.parametrize("snapshot", ["source_before", "source_after", "source_at_finalization"])
@pytest.mark.parametrize("field", ["python_version", "python_implementation", "harness_sha256", "source_blobs"])
def test_complete_runtime_and_source_provenance_required(evidence, snapshot, field):
    evidence["receipt"][snapshot].pop(field)
    with pytest.raises(v.Rejected, match="receipt"):
        verify(evidence)


def test_coherently_wrong_runtime_implementation_rejected(evidence):
    for key in ("source_before", "source_after", "source_at_finalization"):
        evidence["receipt"][key]["python_implementation"] = "PyPy"
    with pytest.raises(v.Rejected, match="receipt source_before"):
        verify(evidence)


def test_copied_accepted_geometry_files_match_independent_source_pin():
    root = Path(__file__).resolve().parents[1]
    source = dict(ACCEPTED_SOURCE_BLOBS)
    cards = v.load_cards(root / "data", source)
    assert len(cards) == 70
    assert sum(c["material"] == "raincoat" for c in cards.values()) == 12
    assert sum(c["material"] == "rope" for c in cards.values()) == 8
    assert sum(cell["water"] for c in cards.values() for cell in c["cells"]) == 4
    assert cards["start_easy"]["material"] is cards["exit"]["material"] is None


@pytest.mark.parametrize("field,value", [
    ("status", "execution_blocked"), ("status", "integrity_invalid"), ("status", "running"),
    ("classification", None), ("classification", "PROGRAM_SUCCESS"), ("run_id", "1"),
    ("run_attempt", "2"), ("expected_head", "0" * 40), ("accepted_tree", "0" * 40),
    ("ruleset_id", "wrong"), ("setup_id", "wrong"), ("fresh_seeds_used", True),
    ("completed_records", 799), ("completed_records", 800.0), ("current", {"pass": 2, "seed": 1000399}),
    ("errors", ["error"]), ("research_interpretation_performed", False), ("population", 399),
    ("passes", [2, 1]), ("unexpected", 1),
    ("worker", 29), ("worker", 30.0), ("max_steps", 999), ("max_steps", 1000.0),
    ("last_durable_completed_records", 799), ("last_durable_completed_records", 800.0),
    ("observed_journal_records", None), ("observed_journal_records", 799),
    ("observed_journal_records", 800.0), ("execution_extent", "unknown"),
])
def test_receipt_contract_rejects(evidence, field, value):
    evidence["receipt"][field] = value
    with pytest.raises(v.Rejected, match="receipt"):
        verify(evidence)


@pytest.mark.parametrize("edit", [
    lambda r: r["attempted"].pop(),
    lambda r: r["attempted"].reverse(),
    lambda r: r["attempted"][0].update(seed=1000001),
    lambda r: r["attempted"][0].update(**{"pass": True}),
    lambda r: r["source_after"].update(harness_blob="0" * 40),
    lambda r: r["source_after"].update(harness_sha256="0" * 64),
    lambda r: r["source_at_finalization"].update(harness_blob="0" * 40),
    lambda r: r["source_at_finalization"].update(harness_sha256="0" * 64),
    lambda r: r["source_at_finalization"].update(python_version="3.11.15"),
    lambda r: r["source_after"].update(python_version="3.11.15"),
    lambda r: r["source_before"].update(extra=True),
    lambda r: r["source_before"]["source_blobs"].update({"src/injected.py": "0" * 40}),
    lambda r: r["policy"].update(setup_weight=251),
    lambda r: r["setup"].update(hand_size=3),
    lambda r: r["step_outcomes"].update(tests="failure"),
])
def test_receipt_nested_contract(evidence, edit):
    edit(evidence["receipt"])
    with pytest.raises(v.Rejected):
        verify(evidence)


@pytest.mark.parametrize("section,field,value", [
    ("run", "id", 1), ("run", "run_attempt", 2), ("run", "head_sha", "0" * 40),
    ("run", "conclusion", "failure"), ("run", "status", "in_progress"), ("run", "event", "workflow_dispatch"),
    ("run", "repository", {"full_name": "different/repo"}), ("run", "path", "other.yml"),
    ("job", "run_id", 1), ("job", "runner_name", "other"), ("job", "name", "pytest"),
    ("job", "conclusion", "failure"), ("job", "steps", []), ("job", "labels", []),
    ("artifact", "id", 333), ("artifact", "expired", True), ("artifact", "workflow_run", {"id": 1}),
])
def test_authoritative_metadata(evidence, section, field, value):
    evidence["metadata"][section][field] = value
    with pytest.raises(v.Rejected):
        verify(evidence)


def test_initial_failed_run_remains_rejected_even_with_coherent_run_fields(evidence):
    previous_run = 36836684444
    evidence["metadata"]["run"]["id"] = previous_run
    evidence["metadata"]["job"]["run_id"] = previous_run
    evidence["metadata"]["artifact"]["workflow_run"]["id"] = previous_run
    evidence["metadata"]["artifact"]["name"] = f"worker30-canonical-baseline-{previous_run}-1"
    evidence["receipt"]["run_id"] = str(previous_run)
    # Even fabricating a complete/successful old-run artifact cannot make that
    # superseded identity eligible under the replacement execution freeze.
    with pytest.raises(v.Rejected, match="authoritative run ID"):
        verify(evidence)


def test_authoritative_steps_and_artifact_digest(evidence):
    inv = archive(evidence)
    evidence["metadata"]["job"]["steps"][1]["conclusion"] = "failure"
    with pytest.raises(v.Rejected, match="step"):
        verify(evidence, inv)
    evidence["metadata"]["job"]["steps"][1]["conclusion"] = "success"
    evidence["metadata"]["artifact"]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(v.Rejected, match="artifact digest"):
        verify(evidence, inv)


@pytest.mark.parametrize("target", ["archive", "receipt", "journal"])
def test_frozen_hash_inventory(evidence, target):
    inv = archive(evidence)
    inv[target]["sha256"] = "0" * 64
    with pytest.raises(v.Rejected, match="SHA256/size mismatch"):
        verify(evidence, inv)


def test_archive_tamper_preserves_original_and_does_not_emit_result(evidence, capsys):
    inv = archive(evidence)
    evidence["path"].write_bytes(evidence["path"].read_bytes() + b"untrusted")
    original = evidence["path"].read_bytes()
    files = {"inventory": inv, "metadata": evidence["metadata"], "source-manifest": evidence["source"]}
    args = [str(evidence["path"])]
    for name, value in files.items():
        path = evidence["path"].parent / (name + ".json")
        path.write_bytes(encoded(value))
        args += ["--" + name, str(path)]
    args += ["--data-dir", str(evidence["data_dir"])]
    assert v.main(args) == 1
    captured = capsys.readouterr()
    assert not captured.out and "no baseline accepted" in captured.err
    assert evidence["path"].read_bytes() == original


@pytest.mark.parametrize("edit", [
    lambda f: f.pop("raw-results/pass-2/1000399.json"),
    lambda f: f.update({"raw-results/pass-1/999999.json": b"{}"}),
    lambda f: f.update({"recovery-receipt-failure.json": b"{}"}),
    lambda f: f.update({"../escape.json": b"{}"}),
    lambda f: f.update({"receipt.json.tmp": b"{}"}),
])
def test_incomplete_extra_recovery_and_unsafe_zip(evidence, edit):
    inv = archive(evidence, edit)
    with pytest.raises(v.Rejected, match="ZIP"):
        verify(evidence, inv)


@pytest.mark.parametrize("kind", ["duplicate", "symlink", "extra_directory"])
def test_ambiguous_zip_entries(evidence, kind):
    inv = archive(evidence)
    with zipfile.ZipFile(evidence["path"], "a") as z:
        if kind == "duplicate":
            with pytest.warns(UserWarning):
                z.writestr("receipt.json", encoded(evidence["receipt"]))
        elif kind == "symlink":
            info = zipfile.ZipInfo("other")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "receipt.json")
        else:
            z.writestr("extra/", b"")
    inv["archive"] = sha_size(evidence["path"].read_bytes())
    with pytest.raises(v.Rejected, match="ZIP"):
        verify(evidence, inv)


@pytest.mark.parametrize("mutate", [
    lambda rows: rows.pop(), lambda rows: rows.append(deepcopy(rows[-1])),
    lambda rows: rows.reverse(), lambda rows: rows[1].update(record=deepcopy(rows[0]["record"])),
    lambda rows: rows[0].update(extra=True), lambda rows: rows[0].update(**{"pass": True}),
    lambda rows: rows[0]["record"].update(seed=999999),
])
def test_complete_serial_population(evidence, mutate):
    mutate(evidence["rows"])
    with pytest.raises(v.Rejected):
        verify(evidence)


@pytest.mark.parametrize("edit", [
    lambda raw: raw.update(public_capture_count=0),
    lambda raw: raw.update(public_capture_count=True),
    lambda raw: raw.update(public_captures=[]),
    lambda raw: raw.update(capture_error={"message": "incomplete"}),
    lambda raw: raw.update(seed=1000001),
    lambda raw: raw["result"].update(turns=3),
    lambda raw: raw["public_captures"][0]["board"]["visible_cells"][0].update(water=True),
])
def test_sidecar_matches_entire_public_capture(evidence, edit):
    inv = archive(evidence, lambda files: edit_sidecar(files, edit))
    with pytest.raises(v.Rejected, match="sidecar"):
        verify(evidence, inv)


def test_full_record_comparison_includes_loss_reason(evidence):
    evidence["rows"][401]["record"]["result"]["reason"] = "deck_exhausted"
    with pytest.raises(v.Rejected, match="differ between passes"):
        verify(evidence)


@pytest.mark.parametrize("field,value", [
    ("wins", 2), ("win_rate", 0.9), ("winning_seed_ids", []), ("failure_reasons", {}),
    ("normalized_pass_sha256", "0" * 64), ("matching_records", 399), ("games_per_pass", True),
    ("quota_overshoots", 1), ("quota_overshoots", False), ("quota_overshoots", 0.0),
])
def test_summary_not_trusted(evidence, field, value):
    evidence["receipt"]["summary"][field] = value
    with pytest.raises(v.Rejected, match="independent recomputation"):
        verify(evidence)


@pytest.mark.parametrize("edit", [
    lambda r: r["result"].update(won=1), lambda r: r["result"].update(turns=6.0),
    lambda r: r["result"].update(open_tunnels=True), lambda r: r["result"].update(visible_water_cells=-1),
    lambda r: r["result"].update(raincoats=4), lambda r: r["result"].update(won=False),
    lambda r: r["result"].update(reason="step_limit"), lambda r: r["result"].update(reason="not-known"),
    lambda r: r["result"].update(reason="no_legal_move"), lambda r: r["result"].update(setup_id="other"),
    lambda r: r["collected_equipment"][0].update(order=True),
    lambda r: r["collected_equipment"][0].update(player_index=1),
    lambda r: r["collected_equipment"][0].update(material="rope"),
    lambda r: r["collected_equipment"][1].update(turn=1),
    lambda r: r["collected_equipment"][1].update(card_id="card-0"),
    lambda r: r["collected_equipment"][0].update(card_id="unknown"),
    lambda r: r["collected_equipment"][0]["cells"][0].update(water=True),
    lambda r: r["collected_equipment"].pop(),
    lambda r: r["board"]["placements"][1].update(card_id="card-0"),
    lambda r: r["board"]["placements"][1].update(placement_index=True),
    lambda r: r["board"]["placements"][1].update(quarter_turns=4),
    lambda r: r["board"]["placements"][1].update(covered_placement_index=0),
    lambda r: r["board"]["visible_cells"].reverse(),
    lambda r: r["board"]["visible_cells"].append(deepcopy(r["board"]["visible_cells"][0])),
    lambda r: r["board"]["visible_cells"][0].update(water=1),
    lambda r: r["board"]["visible_cells"][0].update(water=True),
    lambda r: r["board"]["visible_cells"][0].update(tunnel_edges=["N", "S"]),
    lambda r: r["board"]["visible_cells"][0].update(tunnel_edges=[]),
    lambda r: r["board"]["visible_cells"][0].update(tunnel_edges=["S", "S"]),
    lambda r: r["board"]["visible_cells"][0].update(tunnel_edges=["invalid"]),
])
def test_result_types_victory_equipment_and_public_board(evidence, edit):
    edit(evidence["rows"][0]["record"])
    with pytest.raises(v.Rejected):
        verify(evidence)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                                  b'{"x":false', b'\xff', b'{}{}'])
def test_strict_json(raw):
    with pytest.raises((ValueError, UnicodeError)):
        v.strict_json(raw)


@pytest.mark.parametrize("mutation", [
    lambda b: b[:-1], lambda b: b + b"\n", lambda b: b.replace(b'"pass":1', b'"pass":1,"pass":1', 1),
    lambda b: b.replace(b'"turns":6', b'"turns":NaN', 1),
])
def test_malformed_journal(evidence, mutation):
    inv = archive(evidence, lambda f: f.update({"completed.jsonl": mutation(f["completed.jsonl"])}))
    with pytest.raises((ValueError, UnicodeError)):
        verify(evidence, inv)


def test_self_reported_source_map_is_not_authority(evidence):
    evidence["source"]["src/injected.py"] = "0" * 40
    with pytest.raises(v.Rejected, match="independently pinned"):
        verify(evidence)


def test_changed_data_is_rejected(evidence):
    path = evidence["data_dir"] / "deck-v1.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(v.Rejected, match="accepted data changed"):
        verify(evidence)


@pytest.mark.parametrize("mutation", ["rotation_90", "rotation_180", "wrong_card", "edge_swap", "water_swap"])
def test_physical_geometry_rejects_coherent_full_artifact_mutations(evidence, mutation):
    # This synthetic loss has a two-cell water card above START. Every mutation
    # below preserves the old gate's scalar counters and final adjacency checks.
    base = record(1000000)
    placed = placement("card-20", 1, (0, -2))
    placed["kind"] = "ordinary"
    base["board"]["placements"].append(placed)
    base["board"]["visible_cells"] = [cell(0, -2, "NS", True), cell(0, -1, "NS")] + base["board"]["visible_cells"]
    base["result"].update(turns=1, visible_water_cells=1)
    for row in (evidence["rows"][0], evidence["rows"][400]):
        row["record"] = deepcopy(base)
    evidence["receipt"]["summary"] = summary([r["record"] for r in evidence["rows"][:400]])
    assert verify(evidence)["verified"] is True

    for row in (evidence["rows"][0], evidence["rows"][400]):
        board = row["record"]["board"]
        if mutation == "rotation_90":
            board["placements"][1]["quarter_turns"] = 1
        elif mutation == "rotation_180":
            board["placements"][1]["quarter_turns"] = 2
        elif mutation == "wrong_card":
            board["placements"][1]["card_id"] = "card-67"
        elif mutation == "edge_swap":
            board["visible_cells"][0]["tunnel_edges"] = ["S", "W"]
        else:
            board["visible_cells"][0]["water"] = False
            board["visible_cells"][1]["water"] = True
    # Rebuild both sidecars, journal, independent test-oracle summary, and full
    # ZIP/hash inventory. Rejection must come from physical provenance, not an
    # unrepaired producer hash or a mismatch between the two deterministic passes.
    evidence["receipt"]["summary"] = summary([r["record"] for r in evidence["rows"][:400]])
    with pytest.raises(v.Rejected, match="pinned physical"):
        verify(evidence)


@pytest.mark.parametrize("turns,expected", [
    (0, [cell(3, -4, "NE", True), cell(3, -3, "W")]),
    (1, [cell(3, -4, "N"), cell(4, -4, "ES", True)]),
    (2, [cell(3, -4, "E"), cell(3, -3, "SW", True)]),
    (3, [cell(3, -4, "NW", True), cell(4, -4, "S")]),
])
def test_pinned_card_rotation_normalizes_coordinates_and_preserves_water(turns, expected):
    card = {"cells": [cell(0, 0, "NE", True), cell(0, 1, "W")]}
    geometry = v.physical_placement(card, turns, (3, -4))
    assert [geometry[point] for point in sorted(geometry)] == expected


@pytest.mark.parametrize("attempt", [None, 2, True, "1"])
def test_job_attempt_is_mandatory_exact_first_attempt(evidence, attempt):
    if attempt is None:
        evidence["metadata"]["job"].pop("run_attempt")
    else:
        evidence["metadata"]["job"]["run_attempt"] = attempt
    with pytest.raises(v.Rejected, match="job attempt must be present and exactly 1"):
        verify(evidence)


def test_oversized_sparse_model_file_rejected_before_read(evidence, monkeypatch):
    path = evidence["data_dir"] / "deck-v1.json"
    with path.open("r+b") as stream:
        stream.truncate(v.MAX_MODEL_DATA_BYTES + 1)

    def forbid_open(*args, **kwargs):
        pytest.fail("oversized model file must be rejected before opening/reading it")

    monkeypatch.setattr(Path, "open", forbid_open)
    with pytest.raises(v.Rejected, match="model data exceeds safety bound"):
        v.load_cards(evidence["data_dir"], evidence["source"])


def test_model_file_read_remains_bounded_after_size_check(evidence, monkeypatch):
    class GrowingFile(io.BytesIO):
        def read(self, size=-1):
            assert size == v.MAX_MODEL_DATA_BYTES + 1
            return b" " * size

    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: GrowingFile())
    with pytest.raises(v.Rejected, match="model data exceeds safety bound"):
        v.load_cards(evidence["data_dir"], evidence["source"])



def test_json_file_read_remains_bounded_after_size_check(tmp_path, monkeypatch):
    path = tmp_path / "growing.json"
    path.write_bytes(b"{}")
    monkeypatch.setattr(v, "MAX_BYTES", 64)

    class GrowingFile(io.BytesIO):
        def read(self, size=-1):
            assert size == 65, "JSON input must use a bounded read despite the small stat result"
            return b"{}" + b" " * 63

    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: GrowingFile())
    with pytest.raises(v.Rejected, match="JSON input exceeds safety bound"):
        v.read_json(path)


def test_archive_read_remains_bounded_after_size_check(evidence, monkeypatch):
    inventory = archive(evidence)
    original = evidence["path"].read_bytes()
    expected_size = inventory["archive"]["size_bytes"]

    class GrowingFile(io.BytesIO):
        def read(self, size=-1):
            assert size == expected_size + 1, "archive read must be bounded by its frozen byte size"
            return original + b"x"

    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: GrowingFile())
    with pytest.raises(v.Rejected, match="archive size after read"):
        v.read_archive(evidence["path"], inventory)


def test_json_at_exact_size_bound_still_parses(tmp_path, monkeypatch):
    path = tmp_path / "exact.json"
    raw = b'{"synthetic":true}'
    path.write_bytes(raw)
    monkeypatch.setattr(v, "MAX_BYTES", len(raw))
    assert v.read_json(path) == {"synthetic": True}


def test_unchanged_synthetic_archive_remains_byte_identical(evidence):
    inventory = archive(evidence)
    original = evidence["path"].read_bytes()
    files = v.read_archive(evidence["path"], inventory)
    assert len(files) == 802
    assert sha_size(files["receipt.json"]) == inventory["receipt"]
    assert sha_size(files["completed.jsonl"]) == inventory["journal"]
    assert evidence["path"].read_bytes() == original


def test_complete_verification_preserves_every_input(evidence):
    inv = archive(evidence)
    paths = [evidence["path"], *evidence["data_dir"].iterdir()]
    before = {p: p.read_bytes() for p in paths}
    objects = deepcopy([inv, evidence["metadata"], evidence["source"]])
    assert verify(evidence, inv)["verified"]
    assert [inv, evidence["metadata"], evidence["source"]] == objects
    assert {p: p.read_bytes() for p in paths} == before
