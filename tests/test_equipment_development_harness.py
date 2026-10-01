"""Synthetic/mocked checks only. Never execute a photographed-deck game."""
import hashlib
import copy
import json
import os
import py_compile
from pathlib import Path
from random import Random
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import run_equipment_opportunity_development as h
from bandido_alcatraz.board import Board
from bandido_alcatraz.game import CollectedEquipment, PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.setup import GameSetup
from bandido_alcatraz.simulate import GameResult

HEAD = "a" * 40
PREREG = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5928556762"
SOURCE = {"head": HEAD, "harness_blob": "b" * 40, "source_blobs": {"src/example.py": "c" * 40}}


def observation():
    board = Board()
    board.seed(CardDefinition("synthetic-start", (CellSpec(0, 0, frozenset({Direction.NORTH})),)))
    card = CardDefinition("synthetic-rope", (CellSpec(0, 0, frozenset({Direction.WEST, Direction.EAST})),),
                          material=Material.ROPE)
    return PlayerObservation(board, (), 0, 1, False, False, 1, 0,
                             (CollectedEquipment(card, 1, 0),), GameSetup())


def record(seed, reason="no_legal_move"):
    result = GameResult(False, 1, 1, 0, 0, 1, False, reason, h.RULESET, h.SETUP_ID)
    return h.final_record(seed, result, observation())


def all_rows():
    return [{"pass": p, "record": record(seed)} for p in h.PASSES for seed in h.SEEDS]


def quota_record(seed, raincoats, ropes, *, won=False):
    """Construct public result/history directly; never simulate a game."""
    row = record(seed, "win" if won else "no_legal_move")
    row["result"].update(raincoats=raincoats, ropes=ropes, won=won,
                         turns=raincoats+ropes)
    if won:
        row["result"].update(open_tunnels=0, visible_water_cells=0, exit_placed=True)
    prototype = row["collected_equipment"][0]
    row["collected_equipment"] = []
    for material, count in (("raincoat", raincoats), ("rope", ropes)):
        for index in range(count):
            item = copy.deepcopy(prototype)
            item.update(material=material, card_id=f"synthetic-{material}-{index}",
                        order=len(row["collected_equipment"]) + 1)
            row["collected_equipment"].append(item)
    return row


def sidecar(output, pass_number, row, trace_counts=None):
    path = output / "raw-results" / f"pass-{pass_number}" / f'{row["seed"]}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    h.write_json(path, {"pass": pass_number, "seed": row["seed"], "result": row["result"],
                        "public_capture_count": 1, "public_captures": [row],
                        "trace_counts": trace_counts or {"decision_count": row["result"]["turns"], "non_null_choices": row["result"]["turns"]}})


