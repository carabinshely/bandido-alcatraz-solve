"""Focused synthetic scoring checks; no game, deck, or scientific seed runs."""

import unittest
from random import Random
from unittest.mock import patch

from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.phase_closure import PhaseClosureV7Policy
from bandido_alcatraz.phase_closure_reference import PhaseClosureV7Reference
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.strategy import MoveFeatures
import bandido_alcatraz.phase_closure as phase
import bandido_alcatraz.phase_closure_reference as oracle


class PhaseClosureTests(unittest.TestCase):
    def test_boundary_and_changed_choice(self):
        moves = [Move(Action.PLACE, 0), Move(Action.PLACE, 1)]
        # V4 prefers a bounded merge gain (250) over two closures (200),
        # while the late rule values those closures at 10,000.
        features = [
            MoveFeatures(delta_open_tunnels=0, bounded_merge_setup_gain=1),
            MoveFeatures(delta_open_tunnels=2),
        ]
        # A bounded merge gain scores 250, so V4 chooses move 0; late
        # closure scores 10,000 and chooses move 1.
        for turns, expected in ((19, moves[0]), (20, moves[1])):
            state = PlayerObservation(None, (), 0, 0, False, False,
                                      turns, 0, (), None)
            with self.subTest(turns=turns), \
                 patch.object(PlayerObservation, "legal_moves", return_value=moves), \
                 patch.object(phase, "move_features_no_draw", side_effect=features):
                self.assertEqual(PhaseClosureV7Policy().choose(state, Random(4)), expected)

    def test_exact_v4_weights_and_empty_hand(self):
        policy = PhaseClosureV7Policy()
        self.assertEqual(policy.weights, BoundedMergeV4Policy(250).weights)
        self.assertEqual(policy.late_weights.delta_open_tunnels, 5_000)
        self.assertEqual(policy.late_weights.wins, 1_000_000)
        self.assertEqual(policy.late_weights.closes_last_without_win, -1_000_000)
        state = PlayerObservation(None, (), 0, 0, False, False,
                                  20, 0, (), None)
        with patch.object(PlayerObservation, "legal_moves", return_value=[]), \
             patch.object(phase, "move_features_no_draw", side_effect=AssertionError):
            self.assertIsNone(policy.choose(state, Random(4)))

    def test_candidate_and_independent_reference_match_wire_audit(self):
        state = PlayerObservation(None, (), 0, 0, False, False,
                                  20, 0, (), None)
        moves = [Move(Action.PLACE, 0), Move(Action.PLACE, 1)]
        features = [MoveFeatures(bounded_merge_setup_gain=1),
                    MoveFeatures(delta_open_tunnels=2)]
        with patch.object(PlayerObservation, "legal_moves", return_value=moves), \
             patch.object(phase, "observation_wire", return_value={"synthetic": True}), \
             patch.object(oracle, "observation_wire", return_value={"synthetic": True}), \
             patch.object(phase, "move_features_no_draw", side_effect=features), \
             patch.object(oracle.strategy, "move_features_no_draw", side_effect=features):
            actual = PhaseClosureV7Policy().evaluate(state, Random(7))
            expected = PhaseClosureV7Reference().evaluate(state, Random(7))
        self.assertEqual(actual, expected)
        self.assertEqual(actual[1]["chosen_index"], 1)
        self.assertEqual(actual[1]["tiers"], {"v4_top": [0], "final": [1]})

    def test_empty_late_audit_matches_reference(self):
        state = PlayerObservation(None, (), 0, 0, False, False,
                                  20, 0, (), None)
        with patch.object(PlayerObservation, "legal_moves", return_value=[]), \
             patch.object(phase, "observation_wire", return_value={"synthetic": True}), \
             patch.object(oracle, "observation_wire", return_value={"synthetic": True}):
            actual = PhaseClosureV7Policy().evaluate(state, Random(7))
            expected = PhaseClosureV7Reference().evaluate(state, Random(7))
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
