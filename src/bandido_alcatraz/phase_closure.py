"""Public-turn V4-250 closure reweighting; no hidden replacement draw."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
import sys

from . import moves as canonical_moves
from . import strategy
from .game import PlayerObservation
from .moves import Move
from .policies import BoundedMergeV4Policy
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


class PhaseClosureV7Policy:
    """Raise the visible tunnel-closure weight from turn 20 onward."""

    def __init__(self) -> None:
        self.weights = BoundedMergeV4Policy(setup_weight=250).weights
        from dataclasses import replace
        self.late_weights = replace(self.weights, delta_open_tunnels=5_000)

    def _decision(self, observation: PlayerObservation, rng: Random):
        if type(observation) is not PlayerObservation or type(rng) is not Random:
            raise TypeError("exact public observation and canonical Random required")
        moves = observation.legal_moves()
        if not moves:
            return None, moves, [], [], [], [], [], observation.turns >= 20

        features = [move_features_no_draw(observation, move) for move in moves]
        late = observation.turns >= 20
        weights = self.late_weights if late else self.weights
        scores = [score_features(row, weights) for row in features]
        v4_scores = [score_features(row, self.weights) for row in features]
        best = max(scores)
        v4_best = max(v4_scores)
        v4_top = [index for index, score in enumerate(v4_scores) if score == v4_best]
        final = [index for index, score in enumerate(scores) if score == best]
        chosen = rng.choice([moves[index] for index in final])
        return chosen, moves, features, scores, v4_scores, v4_top, final, late

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
            chosen, moves, features, scores, v4_scores, v4_top, final, late = self._decision(
                observation, rng
            )
        after = sha(observation_wire(observation))
        if before != after:
            raise RuntimeError("PUBLIC_OBSERVATION_MUTATED")
        audit = dict(
            schema="strategy32-phase-closure-v1",
            input_before=before, input_after=after,
            roots=[dict(move=move_wire(move), score=score, v4_score=v4_score,
                        delta_open_tunnels=feature.delta_open_tunnels)
                   for move, feature, score, v4_score in zip(moves, features, scores, v4_scores)],
            tiers=dict(v4_top=v4_top, final=final),
            flags=dict(late=late, closure_weight=5_000 if late else 100),
            chosen_index=moves.index(chosen) if chosen is not None else None,
            chosen=move_wire(chosen), rng_before=rng_before,
            rng_after=sha(rng.getstate()),
        )
        return chosen, audit, dict(meter.counts, roots=len(moves))
