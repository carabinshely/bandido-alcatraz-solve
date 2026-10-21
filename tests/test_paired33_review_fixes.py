"""Synthetic boundary and analysis checks; no game or seed is run."""
import ast
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOUNDS = ROOT / "experiments/paired33/bounds.py"
DIAGNOSTIC = ROOT / "experiments/paired33/diagnostic.py"
spec = importlib.util.spec_from_file_location("paired33_bounds", BOUNDS)
bounds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bounds)


class ReviewFixTests(unittest.TestCase):
    def test_pre_call_reserves_writer_terminal_bytes_and_overhead(self):
        self.assertEqual(bounds.TERMINAL_RESERVE, 4 * 1024 * 1024)
        total = 8 * 1024 * 1024
        upcoming = 30_000
        bounds.reserve(0, upcoming, total)
        with self.assertRaisesRegex(ValueError, "EVIDENCE_CAP_BEFORE_CALL"):
            bounds.reserve(total - bounds.TERMINAL_RESERVE - upcoming - 31,
                           upcoming, total)

    def test_global_record_slots_veto_before_policy_call(self):
        bounds.reserve_records(65_530, 6, 65_536)
        with self.assertRaisesRegex(ValueError, "RECORD_CAP_BEFORE_CALL"):
            bounds.reserve_records(65_531, 6, 65_536)
        source = DIAGNOSTIC.read_text(encoding="utf-8")
        self.assertIn("bounds.reserve_records(len(evidence.names), 6, codec.MAX_RECORDS)", source)

    def test_paired_win_rate_difference_is_normalized(self):
        tree = ast.parse(DIAGNOSTIC.read_text(encoding="utf-8"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "paired_analysis")
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(DIAGNOSTIC), "exec"),
             namespace)
        pairs = []
        for index in range(100):
            pairs.append(dict(results=[
                dict(arm="control", result=dict(won=False), terminal_open_tunnels=1,
                     choice_changes=0),
                dict(arm="candidate", result=dict(won=index < 10),
                     terminal_open_tunnels=1, choice_changes=0)]))
        result = namespace["paired_analysis"](pairs)
        self.assertEqual(result["paired_net_wins"], 10)
        self.assertEqual(result["paired_win_rate_difference"], 0.1)


if __name__ == "__main__":
    unittest.main()
