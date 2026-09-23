import pytest

from bandido_alcatraz.model import Direction, Material
from bandido_alcatraz.photo_geometry import (
    PhotoGeometry,
    card_from_photo_geometry,
)


def test_portrait_ports_compile_to_two_half_cells() -> None:
    card = card_from_photo_geometry(
        "shape",
        geometry=PhotoGeometry(
            frozenset({"T", "LU", "RL", "B"}),
            internal_bridge=True,
        ),
    )

    top, bottom = card.cells

    assert top.tunnel_edges == frozenset(
        {
            Direction.NORTH,
            Direction.WEST,
            Direction.SOUTH,
        }
    )
    assert bottom.tunnel_edges == frozenset(
        {
            Direction.NORTH,
            Direction.EAST,
            Direction.SOUTH,
        }
    )


def test_water_half_is_independent_of_geometry() -> None:
    card = card_from_photo_geometry(
        "water",
        geometry=PhotoGeometry(
            frozenset({"LU", "RL"}),
            internal_bridge=True,
        ),
        water_half="bottom",
    )

    assert not card.cells[0].water
    assert card.cells[1].water


def test_equipment_and_exit_metadata_are_preserved() -> None:
    equipment = card_from_photo_geometry(
        "rope",
        geometry=PhotoGeometry(frozenset({"T"}), internal_bridge=False),
        material=Material.ROPE,
    )
    exit_card = card_from_photo_geometry(
        "exit",
        geometry=PhotoGeometry(frozenset({"T", "B"}), internal_bridge=True),
        is_exit=True,
    )

    assert equipment.material is Material.ROPE
    assert exit_card.is_exit


def test_invalid_port_or_water_half_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown photo ports"):
        PhotoGeometry(frozenset({"X"}), internal_bridge=False)

    with pytest.raises(ValueError, match="water_half"):
        card_from_photo_geometry(
            "bad-water",
            geometry=PhotoGeometry(frozenset({"T"}), internal_bridge=False),
            water_half="left",
        )
