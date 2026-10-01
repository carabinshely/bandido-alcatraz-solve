from __future__ import annotations

from dataclasses import dataclass

from .model import Material

RULESET_ID = "v2-exact-equipment-quota-limited-collect-full-hand-refresh"


@dataclass(frozen=True, slots=True)
class GameStatus:
    raincoats: int
    ropes: int
    open_tunnels: int
    visible_water_cells: int
    exit_placed: bool


def is_equipment_ready(raincoats: int, ropes: int) -> bool:
    """Canonical invariant: exactly three raincoats and two ropes."""
    return raincoats == 3 and ropes == 2


def can_collect(material: Material | None, *, raincoats: int, ropes: int) -> bool:
    """COLLECT is available only while that material's exact quota is unmet."""
    return (
        material is Material.RAINCOAT and raincoats < 3
    ) or (
        material is Material.ROPE and ropes < 2
    )


def is_victory(status: GameStatus) -> bool:
    return (
        status.exit_placed
        and status.open_tunnels == 0
        and status.visible_water_cells == 0
        and is_equipment_ready(status.raincoats, status.ropes)
    )
