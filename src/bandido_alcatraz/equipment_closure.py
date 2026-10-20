"""Close more strongly only after the public equipment quota is complete."""
from __future__ import annotations

from dataclasses import replace
from random import Random

from . import strategy
from .game import PlayerObservation
from .late_closure import LateClosurePolicy
from .moves import Move
from .policies import BoundedMergeV4Policy
from .quota_reserve_closure import OperationLimits, _PhysicalCalls, _require
from .rules import is_equipment_ready
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class EquipmentClosurePolicy(LateClosurePolicy):
    """V4-250, with a public-equipment-triggered closure weight and no floor."""

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
            ready = is_equipment_ready(observation.raincoats, observation.ropes)
            weights = BoundedMergeV4Policy(setup_weight=250).weights
            if ready:
                weights = replace(weights, delta_open_tunnels=1000)
            scores = [strategy.score_move_no_draw(observation, move, weights)
                      for move in legal]
            _require(all(type(score) is int for score in scores),
                     "V4 scores must be integers")
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
            audit = dict(schema="strategy25-equipment-closure-v1",
                         input_before=before, input_after=after,
                         roots=[dict(move=move_wire(move), score=score)
                                for move, score in zip(legal, scores)],
                         tiers=dict(final=final),
                         flags=dict(equipment_ready=ready,
                                    closure_weight=weights.delta_open_tunnels),
                         chosen_index=chosen_index, chosen=move_wire(chosen),
                         rng_before=rng_before, rng_after=sha(rng.getstate()))
        finally:
            meter.__exit__(None, None, None)
        return chosen, audit, dict(meter.counts, roots=len(legal))
