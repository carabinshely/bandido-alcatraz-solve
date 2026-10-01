"""Self-contained, synthetic offline-gate tests; no research games are run.

The 70-card physical model and complete 1,200-record artifact below are made
locally for these tests. Both source-map pins and the frozen control fingerprint
are explicitly patched; these fixtures cannot establish a real research result.
Only the verifier and its hash-pinned pure geometry helper are loaded. There are
no engine, policy, harness, network, Git, or uncommitted fixture dependencies.
Run with: python -m unittest discover -s tests -v
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
import tempfile
import types
import unittest
from unittest.mock import patch
import warnings
import zipfile


VERIFIER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_worker31_development.py"
v = types.ModuleType("worker31_verifier_under_test")
v.__file__ = str(VERIFIER_PATH)
exec(compile(VERIFIER_PATH.read_bytes(), str(VERIFIER_PATH), "exec"), v.__dict__)


def encode(value, newline=True):
    """Fixture encoding independent of the verifier's serialization functions."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + ("\n" if newline else "")).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(raw):
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def file_descriptor(path):
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(32768):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def cell(x, y, edges):
    return {"x": x, "y": y, "tunnel_edges": sorted(edges), "water": False}


def placement(card_id, index=0, origin=None):
    x, y = origin or [0, 0]
    return {"card_id": card_id, "origin": [x, y], "quarter_turns": 0,
            "placement_index": index, "kind": "start" if index == 0 else "ordinary",
            "cells": [[x, y], [x, y + 1]], "overlaps": [], "covered_placement_index": None}


def base_record(seed):
    return {"seed": seed, "setup": deepcopy(v.SETUP), "collected_equipment": [],
            "board": {"placements": [placement("start_easy")],
                      "visible_cells": [cell(0, 0, "ES"), cell(0, 1, "N")]},
            "result": {"won": False, "turns": 0, "open_tunnels": 1,
                       "visible_water_cells": 0, "raincoats": 0, "ropes": 0,
                       "exit_placed": False, "reason": "no_legal_move",
                       "ruleset_id": v.RULESET, "setup_id": v.SETUP_ID}}


def public_card(card_id, cards):
    return {"card_id": card_id, "is_exit": card_id == "exit", **deepcopy(cards[card_id])}


def observation(record, hand=()):
    return {"board": {"placements": deepcopy(record["board"]["placements"]),
                      "cells": deepcopy(record["board"]["visible_cells"])},
            "hand": deepcopy(list(hand)), "raincoats": record["result"]["raincoats"],
            "ropes": record["result"]["ropes"], "exit_placed": record["result"]["exit_placed"],
            "exit_seen": record["result"]["exit_placed"] or any(c["is_exit"] for c in hand),
            "turns": record["result"]["turns"], "set_aside_unplayable": 0,
            "collected_equipment": [
                {"card": {"card_id": c["card_id"], "material": c["material"], "is_exit": False,
                          "cells": deepcopy(c["cells"])},
                 "turn": c["turn"], "player_index": 0} for c in record["collected_equipment"]],
            "setup": deepcopy(v.SETUP), "player_index": 0}


def move(index=0, action="collect", origin=None):
    return {"action": action, "hand_index": index,
            "origin": origin if action == "place" else None, "quarter_turns": 0}


def decision(obs, chosen=None, ordinal=1, candidate=False, before="a" * 64, after=None,
             primary=None, scores=None):
    after = after if after is not None else (before if chosen is None else sha(before.encode()))
    audit = {"public_observation_sha256": sha(encode(obs)), "chosen_move": deepcopy(chosen),
             "rng_before_sha256": before, "rng_after_sha256": after}
    if candidate:
        primary = deepcopy(primary if primary is not None else ([] if chosen is None else [chosen]))
        eligible = bool(primary) and all(m["action"] == "collect" for m in primary)
        if eligible:
            scores = scores if scores is not None else [5] * len(primary)
            rank = [(s is not None, 0 if s is None else s) for s in scores]
            narrowed = [m for m, r in zip(primary, rank) if r == min(rank)]
            opportunities = [{"hand_index": m["hand_index"],
                              "card_id": obs["hand"][m["hand_index"]]["card_id"],
                              "opportunity_score": s} for m, s in zip(primary, scores)]
        else:
            narrowed, opportunities = primary, []
        audit.update(legal_move_count=len(primary), primary_tier=primary,
                     primary_tier_sha256=sha(encode(primary)), primary_score=17 if primary else None,
                     eligible_collect_tier=eligible, collection_opportunities=opportunities,
                     opportunity_null_is_lowest=True, narrowed_tier=deepcopy(narrowed),
                     narrowed_tier_sha256=sha(encode(narrowed)), narrowed_tier_count=len(narrowed),
                     strict_narrowing=len(narrowed) < len(primary))
    return [{"event": "decision_started", "ordinal": ordinal, "observation": deepcopy(obs),
             "rng_before_sha256": before},
            {"event": "decision_completed", "ordinal": ordinal, "audit": audit}]


def terminal(record, decisions=1, actions=0):
    return [{"event": "game_returned", "result": deepcopy(record["result"])},
            {"event": "game_completed", "record_sha256": sha(encode(record)),
             "trace_counts": {"decision_count": decisions, "non_null_choices": actions}}]


def lines(events):
    return b"".join(encode(event) for event in events)


def collect_record(record, card):
    result = deepcopy(record)
    result["result"]["turns"] += 1
    result["result"]["raincoats" if card["material"] == "raincoat" else "ropes"] += 1
    result["collected_equipment"].append({"order": len(result["collected_equipment"]) + 1,
        "card_id": card["card_id"], "material": card["material"], "cells": deepcopy(card["cells"]),
        "turn": result["result"]["turns"], "player_index": 0})
    return result


class MemoryArchive:
    """Already-decoded event transport for focused public-trace unit tests."""
    def __init__(self, events, control=None):
        self.events = events
        self.control = events if control is None else control

    def lines(self, name, limit):
        values = self.control if "/pass-1/" in name else self.events
        for value in values:
            yield value, encode(value)


class SyntheticGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(prefix="worker31-synthetic-")
        cls.addClassCleanup(cls.storage.cleanup)
        cls.root = Path(cls.storage.name)
        cls.data_dir = cls.root / "data"
        cls.data_dir.mkdir()
        instances = [{"card_id": f"card-{i:02d}",
                      "material": "raincoat" if i < 3 else "rope" if i < 5 else None,
                      "external_ports": ["LU", "RU"], "internal_bridge": True, "water_half": None}
                     for i in range(68)]
        documents = {"deck-v1.json": {"instances": instances},
                     "deck-observations-v0.json": {"special_geometry": {
                         "start_easy": {"cells": [cell(0, 0, "ES"), cell(0, 1, "N")]},
                         "exit": {"cells": [cell(0, 0, "SW"), cell(0, 1, "N")]}}}}
        cls.source = {}
        for name, document in documents.items():
            raw = encode(document)
            (cls.data_dir / name).write_bytes(raw)
            cls.source["data/" + name] = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        cls.source_sha = sha(encode(cls.source, newline=False))
        with patch.object(v.g, "SOURCE_MAP_SHA256", cls.source_sha):
            cls.cards = v.g.load_cards(cls.data_dir, cls.source)
        cls.records = [base_record(seed) for seed in v.SEEDS]
        cls.control_sha = sha(encode(cls.records))
        cls.summary = {
            "games_per_pass": 400, "matching_records": 400, "quota_overshoots": 0,
            "control_wins": 0, "wins": 0, "win_rate": 0.0, "winning_seed_ids": [],
            "net_wins": 0, "min_net_wins": 8, "classification": v.CLASSIFICATION,
            "paired_2x2": {"both_win": 0, "control_only": 0, "candidate_only": 0, "both_lose": 400},
            "gained_seed_ids": [], "lost_seed_ids": [], "shared_win_seed_ids": [],
            "both_loss_seed_ids": list(v.SEEDS), "candidate_loss_seed_ids": list(v.SEEDS),
            "control_loss_seed_ids": list(v.SEEDS), "failure_reasons": {"no_legal_move": 400},
            "interpretation": "Spent development screen only; next validation requires separate preregistration",
            "normalized_control_sha256": cls.control_sha, "normalized_candidate_sha256": cls.control_sha,
            "trace_summary": {"candidate_strict_tier_narrowings": 0,
                              "matched_observation_rng_decisions": 400,
                              "selected_action_differences_in_matched_contexts": 0,
                              "candidate_replay_trace_matches": 400,
                              "action_difference_scope": "same seed and ordinal with identical public observation and pre-choice RNG hashes"}}
        snapshot = {"head": v.HEAD, "harness_blob": v.HARNESS_BLOB, "harness_sha256": v.HARNESS_SHA256,
                    "source_blobs": cls.source, "candidate_blob": v.CANDIDATE_BLOB,
                    "candidate_sha256": v.CANDIDATE_SHA256, "python_implementation": "CPython",
                    "python_version": "3.11.9"}
        cls.receipt = {
            "schema": "bandido-equipment-opportunity-development-v1", "expected_head": v.HEAD,
            "preregistration_url": v.PREREGISTRATION, "audit_clarification_url": v.AUDIT_CLARIFICATION,
            "run_id": str(v.RUN_ID), "run_attempt": "1", "accepted_main": v.ACCEPTED_MAIN,
            "accepted_tree": v.ACCEPTED_TREE, "worker": 31, "ruleset_id": v.RULESET,
            "setup_id": v.SETUP_ID, "setup": deepcopy(v.SETUP),
            "policy": {"class": "BoundedMergeV4Policy", "setup_weight": 250},
            "max_steps": 1000, "seed_start": v.SEEDS.start, "seed_end": v.SEEDS.stop - 1,
            "population": 400, "passes": [1, 2, 3],
            "phases": {"1": "v4_control", "2": "candidate", "3": "candidate_replay"},
            "candidate": {"class": "EquipmentOpportunityTiePolicy", "module": v.CANDIDATE_PATH},
            "control_array_sha256": cls.control_sha, "min_net_wins": 8, "fresh_seeds_used": False,
            "status": "complete", "research_interpretation_performed": True,
            "attempted": [{"pass": p, "seed": s} for p in v.PASSES for s in v.SEEDS],
            "current": None, "completed_records": 1200, "errors": [],
            "source_at_initialization": deepcopy(snapshot), "source_before": deepcopy(snapshot),
            "source_after": deepcopy(snapshot), "source_at_finalization": deepcopy(snapshot),
            "last_durable_completed_records": 1200, "observed_journal_records": 1200,
            "step_outcomes": {"tests": "success", "cohort": "success"},
            "classification": v.CLASSIFICATION, "summary": deepcopy(cls.summary)}
        # Initialization is intentionally before the pinned setup-python runtime.
        cls.receipt["source_at_initialization"]["python_version"] = "3.12.4"
        cls.members = {"receipt.json": encode(cls.receipt)}
        rows = []
        for p in v.PASSES:
            for record in cls.records:
                seed = record["seed"]
                rows.append({"pass": p, "record": record})
                counts = {"decision_count": 1, "non_null_choices": 0}
                cls.members[f"raw-results/pass-{p}/{seed}.json"] = encode({
                    "pass": p, "seed": seed, "result": record["result"], "public_capture_count": 1,
                    "public_captures": [record], "trace_counts": counts})
                cls.members[f"decision-traces/pass-{p}/{seed}.jsonl"] = lines(
                    decision(observation(record, [public_card(f"card-{i:02d}", cls.cards) for i in range(5, 11)]),
                             candidate=p != 1) + terminal(record))
        cls.members["completed.jsonl"] = lines(rows)
        cls.archive_path = cls.root / "complete.zip"
        cls.inventory = cls.write_archive(cls.archive_path, cls.members)
        cls.metadata = cls.make_metadata(cls.inventory)

    @staticmethod
    def write_archive(path, members, extra=(), compression=zipfile.ZIP_STORED):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "w", compression=compression) as archive:
                for name, raw in members.items():
                    archive.writestr(name, raw)
                for name, raw in extra:
                    archive.writestr(name, raw)
        return {"schema": "worker31-artifact-inventory-v1", "artifact_id": 123456,
                "archive": file_descriptor(path), "receipt": descriptor(members["receipt.json"]),
                "journal": descriptor(members["completed.jsonl"])}

    @staticmethod
    def make_metadata(inventory):
        return {"run": {"id": v.RUN_ID, "run_attempt": 1, "status": "completed", "conclusion": "success",
                        "head_sha": v.HEAD, "event": "pull_request",
                        "path": ".github/workflows/equipment-opportunity-development.yml",
                        "head_branch": "research/worker31-equipment-opportunity",
                        "repository": {"full_name": v.REPOSITORY},
                        "head_repository": {"full_name": v.REPOSITORY}},
                "job": {"id": 234567, "run_id": v.RUN_ID, "run_attempt": 1, "status": "completed",
                        "conclusion": "success", "head_sha": v.HEAD, "name": "development",
                        "runner_name": "bandido-alcatraz-ci",
                        "labels": ["self-hosted", "Linux", "X64", "bandido-alcatraz-ci"],
                        "steps": [{"name": name, "status": "completed", "conclusion": "success"} for name in [
                            "Initialize evidence before dependencies and tests", "Worker31 focused synthetic tests",
                            "Three complete fixed development phases", "Reconcile final status", "Run actions/upload-artifact@v4"]]},
                "artifact": {"id": inventory["artifact_id"],
                             "name": f"worker31-equipment-opportunity-{v.RUN_ID}-1", "expired": False,
                             "size_in_bytes": inventory["archive"]["size_bytes"],
                             "digest": "sha256:" + inventory["archive"]["sha256"],
                             "workflow_run": {"id": v.RUN_ID, "head_sha": v.HEAD}},
                "execution_commit": {"sha": v.HEAD, "tree": {"sha": v.EXECUTION_TREE}}}

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Production pin checks remain active; only these synthetic data pins change.
        for obj, name, value in [(v, "SOURCE_MAP_SHA256", self.source_sha),
                                 (v.g, "SOURCE_MAP_SHA256", self.source_sha),
                                 (v, "CONTROL_ARRAY_SHA256", self.control_sha), (v, "CONTROL_WINS", 0)]:
            self.stack.enter_context(patch.object(obj, name, value))
        self.case_dir = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="worker31-case-")))

    def bundle(self, updates=None, drop=(), extra=(), compression=zipfile.ZIP_STORED):
        members = dict(self.members)
        members.update(updates or {})
        for name in drop:
            del members[name]
        path = self.case_dir / "mutated.zip"
        inventory = self.write_archive(path, members, extra=extra, compression=compression)
        return path, inventory, self.make_metadata(inventory)

    def verify_bundle(self, bundle=None):
        path, inventory, metadata = bundle or (self.archive_path, self.inventory, self.metadata)
        return v.verify(path, inventory, metadata, self.source, self.data_dir)

    def test_complete_1200_record_synthetic_artifact_passes_without_member_read_all(self):
        before = {p.relative_to(self.root): file_descriptor(p) for p in self.root.rglob("*") if p.is_file()}
        with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("whole-member read forbidden")):
            result = self.verify_bundle()
        self.assertTrue(result["verified"])
        self.assertEqual((result["verified_records"], result["verified_sidecars"], result["verified_traces"]), (1200, 1200, 1200))
        self.assertEqual(result["summary"], self.summary)
        self.assertEqual(result["classification"], v.CLASSIFICATION)
        self.assertEqual(result["runtime"], {"python_implementation": "CPython", "python_version": "3.11.9"})
        self.assertEqual(result["source_map_sha256"], self.source_sha)
        self.assertEqual(before, {p.relative_to(self.root): file_descriptor(p) for p in self.root.rglob("*") if p.is_file()})

    def test_deflated_archive_is_accepted(self):
        result = self.verify_bundle(self.bundle(compression=zipfile.ZIP_DEFLATED))
        self.assertEqual(result["verified_records"], 1200)

    def test_metadata_failure_attempt_and_provenance(self):
        cases = [("run", "status", "in_progress"), ("run", "conclusion", "failure"),
                 ("run", "run_attempt", 2), ("job", "run_attempt", 2),
                 ("run", "id", v.RUN_ID + 1), ("job", "run_id", v.RUN_ID + 1),
                 ("run", "head_sha", "f" * 40), ("job", "head_sha", "f" * 40),
                 ("job", "conclusion", "cancelled"), ("job", "runner_name", "other"),
                 ("run", "event", "workflow_dispatch"), ("run", "head_branch", "main"),
                 ("artifact", "expired", True), ("artifact", "digest", "sha256:" + "0" * 64),
                 ("artifact", "id", 999), ("execution_commit", "sha", "e" * 40)]
        for section, key, value in cases:
            with self.subTest(section=section, key=key):
                metadata = deepcopy(self.metadata)
                metadata[section][key] = value
                with self.assertRaises(v.Rejected):
                    v.validate_metadata(metadata, self.inventory)
        for section, key, value in [("execution_commit", "tree", {"sha": "e" * 40}),
                                    ("run", "head_repository", {"full_name": "other/repo"}),
                                    ("artifact", "workflow_run", {"id": 1, "head_sha": v.HEAD})]:
            metadata = deepcopy(self.metadata)
            metadata[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(v.Rejected):
                v.validate_metadata(metadata, self.inventory)

    def test_required_job_steps_cannot_fail_disappear_duplicate_or_reorder(self):
        for kind in ("failed", "missing", "duplicate", "reordered"):
            metadata = deepcopy(self.metadata)
            steps = metadata["job"]["steps"]
            if kind == "failed":
                steps[1]["conclusion"] = "failure"
            elif kind == "missing":
                steps.pop(1)
            elif kind == "duplicate":
                steps.append(deepcopy(steps[1]))
            else:
                steps[0], steps[1] = steps[1], steps[0]
            with self.subTest(kind=kind), self.assertRaises(v.Rejected):
                v.validate_metadata(metadata, self.inventory)

    def test_repaired_workflow_focused_step_is_exact_and_strict(self):
        v.validate_metadata(self.metadata, self.inventory)
        for name in ("Routine and synthetic tests", "Synthetic tests"):
            metadata = deepcopy(self.metadata)
            metadata["job"]["steps"][1]["name"] = name
            with self.subTest(name=name), self.assertRaisesRegex(v.Rejected, "required job steps"):
                v.validate_metadata(metadata, self.inventory)
        for status, conclusion in (("in_progress", "success"), ("completed", "failure"),
                                   ("completed", "skipped"), ("completed", "cancelled")):
            metadata = deepcopy(self.metadata)
            metadata["job"]["steps"][1].update(status=status, conclusion=conclusion)
            with self.subTest(status=status, conclusion=conclusion), self.assertRaises(v.Rejected):
                v.validate_metadata(metadata, self.inventory)
        metadata = deepcopy(self.metadata)
        steps = metadata["job"]["steps"]
        steps[1], steps[2] = steps[2], steps[1]
        with self.assertRaisesRegex(v.Rejected, "job step order"):
            v.validate_metadata(metadata, self.inventory)

    def test_receipt_rejects_failed_partial_rerun_and_wrong_protocol(self):
        cases = {"status": "failed", "run_attempt": "2", "completed_records": 1199,
                 "last_durable_completed_records": 1199, "observed_journal_records": 1199,
                 "errors": ["failed test"], "current": {"pass": 2, "seed": v.SEEDS.start},
                 "fresh_seeds_used": True, "research_interpretation_performed": False,
                 "accepted_tree": "b" * 40, "accepted_main": "b" * 40,
                 "max_steps": 999, "min_net_wins": 7, "passes": [1, 2],
                 "step_outcomes": {"tests": "failure", "cohort": "success"}}
        for key, value in cases.items():
            receipt = deepcopy(self.receipt)
            receipt[key] = value
            with self.subTest(key=key), self.assertRaises(v.Rejected):
                v.validate_receipt(receipt, self.source)

    def test_all_source_snapshots_are_bound(self):
        for snapshot in ("source_at_initialization", "source_before", "source_after", "source_at_finalization"):
            for key in ("head", "harness_blob", "harness_sha256", "candidate_blob", "candidate_sha256", "source_blobs"):
                receipt = deepcopy(self.receipt)
                receipt[snapshot][key] = {} if key == "source_blobs" else "f" * len(receipt[snapshot][key])
                with self.subTest(snapshot=snapshot, key=key), self.assertRaises(v.Rejected):
                    v.validate_receipt(receipt, self.source)

    def test_research_runtime_is_pinned_but_initial_runtime_is_recorded(self):
        v.validate_receipt(self.receipt, self.source)
        for value in ("3.12.0", "3.11.01", "3.11", "3.11.9rc1"):
            receipt = deepcopy(self.receipt)
            receipt["source_before"]["python_version"] = value
            with self.subTest(version=value), self.assertRaises(v.Rejected):
                v.validate_receipt(receipt, self.source)

    def test_failed_authoritative_run_never_accepts_success_receipt(self):
        metadata = deepcopy(self.metadata)
        metadata["run"]["conclusion"] = "failure"
        with self.assertRaisesRegex(v.Rejected, "authoritative run conclusion"):
            self.verify_bundle((self.archive_path, self.inventory, metadata))

    def test_source_manifest_and_physical_data_tampering_fail(self):
        source = {**self.source, "unexpected.py": "a" * 40}
        with self.assertRaisesRegex(v.Rejected, "source map fingerprint"):
            v.verify(self.archive_path, self.inventory, self.metadata, source, self.data_dir)
        data_dir = self.case_dir / "data"
        data_dir.mkdir()
        for original in self.data_dir.iterdir():
            (data_dir / original.name).write_bytes(original.read_bytes() + b" ")
        with self.assertRaisesRegex(v.Rejected, "accepted data changed"):
            v.verify(self.archive_path, self.inventory, self.metadata, self.source, data_dir)

    def test_control_fingerprint_and_win_count_are_independent(self):
        with patch.object(v, "CONTROL_WINS", 1), self.assertRaisesRegex(v.Rejected, "Worker30 win count"):
            self.verify_bundle()
        receipt = deepcopy(self.receipt)
        receipt["control_array_sha256"] = "b" * 64
        bundle = self.bundle({"receipt.json": encode(receipt)})
        with patch.object(v, "CONTROL_ARRAY_SHA256", "b" * 64), self.assertRaisesRegex(v.Rejected, "Worker30 fingerprint"):
            self.verify_bundle(bundle)

    def test_helper_hash_pin_remains_enforced(self):
        with patch.object(v, "HELPER_SHA256", "b" * 64), self.assertRaisesRegex(ValueError, "pure geometry dependency changed"):
            v.validate_pins()

    def test_stream_hash_is_chunked_exact_and_bounded(self):
        class BoundedReads(io.BytesIO):
            def read(self, size=-1):
                if not 0 <= size <= v.CHUNK:
                    raise AssertionError("unbounded stream read")
                return super().read(size)
        raw = b"abc" * (v.CHUNK + 1)
        self.assertEqual(v.hash_stream(BoundedReads(raw), len(raw)), descriptor(raw))
        with self.assertRaisesRegex(v.Rejected, "stream exceeds byte bound"):
            v.hash_stream(BoundedReads(raw), len(raw) - 1)

    def test_jsonl_iterator_yields_before_reading_next_line(self):
        class OneLineAtATime(io.BytesIO):
            calls = 0
            def readline(self, size=-1):
                self.calls += 1
                if self.calls > 1:
                    raise AssertionError("iterator read ahead")
                if size != v.MAX_LINE + 1:
                    raise AssertionError("line read was not bounded")
                return super().readline(size)
        stream = OneLineAtATime(b'{"a":1}\n{"b":2}\n')
        archive = v.Archive(None, None)
        archive.zip = types.SimpleNamespace(open=lambda name: stream)
        iterator = archive.lines("synthetic.jsonl", 100)
        self.assertEqual(next(iterator), ({"a": 1}, b'{"a":1}\n'))
        self.assertEqual(stream.calls, 1)
        iterator.close()
        self.assertTrue(stream.closed)

    def test_zip_member_crc_detects_tamper_even_with_new_outer_inventory(self):
        name = f"decision-traces/pass-1/{v.SEEDS.start}.jsonl"
        with zipfile.ZipFile(self.archive_path) as archive:
            offset = archive.getinfo(name).header_offset
        raw = bytearray(self.archive_path.read_bytes())
        name_length, extra_length = struct.unpack_from("<HH", raw, offset + 26)
        payload = offset + 30 + name_length + extra_length
        raw[payload + 10] ^= 1
        path = self.case_dir / "corrupt-member.zip"
        path.write_bytes(raw)
        inventory = deepcopy(self.inventory)
        inventory["archive"] = file_descriptor(path)
        with v.Archive(path, inventory) as archive:
            with self.assertRaisesRegex(zipfile.BadZipFile, "CRC"):
                list(archive.lines(name, v.MAX_TRACE))

    def test_outer_archive_digest_and_length_cannot_be_self_attested(self):
        for key, value in (("sha256", "0" * 64), ("size_bytes", self.inventory["archive"]["size_bytes"] - 1)):
            inventory = deepcopy(self.inventory)
            inventory["archive"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(v.Rejected, "archive SHA256/size"):
                with v.Archive(self.archive_path, inventory):
                    pass

    def test_receipt_and_journal_hashes_are_independently_bound(self):
        for name in ("receipt", "journal"):
            inventory = deepcopy(self.inventory)
            inventory[name]["sha256"] = "0" * 64
            with self.subTest(name=name), self.assertRaisesRegex(v.Rejected, name + " SHA256/size"):
                with v.Archive(self.archive_path, inventory):
                    pass

    def test_rejects_path_traversal_unknown_duplicate_and_nonregular_zip_members(self):
        symlink = zipfile.ZipInfo("untrusted-link")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        extras = [("../escape", b"x"), ("/absolute", b"x"), ("raw-results\\evil", b"x"),
                  ("surprise.json", b"{}\n"), ("receipt.json", self.members["receipt.json"]), (symlink, b"target")]
        for name, raw in extras:
            bundle = self.bundle(extra=[(name, raw)])
            with self.subTest(name=str(name)), self.assertRaises(v.Rejected):
                with v.Archive(bundle[0], bundle[1]):
                    pass
        self.assertFalse((self.case_dir.parent / "escape").exists())

    def test_missing_trace_and_unexpected_directory_are_rejected(self):
        name = f"decision-traces/pass-3/{v.SEEDS.start}.jsonl"
        for kwargs in ({"drop": [name]}, {"extra": [("untrusted/", b"")]}):
            bundle = self.bundle(**kwargs)
            with self.assertRaises(v.Rejected):
                with v.Archive(bundle[0], bundle[1]):
                    pass

    def test_zip_truncation_trailer_prefix_and_population_bound(self):
        original = self.archive_path.read_bytes()
        end = original.rfind(b"PK\x05\x06")
        excessive = bytearray(original)
        struct.pack_into("<HH", excessive, end + 8, 2411, 2411)
        for label, raw in [("truncated", original[:-10]), ("trailer", original + b"garbage"),
                           ("prefix", b"prefix" + original), ("population", bytes(excessive))]:
            path = self.case_dir / "bad.zip"
            path.write_bytes(raw)
            inventory = deepcopy(self.inventory)
            inventory["archive"] = file_descriptor(path)
            with self.subTest(label=label), self.assertRaises(v.Rejected):
                with v.Archive(path, inventory):
                    pass

    def test_unsupported_zip_compression_is_rejected(self):
        bundle = self.bundle(compression=zipfile.ZIP_BZIP2)
        with self.assertRaisesRegex(v.Rejected, "unsupported ZIP compression"):
            with v.Archive(bundle[0], bundle[1]):
                pass

    def test_strict_json_duplicate_keys_nonfinite_and_truncation(self):
        for raw in (b'{"a":1,"a":2}\n', b'{"a":NaN}\n', b'{"a":Infinity}\n',
                    b'{"a":-Infinity}\n', b'{"a":1e400}\n', b'{"a":'):
            bundle = self.bundle({"receipt.json": raw})
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.verify_bundle(bundle)

    def test_noncanonical_json_and_jsonl_are_rejected(self):
        bad_receipt = json.dumps(self.receipt, indent=2).encode() + b"\n"
        with self.assertRaisesRegex(v.Rejected, "noncanonical JSON bytes"):
            self.verify_bundle(self.bundle({"receipt.json": bad_receipt}))
        for raw, error in [(b'{}', "partial/empty"), (b'\n', "partial/empty"),
                           (b'{ "a":1}\n', "noncanonical JSONL"), (b'{"a":', "partial/empty")]:
            path, inventory, unused = self.bundle({"completed.jsonl": raw})
            with self.subTest(raw=raw), v.Archive(path, inventory) as archive:
                with self.assertRaisesRegex(v.Rejected, error):
                    list(archive.lines("completed.jsonl", v.MAX_JOURNAL))

    def test_line_and_total_byte_limits_are_enforced(self):
        path, inventory, unused = self.bundle({"completed.jsonl": b'{"a":1}\n'})
        with v.Archive(path, inventory) as archive:
            with patch.object(v, "MAX_LINE", 4), self.assertRaisesRegex(v.Rejected, "JSONL byte bound"):
                list(archive.lines("completed.jsonl", v.MAX_JOURNAL))
            with self.assertRaisesRegex(v.Rejected, "JSONL byte bound"):
                list(archive.lines("completed.jsonl", 4))

    def test_journal_requires_exact_pass_seed_order_and_full_population(self):
        rows = self.members["completed.jsonl"].splitlines(keepends=True)
        wrong_pass = json.loads(rows[0])
        wrong_pass["pass"] = 2
        cases = [("pass", encode(wrong_pass) + b"".join(rows[1:])),
                 ("seed", rows[1] + rows[0] + b"".join(rows[2:])),
                 ("missing", b"".join(rows[:-1])), ("extra", b"".join(rows + [rows[-1]]))]
        for name, raw in cases:
            with self.subTest(name=name), self.assertRaises(v.Rejected):
                self.verify_bundle(self.bundle({"completed.jsonl": raw}))

    def test_raw_sidecar_capture_result_and_counts_must_match(self):
        name = f"raw-results/pass-1/{v.SEEDS.start}.json"
        for key, value in [("public_capture_count", 2), ("seed", v.SEEDS.start + 1),
                           ("trace_counts", {"decision_count": 2, "non_null_choices": 0})]:
            raw = json.loads(self.members[name])
            raw[key] = value
            with self.subTest(key=key), self.assertRaises(v.Rejected):
                self.verify_bundle(self.bundle({name: encode(raw)}))

    def test_candidate_replay_trace_must_be_byte_identical(self):
        name = f"decision-traces/pass-3/{v.SEEDS.start}.jsonl"
        events = [json.loads(row) for row in self.members[name].splitlines()]
        events[0]["rng_before_sha256"] = "b" * 64
        with self.assertRaisesRegex(v.Rejected, "candidate/replay trace bytes differ"):
            self.verify_bundle(self.bundle({name: lines(events)}))

    def test_candidate_replay_record_must_be_identical(self):
        rows = [json.loads(row) for row in self.members["completed.jsonl"].splitlines()]
        record = rows[800]["record"]
        record["result"]["reason"] = "deck_exhausted"
        raw_name = f"raw-results/pass-3/{record['seed']}.json"
        sidecar = json.loads(self.members[raw_name])
        sidecar["result"] = record["result"]
        sidecar["public_captures"] = [record]
        with self.assertRaisesRegex(v.Rejected, "candidate/replay record.*identity"):
            self.verify_bundle(self.bundle({"completed.jsonl": lines(rows), raw_name: encode(sidecar)}))

    def test_producer_summary_and_classification_are_recomputed(self):
        for key in ("summary", "classification"):
            receipt = deepcopy(self.receipt)
            if key == "summary":
                receipt["summary"]["wins"] = 1
            else:
                receipt["classification"] = v.ADVANCED_CLASSIFICATION
            with self.subTest(key=key), self.assertRaisesRegex(v.Rejected, "producer"):
                self.verify_bundle(self.bundle({"receipt.json": encode(receipt)}))

    def action_fixture(self, candidate=False):
        record0 = base_record(v.SEEDS.start)
        coat = public_card("card-00", self.cards)
        ordinary = public_card("card-05", self.cards)
        record1 = collect_record(record0, coat)
        record2 = deepcopy(record1)
        record2["result"]["turns"] += 1
        record2["board"]["placements"].append(placement("card-05", 1, [1, 0]))
        record2["board"]["visible_cells"] += [cell(1, 0, "ESW"), cell(1, 1, "N")]
        filler = [public_card(f"card-{i:02d}", self.cards) for i in range(6, 12)]
        hand0 = [coat, ordinary] + filler[:4]
        hand1 = [ordinary] + filler[:5]
        hand2 = filler
        events = decision(observation(record0, hand0), move(), candidate=candidate, after="b" * 64)
        events += decision(observation(record1, hand1), move(action="place", origin=[1, 0]),
                           ordinal=2, candidate=candidate, before="b" * 64, after="c" * 64)
        events += decision(observation(record2, hand2), ordinal=3, candidate=candidate, before="c" * 64)
        events += terminal(record2, decisions=3, actions=2)
        return record2, events

    def test_nonzero_collection_placement_and_null_transition(self):
        for candidate in (False, True):
            record, events = self.action_fixture(candidate)
            v.g.validate_record(record, record["seed"], self.cards)
            control = self.action_fixture(False)[1]
            result = v.validate_trace(MemoryArchive(events, control=control), record, 2 if candidate else 1, self.cards)
            self.assertEqual(result, ({"decision_count": 3, "non_null_choices": 2}, 0, 3 if candidate else 0, 0))

    def test_public_trace_forbids_hidden_fields_at_all_boundaries(self):
        for target in ("observation", "audit", "start", "completed", "move"):
            record, events = self.action_fixture(True)
            if target == "observation":
                events[0]["observation"]["deck"] = []
            elif target == "audit":
                events[1]["audit"]["rng_state"] = [1, 2, 3]
            elif target == "start":
                events[0]["hidden_hand"] = []
            elif target == "completed":
                events[1]["deck_state"] = []
            else:
                events[1]["audit"]["chosen_move"]["policy_score"] = 12
            with self.subTest(target=target), self.assertRaises(v.Rejected):
                v.validate_trace(MemoryArchive(events), record, 2, self.cards)

    def test_trace_ordinals_turn_counts_rng_chain_and_terminal_are_bound(self):
        mutations = {
            "start ordinal": lambda e: e[0].update(ordinal=2),
            "complete ordinal": lambda e: e[1].update(ordinal=2),
            "observed turns": lambda e: e[2]["observation"].update(turns=0),
            "RNG chain": lambda e: (e[2].update(rng_before_sha256="d" * 64), e[3]["audit"].update(rng_before_sha256="d" * 64)),
            "null consumes RNG": lambda e: e[5]["audit"].update(rng_after_sha256="d" * 64),
            "trace count": lambda e: e[-1]["trace_counts"].update(decision_count=2),
            "action count": lambda e: e[-1]["trace_counts"].update(non_null_choices=1),
            "record hash": lambda e: e[-1].update(record_sha256="e" * 64),
            "reported result": lambda e: e[-2]["result"].update(turns=1),
            "after terminal": lambda e: e.append(deepcopy(e[0])),
            "missing completed": lambda e: e.pop(),
            "missing returned": lambda e: e.pop(-2),
            "no terminal": lambda e: e.__delitem__(slice(-2, None)),
        }
        for name, mutate in mutations.items():
            record, events = self.action_fixture(False)
            mutate(events)
            with self.subTest(name=name), self.assertRaises(v.Rejected):
                v.validate_trace(MemoryArchive(events), record, 1, self.cards)

    def test_transition_cannot_add_unselected_card_or_skip_collection(self):
        record, events = self.action_fixture(False)
        # The second observation remains physically valid, but cannot follow the first choice.
        events[2]["observation"]["collected_equipment"][0]["card"] = public_card("card-01", self.cards)
        events[3]["audit"]["public_observation_sha256"] = sha(encode(events[2]["observation"]))
        with self.assertRaisesRegex(v.Rejected, "public transition vs prior choice"):
            v.validate_trace(MemoryArchive(events), record, 1, self.cards)

    def test_exit_seen_and_aside_counts_cannot_regress(self):
        for field, first, second in [("exit_seen", True, False), ("set_aside_unplayable", 1, 0)]:
            record, events = self.action_fixture(False)
            previous, following = events[0]["observation"], events[2]["observation"]
            previous[field], following[field] = first, second
            with self.subTest(field=field), self.assertRaises(v.Rejected):
                v.validate_public_progression(previous, move(), following)

    def test_narrowing_uses_minimum_opportunity_with_null_lowest(self):
        record = base_record(v.SEEDS.start)
        hand = [public_card(name, self.cards) for name in ("card-00", "card-03", "card-01")]
        primary = [move(i) for i in range(3)]
        for scores, chosen_index, expected in [([7, None, 2], 1, [primary[1]]),
                                                ([7, 2, 2], 1, primary[1:]),
                                                ([None, None, 2], 0, primary[:2]),
                                                ([3, 3, 3], 0, primary)]:
            started, completed = decision(observation(record, hand), primary[chosen_index], candidate=True,
                                          primary=primary, scores=scores)
            audit = completed["audit"]
            self.assertEqual(audit["narrowed_tier"], expected)
            self.assertEqual(v.validate_audit(audit, started, hand, 2), int(len(expected) < len(primary)))

    def test_tampered_narrowing_audit_cannot_change_frozen_rule(self):
        record = base_record(v.SEEDS.start)
        hand = [public_card(name, self.cards) for name in ("card-00", "card-03")]
        primary = [move(0), move(1)]
        started, completed = decision(observation(record, hand), primary[1], candidate=True,
                                      primary=primary, scores=[5, None])
        for label in ("wrong winner", "false strict", "wrong digest", "hidden legal moves", "boolean score", "duplicate tier"):
            audit = deepcopy(completed["audit"])
            if label == "wrong winner":
                audit["narrowed_tier"] = [primary[0]]
                audit["narrowed_tier_sha256"] = sha(encode(audit["narrowed_tier"]))
                audit["chosen_move"] = primary[0]
            elif label == "false strict":
                audit["strict_narrowing"] = False
            elif label == "wrong digest":
                audit["primary_tier_sha256"] = "b" * 64
            elif label == "hidden legal moves":
                audit["legal_move_count"] = 1
            elif label == "boolean score":
                audit["collection_opportunities"][0]["opportunity_score"] = True
            else:
                audit["primary_tier"].append(primary[0])
                audit["legal_move_count"] = 3
                audit["primary_tier_sha256"] = sha(encode(audit["primary_tier"]))
            with self.subTest(label=label), self.assertRaises(v.Rejected):
                v.validate_audit(audit, started, hand, 2)

    def test_noncollect_tier_must_not_be_narrowed(self):
        hand = [public_card("card-00", self.cards), public_card("card-05", self.cards)]
        primary = [move(0), move(1, "place", [1, 0])]
        started, completed = decision(observation(base_record(v.SEEDS.start), hand), primary[0],
                                      candidate=True, primary=primary)
        self.assertEqual(v.validate_audit(completed["audit"], started, hand, 2), 0)
        audit = deepcopy(completed["audit"])
        audit["narrowed_tier"] = [primary[0]]
        audit["narrowed_tier_sha256"] = sha(encode(audit["narrowed_tier"]))
        audit["narrowed_tier_count"] = 1
        audit["strict_narrowing"] = True
        with self.assertRaisesRegex(v.Rejected, "frozen narrowed-tier rule"):
            v.validate_audit(audit, started, hand, 2)

    def test_summary_paired_counts_and_exact_advancement_threshold(self):
        seeds = list(v.SEEDS)
        control = seeds[:45]
        for net, candidate in [(7, seeds[:40] + seeds[45:57]), (8, seeds[:40] + seeds[45:58])]:
            result = v.summarize(control, candidate, Counter({"no_legal_move": 400 - len(candidate)}),
                                 "c" * 64, "d" * 64, {"fixture": True})
            with self.subTest(net=net):
                self.assertEqual(result["net_wins"], net)
                self.assertEqual(result["classification"], v.ADVANCED_CLASSIFICATION if net == 8 else v.CLASSIFICATION)
                self.assertEqual(result["paired_2x2"], {"both_win": 40, "control_only": 5,
                                 "candidate_only": net + 5, "both_lose": 350 - net})
                self.assertEqual(result["gained_seed_ids"], candidate[40:])
                self.assertEqual(result["lost_seed_ids"], seeds[40:45])
                self.assertEqual(result["wins"], len(candidate))
                self.assertEqual(result["normalized_control_sha256"], "c" * 64)
                self.assertEqual(result["normalized_candidate_sha256"], "d" * 64)
                self.assertEqual(result["trace_summary"], {"fixture": True})

    def winning_fixture(self, seed):
        """Five collections then one EXIT placement; constructed without replay helpers."""
        record = base_record(seed)
        hand = [public_card(f"card-{i:02d}", self.cards) for i in range(5)]
        hand.append(public_card("exit", self.cards))
        initial = observation(record, hand)
        rng, events = "a" * 64, []
        for ordinal in range(1, 6):
            after = sha(rng.encode())
            events += decision(observation(record, hand), move(), ordinal=ordinal,
                               candidate=True, before=rng, after=after)
            record = collect_record(record, hand[0])
            hand = hand[1:] + [public_card(f"card-{ordinal + 4:02d}", self.cards)]
            rng = after
        events += decision(observation(record, hand), move(action="place", origin=[1, 0]),
                           ordinal=6, candidate=True, before=rng, after=sha(rng.encode()))
        record["board"]["placements"].append({**placement("exit", 1, [1, 0]), "kind": "exit"})
        record["board"]["visible_cells"] += [cell(1, 0, "SW"), cell(1, 1, "N")]
        record["result"].update(turns=6, exit_placed=True, open_tunnels=0, won=True, reason="win")
        events += terminal(record, decisions=6, actions=6)
        return record, events, initial

    def test_eight_net_wins_advance_in_full_verifier(self):
        # Initial control nulls deliberately do not assert policy legality: this
        # verifier certifies exposed evidence, not exhaustive legal-move search.
        winners = list(v.SEEDS)[:8]
        updates, candidate = {}, {}
        for seed in winners:
            record, events, initial = self.winning_fixture(seed)
            candidate[seed] = record
            control = base_record(seed)
            updates[f"decision-traces/pass-1/{seed}.jsonl"] = lines(decision(initial) + terminal(control))
            for p in (2, 3):
                updates[f"decision-traces/pass-{p}/{seed}.jsonl"] = lines(events)
                updates[f"raw-results/pass-{p}/{seed}.json"] = encode({
                    "pass": p, "seed": seed, "result": record["result"],
                    "public_capture_count": 1, "public_captures": [record],
                    "trace_counts": {"decision_count": 6, "non_null_choices": 6}})
        candidate_records = [candidate.get(seed, base_record(seed)) for seed in v.SEEDS]
        updates["completed.jsonl"] = lines(
            {"pass": p, "record": record} for p in v.PASSES
            for record in (self.records if p == 1 else candidate_records))
        expected = deepcopy(self.summary)
        expected.update(wins=8, win_rate=0.02, winning_seed_ids=winners, net_wins=8,
                        classification=v.ADVANCED_CLASSIFICATION, gained_seed_ids=winners,
                        paired_2x2={"both_win": 0, "control_only": 0, "candidate_only": 8, "both_lose": 392},
                        both_loss_seed_ids=list(v.SEEDS)[8:], candidate_loss_seed_ids=list(v.SEEDS)[8:],
                        failure_reasons={"no_legal_move": 392},
                        normalized_candidate_sha256=sha(encode(candidate_records)))
        expected["trace_summary"]["selected_action_differences_in_matched_contexts"] = 8
        receipt = deepcopy(self.receipt)
        receipt.update(summary=expected, classification=v.ADVANCED_CLASSIFICATION)
        updates["receipt.json"] = encode(receipt)
        result = self.verify_bundle(self.bundle(updates))
        self.assertEqual(result["classification"], v.ADVANCED_CLASSIFICATION)
        self.assertEqual(result["verified_records"], 1200)
        self.assertEqual(result["summary"], expected)

    def test_initial_hand_and_public_draw_progression(self):
        record, events = self.action_fixture(False)
        initial, following = events[0]["observation"], events[2]["observation"]
        v.validate_public_progression(None, None, initial)
        v.validate_public_progression(initial, move(), following)
        for kind in ("short initial", "initial aside", "initial EXIT flag", "missing draw", "reordered", "changed aside"):
            old, new = deepcopy(initial), deepcopy(following)
            if kind == "short initial":
                old["hand"].pop()
            elif kind == "initial aside":
                old["set_aside_unplayable"] = 1
            elif kind == "initial EXIT flag":
                old["exit_seen"] = True
            elif kind == "missing draw":
                new["hand"].pop()
            elif kind == "reordered":
                new["hand"][0], new["hand"][1] = new["hand"][1], new["hand"][0]
            else:
                new["set_aside_unplayable"] = 1
            with self.subTest(kind=kind), self.assertRaises(v.Rejected):
                if kind.startswith("initial") or kind == "short initial":
                    v.validate_public_progression(None, None, old)
                else:
                    v.validate_public_progression(old, move(), new)

    def test_null_refresh_requires_disjoint_hand_and_short_pile_aside_count(self):
        old = observation(base_record(v.SEEDS.start), [public_card(f"card-{i:02d}", self.cards) for i in range(5, 11)])
        new = observation(base_record(v.SEEDS.start), [public_card(f"card-{i:02d}", self.cards) for i in range(11, 17)])
        v.validate_public_progression(old, None, new)
        retained = deepcopy(new)
        retained["hand"][0] = old["hand"][0]
        with self.assertRaisesRegex(v.Rejected, "refresh retained"):
            v.validate_public_progression(old, None, retained)
        old["set_aside_unplayable"] = 60  # Three unseen cards remain.
        new["hand"] = new["hand"][:3]
        new["set_aside_unplayable"] = 66
        v.validate_public_progression(old, None, new)
        new["set_aside_unplayable"] = 60
        with self.assertRaisesRegex(v.Rejected, "refresh set-aside count"):
            v.validate_public_progression(old, None, new)

    def test_initial_control_candidate_context_and_nonnull_rng_are_bound(self):
        record, events = self.action_fixture(True)
        control = self.action_fixture(False)[1]
        control[1]["audit"]["public_observation_sha256"] = "e" * 64
        with self.assertRaisesRegex(v.Rejected, "initial public context"):
            v.validate_trace(MemoryArchive(events, control), record, 2, self.cards)
        audit = deepcopy(events[1]["audit"])
        audit["rng_after_sha256"] = audit["rng_before_sha256"]
        with self.assertRaisesRegex(v.Rejected, "did not advance RNG"):
            v.validate_audit(audit, events[0], events[0]["observation"]["hand"], 2)

    def test_fixed_setup_cannot_skip_initial_decision_or_choose_after_win(self):
        record = base_record(v.SEEDS.start)
        with self.assertRaisesRegex(v.Rejected, "requires an initial decision"):
            v.validate_trace(MemoryArchive(terminal(record, 0, 0)), record, 1, self.cards)
        record, events, initial = self.winning_fixture(v.SEEDS.start)
        final_hand = [public_card(f"card-{i:02d}", self.cards) for i in range(5, 11)]
        extra = decision(observation(record, final_hand), ordinal=7, candidate=True,
                         before=events[-3]["audit"]["rng_after_sha256"])
        events = events[:-2] + extra + terminal(record, 7, 6)
        control = decision(initial) + terminal(base_record(record["seed"]))
        with self.assertRaisesRegex(v.Rejected, "decision after observable terminal state"):
            v.validate_trace(MemoryArchive(events, control), record, 2, self.cards)

    def test_selected_placement_must_attach_and_preserve_overlap_rules(self):
        record = base_record(v.SEEDS.start)
        hand = [public_card("card-05", self.cards)]
        for origin, message in [([9, 9], "disconnected"), ([0, 0], "overlaps multiple"),
                                ([0, -1], "covers non-water"), ([1, 1], "tunnel adjacency")]:
            with self.subTest(origin=origin), self.assertRaisesRegex(v.Rejected, message):
                v.post_choice(record, move(action="place", origin=origin), hand, self.cards)

    def test_cli_rejection_is_not_a_negative_research_classification(self):
        metadata = deepcopy(self.metadata)
        metadata["job"]["conclusion"] = "failure"
        arguments = [str(self.archive_path)]
        for name, document in [("inventory", self.inventory), ("metadata", metadata), ("source-manifest", self.source)]:
            path = self.case_dir / (name + ".json")
            path.write_bytes(encode(document))
            arguments += ["--" + name, str(path)]
        arguments += ["--data-dir", str(self.data_dir)]
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = v.main(arguments)
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("REJECTED:", errors.getvalue())
        self.assertIn("no research classification accepted", errors.getvalue())
        self.assertNotIn(v.CLASSIFICATION, errors.getvalue())


if __name__ == "__main__":
    unittest.main()
