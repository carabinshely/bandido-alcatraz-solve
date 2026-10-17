"""Independent strategy20 tier calculation over the frozen public validator."""
from __future__ import annotations

from random import Random

from . import strategy
from .board import CardPlacement, PlacementKind, VisibleCell
from .game import PlayerObservation
from .model import CardDefinition, Direction
from .moves import Action, Move
from .quota_reserve_closure_reference import OperationLimits, QuotaReserveClosureReference, ReferenceInputError
from .worker32.evidence import move as move_wire


class MobilityFloorReference(QuotaReserveClosureReference):
    def __init__(self, *, catalog: tuple[CardDefinition, ...],
                 start_card: CardDefinition, exit_card: CardDefinition) -> None:
        if type(catalog) is not tuple:
            raise ReferenceInputError("immutable catalog tuple required")
        super().__init__(catalog=catalog, start_card=start_card,
                         exit_card=exit_card, min_open_override=0)
        if start_card.card_id != "start_easy":
            raise ReferenceInputError("easy START identity required")
        if exit_card.material is not None:
            raise ReferenceInputError("EXIT must be non-equipment")

    def _public_validation(self, obs: PlayerObservation) -> dict:
        def coord(value):
            return (type(value) is tuple and len(value) == 2
                    and all(type(part) is int for part in value))

        for record in obs.board.placements:
            if (type(record) is not CardPlacement or type(record.card_id) is not str
                    or not coord(record.origin) or type(record.quarter_turns) is not int
                    or type(record.placement_index) is not int
                    or type(record.kind) is not PlacementKind
                    or type(record.cells) is not tuple
                    or any(not coord(value) for value in record.cells)
                    or type(record.overlaps) is not tuple
                    or any(not coord(value) for value in record.overlaps)
                    or (record.covered_placement_index is not None
                        and type(record.covered_placement_index) is not int)):
                raise ReferenceInputError("exact placement-history fields required")
        for position, cell in obs.board.cells.items():
            if (not coord(position) or type(cell) is not VisibleCell
                    or type(cell.water) is not bool
                    or type(cell.tunnel_edges) is not frozenset
                    or any(type(edge) is not Direction for edge in cell.tunnel_edges)):
                raise ReferenceInputError("exact visible geometry fields required")
        supply = super()._public_validation(obs)
        if type(obs.board._placement_count) is not int:
            raise ReferenceInputError("public placement counter must be an exact integer")
        return supply

    def evaluate(self, observation: PlayerObservation, rng: Random, *,
                 limits: OperationLimits | None = None) -> tuple[Move | None, dict, dict]:
        if type(rng) is not Random:
            raise ReferenceInputError("exact canonical Random required")
        return super().evaluate(observation, rng, limits=limits)

    def _compute(self, obs: PlayerObservation) -> tuple[list[Move], dict]:
        self._public_validation(obs)
        roots = obs.legal_moves()
        scores = [strategy.score_move_no_draw(obs, root, self._weights) for root in roots]
        marks = []
        kept = []
        for index, root in enumerate(roots):
            if root.action is Action.COLLECT:
                projected_open = obs.board.open_tunnels
                eliminate = False
            else:
                projected = strategy.preview_move_without_draw(obs, root).successor
                projected_open = projected.board.open_tunnels
                eliminate = projected_open < 3 and not projected.won
            marks.append(dict(action=root.action.value, after_open=projected_open,
                              risky=eliminate))
            if not eliminate:
                kept.append(index)
        candidates = kept or list(range(len(roots)))
        peak = max((scores[index] for index in candidates), default=None)
        final_indices = [index for index in candidates if scores[index] == peak]
        science = dict(schema="strategy20-global-mobility-floor-v1",
                       roots=[dict(move=move_wire(root), score=score)
                              for root, score in zip(roots, scores)],
                       tiers=dict(safe=kept, final=final_indices), mobility=marks,
                       flags=dict(floor_active=bool(kept) and len(kept) < len(roots),
                                  floor_fallback=bool(roots) and not kept))
        return [roots[index] for index in final_indices], science
