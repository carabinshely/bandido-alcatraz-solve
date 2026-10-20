"""Invented-catalog public-hand reserve checks; no real deck games."""
import sys
import unittest
from random import Random

sys.path[:0] = ["src", "tests"]

from test_strategy19_min_open import invented_case
from bandido_alcatraz.card_reserve import CardReservePolicy
from bandido_alcatraz.card_reserve_reference import CardReserveReference
from bandido_alcatraz.moves import Action
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair():
    obs, source, _ = invented_case(3, None)
    args = dict(catalog=tuple(source.catalog.values()),
                start_card=source._start_card, exit_card=source._exit_card)
    return obs, CardReservePolicy(**args), CardReserveReference(**args)


class CardReserveTests(unittest.TestCase):
    def test_exact_reference_and_public_bonus(self):
        obs, policy, reference = pair()
        before = observation_wire(obs)
        candidate = policy.evaluate(obs, Random(11))
        independent = reference.evaluate(obs, Random(11))
        self.assertEqual(candidate, independent)
        self.assertEqual(observation_wire(obs), before)
        self.assertEqual(candidate[1]["flags"],
                         {"reserve_active": True, "degree_bonus": 2000})
        checked = 0
        for move, row in zip(obs.legal_moves(), candidate[1]["roots"]):
            card = obs.hand[move.hand_index]
            expected = (2000 * (card.external_tunnel_count - 2)
                        if move.action is Action.PLACE and not card.is_exit else 0)
            self.assertEqual(row["bonus"], expected)
            self.assertEqual(row["score"], row["v4_score"] + expected)
            checked += int(expected != 0)
        self.assertGreater(checked, 0)

    def test_resource_veto_preserves_input(self):
        obs, policy, _ = pair()
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(11), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)


if __name__ == "__main__":
    unittest.main()
