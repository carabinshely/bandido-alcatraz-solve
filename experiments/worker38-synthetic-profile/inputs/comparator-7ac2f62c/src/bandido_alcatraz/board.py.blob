from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from .model import CardDefinition, CellSpec, Direction

Coord = tuple[int, int]

_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (0, -1),
    Direction.EAST: (1, 0),
    Direction.SOUTH: (0, 1),
    Direction.WEST: (-1, 0),
}
_OPPOSITE: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.EAST: Direction.WEST,
    Direction.SOUTH: Direction.NORTH,
    Direction.WEST: Direction.EAST,
}


class PlacementKind(StrEnum):
    START = "start"
    ORDINARY = "ordinary"
    EXIT = "exit"


@dataclass(frozen=True, slots=True)
class VisibleCell:
    tunnel_edges: frozenset[Direction]
    water: bool = False


@dataclass(frozen=True, slots=True)
class CardPlacement:
    """One physical card placement retained for final-board rendering."""

    card_id: str
    origin: Coord
    quarter_turns: int
    placement_index: int
    kind: PlacementKind
    cells: tuple[Coord, ...]
    overlaps: tuple[Coord, ...] = ()
    covered_placement_index: int | None = None


@dataclass(frozen=True, slots=True)
class _PlacementHistoryNode:
    placement: CardPlacement
    previous: _PlacementHistoryNode | None


