from __future__ import annotations

from dataclasses import dataclass

from .model import CardDefinition, CellSpec, Direction, Material


PHOTO_PORTS = {"T", "B", "LU", "LL", "RU", "RL"}


@dataclass(frozen=True, slots=True)
class PhotoGeometry:
    external_ports: frozenset[str]
    internal_bridge: bool

    def __post_init__(self) -> None:
        unknown = self.external_ports - PHOTO_PORTS
        if unknown:
            raise ValueError(f"unknown photo ports: {sorted(unknown)}")


def card_from_photo_geometry(
    card_id: str,
    *,
    geometry: PhotoGeometry,
    material: Material | None = None,
    water_half: str | None = None,
    is_exit: bool = False,
) -> CardDefinition:
    if water_half not in (None, "top", "bottom"):
        raise ValueError("water_half must be null, top, or bottom")

    top: set[Direction] = set()
    bottom: set[Direction] = set()

    if "T" in geometry.external_ports:
        top.add(Direction.NORTH)
    if "B" in geometry.external_ports:
        bottom.add(Direction.SOUTH)
    if "LU" in geometry.external_ports:
        top.add(Direction.WEST)
    if "RU" in geometry.external_ports:
        top.add(Direction.EAST)
    if "LL" in geometry.external_ports:
        bottom.add(Direction.WEST)
    if "RL" in geometry.external_ports:
        bottom.add(Direction.EAST)

    if geometry.internal_bridge:
        top.add(Direction.SOUTH)
        bottom.add(Direction.NORTH)

    return CardDefinition(
        card_id=card_id,
        cells=(
            CellSpec(
                0,
                0,
                frozenset(top),
                water=water_half == "top",
            ),
            CellSpec(
                0,
                1,
                frozenset(bottom),
                water=water_half == "bottom",
            ),
        ),
        material=material,
        is_exit=is_exit,
    )
