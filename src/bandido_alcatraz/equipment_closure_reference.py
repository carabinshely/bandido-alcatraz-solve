"""Independent selection oracle for equipment-ready closure."""

from __future__ import annotations

from random import Random

from . import strategy
from .game import PlayerObservation
from .equipment_closure import OperationLimits, _PhysicalCalls
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class EquipmentReadyClosureReference:
    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None):
        if type(observation) is not PlayerObservation or type(rng) is not Random:
            raise TypeError("exact public observation and canonical Random required")
        if limits is None:
            limits = OperationLimits()
        if type(limits) is not OperationLimits:
            raise TypeError("exact operation limits required")

        before = sha(observation_wire(observation))
        rng_before = sha(rng.getstate())
        weights = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            bounded_merge_setup_gain=250,
        )
        ready = observation.raincoats == 3 and observation.ropes == 2
        changed = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            delta_open_tunnels=(20_000 if ready else 100),
            bounded_merge_setup_gain=250,
        )
        with _PhysicalCalls(limits) as meter:
            moves = observation.legal_moves()
            rows = [(move, strategy.move_features_no_draw(observation, move))
                    for move in moves]
            scores = [strategy.score_features(features, changed)
                      for _, features in rows]
            v4_scores = [strategy.score_features(features, weights)
                         for _, features in rows]
            maximum = max(scores, default=None)
            final = [index for index, score in enumerate(scores) if score == maximum]
            v4_best = max(v4_scores, default=None)
            highest = [index for index, score in enumerate(v4_scores) if score == v4_best]
            if moves:
                chosen = rng.choice([moves[i] for i in final])
            else:
                chosen = None

        after = sha(observation_wire(observation))
        if before != after:
            raise RuntimeError("PUBLIC_OBSERVATION_MUTATED")
        audit = dict(
            schema="strategy34-equipment-closure-v1",
            input_before=before, input_after=after,
            roots=[dict(move=move_wire(move), score=score, v4_score=v4_score,
                        delta_open_tunnels=features.delta_open_tunnels)
                   for (move, features), score, v4_score in zip(rows, scores, v4_scores)],
            tiers=dict(v4_top=highest, final=final),
            flags=dict(equipment_ready=ready, open_tunnel_weight=(20_000 if ready else 100)),
            chosen_index=moves.index(chosen) if chosen is not None else None,
            chosen=move_wire(chosen), rng_before=rng_before,
            rng_after=sha(rng.getstate()),
        )
        return chosen, audit, dict(meter.counts, roots=len(moves))
