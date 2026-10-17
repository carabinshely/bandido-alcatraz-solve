"""Invented-catalog checks only; no real-deck game is executed here."""
import sys
import unittest
from random import Random
from unittest.mock import patch

sys.path[:0] = ["src", "tests"]

from test_strategy19_min_open import invented_case
from bandido_alcatraz.game import PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.mobility_floor import MobilityFloorPolicy
from bandido_alcatraz.mobility_floor_reference import MobilityFloorReference
from bandido_alcatraz.quota_reserve_closure import OperationLimits, ResourceExceeded
from bandido_alcatraz.quota_reserve_closure import IntegrityError as CandidateIntegrityError
from bandido_alcatraz.quota_reserve_closure_reference import (
    OperationLimits as ReferenceOperationLimits, ReferenceInputError, ReferenceIntegrityError,
    ResourceExceeded as ReferenceResourceExceeded,
)
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def pair(prior):
    obs, old, _ = invented_case(prior, None)
    args = dict(catalog=tuple(old.catalog.values()), start_card=old._start_card,
                exit_card=old._exit_card)
    return obs, MobilityFloorPolicy(**args), MobilityFloorReference(**args)


class MobilityFloorTests(unittest.TestCase):
    def test_global_guard_changes_choice_outside_old_closure_branch(self):
        obs, candidate, reference = pair(2)
        before = observation_wire(obs)
        choice, audit, physical = candidate.evaluate(obs, Random(11))
        other, reference_audit, other_physical = reference.evaluate(obs, Random(11))
        self.assertEqual((choice, audit, physical), (other, reference_audit, other_physical))
        self.assertEqual(choice.action, Action.COLLECT)
        self.assertEqual(audit["schema"], "strategy20-global-mobility-floor-v1")
        self.assertTrue(audit["flags"]["floor_active"])
        self.assertFalse(audit["flags"]["floor_fallback"])
        self.assertTrue(any(row["risky"] for row in audit["mobility"]))
        self.assertEqual(observation_wire(obs), before)

    def test_floor_falls_back_if_every_legal_move_is_risky(self):
        obs, candidate, reference = pair(3)
        ordinary = tuple(card for card in candidate.catalog.values()
                         if card.card_id.startswith("ordinary-") and card.card_id not in
                         {record.card_id for record in obs.board.placements})[:6]
        obs = PlayerObservation(obs.board, ordinary, obs.raincoats, obs.ropes,
                                obs.exit_placed, obs.exit_seen, obs.turns,
                                obs.set_aside_unplayable, obs.collected_equipment,
                                obs.setup, obs.player_index)
        choice, audit, _ = candidate.evaluate(obs, Random(7))
        other, reference_audit, _ = reference.evaluate(obs, Random(7))
        self.assertEqual((choice, audit), (other, reference_audit))
        self.assertEqual(choice.action, Action.PLACE)
        self.assertTrue(audit["flags"]["floor_fallback"])

    def test_collect_is_never_marked_risky(self):
        obs, candidate, reference = pair(0)
        _, audit, _ = candidate.evaluate(obs, Random(3))
        self.assertEqual(audit, reference.evaluate(obs, Random(3))[1])
        self.assertTrue(all(not row["risky"] for row in audit["mobility"]
                            if row["action"] == "collect"))

    def test_physical_preview_ceiling_fails_closed_without_mutation(self):
        obs, candidate, _ = pair(2)
        before = observation_wire(obs)
        with self.assertRaises(ResourceExceeded):
            candidate.evaluate(obs, Random(3), limits=OperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)

    def test_reference_native_physical_preview_ceiling_fails_closed(self):
        obs, _, reference = pair(2)
        before = observation_wire(obs)
        with self.assertRaises(ReferenceResourceExceeded):
            reference.evaluate(obs, Random(3),
                               limits=ReferenceOperationLimits(previews=0))
        self.assertEqual(observation_wire(obs), before)

    def test_previous_policy_is_unchanged(self):
        obs, old, old_reference = invented_case(2, None)
        self.assertEqual(old.evaluate(obs, Random(7)), old_reference.evaluate(obs, Random(7)))

    def test_corrupt_board_placement_counter_is_rejected_by_both(self):
        obs, candidate, reference = pair(2)
        board = obs.board.clone()
        board._placement_count += 1
        malformed = PlayerObservation(board, obs.hand, obs.raincoats, obs.ropes,
                                      obs.exit_placed, obs.exit_seen, obs.turns,
                                      obs.set_aside_unplayable, obs.collected_equipment,
                                      obs.setup, obs.player_index)
        with self.assertRaises(CandidateIntegrityError):
            candidate.evaluate(malformed, Random(7))
        with self.assertRaises(ReferenceInputError):
            reference.evaluate(malformed, Random(7))

    def test_noncanonical_easy_start_is_rejected_by_both(self):
        _, old, _ = invented_case(0, None)
        invalid_start = CardDefinition("start_easy", (
            CellSpec(0, 0, frozenset((Direction.WEST,))),
        ))
        args = dict(catalog=tuple(old.catalog.values()), start_card=invalid_start,
                    exit_card=old._exit_card)
        with self.assertRaises(CandidateIntegrityError):
            MobilityFloorPolicy(**args)
        with self.assertRaises(ReferenceInputError):
            MobilityFloorReference(**args)

    def test_boolean_board_placement_counter_is_rejected_by_both(self):
        obs, candidate, reference = pair(0)
        board = obs.board.clone()
        board._placement_count = True
        malformed = PlayerObservation(board, obs.hand, obs.raincoats, obs.ropes,
                                      obs.exit_placed, obs.exit_seen, obs.turns,
                                      obs.set_aside_unplayable, obs.collected_equipment,
                                      obs.setup, obs.player_index)
        with self.assertRaises(CandidateIntegrityError):
            candidate.evaluate(malformed, Random(7))
        with self.assertRaises(ReferenceInputError):
            reference.evaluate(malformed, Random(7))

    def test_wrong_identity_five_open_start_is_rejected_by_both(self):
        _, old, _ = invented_case(0, None)
        old_start = old._start_card
        wrong_start = CardDefinition("wrong_easy", old_start.cells)
        args = dict(catalog=tuple(old.catalog.values()), start_card=wrong_start,
                    exit_card=old._exit_card)
        with self.assertRaises(CandidateIntegrityError):
            MobilityFloorPolicy(**args)
        with self.assertRaises(ReferenceInputError):
            MobilityFloorReference(**args)

    def test_equipment_exit_is_rejected_by_both(self):
        _, old, _ = invented_case(0, None)
        cards = tuple(old.catalog.values())
        object.__setattr__(cards[-1], "material", Material.ROPE)
        object.__setattr__(cards[12], "material", None)
        args = dict(catalog=cards, start_card=old._start_card,
                    exit_card=cards[-1])
        with self.assertRaises(CandidateIntegrityError):
            MobilityFloorPolicy(**args)
        with self.assertRaises(ReferenceInputError):
            MobilityFloorReference(**args)

    def test_mutable_catalog_container_is_rejected_by_both(self):
        _, old, _ = invented_case(0, None)
        args = dict(catalog=list(old.catalog.values()), start_card=old._start_card,
                    exit_card=old._exit_card)
        with self.assertRaises(CandidateIntegrityError):
            MobilityFloorPolicy(**args)
        with self.assertRaises(ReferenceInputError):
            MobilityFloorReference(**args)

    def test_rng_wrapper_is_rejected_by_both(self):
        obs, candidate, reference = pair(2)

        class RngWrapper:
            def __init__(self):
                self.inner = Random(7)

            def getstate(self):
                return self.inner.getstate()

            def choice(self, choices):
                return self.inner.choice(choices)

        with self.assertRaises(CandidateIntegrityError):
            candidate.evaluate(obs, RngWrapper())
        with self.assertRaises(ReferenceInputError):
            reference.evaluate(obs, RngWrapper())

    def test_rng_subclass_cannot_select_outside_final_tier(self):
        obs, candidate, reference = pair(2)

        class Rogue(Random):
            def choice(self, choices):
                legal = obs.legal_moves()
                return next(move for move in legal if move not in choices)

        with self.assertRaises(CandidateIntegrityError):
            candidate.evaluate(obs, Rogue(7))
        with self.assertRaises(ReferenceInputError):
            reference.evaluate(obs, Rogue(7))

    def test_scoring_cannot_advance_canonical_rng(self):
        obs, candidate, reference = pair(2)
        rng = Random(7)
        from bandido_alcatraz import strategy
        original = strategy.score_move_no_draw

        def altered(*args, **kwargs):
            rng.random()
            return original(*args, **kwargs)

        with patch.object(strategy, "score_move_no_draw", altered):
            with self.assertRaises(CandidateIntegrityError):
                candidate.evaluate(obs, rng)
        rng = Random(7)
        with patch.object(strategy, "score_move_no_draw", altered):
            with self.assertRaises(ReferenceIntegrityError):
                reference.evaluate(obs, rng)


if __name__ == "__main__":
    unittest.main()
