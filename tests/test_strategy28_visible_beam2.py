"""Invented public-catalog beam checks; no real deck game is run."""
import sys
import unittest
from random import Random

sys.path[:0] = ["src", "tests"]

from test_strategy25_equipment_closure import pair as equipment_pair
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.visible_beam2 import VisibleBeamTwoPolicy
from bandido_alcatraz.visible_beam2_reference import VisibleBeamTwoReference
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair(ready):
    obs, old, _ = equipment_pair(ready)
    args = dict(catalog=tuple(old.catalog.values()), start_card=old._start_card,
                exit_card=old._exit_card)
    return obs, VisibleBeamTwoPolicy(**args), VisibleBeamTwoReference(**args)


class VisibleBeamTwoTests(unittest.TestCase):
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
                self.assertIn(audit["chosen_index"], audit["tiers"]["final"])

    def test_physical_preview_budget_veto_preserves_observation(self):
        obs, policy, _ = pair(False)
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(17), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)


if __name__ == "__main__":
    unittest.main()
