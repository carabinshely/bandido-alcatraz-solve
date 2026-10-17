"""Prospective public-input-only V4-250 global mobility-floor candidate."""
from __future__ import annotations

from random import Random

from . import strategy
from .board import Board
from .game import PlayerObservation
from .model import CardDefinition
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .quota_reserve_closure import (
    OperationLimits, QuotaReserveClosurePolicy, _PhysicalCalls, _require,
)
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class MobilityFloorPolicy(QuotaReserveClosurePolicy):
    """Reject sub-three-open nonwinning placements when another root exists.

    Reuse the frozen source policy's exact public physical-input validation, but
    select directly by canonical V4-250 scores. No quota/closure tier is used.
    """

    __slots__ = ()

    def __init__(self, *, catalog: tuple[CardDefinition, ...],
                 start_card: CardDefinition, exit_card: CardDefinition) -> None:
        super().__init__(catalog=catalog, start_card=start_card,
                         exit_card=exit_card, min_open_override=0)
        seeded = Board()
        seeded.seed(start_card)
        _require(seeded.open_tunnels == 5, "easy START must have five open tunnels")

    def _validate(self, observation: PlayerObservation) -> dict:
        supply = super()._validate(observation)
        _require(type(observation.board._placement_count) is int
                 and observation.board._placement_count == len(observation.board.placements),
                 "public placement counter disagrees with history")
        return supply

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None) -> tuple[Move | None, dict, dict]:
        _require(isinstance(rng, Random), "canonical Random-compatible RNG required")
        if limits is None:
            limits = OperationLimits()
        _require(type(limits) is OperationLimits, "invalid operation limits")
        meter = _PhysicalCalls(limits)
        try:
            meter.__enter__()
            self._validate(observation)
            before = sha(observation_wire(observation))
            rng_before = sha(rng.getstate())
            legal = observation.legal_moves()
            weights = BoundedMergeV4Policy(setup_weight=250).weights
            scores = [strategy.score_move_no_draw(observation, move, weights) for move in legal]
            _require(all(type(score) is int for score in scores), "V4 scores must be integers")
            mobility = []
            safe = []
            for index, move in enumerate(legal):
                if move.action is Action.PLACE:
                    successor = strategy.preview_move_without_draw(observation, move).successor
                    after_open = successor.board.open_tunnels
                    risky = after_open < 3 and not successor.won
                else:
                    after_open = observation.board.open_tunnels
                    risky = False
                mobility.append(dict(action=move.action.value, after_open=after_open, risky=risky))
                if not risky:
                    safe.append(index)
            domain = safe if safe else list(range(len(legal)))
            best = max((scores[i] for i in domain), default=None)
            final = [i for i in domain if scores[i] == best]
            chosen = rng.choice([legal[i] for i in final]) if final else None
            chosen_index = legal.index(chosen) if chosen is not None else None
            after = sha(observation_wire(observation))
            _require(before == after, "public observation mutated by evaluation")
            audit = dict(schema="strategy20-global-mobility-floor-v1",
                         input_before=before, input_after=after,
                         roots=[dict(move=move_wire(move), score=score)
                                for move, score in zip(legal, scores)],
                         tiers=dict(safe=safe, final=final), mobility=mobility,
                         flags=dict(floor_active=len(safe) < len(legal) and bool(safe),
                                    floor_fallback=bool(legal) and not safe),
                         chosen_index=chosen_index, chosen=move_wire(chosen),
                         rng_before=rng_before, rng_after=sha(rng.getstate()))
        finally:
            meter.__exit__(None, None, None)
        return chosen, audit, dict(meter.counts, roots=len(legal))
