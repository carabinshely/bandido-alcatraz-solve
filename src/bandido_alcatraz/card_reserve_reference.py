"""Independent public-card-degree scoring reference for strategy27."""
from __future__ import annotations

from . import strategy
from .game import PlayerObservation
from .late_closure_reference import LateClosureReference
from .model import Direction
from .moves import Action, Move
from .quota_reserve_closure_reference import ReferenceIntegrityError
from .worker32.evidence import move as move_wire


_DELTAS = {
    Direction.NORTH: (0, -1), Direction.EAST: (1, 0),
    Direction.SOUTH: (0, 1), Direction.WEST: (-1, 0),
}


def _public_outlets(card) -> int:
    occupied = {(cell.x, cell.y) for cell in card.cells}
    return sum((cell.x + _DELTAS[edge][0], cell.y + _DELTAS[edge][1])
               not in occupied
               for cell in card.cells for edge in cell.tunnel_edges)


class CardReserveReference(LateClosureReference):
    def _compute(self, obs: PlayerObservation) -> tuple[list[Move], dict]:
        self._public_validation(obs)
        roots = obs.legal_moves()
        weights = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            bounded_merge_setup_gain=250,
        )
        base_scores = [strategy.score_move_no_draw(obs, root, weights)
                       for root in roots]
        degrees = [
            _public_outlets(obs.hand[root.hand_index])
            if root.action is Action.PLACE and not obs.hand[root.hand_index].is_exit
            else None for root in roots
        ]
        bonuses = [2000 * (degree - 2) if obs.turns < 50 and degree is not None
                   else 0 for degree in degrees]
        scores = [base + extra for base, extra in zip(base_scores, bonuses)]
        if any(type(score) is not int for score in scores):
            raise ReferenceIntegrityError("candidate scores must be exact integers")
        peak = max(scores, default=None)
        finalists = [index for index, score in enumerate(scores) if score == peak]
        science = dict(
            schema="strategy27-card-reserve-v1",
            roots=[dict(move=move_wire(root), score=score, v4_score=base,
                        outlet_degree=degree, bonus=bonus)
                   for root, score, base, degree, bonus
                   in zip(roots, scores, base_scores, degrees, bonuses)],
            tiers=dict(final=finalists),
            flags=dict(reserve_active=obs.turns < 50, degree_bonus=2000),
        )
        return [roots[index] for index in finalists], science
