"""Narrow invented-catalog checks; no real deck or game cohort is run."""
import sys
import unittest
from random import Random

sys.path.insert(0, "src")

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.quota_reserve_closure import QuotaReserveClosurePolicy
from bandido_alcatraz.quota_reserve_closure_reference import QuotaReserveClosureReference
from bandido_alcatraz.setup import SOLO_EASY
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def invented_case(prior_placements, threshold=4):
    w, n, e, s = (Direction.WEST, Direction.NORTH, Direction.EAST, Direction.SOUTH)
    start = CardDefinition("start_easy", (
        CellSpec(0, 0, frozenset((w, n, e))),
        CellSpec(1, 0, frozenset((w, n, e, s))),
    ))

    def card(name, material=None, exit=False):
        return CardDefinition(name, (CellSpec(0, 0, frozenset((w,))),), material, exit)

    cards = ([card(f"coat-{i}", Material.RAINCOAT) for i in range(12)]
             + [card(f"rope-{i}", Material.ROPE) for i in range(8)]
             + [card(f"ordinary-{i}") for i in range(48)]
             + [card("exit", exit=True)])
    board = Board()
    board.seed(start)
    for card_index, origin, rotation in ((20, (2, 0), 0),
                                         (21, (1, 1), 1),
                                         (22, (-1, 0), 2))[:prior_placements]:
        board.place(cards[card_index], origin, rotation)
    hand = (cards[0], *cards[23:28])
    obs = PlayerObservation(board, hand, 0, 0, False, False,
                            prior_placements, 0, (), SOLO_EASY)
    args = dict(catalog=tuple(cards), start_card=start, exit_card=cards[-1])
    if threshold is not None:
        args["min_open_override"] = threshold
    return obs, QuotaReserveClosurePolicy(**args), QuotaReserveClosureReference(**args)


class MinimumOpenReserveTests(unittest.TestCase):
    def test_omitted_threshold_preserves_original_policy_and_audit(self):
        obs, policy, reference = invented_case(1, None)
        move, audit, _ = policy.evaluate(obs, Random(11))
        reference_move, reference_audit, _ = reference.evaluate(obs, Random(11))
        self.assertEqual((move, audit), (reference_move, reference_audit))
        self.assertIs(move.action, Action.PLACE)
        self.assertEqual(audit["schema"], "worker35-scientific-v1")
        self.assertEqual(audit["guards"][audit["chosen_index"]]["after"][0], 3)

    def test_four_open_tunnels_allows_existing_override(self):
        obs, policy, reference = invented_case(0)
        before = observation_wire(obs)
        move, audit, _ = policy.evaluate(obs, Random(11))
        reference_move, reference_audit, _ = reference.evaluate(obs, Random(11))
        self.assertEqual(move, reference_move)
        self.assertEqual(audit, reference_audit)
        self.assertIs(move.action, Action.PLACE)
        self.assertTrue(audit["flags"]["closure_branch_selected"])
        self.assertEqual({audit["guards"][i]["after"][0] for i in audit["tiers"]["C"]}, {4})
        self.assertEqual(observation_wire(obs), before)

    def test_one_to_three_open_tunnels_veto_override_and_retain_collect(self):
        for count in (1, 2, 3):
            with self.subTest(resulting_open=4-count):
                obs, policy, reference = invented_case(count)
                before = observation_wire(obs)
                move, audit, _ = policy.evaluate(obs, Random(11))
                reference_move, reference_audit, _ = reference.evaluate(obs, Random(11))
                self.assertEqual(move, reference_move)
                self.assertEqual(audit, reference_audit)
                self.assertIs(move.action, Action.COLLECT)
                self.assertEqual(audit["tiers"]["C"], [])
                self.assertEqual({g["reason"] for g in audit["guards"] if g["after"]},
                                 {"min_open_reserve"})
                self.assertEqual({g["after"][0] for g in audit["guards"] if g["after"]},
                                 {4-count})
                self.assertEqual(observation_wire(obs), before)


if __name__ == "__main__":
    unittest.main()
