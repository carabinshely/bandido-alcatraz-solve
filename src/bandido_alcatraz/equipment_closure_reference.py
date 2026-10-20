"""Independent public-input score calculation for equipment-triggered closure."""
from __future__ import annotations

from . import strategy
from .game import PlayerObservation
from .late_closure_reference import LateClosureReference
from .moves import Move
from .quota_reserve_closure_reference import ReferenceIntegrityError
from .rules import is_equipment_ready
from .worker32.evidence import move as move_wire


class EquipmentClosureReference(LateClosureReference):
    def _compute(self, obs: PlayerObservation) -> tuple[list[Move], dict]:
        self._public_validation(obs)
        roots = obs.legal_moves()
        ready = is_equipment_ready(obs.raincoats, obs.ropes)
        weights = strategy.PolicyWeights(
            collect_excess=0, delta_visible_water=20_000,
            delta_water_obstruction=1_000, new_trapped_water=-100_000,
            bounded_merge_setup_gain=250,
            delta_open_tunnels=1000 if ready else 100,
        )
        scores = [strategy.score_move_no_draw(obs, root, weights)
                  for root in roots]
        if any(type(score) is not int for score in scores):
            raise ReferenceIntegrityError("canonical scores must be exact integers")
        peak = max(scores, default=None)
        final_indices = [index for index, score in enumerate(scores)
                         if score == peak]
        science = dict(schema="strategy25-equipment-closure-v1",
                       roots=[dict(move=move_wire(root), score=score)
                              for root, score in zip(roots, scores)],
                       tiers=dict(final=final_indices),
                       flags=dict(equipment_ready=ready,
                                  closure_weight=weights.delta_open_tunnels))
        return [roots[index] for index in final_indices], science
