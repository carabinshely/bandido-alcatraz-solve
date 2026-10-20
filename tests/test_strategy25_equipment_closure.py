"""Invented-catalog public-input checks; no real deck or game execution."""
import sys
import unittest
from random import Random
from unittest.mock import patch

sys.path[:0] = ["src", "tests"]

from test_strategy19_min_open import invented_case
from bandido_alcatraz import strategy
from bandido_alcatraz.equipment_closure import EquipmentClosurePolicy
from bandido_alcatraz.equipment_closure_reference import EquipmentClosureReference
from bandido_alcatraz.game import CollectedEquipment, PlayerObservation
from bandido_alcatraz.moves import Action
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair(ready=False):
    obs, source, _ = invented_case(3, None)
    catalog = source.catalog
    args = dict(catalog=tuple(catalog.values()), start_card=source._start_card,
                exit_card=source._exit_card)
    if ready:
        collected = tuple(CollectedEquipment(catalog[f"coat-{i}"], 4 + i)
                          for i in range(3)) + tuple(
                          CollectedEquipment(catalog[f"rope-{i}"], 7 + i)
                          for i in range(2))
        hand = tuple(card for card in catalog.values()
                     if card.card_id.startswith("ordinary-")
                     and card.card_id not in {record.card_id for record in obs.board.placements})[:6]
        obs = PlayerObservation(obs.board, hand, 3, 2,
                                obs.exit_placed, obs.exit_seen, obs.turns + 5,
                                obs.set_aside_unplayable, collected, obs.setup,
                                obs.player_index)
    return obs, EquipmentClosurePolicy(**args), EquipmentClosureReference(**args)


class EquipmentClosureTests(unittest.TestCase):
    def test_public_quota_switches_weight_and_reference_agrees(self):
        for ready, weight in ((False, 100), (True, 1000)):
            with self.subTest(ready=ready):
                obs, policy, reference = pair(ready)
                before = observation_wire(obs)
                result = policy.evaluate(obs, Random(11))
                self.assertEqual(result, reference.evaluate(obs, Random(11)))
                self.assertEqual(result[1]["flags"],
                                 {"equipment_ready": ready,
                                  "closure_weight": weight})
                self.assertEqual(observation_wire(obs), before)

    def test_one_open_root_is_not_vetoed(self):
        obs, policy, reference = pair()
        original = strategy.score_features

        def prefer_one_open(features, weights):
            if features.delta_open_tunnels == 1 and not features.wins:
                return 1_000_001
            return original(features, weights)

        with patch.object(strategy, "score_features", side_effect=prefer_one_open):
            chosen, audit, _ = policy.evaluate(obs, Random(7))
            self.assertEqual((chosen, audit), reference.evaluate(obs, Random(7))[:2])
        self.assertEqual(strategy.preview_move_without_draw(obs, chosen)
                         .successor.board.open_tunnels, 1)

    def test_physical_budget_vetoes_without_mutating_observation(self):
        obs, policy, _ = pair()
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(11), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)


if __name__ == "__main__":
    unittest.main()
