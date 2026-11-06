"""Invented-catalog boundary checks for prospective strategy21; CI-only execution."""
import sys
import unittest
from random import Random
from unittest.mock import patch

sys.path[:0] = ["src", "tests"]

from test_strategy19_min_open import invented_case
from bandido_alcatraz.one_open_reserve import OneOpenReservePolicy
from bandido_alcatraz.one_open_reserve_reference import OneOpenReserveReference
from bandido_alcatraz.mobility_floor import MobilityFloorPolicy
from bandido_alcatraz import strategy
from bandido_alcatraz.game import CollectedEquipment, PlayerObservation
from bandido_alcatraz.moves import Action
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair(prior):
    obs, old, _ = invented_case(prior, None)
    args = dict(catalog=tuple(old.catalog.values()), start_card=old._start_card,
                exit_card=old._exit_card)
    return obs, OneOpenReservePolicy(**args), OneOpenReserveReference(**args)


class OneOpenReserveTests(unittest.TestCase):
    def test_two_open_choice_differs_from_three_open_floor_under_fixed_scores(self):
        obs, policy, reference = pair(2)
        old = MobilityFloorPolicy(catalog=tuple(policy.catalog.values()),
                                  start_card=policy._start_card,
                                  exit_card=policy._exit_card)
        before = observation_wire(obs)

        def invented_score(public, move, _weights):
            if move.action is Action.PLACE:
                projected = strategy.preview_move_without_draw(public, move).successor
                return 100 if projected.board.open_tunnels == 2 else -100
            return 0

        with patch.object(strategy, "score_move_no_draw", side_effect=invented_score):
            choice, audit, _ = policy.evaluate(obs, Random(11))
            self.assertEqual((choice, audit), reference.evaluate(obs, Random(11))[:2])
            old_choice, old_audit, _ = old.evaluate(obs, Random(11))
        self.assertIs(choice.action, Action.PLACE)
        self.assertEqual(audit["mobility"][audit["chosen_index"]]["after_open"], 2)
        self.assertEqual(audit["roots"][audit["chosen_index"]]["score"], 100)
        self.assertIs(old_choice.action, Action.COLLECT)
        self.assertTrue(old_audit["flags"]["floor_active"])
        self.assertEqual(observation_wire(obs), before)

    def test_two_open_placement_is_eligible_and_independent_reference_agrees(self):
        obs, policy, reference = pair(2)
        before = observation_wire(obs)
        result = policy.evaluate(obs, Random(11))
        self.assertEqual(result, reference.evaluate(obs, Random(11)))
        audit = result[1]
        self.assertEqual(audit["schema"], "strategy21-one-open-reserve-v1")
        two_open = [row for row in audit["mobility"]
                    if row["action"] == "place" and row["after_open"] == 2]
        self.assertTrue(two_open)
        self.assertTrue(all(not row["risky"] for row in two_open))
        self.assertEqual(observation_wire(obs), before)

    def test_one_open_nonwinning_placement_is_vetoed_when_safe_root_exists(self):
        obs, policy, reference = pair(3)
        result = policy.evaluate(obs, Random(11))
        self.assertEqual(result, reference.evaluate(obs, Random(11)))
        audit = result[1]
        one_open = [row for row in audit["mobility"]
                    if row["action"] == "place" and row["after_open"] == 1]
        self.assertTrue(one_open)
        self.assertTrue(all(row["risky"] for row in one_open))
        self.assertTrue(audit["flags"]["floor_active"])

    def test_physical_preview_limit_fails_closed(self):
        obs, policy, _ = pair(2)
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            policy.evaluate(obs, Random(11), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)

    def test_all_risky_falls_back_and_replays_one_canonical_choice(self):
        obs, policy, reference = pair(3)
        ordinary = tuple(card for card in policy.catalog.values()
                         if card.card_id.startswith("ordinary-") and card.card_id not in
                         {record.card_id for record in obs.board.placements})[:6]
        obs = PlayerObservation(obs.board, ordinary, obs.raincoats, obs.ropes,
                                obs.exit_placed, obs.exit_seen, obs.turns,
                                obs.set_aside_unplayable, obs.collected_equipment,
                                obs.setup, obs.player_index)
        choice, audit, _ = policy.evaluate(obs, Random(7))
        self.assertEqual((choice, audit), reference.evaluate(obs, Random(7))[:2])
        self.assertTrue(audit["flags"]["floor_fallback"])
        self.assertEqual(audit["tiers"]["safe"], [])
        self.assertIs(choice.action, Action.PLACE)
        replay = Random(7)
        self.assertEqual(choice, replay.choice([obs.legal_moves()[i]
                                                for i in audit["tiers"]["final"]]))

    def test_real_preview_keeps_winning_zero_open_exit_eligible(self):
        obs, policy, reference = pair(3)
        cap = next(move for move in obs.legal_moves()
                   if move.action is Action.PLACE
                   and obs.hand[move.hand_index].card_id.startswith("ordinary-")
                   and strategy.preview_move_without_draw(obs, move).successor.board.open_tunnels == 1)
        board = obs.board.clone()
        board.place(obs.hand[cap.hand_index], cap.origin, cap.quarter_turns)
        catalog = policy.catalog
        hand = (policy._exit_card,) + tuple(card for card in catalog.values()
                   if card.card_id.startswith("ordinary-")
                   and card.card_id not in {record.card_id for record in board.placements})[:5]
        collected = tuple(CollectedEquipment(catalog[f"coat-{i}"], 5 + i)
                          for i in range(3)) + tuple(
                          CollectedEquipment(catalog[f"rope-{i}"], 8 + i)
                          for i in range(2))
        ready = PlayerObservation(board, hand, 3, 2, False, True, 9, 0,
                                  collected, obs.setup)
        before = observation_wire(ready)
        choice, audit, _ = policy.evaluate(ready, Random(7))
        self.assertEqual((choice, audit), reference.evaluate(ready, Random(7))[:2])
        self.assertTrue(strategy.preview_move_without_draw(ready, choice).successor.won)
        self.assertEqual(audit["mobility"][audit["chosen_index"]],
                         {"action": "place", "after_open": 0, "risky": False})
        self.assertTrue(any(row["after_open"] == 0 and row["risky"]
                            for row in audit["mobility"]))
        self.assertEqual(observation_wire(ready), before)


if __name__ == "__main__":
    unittest.main()
