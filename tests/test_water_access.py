"""Narrow synthetic ranking test; no games or hidden draws are run here."""

from random import Random
from unittest import TestCase
from unittest.mock import patch

from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.strategy import MoveFeatures
from bandido_alcatraz.water_access import WaterAccessV8Policy
from bandido_alcatraz.water_access_reference import WaterAccessV8Reference
import bandido_alcatraz.water_access as candidate_module
import bandido_alcatraz.water_access_reference as reference_module


class WaterAccessTests(TestCase):
    def test_water_access_can_prefer_opening_water_access_over_immediate_cover(self):
        cover = object()
        clear_access = object()
        features = {
            cover: MoveFeatures(delta_visible_water=1),
            clear_access: MoveFeatures(delta_water_obstruction=3),
        }

        class VisibleMoves:
            def legal_moves(self):
                return [cover, clear_access]

        with patch("bandido_alcatraz.strategy.move_features", side_effect=lambda _, move: features[move]), \
             patch("bandido_alcatraz.water_access.move_features_no_draw", side_effect=lambda _, move: features[move]), \
             patch("bandido_alcatraz.water_access.PlayerObservation", VisibleMoves):
            state = VisibleMoves()
            self.assertIs(BoundedMergeV4Policy(setup_weight=250).choose(state, Random(0)), cover)
            self.assertIs(WaterAccessV8Policy().choose(state, Random(0)), clear_access)

    def test_candidate_keeps_every_other_v4_weight(self):
        baseline = BoundedMergeV4Policy(setup_weight=250).weights
        candidate = WaterAccessV8Policy().weights
        self.assertEqual(candidate.delta_water_obstruction, 10_000)
        self.assertEqual(
            {
                field: getattr(candidate, field)
                for field in baseline.__dataclass_fields__
                if field != "delta_water_obstruction"
            },
            {
                field: getattr(baseline, field)
                for field in baseline.__dataclass_fields__
                if field != "delta_water_obstruction"
            },
        )

    def test_candidate_and_independent_reference_match_public_audit(self):
        state = PlayerObservation(None, (), 0, 0, False, False, 20, 0, (), None)
        moves = [Move(Action.PLACE, 0), Move(Action.PLACE, 1)]
        features = [MoveFeatures(delta_visible_water=1),
                    MoveFeatures(delta_water_obstruction=3)]
        with patch.object(PlayerObservation, "legal_moves", return_value=moves), \
             patch.object(candidate_module, "observation_wire", return_value={"synthetic": True}), \
             patch.object(reference_module, "observation_wire", return_value={"synthetic": True}), \
             patch.object(candidate_module, "move_features_no_draw", side_effect=features), \
             patch.object(reference_module.strategy, "move_features_no_draw", side_effect=features):
            actual = WaterAccessV8Policy().evaluate(state, Random(7))
            expected = WaterAccessV8Reference().evaluate(state, Random(7))
        self.assertEqual(actual, expected)
        self.assertEqual(actual[1]["tiers"], {"v4_top": [0], "final": [1]})

    def test_empty_public_hand_matches_reference(self):
        state = PlayerObservation(None, (), 0, 0, False, False, 20, 0, (), None)
        with patch.object(PlayerObservation, "legal_moves", return_value=[]), \
             patch.object(candidate_module, "observation_wire", return_value={"synthetic": True}), \
             patch.object(reference_module, "observation_wire", return_value={"synthetic": True}):
            self.assertEqual(WaterAccessV8Policy().evaluate(state, Random(7)),
                             WaterAccessV8Reference().evaluate(state, Random(7)))
