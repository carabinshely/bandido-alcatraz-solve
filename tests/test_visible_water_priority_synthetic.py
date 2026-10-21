"""Synthetic policy wiring only: no deck, game run, or scientific seed."""

from pathlib import Path
from random import Random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.strategy import MoveFeatures
from bandido_alcatraz import strategy, visible_water_priority as candidate
from bandido_alcatraz import visible_water_priority_reference as reference


class VisibleWaterPrioritySyntheticTests(unittest.TestCase):
    def test_candidate_and_independent_reference_select_water_cover(self):
        public = PlayerObservation(Board(), (), 0, 0, False, False, 0, 0, (), None)
        features = {0: MoveFeatures(delta_visible_water=1),
                    1: MoveFeatures(delta_open_tunnels=300)}
        patches = [
            patch.object(PlayerObservation, "legal_moves", lambda _: [0, 1]),
            patch.object(candidate, "move_features_no_draw", lambda _, move: features[move]),
            patch.object(strategy, "move_features_no_draw", lambda _, move: features[move]),
            patch.object(candidate, "observation_wire", lambda _: {"synthetic": True}),
            patch.object(reference, "observation_wire", lambda _: {"synthetic": True}),
            patch.object(candidate, "move_wire", lambda move: move),
            patch.object(reference, "move_wire", lambda move: move),
        ]
        for item in patches:
            item.start()
        try:
            policy = candidate.VisibleWaterPriorityPolicy()
            self.assertEqual(policy.v4_weights.delta_visible_water, 20_000)
            self.assertEqual(policy.candidate_weights.delta_visible_water, 100_000)
            left = policy.evaluate(public, Random(77))
            right = reference.VisibleWaterPriorityReference().evaluate(public, Random(77))
            self.assertEqual(left[0], 0)
            self.assertEqual(right[0], 0)
            self.assertEqual(left[1], right[1])
            self.assertEqual(left[1]["tiers"], {"v4_top": [1], "final": [0]})
            self.assertEqual(left[1]["roots"][0]["score"], 100_000)
        finally:
            for item in reversed(patches):
                item.stop()


if __name__ == "__main__":
    unittest.main()
