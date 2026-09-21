from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Direction(StrEnum):
    NORTH = "N"
    EAST = "E"
    SOUTH = "S"
    WEST = "W"

    def rotated(self, quarter_turns: int) -> "Direction":
        order = (Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST)
        return order[(order.index(self) + quarter_turns) % 4]


class Material(StrEnum):
    RAINCOAT = "raincoat"
    ROPE = "rope"


@dataclass(frozen=True, slots=True)
class CellSpec:
    """One unit cell of a card footprint."""

    x: int
    y: int
    tunnel_edges: frozenset[Direction]
    water: bool = False

    def rotated(self, quarter_turns: int) -> "CellSpec":
        turns = quarter_turns % 4
        x, y = self.x, self.y
        for _ in range(turns):
            x, y = -y, x
        return CellSpec(
            x=x,
            y=y,
            tunnel_edges=frozenset(edge.rotated(turns) for edge in self.tunnel_edges),
            water=self.water,
        )


@dataclass(frozen=True, slots=True)
class CardDefinition:
    """Abstract card definition without artwork or assumed multiplicity."""

    card_id: str
    cells: tuple[CellSpec, ...]
    material: Material | None = None
    is_exit: bool = False

    def __post_init__(self) -> None:
        if not self.cells:
            raise ValueError("a card must contain at least one cell")
        coords = [(cell.x, cell.y) for cell in self.cells]
        if len(coords) != len(set(coords)):
            raise ValueError("card cells must occupy unique coordinates")
        if self.is_exit and self.material is not None:
            raise ValueError("EXIT card cannot also be equipment")

    @property
    def has_water(self) -> bool:
        return any(cell.water for cell in self.cells)

    def rotated(self, quarter_turns: int) -> "CardDefinition":
        rotated_cells = [cell.rotated(quarter_turns) for cell in self.cells]
        min_x = min(cell.x for cell in rotated_cells)
        min_y = min(cell.y for cell in rotated_cells)
        normalized = tuple(
            CellSpec(
                x=cell.x - min_x,
                y=cell.y - min_y,
                tunnel_edges=cell.tunnel_edges,
                water=cell.water,
            )
            for cell in sorted(rotated_cells, key=lambda item: (item.y, item.x))
        )
        return CardDefinition(
            self.card_id,
            normalized,
            self.material,
            self.is_exit,
        )