def synthetic_trace(output, pass_number, seed):
    path = h.trace_path(output, pass_number, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = record(seed)
    public = json.loads(h.encoded(h.public_observation_record(observation())))
    public.update(turns=0, ropes=0, hand=[public["collected_equipment"][0]["card"]], collected_equipment=[])
    move = {"action": "collect", "hand_index": 0, "origin": None, "quarter_turns": 0}
    audit = {"public_observation_sha256": h.digest(public), "chosen_move": move,
             "rng_before_sha256": "a" * 64, "rng_after_sha256": "b" * 64}
    if pass_number != 1:
        audit.update(legal_move_count=1, primary_tier=[move], primary_tier_sha256=h.digest([move]), primary_score=10000,
            eligible_collect_tier=True, collection_opportunities=[{"hand_index": 0, "card_id": "synthetic-rope", "opportunity_score": None}],
            opportunity_null_is_lowest=True, narrowed_tier=[move], narrowed_tier_sha256=h.digest([move]),
            narrowed_tier_count=1, strict_narrowing=False)
    h.append_jsonl(path, {"event": "decision_started", "ordinal": 1, "observation": public, "rng_before_sha256": "a" * 64})
    h.append_jsonl(path, {"event": "decision_completed", "ordinal": 1, "audit": audit})
    h.append_jsonl(path, {"event": "game_returned", "result": row["result"]})
    h.append_jsonl(path, {"event": "game_completed", "record_sha256": h.digest(row),
                        "trace_counts": {"decision_count": 1, "non_null_choices": 1}})


class BaselineHarnessTests(unittest.TestCase):
    def setUp(self):
        for name, value in (("CONTROL_WINS", 0), ("CONTROL_ARRAY_SHA256", hashlib.sha256(h.encoded([record(s) for s in h.SEEDS]).encode()).hexdigest())):
            patched = patch.object(h, name, value)
            patched.start()
            self.addCleanup(patched.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run-7-attempt-2"
        self.env = patch.dict(h.os.environ, {"GITHUB_RUN_ID": "7", "GITHUB_RUN_ATTEMPT": "2",
                                            "PYTHONPYCACHEPREFIX": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        for setting, value in (("pycache_prefix", None), ("dont_write_bytecode", True)):
            patched = patch.object(h.sys, setting, value)
            patched.start()
            self.addCleanup(patched.stop)

    def receipt(self):
        return h.read_receipt(self.output)

    def initialize(self):
        return h.initialize(self.output, HEAD, PREREG)

    def run_mock(self, game=None, preflight=None):
        def mocked_game(seed, *, output, pass_number):
            row = (game or record)(seed)
            sidecar(output, pass_number, row)
            synthetic_trace(output, pass_number, seed)
            return row
        with patch.object(h, "preflight", side_effect=preflight, return_value=SOURCE), \
             patch.object(h, "verify_source", return_value=SOURCE), \
             patch.object(h, "one_game", side_effect=mocked_game), patch("builtins.print"):
            return h.run(self.output, HEAD, PREREG)

    def test_exact_frozen_population_and_default_setup(self):
        self.assertEqual(h.SEEDS, tuple(range(1000000, 1000400)))
        self.assertEqual(h.PASSES, (1, 2, 3))
        self.assertEqual(GameSetup().setup_id, h.SETUP_ID)
        self.assertEqual(h.ACCEPTED_MAIN, "7be68ee6eac1337663b960791812c8092c7d53e4")
        self.assertEqual(h.ACCEPTED_TREE, "7ed3b7f1f5a8d09991542f5d22f102e0b83fe612")
        self.assertEqual(h.RULESET, "v2-exact-equipment-quota-limited-collect-full-hand-refresh")
        self.assertEqual(h.PREREGISTRATION_URL, PREREG)
        self.assertEqual(h.MAX_STEPS, 1000)
        self.assertEqual(h.CLASSIFICATION, "equipment_opportunity_tie_development_no_advancement")

    def test_receipt_precedes_preflight_and_game_attempt_precedes_compute(self):
        def preflight(*unused):
            self.assertEqual(self.receipt()["status"], "initialized")
            self.assertEqual(self.receipt()["attempted"], [])
            return SOURCE
        def game(seed):
            receipt = self.receipt()
            self.assertEqual(receipt["current"], {"pass": 1, "seed": seed})
            self.assertEqual(receipt["attempted"], [{"pass": 1, "seed": seed}])
            raise OSError("synthetic interruption before result")
        self.assertEqual(self.run_mock(game, preflight), 1)
        self.assertEqual(self.receipt()["completed_records"], 0)
        self.assertEqual(self.receipt()["status"], "execution_blocked")

    def test_two_complete_serial_passes_zero_wins_await_finalization(self):
        calls = []
        def game(seed):
            calls.append(seed)
            return record(seed)
        self.assertEqual(self.run_mock(game), 0)
        self.assertEqual(calls, list(h.SEEDS) * 3)
        receipt = self.receipt()
        self.assertEqual(receipt["completed_records"], 1200)
        self.assertEqual(receipt["status"], "awaiting_finalization")
        self.assertIsNone(receipt["classification"])
        self.assertFalse(receipt["research_interpretation_performed"])
        with patch.object(h, "verify_source", return_value=SOURCE), patch("builtins.print"):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 0)
        receipt = self.receipt()
        self.assertEqual(receipt["classification"], h.CLASSIFICATION)
        self.assertEqual(receipt["summary"]["wins"], 0)
        self.assertEqual(receipt["summary"]["matching_records"], 400)
        self.assertEqual(receipt["summary"]["quota_overshoots"], 0)
        self.assertEqual(receipt["worker"], 31)

    def test_all_quota_boundaries_accept_consistent_public_history(self):
        for raincoats in range(4):
            for ropes in range(3):
                with self.subTest(raincoats=raincoats, ropes=ropes):
                    h.validate_record(quota_record(h.SEEDS[0], raincoats, ropes), h.SEEDS[0])
        h.validate_record(quota_record(h.SEEDS[0], 3, 2, won=True), h.SEEDS[0])

    def test_quota_overshoot_invalidates_even_matching_passes(self):
        for field, value in (("raincoats", 4), ("ropes", 3), ("raincoats", -1),
                             ("ropes", -1), ("raincoats", True), ("ropes", 1.0)):
            with self.subTest(field=field, value=value):
                rows = all_rows()
                for offset in (0, len(h.SEEDS)):
                    rows[offset]["record"]["result"][field] = value
                with self.assertRaisesRegex(h.IntegrityError, "quota overshoot"):
                    h.compare_passes(rows)

    def test_history_cannot_hide_excess_collection_or_duplicate_identity(self):
        invalids = []
        row = quota_record(h.SEEDS[0], 3, 2)
        row["result"]["raincoats"] = 2
        invalids.append((row, "disagrees"))
        row = quota_record(h.SEEDS[0], 4, 2)
        row["result"]["raincoats"] = 3
        invalids.append((row, "disagrees"))
        row = quota_record(h.SEEDS[0], 3, 2)
        row["collected_equipment"][1]["card_id"] = row["collected_equipment"][0]["card_id"]
        invalids.append((row, "duplicate"))
        row = quota_record(h.SEEDS[0], 3, 2)
        row["collected_equipment"][0]["material"] = "unknown"
        invalids.append((row, "unknown"))
        row = quota_record(h.SEEDS[0], 3, 2)
        row["collected_equipment"][0]["order"] = 2
        invalids.append((row, "order"))
        for row, message in invalids:
            with self.subTest(message=message), self.assertRaisesRegex(h.IntegrityError, message):
                h.validate_record(row, h.SEEDS[0])

    def test_win_requires_exact_quotas_without_changing_losing_records(self):
        for raincoats, ropes in ((0, 0), (3, 1), (2, 2)):
            with self.subTest(raincoats=raincoats, ropes=ropes), \
                 self.assertRaisesRegex(h.IntegrityError, "win without exact"):
                h.validate_record(quota_record(h.SEEDS[0], raincoats, ropes, won=True), h.SEEDS[0])

    def test_overshoot_is_durable_before_validation_and_cannot_be_finalized(self):
        self.assertEqual(self.run_mock(lambda seed: quota_record(seed, 4, 2)), 1)
        rows = h.read_records(self.output)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["record"]["result"]["raincoats"], 4)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        before = (self.output / "completed.jsonl").read_bytes()
        self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "failure"), 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertIsNone(self.receipt()["classification"])
        self.assertEqual((self.output / "completed.jsonl").read_bytes(), before)

    def test_raw_sidecar_evidence_is_complete_and_matches_the_journal(self):
        row = record(h.SEEDS[0])
        rows = [{"pass": 1, "record": row}]
        sidecar(self.output, 1, row)
        h.verify_raw_sidecars(self.output, rows)
        path = self.output / "raw-results" / "pass-1" / f'{h.SEEDS[0]}.json'
        raw = json.loads(path.read_text())
        raw["result"]["ropes"] = 2
        h.write_json(path, raw)
        with self.assertRaisesRegex(h.IntegrityError, "sidecar disagrees"):
            h.verify_raw_sidecars(self.output, rows)
        sidecar(self.output, 1, row)
        extra = path.with_name("extra.json")
        extra.write_text("{}")
        with self.assertRaisesRegex(h.IntegrityError, "sidecar population"):
            h.verify_raw_sidecars(self.output, rows)
        extra.unlink()
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            h.verify_raw_sidecars(self.output, rows)

    def test_finalizer_rejects_missing_sidecar_and_incomplete_attempt_provenance(self):
        self.assertEqual(self.run_mock(), 0)
        path = self.output / "raw-results" / "pass-2" / f'{h.SEEDS[-1]}.json'
        raw = path.read_bytes()
        path.unlink()
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "execution_blocked")
        self.assertEqual(self.receipt()["completed_records"], 1200)
        path.write_bytes(raw)
        receipt = self.receipt()
        receipt.update(status="awaiting_finalization", attempted=receipt["attempted"][:-1])
        h.write_json(self.output / "receipt.json", receipt)
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertIn("attempt provenance", self.receipt()["errors"][-1]["message"])

    def test_frozen_receipt_configuration_cannot_drift(self):
        receipt = self.initialize()
        receipt["ruleset_id"] = "superseded-model"
        h.write_json(self.output / "receipt.json", receipt)
        with self.assertRaisesRegex(h.IntegrityError, "identity mismatch: ruleset_id"):
            h.run(self.output, HEAD, PREREG)

    def test_raw_record_precedes_step_limit_validation(self):
        self.assertEqual(self.run_mock(lambda seed: record(seed, "step_limit")), 1)
        raw = h.read_records(self.output)
        self.assertEqual(len(raw), 1)
        self.assertEqual(raw[0]["record"]["result"]["reason"], "step_limit")
        self.assertEqual(self.receipt()["completed_records"], 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertNotIn("summary", self.receipt())

    def test_partial_records_and_attempted_current_survive_exception(self):
        def game(seed):
            if seed == h.SEEDS[2]:
                raise OSError("synthetic worker failure")
            return record(seed)
        self.assertEqual(self.run_mock(game), 1)
        self.assertEqual(len(h.read_records(self.output)), 2)
        receipt = self.receipt()
        self.assertEqual(len(receipt["attempted"]), 3)
        self.assertEqual(receipt["current"], {"pass": 1, "seed": h.SEEDS[2]})
        self.assertEqual(receipt["completed_records"], 2)
        self.assertFalse(receipt["research_interpretation_performed"])

    def test_preflight_absence_is_infrastructure_mismatch_is_invalid(self):
        for error, status in [(FileNotFoundError("missing source"), "execution_blocked"),
                              (h.InfrastructureError("git absent"), "execution_blocked"),
                              (h.IntegrityError("source mismatch"), "integrity_invalid")]:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                with patch.object(h, "preflight", side_effect=error), patch.object(h, "one_game") as game:
                    self.assertEqual(h.run(output, HEAD, PREREG), 1)
                game.assert_not_called()
                receipt = h.read_receipt(output)
                self.assertEqual(receipt["status"], status)
                self.assertEqual(receipt["attempted"], [])
                self.assertIsNone(receipt["classification"])

    def test_previous_attempt_is_never_overwritten_or_resumed(self):
        self.initialize()
        before = (self.output / "receipt.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.initialize()
        self.assertEqual((self.output / "receipt.json").read_bytes(), before)
        self.assertEqual(self.run_mock(lambda seed: record(seed, "step_limit")), 1)
        before = (self.output / "receipt.json").read_bytes()
        raw = (self.output / "completed.jsonl").read_bytes()
        with patch.object(h, "one_game") as game, self.assertRaises(h.IntegrityError):
            h.run(self.output, HEAD, PREREG)
        game.assert_not_called()
        self.assertEqual((self.output / "receipt.json").read_bytes(), before)
        self.assertEqual((self.output / "completed.jsonl").read_bytes(), raw)

    def test_attempt_identity_cannot_mix(self):
        self.initialize()
        before = (self.output / "receipt.json").read_bytes()
        with patch.dict(h.os.environ, {"GITHUB_RUN_ATTEMPT": "3"}), self.assertRaises(h.IntegrityError):
            h.run(self.output, HEAD, PREREG)
        self.assertEqual((self.output / "receipt.json").read_bytes(), before)

    def test_record_contains_public_geometry_and_no_private_fields(self):
        row = record(h.SEEDS[0])
        self.assertEqual(row["result"]["ruleset_id"], h.RULESET)
        self.assertEqual(row["setup"]["hand_size"], 6)
        self.assertEqual(row["collected_equipment"][0], {
            "order": 1, "card_id": "synthetic-rope", "material": "rope", "turn": 1,
            "player_index": 0, "cells": [{"x": 0, "y": 0, "tunnel_edges": ["E", "W"], "water": False}]})
        self.assertEqual(row["board"]["placements"][0]["card_id"], "synthetic-start")
        self.assertEqual(row["board"]["visible_cells"][0]["tunnel_edges"], ["N"])
        for name in ("hand", "draw_pile", "private_hands", "face_down_set_aside"):
            self.assertNotIn('"' + name + '"', h.encoded(row))

    def test_collection_and_placement_order_are_comparison_material(self):
        rows = all_rows()
        rows[-1]["record"]["collected_equipment"][0]["turn"] += 1
        with self.assertRaisesRegex(h.IntegrityError, "collection turn|differ across"):
            h.compare_passes(rows)
        rows = all_rows()
        rows[-1]["record"]["board"]["placements"][0]["quarter_turns"] += 1
        with self.assertRaisesRegex(h.IntegrityError, "differ across"):
            h.compare_passes(rows)

    def test_incomplete_duplicate_reordered_wrong_setup_are_invalid(self):
        rows = all_rows()
        invalids = [rows[:-1], [rows[1], rows[0], *rows[2:]], [*rows[:-1], rows[-2]]]
        for invalid in invalids:
            with self.subTest(), self.assertRaises(h.IntegrityError):
                h.compare_passes(invalid)
        rows[-1]["record"]["result"]["setup_id"] = "wrong"
        with self.assertRaisesRegex(h.IntegrityError, "setup mismatch"):
            h.compare_passes(rows)

    def test_fresh_policy_deck_and_simulator_rng_contract_without_games(self):
        from bandido_alcatraz import physical_deck, policies, simulate
        policies_created, decks, arguments = [], [], []
        def load(unused):
            deck = SimpleNamespace(start_for_setup=lambda setup: "synthetic-start",
                                   draw_deck=lambda: ["synthetic-card"])
            decks.append(deck)
            return deck
        def policy(**kwargs):
            self.assertEqual(kwargs, {"setup_weight": 250})
            instance = SimpleNamespace()
            policies_created.append(instance)
            return instance
        def play(**kwargs):
            arguments.append(kwargs)
            kwargs["policy"].on_game_finished(observation())
            return GameResult(False, 1, 1, 0, 0, 1, False, "no_legal_move", h.RULESET, h.SETUP_ID)
        with patch.object(physical_deck, "load_real_deck", side_effect=load), \
             patch.object(policies, "BoundedMergeV4Policy", side_effect=policy), \
             patch.object(simulate, "play_game", side_effect=play):
            h.one_game(h.SEEDS[0], output=self.output, pass_number=1)
            h.one_game(h.SEEDS[1], output=self.output, pass_number=1)
            for seed in (999999, 1000400, True, "1000000"):
                with self.assertRaises(h.IntegrityError):
                    h.one_game(seed, output=self.output, pass_number=1)
        self.assertEqual(len(decks), 2)
        self.assertIsNot(policies_created[0], policies_created[1])
        self.assertIsNot(arguments[0]["deck"], arguments[1]["deck"])
        self.assertEqual([a["seed"] for a in arguments], list(h.SEEDS[:2]))
        self.assertEqual(arguments[0]["hand_size"], 6)
        self.assertEqual(arguments[0]["max_steps"], 1000)

    def test_policy_receives_only_detached_observation_without_hidden_draw(self):
        from bandido_alcatraz.policies import BoundedMergeV4Policy
        own = observation()
        self.assertFalse(hasattr(own, "draw_pile"))
        # An empty synthetic hand exercises choose without any photographed deck/game.
        self.assertIsNone(BoundedMergeV4Policy(setup_weight=250).choose(own, Random(0)))

    def make_complete_receipt(self):
        receipt = self.initialize()
        receipt.update(status="complete", classification=h.CLASSIFICATION,
                       research_interpretation_performed=True, summary={"wins": 0},
                       source_before=SOURCE, source_after=SOURCE)
        h.write_json(self.output / "receipt.json", receipt)
        return receipt

    def test_finalizer_clears_stale_complete_after_any_failed_step(self):
        for tests, cohort, status in [("failure", "success", "integrity_invalid"),
                                      ("success", "failure", "execution_blocked"),
                                      ("success", "cancelled", "execution_blocked"),
                                      ("skipped", "skipped", "execution_blocked")]:
            with self.subTest(tests=tests, cohort=cohort), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                receipt = h.initialize(output, HEAD, PREREG)
                receipt.update(status="complete", classification=h.CLASSIFICATION,
                               research_interpretation_performed=True, summary={"wins": 0})
                h.write_json(output / "receipt.json", receipt)
                h.append_record(output, 1, record(h.SEEDS[0]))
                raw = (output / "completed.jsonl").read_bytes()
                with patch.object(h, "verify_source", return_value=SOURCE):
                    self.assertEqual(h.finalize(output, HEAD, PREREG, tests, cohort), 1)
                after = h.read_receipt(output)
                self.assertEqual(after["status"], status)
                self.assertIsNone(after["classification"])
                self.assertFalse(after["research_interpretation_performed"])
                self.assertNotIn("summary", after)
                self.assertEqual(after["completed_records"], 1)
                self.assertEqual((output / "completed.jsonl").read_bytes(), raw)

    def test_failed_tests_with_skipped_cohort_and_no_journal_remain_integrity_invalid(self):
        self.initialize()
        self.assertFalse((self.output / "completed.jsonl").exists())
        with patch.object(h, "verify_source", return_value=SOURCE) as verify, \
             patch.object(h, "one_game") as game:
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "failure", "skipped"), 1)
        verify.assert_called_once_with(HEAD)
        game.assert_not_called()
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "integrity_invalid")
        self.assertEqual(receipt["step_outcomes"], {"tests": "failure", "cohort": "skipped"})
        self.assertEqual(receipt["errors"][0], {"phase": "tests", "type": "IntegrityError",
                                                "message": "synthetic test step failed"})
        self.assertEqual(receipt["errors"][-1]["type"], "FileNotFoundError")
        self.assertEqual(receipt["errors"][-1]["phase"], "finalize")
        self.assertEqual(receipt["source_at_finalization"], SOURCE)
        self.assertEqual(receipt["completed_records"], 0)
        self.assertEqual(receipt["last_durable_completed_records"], 0)
        self.assertIsNone(receipt["observed_journal_records"])
        self.assertEqual(receipt["attempted"], [])
        self.assertIsNone(receipt["classification"])
        self.assertFalse(receipt["research_interpretation_performed"])

    def test_finalizer_cannot_bless_initialized_or_invalid_attempt(self):
        self.initialize()
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "execution_blocked")
        receipt = self.receipt()
        receipt["status"] = "integrity_invalid"
        h.write_json(self.output / "receipt.json", receipt)
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")

    def test_missing_output_directory_never_implies_zero_execution(self):
        for cohort in ("failure", "cancelled", "success", "skipped"):
            with self.subTest(cohort=cohort), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "missing-attempt"
                self.assertFalse(output.exists())
                self.assertEqual(h.finalize(output, HEAD, PREREG, "success", cohort), 1)
                self.assertFalse((output / "receipt.json").exists())
                sidecars = list(output.glob("recovery-receipt-*.json"))
                self.assertEqual(len(sidecars), 1)
                recovery = json.loads(sidecars[0].read_text())
                self.assertEqual(recovery["status"], "execution_blocked")
                self.assertIsNone(recovery["attempted"])
                self.assertIsNone(recovery["completed_records"])
                self.assertIsNone(recovery["classification"])
                self.assertFalse(recovery["research_interpretation_performed"])
                self.assertIn("unknown", recovery["execution_extent"])
                self.assertEqual(recovery["step_outcomes"]["cohort"], cohort)

    def test_interrupted_journal_bytes_preserved(self):
        self.initialize()
        path = self.output / "completed.jsonl"
        path.write_text('{"pass":1', encoding="utf-8")
        raw = path.read_bytes()
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "failure"), 1)
        self.assertEqual(self.receipt()["status"], "execution_blocked")
        self.assertEqual(path.read_bytes(), raw)

    def test_finalizer_rechecks_raw_population_and_source(self):
        self.make_complete_receipt()
        h.append_record(self.output, 1, record(h.SEEDS[0]))
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertNotIn("summary", self.receipt())

    def test_late_finalization_save_and_reporting_failures_clear_success(self):
        for failure in ("save", "print"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                receipt = h.initialize(output, HEAD, PREREG)
                receipt.update(status="awaiting_finalization", source_before=SOURCE, source_after=SOURCE)
                receipt["attempted"] = [{"pass": p, "seed": s} for p in h.PASSES for s in h.SEEDS]
                h.write_json(output / "receipt.json", receipt)
                (output / "completed.jsonl").write_text("".join(h.encoded(row) for row in all_rows()))
                for row in all_rows():
                    sidecar(output, row["pass"], row["record"])
                    synthetic_trace(output, row["pass"], row["record"]["seed"])
                original = h.write_json
                def write(path, value):
                    if failure == "save" and value.get("status") == "complete":
                        raise OSError("synthetic final save failure")
                    original(path, value)
                with patch.object(h, "verify_source", return_value=SOURCE), \
                     patch.object(h, "write_json", side_effect=write), \
                     patch("builtins.print", side_effect=BrokenPipeError("stdout closed") if failure == "print" else None):
                    self.assertEqual(h.finalize(output, HEAD, PREREG, "success", "success"), 1)
                after = h.read_receipt(output)
                self.assertEqual(after["status"], "execution_blocked")
                self.assertEqual(after["completed_records"], 1200)
                self.assertIsNone(after["classification"])
                self.assertFalse(after["research_interpretation_performed"])
                self.assertNotIn("summary", after)

    def test_source_change_at_finalization_invalidates_prior_complete(self):
        self.make_complete_receipt()
        h.append_record(self.output, 1, record(h.SEEDS[0]))
        with patch.object(h, "verify_source", return_value={**SOURCE, "harness_blob": "changed"}):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertIsNone(self.receipt()["classification"])

    def test_setup_dimensions_and_missing_geometry_cannot_match_themselves(self):
        row = record(h.SEEDS[0])
        row["setup"]["hand_size"] = 3
        with self.assertRaisesRegex(h.IntegrityError, "setup dimensions"):
            h.validate_record(row, h.SEEDS[0])
        row = record(h.SEEDS[0])
        row["board"]["placements"] = []
        with self.assertRaisesRegex(h.IntegrityError, "geometry"):
            h.validate_record(row, h.SEEDS[0])

    def test_source_checked_after_partial_failure(self):
        with patch.object(h, "preflight", return_value=SOURCE), \
             patch.object(h, "one_game", side_effect=OSError("interrupted")), \
             patch.object(h, "verify_source", side_effect=h.IntegrityError("source drift")) as verify:
            self.assertEqual(h.run(self.output, HEAD, PREREG), 1)
        verify.assert_called_once_with(HEAD)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertEqual(len(self.receipt()["errors"]), 2)

    def test_cancelled_or_failed_producer_still_reconciles_source(self):
        for outcome in ("cancelled", "failure"):
            for source_error, status in ((h.IntegrityError("changed source"), "integrity_invalid"),
                                          (h.InfrastructureError("git missing"), "execution_blocked")):
                with self.subTest(outcome=outcome, source_error=source_error), tempfile.TemporaryDirectory() as temp:
                    output = Path(temp) / "attempt"
                    receipt = h.initialize(output, HEAD, PREREG)
                    receipt.update(status="running", source_before=SOURCE,
                                   attempted=[{"pass": 1, "seed": h.SEEDS[0]}],
                                   current={"pass": 1, "seed": h.SEEDS[0]})
                    h.write_json(output / "receipt.json", receipt)
                    with patch.object(h, "verify_source", side_effect=source_error) as verify:
                        self.assertEqual(h.finalize(output, HEAD, PREREG, "success", outcome), 1)
                    verify.assert_called_once_with(HEAD)
                    final = h.read_receipt(output)
                    self.assertEqual(final["status"], status)
                    self.assertEqual(final["errors"][0]["phase"], "source_at_finalization")
                    self.assertEqual(final["errors"][0]["message"], str(source_error))
                    self.assertFalse(final["research_interpretation_performed"])

    def test_failure_finalization_retains_accessible_source_evidence_and_detects_drift(self):
        self.initialize()
        receipt = self.receipt()
        receipt.update(status="running", source_before=SOURCE)
        h.write_json(self.output / "receipt.json", receipt)
        (self.output / "completed.jsonl").write_text("")
        changed = {**SOURCE, "harness_blob": "changed"}
        with patch.object(h, "verify_source", return_value=changed):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "cancelled"), 1)
        self.assertEqual(self.receipt()["status"], "integrity_invalid")
        self.assertEqual(self.receipt()["source_at_finalization"], changed)
        self.assertIn("source changed", self.receipt()["errors"][0]["message"])

    def test_missing_unreadable_empty_and_short_journal_never_erase_durable_count(self):
        for mode, expected_status, observed in (("missing", "execution_blocked", None),
                ("unreadable", "execution_blocked", None), ("empty", "integrity_invalid", 0),
                ("short", "integrity_invalid", 1)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                receipt = h.initialize(output, HEAD, PREREG)
                receipt.update(status="running", source_before=SOURCE, completed_records=2,
                               attempted=[{"pass": 1, "seed": s} for s in h.SEEDS[:3]],
                               current={"pass": 1, "seed": h.SEEDS[2]})
                h.write_json(output / "receipt.json", receipt)
                journal = output / "completed.jsonl"
                if mode == "empty":
                    journal.write_text("")
                elif mode in ("short", "unreadable"):
                    h.append_record(output, 1, record(h.SEEDS[0]))
                prior = journal.read_bytes() if journal.exists() else None
                reader = h.read_records
                with patch.object(h, "verify_source", return_value=SOURCE), \
                     patch.object(h, "read_records", side_effect=PermissionError("journal denied") if mode == "unreadable" else reader):
                    self.assertEqual(h.finalize(output, HEAD, PREREG, "success", "cancelled"), 1)
                final = h.read_receipt(output)
                self.assertEqual(final["status"], expected_status)
                self.assertEqual(final["completed_records"], 2)
                self.assertEqual(final["last_durable_completed_records"], 2)
                self.assertEqual(final["observed_journal_records"], observed)
                self.assertIn("unknown", final["execution_extent"])
                self.assertEqual(final["current"], {"pass": 1, "seed": h.SEEDS[2]})
                self.assertEqual(journal.read_bytes() if journal.exists() else None, prior)

    def test_git_command_error_is_not_non_ancestry(self):
        for code in (1, 128):
            with patch.object(h.subprocess, "run", return_value=subprocess.CompletedProcess([], code, "", "failure")):
                if code == 1:
                    self.assertEqual(h.git("merge-base", allowed=(0, 1)).returncode, 1)
                else:
                    with self.assertRaises(h.InfrastructureError):
                        h.git("merge-base", allowed=(0, 1))

    def test_source_non_ancestry_vs_missing_history(self):
        for code, error_type in [(1, h.IntegrityError), (128, h.InfrastructureError)]:
            def command(arguments, **kwargs):
                if arguments[1] == "merge-base":
                    return subprocess.CompletedProcess(arguments, code, "", "synthetic git failure")
                out = HEAD if arguments[1:] == ["rev-parse", "HEAD"] else h.ACCEPTED_TREE
                return subprocess.CompletedProcess(arguments, 0, out, "")
            with self.subTest(code=code), patch.object(h.subprocess, "run", side_effect=command):
                with self.assertRaises(error_type):
                    h.verify_source(HEAD)

    def test_blob_hash_mismatch_and_missing_file_are_distinct(self):
        path = Path(self.temp.name) / "source.py"
        path.write_bytes(b"synthetic\n")
        self.assertEqual(h.blob_hash(path), hashlib.sha1(b"blob 10\0synthetic\n").hexdigest())
        with self.assertRaises(FileNotFoundError):
            h.blob_hash(path.with_name("absent"))

    def test_preflight_requires_actual_runner_and_exact_event_head(self):
        event = Path(self.temp.name) / "event.json"
        event.write_text(json.dumps({"pull_request": {"head": {"sha": HEAD}}}))
        environment = {"GITHUB_ACTIONS": "true", "RUNNER_NAME": "bandido-alcatraz-ci",
                       "GITHUB_REPOSITORY": h.REPOSITORY, "EXPECTED_HEAD": HEAD,
                       "GITHUB_EVENT_PATH": str(event), "PYTHONHASHSEED": "0"}
        with patch.dict(h.os.environ, environment), patch.object(h, "verify_source", return_value=SOURCE), \
             patch.object(h.sys, "version_info", (3, 11, 15)), \
             patch.object(h.platform, "python_implementation", return_value="CPython"):
            self.assertEqual(h.preflight(HEAD, PREREG), SOURCE)
            with patch.dict(h.os.environ, {"RUNNER_NAME": "wrong", "BANDIDO_RESEARCH_RUNNER": "bandido-alcatraz-ci"}):
                with self.assertRaisesRegex(h.IntegrityError, "unauthorized research runner"):
                    h.preflight(HEAD, PREREG)
            event.write_text(json.dumps({"pull_request": {"head": {"sha": "b" * 40}}}))
            with self.assertRaisesRegex(h.IntegrityError, "PR event head"):
                h.preflight(HEAD, PREREG)
            event.write_text(json.dumps({"pull_request": {"head": {"sha": HEAD}}}))
            with patch.object(h.sys, "version_info", (3, 12, 0)):
                with self.assertRaisesRegex(h.IntegrityError, "CPython 3.11"):
                    h.preflight(HEAD, PREREG)
            with self.assertRaisesRegex(h.IntegrityError, "preregistration mismatch"):
                h.preflight(HEAD, PREREG.replace("5928556762", "1"))

    def test_missing_raw_artifact_is_infrastructure_not_bad_science(self):
        self.make_complete_receipt()
        with patch.object(h, "verify_source", return_value=SOURCE):
            self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "execution_blocked")
        self.assertIsNone(self.receipt()["classification"])

    def test_missing_runner_prerequisites_is_infrastructure(self):
        with patch.dict(h.os.environ, {}, clear=True), self.assertRaises(h.InfrastructureError):
            h.preflight(HEAD, PREREG)

    def test_ignored_stale_bytecode_is_rejected_with_matching_tracked_source(self):
        root = Path(self.temp.name) / "synthetic-repo"
        for name in ("src", "data", "scripts"):
            (root / name).mkdir(parents=True)
        source = root / "src" / "probe.py"
        source.write_text("VALUE='good'\n")
        (root / "data" / "fixture.json").write_text("{}\n")
        (root / h.HARNESS_PATH).write_text("# synthetic harness\n")
        (root / ".gitignore").write_text("__pycache__/\n*.py[cod]\n")
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid",
            "commit", "-qm", "Synthetic source fixture")
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        accepted = head
        (root / h.CANDIDATE_PATH).parent.mkdir(parents=True, exist_ok=True)
        (root / h.CANDIDATE_PATH).write_text("# synthetic isolated candidate\n")
        git("add", ".")
        git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "-qm", "Candidate")
        head = git("rev-parse", "HEAD")
        with patch.object(h, "ROOT", root), patch.object(h, "ACCEPTED_MAIN", accepted), \
             patch.object(h, "ACCEPTED_TREE", tree), patch.object(h, "SCIENTIFIC_FILE_COUNT", 2):
            source_evidence = h.verify_source(head)
            self.assertEqual(source_evidence["head"], head)
            self.assertEqual(source_evidence["harness_sha256"],
                             hashlib.sha256((root / h.HARNESS_PATH).read_bytes()).hexdigest())
            self.assertEqual(source_evidence["python_version"], h.platform.python_version())
            self.assertEqual(source_evidence["python_implementation"], "CPython")
            stat = source.stat()
            source.write_text("VALUE='evil'\n")
            os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            py_compile.compile(str(source), doraise=True)
            source.write_text("VALUE='good'\n")
            os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            self.assertEqual(git("diff", "--", "src"), "")
            self.assertEqual(git("ls-files", "--others", "--exclude-standard", "--", "src"), "")
            with self.assertRaisesRegex(h.IntegrityError, "untracked source/data"):
                h.verify_source(head)

    def test_external_bytecode_cache_cannot_bypass_matching_source_checks(self):
        root = Path(self.temp.name) / "external-cache-repo"
        for name in ("src", "data", "scripts"):
            (root / name).mkdir(parents=True)
        source = root / "src" / "probe.py"
        source.write_text("VALUE='good'\n")
        (root / "data" / "fixture.json").write_text("{}\n")
        (root / h.HARNESS_PATH).write_text("# synthetic harness\n")
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid",
            "commit", "-qm", "Synthetic external-cache fixture")
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        prefix = Path(self.temp.name) / "external-cache"
        environment = {**os.environ, "PYTHONPYCACHEPREFIX": str(prefix),
                       "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src")}
        stat = source.stat()
        source.write_text("VALUE='evil'\n")
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        subprocess.run([h.sys.executable, "-c", "import py_compile,sys; py_compile.compile(sys.argv[1],doraise=True)",
                        str(source)], env=environment, check=True)
        source.write_text("VALUE='good'\n")
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        loaded = subprocess.check_output([h.sys.executable, "-c", "import probe; print(probe.VALUE); print(probe.__file__)"],
                                         env=environment, text=True).splitlines()
        self.assertEqual(loaded, ["evil", str(source)])
        self.assertEqual(git("diff", "--", "src", "data"), "")
        self.assertEqual(git("ls-files", "--others", "--", "src", "data"), "")
        with patch.object(h, "ROOT", root), patch.object(h, "ACCEPTED_MAIN", head), \
             patch.object(h, "ACCEPTED_TREE", tree), patch.object(h.sys, "pycache_prefix", str(prefix)), \
             patch.dict(h.os.environ, {"PYTHONPYCACHEPREFIX": str(prefix)}):
            with self.assertRaisesRegex(h.IntegrityError, "external Python bytecode"):
                h.verify_source(head)

    def test_bytecode_guards_check_environment_runtime_and_precede_scientific_imports(self):
        from bandido_alcatraz import physical_deck
        for prefix, environment, disabled in (("/tmp/external", "", True),
                                               (None, "/tmp/external", True), (None, "", False)):
            with self.subTest(prefix=prefix, environment=environment, disabled=disabled), \
                 patch.object(h.sys, "pycache_prefix", prefix), patch.object(h.sys, "dont_write_bytecode", disabled), \
                 patch.dict(h.os.environ, {"PYTHONPYCACHEPREFIX": environment}), \
                 patch.object(physical_deck, "load_real_deck") as load:
                with self.assertRaises(h.IntegrityError):
                    h.one_game(h.SEEDS[0], output=self.output, pass_number=1)
                load.assert_not_called()

    def test_engine_validation_assertion_and_schema_failures_are_invalid(self):
        for error in (ValueError("illegal move"), AssertionError("no-draw retained-card mapping mismatch"),
                      TypeError("bad result schema"), KeyError("missing field"), AttributeError("bad observation")):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                with patch.object(h, "preflight", return_value=SOURCE), \
                     patch.object(h, "verify_source", return_value=SOURCE), \
                     patch.object(h, "one_game", side_effect=error):
                    self.assertEqual(h.run(output, HEAD, PREREG), 1)
                receipt = h.read_receipt(output)
                self.assertEqual(receipt["status"], "integrity_invalid")
                self.assertEqual(receipt["attempted"], [{"pass": 1, "seed": h.SEEDS[0]}])
                self.assertIsNone(receipt["classification"])
        for error in (OSError("disk full"), PermissionError("access denied"), MemoryError("resource exhausted"),
                      h.InfrastructureError("git unavailable"), ImportError("dependency unavailable")):
            with self.subTest(error=error):
                self.assertFalse(h.integrity_error(error))

    def test_finalizer_preserves_missing_unreadable_and_malformed_receipts(self):
        cases = [(None, None, "execution_blocked"),
                 (b'{"old": "evidence"}\n', PermissionError("receipt inaccessible"), "execution_blocked"),
                 (b'{"status": "running",', None, "integrity_invalid"),
                 (b'[]\n', None, "integrity_invalid")]
        for content, read_error, status in cases:
            with self.subTest(content=content, read_error=read_error), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                output.mkdir()
                original = output / "receipt.json"
                if content is not None:
                    original.write_bytes(content)
                raw = output / "completed.jsonl"
                raw.write_bytes(b'{"previous":"raw evidence"}\n')
                reader = h.read_receipt
                with patch.object(h, "read_receipt", side_effect=read_error or reader):
                    self.assertEqual(h.finalize(output, HEAD, PREREG, "success", "failure"), 1)
                sidecars = list(output.glob("recovery-receipt-*.json"))
                self.assertEqual(len(sidecars), 1)
                recovered = json.loads(sidecars[0].read_text())
                self.assertEqual(recovered["status"], status)
                self.assertIsNone(recovered["attempted"])
                self.assertIsNone(recovered["completed_records"])
                self.assertIsNone(recovered["classification"])
                self.assertFalse(recovered["research_interpretation_performed"])
                self.assertIn("unknown", recovered["execution_extent"])
                if content is None:
                    self.assertFalse(original.exists())
                else:
                    self.assertEqual(original.read_bytes(), content)
                self.assertEqual(raw.read_bytes(), b'{"previous":"raw evidence"}\n')

    def test_returned_result_is_durable_before_missing_duplicate_or_bad_capture(self):
        from bandido_alcatraz import physical_deck, policies, simulate
        for mode in ("missing", "duplicate", "malformed"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                result = GameResult(False, 1, 1, 0, 0, 1, False, "step_limit", h.RULESET, h.SETUP_ID)
                deck = SimpleNamespace(start_for_setup=lambda setup: "synthetic-start", draw_deck=lambda: [])
                def play(**kwargs):
                    if mode == "duplicate":
                        kwargs["policy"].on_game_finished(observation())
                        kwargs["policy"].on_game_finished(observation())
                    elif mode == "malformed":
                        own = observation()
                        broken = SimpleNamespace(board=own.board, setup=own.setup,
                                                 collected_equipment=(SimpleNamespace(material=None),))
                        kwargs["policy"].on_game_finished(broken)
                    return result
                with patch.object(h, "preflight", return_value=SOURCE), \
                     patch.object(h, "verify_source", return_value=SOURCE), \
                     patch.object(physical_deck, "load_real_deck", return_value=deck), \
                     patch.object(policies, "BoundedMergeV4Policy", return_value=SimpleNamespace()), \
                     patch.object(simulate, "play_game", side_effect=play):
                    self.assertEqual(h.run(output, HEAD, PREREG), 1)
                raw = json.loads((output / "raw-results" / "pass-1" / f"{h.SEEDS[0]}.json").read_text())
                self.assertEqual(raw["result"]["reason"], "step_limit")
                self.assertEqual(raw["seed"], h.SEEDS[0])
                self.assertEqual(raw["pass"], 1)
                receipt = h.read_receipt(output)
                self.assertEqual(receipt["status"], "integrity_invalid")
                self.assertEqual(receipt["completed_records"], 0)
                self.assertEqual(len(receipt["attempted"]), 1)
                if mode == "missing":
                    self.assertEqual(raw["public_capture_count"], 0)
                elif mode == "duplicate":
                    self.assertEqual(len(raw["public_captures"]), 2)
                else:
                    self.assertEqual(raw["capture_error"]["type"], "AttributeError")
                    self.assertIn("board", raw["public_captures"][0])
                    self.assertIn("setup", raw["public_captures"][0])

    def test_returned_result_is_saved_before_normalization_is_entered(self):
        from bandido_alcatraz import physical_deck, policies, simulate
        self.initialize()
        result = GameResult(False, 1, 1, 0, 0, 1, False, "step_limit", h.RULESET, h.SETUP_ID)
        deck = SimpleNamespace(start_for_setup=lambda setup: "synthetic-start", draw_deck=lambda: [])
        def play(**kwargs):
            kwargs["policy"].on_game_finished(observation())
            return result
        def normalize(*args, **kwargs):
            raw = json.loads((self.output / "raw-results" / "pass-1" / f"{h.SEEDS[0]}.json").read_text())
            self.assertEqual(raw["result"]["reason"], "step_limit")
            raise AssertionError("synthetic normalization failure")
        with patch.object(physical_deck, "load_real_deck", return_value=deck), \
             patch.object(policies, "BoundedMergeV4Policy", return_value=SimpleNamespace()), \
             patch.object(simulate, "play_game", side_effect=play), \
             patch.object(h, "final_record", side_effect=normalize):
            with self.assertRaisesRegex(AssertionError, "normalization failure"):
                h.one_game(h.SEEDS[0], output=self.output, pass_number=1)

    def test_public_state_and_geometry_mismatches_keep_original_raw_result(self):
        from bandido_alcatraz import physical_deck, policies, simulate
        for changed in ({"open_tunnels": 2}, {"raincoats": 1}):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "attempt"
                result = GameResult(**{**record(h.SEEDS[0])["result"], **changed})
                deck = SimpleNamespace(start_for_setup=lambda setup: "synthetic-start", draw_deck=lambda: [])
                def play(**kwargs):
                    kwargs["policy"].on_game_finished(observation())
                    return result
                with patch.object(physical_deck, "load_real_deck", return_value=deck), \
                     patch.object(policies, "BoundedMergeV4Policy", return_value=SimpleNamespace()), \
                     patch.object(simulate, "play_game", side_effect=play):
                    with self.assertRaisesRegex(h.IntegrityError, "GameResult disagrees"):
                        h.one_game(h.SEEDS[0], output=output, pass_number=1)
                raw = json.loads((output / "raw-results" / "pass-1" / f'{h.SEEDS[0]}.json').read_text())
                for field, value in changed.items():
                    self.assertEqual(raw["result"][field], value)
                self.assertEqual(len(raw["public_captures"]), 1)
                self.assertIn("board", raw["public_captures"][0])

    def test_cli_unknown_mode_or_missing_required_argument_cannot_execute(self):
        with patch.object(h, "one_game") as game, patch("sys.stderr"), self.assertRaises(SystemExit):
            h.main(["run"])
        game.assert_not_called()


# Worker31-specific checks below only call choose on synthetic observations or
# replace play_game. They never execute an outcome-bearing photographed game.

def test_frozen_threshold_and_full_control_digest_are_independent_gates():
    rows = all_rows()
    control = [row['record'] for row in rows[:400]]
    with patch.object(h, 'CONTROL_ARRAY_SHA256', h.digest(control)), patch.object(h, 'CONTROL_WINS', 0):
        for gained in (7, 8):
            changed = copy.deepcopy(rows)
            for phase in (1, 2):
                for index in range(gained):
                    changed[phase * 400 + index]['record'] = quota_record(h.SEEDS[index], 3, 2, won=True)
            summary = h.compare_passes(changed)
            assert summary['net_wins'] == gained
            assert summary['classification'] == (h.ADVANCED_CLASSIFICATION if gained == 8 else h.CLASSIFICATION)
            assert summary['paired_2x2'] == {'both_win': 0, 'control_only': 0, 'candidate_only': gained, 'both_lose': 400-gained}
            assert summary['gained_seed_ids'] == list(h.SEEDS[:gained])
            assert summary['candidate_loss_seed_ids'] == list(h.SEEDS[gained:])
        rows[399]['record']['result']['reason'] = 'deck_exhausted'
        try:
            h.compare_passes(rows)
        except h.IntegrityError as error:
            assert 'complete control normalized array' in str(error)
        else:
            raise AssertionError('full control-array tampering was accepted')


def test_trace_wrapper_uses_only_public_observation_once_and_preserves_rng(tmp_path):
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    from bandido_alcatraz.equipment_opportunity import EquipmentOpportunityTiePolicy, public_observation_record
    from dataclasses import replace
    own = replace(observation(), turns=0, ropes=0, collected_equipment=())
    assert h.public_observation_record(own) == public_observation_record(own)
    for phase, policy in ((1, BoundedMergeV4Policy(setup_weight=250)), (2, EquipmentOpportunityTiePolicy()), (3, EquipmentOpportunityTiePolicy())):
        wrapped = h.AuditPolicy(policy, output=tmp_path, pass_number=phase, seed=h.SEEDS[0])
        rng = Random(17)
        before = rng.getstate()
        with patch.object(PlayerObservation, 'legal_moves', autospec=True, return_value=[]) as legal:
            assert wrapped.choose(own, rng) is None
            assert wrapped.choose(own, rng) is None
        assert legal.call_count == 2
        assert rng.getstate() == before
        events = h.read_trace(wrapped.path)
        assert [event['ordinal'] for event in events] == [1, 1, 2, 2]
        assert [event['observation']['turns'] for event in events[::2]] == [0, 0]
        for forbidden in ('draw_pile', 'private_hands', 'face_down_set_aside'):
            assert forbidden not in h.encoded(events)
        assert ('primary_tier' in events[1]['audit']) == (phase != 1)
        row = h.final_record(h.SEEDS[0], GameResult(False, 0, 1, 0, 0, 0, False, 'no_legal_move', h.RULESET, h.SETUP_ID), own)
        h.append_jsonl(wrapped.path, {'event': 'game_returned', 'result': row['result']})
        h.append_jsonl(wrapped.path, {'event': 'game_completed', 'record_sha256': h.digest(row), 'trace_counts': wrapped.trace_counts()})
        assert h.validate_trace(h.read_trace(wrapped.path), row, phase) == 0
    assert h.read_trace(h.trace_path(tmp_path, 2, h.SEEDS[0])) == h.read_trace(h.trace_path(tmp_path, 3, h.SEEDS[0]))


def test_trace_started_is_durable_before_failed_choice_and_hidden_state_is_rejected(tmp_path):
    from bandido_alcatraz.game import GameState
    class Broken:
        def choose(self, own, rng):
            events = h.read_trace(wrapper.path)
            assert events[0]['event'] == 'decision_started'
            assert events[0]['ordinal'] == 1
            raise RuntimeError('synthetic choice interrupted')
    wrapper = h.AuditPolicy(Broken(), output=tmp_path, pass_number=1, seed=h.SEEDS[0])
    try:
        wrapper.choose(observation(), Random(3))
    except RuntimeError:
        pass
    else:
        raise AssertionError('synthetic failure did not occur')
    assert len(h.read_trace(wrapper.path)) == 1
    state = GameState(observation().board, [], [], setup=GameSetup())
    try:
        wrapper.choose(state, Random(3))
    except TypeError:
        pass
    else:
        raise AssertionError('private GameState was accepted')
    assert len(h.read_trace(wrapper.path)) == 1


def test_candidate_audit_mismatch_is_preserved_before_rejection(tmp_path):
    class BadAudit:
        last_audit = {'unexpected_private_field': 'synthetic-invalid-marker'}
        def choose(self, own, rng):
            return None
    wrapped = h.AuditPolicy(BadAudit(), output=tmp_path, pass_number=2, seed=h.SEEDS[0])
    try:
        wrapped.choose(observation(), Random(0))
    except h.IntegrityError as error:
        assert 'candidate audit disagrees' in str(error)
    else:
        raise AssertionError('malformed audit accepted')
    assert h.read_trace(wrapped.path)[1]['audit'] == BadAudit.last_audit


def test_real_git_checkout_with_actions_context_pins_exactly_one_new_scientific_file(tmp_path, monkeypatch):
    import shutil
    root = tmp_path / 'real-checkout'
    root.mkdir()
    original = Path(h.__file__).parents[1]
    for directory in ('src', 'data'):
        shutil.copytree(original / directory, root / directory, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    candidate = (root / h.CANDIDATE_PATH).read_bytes()
    (root / h.CANDIDATE_PATH).unlink()
    (root / h.HARNESS_PATH).parent.mkdir()
    (root / h.HARNESS_PATH).write_bytes((original / h.HARNESS_PATH).read_bytes())
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
    git('init', '-q')
    git('add', '.')
    git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid', 'commit', '-qm', 'Accepted scientific snapshot')
    accepted, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    (root / h.CANDIDATE_PATH).write_bytes(candidate)
    git('add', '.')
    git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid', 'commit', '-qm', 'Isolated candidate')
    head = git('rev-parse', 'HEAD')
    event = tmp_path / 'event.json'
    event.write_text(json.dumps({'pull_request': {'head': {'sha': head}}}))
    monkeypatch.setattr(h, 'ROOT', root)
    monkeypatch.setattr(h, 'ACCEPTED_MAIN', accepted)
    monkeypatch.setattr(h, 'ACCEPTED_TREE', tree)
    monkeypatch.setattr(h.sys, 'dont_write_bytecode', True)
    monkeypatch.setattr(h.sys, 'pycache_prefix', None)
    monkeypatch.setattr(h.sys, 'version_info', (3, 11, 16))
    for key, value in {'GITHUB_ACTIONS': 'true', 'RUNNER_NAME': 'bandido-alcatraz-ci',
                       'GITHUB_REPOSITORY': h.REPOSITORY, 'EXPECTED_HEAD': head,
                       'GITHUB_RUN_ID': 'synthetic-7', 'GITHUB_RUN_ATTEMPT': '1',
                       'GITHUB_EVENT_PATH': str(event), 'PYTHONHASHSEED': '0', 'PYTHONPYCACHEPREFIX': ''}.items():
        monkeypatch.setenv(key, value)
    evidence = h.preflight(head, PREREG)
    assert len(evidence['source_blobs']) == 26
    assert evidence['candidate_blob'] == git('rev-parse', f'HEAD:{h.CANDIDATE_PATH}')
    assert evidence['candidate_sha256'] == hashlib.sha256(candidate).hexdigest()
    assert evidence['harness_blob'] == git('rev-parse', f'HEAD:{h.HARNESS_PATH}')
    (root / h.CANDIDATE_PATH).write_bytes(candidate + b'\n')
    try:
        h.verify_source(head)
    except h.IntegrityError as error:
        assert 'candidate differs' in str(error)
    else:
        raise AssertionError('candidate worktree mutation accepted')
    (root / h.CANDIDATE_PATH).write_bytes(candidate)
    extra = root / 'src/bandido_alcatraz/second_candidate.py'
    extra.write_text('# forbidden new scientific file\n')
    git('add', '.')
    git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid', 'commit', '-qm', 'Forbidden addition')
    try:
        h.verify_source(git('rev-parse', 'HEAD'))
    except h.IntegrityError as error:
        assert 'only the isolated candidate' in str(error)
    else:
        raise AssertionError('second scientific file accepted')


def test_control_phase_does_not_import_candidate_in_fresh_process(tmp_path):
    root = Path(h.__file__).parents[1]
    code = '''
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import sys
from scripts import run_equipment_opportunity_development as h
from bandido_alcatraz import physical_deck, simulate
from tests.test_equipment_development_harness import observation, record
assert 'bandido_alcatraz.equipment_opportunity' not in sys.modules
def fake_play(**kw):
    kw['policy'].on_game_finished(observation())
    return simulate.GameResult(**record(h.SEEDS[0])['result'])
deck=SimpleNamespace(start_for_setup=lambda s:None, draw_deck=lambda:[])
with patch.object(physical_deck,'load_real_deck',return_value=deck), patch.object(simulate,'play_game',side_effect=fake_play):
    h.one_game(h.SEEDS[0],output=Path(sys.argv[1]),pass_number=1)
assert 'bandido_alcatraz.equipment_opportunity' not in sys.modules
'''
    env = {**os.environ, 'PYTHONPATH': f'{root / "src"}:{root}', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPYCACHEPREFIX': ''}
    subprocess.run([h.sys.executable, '-c', code, str(tmp_path / 'output')], cwd=root, env=env, check=True)


def test_real_synthetic_narrowing_trace_replays_and_tampering_is_rejected(tmp_path):
    import pytest
    from bandido_alcatraz.equipment_opportunity import EquipmentOpportunityTiePolicy
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    from bandido_alcatraz.game import GameState
    board = Board()
    board.seed(CardDefinition('synthetic-start', (CellSpec(0, 0, frozenset({Direction.EAST})),)))
    cards = [CardDefinition('straight', (CellSpec(0, 0, frozenset({Direction.WEST, Direction.EAST})),), Material.ROPE),
             CardDefinition('closure', (CellSpec(0, 0, frozenset({Direction.WEST})),), Material.ROPE)]
    own = GameState(board, [], cards, setup=GameSetup()).observation()
    seed = h.SEEDS[0]
    rows = []
    for phase in h.PASSES:
        policy = BoundedMergeV4Policy(setup_weight=250) if phase == 1 else EquipmentOpportunityTiePolicy()
        wrapper = h.AuditPolicy(policy, output=tmp_path, pass_number=phase, seed=seed)
        wrapper.choose(own, Random(0))
        row = record(seed)
        rows.append({'pass': phase, 'record': row})
        sidecar(tmp_path, phase, row)
        h.append_jsonl(wrapper.path, {'event': 'game_returned', 'result': row['result']})
        h.append_jsonl(wrapper.path, {'event': 'game_completed', 'record_sha256': h.digest(row), 'trace_counts': wrapper.trace_counts()})
    with patch.object(h, 'SEEDS', (seed,)):
        summary = h.verify_traces(tmp_path, rows)
    assert summary['candidate_strict_tier_narrowings'] == 1
    assert summary['matched_observation_rng_decisions'] == 1
    assert summary['candidate_replay_trace_matches'] == 1
    events = h.read_trace(h.trace_path(tmp_path, 2, seed))
    audit = events[1]['audit']
    assert audit['strict_narrowing'] is True
    assert [x['opportunity_score'] for x in audit['collection_opportunities']] == [0, -999900]
    broken = copy.deepcopy(events)
    broken[1]['audit']['narrowed_tier'] = audit['primary_tier']
    broken[1]['audit']['narrowed_tier_count'] = 2
    broken[1]['audit']['narrowed_tier_sha256'] = h.digest(audit['primary_tier'])
    with pytest.raises(h.IntegrityError, match='frozen rule'):
        h.validate_trace(broken, row, 2)
    broken = copy.deepcopy(events)
    broken[1]['audit']['rng_after_sha256'] = 'f' * 64
    h.trace_path(tmp_path, 3, seed).write_text(''.join(h.encoded(e) for e in broken))
    with patch.object(h, 'SEEDS', (seed,)), pytest.raises(h.IntegrityError, match='differ across replay'):
        h.verify_traces(tmp_path, rows)


def test_unreadable_receipt_cannot_mask_known_test_failure(tmp_path):
    output = tmp_path / 'attempt'
    with patch.object(h, 'read_receipt', side_effect=PermissionError('synthetic unreadable receipt')):
        assert h.finalize(output, HEAD, PREREG, 'failure', 'skipped') == 1
    recovered = json.loads(next(output.glob('recovery-receipt-*.json')).read_text())
    assert recovered['status'] == 'integrity_invalid'
    assert any(error['phase'] == 'tests' for error in recovered['errors'])
    assert recovered['completed_records'] is None
    assert recovered['observed_source_at_failed_finalization']


def test_cli_rejects_empty_root_checkout_and_ancestor_before_any_io():
    for path in ('', ' ', '.', '/', str(h.ROOT), str(h.ROOT / 'evidence'), str(h.ROOT.parent)):
        for mode in ('initialize', 'run', 'finalize'):
            with patch.object(h, mode) as operation, patch('sys.stderr'):
                assert h.main([mode, '--output-dir', path, '--expected-head', HEAD, '--preregistration-url', PREREG]) == 1
            operation.assert_not_called()


def test_actions_output_path_is_exact_bounded_attempt_and_rejects_symlinks(tmp_path, monkeypatch):
    import pytest
    base = tmp_path / 'checkout'
    base.mkdir()
    monkeypatch.setenv('GITHUB_WORKSPACE', str(base))
    monkeypatch.setenv('GITHUB_RUN_ID', '23')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2')
    expected = base.parent / 'bandido-equipment-development/23/2'
    assert h.safe_output_path(str(expected), actions=True) == expected
    assert h.safe_output_path(str(base / '../bandido-equipment-development/23/2'), actions=True) == expected
    for path in (base, expected.parent, expected / 'extra', tmp_path / 'other', Path('/')):
        with pytest.raises(h.IntegrityError):
            h.safe_output_path(str(path), actions=True)
    expected.parent.mkdir(parents=True)
    target = tmp_path / 'unrelated'
    target.mkdir()
    expected.symlink_to(target, target_is_directory=True)
    with pytest.raises(h.IntegrityError, match='nonsymlinked'):
        h.safe_output_path(str(expected), actions=True)


def test_canonical_record_sidecar_and_trace_equality_reject_numeric_type_mutations(tmp_path):
    import pytest
    assert not h.exact_json(0, False)
    assert not h.exact_json(0, 0.0)
    rows = all_rows()
    mutated = copy.deepcopy(rows)
    mutated[-1]['record']['board']['placements'][0]['placement_index'] = 0.0
    assert mutated == rows  # Documents precisely why Python == was insufficient.
    with patch.object(h, 'validate_record'), pytest.raises(h.IntegrityError, match='differ across candidate replay'):
        h.compare_passes(mutated)
    row = record(h.SEEDS[0])
    sidecar(tmp_path, 1, row)
    path = tmp_path / 'raw-results/pass-1' / f'{h.SEEDS[0]}.json'
    raw = json.loads(path.read_text())
    before = copy.deepcopy(raw)
    raw['result']['raincoats'] = False
    assert raw == before
    h.write_json(path, raw)
    with pytest.raises(h.IntegrityError, match='raw sidecar disagrees'):
        h.verify_raw_sidecars(tmp_path, [{'pass': 1, 'record': row}])
    for phase in h.PASSES:
        sidecar(tmp_path, phase, row)
        synthetic_trace(tmp_path, phase, row['seed'])
    replay_path = h.trace_path(tmp_path, 3, row['seed'])
    events = h.read_trace(replay_path)
    before = copy.deepcopy(events)
    events[-2]['result']['turns'] = 1.0
    assert events == before
    replay_path.write_text(''.join(h.encoded(event) for event in events))
    with patch.object(h, 'SEEDS', (row['seed'],)), patch.object(h, 'validate_trace', return_value=0), \
         pytest.raises(h.IntegrityError, match='traces differ across replay'):
        h.verify_traces(tmp_path, [{'pass': p, 'record': row} for p in h.PASSES])


def test_trace_turn_accounting_rejects_missing_non_null_actions_and_wrong_observation_turns(tmp_path):
    import pytest
    seed = h.SEEDS[0]
    synthetic_trace(tmp_path, 1, seed)
    events = h.read_trace(h.trace_path(tmp_path, 1, seed))
    row = record(seed)
    missing = copy.deepcopy(events[-2:])
    missing[-1]['trace_counts'] = {'decision_count': 0, 'non_null_choices': 0}
    with pytest.raises(h.IntegrityError, match='non-null choices disagree'):
        h.validate_trace(missing, row, 1)
    wrong = copy.deepcopy(events)
    wrong[0]['observation']['turns'] = 1
    wrong[1]['audit']['public_observation_sha256'] = h.digest(wrong[0]['observation'])
    with pytest.raises(h.IntegrityError, match='preceding non-null choices'):
        h.validate_trace(wrong, row, 1)


def test_omitted_no_move_pair_detected_by_durable_wrapper_count_and_raw_sidecar(tmp_path):
    import pytest
    from dataclasses import replace
    from bandido_alcatraz.policies import BoundedMergeV4Policy
    from bandido_alcatraz.equipment_opportunity import EquipmentOpportunityTiePolicy
    own = replace(observation(), turns=0, ropes=0, collected_equipment=())
    seed = h.SEEDS[0]
    row = h.final_record(seed, GameResult(False, 0, 1, 0, 0, 0, False, 'no_legal_move', h.RULESET, h.SETUP_ID), own)
    for phase in h.PASSES:
        policy = BoundedMergeV4Policy(setup_weight=250) if phase == 1 else EquipmentOpportunityTiePolicy()
        wrapper = h.AuditPolicy(policy, output=tmp_path, pass_number=phase, seed=seed)
        rng = Random(0)
        assert wrapper.choose(own, rng) is None
        assert wrapper.choose(own, rng) is None
        sidecar(tmp_path, phase, row, wrapper.trace_counts())
        h.append_jsonl(wrapper.path, {'event': 'game_returned', 'result': row['result']})
        h.append_jsonl(wrapper.path, {'event': 'game_completed', 'record_sha256': h.digest(row), 'trace_counts': wrapper.trace_counts()})
    path = h.trace_path(tmp_path, 1, seed)
    events = h.read_trace(path)
    omitted = copy.deepcopy(events[2:])
    omitted[0]['ordinal'] = omitted[1]['ordinal'] = 1
    with pytest.raises(h.IntegrityError, match='decision count'):
        h.validate_trace(omitted, row, 1)
    omitted[-1]['trace_counts']['decision_count'] = 1
    path.write_text(''.join(h.encoded(event) for event in omitted))
    with patch.object(h, 'SEEDS', (seed,)), pytest.raises(h.IntegrityError, match='raw returned-result sidecar'):
        h.verify_traces(tmp_path, [{'pass': p, 'record': row} for p in h.PASSES])


def test_nested_public_trace_schema_and_scalar_types_reject_rehashed_hidden_fields(tmp_path):
    import pytest
    seed = h.SEEDS[0]
    synthetic_trace(tmp_path, 1, seed)
    original = h.read_trace(h.trace_path(tmp_path, 1, seed))
    mutations = [
        lambda o, a: o['board'].update(hidden_draw_order=['secret']),
        lambda o, a: o['board']['cells'][0].update(hidden_draw_order=['secret']),
        lambda o, a: o['board']['placements'][0].update(hidden_draw_order=['secret']),
        lambda o, a: o['board']['placements'][0].update(quarter_turns=False),
        lambda o, a: o['board']['placements'][0]['origin'].__setitem__(0, 0.0),
        lambda o, a: o['board']['cells'][0].update(water=0),
        lambda o, a: o['board']['cells'][0].update(x=False),
        lambda o, a: o['hand'][0].update(hidden_draw_order=['secret']),
        lambda o, a: o['hand'][0]['cells'][0].update(hidden_draw_order=['secret']),
        lambda o, a: o['hand'][0].update(is_exit=0),
        lambda o, a: o['hand'][0]['cells'][0].update(water=0.0),
        lambda o, a: o['hand'][0]['cells'][0].update(tunnel_edges=[True]),
        lambda o, a: o['setup'].update(hand_size=6.0),
        lambda o, a: o['setup'].update(player_count=True),
        lambda o, a: o.update(set_aside_unplayable=False),
        lambda o, a: o.update(exit_seen=0),
        lambda o, a: a['chosen_move'].update(hidden_draw_order=['secret']),
        lambda o, a: a['chosen_move'].update(hand_index=False),
        lambda o, a: a['chosen_move'].update(quarter_turns=0.0),
        lambda o, a: a['chosen_move'].update(action='place', origin=[0.0, 1]),
        lambda o, a: o['collected_equipment'].append({'card': o['hand'][0], 'turn': 0, 'player_index': 0, 'hidden': []}),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(original)
        public, audit = changed[0]['observation'], changed[1]['audit']
        mutate(public, audit)
        audit['public_observation_sha256'] = h.digest(public)
        with pytest.raises(h.IntegrityError):
            h.validate_trace(changed, record(seed), 1)
    synthetic_trace(tmp_path, 2, seed)
    candidate = h.read_trace(h.trace_path(tmp_path, 2, seed))
    candidate[1]['audit']['primary_tier'][0]['hand_index'] = False
    candidate[1]['audit']['primary_tier_sha256'] = h.digest(candidate[1]['audit']['primary_tier'])
    with pytest.raises(h.IntegrityError, match='move hand index'):
        h.validate_trace(candidate, record(seed), 2)
