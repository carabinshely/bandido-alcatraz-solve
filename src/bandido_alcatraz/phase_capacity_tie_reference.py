"""Independent selection oracle for the phase-capacity tie experiment."""

from __future__ import annotations

from random import Random

from . import strategy
from .game import PlayerObservation
from .moves import Action
from .phase_capacity_tie import OperationLimits, _PhysicalCalls
from .rules import is_equipment_ready
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


class PhaseCapacityTieReference:
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
        with _PhysicalCalls(limits) as meter:
            moves = observation.legal_moves()
            rows = [(move, strategy.move_features_no_draw(observation, move))
                    for move in moves]
            scores = [strategy.score_features(features, weights)
                      for _, features in rows]
            maximum = max(scores, default=None)
            highest = [index for index, score in enumerate(scores) if score == maximum]
            final = highest
            ready = False
            if moves:
                ready = observation.exit_placed and is_equipment_ready(
                    observation.raincoats, observation.ropes
                )
                if len(highest) > 1 and all(moves[i].action is Action.PLACE for i in highest):
                    capacity = [rows[i][1].delta_open_tunnels for i in highest]
                    target = max(capacity) if ready else min(capacity)
                    final = [i for i in highest if rows[i][1].delta_open_tunnels == target]
                chosen = rng.choice([moves[i] for i in final])
            else:
                chosen = None

        after = sha(observation_wire(observation))
        if before != after:
            raise RuntimeError("PUBLIC_OBSERVATION_MUTATED")
        audit = dict(
            schema="strategy31-phase-capacity-tie-v1",
            input_before=before, input_after=after,
            roots=[dict(move=move_wire(move), score=score, v4_score=score,
                        delta_open_tunnels=features.delta_open_tunnels)
                   for (move, features), score in zip(rows, scores)],
            tiers=dict(v4_top=highest, final=final),
            flags=dict(phase_ready=ready, phase_tie_active=len(final) < len(highest)),
            chosen_index=moves.index(chosen) if chosen is not None else None,
            chosen=move_wire(chosen), rng_before=rng_before,
            rng_after=sha(rng.getstate()),
        )
        return chosen, audit, dict(meter.counts, roots=len(moves))
