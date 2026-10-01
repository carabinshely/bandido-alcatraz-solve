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

from scripts import verify_worker29_baseline as v


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
            "winning_seed_ids": wins, "failure_reasons": dict(sorted(failures.items())),
            "interpretation": "Corrected-model baseline only; spent seeds; no improvement or confirmation claim",
            "normalized_pass_sha256": hashlib.sha256(encoded(first)).hexdigest()}


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """The sole pin override is explicit, confined to synthetic data authority."""
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
    source_receipt = {"head": v.HEAD, "harness_blob": v.HARNESS_BLOB, "source_blobs": source}
    receipt = {
        "schema": "bandido-canonical-baseline-v1", "expected_head": v.HEAD,
        "preregistration_url": v.PREREGISTRATION, "run_id": str(v.RUN_ID), "run_attempt": "1",
        "accepted_main": v.ACCEPTED_MAIN, "accepted_tree": v.ACCEPTED_TREE,
        "ruleset_id": v.RULESET, "setup_id": v.SETUP_ID, "setup": dict(v.SETUP),
        "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
        "seed_start": 1000000, "seed_end": 1000399, "population": 400, "passes": [1, 2],
        "fresh_seeds_used": False, "status": "complete", "classification": v.CLASSIFICATION,
        "research_interpretation_performed": True,
        "attempted": [{"pass": p, "seed": s} for p, s in v.EXPECTED], "current": None,
        "completed_records": 800, "errors": [], "source_before": deepcopy(source_receipt),
        "source_after": deepcopy(source_receipt), "step_outcomes": {"tests": "success", "cohort": "success"},
        "summary": summary(first),
    }
    rows = [{"pass": p, "record": deepcopy(r)} for p in (1, 2) for r in first]
    names = ["Initialize evidence before dependencies and tests", "Routine and synthetic tests",
             "Two complete fixed baseline passes", "Reconcile final status", "Run actions/upload-artifact@v4"]
    metadata = {
        "run": {"id": v.RUN_ID, "run_attempt": 1, "head_sha": v.HEAD, "status": "completed",
                "conclusion": "success", "event": "pull_request", "path": ".github/workflows/canonical-baseline.yml",
                "head_branch": "research/worker29-canonical-baseline", "repository": {"full_name": v.REPOSITORY},
                "head_repository": {"full_name": v.REPOSITORY}},
        "job": {"id": 111, "run_id": v.RUN_ID, "run_attempt": 1, "head_sha": v.HEAD, "name": "baseline", "status": "completed",
                "conclusion": "success", "runner_name": "bandido-alcatraz-ci",
                "labels": ["self-hosted", "Linux", "X64", "bandido-alcatraz-ci"],
                "steps": [{"name": n, "status": "completed", "conclusion": "success"} for n in names]},
        "artifact": {"id": 222, "name": f"worker29-canonical-baseline-{v.RUN_ID}-1", "expired": False,
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
    inventory = {"schema": "worker29-artifact-inventory-v1", "artifact_id": 222,
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
    assert v.SOURCE_MAP_SHA256 == "54156930984b646b6431b325dba6ed39e13f89c165c0d4124dab436c913f975a"
    assert v.HEAD == "bf7b1273f8f87b7bc50ccf1ce61acc0f97e9a7f9"
    assert v.HARNESS_BLOB == "4ac40f10960b71f7a14c7455f08e3b486d9b54a0"
    tree = ast.parse(Path(v.__file__).read_text())
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports += [item.name for node in ast.walk(tree) if isinstance(node, ast.Import) for item in node.names]
    assert not any(name and ("bandido" in name or "canonical_baseline" in name) for name in imports)
    assert len(v.EXPECTED) == 800 and v.EXPECTED[0] == (1, 1000000) and v.EXPECTED[-1] == (2, 1000399)


def test_complete_synthetic_cohort_recomputes_independent_summary(evidence):
    report = verify(evidence)
    assert report["verified"] is True
    assert report["verified_sidecars"] == 800
    assert report["summary"] == summary([r["record"] for r in evidence["rows"][:400]])
    assert report["summary"]["wins"] == 1
    assert report["summary"]["winning_seed_ids"] == [1000000]


def test_zero_win_complete_cohort_is_accepted(evidence):
    evidence["rows"] = [{"pass": p, "record": record(seed)} for p, seed in v.EXPECTED]
    evidence["receipt"]["summary"] = summary([r["record"] for r in evidence["rows"][:400]])
    assert verify(evidence)["summary"]["wins"] == 0


@pytest.mark.parametrize("field,value", [
    ("status", "execution_blocked"), ("status", "integrity_invalid"), ("status", "running"),
    ("classification", None), ("classification", "PROGRAM_SUCCESS"), ("run_id", "1"),
    ("run_attempt", "2"), ("expected_head", "0" * 40), ("accepted_tree", "0" * 40),
    ("ruleset_id", "wrong"), ("setup_id", "wrong"), ("fresh_seeds_used", True),
    ("completed_records", 799), ("completed_records", 800.0), ("current", {"pass": 2, "seed": 1000399}),
    ("errors", ["error"]), ("research_interpretation_performed", False), ("population", 399),
    ("passes", [2, 1]), ("unexpected", 1),
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
