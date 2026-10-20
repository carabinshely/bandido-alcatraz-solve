"""Invented public-catalog collect-guard checks; no real deck game is run."""
import sys
import unittest
from random import Random
from unittest.mock import patch

sys.path[:0] = ["src", "tests"]

from test_strategy25_equipment_closure import pair as equipment_pair
from bandido_alcatraz import strategy
from bandido_alcatraz.game import GameState
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.visible_beam2_collect_guard import CollectGuardBeamTwoPolicy
from bandido_alcatraz.visible_beam2_collect_guard_reference import CollectGuardBeamTwoReference
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair(ready):
    obs, old, _ = equipment_pair(ready)
    args = dict(catalog=tuple(old.catalog.values()), start_card=old._start_card,
                exit_card=old._exit_card)
    return obs, CollectGuardBeamTwoPolicy(**args), CollectGuardBeamTwoReference(**args)


class CollectGuardBeamTwoTests(unittest.TestCase):
    def test_collect_guard_overrides_higher_beam_path(self):
        obs, policy, reference = pair(False)
        self.assertEqual(len(obs.legal_moves()), 13)

        def evaluate_with_invented_scores(evaluator):
            ordinal = 0

            def score(_features, _weights):
                nonlocal ordinal
                current = ordinal
                ordinal += 1
                if current == 0:
                    return 100  # collect is V4's sole highest first action
                if current == 1:
                    return 90  # placement is second, with a superior continuation
                return 1000 if current >= 23 else 0

            with patch.object(strategy, "score_features", side_effect=score):
                result = evaluator.evaluate(obs, Random(17))
            self.assertEqual(ordinal, 28)
            return result

        candidate = evaluate_with_invented_scores(policy)
        self.assertEqual(candidate, evaluate_with_invented_scores(reference))
        audit = candidate[1]
        self.assertEqual(audit["tiers"]["v4_top"], [0])
        self.assertEqual(audit["tiers"]["beam_final"], [1])
        self.assertTrue(audit["flags"]["collect_guard_active"])
        self.assertEqual(audit["tiers"]["final"], [0])
        self.assertEqual(candidate[0].action.value, "collect")

    def test_shared_primitives_against_direct_synthetic_oracle(self):
        weights = BoundedMergeV4Policy(setup_weight=250).weights
        for ready in (False, True):
            with self.subTest(ready=ready):
                obs, _, _ = pair(ready)
                for move in obs.legal_moves():
                    direct = GameState(
                        board=obs.board.clone(), draw_pile=[], hand=list(obs.hand),
                        raincoats=obs.raincoats, ropes=obs.ropes,
                        exit_placed=obs.exit_placed, exit_seen=obs.exit_seen,
                        turns=obs.turns, set_aside_unplayable=obs.set_aside_unplayable,
                        collected_equipment=obs.collected_equipment,
                        setup=obs.setup, player_index=obs.player_index)
                    direct.apply(move, validate=True)
                    preview = strategy.preview_move_without_draw(obs, move).successor
                    self.assertEqual(observation_wire(preview.observation()),
                                     observation_wire(direct.observation()))
                    no_draw = strategy.move_features_no_draw(obs, move)
                    older = strategy.move_features(obs, move)
                    self.assertEqual(no_draw, older)
                    expected = sum(getattr(older, name) * getattr(weights, name)
                                   for name in older.__dataclass_fields__)
                    self.assertEqual(strategy.score_move_no_draw(obs, move, weights),
                                     expected)

    def test_ready_and_unready_reference_agree_on_public_input(self):
        for ready in (False, True):
            with self.subTest(ready=ready):
                obs, policy, reference = pair(ready)
                before = observation_wire(obs)
                result = policy.evaluate(obs, Random(17))
                self.assertEqual(result, reference.evaluate(obs, Random(17)))
                self.assertEqual(observation_wire(obs), before)
                audit = result[1]
                self.assertLessEqual(len(audit["tiers"]["top"]), 2)
                self.assertEqual(audit["tiers"]["top"],
                                 sorted(range(len(audit["roots"])),
                                        key=lambda i: (-audit["roots"][i]["one_score"], i))[:2])
                v4_top = audit["tiers"]["v4_top"]
                self.assertEqual(v4_top,
                                 [i for i, row in enumerate(audit["roots"])
                                  if row["one_score"] == max(r["one_score"]
                                                              for r in audit["roots"])])
                self.assertEqual(audit["tiers"]["final"],
                                 v4_top if audit["flags"]["collect_guard_active"]
                                 else audit["tiers"]["beam_final"])
                self.assertIn(audit["chosen_index"], audit["tiers"]["final"])

    def test_physical_preview_budget_veto_preserves_observation(self):
        obs, policy, _ = pair(False)
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(17), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)


if __name__ == "__main__":
    unittest.main()
