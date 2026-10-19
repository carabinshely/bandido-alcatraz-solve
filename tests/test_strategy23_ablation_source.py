"""Source-only isolation check; deliberately does not import or run game policy."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "src" / "bandido_alcatraz"


class FloorOnlySourceIsolation(unittest.TestCase):
    def test_candidate_removes_only_late_weight(self):
        late = (ROOT / "late_closure.py").read_text()
        floor = (ROOT / "floor_only.py").read_text()
        expected = late.replace(
            '"""Prospective public-turn closure pressure over the V4-250 floor candidate."""',
            '"""Prospective two-open mobility floor with unchanged V4-250 scoring."""',
        ).replace("from dataclasses import replace\n", "").replace(
            "LateClosurePolicy", "FloorOnlyPolicy"
        ).replace(
            "            if observation.turns >= 20:\n"
            "                weights = replace(weights, delta_open_tunnels=1000)\n", ""
        ).replace("strategy22-late-closure-v1", "strategy23-floor-only-v1")
        self.assertEqual(floor, expected)
        ast.parse(floor)

    def test_independent_reference_keeps_original_weight(self):
        late = (ROOT / "late_closure_reference.py").read_text()
        floor = (ROOT / "floor_only_reference.py").read_text()
        expected = late.replace(
            '"""Independent strategy22 closure-weight calculation over the public validator."""',
            '"""Independent strategy23 unchanged-weight floor calculation."""',
        ).replace("LateClosureReference", "FloorOnlyReference").replace(
            "delta_open_tunnels=1000 if obs.turns >= 20 else 100",
            "delta_open_tunnels=100",
        ).replace("strategy22-late-closure-v1", "strategy23-floor-only-v1")
        self.assertEqual(floor, expected)
        ast.parse(floor)


if __name__ == "__main__":
    unittest.main()
