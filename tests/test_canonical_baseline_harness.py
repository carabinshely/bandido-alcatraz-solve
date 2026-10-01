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

from scripts import run_canonical_baseline as h
from bandido_alcatraz.board import Board
from bandido_alcatraz.game import CollectedEquipment, PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.setup import GameSetup
from bandido_alcatraz.simulate import GameResult

HEAD = "a" * 40
PREREG = "https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5927438161"
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


def sidecar(output, pass_number, row):
    path = output / "raw-results" / f"pass-{pass_number}" / f'{row["seed"]}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    h.write_json(path, {"pass": pass_number, "seed": row["seed"], "result": row["result"],
                        "public_capture_count": 1, "public_captures": [row]})


class BaselineHarnessTests(unittest.TestCase):
    def setUp(self):
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
            return row
        with patch.object(h, "preflight", side_effect=preflight, return_value=SOURCE), \
             patch.object(h, "verify_source", return_value=SOURCE), \
             patch.object(h, "one_game", side_effect=mocked_game), patch("builtins.print"):
            return h.run(self.output, HEAD, PREREG)

    def test_exact_frozen_population_and_default_setup(self):
        self.assertEqual(h.SEEDS, tuple(range(1000000, 1000400)))
        self.assertEqual(h.PASSES, (1, 2))
        self.assertEqual(GameSetup().setup_id, h.SETUP_ID)
        self.assertEqual(h.ACCEPTED_MAIN, "d357a01bed0cccb34bae3c440cc7201ef39a2a84")
        self.assertEqual(h.ACCEPTED_TREE, "8f694dfff0999ba57015a6fdb2bcfc05793cf063")
        self.assertEqual(h.RULESET, "v2-exact-equipment-quota-limited-collect-full-hand-refresh")
        self.assertEqual(h.PREREGISTRATION_URL, PREREG)
        self.assertEqual(h.MAX_STEPS, 1000)
        self.assertEqual(h.CLASSIFICATION, "canonical_quota_limited_solo_baseline_reproduced")

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
        self.assertEqual(calls, list(h.SEEDS) * 2)
        receipt = self.receipt()
        self.assertEqual(receipt["completed_records"], 800)
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
        self.assertEqual(receipt["worker"], 30)

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
        self.assertEqual(self.receipt()["completed_records"], 800)
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
            h.one_game(h.SEEDS[0], output=self.output, pass_number=2)
            for seed in (999999, 1000400, True, "1000000"):
                with self.assertRaises(h.IntegrityError):
                    h.one_game(seed, output=self.output, pass_number=1)
        self.assertEqual(len(decks), 2)
        self.assertIsNot(policies_created[0], policies_created[1])
        self.assertIsNot(arguments[0]["deck"], arguments[1]["deck"])
        self.assertEqual(arguments[0]["seed"], arguments[1]["seed"])
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
        self.assertEqual(h.finalize(self.output, HEAD, PREREG, "success", "success"), 1)
        self.assertEqual(self.receipt()["status"], "execution_blocked")
        receipt = self.receipt()
        receipt["status"] = "integrity_invalid"
        h.write_json(self.output / "receipt.json", receipt)
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
                self.assertEqual(after["completed_records"], 800)
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
                h.preflight(HEAD, PREREG.replace("5927438161", "1"))

    def test_missing_raw_artifact_is_infrastructure_not_bad_science(self):
        self.make_complete_receipt()
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
        with patch.object(h, "ROOT", root), patch.object(h, "ACCEPTED_MAIN", head), \
             patch.object(h, "ACCEPTED_TREE", tree):
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


if __name__ == "__main__":
    unittest.main()
