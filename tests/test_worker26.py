"""Synthetic tests only: no photographed-deck game or research seed is run."""
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import Future
from unittest.mock import patch

from scripts import run_worker26 as w
from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction

class Rng:
    def __init__(self): self.calls = []
    def choice(self, values):
        self.calls.append(list(values))
        return values[0]

class Hidden:
    def fail(self, *args, **kwargs): raise AssertionError("hidden draw access")
    __iter__ = __len__ = __getitem__ = __bool__ = copy = pop = fail

def card(name, directions):
    return CardDefinition(name, (CellSpec(0, 0, frozenset(directions)),))

class CandidateTests(unittest.TestCase):
    def test_lexicographic_tie_and_order_and_one_rng(self):
        rng = Rng()
        with patch.object(w, "best_two_action_first_moves", return_value=["c", "a", "b"]), patch.object(w, "score_move_no_draw", side_effect=[2, 5, 5]):
            self.assertEqual(w.ImmediateTieV7Policy().choose(object(), rng), "a")
        self.assertEqual(rng.calls, [["a", "b"]])

    def test_no_action_uses_no_rng(self):
        rng = Rng()
        with patch.object(w, "best_two_action_first_moves", return_value=[]):
            self.assertIsNone(w.ImmediateTieV7Policy().choose(object(), rng))
        self.assertEqual(rng.calls, [])

    def test_no_hidden_draw_or_source_mutation(self):
        board = Board(); board.seed(card("start", {Direction.EAST}))
        state = GameState(board=board, draw_pile=Hidden(), hand=[card("end", {Direction.WEST}), card("a", set()), card("b", set())])
        before = (state.board.open_tunnels, list(state.hand), state.turns)
        rng = Rng(); move = w.ImmediateTieV7Policy().choose(state, rng)
        self.assertIn(move, state.legal_moves())
        self.assertEqual(len(rng.calls), 1)
        self.assertEqual(before, (state.board.open_tunnels, list(state.hand), state.turns))

    def test_out_of_scope_rejected_before_compute(self):
        with patch.object(w, "play_game", side_effect=AssertionError("must not simulate")):
            with self.assertRaises(w.IntegrityError): w.one_game(("v7", 999))

    def test_population_and_fixed_gate(self):
        a = [{"seed": s, "won": False} for s in w.SEEDS]
        b = [dict(r) for r in a]
        b[0]["won"] = True
        self.assertFalse(w.summarize(a, b)["advance"])
        b[1]["won"] = True
        self.assertTrue(w.summarize(a, b)["advance"])
        with self.assertRaises(w.IntegrityError): w.summarize(a, b[:-1])
        with self.assertRaises(w.IntegrityError): w.summarize(a, b[::-1])

    def check_failure(self, error, expected):
        with tempfile.TemporaryDirectory() as tmp, patch.object(w, "preflight", side_effect=error), patch.object(w, "one_game", side_effect=AssertionError("must not simulate")), patch("sys.argv", ["test", "--execute", "--output", tmp]):
            self.assertEqual(w.main(), 1)
            receipt = json.loads((Path(tmp) / "receipt.json").read_text())
            self.assertEqual(receipt["status"], expected)
            self.assertEqual(receipt["completed_policy_seed_records"], 0)
            self.assertEqual(receipt["submitted_candidate_seeds"], [])
            self.assertFalse(receipt["research_interpretation_performed"])
            return receipt

    def test_inaccessible_input_is_blocker(self):
        receipt = self.check_failure(FileNotFoundError("input absent"), "execution_blocked")
        self.assertIsNone(receipt["classification"])

    def test_integrity_failure_is_invalid(self):
        self.check_failure(w.IntegrityError("source mismatch"), "diagnostic_invalid")

    def test_corrupt_json_is_invalid(self):
        self.check_failure(json.JSONDecodeError("corrupt", "x", 0), "diagnostic_invalid")

    def test_baseline_mismatch_prevents_candidate(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(w, "preflight", return_value=([{"seed": 1000, "won": True}], {})), patch.object(w, "one_game", return_value={"seed": 1000, "won": False}) as game, patch.object(w, "ProcessPoolExecutor", side_effect=AssertionError("candidate must not start")), patch("sys.argv", ["test", "--execute", "--output", tmp]):
            self.assertEqual(w.main(), 1)
            self.assertEqual(game.call_count, 1)
            r = json.loads((Path(tmp) / "receipt.json").read_text())
            self.assertEqual(r["status"], "diagnostic_invalid")
            self.assertEqual(r["submitted_candidate_seeds"], [])
            self.assertFalse(r["research_interpretation_performed"])

    def test_partial_submission_drains_completed_record(self):
        class Pool:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def submit(self, fn, task):
                if task[1] == 1001: raise OSError("scheduler unavailable")
                f = Future(); f.set_result({"seed": task[1], "won": False}); return f
        expected = [{"seed": s, "won": False} for s in w.SEEDS]
        with tempfile.TemporaryDirectory() as tmp, patch.object(w, "preflight", return_value=(expected, {})), patch.object(w, "one_game", side_effect=lambda t: {"seed": t[1], "won": False}), patch.object(w, "ProcessPoolExecutor", return_value=Pool()), patch("sys.argv", ["test", "--execute", "--output", tmp]):
            self.assertEqual(w.main(), 1)
            r = json.loads((Path(tmp)/"receipt.json").read_text())
            self.assertEqual(r["status"], "execution_blocked")
            self.assertIsNone(r["classification"])
            self.assertEqual(r["submission_attempted_seeds"], [1000,1001])
            self.assertEqual(r["submitted_candidate_seeds"], [1000])
            self.assertEqual(r["v7"], [{"seed":1000,"won":False}])
            self.assertEqual(r["completed_policy_seed_records"], 101)
            self.assertFalse(r["research_interpretation_performed"])

    def test_future_infrastructure_vs_integrity(self):
        for error, status in [(OSError("disk"), "execution_blocked"), (w.IntegrityError("bad score"), "diagnostic_invalid")]:
            class Pool:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def submit(self, fn, task):
                    f=Future()
                    if task[1] == 1000: f.set_exception(error)
                    else: f.set_result({"seed":task[1],"won":False})
                    return f
            expected = [{"seed":s,"won":False} for s in w.SEEDS]
            with tempfile.TemporaryDirectory() as tmp, patch.object(w,"preflight",return_value=(expected,{})), patch.object(w,"one_game",side_effect=lambda t:{"seed":t[1],"won":False}), patch.object(w,"ProcessPoolExecutor",return_value=Pool()), patch("sys.argv",["test","--execute","--output",tmp]):
                self.assertEqual(w.main(),1)
                r=json.loads((Path(tmp)/"receipt.json").read_text())
                self.assertEqual(r["status"],status)
                self.assertEqual(len(r["v7"]),99)
                self.assertFalse(r["research_interpretation_performed"])

    def test_timeout_finalizer_preserves_partial_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); w.write_json(p/"receipt.json", {"status":"running","v7":[{"seed":1000}],"completed_policy_seed_records":101})
            w.finalize(p,"failure","success")
            r=json.loads((p/"receipt.json").read_text())
            self.assertEqual(r["status"],"execution_blocked")
            self.assertIsNone(r["classification"])
            self.assertEqual(r["v7"],[{"seed":1000}])
            self.assertFalse(r["research_interpretation_performed"])
            w.write_json(p/"receipt.json", {"status":"complete","marker":1})
            w.finalize(p,"success","success")
            self.assertEqual(json.loads((p/"receipt.json").read_text()),{"status":"complete","marker":1})

    def test_dirty_harness_is_invalid_before_seed_execution(self):
        with patch.object(w,"git",side_effect=["dirty","committed"]), patch.object(w,"one_game",side_effect=AssertionError("no research")):
            with self.assertRaisesRegex(w.IntegrityError,"harness differs"):
                w.verify_harness_binding()
        with patch.object(w,"git",side_effect=["same","same"]):
            self.assertEqual(w.verify_harness_binding(),"same")

    def test_reused_output_preserves_old_attempt_without_mixing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); old_receipt=b'{"status":"execution_blocked"}\n'; old_journal=b'{"old":"record"}\n'
            (p/"receipt.json").write_bytes(old_receipt); (p/"completed.jsonl").write_bytes(old_journal)
            with patch.object(w,"preflight",side_effect=OSError("input inaccessible")), patch.object(w,"one_game",side_effect=AssertionError("no research")), patch("sys.argv",["test","--execute","--output",tmp]):
                self.assertEqual(w.main(),1)
            r=json.loads((p/"receipt.json").read_text()); archived=p/r["preserved_previous_attempt"]
            self.assertEqual((archived/"receipt.json").read_bytes(),old_receipt)
            self.assertEqual((archived/"completed.jsonl").read_bytes(),old_journal)
            self.assertFalse((p/"completed.jsonl").exists())
            self.assertEqual(r["completed_policy_seed_records"],0)

    def test_late_save_and_reporting_failures_clear_interpretation(self):
        expected=[{"seed":s,"won":False} for s in w.SEEDS]
        class Pool:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def submit(self,fn,task):
                f=Future(); f.set_result({"seed":task[1],"won":task[1] in (1000,1001)}); return f
        for failure in ("print", "save"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                original=w.write_json
                def write(path, value):
                    if failure=="save" and value.get("status")=="complete": raise OSError("final save failed")
                    original(path,value)
                with patch.object(w,"preflight",return_value=(expected,{})), patch.object(w,"one_game",side_effect=lambda t:{"seed":t[1],"won":False}), patch.object(w,"ProcessPoolExecutor",return_value=Pool()), patch.object(w,"write_json",side_effect=write), patch("builtins.print",side_effect=BrokenPipeError("stdout closed") if failure=="print" else None), patch("sys.argv",["test","--execute","--output",tmp]):
                    self.assertEqual(w.main(),1)
                r=json.loads((Path(tmp)/"receipt.json").read_text())
                self.assertEqual(r["completed_policy_seed_records"],200)
                self.assertEqual(r["status"],"execution_blocked")
                self.assertIsNone(r["classification"])
                self.assertFalse(r["research_interpretation_performed"])
                self.assertNotIn("summary",r)

if __name__ == "__main__": unittest.main()
