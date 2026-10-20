"""Prefer spending high-outlet visible cards early; keep closers for later."""
from __future__ import annotations

from random import Random

from . import strategy
from .game import PlayerObservation
from .late_closure import LateClosurePolicy
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .quota_reserve_closure import OperationLimits, _PhysicalCalls, _require
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class CardReservePolicy(LateClosurePolicy):
    """Exact V4-250 plus a fixed early public-hand outlet-degree preference."""

    __slots__ = ()

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None) -> tuple[Move | None, dict, dict]:
        _require(type(rng) is Random, "exact canonical Random required")
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
            features = [strategy.move_features_no_draw(observation, move)
                        for move in legal]
            v4_scores = [strategy.score_features(row, weights) for row in features]
            degrees = [
                observation.hand[move.hand_index].external_tunnel_count
                if move.action is Action.PLACE
                and not observation.hand[move.hand_index].is_exit else None
                for move in legal
            ]
            bonuses = [
                2000 * (degree - 2) if observation.turns < 50 and degree is not None
                else 0 for degree in degrees
            ]
            scores = [base + bonus for base, bonus in zip(v4_scores, bonuses)]
            _require(all(type(score) is int for score in scores),
                     "candidate scores must be exact integers")
            best = max(scores, default=None)
            final = [i for i, score in enumerate(scores) if score == best]
            _require(sha(rng.getstate()) == rng_before,
                     "scoring mutated RNG state")
            chosen = rng.choice([legal[i] for i in final]) if final else None
            _require(chosen is None if not final else chosen in [legal[i] for i in final],
                     "RNG choice escaped final tier")
            chosen_index = legal.index(chosen) if chosen is not None else None
            after = sha(observation_wire(observation))
            _require(before == after, "public observation mutated by evaluation")
            audit = dict(
                schema="strategy27-card-reserve-v1", input_before=before, input_after=after,
                roots=[dict(move=move_wire(move), score=score,
                            v4_score=v4_score, outlet_degree=degree, bonus=bonus)
                       for move, score, v4_score, degree, bonus
                       in zip(legal, scores, v4_scores, degrees, bonuses)],
                tiers=dict(final=final), flags=dict(reserve_active=observation.turns < 50,
                                                     degree_bonus=2000),
                chosen_index=chosen_index, chosen=move_wire(chosen),
                rng_before=rng_before, rng_after=sha(rng.getstate()),
            )
        finally:
            meter.__exit__(None, None, None)
        return chosen, audit, dict(meter.counts, roots=len(legal))
