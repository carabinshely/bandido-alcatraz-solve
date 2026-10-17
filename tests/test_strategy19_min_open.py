"""Narrow invented-catalog checks; no real deck or game cohort is run."""
import sys
import unittest
from random import Random

sys.path.insert(0, "src")

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.quota_reserve_closure import (
    OperationLimits, QuotaReserveClosurePolicy, ResourceExceeded,
)
from bandido_alcatraz.quota_reserve_closure_reference import QuotaReserveClosureReference
from bandido_alcatraz.setup import SOLO_EASY
from bandido_alcatraz.worker32.evidence import observation as observation_wire, sha


def invented_case(prior_placements, threshold=4, *, wet_coat=False,
                  exit_edges=None, spent_coats=0):
    w, n, e, s = (Direction.WEST, Direction.NORTH, Direction.EAST, Direction.SOUTH)
    start = CardDefinition("start_easy", (
        CellSpec(0, 0, frozenset((w, n, e))),
        CellSpec(1, 0, frozenset((w, n, e, s))),
    ))

    def card(name, material=None, exit=False, edges=(w,), water=False):
        return CardDefinition(name, (CellSpec(0, 0, frozenset(edges), water),), material, exit)

    cards = ([card(f"coat-{i}", Material.RAINCOAT,
                   edges=(w, e) if spent_coats else (w,), water=wet_coat)
              for i in range(12)]
             + [card(f"rope-{i}", Material.ROPE) for i in range(8)]
             + [card(f"ordinary-{i}") for i in range(48)]
             + [card("exit", exit=True, edges=(w,) if exit_edges is None else exit_edges)])
    board = Board()
    board.seed(start)
    for card_index, origin, rotation in ((20, (2, 0), 0),
                                         (21, (1, 1), 1),
                                         (22, (-1, 0), 2))[:prior_placements]:
        board.place(cards[card_index], origin, rotation)
    for i in range(spent_coats):
        board.place(cards[i], (i+2, 0), 0)
    hand = (cards[spent_coats], *cards[23:28])
    obs = PlayerObservation(board, hand, 0, 0, False, False,
                            prior_placements+spent_coats, 0, (), SOLO_EASY)
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

    def test_reserve_filter_and_existing_water_exit_guards(self):
        obs, policy, _ = invented_case(0, spent_coats=9)
        move, audit, _ = policy.evaluate(obs, Random(11))
        self.assertIs(move.action, Action.COLLECT)
        self.assertTrue(audit["flags"]["reserve_filter_active"])
        self.assertEqual({g["reason"] for r, g in zip(audit["roots"], audit["guards"])
                          if r["move"]["action"] == "place"
                          and r["move"]["hand_index"] == 0}, {"reserve_filtered"})
        for options, reason in ((dict(wet_coat=True), "visible_water_increased"),
                                (dict(exit_edges=()), "no_exit_capacity")):
            with self.subTest(reason=reason):
                obs, policy, reference = invented_case(0, **options)
                move, audit, _ = policy.evaluate(obs, Random(11))
                ref_move, ref_audit, _ = reference.evaluate(obs, Random(11))
                self.assertEqual((move, audit), (ref_move, ref_audit))
                self.assertIs(move.action, Action.COLLECT)
                self.assertEqual({g["reason"] for g in audit["guards"] if g["after"]},
                                 {reason})

    def test_guard_precedence_and_physical_limit(self):
        obs, policy, _ = invented_case(1, wet_coat=True, exit_edges=())
        move, audit, _ = policy.evaluate(obs, Random(11))
        self.assertIs(move.action, Action.COLLECT)
        self.assertEqual({g["reason"] for g in audit["guards"] if g["after"]},
                         {"min_open_reserve"})
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(11), limits=OperationLimits(previews=0))

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
        replay = Random(11)
        self.assertEqual(move, replay.choice([obs.legal_moves()[i]
                                              for i in audit["tiers"]["final"]]))
        self.assertEqual(audit["rng_after"], sha(replay.getstate()))
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