class Board:
    def __init__(self) -> None:
        self._cells: dict[Coord, VisibleCell] = {}
        # Persistent linked history keeps clone() and hypothetical policy
        # previews O(1) while retaining enough physical-card provenance for
        # final rendering.
        self._placement_tail: _PlacementHistoryNode | None = None
        self._placement_count = 0

    @property
    def cells(self) -> dict[Coord, VisibleCell]:
        return dict(self._cells)

    @property
    def placements(self) -> tuple[CardPlacement, ...]:
        records: list[CardPlacement] = []
        node = self._placement_tail
        while node is not None:
            records.append(node.placement)
            node = node.previous
        records.reverse()
        return tuple(records)

    @property
    def visible_water_cells(self) -> int:
        return sum(cell.water for cell in self._cells.values())

    @property
    def open_tunnels(self) -> int:
        return sum(self.open_tunnel_target_counts.values())

    @property
    def open_tunnel_target_counts(self) -> Counter[Coord]:
        targets: Counter[Coord] = Counter()
        for (x, y), cell in self._cells.items():
            for edge in cell.tunnel_edges:
                dx, dy = _DELTAS[edge]
                neighbor = (x + dx, y + dy)
                if neighbor not in self._cells:
                    targets[neighbor] += 1
        return targets

    @property
    def merge_opportunities(self) -> int:
        return sum(
            count * (count - 1) // 2
            for count in self.open_tunnel_target_counts.values()
            if count >= 2
        )

    @property
    def water_obstruction(self) -> int:
        obstruction = 0
        for (x, y), cell in self._cells.items():
            if not cell.water:
                continue
            for dx, dy in _DELTAS.values():
                if (x + dx, y + dy) in self._cells:
                    obstruction += 1
        return obstruction

    @property
    def trapped_water_cells(self) -> int:
        trapped = 0
        for (x, y), cell in self._cells.items():
            if not cell.water:
                continue
            empty_neighbors = sum(
                (x + dx, y + dy) not in self._cells
                for dx, dy in _DELTAS.values()
            )
            if empty_neighbors == 0:
                trapped += 1
        return trapped

    def clone(self) -> "Board":
        other = Board()
        other._cells = dict(self._cells)
        other._placement_tail = self._placement_tail
        other._placement_count = self._placement_count
        return other

    def candidate_origins(self, card: CardDefinition) -> set[Coord]:
        """Generate plausible origins; can_place remains the authority."""
        origins: set[Coord] = set()

        for (x, y), existing in self._cells.items():
            for edge in existing.tunnel_edges:
                dx, dy = _DELTAS[edge]
                neighbor = (x + dx, y + dy)
                if neighbor in self._cells:
                    continue
                required = _OPPOSITE[edge]
                for cell in card.cells:
                    if required in cell.tunnel_edges:
                        origins.add((neighbor[0] - cell.x, neighbor[1] - cell.y))

        water_coords = [coord for coord, cell in self._cells.items() if cell.water]
        for water_coord in water_coords:
            for cell in card.cells:
                origins.add((water_coord[0] - cell.x, water_coord[1] - cell.y))

        return origins

    def seed(
        self,
        card: CardDefinition,
        origin: Coord = (0, 0),
        quarter_turns: int = 0,
    ) -> None:
        if self._cells:
            raise ValueError("board is already seeded")
        placed = card.rotated(quarter_turns)
        self._validate_internal_edges(placed)
        placed_cells: list[Coord] = []
        for cell in placed.cells:
            coord = (origin[0] + cell.x, origin[1] + cell.y)
            placed_cells.append(coord)
            self._cells[coord] = VisibleCell(cell.tunnel_edges, cell.water)
        self._record_placement(
            card=card,
            origin=origin,
            quarter_turns=quarter_turns,
            kind=PlacementKind.START,
            cells=tuple(sorted(placed_cells)),
            overlaps=(),
        )

    def can_place(
        self,
        card: CardDefinition,
        origin: Coord,
        quarter_turns: int = 0,
    ) -> bool:
        try:
            self._prepare_placement(card, origin, quarter_turns)
        except ValueError:
            return False
        return True

    def place(
        self,
        card: CardDefinition,
        origin: Coord,
        quarter_turns: int = 0,
    ) -> None:
        prepared, overlaps = self._prepare_placement(card, origin, quarter_turns)
        for coord, cell in prepared.items():
            # Overlap replaces the visible half-cell. Preserve the new card's
            # water flag: covering a water half with another water half does
            # not make the newly visible water disappear.
            self._cells[coord] = VisibleCell(cell.tunnel_edges, cell.water)
        self._record_placement(
            card=card,
            origin=origin,
            quarter_turns=quarter_turns,
            kind=PlacementKind.EXIT if card.is_exit else PlacementKind.ORDINARY,
            cells=tuple(sorted(prepared)),
            overlaps=tuple(sorted(overlaps)),
        )

    def _record_placement(
        self,
        *,
        card: CardDefinition,
        origin: Coord,
        quarter_turns: int,
        kind: PlacementKind,
        cells: tuple[Coord, ...],
        overlaps: tuple[Coord, ...],
    ) -> None:
        covered_placement_index: int | None = None
        if overlaps:
            overlap = overlaps[0]
            node = self._placement_tail
            while node is not None:
                if overlap in node.placement.cells:
                    covered_placement_index = node.placement.placement_index
                    break
                node = node.previous

        placement = CardPlacement(
            card_id=card.card_id,
            origin=origin,
            quarter_turns=quarter_turns % 4,
            placement_index=self._placement_count,
            kind=kind,
            cells=cells,
            overlaps=overlaps,
            covered_placement_index=covered_placement_index,
        )
        self._placement_tail = _PlacementHistoryNode(
            placement=placement,
            previous=self._placement_tail,
        )
        self._placement_count += 1

    def _prepare_placement(
        self, card: CardDefinition, origin: Coord, quarter_turns: int
    ) -> tuple[dict[Coord, CellSpec], set[Coord]]:
        if not self._cells:
            raise ValueError("seed the board before placing ordinary cards")

        placed = card.rotated(quarter_turns)
        self._validate_internal_edges(placed)
        new_cells: dict[Coord, CellSpec] = {
            (origin[0] + cell.x, origin[1] + cell.y): cell for cell in placed.cells
        }
        overlaps = set(new_cells).intersection(self._cells)

        if overlaps:
            if len(overlaps) != 1:
                raise ValueError("a placement may cover only one existing water cell")
            coord = next(iter(overlaps))
            existing = self._cells[coord]
            if not existing.water:
                raise ValueError("only a visible water cell may be covered")
            if new_cells[coord].tunnel_edges != existing.tunnel_edges:
                raise ValueError("water cover must preserve the covered tunnel/earth pattern")

        attached = bool(overlaps)
        for coord, cell in new_cells.items():
            for edge in Direction:
                dx, dy = _DELTAS[edge]
                neighbor_coord = (coord[0] + dx, coord[1] + dy)
                new_has_tunnel = edge in cell.tunnel_edges

                if neighbor_coord in new_cells:
                    neighbor_has_tunnel = (
                        _OPPOSITE[edge] in new_cells[neighbor_coord].tunnel_edges
                    )
                    if new_has_tunnel != neighbor_has_tunnel:
                        raise ValueError("card has mismatched internal edges")
                    continue

                neighbor = self._cells.get(neighbor_coord)
                if neighbor is None or neighbor_coord in overlaps:
                    continue

                neighbor_has_tunnel = _OPPOSITE[edge] in neighbor.tunnel_edges
                if new_has_tunnel != neighbor_has_tunnel:
                    raise ValueError("tunnel/earth mismatch with adjacent card")
                if new_has_tunnel:
                    attached = True

        if not attached:
            raise ValueError("placement must connect to an existing tunnel")

        return new_cells, overlaps

    @staticmethod
    def _validate_internal_edges(card: CardDefinition) -> None:
        cells = {(cell.x, cell.y): cell for cell in card.cells}
        for (x, y), cell in cells.items():
            for edge in Direction:
                dx, dy = _DELTAS[edge]
                neighbor = cells.get((x + dx, y + dy))
                if neighbor is None:
                    continue
                if (edge in cell.tunnel_edges) != (
                    _OPPOSITE[edge] in neighbor.tunnel_edges
                ):
                    raise ValueError("card has mismatched internal edges")
