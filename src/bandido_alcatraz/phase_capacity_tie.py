"""Public-state V4-250 tie-break based on visible tunnel capacity.

This changes only ties in V4's immediate-score best tier. It never inspects a
replacement draw; the current hand and board are the complete policy input.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
import sys

from . import moves as canonical_moves
from . import strategy
from .game import PlayerObservation
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .rules import is_equipment_ready
from .strategy import move_features_no_draw, score_features
from .worker32.evidence import move as move_wire, observation as observation_wire, sha


@dataclass(frozen=True, slots=True)
class OperationLimits:
    legal_enumerations: int = 32768
    previews: int = 32768
    exit_geometry_checks: int = 32768

    def __post_init__(self):
        if any(type(getattr(self, name)) is not int or getattr(self, name) < 0
               for name in self.__dataclass_fields__):
            raise TypeError("exact nonnegative operation limits required")


class _PhysicalCalls:
    """Count canonical Python function entries while a decision is live."""

    def __init__(self, limits: OperationLimits) -> None:
        self.limits = limits
        self.counts = dict(legal_enumerations=0, previews=0,
                           exit_geometry_checks=0)
        self.codes = {
            canonical_moves.legal_moves.__code__: "legal_enumerations",
            canonical_moves.placement_moves.__code__: "legal_enumerations",
            strategy.preview_move_without_draw.__code__: "previews",
            strategy.standalone_exit_legal_move_count.__code__: "exit_geometry_checks",
        }

    def _profile(self, frame, event, arg):
        if event == "call":
            name = self.codes.get(frame.f_code)
            if name is not None:
                self.counts[name] += 1
                if self.counts[name] > getattr(self.limits, name):
                    raise RuntimeError("PHYSICAL_" + name.upper() + "_LIMIT")

    def __enter__(self):
        if sys.getprofile() is not None:
            raise RuntimeError("PROFILE_HOOK_ALREADY_ACTIVE")
        sys.setprofile(self._profile)
        return self

    def __exit__(self, exc_type, exc, traceback):
        sys.setprofile(None)


class PhaseCapacityTiePolicy:
    """Preserve capacity before readiness, then favor closure among V4 ties."""

    def __init__(self) -> None:
        self.weights = BoundedMergeV4Policy(setup_weight=250).weights

    def _decision(self, observation: PlayerObservation, rng: Random):
        if type(observation) is not PlayerObservation or type(rng) is not Random:
            raise TypeError("exact public observation and canonical Random required")
        moves = observation.legal_moves()
        if not moves:
            return None, moves, [], [], [], [], False

        features = [move_features_no_draw(observation, move) for move in moves]
        scores = [score_features(row, self.weights) for row in features]
        best = max(scores)
        v4_top = [index for index, score in enumerate(scores) if score == best]
        final = v4_top
        ready = observation.exit_placed and is_equipment_ready(
            observation.raincoats, observation.ropes
        )

        # A COLLECT/PLACE score tie keeps the canonical V4 draw. The phase rule
        # applies only to equally scored placements with differing capacity.
        if len(v4_top) > 1 and all(moves[index].action is Action.PLACE for index in v4_top):
            deltas = [features[index].delta_open_tunnels for index in v4_top]
            selected = max(deltas) if ready else min(deltas)
            final = [index for index in v4_top
                     if features[index].delta_open_tunnels == selected]

        chosen = rng.choice([moves[index] for index in final])
        return chosen, moves, features, scores, v4_top, final, ready

    def choose(self, observation: PlayerObservation, rng: Random) -> Move | None:
        return self._decision(observation, rng)[0]

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None):
        if limits is None:
            limits = OperationLimits()
        if type(limits) is not OperationLimits:
            raise TypeError("exact operation limits required")
        before = sha(observation_wire(observation))
        rng_before = sha(rng.getstate())
        with _PhysicalCalls(limits) as meter:
            chosen, moves, features, scores, v4_top, final, ready = self._decision(
                observation, rng
            )
        after = sha(observation_wire(observation))
        if before != after:
            raise RuntimeError("PUBLIC_OBSERVATION_MUTATED")
        audit = dict(
            schema="strategy31-phase-capacity-tie-v1",
            input_before=before, input_after=after,
            roots=[dict(move=move_wire(move), score=score, v4_score=score,
                        delta_open_tunnels=feature.delta_open_tunnels)
                   for move, feature, score in zip(moves, features, scores)],
            tiers=dict(v4_top=v4_top, final=final),
            flags=dict(phase_ready=ready, phase_tie_active=len(final) < len(v4_top)),
            chosen_index=moves.index(chosen) if chosen is not None else None,
            chosen=move_wire(chosen), rng_before=rng_before,
            rng_after=sha(rng.getstate()),
        )
        return chosen, audit, dict(meter.counts, roots=len(moves))
