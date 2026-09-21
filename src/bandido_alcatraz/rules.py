from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameStatus:
    raincoats: int
    ropes: int
    open_tunnels: int
    visible_water_cells: int
    exit_placed: bool


def is_equipment_ready(raincoats: int, ropes: int) -> bool:
    """Project v0 rule: required equipment is a minimum threshold."""
    return raincoats >= 3 and ropes >= 2


def is_victory(status: GameStatus) -> bool:
    return (
        status.exit_placed
        and status.open_tunnels == 0
        and status.visible_water_cells == 0
        and is_equipment_ready(status.raincoats, status.ropes)
    )
