"""Narrow synthetic policy mechanics; no game or scientific seed is run."""

import unittest
from random import Random
from unittest.mock import patch

from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.phase_capacity_tie import PhaseCapacityTiePolicy
from bandido_alcatraz.strategy import MoveFeatures
import bandido_alcatraz.phase_capacity_tie as phase


def observation(*, raincoats=0, ropes=0, exit_placed=False):
    return PlayerObservation(None, (), raincoats, ropes, exit_placed, False,
                             0, 0, (), None)


class PhaseCapacityTieTests(unittest.TestCase):
    def setUp(self):
        self.moves = [Move(Action.PLACE, 0), Move(Action.PLACE, 1)]
        self.features = [MoveFeatures(delta_open_tunnels=-1),
                         MoveFeatures(delta_open_tunnels=1)]

    def choose(self, state, moves=None):
        moves = self.moves if moves is None else moves
        with patch.object(PlayerObservation, "legal_moves", return_value=moves), \
             patch.object(phase, "move_features_no_draw", side_effect=self.features[:len(moves)]), \
             patch.object(phase, "score_features", side_effect=[42] * len(moves)):
            return PhaseCapacityTiePolicy().choose(state, Random(1))

    def test_preserves_capacity_before_quota_and_exit(self):
        self.assertEqual(self.choose(observation(ropes=0)), self.moves[0])
        self.assertEqual(self.choose(observation(raincoats=3, ropes=2)), self.moves[0])

    def test_favors_closure_only_after_quota_and_exit(self):
        self.assertEqual(self.choose(observation(raincoats=3, ropes=2, exit_placed=True)),
                         self.moves[1])

    def test_collect_place_tie_keeps_canonical_tier(self):
        moves = [Move(Action.COLLECT, 0), Move(Action.PLACE, 1)]
        with patch.object(PlayerObservation, "legal_moves", return_value=moves), \
             patch.object(phase, "move_features_no_draw", side_effect=self.features), \
             patch.object(phase, "score_features", side_effect=[42, 42]), \
             patch.object(phase.Random, "choice", autospec=True, return_value=moves[1]) as choice:
            self.assertEqual(PhaseCapacityTiePolicy().choose(observation(), Random(1)), moves[1])
            self.assertEqual(choice.call_args.args[1], moves)

    def test_no_moves_does_not_score(self):
        with patch.object(PlayerObservation, "legal_moves", return_value=[]), \
             patch.object(phase, "move_features_no_draw", side_effect=AssertionError("scored")):
            self.assertIsNone(PhaseCapacityTiePolicy().choose(observation(), Random(1)))


if __name__ == "__main__":
    unittest.main()
