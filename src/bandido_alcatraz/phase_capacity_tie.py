"""Public-state V4-250 tie-break based on visible tunnel capacity.

This changes only ties in V4's immediate-score best tier. It never inspects a
replacement draw; the current hand and board are the complete policy input.
"""

from __future__ import annotations

from random import Random

from .game import PlayerObservation
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .rules import is_equipment_ready
from .strategy import move_features_no_draw, score_features


class PhaseCapacityTiePolicy:
    """Preserve capacity before readiness, then favor closure among V4 ties."""

    def __init__(self) -> None:
        self.weights = BoundedMergeV4Policy(setup_weight=250).weights

    def choose(self, observation: PlayerObservation, rng: Random) -> Move | None:
        if type(observation) is not PlayerObservation or type(rng) is not Random:
            raise TypeError("exact public observation and canonical Random required")
        moves = observation.legal_moves()
        if not moves:
            return None

        features = [move_features_no_draw(observation, move) for move in moves]
        scores = [score_features(row, self.weights) for row in features]
        best = max(scores)
        top = [index for index, score in enumerate(scores) if score == best]

        # A COLLECT/PLACE score tie keeps the canonical V4 draw. The phase rule
        # applies only to equally scored placements with differing capacity.
        if len(top) > 1 and all(moves[index].action is Action.PLACE for index in top):
            deltas = [features[index].delta_open_tunnels for index in top]
            ready = observation.exit_placed and is_equipment_ready(
                observation.raincoats, observation.ropes
            )
            selected = max(deltas) if ready else min(deltas)
            top = [index for index in top
                   if features[index].delta_open_tunnels == selected]

        return rng.choice([moves[index] for index in top])
