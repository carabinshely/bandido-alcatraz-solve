from __future__ import annotations

from .model import CardDefinition, CellSpec, Direction


_PORTS = {"W", "E", "NW", "NE", "SW", "SE"}


def card_from_port_geometry(
    card_id: str,
    *,
    external_ports: list[str],
    internal_bridge: bool,
) -> CardDefinition:
    ports = set(external_ports)
    unknown = ports - _PORTS
    if unknown:
        raise ValueError(f"unknown external ports: {sorted(unknown)}")
    if len(ports) != len(external_ports):
        raise ValueError("external ports must be unique")

    left_edges: set[Direction] = set()
    right_edges: set[Direction] = set()

    if "W" in ports:
        left_edges.add(Direction.WEST)
    if "NW" in ports:
        left_edges.add(Direction.NORTH)
    if "SW" in ports:
        left_edges.add(Direction.SOUTH)

    if "E" in ports:
        right_edges.add(Direction.EAST)
    if "NE" in ports:
        right_edges.add(Direction.NORTH)
    if "SE" in ports:
        right_edges.add(Direction.SOUTH)

    if internal_bridge:
        left_edges.add(Direction.EAST)
        right_edges.add(Direction.WEST)

    return CardDefinition(
        card_id,
        (
            CellSpec(0, 0, frozenset(left_edges)),
            CellSpec(1, 0, frozenset(right_edges)),
        ),
    )
