"""Invented public observations only; no scientific games or real-deck rollout."""
import sys
import unittest
from random import Random
from unittest.mock import patch

sys.path[:0] = ["src", "tests"]

from test_strategy25_equipment_closure import pair as equipment_pair
from bandido_alcatraz import strategy
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.visible_v4_tier_beam2 import V4TierBeamTwoPolicy
from bandido_alcatraz.visible_v4_tier_beam2_reference import V4TierBeamTwoReference
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair(ready):
    obs, old, _ = equipment_pair(ready)
    args = dict(catalog=tuple(old.catalog.values()), start_card=old._start_card,
                exit_card=old._exit_card)
    return obs, V4TierBeamTwoPolicy(**args), V4TierBeamTwoReference(**args)


class V4TierBeamTwoTests(unittest.TestCase):
    def test_never_leaves_v4_best_current_score_tier(self):
        for ready in (False, True):
            with self.subTest(ready=ready):
                obs, policy, reference = pair(ready)
                before = observation_wire(obs)
                candidate = policy.evaluate(obs, Random(17))
                oracle = reference.evaluate(obs, Random(17))
                self.assertEqual(candidate, oracle)
                self.assertEqual(observation_wire(obs), before)
                audit = candidate[1]
                self.assertTrue(set(audit["tiers"]["final"]).issubset(
                    audit["tiers"]["v4_top"]))
                self.assertIn(audit["chosen_index"], audit["tiers"]["v4_top"])

    def test_unique_v4_top_skips_lower_scoring_root(self):
        obs, policy, reference = pair(False)

        def evaluate_with_invented_scores(evaluator):
            ordinal = 0

            def score(_features, _weights):
                nonlocal ordinal
                current = ordinal
                ordinal += 1
                if current == 0:
                    return 100
                if current == 1:
                    return 90
                return 0

            with patch.object(strategy, "score_features", side_effect=score):
                return evaluator.evaluate(obs, Random(17))

        candidate = evaluate_with_invented_scores(policy)
        oracle = evaluate_with_invented_scores(reference)
        self.assertEqual(candidate, oracle)
        self.assertEqual(candidate[1]["tiers"]["v4_top"], [0])
        self.assertEqual(candidate[1]["tiers"]["final"], [0])
        self.assertEqual(candidate[1]["tiers"]["top"], [])
        self.assertEqual(candidate[0].action.value, "collect")

    def test_unique_second_score_breaks_only_a_v4_tie(self):
        obs, policy, reference = pair(True)
        root_count = len(obs.legal_moves())

        def evaluate_with_invented_continuation(evaluator):
            ordinal = 0

            def score(_features, _weights):
                nonlocal ordinal
                current = ordinal
                ordinal += 1
                if current < root_count:
                    return 100  # All current actions are tied at V4's best score.
                return 0 if current < root_count + 5 else 1000

            with patch.object(strategy, "score_features", side_effect=score):
                return evaluator.evaluate(obs, Random(17))

        candidate = evaluate_with_invented_continuation(policy)
        self.assertEqual(candidate, evaluate_with_invented_continuation(reference))
        audit = candidate[1]
        self.assertTrue(audit["flags"]["unique_tie_break"])
        self.assertEqual(audit["tiers"]["final"], [1])
        self.assertIn(1, audit["tiers"]["v4_top"])

    def test_physical_budget_veto_leaves_observation_intact(self):
        obs, policy, _ = pair(False)
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(17), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)


if __name__ == "__main__":
    unittest.main()
